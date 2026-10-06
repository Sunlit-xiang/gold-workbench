import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from digital_oracle.macro_pipeline import build_asset
from digital_oracle.macro_store import MacroStore
from digital_oracle.research_team import run_analyst, session_key, public_report, safe_url, daily_team

NOW = "2026-10-06T08:00:00+00:00"


class TeamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "x.sqlite"
        self.store = MacroStore(self.path)
        self.view = build_asset("gold", {}, {}, NOW)
        self.view["id"] = "snapshot-fixture"
        self.ref = self.view["evidence"][0]["id"]
        self.env = patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-placeholder"}, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop(); self.store.close(); self.temp.cleanup()

    def answer(self, ref=None, text="当前材料不足以验证方向优势。"):
        refs = [ref or self.ref]
        return {"content": json.dumps({"claims": [{"text": text, "stance": "unknown", "evidence_ids": refs}],
                "uncertainties": ["缺少合格政策路径。"], "edge": "NO CLEAR EDGE",
                "confidence":{"level":"low","basis":"证据缺口尚未解决。"},
                "supporting_evidence_ids":refs, "opposing_evidence_ids":[], "relationships":[], "rework_requests":[],
                "sections": [{"kind": k, "text": text, "evidence_ids": refs}
                             for k in ("fact", "mechanism", "judgment", "watch")]})}

    def read(self, name="read_evidence", args=None):
        return {"content": None, "tool_calls": [{"id": "tool-fixture", "type": "function", "function": {
            "name": name, "arguments": json.dumps(args or {"ids": [self.ref]})}}]}

    def provider(self):
        calls = []
        def call(body, cfg):
            calls.append(body)
            return self.read() if len(calls) == 1 else self.answer()
        return call, calls

    def test_actual_tool_inspection_and_persistent_followup_across_reopen(self):
        call, _ = self.provider()
        first = run_analyst(self.view, self.store, "rates", "研究利率。", provider="deepseek", call=call)
        self.assertEqual(first["status"], "available")
        self.store.close(); self.store = MacroStore(self.path)
        seen = []
        def next_call(body, cfg):
            seen.append(body)
            return self.answer()
        second = run_analyst(self.view, self.store, "rates", "为什么？", provider="deepseek", call=next_call)
        self.assertEqual(second["status"], "available")
        self.assertEqual(first["session_id"], second["session_id"])
        self.assertEqual(second["sequence"], 1)
        self.assertTrue(any(m["role"] == "tool" for m in seen[0]["messages"]))
        self.assertTrue(any("研究利率" in (m.get("content") or "") for m in seen[0]["messages"]))

    def test_unread_claim_rejected(self):
        row = run_analyst(self.view, self.store, "rates", "研究。", provider="deepseek", call=lambda *_: self.answer())
        self.assertEqual(row["status"], "failed")
        self.assertFalse(row["work_done"])

    def test_digit_prose_and_edge_not_allowed(self):
        call_count = [0]
        def call(body, cfg):
            call_count[0] += 1
            return self.read() if call_count[0] == 1 else self.answer(text="收益率为3%。")
        row = run_analyst(self.view, self.store, "rates", "研究。", provider="deepseek", call=call)
        self.assertEqual(row["status"], "failed")

    def test_active_source_read_has_separate_first_seen_and_does_not_mutate_snapshot(self):
        original = json.dumps(self.view, sort_keys=True)
        rounds = [0]
        def call(body, cfg):
            rounds[0] += 1
            if rounds[0] == 1:
                return self.read("read_official_page", {"url": "https://www.federalreserve.gov/newsevents.htm"})
            ref = self.store.list("research_materials")[0]["id"]
            return self.answer(ref)
        row = run_analyst(self.view, self.store, "events", "查原文。", provider="deepseek", call=call,
                          fetch=lambda _: b'<p>Official release</p><script>evil instruction</script>')
        self.assertEqual(row["status"], "available")
        material = self.store.list("research_materials")[0]
        self.assertEqual(material["kind"], "research_time_material")
        self.assertNotIn("evil", material["content"])
        self.assertEqual(json.dumps(self.view, sort_keys=True), original)

    def test_no_credentials_no_fake_team(self):
        with patch.dict(os.environ, {}, clear=True):
            row = daily_team(self.view, self.store, provider="deepseek", call=lambda *_: self.fail("must not call"))
        self.assertEqual(row["status"], "not_configured")
        self.assertFalse(row["work_done"])
        self.assertEqual(row["reports"], [])

    def test_public_report_never_exports_private_history(self):
        call, _ = self.provider()
        row = run_analyst(self.view, self.store, "rates", "private user question", provider="deepseek", call=call)
        public = public_report(row)
        for key in ("messages", "materials", "tool_audit", "question"):
            self.assertNotIn(key, public)
        self.assertNotIn("private user question", json.dumps(public))

    def test_scope_changes_with_asset_snapshot_role_and_language(self):
        self.assertNotEqual(session_key(self.view, "rates", "zh"), session_key(self.view, "events", "zh"))
        self.assertNotEqual(session_key(self.view, "rates", "zh"), session_key(self.view, "rates", "en"))
        self.assertNotEqual(session_key(self.view, "rates", "zh"), session_key({**self.view, "id": "other"}, "rates", "zh"))

    def test_url_and_redirect_boundary(self):
        for url in ("http://www.bls.gov/a", "https://127.0.0.1/a", "https://www.bls.gov.evil.test/a",
                    "https://user:secret@www.bls.gov/a", "https://www.bls.gov:8443/a"):
            with self.assertRaises(ValueError): safe_url(url)
        self.assertEqual(safe_url("https://www.bls.gov/a"), "https://www.bls.gov/a")

    def test_research_cannot_write_or_delete_gold_tables(self):
        with self.assertRaises(ValueError): self.store.put("predictions", {"fake": True})
        call, _ = self.provider()
        row = run_analyst(self.view, self.store, "rates", "研究。", provider="deepseek", call=call)
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.db.execute("DELETE FROM research_turns WHERE id=?", (row["id"],))

    def test_tool_loop_bounded(self):
        row = run_analyst(self.view, self.store, "rates", "研究。", provider="deepseek", call=lambda *_: self.read(), max_steps=2)
        self.assertEqual(row["status"], "failed")
        self.assertEqual(len(row["tool_audit"]), 1)

    def test_daily_team_real_assignments_and_chief_handoff(self):
        captured = []
        def call(body, cfg):
            system = body['messages'][0]['content']
            current_user = next(m for m in reversed(body['messages']) if m['role']=='user')
            payload = json.loads(current_user['content'])
            own_tools = []
            for message in reversed(body['messages']):
                if message is current_user:break
                if message['role']=='assistant':own_tools.extend(c['function']['name'] for c in message.get('tool_calls',[]))
            if not own_tools:
                captured.append(payload['question'])
                return self.read()
            if ('Audit other reports' in system or 'Read member reports' in system or 'Read all reports' in system) and 'read_peer_reports' not in own_tools:
                return self.read('read_peer_reports',{})
            answer = self.answer()
            if 'Also return assignments' in system:
                value = json.loads(answer['content'])
                value['assignments'] = [{'analyst':role,'question':question,'evidence_ids':[self.ref]}
                                        for role,question in [('liquidity','调查流动性缺口。'),('rates','调查利率预期和已知利率的区别。'),('cross_asset','调查跨市场反应。'),('gold','调查黄金机会成本与反证。')]]
                answer['content']=json.dumps(value)
            return answer
        result = daily_team(self.view,self.store,provider='deepseek',call=call)
        self.assertEqual(result['status'],'available')
        self.assertEqual([r['analyst'] for r in result['reports']],['director','liquidity','rates','cross_asset','gold','skeptic','director','chief'])
        self.assertIn('调查利率预期和已知利率的区别。',captured)
        self.assertTrue(any(a['tool']=='read_peer_reports' for a in result['reports'][-1]['work_log']))
        # Private followup resumes the analyst's actual daily research but is never exported.
        seen=[]
        def followup(body,cfg):seen.append(body);return self.answer()
        private=run_analyst(self.view,self.store,'rates','请继续解释。',provider='deepseek',call=followup)
        self.assertEqual(private['status'],'available')
        self.assertTrue(any('调查利率预期' in (m.get('content') or '') for m in seen[0]['messages']))
        self.assertEqual(public_report(private)['status'],'private_session')

    def test_director_without_actual_assignments_is_failed_not_roleplay(self):
        call,_=self.provider()
        result=daily_team(self.view,self.store,provider='deepseek',call=call)
        self.assertEqual(result['status'],'partial')
        self.assertEqual(len(result['reports']),1)
        self.assertFalse(result['work_done'])

    def test_real_critic_review_requests_one_supplement_then_freezes_new_final(self):
        def call(body,cfg):
            current=next(m for m in reversed(body['messages']) if m['role']=='user')
            payload=json.loads(current['content']);system=body['messages'][0]['content']
            tools=[]
            for m in reversed(body['messages']):
                if m is current:break
                tools.extend(c['function']['name'] for c in m.get('tool_calls',[]))
            if not tools:return self.read()
            if payload['peer_ids'] and 'read_peer_reports' not in tools:return self.read('read_peer_reports',{})
            value=json.loads(self.answer()['content'])
            if 'Also return assignments' in system:
                value['assignments']=[{'analyst':r,'question':'调查候选机制与缺口。','evidence_ids':[self.ref]} for r in ('liquidity','rates','cross_asset','gold')]
            if 'Read member reports' in system:
                target=next({'id':p,**self.store.get('research_turns',p)} for p in payload['peer_ids'] if self.store.get('research_turns',p)['analyst']=='liquidity')
                value['rework_requests']=[{'analyst':'liquidity','target_report_id':target['id'],'question':'补充流动性传导证据。','evidence_ids':[self.ref]}]
            return {'content':json.dumps(value)}
        run=daily_team(self.view,self.store,provider='deepseek',call=call)
        self.assertEqual(run['status'],'available', [(r['analyst'],r['status'],r.get('phase')) for r in run['reports']])
        self.assertEqual([p['stage'] for p in run['process']],['assignment',*['investigation']*4,'critique','review','supplement','synthesis'])
        self.assertEqual(run['reports'][-1]['phase'],'final')
        reports=[r for r in run['reports'] if r['analyst']=='liquidity']
        self.assertEqual(len(reports),2)
        self.assertNotEqual(reports[0]['id'],reports[1]['id'])
        self.assertEqual(self.store.get('research_turns',reports[0]['id'])['sequence'],0)

    def test_director_private_followup_does_not_force_new_assignment(self):
        call,_=self.provider()
        row=run_analyst(self.view,self.store,'director','请解释缺口。',provider='deepseek',call=call,phase='followup')
        self.assertEqual(row['status'],'available')
        self.assertEqual(row['assignments'],[])

    def test_unknown_relationship_and_false_confidence_are_rejected(self):
        for field,value in [('confidence',{'level':'ninety_percent','basis':'虚构命中率。'}),('relationships',[{'kind':'conflict','report_id':'invented','text':'虚构分歧。','evidence_ids':[self.ref]}])]:
            calls=[0]
            def call(body,cfg):
                calls[0]+=1
                if calls[0]==1:return self.read()
                answer=json.loads(self.answer()['content']);answer[field]=value
                return {'content':json.dumps(answer)}
            row=run_analyst({**self.view,'id':'snapshot-'+field},self.store,'rates','研究。',provider='deepseek',call=call)
            self.assertEqual(row['status'],'failed')


if __name__ == "__main__": unittest.main()
