"""Independent asset research CLI. No Codex, model API or browser needed."""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from digital_oracle.asset_store import AssetStore, canonical
from digital_oracle.asset_pipeline import DEFAULT_DB, collect_dataset, run_research, publish_shadow, freeze, evaluate_due, calibrate, dashboard


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["collect", "research", "publish-shadow", "freeze", "evaluate", "calibrate", "daily", "dashboard", "backup", "export-research", "prediction"])
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--open-holdout", action="store_true")
    parser.add_argument("--output", help="backup destination")
    parser.add_argument("--id", help="immutable prediction id")
    args = parser.parse_args()
    store = AssetStore(args.db)
    try:
        if args.command=="collect":
            d = collect_dataset(store)
            result = {"dataset_id": d["id"], "rows": {k:len(v["rows"]) for k,v in d["series"].items()}, "errors": d["errors"]}
        elif args.command=="research":
            r = run_research(store, args.open_holdout)
            result = {"report_id": r["id"], "verdict": r["verdict"], "horizons": {h: v.get("models", {}).get("full", v) for h,v in r["horizons"].items()}}
        elif args.command=="publish-shadow":
            m = publish_shadow(store)
            result = {"model_id": m["id"], "version": m["version"], "train": {h:v and v["n_train"] for h,v in m["models"].items()}}
        elif args.command=="freeze": result = {"prediction_ids": freeze(store)}
        elif args.command=="evaluate": result = {"outcome_ids": evaluate_due(store)}
        elif args.command=="calibrate": result = calibrate(store)
        elif args.command=="dashboard": result = dashboard(store)
        elif args.command=="prediction":
            if not args.id: parser.error("prediction requires --id")
            result=store.get("predictions",args.id)
            if result is None: raise ValueError("Prediction not found")
        elif args.command=="daily":
            collect_dataset(store)
            result = {"outcomes": evaluate_due(store), "predictions": freeze(store)}
            result["calibration"] = calibrate(store)["id"]
        elif args.command=="export-research":
            if not args.output: parser.error("export-research requires --output directory")
            report=store.latest("reports")
            if not report: raise ValueError("No research report")
            destination=Path(args.output)
            destination.mkdir(parents=True, exist_ok=False)
            for horizon, content in report["horizons"].items():
                forecasts=content.pop("forecasts", [])
                if forecasts:
                    fields=[k for k in forecasts[0] if k!="scores"]+list(forecasts[0]["scores"])
                    with (destination/f"forecasts-{horizon}.csv").open("w",encoding="utf-8-sig",newline="") as handle:
                        writer=csv.DictWriter(handle,fieldnames=fields); writer.writeheader()
                        for observation in forecasts: writer.writerow({k:v for k,v in observation.items() if k!="scores"} | observation["scores"])
            (destination/"report-and-coefficients.json").write_text(canonical(report),encoding="utf-8")
            result={"exported":str(destination.resolve()),"report_id":report["id"]}
        else:
            if not args.output: parser.error("backup requires --output")
            store.backup(args.output)
            result = {"backup": args.output}
        print(canonical(result))
    except Exception as exc:
        store.event("command_failed", command=args.command, error=f"{type(exc).__name__}: {exc}")
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}), file=sys.stderr)
        return 1
    finally:
        store.close()
    return 0


if __name__=="__main__":
    raise SystemExit(main())
