import json
import math
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from digital_oracle.asset_store import AssetStore, digest
from digital_oracle.macro_store import MacroStore
from digital_oracle.macro_core import Evidence, change, surprise, event_reaction, memory_relevance
from digital_oracle.macro_sources import parse_ecb, parse_fred, parse_rba, parse_rbnz, parse_feed, collect_public, REGISTRY
from digital_oracle.macro_pipeline import build_asset, matched_spread, macro_dashboard
from digital_oracle.macro_ai import config, validate_summary, research
from digital_oracle.upstream import inspect_project, track
from scripts.gold_state import pack, unpack
from cryptography.fernet import Fernet

NOW='2026-10-06T10:00:00+00:00'


class MathTests(unittest.TestCase):
    def test_surprise_frozen_consensus_required(self):
        args=dict(units='%',consensus_units='%',event_time=NOW,consensus_available_at='2026-10-06T09:59:00Z')
        value=surprise(.4,.3,**args,prior_surprises=[-.2,.2]*15)
        self.assertAlmostEqual(value['raw'],.1);self.assertIsNotNone(value['z'])
        args['consensus_available_at']=NOW
        self.assertEqual(surprise(.4,.3,**args)['status'],'UNKNOWN')
        self.assertEqual(surprise(.4,None,**args)['status'],'MISSING')

    def test_surprise_units_and_insufficient_distribution(self):
        args=dict(units='%',consensus_units='bp',event_time=NOW,consensus_available_at='2026-10-06T09:00:00Z')
        self.assertEqual(surprise(.4,.3,**args)['status'],'UNKNOWN')
        args['consensus_units']='%'
        self.assertIsNone(surprise(.4,.3,**args)['z'])

    def test_nonfinite_and_boolean_rejected(self):
        for x in (float('nan'),float('inf'),True):
            with self.assertRaises(ValueError):Evidence(asset='gold',country=['US'],topic='x',family='rates',layer='tactical',source='s',source_quality=1,url='',ingestion_time=NOW,available_at=NOW,actual=x)

    def test_normalization_prior_only(self):
        rows=[{'date':f'{i:04}','close':2+math.sin(i)/10+i/1000} for i in range(260)]
        a=change(rows,5,'bp');changed=[*rows[:-1],{**rows[-1],'close':20}];b=change(changed,5,'bp')
        self.assertEqual(a['z_mean'],b['z_mean']);self.assertEqual(a['z_std'],b['z_std']);self.assertNotEqual(a['value'],b['value'])
        self.assertEqual(a['normalization_n'],252)

    def test_native_days_not_calendar_days(self):
        rows=[{'date':'2026-10-02','close':100},{'date':'2026-10-05','close':110}]
        value=change(rows,1);self.assertAlmostEqual(value['value'],100*math.log(1.1));self.assertEqual(value['from_date'],'2026-10-02')
        self.assertIsNone(change(rows,5))

    def test_daily_quotes_cannot_fake_event_reaction(self):
        quotes=[dict(time='2026-10-06T09:59:30Z',value=100,available_at='2026-10-06T09:59:30Z',instrument='XAU'),dict(time='2026-10-06T10:05:00Z',value=101,available_at='2026-10-06T10:05:00Z',instrument='XAU')]
        self.assertEqual(event_reaction(NOW,quotes,5,'2026-10-06T10:10:00Z')['status'],'MISSING')
        for q in quotes:q['granularity_seconds']=30
        self.assertEqual(event_reaction(NOW,quotes,5,'2026-10-06T10:10:00Z')['status'],'available')
        quotes[0]['available_at']='2026-10-06T10:01:00Z'
        self.assertEqual(event_reaction(NOW,quotes,5,'2026-10-06T10:10:00Z')['status'],'MISSING')
        self.assertEqual(event_reaction(NOW,quotes,5,'2026-10-06T10:01:00Z')['status'],'PENDING')

    def test_memory_relevance_not_prediction_weight(self):
        self.assertEqual(memory_relevance(NOW,NOW,'event'),1)
        self.assertAlmostEqual(memory_relevance(NOW,'2026-10-09T10:00:00Z','event'),.5)
        self.assertGreater(memory_relevance(NOW,'2026-10-09T10:00:00Z','structural'),.9)

    def test_availability_cannot_precede_publication(self):
        with self.assertRaises(ValueError):
            Evidence(asset='gold',country=['US'],topic='x',family='events',layer='event',source='s',source_quality=1,
                     url='',ingestion_time=NOW,available_at=NOW,publication_time='2026-10-06T10:01:00Z')

    def test_invalid_reaction_window_and_impossible_quote(self):
        with self.assertRaises(ValueError):event_reaction(NOW,[],0,NOW)
        quotes=[{'time':'2026-10-06T09:59:30Z','available_at':'2026-10-06T09:59:00Z','value':100,'instrument':'XAU','granularity_seconds':30},
                {'time':'2026-10-06T10:05:00Z','available_at':'2026-10-06T10:05:00Z','value':101,'instrument':'XAU','granularity_seconds':30}]
        self.assertEqual(event_reaction(NOW,quotes,5,'2026-10-06T10:10:00Z')['status'],'MISSING')


