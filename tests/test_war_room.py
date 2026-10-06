from pathlib import Path
import tempfile
import unittest

from digital_oracle.macro_store import MacroStore
from digital_oracle.macro_pipeline import build_asset
from digital_oracle.war_room import board
from digital_oracle.research_team import PROMPT_VERSION

NOW = '2026-10-06T08:00:00+00:00'


class BoardTests(unittest.TestCase):
    def test_actual_pending_daily_admission_visible_but_private_question_not_exported(self):
        with tempfile.TemporaryDirectory() as folder:
            store=MacroStore(Path(folder)/'x.sqlite');view=build_asset('gold',{}, {},NOW)
            sid=store.put('macro_snapshots',view)
            for scope in ('daily','private'):
                session=store.put('research_sessions',{'snapshot_id':sid,'analyst':'liquidity','language':'zh','prompt_version':PROMPT_VERSION,'audience':scope})
                store.put('research_requests',{'session_id':session,'question':'调查流动性。' if scope=='daily' else 'PRIVATE USER QUESTION','phase':'plan','available_at':NOW})
            result=board(store,'gold','zh',NOW)
            self.assertEqual(result['research_run']['process'][0]['status'],'awaiting_result')
            self.assertEqual(result['situation']['status'],'NOT YET ANALYZED')
            self.assertNotIn('PRIVATE USER QUESTION',str(result))
            self.assertEqual(result['research_run']['reports'],[])
            store.close()

    def test_final_director_does_not_erase_member_questions_or_original_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            store=MacroStore(Path(folder)/'x.sqlite');view=build_asset('gold',{}, {},NOW)
            sid=store.put('macro_snapshots',view)
            sections=[{'kind':k,'text':'已读证据仍有缺口。','evidence_ids':[]} for k in ('fact','mechanism','judgment','watch')]
            original={'id':'original','analyst':'director','phase':'plan','status':'available','work_done':True,'assignments':[{'analyst':'liquidity','question':'调查原问题。'}]}
            final={'id':'final','analyst':'chief','phase':'final','status':'available','work_done':True,'assignments':[],'sections':sections}
            store.put('research_runs',{'snapshot_id':sid,'language':'zh','prompt_version':PROMPT_VERSION,'reports':[original,final],'process':[{'analyst':'liquidity','question':'补证传导问题。','stage':'supplement'}]})
            result=board(store,'gold','zh',NOW)
            self.assertEqual(result['situation']['status'],'ANALYZED')
            self.assertEqual(next(m for m in result['team'] if m['analyst']=='liquidity')['task'],'补证传导问题。')
            self.assertEqual(len(result['research_run']['reports']),2)
            store.close()

    def test_missing_data_never_generates_fake_team_or_new_news(self):
        with tempfile.TemporaryDirectory() as folder:
            store=MacroStore(Path(folder)/'x.sqlite')
            view=build_asset('gold',{}, {},NOW)
            view['id']=store.put('macro_snapshots',view)
            result=board(store,'gold','zh',NOW)
            self.assertEqual(result['headline_kind'],'code_generated_context')
            self.assertEqual(result['situation']['status'],'NOT YET ANALYZED')
            self.assertEqual(result['situation']['top_stories'],[])
            self.assertEqual(result['edge'],'NO CLEAR EDGE')
            self.assertEqual(result['chief_brief'],[])
            self.assertTrue(all(not m['work_done'] for m in result['team']))
            self.assertEqual(result['past_24h']['official_releases'],[])
            store.close()

    def test_original_observation_windows_not_relabelled_daily_news(self):
        with tempfile.TemporaryDirectory() as folder:
            store=MacroStore(Path(folder)/'x.sqlite')
            rows=[{'date':f'2026-10-0{i}','close':100+i} for i in range(1,6)]
            rows=[{'date':'2026-09-28','close':100},*rows]
            source={'source':'yahoo','url':'https://finance.yahoo.com','fetched_at':NOW,'rows':rows}
            view=build_asset('gold',{'series':{'gold':source}}, {},NOW)
            view['id']=store.put('macro_snapshots',view)
            result=board(store,'gold','en',NOW)
            self.assertIn('2026-09-28 to 2026-10-05',result['headline'])
            self.assertEqual(result['past_24h']['official_releases'],[])
            self.assertIn('not proof of a forward Edge',result['headline'])
            store.close()


if __name__=='__main__':unittest.main()
