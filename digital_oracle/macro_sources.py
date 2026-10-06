"""Bounded public-source adapters. Failed requests never synthesize observations."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import io
import math
import re
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from .asset_store import digest

REGISTRY = {
    "ecb_fx": {"source": "ECB", "tier": 1, "frequency": "daily reference", "url": "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml", "role": "reference fixing, not executable/intraday spot", "max_age_days": 5},
    "au_cash": {"source": "RBA F1", "tier": 1, "frequency": "daily", "url": "https://www.rba.gov.au/statistics/tables/csv/f01-data.csv", "role": "cash target, not OIS path", "max_age_days": 5},
    "nz_cash": {"source": "RBNZ B2", "tier": 1, "frequency": "daily", "url": "https://www.rbnz.govt.nz/statistics/series/exchange-and-interest-rates/wholesale-interest-rates", "role": "OCR, not OIS path", "max_age_days": 5},
    "au_money": {"source": "FRED / OECD", "tier": 1, "frequency": "monthly", "series_id": "IRSTCI01AUM156N", "unit": "% p.a.", "role": "overnight money rate, not policy target", "max_age_days": 75},
    "nz_money": {"source": "FRED / OECD", "tier": 1, "frequency": "monthly", "series_id": "IRSTCI01NZM156N", "unit": "% p.a.", "role": "overnight money rate, not policy target", "max_age_days": 75},
    "fed_news": {"source": "Fed", "tier": 1, "frequency": "event", "url": "https://www.federalreserve.gov/feeds/press_monetary.xml", "role": "official headlines; no numeric surprise"},
    "rba_news": {"source": "RBA", "tier": 1, "frequency": "event", "url": "https://www.rba.gov.au/rss/rss-cb-media-releases.xml", "role": "official headlines; no numeric surprise"},
    "ecb_news": {"source": "ECB", "tier": 1, "frequency": "event", "url": "https://www.ecb.europa.eu/rss/press.html", "role": "official headlines; no numeric surprise"},
}
for spec in REGISTRY.values():
    if "series_id" in spec:
        spec["url"] = "https://fred.stlouisfed.org/graph/?g=0&series_id=" + spec["series_id"]


def request_bytes(url):
    req = Request(url, headers={"User-Agent": "DigitalOracleResearch/2.0", "Accept": "*/*"})
    with urlopen(req, timeout=18) as response:
        raw = response.read(3_000_001)
    if len(raw) > 3_000_000:
        raise ValueError("source exceeds payload limit")
    return raw


def parse_fred(raw, today):
    rows = []
    for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
        values = list(row.values())
        if len(values) < 2 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", values[0] or ""):
            continue
        try:
            value = float(values[1])
        except (ValueError, TypeError):
            continue
        if values[0] < today and math.isfinite(value):
            rows.append({"date": values[0], "close": value})
    if not rows:
        raise ValueError("empty FRED series")
    return sorted(rows, key=lambda r: r["date"])[-400:]


def parse_ecb(raw, today):
    result = {"audnzd": [], "eurusd": [], "usdjpy": []}
    root = ET.fromstring(raw)
    for cube in root.iter():
        day = cube.attrib.get("time")
        if not day or day >= today:
            continue
        rates = {n.attrib["currency"]: float(n.attrib["rate"]) for n in cube if "currency" in n.attrib}
        if not all(rates.get(c, 0) > 0 for c in ("AUD", "NZD", "USD", "JPY")):
            continue
        for key, value in (("audnzd", rates["NZD"] / rates["AUD"]),
                           ("eurusd", rates["USD"]), ("usdjpy", rates["JPY"] / rates["USD"])):
            if math.isfinite(value):
                result[key].append({"date": day, "close": value})
    if not result["audnzd"]:
        raise ValueError("ECB reference currencies absent")
    return {k: sorted(v, key=lambda r: r["date"]) for k, v in result.items()}


def parse_rba(raw, today):
    table = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    code = "FCMMCRTD"
    header = next((r for r in table if code in r), None)
    if not header:
        raise ValueError("RBA cash target series ID absent")
    index = header.index(code)
    rows = []
    for row in table:
        if len(row) <= index:
            continue
        try:
            day = datetime.strptime(row[0].strip(), "%d-%b-%Y").date().isoformat()
            value = float(row[index])
        except ValueError:
            continue
        if day < today and math.isfinite(value):
            rows.append({"date": day, "close": value})
    if not rows:
        raise ValueError("RBA dated cash target absent")
    return sorted(rows, key=lambda r: r["date"])[-100:]


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "tr": self.row = []
        if tag in ("td", "th") and self.row is not None: self.cell = []

    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join(" ".join(self.cell).split())); self.cell = None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row); self.row = None


def parse_rbnz(raw, today):
    parser = TableParser(); parser.feed(raw.decode("utf-8"))
    idx = None
    rows = []
    for row in parser.rows:
        if any("Official Cash Rate" in cell for cell in row) and row and row[0] == "Date":
            idx = next(i for i, v in enumerate(row) if "Official Cash Rate" in v)
            continue
        if idx is None or len(row) <= idx:
            continue
        try:
            day = datetime.strptime(row[0].replace("Sept", "Sep"), "%d %b %Y").date().isoformat()
            value = float(row[idx])
        except ValueError:
            continue
        if day < today and math.isfinite(value):
            rows.append({"date": day, "close": value})
    if not rows:
        raise ValueError("dated RBNZ OCR table absent; do not scrape undated policy text")
    return sorted(rows, key=lambda r: r["date"])


def parse_feed(raw, now):
    root = ET.fromstring(raw)
    rows = []
    for item in root.findall(".//item")[:12]:
        pub = item.findtext("pubDate")
        try:
            published = parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat() if pub else None
        except (ValueError, TypeError):
            published = None
        if published and datetime.fromisoformat(published) > datetime.fromisoformat(now):
            continue
        rows.append({"title": item.findtext("title") or "", "url": item.findtext("link") or "",
                     "publication_time": published, "scope": "official headline only"})
    if not rows:
        raise ValueError("RSS items absent")
    return rows


def collect_public(store, now, fetch=request_bytes):
    prior = {}
    for p in store.list("macro_payloads", 10000):
        prior.setdefault(p.get("source_id"), p)

    def collect_one(pair):
        key, spec = pair
        base = {"source_id": key, **spec, "ingestion_time": now, "available_at": now, "status": "UNKNOWN"}
        try:
            cached = prior.get(key)
            age = (datetime.fromisoformat(now) - datetime.fromisoformat(cached["ingestion_time"])).total_seconds() if cached else 999999
            if cached and 0 <= age < 21600:
                return key, {**cached, "cached": True}, None
            url = spec["url"]
            if "series_id" in spec:
                url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + spec["series_id"]
            raw = fetch(url)
            text = raw.decode("utf-8-sig")
            payload = {"source_id": key, "url": url, "ingestion_time": now, "available_at": now,
                       "content_hash": digest(text), "raw_text": text}
            today = now[:10]
            if "series_id" in spec: base["rows"] = parse_fred(raw, today)
            elif key == "ecb_fx": base["series"] = parse_ecb(raw, today)
            elif key == "au_cash": base["rows"] = parse_rba(raw, today)
            elif key == "nz_cash": base["rows"] = parse_rbnz(raw, today)
            else: base["items"] = parse_feed(raw, now)
            base["status"] = "available"
            return key, base, payload
        except Exception as exc:
            base["error"] = type(exc).__name__
            # Keep last known data visibly stale, never a silent successful fallback.
            if key in prior:
                base.update({k: prior[key][k] for k in ("rows", "series", "items", "payload_id", "ingestion_time", "available_at") if k in prior[key]})
                base["status"] = "STALE"
            return key, base, None

    results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for key, result, payload in pool.map(collect_one, REGISTRY.items()):
            if payload:
                payload["parsed"] = result
                payload_id = store.put("macro_payloads", payload)
                result["payload_id"] = payload_id
            # The cache record includes parsed data without rewriting archived payload.
            if result.get("status") == "available" and not result.get("cached"):
                store.put("macro_payloads", {**result, "source_id": key, "cache_entry": True})
            results[key] = result
    return results
