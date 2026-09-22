import json
import math
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from digital_oracle.asset_store import AssetStore
from digital_oracle.asset_model import zscore, targets, fit_ridge, prediction_details, build_features, fit_live
from digital_oracle.asset_research import walk_forward, metrics, research
from digital_oracle.asset_pipeline import freeze, publish_shadow, evaluate_due
from digital_oracle.providers.research_history import ResearchHistoryProvider


def dataset(n=1500):
    rng = np.random.default_rng(13)
    days = pd.bdate_range("2010-01-01", periods=n)
    series = {}
    for k in ("gold", "dxy", "spx", "vix", "real", "bei", "us2", "us10", "gld", "silver", "brent", "cot"):
        if k=="cot":
            dates = pd.date_range("2007-01-02", days[-1], freq="W-TUE")
            values = rng.normal(.2, .05, len(dates))
        else:
            dates = days
            values = 100*np.exp(np.cumsum(rng.normal(0,.008,len(days))))
        rows = [{"date": str(d.date()), "close": float(v), "open": float(v), "high": float(v*1.01), "low": float(v*.99), "volume": 100} for d,v in zip(dates, values)]
        series[k] = {"rows": rows, "source": "synthetic", "url": "https://example.invalid", "unit": "test", "first_seen_at": "2000-01-01T00:00:00+00:00", "payload_id": "test-"+k}
    return {"series": series, "created_at": "2000-01-01T00:00:00+00:00", "errors": {}}


class MathematicsTests(unittest.TestCase):
    def test_z_does_not_use_current_or_future(self):
        s = pd.Series(range(1,501), dtype=float)
        z = zscore(s, 30, 20)
        changed = s.copy(); changed.iloc[301:] = 1e9
        self.assertEqual(z.iloc[300], zscore(changed, 30, 20).iloc[300])
        expected = (s.iloc[300]-s.iloc[270:300].mean())/s.iloc[270:300].std()
        self.assertAlmostEqual(z.iloc[300], expected)

    def test_zero_variance_invalid(self):
        self.assertTrue(zscore(pd.Series([1.]*500)).isna().all())

    def test_target_is_after_issue(self):
        f = pd.DataFrame({"price": np.arange(100,130), "rv": .2}, index=pd.bdate_range("2020-01-01",periods=30))
        ret, sigma, b, e = targets(f, 5)
        for i in np.flatnonzero(np.isfinite(ret)):
            self.assertGreater(f.index[b[i]], f.index[i]+pd.Timedelta(days=1))
            self.assertEqual(e[i]-b[i],5)
            self.assertAlmostEqual(ret[i], math.log(f.price.iloc[e[i]]/f.price.iloc[b[i]]))

    def test_ridge_and_contribution_identity(self):
        d = dataset(); f = build_features(d); m = fit_live(f,1)
        self.assertIsNotNone(m)
        details = prediction_details(f,m,1,d)
        total = sum(x["contribution"] for x in details["tree"])+details["intercept_contribution"]
        self.assertAlmostEqual(total, details["score"],12)
        self.assertEqual(details["edge"],"No Edge")
        self.assertTrue(all(x["contribution"]==0 for x in details["tree"] if x["role"] in ("context","risk","disabled")))

    def test_future_changes_do_not_change_past_predictions(self):
        f = build_features(dataset())
        first,_ = walk_forward(f,5,["trend","dxy","real"])
        changed = f.copy(); changed.loc[changed.index[1200]:,"price"] *= 10
        second, fits = walk_forward(changed,5,["trend","dxy","real"])
        np.testing.assert_allclose(first[:1180],second[:1180],equal_nan=True)
        for fit in fits:
            self.assertLess(fit["last_label"],fit["date"])

    def test_flat_is_not_a_directional_hit(self):
        m=metrics(np.ones(40),np.zeros(40),np.ones(40)*.1,np.ones(40),5)
        self.assertEqual(m["hit_rate"],0)
        self.assertEqual(m["coverage"],1)
        self.assertEqual(m["nonoverlap_min_n"],8)

    def test_no_silent_holdout(self):
        with self.assertRaisesRegex(ValueError,"explicit"):
            research(pd.DataFrame())


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.store=AssetStore(Path(self.temp.name)/"test.sqlite")
    def tearDown(self):
        self.store.close(); self.temp.cleanup()

    def test_append_only_and_idempotence(self):
        self.store.put("predictions",{"x":1},"p")
        self.store.put("predictions",{"x":1},"p")
        self.assertEqual(len(self.store.list("predictions")),1)
        with self.assertRaises(ValueError): self.store.put("predictions",{"x":2},"p")
        with self.assertRaises(sqlite3.IntegrityError): self.store.db.execute("UPDATE predictions SET body='{}'")
        with self.assertRaises(sqlite3.IntegrityError): self.store.db.execute("DELETE FROM predictions")
        self.store.db.rollback()

    def test_freeze_and_real_due_outcome_idempotence(self):
        d=dataset(1600)
        # Historical synthetic data only in temporary DB, never the production ledger.
        observed_end = pd.Timestamp(d["series"]["gold"]["rows"][-15]["date"])
        early = json.loads(json.dumps(d))
        for s in early["series"].values(): s["rows"]=[r for r in s["rows"] if r["date"]<=str(observed_end.date())]
        self.store.put("datasets",early)
        publish_shadow(self.store)
        now = (observed_end+pd.Timedelta(days=1,hours=6)).to_pydatetime().replace(tzinfo=timezone.utc)
        ids=freeze(self.store,now)
        self.assertEqual(ids,freeze(self.store,now+timedelta(hours=1)))
        self.assertEqual(len(ids),4)
        h4=[p for p in self.store.list("predictions") if p["horizon"]=="H4"][0]
        self.assertIsNone(h4["details"]["score"])
        self.store.put("datasets",d)
        future=datetime.fromisoformat(d["series"]["gold"]["rows"][-1]["date"]).replace(tzinfo=timezone.utc)+timedelta(days=1)
        outcomes=evaluate_due(self.store,future)
        self.assertEqual(len(outcomes),3)
        self.assertEqual(evaluate_due(self.store,future),[])
        for o in self.store.list("outcomes"):
            self.assertGreater(o["baseline"]["date"],now.date().isoformat())

    def test_cot_missing_is_not_zero(self):
        raw=json.dumps([{"cftc_contract_market_code":"088691","report_date_as_yyyy_mm_dd":"2020-01-07T00:00:00","open_interest_all":"100","m_money_positions_long_all":None,"m_money_positions_short_all":"10"}])
        self.assertEqual(ResearchHistoryProvider.parse_cot(raw,"2026-01-01"),[])

    def test_contract_mismatch_rejected(self):
        with self.assertRaises(Exception): ResearchHistoryProvider.parse_cot('[{"cftc_contract_market_code":"OTHER"}]',"2026-01-01")

    def test_fred_missing_and_future_excluded(self):
        self.assertEqual(ResearchHistoryProvider.parse_fred("observation_date,DFII10\n2020-01-01,.\n2020-01-02,1\n2027-01-01,9\n","DFII10","2026-01-01"),[{"date":"2020-01-02","close":1.0}])


if __name__=="__main__": unittest.main()
