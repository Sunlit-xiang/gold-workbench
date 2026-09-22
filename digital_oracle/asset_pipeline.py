"""Independent collection -> model -> frozen prediction -> append-only outcome."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd

from .asset_store import AssetStore, digest, utcnow
from .asset_model import ASSET, MODEL_SPEC, build_features, fit_live, prediction_details
from .asset_research import research, metrics
from .providers.research_history import collect_dataset

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "research_data" / "oracle.sqlite"


def code_hash():
    files = sorted(Path(__file__).parent.glob("asset_*.py"))+[Path(__file__).parent/"providers"/"research_history.py"]
    return hashlib.sha256(b"".join(p.name.encode()+p.read_bytes() for p in files)).hexdigest()


def checked_dataset(store):
    data = store.latest("datasets")
    if not data or "gold" not in data["series"]:
        raise ValueError("No Gold dataset. Run collect first; inspect source errors if collection failed.")
    return data


def run_research(store, open_holdout=False):
    if not open_holdout:
        raise ValueError("Explicit --open-holdout required. Register protocol and run tests first.")
    dataset = checked_dataset(store)
    protocol_hash = hashlib.sha256((ROOT/"docs"/"GOLD_EXPERIMENT_PROTOCOL.md").read_bytes()).hexdigest()
    store.event("holdout_opened", dataset_id=dataset["id"], protocol_hash=protocol_hash, code_hash=code_hash(),
                warning="One-way access; this sample cannot be called unseen in subsequent experiments")
    report = research(build_features(dataset), include_holdout=True)
    report.update({"created_at": utcnow(), "dataset_id": dataset["id"], "protocol_hash": protocol_hash, "code_hash": code_hash()})
    key = store.put("reports", report)
    return {"id": key, **report}


def publish_shadow(store):
    """Explicit user/CLI action, never part of the daily job."""
    dataset = checked_dataset(store)
    frame = build_features(dataset)
    manifest = {"asset": ASSET, "spec": MODEL_SPEC, "code_hash": code_hash(), "dataset_id": dataset["id"],
                "created_at": utcnow(), "activation": "research_shadow_only", "models": {}}
    for key, h in ASSET["horizons"].items():
        manifest["models"][key] = fit_live(frame, h) if h else None
    manifest["version"] = "Gold.GCProxy.G001.shadow."+digest(manifest)[:12]
    key = store.put("models", manifest)
    store.event("shadow_published", model_id=key, version=manifest["version"], edge="No Edge")
    return {"id": key, **manifest}


def freeze(store, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("issued_at requires timezone")
    dataset = checked_dataset(store)
    model = store.latest("models")
    if not model:
        raise ValueError("No published shadow model. Run publish-shadow explicitly.")
    if model["code_hash"] != code_hash():
        raise ValueError("Numeric code changed since publication; explicitly publish a new model version before freezing")
    frame = build_features(dataset)
    # Never issue a 'live' record for a feature that was observed in the future.
    first_seen = datetime.fromisoformat(dataset["created_at"])
    if first_seen > now:
        raise ValueError("Cannot backdate prediction before dataset first_seen")
    issued_day = now.date().isoformat()
    stale = (now.date()-frame.index[-1].date()).days>4
    ids = []
    for horizon, h in ASSET["horizons"].items():
        key = digest({"asset": ASSET["asset_id"], "model": model["id"], "horizon": horizon, "day": issued_day})
        if store.get("predictions", key):
            ids.append(key)
            continue
        detail = prediction_details(frame, model["models"].get(horizon), h or 1, dataset)
        if h is None or stale:
            detail.update({"score": None, "direction": None, "edge": "No Edge", "candidate_threshold_met": False,
                           "intercept_contribution": 0,
                           "data_status": "insufficient_hourly_data" if h is None else "stale_gold_data"})
            for leaf in detail["tree"]:
                leaf["contribution"] = 0
                leaf["coefficient"] = 0
        body = {"asset": ASSET["asset_id"], "horizon": horizon, "model_id": model["id"], "model_version": model["version"],
                "dataset_id": dataset["id"], "issued_at": now.isoformat(), "issued_day": issued_day, "purpose": "live_research_shadow",
                "cohort": ASSET["cohort"], "details": detail,
                "evaluation_contract": {"version": "GC.daily.next-session.v1", "baseline": "first completed observed GC date strictly after issued UTC date",
                                        "horizon_sessions": h, "max_baseline_wait_days": 7, "max_endpoint_wait_days": 16,
                                        "noise_floor": .001, "flat_sigma": .25, "price_field": "Yahoo GC=F daily close; not executable fill"}}
        store.put("predictions", body, key)
        ids.append(key)
    store.event("freeze", prediction_ids=ids, model_id=model["id"], dataset_id=dataset["id"])
    return ids


def evaluate_due(store, now=None):
    now = now or datetime.now(timezone.utc)
    dataset = checked_dataset(store)
    bars = dataset["series"]["gold"]["rows"]
    completed = {x["prediction_id"] for x in store.list("outcomes", 100000)}
    added = []
    for prediction in reversed(store.list("predictions", 100000)):
        if prediction["id"] in completed:
            continue
        contract = prediction["evaluation_contract"]
        h = contract["horizon_sessions"]
        if h is None:
            continue
        after = [r for r in bars if prediction["issued_day"] < r["date"] < now.date().isoformat()]
        age = (now.date()-datetime.fromisoformat(prediction["issued_day"]).date()).days
        if len(after)<=h:
            if age <= contract["max_endpoint_wait_days"]:
                continue
            body = {"prediction_id": prediction["id"], "status": "unscorable", "reason": "missing baseline/endpoint after wait limit", "assessed_at": now.isoformat()}
        else:
            baseline, endpoint = after[0], after[h]
            if (pd.Timestamp(baseline["date"])-pd.Timestamp(prediction["issued_day"])).days>7:
                body = {"prediction_id": prediction["id"], "status": "unscorable", "reason": "baseline late", "assessed_at": now.isoformat()}
            elif any((pd.Timestamp(after[i+1]["date"])-pd.Timestamp(after[i]["date"])).days>4 for i in range(h)):
                body = {"prediction_id": prediction["id"], "status": "unscorable", "reason": "ambiguous data gap; not compressing missing sessions", "assessed_at": now.isoformat()}
            else:
                import math
                ret = math.log(endpoint["close"]/baseline["close"])
                sigma = prediction["details"]["sigma"]
                if sigma is None or sigma<=0:
                    body = {"prediction_id": prediction["id"], "status": "unscorable", "reason": "missing frozen volatility", "assessed_at": now.isoformat()}
                else:
                    threshold = max(.001, .25*sigma)
                    label = "Positive" if ret>threshold else "Negative" if ret < -threshold else "Neutral"
                    body = {"prediction_id": prediction["id"], "status": "evaluated", "assessed_at": now.isoformat(),
                            "baseline": baseline, "endpoint": endpoint, "return": ret, "label": label, "flat_threshold": threshold,
                            "directional_hit": prediction["details"]["direction"]==label if prediction["details"]["direction"] else None,
                            "evaluation_version": contract["version"], "dataset_id": dataset["id"],
                            "payload_id": dataset["series"]["gold"]["payload_id"], "supersedes_id": None}
        added.append(store.put("outcomes", body, "outcome:"+prediction["id"]))
    return added


def calibrate(store):
    predictions = {p["id"]: p for p in store.list("predictions", 100000)}
    outcomes = store.list("outcomes", 100000)
    evaluated = [o for o in outcomes if o["status"]=="evaluated"]
    grouped = {}
    for o in evaluated:
        p = predictions[o["prediction_id"]]
        key = p["model_version"]+":"+p["horizon"]
        group = grouped.setdefault(key, {"n": 0, "directional_n": 0, "hits": 0, "validated_edges": 0})
        group["n"] += 1
        if p["details"]["direction"] in ("Positive", "Negative"):
            group["directional_n"] += 1
            group["hits"] += int(o["directional_hit"])
    for g in grouped.values():
        g["coverage"] = g["directional_n"]/g["n"]
        g["hit_rate"] = g["hits"]/g["directional_n"] if g["directional_n"] else None
    body = {"created_at": utcnow(), "groups": grouped, "total_predictions": len(predictions), "evaluated": len(evaluated),
            "outcome_ids": [o["id"] for o in outcomes], "decision": "NONE", "parameter_changes": [],
            "reason": "Descriptive forward statistics only; no automatic parameter promotion. Independent-sample/PIT/roll gates apply."}
    key = store.put("calibrations", body)
    return {"id": key, **body}


def dashboard(store):
    dataset = store.latest("datasets")
    model = store.latest("models")
    predictions = store.list("predictions", 200)
    outcomes = {o["prediction_id"]: o for o in store.list("outcomes", 10000)}
    current = {}
    for p in predictions:
        if p["horizon"] not in current:
            current[p["horizon"]] = p
    report = store.latest("reports")
    research_summary = None
    if report:
        research_summary = {k: v for k,v in report.items() if k!="horizons"}
        research_summary["horizons"] = {h: {k:v for k,v in value.items() if k not in ("forecasts", "coefficient_history")} for h,value in report["horizons"].items()}
    sources = []
    if dataset:
        for key, s in dataset["series"].items():
            sources.append({"id": key, "source": s["source"], "instrument": s["instrument"], "first": s["rows"][0]["date"],
                            "last": s["rows"][-1]["date"], "count": len(s["rows"]), "fetched_at": s["fetched_at"], "pit": s["pit_status"], "note": s["note"]})
    return {"asset": ASSET, "now": utcnow(), "model": model, "current": current,
            "prices": dataset["series"].get("gold", {}).get("rows", [])[-260:] if dataset else [],
            "sources": sources, "source_errors": dataset.get("errors", {}) if dataset else {},
            "research": research_summary, "calibration": store.latest("calibrations"),
            "ledger": [{k:v for k,v in p.items() if k!="details"} | {"score": p["details"]["score"], "direction": p["details"]["direction"], "edge": p["details"]["edge"], "outcome": outcomes.get(p["id"])} for p in predictions],
            "events": store.list("events", 12), "limitations": ["GC Proxy ≠ XAUUSD Spot", "Research OOS ≠ live forward validation", "H4 unavailable", "Daily model does not retrain itself", "No validated Edge"]}
