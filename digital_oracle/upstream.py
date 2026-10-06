"""Read-only upstream intelligence. Observations do not authorize adoption."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .asset_store import digest

WATCHLIST = Path(__file__).resolve().parents[1] / "docs/upstream-watchlist.json"


def github_get(path):
    headers = {"User-Agent": "DigitalOracle-Upstream/1", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        with urlopen(Request("https://api.github.com/" + path, headers=headers), timeout=20) as response:
            raw = response.read(3_000_001)
            if len(raw) > 3_000_000:
                raise ValueError("upstream payload exceeds limit")
            return json.loads(raw)
    except HTTPError as exc:
        if exc.code == 404 and path.endswith("releases/latest"):
            return None  # Explicitly no published release, not a failed HEAD check.
        raise


def inspect_project(project, previous=None, fetch=github_get, checked_at=None):
    stamp = checked_at or datetime.now(timezone.utc).isoformat()
    repo = project["repository"]
    result = {"repository": repo, "baseline": project["baseline"], "checked_at": stamp,
              "status": "UNKNOWN", "adoption": project["adoption"], "changes": [],
              "action": "No automatic adoption", "baseline_url": f"https://github.com/{repo}/tree/{project['baseline']}"}
    try:
        meta = fetch(f"repos/{repo}")
        canonical_repo = meta["full_name"]
        head = fetch(f"repos/{canonical_repo}/commits/{meta['default_branch']}")
        result.update(canonical_repository=canonical_repo, head=head["sha"], head_time=head["commit"]["committer"]["date"],
                      url=meta["html_url"], archived=meta["archived"],
                      license_label=(meta.get("license") or {}).get("spdx_id"), status="available")
        # Pin auxiliary queries to the inspected HEAD; avoid mid-check branch drift.
        license_data = fetch(f"repos/{canonical_repo}/license?ref={head['sha']}")
        result["license_blob"] = license_data["sha"]
        result["license_url"] = license_data["html_url"]
        release = fetch(f"repos/{canonical_repo}/releases/latest")
        result["release"] = ({k: release.get(k) for k in ("tag_name", "published_at", "html_url", "body")} if release else None)
        if result["release"] and result["release"].get("body"):
            result["release"]["body"] = result["release"]["body"][:6000]
        previous_release=(previous or {}).get("release") or {}
        current_release=result["release"] or {}
        result["release_changed"]=bool(previous and previous_release!=current_release)
        prior_head = previous.get("head") if previous and previous.get("status") == "available" else project["baseline"]
        result["compared_from"] = prior_head
        result["compare_url"] = f"https://github.com/{canonical_repo}/compare/{prior_head}...{head['sha']}"
        result["changed"] = prior_head != head["sha"]
        if result["changed"]:
            delta = fetch(f"repos/{canonical_repo}/compare/{prior_head}...{head['sha']}")
            files = delta.get("files", [])
            result["changes"] = [{"path": f["filename"], "status": f["status"],
                                  "research_relevant": any(f["filename"].startswith(p) for p in project["paths"])} for f in files]
            result["compare_truncated"] = len(files) >= 300
            result["ahead_by"] = delta.get("ahead_by")
        result["license_changed"] = bool(previous and previous.get("license_blob") and previous["license_blob"] != result["license_blob"])
        # Public advisories only. No advisory is not proof of security.
        try:
            advisories = fetch(f"repos/{canonical_repo}/security-advisories?per_page=30")
            result["security"] = {"status": "available", "public_advisories": [
                {k: a.get(k) for k in ("ghsa_id", "severity", "summary", "html_url", "published_at")} for a in advisories]}
            result["security"]["coverage"]="First 30 public advisories; not a full security audit"
        except Exception as exc:
            result["security"] = {"status": "UNKNOWN", "error": type(exc).__name__}
        public_ids={a["ghsa_id"] for a in result["security"].get("public_advisories",[])}
        previous_ids={a["ghsa_id"] for a in (previous or {}).get("security",{}).get("public_advisories",[])}
        result["new_public_advisories"]=sorted(public_ids-previous_ids)
        result["impact"] = "REVIEW_REQUIRED" if (result["changed"] or result["license_changed"] or result["release_changed"]
                        or result["new_public_advisories"] or meta["archived"] or canonical_repo != repo) else "NO_HEAD_CHANGE"
        result["next_step"] = "Read changed code in isolation; register a falsifiable experiment before any model or dependency change."
    except Exception as exc:
        result["error"] = type(exc).__name__  # Never leak authenticated request diagnostics.
        result["status"] = "UNKNOWN"
    return result


def track(store, fetch=github_get, now=None):
    watchlist = json.loads(WATCHLIST.read_text(encoding="utf-8"))
    previous = {}
    for row in store.list("upstream_observations", 10000):
        if row.get("status") == "available":
            previous.setdefault(row["repository"], row)
    results = []
    stamp = now or datetime.now(timezone.utc).isoformat()
    for project in watchlist["projects"]:
        row = inspect_project(project, previous.get(project["repository"]), fetch, stamp)
        row["watchlist_hash"] = digest(watchlist)
        row["id"] = store.put("upstream_observations", row)
        if row.get("impact")=="REVIEW_REQUIRED":
            # Stable case identity: later unchanged checks never silently clear a review.
            case=digest({k:row.get(k) for k in ("repository","head","license_blob","release","new_public_advisories","archived")})
            if not store.get("upstream_reviews",case):
                store.put("upstream_reviews",{"case_id":case,"repository":row["repository"],"observation_id":row["id"],
                          "available_at":stamp,"state":"PENDING","policy":"Manual isolated review and experiment; no auto promotion"},case)
        results.append(row)
    return {"checked_at": stamp, "projects": results, "policy": watchlist["policy"]}


def latest_tracking(store):
    latest = {}
    for row in store.list("upstream_observations", 10000):
        latest.setdefault(row["repository"], row)
    return list(latest.values())


def pending_reviews(store):
    latest={}
    for row in store.list("upstream_reviews",10000):latest.setdefault(row["case_id"],row)
    return [row for row in latest.values() if row["state"]=="PENDING"]
