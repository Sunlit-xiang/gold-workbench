"""Structured economic calendar provider for premarket event risk."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Any, Mapping
from urllib.parse import quote

from digital_oracle.http import JsonHttpClient, UrllibJsonClient

from ._coerce import _coerce_int
from .base import ProviderError, ProviderParseError, SignalProvider


TRADING_ECONOMICS_CALENDAR_URL = "https://api.tradingeconomics.com/calendar/country"

_COUNTRY_CURRENCY = {
    "united states": "USD",
    "euro area": "EUR",
    "germany": "EUR",
    "united kingdom": "GBP",
    "japan": "JPY",
    "australia": "AUD",
    "canada": "CAD",
    "new zealand": "NZD",
    "switzerland": "CHF",
}


def _utc_string(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.endswith("Z") or "+" in raw[10:]:
        return raw
    return f"{raw}Z"


@dataclass(frozen=True)
class EconomicCalendarQuery:
    start_date: str = ""
    end_date: str = ""
    countries: tuple[str, ...] = ("united states",)
    min_importance: int = 2

    def normalized_dates(self) -> tuple[str, str]:
        today = date.today().isoformat()
        return self.start_date or today, self.end_date or self.start_date or today


@dataclass(frozen=True)
class EconomicEvent:
    event_id: str
    time_utc: str
    country: str
    currency: str
    name: str
    category: str
    importance: int
    time_precision: str
    previous: str | None
    forecast: str | None
    actual: str | None
    source: str
    source_url: str | None
    last_updated: str | None
    fetched_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TradingEconomicsCalendarProvider(SignalProvider):
    """Trading Economics' documented calendar API.

    A personal API key is required.  The provider intentionally has no hidden
    HTML-scraping fallback; callers can surface a clear degraded state instead.
    """

    provider_id = "trading_economics_calendar"
    display_name = "Trading Economics Economic Calendar"
    capabilities = ("economic_calendar", "event_risk")

    def __init__(
        self,
        api_key: str | None = None,
        http_client: JsonHttpClient | None = None,
    ) -> None:
        self.api_key = (api_key or os.environ.get("TRADING_ECONOMICS_API_KEY", "")).strip()
        self.http_client = http_client or UrllibJsonClient()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def list_events(self, query: EconomicCalendarQuery | None = None) -> list[EconomicEvent]:
        if not self.configured:
            raise ProviderError(
                "economic calendar is not configured; set TRADING_ECONOMICS_API_KEY"
            )
        query = query or EconomicCalendarQuery()
        start_date, end_date = query.normalized_dates()
        countries = quote(",".join(query.countries), safe=",")
        payload = self.http_client.get_json(
            f"{TRADING_ECONOMICS_CALENDAR_URL}/{countries}/{start_date}/{end_date}",
            params={"c": self.api_key, "f": "json"},
        )
        if not isinstance(payload, list):
            raise ProviderParseError("expected Trading Economics calendar response to be a list")

        fetched_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        events: list[EconomicEvent] = []
        for row in payload:
            if not isinstance(row, Mapping):
                continue
            importance = _coerce_int(row.get("Importance")) or 0
            if importance < max(1, query.min_importance):
                continue
            country = str(row.get("Country", ""))
            currency = str(row.get("Currency", "")).strip()
            if not currency:
                currency = _COUNTRY_CURRENCY.get(country.lower(), "")
            events.append(
                EconomicEvent(
                    event_id=str(row.get("CalendarId") or row.get("CalendarID") or ""),
                    time_utc=_utc_string(row.get("Date")),
                    country=country,
                    currency=currency,
                    name=str(row.get("Event", "")),
                    category=str(row.get("Category", "")),
                    importance=importance,
                    time_precision=self._time_precision(row.get("DateSpan")),
                    previous=str(row.get("Previous")) if row.get("Previous") not in (None, "") else None,
                    forecast=str(row.get("Forecast")) if row.get("Forecast") not in (None, "") else None,
                    actual=str(row.get("Actual")) if row.get("Actual") not in (None, "") else None,
                    source=str(row.get("Source", "Trading Economics")),
                    source_url=(
                        str(row.get("SourceURL")) if row.get("SourceURL") not in (None, "") else None
                    ),
                    last_updated=(
                        _utc_string(row.get("LastUpdate"))
                        if row.get("LastUpdate") not in (None, "")
                        else None
                    ),
                    fetched_at=fetched_at,
                )
            )
        return sorted(events, key=lambda event: event.time_utc)

    @staticmethod
    def _time_precision(value: object) -> str:
        date_span = _coerce_int(value)
        if date_span == 0:
            return "exact"
        if date_span is not None and date_span > 0:
            return "estimated"
        return "unknown"