class SourceTests(unittest.TestCase):
    def test_ecb_cross_quote_conventions_and_future(self):
        raw=b'<Envelope><Cube><Cube time="2026-10-05"><Cube currency="AUD" rate="1.6"/><Cube currency="NZD" rate="2"/><Cube currency="USD" rate="1.2"/><Cube currency="JPY" rate="180"/></Cube><Cube time="2026-10-06"><Cube currency="AUD" rate="1"/></Cube></Cube></Envelope>'
        value=parse_ecb(raw,'2026-10-06')
        self.assertEqual(value['audnzd'][0]['close'],1.25);self.assertEqual(value['eurusd'][0]['close'],1.2);self.assertEqual(value['usdjpy'][0]['close'],150)

    def test_fred_missing_nonfinite_and_today(self):
        raw=b'observation_date,X\n2026-10-01,2.5\n2026-10-02,.\n2026-10-03,inf\n2026-10-06,3'
        self.assertEqual(parse_fred(raw,'2026-10-06'),[{'date':'2026-10-01','close':2.5}])

    def test_rba_series_id_not_position(self):
        raw=b'Title,Other,Cash\nSeries ID,SOMETHING,FCMMCRTD\n02-Oct-2026,100,3.5\n06-Oct-2026,100,4'
        self.assertEqual(parse_rba(raw,'2026-10-06')[0]['close'],3.5)
        with self.assertRaises(ValueError):parse_rba(b'Title,Cash\n02-Oct-2026,3.5','2026-10-06')

    def test_rbnz_requires_dated_ocr_column(self):
        raw=b'<table><tr><th>Date</th><th>Official Cash Rate (OCR)</th><th>30 days</th></tr><tr><td>02 Oct 2026</td><td>2.75</td><td>3</td></tr></table>'
        self.assertEqual(parse_rbnz(raw,'2026-10-06')[0]['close'],2.75)
        with self.assertRaises(ValueError):parse_rbnz(b'<p>OCR is 3</p>','2026-10-06')

    def test_feed_future_is_not_known(self):
        raw=b'<rss><channel><item><title>Current</title><link>https://example.org/1</link><pubDate>Mon, 05 Oct 2026 12:00:00 GMT</pubDate></item><item><title>Future</title><pubDate>Wed, 07 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>'
        self.assertEqual(len(parse_feed(raw,NOW)),1)

    def test_failed_collection_is_unknown_not_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            store=MacroStore(Path(folder)/'x.sqlite')
            def fail(url):raise TimeoutError('private gateway diagnostic')
            results=collect_public(store,NOW,fail)
            self.assertTrue(all(r['status']=='UNKNOWN' for r in results.values()))
            self.assertNotIn('private',json.dumps(results));store.close()


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.db=Path(self.temp.name)/'x.sqlite';self.store=MacroStore(self.db)

    def tearDown(self):self.store.close();self.temp.cleanup()

    def test_immutable_and_namespace_separation(self):
        legacy=AssetStore(self.db);legacy.put('datasets',{'series':{}},'old')
        self.store.put('macro_snapshots',{'asset_id':'gold','available_at':NOW},'new')
        self.assertEqual(legacy.latest('datasets')['id'],'old')
        with self.assertRaises(ValueError):self.store.put('macro_snapshots',{'changed':True},'new')
        with self.assertRaises(sqlite3.IntegrityError):self.store.db.execute('DELETE FROM macro_snapshots')
        legacy.close()

    def test_pit_different_offsets(self):
        self.store.put('macro_evidence',{'available_at':'2026-10-06T18:01:00+08:00'},'future')
        self.store.put('macro_evidence',{'available_at':'2026-10-06T17:59:00+08:00'},'past')
        self.assertEqual([r['id'] for r in self.store.as_of('macro_evidence',NOW)],['past'])

    def test_macro_archive_encrypted_roundtrip(self):
        self.store.put('macro_evidence',{'available_at':NOW,'raw':'preserve'},'x')
        key=Fernet.generate_key();archive=Path(self.temp.name)/'state.encrypted';restored=Path(self.temp.name)/'restore.sqlite'
        pack(self.db,archive,key);unpack(archive,restored,key)
        s=MacroStore(restored);self.assertEqual(s.get('macro_evidence','x')['raw'],'preserve');s.close()

    def test_snapshot_replay_hash_survives_display(self):
        view=build_asset('gold',{}, {},NOW)
        view['id']=self.store.put('macro_snapshots',view)
        frozen=self.store.get('macro_snapshots',view['id']);before=digest(frozen)
        rendered=macro_dashboard(self.store,'gold',NOW)
        self.assertTrue(rendered['evidence']);self.assertEqual(digest(self.store.get('macro_snapshots',view['id'])),before)

    def test_fx_requires_matched_dates_and_marks_stale(self):
        a={'status':'available','source':'AU','url':'https://example.org/a','rows':[{'date':'2026-10-01','close':3.5}]}
        b={'status':'available','source':'NZ','url':'https://example.org/b','rows':[{'date':'2026-09-30','close':2.75}]}
        e=matched_spread('audnzd',a,b,NOW,'policy_spread','theory');self.assertIsNone(e['actual'])
        b['rows'][0]['date']='2026-10-01';e=matched_spread('audnzd',a,b,NOW,'policy_spread','theory');self.assertEqual(e['actual'],.75)
        self.assertEqual(e['stance'],'context');self.assertEqual(len(e['source_refs']),2)


