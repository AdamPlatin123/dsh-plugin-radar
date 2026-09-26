#!/usr/bin/env python3
"""Aggregate a single summary.json (SOP §8.2) — discovery-track candidate statistics.

Scope (P1 修正，与实际消费方对齐)：summary.json 统计的是发现轨候选仓人群
（discover → normalize → 本脚本），消费方为 ops/dashboard.py 与 probe；
公开清单/README/latest.json 的渲染-导出走 canonical 路径
（engine/aggregation/build_canonical.py），与本文件人群不同、互不供给。

Counts are computed independently from candidates.json + catalog.json, never reverse-
parsed from Markdown. Evidence axes are kept separate; not_run/inconclusive can never
enter a pass count. Emits new_since_last / removed_since_last against the prior summary.
"""
from __future__ import annotations
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAND = ROOT / "generated" / "current" / "candidates.json"
CAT = ROOT / "generated" / "current" / "catalog.json"
PREV = ROOT / "generated" / "current" / "summary.json"  # read before overwrite
OUT = ROOT / "generated" / "current" / "summary.json"

EVIDENCE_AXES = ("static", "compile", "runtime", "security")
PASS_VALUES = {"pass", "warn"}
NEVER_PASS = {"not_run", "inconclusive"}


def load(p: Path):
    return json.loads(p.read_text()) if p.is_file() else {}


def main() -> int:
    radar = load(CAND)
    catalog = load(CAT)
    if not radar:
        print("[aggregate] candidates.json missing — run discover first", file=sys.stderr)
        return 2
    candidates = radar.get("candidates", [])
    entries = catalog.get("entries", [])

    # Catalog-state counts (curated view)
    states = {"candidate": 0, "listed": 0, "rejected": 0, "removed": 0, "blocked": 0}
    by_evidence = {ax: {"pass": 0, "warn": 0, "fail": 0, "not_run": 0, "inconclusive": 0} for ax in EVIDENCE_AXES}
    for e in entries:
        st = e.get("curation", {}).get("state", "candidate")
        states[st] = states.get(st, 0) + 1
        ev = e.get("observation", {}).get("evidence", {}) or e.get("evidence", {})
        for ax in EVIDENCE_AXES:
            v = ev.get(ax, "not_run")
            if v in by_evidence[ax]:
                by_evidence[ax][v] += 1

    # Radar source counts
    sc = radar.get("source_counts", {})

    # new/removed vs prior summary (by stable id)
    prev = load(PREV)
    prev_ids = {e.get("id") for e in prev.get("candidates", [])} if prev else set()
    cur_ids = {c.get("id") for c in candidates}
    new_since = len(cur_ids - prev_ids)
    removed_since = len(prev_ids - cur_ids)

    # shrinkage guard (SOP §8.1): fail closed if total dropped >5% with no tombstoning
    shrink_ok = True
    if prev and prev.get("counts", {}).get("total"):
        prev_total = prev["counts"]["total"]
        cur_total = len(candidates)
        if cur_total < prev_total * 0.95:
            shrink_ok = False

    not_run_or_inc = sum(
        1 for e in entries
        if all((e.get("observation", {}).get("evidence", {}) or {}).get(ax, "not_run") in NEVER_PASS
               for ax in EVIDENCE_AXES)
    )

    pipeline = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True,
    ).stdout.strip() or "unknown"

    summary = {
        "run_id": radar.get("run_id", ""),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pipeline_commit": pipeline,
        "counts": {
            "total": len(candidates),
            "candidate": states["candidate"],
            "listed": states["listed"],
            "rejected": states["rejected"],
            "removed": states["removed"],
            "blocked": states["blocked"],
            "by_evidence": by_evidence,
        },
        "sources": {k: sc.get(k, 0) for k in ("org", "topic", "keyword", "clones", "research")},
        "new_since_last": new_since,
        "removed_since_last": removed_since,
        "not_run_or_inconclusive": not_run_or_inc,
        "shrinkage_ok": shrink_ok,
    }
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    tmp.replace(OUT)
    print(f"[aggregate] summary → {OUT.relative_to(ROOT)}")
    print(f"[aggregate] total={summary['counts']['total']} candidate={states['candidate']} listed={states['listed']} | new={new_since} removed={removed_since} shrinkage_ok={shrink_ok}")
    if not shrink_ok:
        print("[aggregate] FAIL CLOSED: candidate total shrank >5% vs last published — source likely incomplete", file=sys.stderr)
        return 20
    return 0


if __name__ == "__main__":
    sys.exit(main())
