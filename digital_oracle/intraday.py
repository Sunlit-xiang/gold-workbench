"""Premarket Market Context data orchestration.

The module fetches and normalizes facts.  It deliberately does not classify
the market with fixed trading rules; Codex performs signal routing and
cross-market interpretation under the intraday skill instructions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from .concurrent import gather
from .providers.deribit import DeribitFuturesCurveQuery, DeribitProvider
from .providers.economic_calendar import (
    EconomicCalendarQuery,
    TradingEconomicsCalendarProvider,
)
from .providers.market_core import MarketSnapshot, MarketSnapshotQuery, YahooMarketCoreProvider
from .providers.treasury import USTreasuryProvider, YieldCurveQuery, YieldCurveSnapshot


CORE_MARKETS: dict[str, MarketSnapshotQuery] = {
    "dxy": MarketSnapshotQuery("dxy", "美元指数 DXY", "DX-Y.NYB", max_age_seconds=1800),
    "es": MarketSnapshotQuery("es", "标普500期货 ES", "ES=F", max_age_seconds=1800),
    "nq": MarketSnapshotQuery("nq", "纳斯达克100期货 NQ", "NQ=F", max_age_seconds=1800),
    "vix": MarketSnapshotQuery("vix", "VIX 波动率", "^VIX", max_age_seconds=3600),
}

TARGET_MARKETS: dict[str, tuple[MarketSnapshotQuery, ...]] = {
    "global": (),
    "equities": (),
    "gold": (
        MarketSnapshotQuery("gold", "黄金 Gold", "GC=F", unit="USD", max_age_seconds=1800),
    ),
    "eurusd": (
        MarketSnapshotQuery("eurusd", "欧元美元 EURUSD", "EURUSD=X", max_age_seconds=1800),
    ),
    "gbpusd": (
        MarketSnapshotQuery("gbpusd", "英镑美元 GBPUSD", "GBPUSD=X", max_age_seconds=1800),
    ),
    "usdjpy": (
        MarketSnapshotQuery("usdjpy", "美元日元 USDJPY", "JPY=X", max_age_seconds=1800),
    ),
    "audusd": (
        MarketSnapshotQuery("audusd", "澳元美元 AUDUSD", "AUDUSD=X", max_age_seconds=1800),
    ),
    "btc": (
        MarketSnapshotQuery("btc", "比特币 BTC", "BTC-USD", unit="USD", max_age_seconds=900),
    ),
    "eth": (
        MarketSnapshotQuery("eth", "以太坊 ETH", "ETH-USD", unit="USD", max_age_seconds=900),
    ),
    "crypto": (
        MarketSnapshotQuery("btc", "比特币 BTC", "BTC-USD", unit="USD", max_age_seconds=900),
        MarketSnapshotQuery("eth", "以太坊 ETH", "ETH-USD", unit="USD", max_age_seconds=900),
    ),
}

TARGET_COUNTRIES: dict[str, tuple[str, ...]] = {
    "global": ("united states", "euro area", "united kingdom", "japan", "australia"),
    "equities": ("united states",),
    "gold": ("united states",),
    "eurusd": ("united states", "euro area", "germany"),
    "gbpusd": ("united states", "united kingdom"),
    "usdjpy": ("united states", "japan"),
    "audusd": ("united states", "australia"),
    "btc": ("united states",),
    "eth": ("united states",),
    "crypto": ("united states",),
}

SESSION_TIMEZONES = {
    "asia": "Asia/Shanghai",
    "london": "Europe/London",
    "new_york": "America/New_York",
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_curve_date(raw: str) -> date | None:
    for pattern in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, pattern).date()
        except ValueError:
            continue
    return None


def _error_text(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


@dataclass(frozen=True)
class IntradayContextQuery:
    target: str = "global"
    session: str = "auto"
    calendar_date: str = ""


@dataclass
class PremarketDataBundle:
    schema_version: str
    generated_at: str
    target: str
    session: str
    session_date: str
    session_timezone: str
    core: dict[str, dict[str, Any]]
    target_specific: dict[str, dict[str, Any]]
    events: list[dict[str, Any]]
    derivatives: dict[str, Any]
    errors: dict[str, str]
    data_quality: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IntradayMarketContextService:
    """Build the evidence bundle consumed by Codex and the dashboard."""

    def __init__(
        self,
        *,
        market_provider: YahooMarketCoreProvider | None = None,
        treasury_provider: USTreasuryProvider | None = None,
        calendar_provider: TradingEconomicsCalendarProvider | None = None,
        deribit_provider: DeribitProvider | None = None,
    ) -> None:
        self.market_provider = market_provider or YahooMarketCoreProvider()
        self.treasury_provider = treasury_provider or USTreasuryProvider()
        self.calendar_provider = calendar_provider or TradingEconomicsCalendarProvider()
        self.deribit_provider = deribit_provider or DeribitProvider()

    def build(self, query: IntradayContextQuery | None = None) -> PremarketDataBundle:
        query = query or IntradayContextQuery()
        target = query.target.strip().lower()
        if target not in TARGET_MARKETS:
            raise ValueError(f"unsupported intraday target: {query.target!r}")

        generated_at = datetime.now(timezone.utc)
        session = self._session(query.session, generated_at)
        session_timezone = SESSION_TIMEZONES[session]
        session_date = generated_at.astimezone(ZoneInfo(session_timezone)).date().isoformat()

        market_queries = dict(CORE_MARKETS)
        for target_query in TARGET_MARKETS[target]:
            market_queries[target_query.key] = target_query

        tasks: dict[str, Any] = {
            f"market:{key}": (lambda q=snapshot_query: self.market_provider.get_snapshot(q))
            for key, snapshot_query in market_queries.items()
        }
        tasks["rates:nominal"] = lambda: self.treasury_provider.list_yield_curve(
            YieldCurveQuery(curve_kind="nominal")
        )
        if target == "gold":
            tasks["rates:real"] = lambda: self.treasury_provider.list_yield_curve(
                YieldCurveQuery(curve_kind="real")
            )

        calendar_day = query.calendar_date or session_date
        tasks["events"] = lambda: self.calendar_provider.list_events(
            EconomicCalendarQuery(
                start_date=calendar_day,
                end_date=calendar_day,
                countries=TARGET_COUNTRIES[target],
                min_importance=2,
            )
        )
        if target in {"btc", "eth", "crypto"}:
            currencies = ("BTC", "ETH") if target == "crypto" else (target.upper(),)
            for currency in currencies:
                tasks[f"deribit:{currency.lower()}"] = (
                    lambda c=currency: self.deribit_provider.get_futures_term_structure(
                        DeribitFuturesCurveQuery(currency=c)
                    )
                )

        result = gather(tasks, max_workers=min(8, len(tasks)))
        errors = {key: _error_text(exc) for key, exc in result.errors.items()}

        core: dict[str, dict[str, Any]] = {}
        target_specific: dict[str, dict[str, Any]] = {}
        for key in market_queries:
            value = result.results.get(f"market:{key}")
            if not isinstance(value, MarketSnapshot):
                continue
            destination = core if key in CORE_MARKETS else target_specific
            destination[key] = value.to_dict()

        nominal = result.results.get("rates:nominal")
        if isinstance(nominal, list):
            for tenor, key, label in (("2Y", "us2y", "美国2年期收益率"), ("10Y", "us10y", "美国10年期收益率")):
                rate = self._rate_snapshot(nominal, tenor=tenor, key=key, label=label)
                if rate is not None:
                    core[key] = rate

        real = result.results.get("rates:real")
        if isinstance(real, list):
            rate = self._rate_snapshot(
                real,
                tenor="10Y",
                key="us10y_real",
                label="美国10年期实际利率",
            )
            if rate is not None:
                target_specific["us10y_real"] = rate

        events_value = result.results.get("events")
        events = [event.to_dict() for event in events_value] if isinstance(events_value, list) else []

        derivatives: dict[str, Any] = {}
        for key, value in result.results.items():
            if not key.startswith("deribit:"):
                continue
            perpetual = value.perpetual() if hasattr(value, "perpetual") else None
            dated = next((point for point in value.points if not point.is_perpetual), None)
            derivatives[key.partition(":")[2]] = {
                "source": "Deribit",
                "market_time": self._milliseconds_to_utc(getattr(value, "generated_timestamp_ms", None)),
                "funding_rate": (
                    perpetual.raw.get("summary", {}).get("current_funding")
                    if perpetual is not None and isinstance(perpetual.raw, dict)
                    else None
                ),
                "open_interest": getattr(perpetual, "open_interest", None),
                "basis": getattr(dated, "basis_vs_perpetual", None),
                "annualized_basis": getattr(dated, "annualized_basis_vs_perpetual", None),
                "basis_instrument": getattr(dated, "instrument_name", None),
            }

        all_snapshots = list(core.values()) + list(target_specific.values())
        stale = sorted(
            snapshot["key"]
            for snapshot in all_snapshots
            if snapshot.get("freshness") in {"stale", "unknown"}
        )
        return PremarketDataBundle(
            schema_version="1.0",
            generated_at=generated_at.isoformat().replace("+00:00", "Z"),
            target=target,
            session=session,
            session_date=session_date,
            session_timezone=session_timezone,
            core=core,
            target_specific=target_specific,
            events=events,
            derivatives=derivatives,
            errors=errors,
            data_quality={
                "complete": not errors,
                "stale_or_unknown": stale,
                "calendar_configured": self.calendar_provider.configured,
            },
        )

    @staticmethod
    def _rate_snapshot(
        curves: list[YieldCurveSnapshot], *, tenor: str, key: str, label: str
    ) -> dict[str, Any] | None:
        available = [curve for curve in curves if curve.yield_for(tenor) is not None]
        if not available:
            return None
        latest = available[0]
        previous = available[1] if len(available) > 1 else None
        current_value = latest.yield_for(tenor)
        previous_value = previous.yield_for(tenor) if previous is not None else None
        change = (
            current_value - previous_value
            if current_value is not None and previous_value is not None
            else None
        )
        fetched_at = _now_utc()
        latest_date = _normalize_curve_date(latest.date)
        previous_date = _normalize_curve_date(previous.date) if previous is not None else None
        age_days = (date.today() - latest_date).days if latest_date is not None else None
        freshness = "fresh" if age_days is not None and 0 <= age_days <= 3 else "stale"
        market_date = latest_date.isoformat() if latest_date is not None else latest.date
        return {
            "key": key,
            "label": label,
            "symbol": tenor,
            "current": current_value,
            "unit": "%",
            "previous_close": previous_value,
            "session_open": None,
            "since_previous_close": change,
            "since_previous_close_pct": None,
            "today_change": None,
            "today_change_pct": None,
            "market_time": f"{market_date}T00:00:00Z",
            "fetched_at": fetched_at,
            "age_seconds": None,
            "freshness": freshness,
            "source": "U.S. Department of the Treasury",
            "source_url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates",
            "frequency": "daily",
            "exchange_timezone": "UTC",
            "metadata": {
                "change_bps": change * 100.0 if change is not None else None,
                "previous_date": previous_date.isoformat() if previous_date is not None else None,
                "curve_kind": latest.curve_kind,
            },
        }

    @staticmethod
    def _milliseconds_to_utc(value: int | None) -> str | None:
        if value is None:
            return None
        return datetime.fromtimestamp(value / 1000.0, timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _session(requested: str, now_utc: datetime | None = None) -> str:
        requested = requested.strip().lower()
        if requested != "auto":
            if requested not in SESSION_TIMEZONES:
                raise ValueError(f"unsupported session: {requested!r}")
            return requested
        hour = (now_utc or datetime.now(timezone.utc)).hour
        if 5 <= hour < 11:
            return "london"
        if 11 <= hour < 17:
            return "new_york"
        return "asia"