class AITests(unittest.TestCase):
    def test_missing_secret_degrades_and_never_exposes(self):
        with patch.dict(os.environ,{},clear=True):self.assertEqual(config('deepseek')['status'],'not_configured')
        with patch.dict(os.environ,{'ORACLE_AI_BASE_URL':'http://127.0.0.1/private'},clear=True):self.assertEqual(config('openai-compatible')['status'],'invalid_configuration')

    def test_untraceable_claim_and_numeric_invention_rejected(self):
        evidence=[{'id':'a'}];base={'edge':'NO CLEAR EDGE','uncertainties':[],'claims':[{'text':'Opportunity cost is a prior.','stance':'context','evidence_ids':['a']}]}
        self.assertEqual(validate_summary(base,evidence)['edge'],'NO CLEAR EDGE')
        for bad in ({'text':'Gold will rise 60%'},{'evidence_ids':['invented']},{'stance':'BUY'}):
            body={**base,'claims':[{**base['claims'][0],**bad}]}
            with self.assertRaises(ValueError):validate_summary(body,evidence)

    def test_agent_selects_evidence_and_logs_tool(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'DEEPSEEK_API_KEY':'test-placeholder'},clear=True):
            store=MacroStore(Path(folder)/'x.sqlite');view=build_asset('gold',{}, {},NOW);view['id']='snapshot'
            evidence_id=view['evidence'][0]['id'];calls=[]
            def provider(body,cfg):
                calls.append(body)
                if len(calls)==1:return {'role':'assistant','content':None,'tool_calls':[{'id':'t','type':'function','function':{'name':'select_evidence','arguments':json.dumps({'ids':[evidence_id]})}}]}
                return {'role':'assistant','content':json.dumps({'edge':'NO CLEAR EDGE','uncertainties':['Missing pricing.'],'claims':[{'text':'The source is missing.','stance':'unknown','evidence_ids':[evidence_id]}]})}
            result=research(view,store,'deepseek',language='en',call=provider)
            self.assertEqual(result['status'],'available');self.assertEqual(len(result['tool_audit']),1)
            self.assertNotIn('test-placeholder',json.dumps(result));self.assertEqual(len(store.list('macro_ai')),1);store.close()

    def test_research_without_inspecting_values_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'DEEPSEEK_API_KEY':'test-placeholder'},clear=True):
            store=MacroStore(Path(folder)/'x.sqlite');view=build_asset('gold',{}, {},NOW);view['id']='snapshot'
            def provider(body,cfg):return {'content':json.dumps({'edge':'NO CLEAR EDGE','uncertainties':[],'claims':[]})}
            self.assertEqual(research(view,store,'deepseek',call=provider)['status'],'failed');store.close()


