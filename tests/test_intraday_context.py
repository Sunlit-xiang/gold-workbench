from __future__ import annotations

import unittest
from datetime import date

from digital_oracle.intraday import IntradayContextQuery, IntradayMarketContextService
from digital_oracle.providers.economic_calendar import EconomicEvent
from digital_oracle.providers.market_core import MarketSnapshot
from digital_oracle.providers.treasury import YieldCurveSnapshot, YieldPoint


def _snapshot(key: str, label: str, symbol: str) -> MarketSnapshot:
    return MarketSnapshot(
        key=key,
        label=label,
        symbol=symbol,
        current=101.0,
        unit="price",
        previous_close=100.0,
        session_open=100.5,
        since_previous_close=1.0,
        since_previous_close_pct=1.0,
        today_change=0.5,
        today_change_pct=0.5,
        market_time="2026-08-15T08:00:00Z",
        fetched_at="2026-08-15T08:00:01Z",
        age_seconds=1.0,
        freshness="fresh",
        source="fake",
        source_url="https://example.com",
        frequency="1h",
    )


class FakeMarketProvider:
    def get_snapshot(self, query):
        return _snapshot(query.key, query.label, query.symbol)


class FakeTreasuryProvider:
    def list_yield_curve(self, query):
        kind = query.curve_kind
        today = date.today().isoformat()
        return [
            YieldCurveSnapshot(kind, today, (YieldPoint("2Y", 4.1), YieldPoint("10Y", 4.5))),
            YieldCurveSnapshot(kind, "2026-08-14", (YieldPoint("2Y", 4.0), YieldPoint("10Y", 4.4))),
        ]


class FakeCalendarProvider:
    configured = True

    def list_events(self, query):
        return [
            EconomicEvent(
                event_id="1",
                time_utc="2026-08-15T12:30:00Z",
                country="United States",
                currency="USD",
                name="CPI",
                category="Inflation",
                importance=3,
                time_precision="exact",
                previous="2.8%",
                forecast="2.9%",
                actual=None,
                source="BLS",
                source_url="https://bls.gov",
                last_updated=None,
                fetched_at="2026-08-15T08:00:00Z",
            )
        ]


class IntradayMarketContextServiceTests(unittest.TestCase):
    def test_gold_bundle_contains_core_target_slow_rate_and_event(self) -> None:
        service = IntradayMarketContextService(
            market_provider=FakeMarketProvider(),
            treasury_provider=FakeTreasuryProvider(),
            calendar_provider=FakeCalendarProvider(),
        )
        bundle = service.build(IntradayContextQuery(target="gold", session="london"))

        self.assertEqual(bundle.target, "gold")
        self.assertEqual(bundle.session, "london")
        self.assertEqual(bundle.session_timezone, "Europe/London")
        self.assertEqual(set(bundle.core), {"dxy", "es", "nq", "vix", "us2y", "us10y"})
        self.assertIn("gold", bundle.target_specific)
        self.assertIn("us10y_real", bundle.target_specific)
        self.assertEqual(bundle.events[0]["name"], "CPI")
        self.assertTrue(bundle.data_quality["complete"])
        self.assertAlmostEqual(bundle.core["us2y"]["metadata"]["change_bps"], 10.0)

    def test_rejects_unknown_target(self) -> None:
        service = IntradayMarketContextService(
            market_provider=FakeMarketProvider(),
            treasury_provider=FakeTreasuryProvider(),
            calendar_provider=FakeCalendarProvider(),
        )
        with self.assertRaises(ValueError):
            service.build(IntradayContextQuery(target="oil"))


if __name__ == "__main__":
    unittest.main()
