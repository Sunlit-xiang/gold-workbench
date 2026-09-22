"""Cloud daily run: restore approved state, collect, freeze, evaluate and export."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from digital_oracle.asset_store import AssetStore, canonical
from digital_oracle.asset_pipeline import collect_dataset, freeze, evaluate_due, calibrate, code_hash
from digital_oracle.gold_delivery import export_site


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db",default="research_data/oracle.sqlite")
    parser.add_argument("--output",default="dist")
    parser.add_argument("--collect",action="store_true")
    args=parser.parse_args()
    if not Path(args.db).exists():
        raise ValueError("No restored evidence ledger. Initialize an encrypted archive; never silently reset history.")
    store=AssetStore(args.db)
    try:
        model=store.latest("models")
        if not model or model["code_hash"]!=code_hash():
            raise ValueError("Approved model/code hash mismatch; no automatic refit or promotion")
        if args.collect:
            dataset=collect_dataset(store)
            if not dataset["series"].get("gold"):
                raise ValueError("Gold collection failed; preserve existing site and archive the failure")
            evaluate_due(store)
            freeze(store)
            calibrate(store)
        print(canonical(export_site(store,args.output)))
    except Exception as exc:
        store.event("cloud_run_failed",error=type(exc).__name__)
        raise
    finally:
        store.close()


if __name__=="__main__":main()