class UpstreamTests(unittest.TestCase):
    project={'repository':'owner/repo','baseline':'a'*40,'paths':['data/'],'adoption':'architecture only'}

    def fixture(self,path):
        if path.endswith('repos/owner/repo'):return {'full_name':'owner/repo','default_branch':'main','html_url':'https://github.com/owner/repo','archived':False,'license':{'spdx_id':'MIT'}}
        if '/commits/' in path:return {'sha':'b'*40,'commit':{'committer':{'date':NOW}}}
        if '/license?' in path:return {'sha':'license-new','html_url':'https://github.com/owner/repo/LICENSE'}
        if 'releases/latest' in path:return None
        if '/compare/' in path:return {'files':[{'filename':'data/pit.py','status':'modified'},{'filename':'logo.svg','status':'modified'}],'ahead_by':2}
        if 'security-advisories' in path:return []
        raise ValueError(path)

    def test_upstream_change_license_and_relevance(self):
        row=inspect_project(self.project,{'status':'available','head':'a'*40,'license_blob':'license-old'},self.fixture,NOW)
        self.assertEqual(row['status'],'available');self.assertTrue(row['license_changed']);self.assertTrue(row['changes'][0]['research_relevant'])
        self.assertFalse(row['changes'][1]['research_relevant']);self.assertEqual(row['action'],'No automatic adoption')

    def test_failed_check_unknown_not_no_update(self):
        def fail(path):raise TimeoutError('sensitive diagnostics')
        row=inspect_project(self.project,fetch=fail,checked_at=NOW)
        self.assertEqual(row['status'],'UNKNOWN');self.assertNotIn('sensitive',json.dumps(row))

    def test_release_update_requires_review_even_without_new_head(self):
        prior={'status':'available','head':'b'*40,'release':{'tag_name':'old'},'license_blob':'license-new'}
        row=inspect_project(self.project,prior,self.fixture,NOW)
        self.assertFalse(row['changed']);self.assertTrue(row['release_changed']);self.assertEqual(row['impact'],'REVIEW_REQUIRED')

    def test_review_queue_persists_after_unchanged_check(self):
        from digital_oracle.upstream import pending_reviews
        with tempfile.TemporaryDirectory() as folder:
            store=MacroStore(Path(folder)/'x.sqlite')
            with patch('digital_oracle.upstream.WATCHLIST',Path(folder)/'watch.json'):
                Path(folder,'watch.json').write_text(json.dumps({'policy':'observe','projects':[self.project]}),encoding='utf-8')
                track(store,self.fixture,NOW);track(store,self.fixture,NOW)
            self.assertEqual(len(pending_reviews(store)),1);store.close()

    def test_successful_prior_not_erased_by_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            store=MacroStore(Path(folder)/'x.sqlite');store.put('upstream_observations',{'repository':'owner/repo','status':'available','head':'a'*40,'checked_at':NOW})
            with patch('digital_oracle.upstream.WATCHLIST',Path(folder)/'watch.json'):
                # Fixture file creation is a test operation, not editing repository source.
                Path(folder,'watch.json').write_text(json.dumps({'policy':'observe','projects':[self.project]}),encoding='utf-8')
                result=track(store,self.fixture,NOW)
            self.assertEqual(result['projects'][0]['compared_from'],'a'*40);self.assertEqual(len(store.list('upstream_observations')),2);store.close()


if __name__=='__main__':unittest.main()
