"""Macro evidence CLI: no Codex session, no browser credentials, no auto model fitting."""
import argparse
from pathlib import Path
import shutil
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from digital_oracle.asset_store import AssetStore, canonical
from digital_oracle.macro_store import MacroStore
from digital_oracle.macro_core import ASSETS
from digital_oracle.macro_pipeline import collect_macro, macro_dashboard
from digital_oracle.macro_ai import research
from digital_oracle.upstream import track
from digital_oracle.war_room import board

ROOT=Path(__file__).resolve().parents[1]


def export_macro(db,output):
    store=MacroStore(db)
    try:
        dest=Path(output);data=dest/"data";data.mkdir(parents=True,exist_ok=True)
        for name in ("macro.html","macro.js","macro.css","war-room.html","war-room.js","war-room.css","war-room-demo.js"):
            shutil.copyfile(ROOT/"web/public"/name,dest/name)
        shutil.copyfile(ROOT/"web/public/war-room.html",dest/"index.html")
        snapshots=data/"macro-snapshots";snapshots.mkdir(exist_ok=True)
        for row in store.list("macro_snapshots",100000):
            (snapshots/(row["id"]+".json")).write_text(canonical(row),encoding="utf-8")
        for asset in ASSETS:
            (data/("macro-"+asset+".json")).write_text(canonical(macro_dashboard(store,asset)),encoding="utf-8")
            legacy=AssetStore(db)
            try:
                dataset=legacy.latest('datasets') or {}
                reduced={k:{**{f:v for f,v in s.items() if f not in ('raw','rows')},'rows':s.get('rows',[])[-400:]}
                         for k,s in dataset.get('series',{}).items()}
                seed={'schema_version':1,'asset_id':asset,'snapshot':macro_dashboard(store,asset),
                      'dataset':{'id':dataset.get('id'),'created_at':dataset.get('created_at'),'series':reduced},
                      'pit_history':[e for e in store.as_of('macro_evidence',store.latest('macro_snapshots')['as_of'],100000)
                                     if e['asset']==asset][:600]}
                (data/(f'oracle-seed-{asset}.json')).write_text(canonical(seed),encoding='utf-8')
            finally:legacy.close()
            for language in ('zh','en'):
                (data/(f"war-room-{asset}-{language}.json")).write_text(canonical(board(store,asset,language)),encoding="utf-8")
    finally:store.close()


def main():
    if hasattr(sys.stdout,"reconfigure"):sys.stdout.reconfigure(encoding="utf-8")
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("command",choices=("collect","dashboard","snapshot","upstream","export","research"))
    p.add_argument("--id",help="Immutable macro snapshot identity")
    p.add_argument("--db",default="research_data/oracle.sqlite")
    p.add_argument("--asset",choices=tuple(ASSETS),default="gold")
    p.add_argument("--output",default="dist")
    p.add_argument("--provider");p.add_argument("--model");p.add_argument("--language",choices=("zh","en"),default="zh")
    args=p.parse_args()
    if not Path(args.db).exists():raise ValueError("existing ledger required; refusing implicit initialization")
    store=MacroStore(args.db)
    try:
        if args.command=="collect":
            legacy=AssetStore(args.db)
            try: result={k:{"id":v["id"],"evidence":len(v["evidence"])} for k,v in collect_macro(store,legacy).items()}
            finally:legacy.close()
        elif args.command=="upstream":result=track(store)
        elif args.command=="dashboard":result=macro_dashboard(store,args.asset)
        elif args.command=="snapshot":
            import re
            if not args.id or not re.fullmatch(r"[a-f0-9]{64}",args.id):raise ValueError("invalid snapshot identity")
            result=store.get("macro_snapshots",args.id)
            if not result:raise ValueError("snapshot not found")
        elif args.command=="research":result=research(macro_dashboard(store,args.asset),store,args.provider,args.model,args.language)
        else:export_macro(args.db,args.output);result={"output":args.output}
        print(canonical(result))
    finally:store.close()


if __name__=="__main__":main()
