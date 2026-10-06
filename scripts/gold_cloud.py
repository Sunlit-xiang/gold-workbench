"""Cloud daily run: restore approved state, collect, freeze, evaluate and export."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from digital_oracle.asset_store import AssetStore, canonical
from digital_oracle.asset_pipeline import collect_dataset, freeze, evaluate_due, calibrate, code_hash
from digital_oracle.gold_delivery import export_site
from digital_oracle.macro_store import MacroStore
from digital_oracle.macro_pipeline import collect_macro, macro_dashboard
from digital_oracle.macro_ai import research as macro_research
from digital_oracle.upstream import track
from macro_workbench import export_macro


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db",default="research_data/oracle.sqlite")
    parser.add_argument("--output",default="dist")
    parser.add_argument("--collect",action="store_true")
    parser.add_argument("--upstream",action="store_true",help="Weekly read-only upstream review; does not freeze new Gold calls")
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
        macro=MacroStore(args.db)
        try:
            # Initial migration bootstraps macro evidence without altering the old Gold model.
            if args.collect or not macro.latest("macro_snapshots"):
                collect_macro(macro,store)
                for asset in ('gold','audnzd'):
                    for language in ('zh','en'):
                        macro_research(macro_dashboard(macro,asset),macro,language=language)
            if args.upstream or not macro.latest('upstream_observations'):track(macro)
        finally:macro.close()
        result=export_site(store,args.output)
        export_macro(args.db,args.output)
        print(canonical(result))
    except Exception as exc:
        store.event("cloud_run_failed",error=type(exc).__name__)
        raise
    finally:
        store.close()


if __name__=="__main__":main()
