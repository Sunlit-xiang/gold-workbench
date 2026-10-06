"""Cloud contract tests. Run with .vercel-dev/Scripts/python -m unittest this module.

Fakes are test-only; no mock reports are emitted by production APIs. Live cloud
Postgres/DeepSeek acceptance remains separate and requires owner configuration.
"""
import asyncio
from contextlib import nullcontext
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, AsyncMock

try:
    import fastapi
    import vercel.workflow
    CLOUD_AVAILABLE=True
except ImportError: CLOUD_AVAILABLE=False

from digital_oracle.macro_store import MacroStore
from digital_oracle.macro_pipeline import build_asset
from digital_oracle.asset_store import digest, utcnow


class FakeCloudStore(MacroStore):
    TABLES=(*MacroStore.TABLES,'research_packs')
    def __init__(self,path):
        super().__init__(path);self.job_row={'id':'a'*32,'asset':'gold','language':'zh','provider':'deepseek',
                'model':'deepseek-chat','status':'queued','pack_id':None,'created_at':utcnow()}
    def job(self,key): return dict(self.job_row)
    def update_job(self,key,**fields): self.job_row.update(fields)
    def step_lock(self,*args): return nullcontext()
    def close(self): pass


@unittest.skipUnless(CLOUD_AVAILABLE,'isolated Vercel SDK dependencies not installed in this interpreter')
class CloudTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=FakeCloudStore(Path(self.temp.name)/'test.sqlite')
        self.env=patch.dict(os.environ,{'DEEPSEEK_API_KEY':'test-placeholder','WAR_ROOM_PASSWORD':'owner-test-password-long-enough'},clear=True)
        self.env.start()
    def tearDown(self):
        self.env.stop();self.store.db.close();self.temp.cleanup()

    def test_capabilities_no_secret_leak_and_research_requires_owner(self):
        from fastapi.testclient import TestClient
        import app
        with TestClient(app.app,base_url='https://testserver') as client:
            r=client.get('/api/war-room/capabilities');text=r.text
            self.assertEqual(r.status_code,200);self.assertIn('DATABASE_URL',text)
            self.assertNotIn('test-placeholder',text);self.assertNotIn('owner-test-password-long-enough',text)
            r=client.post('/api/war-room/research',json={})
            self.assertEqual(r.status_code,403)
            r=client.post('/api/war-room/research',json={},headers={'Origin':'https://testserver'})
            self.assertEqual(r.status_code,401)
            r=client.post('/api/war-room/login',json={'password':'owner-test-password-long-enough'},headers={'Origin':'https://testserver'})
            self.assertEqual(r.status_code,200);self.assertIn('HttpOnly',r.headers['set-cookie']);self.assertIn('Secure',r.headers['set-cookie'])
            r=client.post('/api/war-room/research',json={'api_key':'browser-secret'},headers={'Origin':'https://testserver'})
            self.assertEqual(r.status_code,400)
            r=client.get('/data/../../private.json');self.assertEqual(r.status_code,404)

    def test_missing_provider_does_not_queue_or_create_storage(self):
        from fastapi.testclient import TestClient
        import app
        with patch.dict(os.environ,{'DEEPSEEK_API_KEY':''}),patch('app.storage',side_effect=AssertionError('must not create storage')):
            with TestClient(app.app,base_url='https://testserver') as client:
                client.post('/api/war-room/login',json={'password':'owner-test-password-long-enough'},headers={'Origin':'https://testserver'})
                r=client.post('/api/war-room/research',json={'asset':'gold','request_id':'request-placeholder-123'},headers={'Origin':'https://testserver'})
                self.assertEqual(r.status_code,503);self.assertFalse(r.json()['work_done'])

    def test_real_static_assets_and_owner_unicode(self):
        from fastapi.testclient import TestClient
        import app
        with TestClient(app.app,base_url='https://testserver') as client:
            for path,kind in (('/','text/html'),('/war-room.js','javascript'),('/war-room.css','text/css')):
                r=client.get(path)
                self.assertEqual(r.status_code,200,path)
                self.assertIn(kind,r.headers['content-type'])
                self.assertGreater(len(r.content),1000)
            self.assertEqual(client.get('/app.py').status_code,404)
            with patch.dict(os.environ,{'WAR_ROOM_PASSWORD':'工作台密码请使用随机长字符串-1234567890'}):
                r=client.post('/api/war-room/login',json={'password':os.environ['WAR_ROOM_PASSWORD']},headers={'Origin':'https://testserver'})
                self.assertEqual(r.status_code,200)

    def test_pack_refresh_failure_is_not_neutral_and_never_rewrites_seed(self):
        from warroom_cloud.pack import assemble
        seed={'asset_id':'gold','snapshot':{'id':'old','as_of':'2025-01-01T00:00:00+00:00'},'dataset':{'series':{}},'pit_history':[]}
        original=copy.deepcopy(seed)
        class BadProvider:
            def fetch(self,key): raise TimeoutError('no fixture network')
        def no_fetch(url): raise TimeoutError('no fixture network')
        pack=assemble(self.store,self.store.job_row,seed=seed,provider=BadProvider(),public_fetch=no_fetch)
        self.assertEqual(seed,original);self.assertTrue(pack['refresh_failures']);self.assertTrue(pack['gaps'])
        self.assertEqual(pack['view']['decision']['edge'],'NO CLEAR EDGE')
        self.assertEqual(pack['pit_history_count'],0)
        with self.assertRaises(ValueError): self.store.put('predictions',{'fake':True})
        with self.assertRaises(Exception): self.store.db.execute('DELETE FROM research_packs')

    def test_real_contract_team_pipeline_checkpoint_and_chief_not_director_final(self):
        import warroom_cloud.workflows as w
        view=build_asset('gold',{}, {},utcnow());view['id']=self.store.put('macro_snapshots',view)
        pack={'view':view,'run_id':'a'*32,'available_at':utcnow(),'gaps':[]};key=self.store.put('research_packs',pack)
        ref=view['evidence'][0]['id']
        def provider(body,cfg):
            current=next(m for m in reversed(body['messages']) if m['role']=='user');payload=json.loads(current['content'])
            tools=[]
            for m in reversed(body['messages']):
                if m is current: break
                tools.extend(c['function']['name'] for c in m.get('tool_calls',[]))
            def tool(name,args): return {'tool_calls':[{'id':'test-call','type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}
            if not tools:return tool('read_evidence',{'ids':[ref]})
            if payload['peer_ids'] and 'read_peer_reports' not in tools:return tool('read_peer_reports',{})
            value={'claims':[{'text':'证据仍有缺口。','stance':'unknown','evidence_ids':[ref]}],
                   'uncertainties':['缺少合格政策定价。'],'edge':'NO CLEAR EDGE',
                   'sections':[{'kind':k,'text':'证据仍有缺口。','evidence_ids':[ref]} for k in ('fact','mechanism','judgment','watch')],
                   'confidence':{'level':'low','basis':'缺口尚未解决。'},'relationships':[],'rework_requests':[]}
            if 'Also return assignments' in body['messages'][0]['content']:
                value['assignments']=[{'analyst':r,'question':'调查机制与缺口。','evidence_ids':[ref]} for r in ('liquidity','rates','cross_asset','gold')]
            return {'content':json.dumps(value)}
        with patch.object(w,'CloudStore',return_value=self.store),patch.object(w,'bounded_call',return_value=provider):
            real_step=w.investigate.func;real_finish=w.finish.func
            with patch.object(w,'prepare',AsyncMock(return_value=key)),patch.object(w,'investigate',side_effect=real_step),patch.object(w,'finish',side_effect=real_finish):
                result=asyncio.run(w.team_research.func('a'*32))
            self.assertEqual(result['status'],'available')
            reports=self.store.latest('research_runs')['reports']
            self.assertEqual([r['analyst'] for r in reports],['director','liquidity','rates','cross_asset','gold','skeptic','director','chief'])
            before=len(self.store.list('research_turns',100))
            repeated=asyncio.run(real_step('a'*32,key,'chief','Read all actual reports and write the final on-demand asset Brief. Preserve unresolved disagreements and missing evidence.','final','synthesis'))
            self.assertEqual(repeated['status'],'available');self.assertEqual(len(self.store.list('research_turns',100)),before)
            self.assertEqual(self.store.job_row['status'],'completed')

    def test_failed_director_does_not_generate_fake_consensus(self):
        import warroom_cloud.workflows as w
        calls=[]
        async def failed(*args):calls.append(args[2]);return {'analyst':'director','status':'failed'}
        async def done(job,pack,reports):return {'reports':reports}
        with patch.object(w,'prepare',AsyncMock(return_value='pack')),patch.object(w,'investigate',side_effect=failed),patch.object(w,'finish',side_effect=done):
            result=asyncio.run(w.team_research.func('a'*32))
        self.assertEqual(calls,['director']);self.assertEqual(len(result['reports']),1)


if __name__=='__main__':unittest.main()
