import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet, InvalidToken
from digital_oracle.gold_delivery import context_snapshot, commentary, export_site
from digital_oracle.asset_store import AssetStore, digest
from scripts.gold_state import pack, unpack
from scripts.publish_ledger import publish


class DeliveryTests(unittest.TestCase):
    def test_rate_bp_and_positioning_pp_not_percent_returns(self):
        series={}
        for key in ('real','gold','cot'):
            series[key]={'rows':[{'date':f'2026-09-{i+1:02d}','close':2+i*.01} for i in range(6)],
                         'unit':'percent','source':'test','instrument':key,'url':'https://example.org',
                         'fetched_at':'2026-09-07','payload_id':'test'}
        result=context_snapshot({'series':series,'created_at':'2026-09-07'})
        facts={f['id']:f for f in result['facts']}
        self.assertAlmostEqual(facts['real']['move'],5)
        self.assertEqual(facts['real']['move_unit'],'bp')
        self.assertAlmostEqual(facts['cot']['move'],4)
        self.assertEqual(facts['cot']['move_unit'],'pp')
        self.assertAlmostEqual(facts['gold']['move'],2.5)

    def test_ai_missing_key_does_not_require_network_or_modify_data(self):
        evidence={'x':1}
        with patch.dict('os.environ',{},clear=True):
            result=commentary(evidence,provider='deepseek')
        self.assertEqual(result['status'],'not_configured')
        self.assertEqual(evidence,{'x':1})
        with self.assertRaises(ValueError):commentary(evidence,provider='http://localhost')

    def test_authenticated_archive_round_trip_and_wrong_key(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);source=folder/'source.sqlite';archive=folder/'db.encrypted'
            s=AssetStore(source);s.put('predictions',{'fixed':1},'p');s.close()
            key=Fernet.generate_key();pack(source,archive,key)
            with self.assertRaises(InvalidToken):unpack(archive,folder/'wrong.sqlite',Fernet.generate_key())
            self.assertFalse((folder/'wrong.sqlite').exists())
            restored=folder/'restored.sqlite';unpack(archive,restored,key)
            s=AssetStore(restored);self.assertEqual(s.get('predictions','p'),{'fixed':1});s.close()
            with self.assertRaises(ValueError):unpack(archive,restored,key)

    def test_public_ledger_allows_first_outcome_but_no_rewrites_or_missing_records(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source';target=Path(folder)/'dest';source.mkdir()
            record={'prediction':{'score':.5},'outcome':None};file=source/'p.json'
            file.write_text(json.dumps(record));publish(source,target)
            record['outcome']={'return':.1};file.write_text(json.dumps(record));publish(source,target)
            record['prediction']['score']=.6;file.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,'prediction'):publish(source,target)
            record['prediction']['score']=.5;record['outcome']['return']=.2;file.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,'outcome'):publish(source,target)
            file.unlink()
            with self.assertRaisesRegex(ValueError,'missing'):publish(source,target)


if __name__=='__main__':unittest.main()
