"""Explicit research-history adapter using existing HTTP/Provider interfaces.

Latest-vintage downloads are NOT certified point-in-time history.
Raw upstream responses are archived before normalization.
"""
from __future__ import annotations

import csv
import io
import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

from digital_oracle.http import UrllibJsonClient
from digital_oracle.asset_store import utcnow
from .base import SignalProvider, ProviderParseError

SOURCES = {
    "gold": ("yahoo", "GC=F", "USD/oz", "GC continuous proxy; roll methodology unaudited"),
    "dxy": ("yahoo", "DX-Y.NYB", "index", "ICE fixed basket USD proxy"),
    "spx": ("yahoo", "^GSPC", "index", "US equity cash index"),
    "vix": ("yahoo", "^VIX", "volatility points", "cash volatility index"),
    "gld": ("yahoo", "GLD", "USD/share", "ETF cross-check, not spot"),
    "silver": ("yahoo", "SI=F", "USD/oz", "continuous futures context"),
    "brent": ("yahoo", "BZ=F", "USD/barrel", "continuous futures context"),
    "real": ("fred", "DFII10", "percent", "10Y TIPS real constant maturity; latest vintage"),
    "us2": ("fred", "DGS2", "percent", "2Y nominal; latest vintage"),
    "us10": ("fred", "DGS10", "percent", "10Y nominal; latest vintage"),
    "bei": ("fred", "T10YIE", "percent", "10Y breakeven; latest vintage"),
    "cot": ("cftc", "088691", "contracts", "Disaggregated futures only Managed Money COMEX Gold"),
}


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


class ResearchHistoryProvider(SignalProvider):
    provider_id = "research_history"
    display_name = "Archived research history (Yahoo / FRED / CFTC)"
    capabilities = ("daily_history", "weekly_positioning", "raw_lineage")

    def __init__(self, http_client=None):
        self.http_client = http_client or UrllibJsonClient(timeout_seconds=25, retry_attempts=2)

    def fetch(self, key, today=None):
        today = today or datetime.now(timezone.utc).date().isoformat()
        kind, symbol, unit, note = SOURCES[key]
        if kind == "yahoo":
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe='')}"
            params = {"period1": 1136073600, "period2": int(datetime.now(timezone.utc).timestamp()), "interval": "1d"}
        elif kind == "fred":
            url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
            params = {"id": symbol, "cosd": "2006-01-01"}
        else:
            url = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
            params = {"cftc_contract_market_code": symbol, "$limit": 5000, "$order": "report_date_as_yyyy_mm_dd ASC"}
        raw = self.http_client.get_text(url, params=params)
        fetched = utcnow()
        if kind == "yahoo":
            rows = self.parse_yahoo(raw, today)
        elif kind == "fred":
            rows = self.parse_fred(raw, symbol, today)
        else:
            rows = self.parse_cot(raw, today)
        if not rows:
            raise ProviderParseError(f"{key}: no valid completed observations")
        return {"series": key, "source": kind, "instrument": symbol, "unit": unit,
                "url": url, "params": params, "fetched_at": fetched, "first_seen_at": fetched,
                "pit_status": "reconstructed_latest_vintage", "note": note, "raw": raw, "rows": rows}

    @staticmethod
    def parse_yahoo(raw, today):
        payload = json.loads(raw)
        results = payload.get("chart", {}).get("result")
        if not results:
            raise ProviderParseError("Yahoo chart missing result")
        chart = results[0]
        tz = ZoneInfo(chart["meta"].get("exchangeTimezoneName", "America/New_York"))
        values = chart["indicators"]["quote"][0]
        rows = []
        for i, timestamp in enumerate(chart.get("timestamp", [])):
            day = datetime.fromtimestamp(timestamp, tz).date().isoformat()
            if day >= today:
                continue  # Never use today's possibly incomplete daily candle.
            row = {"date": day, "source_timestamp": timestamp}
            for field in ("open", "high", "low", "close", "volume"):
                row[field] = number(values.get(field, [None] * len(chart["timestamp"]))[i])
            if row["close"] is not None and row["close"] > 0:
                if row["high"] is not None and row["low"] is not None and row["high"] < row["low"]:
                    row["quality_flag"] = "inverted_ohlc_close_retained_range_unusable"
                    row["high"], row["low"] = None, None
                rows.append(row)
        return sorted({r["date"]: r for r in rows}.values(), key=lambda r: r["date"])

    @staticmethod
    def parse_fred(raw, symbol, today):
        if "observation_date" not in raw[:100]:
            raise ProviderParseError("FRED CSV schema mismatch")
        rows = []
        for row in csv.DictReader(io.StringIO(raw)):
            value = number(row.get(symbol))
            day = row.get("observation_date", "")
            if value is not None and "2006-01-01" <= day < today:
                rows.append({"date": day, "close": value})
        return sorted(rows, key=lambda r: r["date"])

    @staticmethod
    def parse_cot(raw, today):
        rows = []
        for row in json.loads(raw):
            if row.get("cftc_contract_market_code") != "088691":
                raise ProviderParseError("COT contract identity mismatch")
            day = row["report_date_as_yyyy_mm_dd"][:10]
            oi, long, short = (number(row.get(k)) for k in ("open_interest_all", "m_money_positions_long_all", "m_money_positions_short_all"))
            if day < today and oi and long is not None and short is not None:
                rows.append({"date": day, "close": (long-short)/oi, "long": long, "short": short, "oi": oi})
        return sorted({r["date"]: r for r in rows}.values(), key=lambda r: r["date"])


def collect_dataset(store, provider=None):
    provider = provider or ResearchHistoryProvider()
    series, errors = {}, {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(provider.fetch, key): key for key in SOURCES}
        for future in as_completed(jobs):
            key = jobs[future]
            try:
                data = future.result()
                raw = data.pop("raw")
                payload_id = store.put("payloads", {"series": key, "url": data["url"], "params": data["params"], "fetched_at": data["fetched_at"], "raw": raw})
                data["payload_id"] = payload_id
                series[key] = data
            except Exception as exc:
                errors[key] = f"{type(exc).__name__}: {str(exc)[:220]}"
    dataset = {"asset": "gold", "instrument": "GC=F", "created_at": utcnow(), "series": series, "errors": errors}
    key = store.put("datasets", dataset)
    store.event("collection", dataset_id=key, successes=list(series), failures=errors)
    return {"id": key, **dataset}
