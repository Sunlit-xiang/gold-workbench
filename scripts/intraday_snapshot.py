#!/usr/bin/env python3
"""Print a structured premarket evidence bundle for Codex or the Web UI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digital_oracle.intraday import IntradayContextQuery, IntradayMarketContextService


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Build Digital Oracle premarket context data")
    parser.add_argument(
        "--target",
        default="global",
        choices=("global", "equities", "gold", "eurusd", "gbpusd", "usdjpy", "audusd", "btc", "eth", "crypto"),
    )
    parser.add_argument("--session", default="auto", choices=("auto", "asia", "london", "new_york"))
    parser.add_argument("--date", default="", help="economic calendar date, YYYY-MM-DD")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    bundle = IntradayMarketContextService().build(
        IntradayContextQuery(target=args.target, session=args.session, calendar_date=args.date)
    )
    print(
        json.dumps(
            bundle.to_dict(),
            ensure_ascii=False,
            indent=2 if args.pretty else None,
            sort_keys=args.pretty,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
