"""Build a static workbench or return a read-only enriched local dashboard."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from digital_oracle.asset_store import AssetStore, canonical
from digital_oracle.asset_pipeline import DEFAULT_DB
from digital_oracle.gold_delivery import delivery_dashboard, export_site, commentary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["export", "dashboard", "commentary", "seed"])
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--output", default="dist")
    p.add_argument("--offline", action="store_true")
    args = p.parse_args()
    store = AssetStore(args.db)
    try:
        if args.command == "export":
            result = export_site(store, args.output, not args.offline, not args.offline)
        elif args.command == "dashboard":
            result = delivery_dashboard(store)
        elif args.command == "seed":
            # Frozen parameters and research report only; no raw histories, secrets or local paths.
            seed = {"model": store.latest("models"), "report": store.latest("reports")}
            seed["report"] = delivery_dashboard(store)["research"]
            Path(args.output).write_text(canonical(seed), encoding="utf-8")
            result = {"output": args.output, "model_version": seed["model"]["version"]}
        else:
            config = json.load(sys.stdin)
            result = commentary(delivery_dashboard(store), **config)
        print(canonical(result))
    finally:
        store.close()


if __name__ == "__main__":
    main()
