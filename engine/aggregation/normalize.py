#!/usr/bin/env python3
"""Radar/Catalog separation (SOP §5.3, §7.1).

- Radar (generated/current/candidates.json) = everything discovered. state=candidate implicit.
- Catalog (catalog/plugins/<id>.json) = curated fact source, keyed by STABLE github id.
  New candidates do NOT auto-enter the Catalog; only investigated repos are seeded
  here as state=candidate, awaiting a curation PR to become listed.

This script overlays live observations onto existing catalog entries (full_name drift
from rename, lifecycle from archived, support, is_plugin) WITHOUT overwriting human
fields (curation/ownership/disclosures), seeds catalog entries for newly-investigated
repos, and blocks tombstoned ids from re-entering.

Output: generated/current/catalog.json (curated view with observation overlay).
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import sys as _sys
_LIB = Path(__file__).resolve().parents[1] / 'lib'
if str(_LIB) not in _sys.path:
    _sys.path.insert(0, str(_LIB))
from radar.atomicio import atomic_write_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent   # engine/aggregation → 仓库根
CAND = ROOT / "generated" / "current" / "candidates.json"
CAT_DIR = ROOT / "catalog" / "plugins"
TOMB = ROOT / "catalog" / "tombstones.json"
OUT = ROOT / "generated" / "current" / "catalog.json"


def load_json(p: Path, default):
    if not p.is_file():
        return default
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return default


def lifecycle_from(obs: dict) -> str:
    if obs.get("archived"):
        return "archived"
    return "active"


def main() -> int:
    if not CAND.is_file():
        print("[normalize] candidates.json missing — run discover first", file=sys.stderr)
        return 2
    radar = load_json(CAND, {})
    candidates = {c["id"]: c for c in radar.get("candidates", []) if "id" in c}

    tomb = load_json(TOMB, {"entries": []})
    blocked_ids = {e.get("id") for e in tomb.get("entries", []) if e.get("id")}

    CAT_DIR.mkdir(parents=True, exist_ok=True)
    existing = {p.stem: json.loads(p.read_text()) for p in CAT_DIR.glob("*.json") if p.is_file()}

    run_id = radar.get("run_id", "")
    observed_at = radar.get("observed_at", "")
    seeded = 0
    blocked_readds = 0
    catalog_view = []

    for cid, obs in candidates.items():
        if cid.startswith("github:unknown:"):
            continue  # no stable id → Radar only, never curated
        if cid in blocked_ids:
            blocked_readds += 1
            continue
        fn = cid.split(":")[1]  # numeric id → filename
        entry = existing.get(fn)
        if entry is None:
            # Seed only if investigated (research note) AND looks like a plugin.
            # Auto-discovered-only repos stay in Radar, not Catalog.
            if not (obs.get("has_research_note") and obs.get("is_plugin") is True):
                continue
            entry = {
                "schema_version": 1,
                "id": cid,
                "repository": {"full_name": obs.get("full_name", ""), "url": obs.get("url", "")},
                "package": obs.get("package", {}),
                "curation": {"state": "candidate", "category": "", "description_zh": ""},
                "ownership": {"method": "auto_discovered", "verified_at": ""},
                "lifecycle": {"state": lifecycle_from(obs)},
                "disclosures": {"risk": "unknown", "network": False, "filesystem": "none",
                                "credentials": [], "data_handling_url": ""},
            }
            (CAT_DIR / f"{fn}.json").write_text(json.dumps(entry, ensure_ascii=False, indent=2))
            seeded += 1
            existing[fn] = entry
        else:
            # Overlay live facts; never touch human curation/ownership/disclosures.
            entry["repository"]["full_name"] = obs.get("full_name", entry["repository"].get("full_name", ""))
            entry["repository"]["url"] = obs.get("url") or entry["repository"].get("url", "")
            entry["lifecycle"]["state"] = lifecycle_from(obs)
            if obs.get("package"):
                entry["package"] = obs.get("package")
        # attach observation snapshot for the curated view
        view = dict(entry)
        view["observation"] = {
            "run_id": run_id, "observed_at": observed_at,
            "is_plugin": obs.get("is_plugin"), "support": obs.get("support", ""),
            "stars": obs.get("stars", 0), "has_research_note": obs.get("has_research_note", False),
            "sources": obs.get("sources", []),
        }
        catalog_view.append(view)

    catalog_view.sort(key=lambda x: x.get("repository", {}).get("full_name", "").lower())
    doc = {
        "run_id": run_id, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "catalog_count": len(catalog_view), "seeded_this_run": seeded,
        "blocked_readds": blocked_readds,
        "entries": catalog_view,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(OUT, doc)   # P3：唯一原子写
    print(f"[normalize] catalog view {len(catalog_view)} → {OUT.relative_to(ROOT)}")
    print(f"[normalize] seeded {seeded} new catalog entries (researched+plugin); blocked {blocked_readds} tombstone re-adds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
