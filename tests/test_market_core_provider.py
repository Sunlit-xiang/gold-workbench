from __future__ import annotations

import time
import unittest
from typing import Any, Mapping

from digital_oracle.providers.base import ProviderError
from digital_oracle.providers.market_core import MarketSnapshotQuery, YahooMarketCoreProvider


class FakeClient:
    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.calls: list[tuple[str, Mapping[str, object] | None]] = []

    def get_json(self, url: str, *, params: Mapping[str, object] | None = None) -> Any:
        self.calls.append((url, params))
        return self.payload


class YahooMarketCoreProviderTests(unittest.TestCase):
    def test_preserves_market_time_and_computes_premarket_changes(self) -> None:
        now = int(time.time())
        payload = {
            "chart": {
                "error": None,
                "result": [
                    {
                        "meta": {
                            "regularMarketPrice": 102.0,
                            "chartPreviousClose": 100.0,
                            "regularMarketTime": now,
                            "exchangeTimezoneName": "UTC",
                            "exchangeName": "TEST",
                            "instrumentType": "FUTURE",
                            "currency": "USD",
                        },
                        "timestamp": [now - 3600, now],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [101.0, 101.5],
                                    "close": [101.5, 102.0],
                                }
                            ]
                        },
                    }
                ],
            }
        }
        client = FakeClient(payload)
        snapshot = YahooMarketCoreProvider(http_client=client).get_snapshot(
            MarketSnapshotQuery("es", "ES", "ES=F", max_age_seconds=30)
        )

        self.assertEqual(snapshot.current, 102.0)
        self.assertEqual(snapshot.previous_close, 100.0)
        self.assertEqual(snapshot.session_open, 101.0)
        self.assertAlmostEqual(snapshot.since_previous_close_pct or 0.0, 2.0)
        self.assertAlmostEqual(snapshot.today_change_pct or 0.0, 0.990099, places=5)
        self.assertEqual(snapshot.freshness, "fresh")
        self.assertTrue(snapshot.market_time and snapshot.market_time.endswith("Z"))
        self.assertIn("ES%3DF", client.calls[0][0])

    def test_chart_error_is_not_silently_accepted(self) -> None:
        client = FakeClient({"chart": {"error": {"code": "Not Found"}, "result": None}})
        with self.assertRaises(ProviderError):
            YahooMarketCoreProvider(http_client=client).get_snapshot(
                MarketSnapshotQuery("x", "X", "NOPE")
            )


if __name__ == "__main__":
    unittest.main()
