from __future__ import annotations

import unittest
from typing import Any, Mapping

from digital_oracle.providers.base import ProviderError
from digital_oracle.providers.economic_calendar import (
    EconomicCalendarQuery,
    TradingEconomicsCalendarProvider,
)


class FakeClient:
    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.calls: list[tuple[str, Mapping[str, object] | None]] = []

    def get_json(self, url: str, *, params: Mapping[str, object] | None = None) -> Any:
        self.calls.append((url, params))
        return self.payload


class TradingEconomicsCalendarProviderTests(unittest.TestCase):
    def test_parses_fields_filters_importance_and_sorts(self) -> None:
        payload = [
            {
                "CalendarId": "2",
                "Date": "2026-08-15T14:00:00",
                "Country": "United States",
                "Event": "Consumer Sentiment",
                "Category": "Consumer Confidence",
                "Importance": 2,
                "DateSpan": 1,
                "Actual": "",
                "Forecast": "58.0",
                "Previous": "57.5",
                "Source": "University of Michigan",
                "SourceURL": "https://example.com/source",
                "LastUpdate": "2026-08-15T10:00:00",
                "Currency": "",
            },
            {
                "CalendarId": "1",
                "Date": "2026-08-15T12:30:00",
                "Country": "United States",
                "Event": "CPI YoY",
                "Category": "Inflation Rate",
                "Importance": 3,
                "DateSpan": 0,
                "Actual": "3.0%",
                "Forecast": "2.9%",
                "Previous": "2.8%",
                "Source": "BLS",
            },
            {"CalendarId": "0", "Importance": 1, "Event": "Low impact"},
        ]
        client = FakeClient(payload)
        provider = TradingEconomicsCalendarProvider(api_key="test-key", http_client=client)
        events = provider.list_events(
            EconomicCalendarQuery(
                start_date="2026-08-15",
                end_date="2026-08-15",
                countries=("united states",),
                min_importance=2,
            )
        )

        self.assertEqual([event.event_id for event in events], ["1", "2"])
        self.assertEqual(events[0].currency, "USD")
        self.assertEqual(events[0].actual, "3.0%")
        self.assertEqual(events[0].time_utc, "2026-08-15T12:30:00Z")
        self.assertEqual(events[0].time_precision, "exact")
        self.assertEqual(events[1].time_precision, "estimated")
        self.assertIn("2026-08-15/2026-08-15", client.calls[0][0])
        self.assertEqual(client.calls[0][1]["c"], "test-key")

    def test_missing_key_is_an_explicit_configuration_error(self) -> None:
        provider = TradingEconomicsCalendarProvider(api_key="", http_client=FakeClient([]))
        with self.assertRaises(ProviderError):
            provider.list_events()


if __name__ == "__main__":
    unittest.main()
