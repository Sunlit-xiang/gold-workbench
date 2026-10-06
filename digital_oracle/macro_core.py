"""Typed macro contracts and deterministic evidence calculus; not a direction oracle."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import math
import statistics
from typing import Literal

from .asset_store import digest

VERSION = "MEP-1.0"
ASSETS = {
    "gold": {"name": "Gold · GC Proxy", "instrument": "GC=F", "countries": ["US"], "kind": "commodity", "price": "gold"},
    "audnzd": {"name": "AUDNZD", "instrument": "ECB reference cross · NZD per AUD", "countries": ["AU", "NZ"], "kind": "relative_macro", "price": "audnzd"},
    "eurusd": {"name": "EURUSD", "instrument": "ECB reference · USD per EUR", "countries": ["EA", "US"], "kind": "relative_macro", "price": "eurusd"},
    "usdjpy": {"name": "USDJPY", "instrument": "ECB reference cross · JPY per USD", "countries": ["US", "JP"], "kind": "relative_macro", "price": "usdjpy"},
}
COUNTRIES = {
    "US": {"central_bank": "Fed", "statistics": ["BLS", "BEA"], "policy": "https://www.federalreserve.gov/monetarypolicy.htm", "drivers": ["policy path", "inflation", "labour", "growth", "Treasury curve"]},
    "AU": {"central_bank": "RBA", "statistics": ["ABS"], "policy": "https://www.rba.gov.au/monetary-policy/", "drivers": ["policy path", "inflation", "labour", "housing/credit", "iron ore", "China", "terms of trade"]},
    "NZ": {"central_bank": "RBNZ", "statistics": ["Stats NZ"], "policy": "https://www.rbnz.govt.nz/monetary-policy", "drivers": ["OCR path", "inflation", "labour", "housing/credit", "dairy", "terms of trade"]},
    "EA": {"central_bank": "ECB", "statistics": ["Eurostat"], "policy": "https://www.ecb.europa.eu/mopo/html/index.en.html", "drivers": ["policy path", "inflation", "growth", "energy", "credit"]},
    "JP": {"central_bank": "BoJ", "statistics": ["Statistics Bureau"], "policy": "https://www.boj.or.jp/en/mopo/", "drivers": ["policy path", "wages", "inflation", "carry", "intervention"]},
}


def instant(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("explicit timezone required")
    return dt.astimezone(timezone.utc)


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("finite numeric observation required")
    return float(value)


@dataclass(frozen=True)
class Evidence:
    asset: str
    country: list[str]
    topic: str
    family: str
    layer: Literal["structural", "tactical", "event", "risk"]
    source: str
    source_quality: int
    url: str
    ingestion_time: str
    available_at: str
    observation_date: str | None = None
    publication_time: str | None = None
    event_time: str | None = None
    actual: float | None = None
    forecast: float | None = None
    previous: float | None = None
    revision: float | None = None
    units: str = ""
    horizon: str = "context only"
    status: str = "MISSING"
    pit: str = "first_seen only; latest vintage"
    raw_payload_id: str | None = None
    transformation: dict = field(default_factory=dict)
    interpretation: str = ""
    stance: str = "unknown"
    validation: str = "context_only"
    independence_cluster: str = ""

    def __post_init__(self):
        if self.asset not in ASSETS or self.source_quality not in (1, 2, 3, 4):
            raise ValueError("invalid asset/source quality")
        if instant(self.available_at) < instant(self.ingestion_time):
            raise ValueError("availability must include first seen")
        if self.publication_time and instant(self.available_at) < instant(self.publication_time):
            raise ValueError("availability cannot precede publication")
        for number in (self.actual, self.forecast, self.previous, self.revision):
            if number is not None:
                finite(number)

    def record(self):
        row = asdict(self)
        return {"id": digest(row), **row}


def surprise(actual, consensus, *, units, consensus_units, consensus_available_at,
             event_time, prior_surprises=()):
    if actual is None or consensus is None:
        return {"status": "MISSING", "reason": "actual or frozen pre-release consensus absent"}
    if not units or units != consensus_units:
        return {"status": "UNKNOWN", "reason": "units mismatch"}
    if not consensus_available_at or instant(consensus_available_at) >= instant(event_time):
        return {"status": "UNKNOWN", "reason": "consensus was not frozen before release"}
    delta = finite(actual) - finite(consensus)
    values = [finite(x) for x in prior_surprises]
    sd = statistics.stdev(values) if len(values) >= 20 else None
    return {"status": "available", "raw": delta, "units": units,
            "z": delta / sd if sd and sd > 0 else None, "prior_n": len(values),
            "formula": "actual - frozen consensus; z = surprise / prior-only sample std (n>=20)",
            "direction": "not inferred from surprise alone"}


def event_reaction(event_time, quotes, minutes, now, max_gap_seconds=60):
    """True timestamped observations only. No daily bar can impersonate a 5m quote."""
    if finite(minutes) <= 0 or finite(max_gap_seconds) < 0:
        raise ValueError("positive window and nonnegative boundary gap required")
    release, at = instant(event_time), instant(now)
    end = release + timedelta(minutes=minutes)
    if at < end:
        return {"status": "PENDING"}
    eligible = [q for q in quotes if instant(q["time"]) <= instant(q["available_at"]) <= at and finite(q["value"]) > 0
                and 0 < q.get("granularity_seconds", 86400) <= min(60, minutes * 60)]
    before = [q for q in eligible if instant(q["time"]) < release and instant(q["available_at"]) < release]
    after = [q for q in eligible if end <= instant(q["time"]) <= at]
    if not before or not after:
        return {"status": "MISSING", "reason": "timestamped pre/post quotes unavailable"}
    pre, post = max(before, key=lambda q: instant(q["time"])), min(after, key=lambda q: instant(q["time"]))
    if (release - instant(pre["time"])).total_seconds() > max_gap_seconds or (instant(post["time"]) - end).total_seconds() > max_gap_seconds:
        return {"status": "MISSING", "reason": "event window boundary gap"}
    if pre.get("instrument") != post.get("instrument") or not pre.get("instrument"):
        return {"status": "UNKNOWN", "reason": "instrument mismatch"}
    return {"status": "available", "minutes": minutes, "pre": pre, "post": post,
            "log_return_pct": 100 * math.log(post["value"] / pre["value"]),
            "interpretation": "observed reaction, not identified causality"}


def change(rows, lag=5, kind="return"):
    if len(rows) <= lag:
        return None
    a, b = rows[-1], rows[-1 - lag]
    if kind == "bp":
        delta, unit = (a["close"] - b["close"]) * 100, "bp"
        formula = "100 * (current_percent_yield - previous_percent_yield)"
    elif kind == "pp":
        delta, unit = (a["close"] - b["close"]) * 100, "pp"
        formula = "100 * (current_ratio - previous_ratio)"
    else:
        if min(a["close"], b["close"]) <= 0:
            return None
        delta, unit = 100 * math.log(a["close"] / b["close"]), "% log return"
        formula = "100 * ln(current / previous)"
    moves = []
    # Prior-only distribution: omit today's move; no normalization look-ahead.
    for i in range(max(lag, len(rows) - 253), len(rows) - 1):
        x, y = rows[i]["close"], rows[i - lag]["close"]
        if kind in ("bp", "pp"):
            moves.append(100 * (x - y))
        elif min(x, y) > 0:
            moves.append(100 * math.log(x / y))
    sd = statistics.stdev(moves) if len(moves) >= 60 else None
    mean = statistics.mean(moves) if moves else None
    return {"value": delta, "unit": unit, "lag": lag, "from_date": b["date"], "to_date": a["date"],
            "formula": formula, "z": (delta - mean) / sd if sd and sd > 0 else None,
            "z_mean": mean, "z_std": sd, "normalization_n": len(moves),
            "normalization": "max 252 prior native-observation moves; z only n>=60"}


def memory_relevance(available_at, now, layer):
    days = max(0, (instant(now) - instant(available_at)).total_seconds() / 86400)
    half_life = {"event": 3, "tactical": 10, "structural": 180, "risk": 3}[layer]
    return math.exp(-math.log(2) * days / half_life)


def unique_clusters(evidence):
    return len({e["independence_cluster"] for e in evidence if e.get("status") == "available"})
