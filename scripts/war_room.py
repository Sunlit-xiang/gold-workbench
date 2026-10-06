"""War Room CLI. Private interactive input is stdin, never a process argument or Pages export."""
import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from digital_oracle.asset_store import canonical
from digital_oracle.macro_core import ASSETS
from digital_oracle.macro_pipeline import macro_dashboard
from digital_oracle.macro_store import MacroStore
from digital_oracle.research_team import daily_team, run_analyst, session_key, ROLES
from digital_oracle.war_room import board


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("board", "team", "ask", "analyst"))
    parser.add_argument("--db", default="research_data/oracle.sqlite")
    parser.add_argument("--asset", choices=tuple(ASSETS), default="gold")
    parser.add_argument("--language", choices=("zh", "en"), default="zh")
    args = parser.parse_args()
    if not Path(args.db).is_file():
        raise ValueError("Existing ledger required; no implicit history initialization")
    store = MacroStore(args.db)
    try:
        if args.command == "board":
            result = board(store, args.asset, args.language)
        else:
            raw = sys.stdin.read(12001)
            if len(raw) > 12000:
                raise ValueError("research input too large")
            data = json.loads(raw or "{}")
            identity = data.get("snapshot_id")
            if identity:
                if not re.fullmatch(r"[a-f0-9]{64}", identity):
                    raise ValueError("invalid snapshot identity")
                view = store.get("macro_snapshots", identity)
                if not view or view["asset_id"] != args.asset:
                    raise ValueError("snapshot asset mismatch")
                view["id"] = identity
            else:
                view = macro_dashboard(store, args.asset)
            provider = data.get("provider"); model = data.get("model")
            if args.command == "team":
                result = daily_team(view, store, language=args.language, provider=provider, model=model)
            elif args.command == "analyst":
                role = data.get("analyst")
                if role not in ROLES:
                    raise ValueError("unknown analyst")
                sid = session_key(view, role, args.language)
                turns = [r for r in reversed(store.list("research_turns", 100000)) if r["session_id"] == sid]
                result = {"session_id": sid, "analyst": role, "snapshot_id": view.get("id"), "turns": []}
                for turn in turns:
                    request = store.get("research_requests", turn["id"])
                    result["turns"].append({"question": request["question"], **{k: turn[k] for k in
                        ("status", "summary", "sections", "available_at", "sequence") if k in turn}})
            else:
                role = data.get("analyst")
                if role not in ROLES:
                    raise ValueError("unknown analyst")
                runs = [run for run in store.list("research_runs", 10000) if run["snapshot_id"] == view.get("id") and run["language"] == args.language]
                peers = [{'id':report['id'],**store.get("research_turns", report["id"])} for report in (runs[0]["reports"] if runs else []) if report.get("status") == "available"]
                result = run_analyst(view, store, role, data.get("question"), language=args.language,
                                     provider=provider, model=model, peers=peers[:12], phase='followup')
                # Private local response: no raw tool bodies/messages or secrets in HTTP.
                result = {k: result[k] for k in ("id", "status", "analyst", "work_done", "session_id", "snapshot_id",
                          "summary", "sections", "sequence", "available_at", "provider", "model", "error", "note",
                          "confidence", "supporting_evidence_ids", "opposing_evidence_ids", "relationships", "cited_sources") if k in result}
        print(canonical(result))
    finally:
        store.close()


if __name__ == "__main__": main()
