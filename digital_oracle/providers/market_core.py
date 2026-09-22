"""Premarket snapshots for the shared cross-market core.

This module intentionally does not perform technical analysis.  It turns a
small amount of intraday quote history into a timestamped snapshot containing
the current value, previous close, current-session open and freshness status.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from digital_oracle.http import JsonHttpClient, UrllibJsonClient

from ._coerce import _coerce_float, _coerce_int
from .base import ProviderError, ProviderParseError, SignalProvider


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"


def _iso_utc(timestamp: int | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat().replace("+00:00", "Z")


def _pct_change(current: float | None, reference: float | None) -> float | None:
    if current is None or reference in (None, 0):
        return None
    return (current / reference - 1.0) * 100.0


def _freshness(age_seconds: float | None, max_age_seconds: int) -> str:
    if age_seconds is None:
        return "unknown"
    if age_seconds <= max_age_seconds:
        return "fresh"
    if age_seconds <= max_age_seconds * 4:
        return "delayed"
    return "stale"


@dataclass(frozen=True)
class MarketSnapshotQuery:
    key: str
    label: str
    symbol: str
    unit: str = "price"
    chart_range: str = "5d"
    interval: str = "1h"
    include_pre_post: bool = True
    max_age_seconds: int = 900


@dataclass(frozen=True)
class MarketSnapshot:
    key: str
    label: str
    symbol: str
    current: float | None
    unit: str
    previous_close: float | None
    session_open: float | None
    since_previous_close: float | None
    since_previous_close_pct: float | None
    today_change: float | None
    today_change_pct: float | None
    market_time: str | None
    fetched_at: str
    age_seconds: float | None
    freshness: str
    source: str
    source_url: str
    frequency: str
    exchange_timezone: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class YahooMarketCoreProvider(SignalProvider):
    """Timestamp-preserving Yahoo chart snapshots for the premarket dashboard."""

    provider_id = "yahoo_market_core"
    display_name = "Yahoo Finance Market Core"
    capabilities = ("premarket_snapshot", "freshness")

    def __init__(self, http_client: JsonHttpClient | None = None) -> None:
        self.http_client = http_client or UrllibJsonClient()

    def get_snapshot(self, query: MarketSnapshotQuery) -> MarketSnapshot:
        symbol = query.symbol.strip()
        url = f"{YAHOO_CHART_URL}/{quote(symbol, safe='')}"
        payload = self.http_client.get_json(
            url,
            params={
                "range": query.chart_range,
                "interval": query.interval,
                "includePrePost": query.include_pre_post,
                "events": "div,splits",
            },
        )
        result = self._unwrap_result(payload)
        meta = result.get("meta")
        if not isinstance(meta, Mapping):
            raise ProviderParseError("expected Yahoo chart result.meta to be an object")

        timestamps = result.get("timestamp")
        if not isinstance(timestamps, list):
            timestamps = []
        quote_rows = self._quote_rows(result)

        current = _coerce_float(meta.get("regularMarketPrice"))
        last_timestamp, last_close = self._last_close(timestamps, quote_rows)
        if current is None:
            current = last_close

        market_timestamp = _coerce_int(meta.get("regularMarketTime")) or last_timestamp
        previous_close = _coerce_float(meta.get("chartPreviousClose"))
        if previous_close is None:
            previous_close = _coerce_float(meta.get("previousClose"))

        exchange_timezone = (
            str(meta.get("exchangeTimezoneName"))
            if meta.get("exchangeTimezoneName") is not None
            else None
        )
        session_open = self._session_open(
            timestamps,
            quote_rows,
            market_timestamp=market_timestamp,
            exchange_timezone=exchange_timezone,
        )

        fetched = datetime.now(timezone.utc)
        age_seconds = None
        if market_timestamp is not None:
            age_seconds = max(0.0, fetched.timestamp() - market_timestamp)
        since_previous = (
            current - previous_close
            if current is not None and previous_close is not None
            else None
        )
        today_change = (
            current - session_open if current is not None and session_open is not None else None
        )

        return MarketSnapshot(
            key=query.key,
            label=query.label,
            symbol=symbol,
            current=current,
            unit=query.unit,
            previous_close=previous_close,
            session_open=session_open,
            since_previous_close=since_previous,
            since_previous_close_pct=_pct_change(current, previous_close),
            today_change=today_change,
            today_change_pct=_pct_change(current, session_open),
            market_time=_iso_utc(market_timestamp),
            fetched_at=fetched.isoformat().replace("+00:00", "Z"),
            age_seconds=round(age_seconds, 3) if age_seconds is not None else None,
            freshness=_freshness(age_seconds, query.max_age_seconds),
            source="Yahoo Finance chart API",
            source_url=url,
            frequency=query.interval,
            exchange_timezone=exchange_timezone,
            metadata={
                "exchange": meta.get("exchangeName"),
                "instrument_type": meta.get("instrumentType"),
                "currency": meta.get("currency"),
                "market_state": meta.get("marketState"),
            },
        )

    @staticmethod
    def _unwrap_result(payload: Any) -> Mapping[str, Any]:
        if not isinstance(payload, Mapping):
            raise ProviderParseError("expected Yahoo chart payload to be an object")
        chart = payload.get("chart")
        if not isinstance(chart, Mapping):
            raise ProviderParseError("expected Yahoo chart payload.chart to be an object")
        error = chart.get("error")
        if error:
            raise ProviderError(f"Yahoo chart returned an error: {error}")
        results = chart.get("result")
        if not isinstance(results, list) or not results or not isinstance(results[0], Mapping):
            raise ProviderError("Yahoo chart returned no result")
        return results[0]

    @staticmethod
    def _quote_rows(result: Mapping[str, Any]) -> Mapping[str, Any]:
        indicators = result.get("indicators")
        if not isinstance(indicators, Mapping):
            return {}
        quotes = indicators.get("quote")
        if not isinstance(quotes, list) or not quotes or not isinstance(quotes[0], Mapping):
            return {}
        return quotes[0]

    @staticmethod
    def _last_close(
        timestamps: list[Any], quote_rows: Mapping[str, Any]
    ) -> tuple[int | None, float | None]:
        closes = quote_rows.get("close")
        if not isinstance(closes, list):
            return None, None
        for index in range(min(len(timestamps), len(closes)) - 1, -1, -1):
            close = _coerce_float(closes[index])
            timestamp = _coerce_int(timestamps[index])
            if close is not None and timestamp is not None:
                return timestamp, close
        return None, None

    @staticmethod
    def _session_open(
        timestamps: list[Any],
        quote_rows: Mapping[str, Any],
        *,
        market_timestamp: int | None,
        exchange_timezone: str | None,
    ) -> float | None:
        opens = quote_rows.get("open")
        if not isinstance(opens, list) or market_timestamp is None:
            return None
        try:
            tz = ZoneInfo(exchange_timezone) if exchange_timezone else timezone.utc
        except ZoneInfoNotFoundError:
            tz = timezone.utc
        market_date = datetime.fromtimestamp(market_timestamp, tz).date()
        for timestamp_raw, open_raw in zip(timestamps, opens):
            timestamp = _coerce_int(timestamp_raw)
            open_value = _coerce_float(open_raw)
            if timestamp is None or open_value is None:
                continue
            if datetime.fromtimestamp(timestamp, tz).date() == market_date:
                return open_value
        return None
