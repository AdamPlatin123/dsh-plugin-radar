#!/usr/bin/env python3
"""Radar discovery: multi-path candidate collection, deduped by stable GitHub repo id.

Paths (SOP §7.1):
  P1 tag : topic:dsh-plugin + topic:dsh-external (public only; private dsh-external org repos EXCLUDED by policy)
  P2 keyword : "deepseek harness", "DSH plugin", "dsh plugin"  (35s spacing + 403 backoff; dshow blacklist)
  P3 library : research/*.md names + .clones/ dirs + existing reports (local facts)
  P4b npm : registry.npmjs.org keywords:dsh-plugin + name:dsh-* → package.repository 映射回 GitHub（#189 交叉路）

Output: generated/current/candidates.json — Radar only. "Discovered" != "listed".
Discovery never writes the curated Catalog; it only records what was found.

Cross-references local clones (package.json) to classify is_plugin, and research/*.md
+ .support-status.json to carry forward prior knowledge — without network per repo.
"""
from __future__ import annotations
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from urllib.parse import quote
from pathlib import Path
import sys as _sys
_LIB = Path(__file__).resolve().parents[1] / 'lib'
if str(_LIB) not in _sys.path:
    _sys.path.insert(0, str(_LIB))
from radar.thresholds import DISCOVER_PARTIAL_RATIO  # noqa: E402

os.environ["PATH"] = os.path.expanduser("~/.local/bin") + ":/usr/local/bin:" + os.environ.get("PATH", "")
ROOT = Path(__file__).resolve().parent.parent.parent   # engine/discovery → 仓库根（原 parent.parent 在 engine 布局下漂移）
OUT = ROOT / "generated" / "current" / "candidates.json"
CLONES = ROOT / ".clones"
RESEARCH = ROOT / "research"
SUPPORT = ROOT / ".support-status.json"

# 搜索专用身份（~/.radar-search.env 的 SEARCH_TOKEN）：search 配额与主账号隔离，
# 供 SEARCHES 的 topic/keyword 查询使用；org 路读私有 org 仓仍用主账号。
# 无该文件时 SEARCH_TOKEN 为空，行为与原先一致（回落主账号）。
SEARCH_TOKEN = ""
for _ln in (Path.home() / ".radar-search.env").read_text().splitlines() if (Path.home() / ".radar-search.env").exists() else []:
    if _ln.startswith("SEARCH_TOKEN="):
        SEARCH_TOKEN = _ln.split("=", 1)[1].strip()
# (label, gh api path, jq expr) — P1 + P2. jq streams one repo object per line (JSONL),
# because --paginate concatenates per-page output; .items[] for search, .[] for org list.
# 递归分片种子（#189 sjh9714 设计）：count 探测 ≤1000 直接全量；超限按 created
# 时间窗二分降粒度，窗 <1 天仍超则记"饱和分片"（结果为下界，显式可见不静默）。
# 边界实测（2026-08-16 专用搜索身份）：topic:dsh-plugin stars<5 按月 1..7 月
# 0/2/8/12/29/45，8 月 4184（爆发段）；keyword 单词 6073/2854/2855 全超限；
# sjh9714：8 月 0 星 1772、半月 1244、单日 806 贴线——静态分段不可行，必须递归。
SEEDS = [
    ("topic", "topic:dsh-plugin stars:>=100"),
    ("topic", "topic:dsh-plugin stars:20..100"),
    ("topic", "topic:dsh-plugin stars:5..20"),
    ("topic", "topic:dsh-plugin stars:<5"),
    ("topic", "topic:dsh-external"),
    ("keyword", "deepseek harness"),
    ("keyword", "DSH plugin"),
    ("keyword", "dsh plugin"),
]
SAT_LIMIT = 1000              # GitHub Search 单查询硬上限
# ---- P5 代码搜索 + 整合包识别（2026-08-27：找到所有能找到的真插件 + 整合包）----
CODE_SEEDS = ["filename:cordis.yml", "filename:cordis.yaml", "filename:dsh.bundle"]
BUNDLE_MIN_SUBS = 2  # npm 依赖中 dsh 系包 ≥2 判为整合包
SEARCH_EPOCH = (2026, 1, 1)   # dsh 生态起点（此前无仓）


def gh(path: str, jq: str, timeout: int = 120, token: str = "") -> list[dict]:
    """Call gh api --paginate with a streaming jq expr; parse JSONL (one repo per line)."""
    try:
        r = None
        for attempt in range(3):
            _env = dict(os.environ)
            if token:
                _env["GH_TOKEN"] = token
            r = subprocess.run(
                ["gh", "api", "--paginate", path, "--jq", jq],
                capture_output=True, text=True, timeout=timeout, env=_env,
            )
            if r.returncode == 0:
                break
            if "rate limit" in r.stderr.lower():
                wait = 65 * (attempt + 1)
                print(f"[discover] RATE-LIMITED {path}: backoff {wait}s (try {attempt + 1}/3)", file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"[discover] gh api FAILED {path}: {r.stderr.strip()[:160]}", file=sys.stderr)
                return []
        if r is None or r.returncode != 0:
            print(f"[discover] gh api FAILED {path}: rate-limit retries exhausted", file=sys.stderr)
            return []
        items = []
        for line in r.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return items
    except subprocess.TimeoutExpired as e:
        print(f"[discover] gh api ERROR {path}: timeout", file=sys.stderr)
        return []


def npm_get(url: str) -> "dict | None":
    """GET registry.npmjs.org；直连失败回落本地代理（RADAR_PROXY，默认 20171）。失败返回 None。"""
    proxy = os.environ.get("RADAR_PROXY", "http://127.0.0.1:20171")
    for extra in ([], ["-x", proxy]):
        r = subprocess.run(["curl", "-s", "--max-time", "30", *extra, url],
                           capture_output=True, text=True, timeout=40)
        try:
            return json.loads(r.stdout or "{}")
        except json.JSONDecodeError:
            continue
    return None


def bare(full_name: str) -> str:
    return full_name.split("/")[-1]


def org_repo_names() -> set[str]:
    """Private-org exclusion list: dsh-external repos are 100% private (404 outside);
    policy excludes them from the public-ecoscope radar. Core REST pool, ~2 req/round."""
    r = subprocess.run(
        ["gh", "api", "--paginate", "orgs/dsh-external/repos?per_page=100&type=all", "--jq", ".[].name"],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        print(f"[discover] WARN org-exclude fetch failed (fail-open): {r.stderr.strip()[:120]}", file=sys.stderr)
        return set()
    return {l.strip() for l in r.stdout.splitlines() if l.strip()}


def read_clone_pkg(name_bare: str) -> tuple[bool, str, str]:
    """Return (is_plugin, package_name, entry) from a local clone's package.json."""
    pkg = CLONES / name_bare / "package.json"
    if not pkg.is_file():
        return (False, "", "")
    try:
        d = json.loads(pkg.read_text(errors="replace"))
    except json.JSONDecodeError:
        return (False, "", "")
    name = d.get("name", "") or ""
    entry = d.get("main") or (d.get("exports") and "exports") or (d.get("dsh") and "dsh") or ""
    is_plugin = bool(name and (d.get("main") or d.get("exports") or d.get("dsh")))
    return (is_plugin, name, entry)


import time as _t
_PACE_S = 2.6                 # ≈23 req/min，为 30/min 专用搜索池留余量
_last_call = [0.0]

def _paced():
    wait = _last_call[0] + _PACE_S - _t.monotonic()
    if wait > 0:
        _t.sleep(wait)
    _last_call[0] = _t.monotonic()

def gh_count(q: str) -> "int | None":
    """count 探测（per_page=1 取 total_count），走专用搜索身份。"""
    import urllib.parse
    _paced()
    _env = dict(os.environ)
    if SEARCH_TOKEN:
        _env["GH_TOKEN"] = SEARCH_TOKEN
    r = subprocess.run(
        ["gh", "api", f"search/repositories?q={urllib.parse.quote(q)}&per_page=1", "--jq", ".total_count"],
        capture_output=True, text=True, timeout=60, env=_env)
    if r.returncode != 0 or not r.stdout.strip().isdigit():
        print(f"[discover] count FAILED {q[:70]}: {r.stderr.strip()[:120]}", file=sys.stderr)
        return None
    return int(r.stdout.strip())

def collect_shard(label, q_core, lo, hi, shard_log, saturated):
    """递归分片采集：返回 [(label, item)]。超限二分时间窗；窗<1天仍超→饱和（尽力拉取并标记）。"""
    import datetime as _dt, urllib.parse
    q = f"{q_core} created:{lo.isoformat()}..{hi.isoformat()}"
    cnt = gh_count(q)
    if cnt is None:
        return []
    full = gh(f"search/repositories?q={urllib.parse.quote(q)}&per_page=100", ".items[]", token=SEARCH_TOKEN) \
        if cnt <= SAT_LIMIT or (hi - lo).days <= 1 else None  # 单日窗不再二分（防零宽死循环）
    if full is not None:
        print(f"[discover] shard ok label={label} count={cnt} q={q[:90]}", flush=True)
        shard_log.setdefault(label, []).append({"q": q, "count": cnt,
                                               "saturated": cnt > SAT_LIMIT})
        if cnt > SAT_LIMIT:
            saturated.append({"label": label, "q": q, "total": cnt})
            print(f"[discover] SATURATED {q[:70]} total={cnt} (下界)", file=sys.stderr)
        return [(label, it) for it in full]
    mid = lo + _dt.timedelta(days=(hi - lo).days // 2)
    return (collect_shard(label, q_core, lo, mid, shard_log, saturated)
            + collect_shard(label, q_core, mid, hi, shard_log, saturated))


def scan_bundles_and_code(by_id: dict, npm_pkg_names: list) -> None:
    """P5 代码搜索 + 整合包识别（2026-08-27）。
    a) filename:cordis.yml/yaml、dsh.bundle 代码搜索——抓无 topic 无 npm 的真插件仓；
    b) npm 包 dependencies 含 >=2 个 dsh 系包 → 整合包，写 bundles.json sidecar。"""
    import datetime as _dt
    code_seen = {}
    for q in CODE_SEEDS:
        try:
            items = gh(f"/search/code?q={quote(q)}", ".items[].repository",
                       timeout=60, token=SEARCH_TOKEN)
        except Exception as e:
            print(f"[discover] code search failed: {q}: {e}", file=sys.stderr)
            continue
        for r in items or []:
            full = (r.get("full_name") or "").strip()
            if not full or full.lower().startswith("dsh-external/"):
                continue
            code_seen[full.lower()] = {"full_name": full, "id": r.get("id"),
                                       "url": r.get("html_url") or f"https://github.com/{full}",
                                       "node_id": r.get("node_id") or "",
                                       "sources": ["code"]}
        time.sleep(7)  # code search ~10 req/min
    have = {str(v.get("full_name", "")).lower() for v in by_id.values()}
    added = 0
    for _k, r in code_seen.items():
        if _k not in have:
            key = r["node_id"] or ("github:%s" % r.get("id") or _k)
            by_id[key] = r
            added += 1
    print(f"[discover] code-search: 命中 {len(code_seen)} 仓，新增 {added}", file=sys.stderr)

    bundles = {}
    for name in npm_pkg_names[:400]:
        doc = npm_get(f"https://registry.npmjs.org/{quote(name)}")
        if not doc:
            continue
        deps = set((doc.get("dependencies") or {}).keys())
        subs = sorted(d for d in deps if re.search(r"dsh[-_]|dsh-plugin", d, re.I))
        if len(subs) >= BUNDLE_MIN_SUBS:
            bundles[name] = {"subs": subs[:50], "via": "npm-deps"}
        time.sleep(0.2)
    try:
        (ROOT / "generated/current/bundles.json").write_text(json.dumps(
            {"generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
             "bundles": bundles}, ensure_ascii=False, indent=1))
    except OSError:
        pass
    print(f"[discover] 整合包识别: {len(bundles)} 个 → bundles.json", file=sys.stderr)


def main() -> int:
    _lf = open(ROOT / ".discover.lock", "w")
    try:
        fcntl.flock(_lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("[discover] another run holds the lock — exiting", file=sys.stderr)
        return 0
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pipeline = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True,
    ).stdout.strip() or "unknown"

    # --- P1 + P2: network discovery, merged by numeric id ---
    by_id: dict[str, dict] = {}
    source_counts = {"org": 0, "topic": 0, "keyword": 0, "clones": 0, "research": 0}
    import datetime as _dt2
    shard_log: dict = {}
    saturated: list = []
    _lo = _dt2.date(*SEARCH_EPOCH)
    _hi = _dt2.date.today() + _dt2.timedelta(days=1)
    _collected: list = []
    for label, q_core in SEEDS:
        _collected.extend(collect_shard(label, q_core, _lo, _hi, shard_log, saturated))
    if saturated:
        print(f"[discover] 本轮含 {len(saturated)} 个饱和分片：候选总量为下界非真值", file=sys.stderr)
    _by_label: dict = {}
    for label, it in _collected:
        _by_label.setdefault(label, []).append(it)
    for label, items in _by_label.items():
        source_counts[label] = source_counts.get(label, 0) + len(items)
        for it in items:
            rid = it.get("id")
            if not rid:
                continue
            key = f"github:{rid}"
            entry = by_id.setdefault(key, {
                "id": key, "full_name": it.get("full_name", ""), "url": it.get("html_url", ""),
                "description": it.get("description") or "", "archived": bool(it.get("archived")),
                "fork": bool(it.get("fork")), "stars": it.get("stargazers_count", 0),
                "updated_at": it.get("updated_at", ""), "topics": it.get("topics", []) or [],
                "sources": [], "is_plugin": "unknown", "package": {}, "has_research_note": False,
                "support": "", "evidence": {},
            })
            if label not in entry["sources"]:
                entry["sources"].append(label)
            # keep richest full_name/description seen
            if not entry["full_name"] and it.get("full_name"):
                entry["full_name"] = it["full_name"]

    noise_re = re.compile(r"dshow|direct\s*show", re.I)
    _before = len(by_id)
    by_id = {k: v for k, v in by_id.items()
             if not noise_re.search((v.get("full_name") or "") + " " + (v.get("description") or ""))}
    _noise = _before - len(by_id)
    if _noise:
        print(f"[discover] blacklist dropped {_noise} dshow/directshow noise candidates")

    org_names = org_repo_names()
    if org_names:
        before = len(by_id)
        by_id = {k: v for k, v in by_id.items() if not v["full_name"].startswith("dsh-external/")}
        dropped = before - len(by_id)
        if dropped:
            print(f"[discover] excluded {dropped} dsh-external org (private) candidates")
    source_counts["org"] = 0  # org branch removed by policy; key kept for stream compat

    any_network = any(c for k, c in source_counts.items() if k in ("org", "topic", "keyword"))
    if not any_network:
        print("[discover] ALL network paths failed — fail closed (no candidates written)", file=sys.stderr)
        return 20

    # --- P3: local library cross-reference (clones + research + support) ---
    research_bares = {p.stem for p in RESEARCH.glob("*.md")}
    support = {}
    if SUPPORT.is_file():
        try:
            support = json.loads(SUPPORT.read_text())
        except json.JSONDecodeError:
            pass

    # --- P4: registry feed（PLUGINS.md 手动登记 = 必检；PR 登记不再依赖搜索撞车） ---
    reg_added = 0
    reg_tagged = 0
    reg_md = ROOT / "PLUGINS.md"
    # 登记表单文件同步：镜像仓 AdamPlatin123/awesome-dsh-plugins main 的 PLUGINS.md 是权威登记表（社区登记 PR 的合并处；2026-08-27 决策）。
    # 只覆盖此一个文件，不整仓 pull（本仓 scripts/ 等另有本地修改）；fetch 失败降级用本地旧表。
    _sync = subprocess.run(
        ["git", "-C", str(ROOT), "fetch", "-q", "origin", "main"],
        capture_output=True, text=True, timeout=60)
    if _sync.returncode == 0:
        _show = subprocess.run(
            ["git", "-C", str(ROOT), "show", "origin/main:PLUGINS.md"],
            capture_output=True, text=True, timeout=30)
        if _show.returncode == 0 and _show.stdout.strip():
            reg_md.write_text(_show.stdout, encoding="utf-8")
        else:
            print("[discover] registry sync: show 失败，用本地登记表", file=sys.stderr)
    else:
        print(f"[discover] registry sync: fetch 失败（{_sync.stderr.strip()[:60]}），用本地登记表", file=sys.stderr)
    if reg_md.is_file():
        reg_names = sorted({m for m in re.findall(
            r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", reg_md.read_text())
            if m.split("/")[0].lower() not in ("topics", "dsh-external")})
        by_full = {v["full_name"].lower(): v for v in by_id.values()}
        for full in reg_names:
            v = by_full.get(full.lower())
            if v is not None:
                if "registry" not in v["sources"]:
                    v["sources"].append("registry")
                    reg_tagged += 1
                continue
            r = subprocess.run(
                ["gh", "api", f"repos/{full}", "--jq",
                 '{id: .id, full_name: .full_name, html_url: .html_url, description: .description,'
                 ' archived: .archived, fork: .fork, stars: .stargazers_count,'
                 ' updated_at: .updated_at, topics: .topics}'],
                capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                print(f"[discover] registry fetch failed: {full}: {r.stderr.strip()[:80]}", file=sys.stderr)
                continue
            try:
                it = json.loads(r.stdout)
            except json.JSONDecodeError:
                continue
            rid = it.get("id")
            if not rid:
                continue
            key = f"github:{rid}"
            by_id.setdefault(key, {
                "id": key, "full_name": it.get("full_name", ""), "url": it.get("html_url", ""),
                "description": it.get("description") or "", "archived": bool(it.get("archived")),
                "fork": bool(it.get("fork")), "stars": it.get("stars", 0),
                "updated_at": it.get("updated_at", ""), "topics": it.get("topics", []) or [],
                "sources": ["registry"], "is_plugin": True, "package": {},
                "has_research_note": False, "support": "", "evidence": {},
            })
            reg_added += 1
    source_counts["registry"] = sum(1 for v in by_id.values() if "registry" in v["sources"])
    if reg_added or reg_tagged:
        print(f"[discover] registry: tagged {reg_tagged} searched + added {reg_added} missed-by-search")

    # --- P4b: npm registry cross-discovery（#189：GitHub 搜索 1000/查询上限外的交叉路）---
    # keywords:dsh-plugin 主路 + name:dsh-* 辅路；package.repository 映射回 GitHub owner/repo，
    # 按既有 numeric-id 键去重合并，来源标 npm。npm 属辅路：失败仅告警，不参与 fail-closed 判定。
    npm_added = 0
    npm_tagged = 0
    npm_seen: set[str] = set()
    npm_pkg_names: list[str] = []
    by_full = {v["full_name"].lower(): v for v in by_id.values()}
    for _text in ("keywords:dsh-plugin", "name:dsh-*"):
        for _off in range(0, 4000, 250):
            if npm_added >= 400:
                print("[discover] npm: 新增达 400 上限，剩余留待下轮", file=sys.stderr)
                break
            page = npm_get(f"https://registry.npmjs.org/-/v1/search?text={quote(_text)}&size=250&from={_off}")
            if page is None:
                print(f"[discover] npm search failed: {_text} from={_off}", file=sys.stderr)
                break
            objs = page.get("objects") or []
            for o in objs:
                pkg = o.get("package") or {}
                link = ((pkg.get("links") or {}).get("repository") or "").strip()
                m = re.match(r"(?:git\+)?https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$", link)
                if not m:
                    continue
                full = f"{m.group(1)}/{m.group(2)}"
                if full.lower() in npm_seen:
                    continue
                npm_seen.add(full.lower())
                if pkg.get("name"):
                    npm_pkg_names.append(pkg["name"])
                v = by_full.get(full.lower())
                if v is not None:
                    if "npm" not in v["sources"]:
                        v["sources"].append("npm")
                        npm_tagged += 1
                    if pkg.get("name") and not v.get("package", {}).get("name"):
                        v["package"] = {"name": pkg["name"], "entry": v.get("package", {}).get("entry", "")}
                    continue
                r = subprocess.run(
                    ["gh", "api", f"repos/{full}", "--jq",
                     '{id: .id, full_name: .full_name, html_url: .html_url, description: .description,'
                     ' archived: .archived, fork: .fork, stars: .stargazers_count,'
                     ' updated_at: .updated_at, topics: .topics}'],
                    capture_output=True, text=True, timeout=30)
                if r.returncode != 0:
                    print(f"[discover] npm fetch failed: {full}: {r.stderr.strip()[:80]}", file=sys.stderr)
                    continue
                try:
                    it = json.loads(r.stdout)
                except json.JSONDecodeError:
                    continue
                rid = it.get("id")
                if not rid:
                    continue
                key = f"github:{rid}"
                v2 = by_id.get(key)
                if v2 is not None:
                    if "npm" not in v2["sources"]:
                        v2["sources"].append("npm")
                        npm_tagged += 1
                    continue
                by_id[key] = {
                    "id": key, "full_name": it.get("full_name", ""), "url": it.get("html_url", ""),
                    "description": it.get("description") or "", "archived": bool(it.get("archived")),
                    "fork": bool(it.get("fork")), "stars": it.get("stars", 0),
                    "updated_at": it.get("updated_at", ""), "topics": it.get("topics", []) or [],
                    "sources": ["npm"], "is_plugin": True,
                    "package": {"name": pkg.get("name", ""), "entry": ""},
                    "has_research_note": False, "support": "", "evidence": {},
                }
                by_full[it.get("full_name", "").lower()] = by_id[key]
                npm_added += 1
            if len(objs) < 250:
                break
            time.sleep(1)
    source_counts["npm"] = sum(1 for v in by_id.values() if "npm" in v["sources"])
    if npm_added or npm_tagged:
        print(f"[discover] npm: tagged {npm_tagged} known + added {npm_added} missed-by-search")

    seen_bares = {bare(v["full_name"]) for v in by_id.values()}
    for v in by_id.values():
        b = bare(v["full_name"])
        if CLONES and (CLONES / b).is_dir():
            if "clones" not in v["sources"]:
                v["sources"].append("clones")
            is_plug, pname, entry = read_clone_pkg(b)
            v["is_plugin"] = is_plug if is_plug else v["is_plugin"]
            if pname:
                v["package"] = {"name": pname, "entry": entry}
        if b in research_bares:
            v["has_research_note"] = True
            if "research" not in v["sources"]:
                v["sources"].append("research")
        if b in support:
            v["support"] = support[b].get("support", "")

    source_counts["clones"] = sum(1 for v in by_id.values() if "clones" in v["sources"])
    source_counts["research"] = sum(1 for v in by_id.values() if "research" in v["sources"])

    # local-only clones/research not surfaced by network (offline resilience + completeness)
    for d in CLONES.glob("*/") if CLONES.is_dir() else []:
        b = d.name
        if b in seen_bares or b in org_names:
            continue
        is_plug, pname, entry = read_clone_pkg(b)
        if not is_plug:
            continue  # clones holds non-plugins too; only carry installable ones as candidates
        # numeric id unknown without network — keyed by clone name with a sentinel
        key = f"github:unknown:{b}"
        by_id.setdefault(key, {
            "id": key, "full_name": b, "url": "", "description": "", "archived": False,
            "fork": False, "stars": 0, "updated_at": "", "topics": [], "sources": ["clones"],
            "is_plugin": True, "package": {"name": pname, "entry": entry},
            "has_research_note": b in research_bares, "support": support.get(b, {}).get("support", ""),
            "evidence": {},
        })

    candidates = sorted(by_id.values(), key=lambda x: x["full_name"].lower())
    doc = {
        "run_id": run_id, "observed_at": observed_at, "pipeline_commit": pipeline,
        "source_counts": source_counts,
        "sources_queried": [q for _, q in SEEDS] + ["library:research", "library:clones", "npm:keywords:dsh-plugin", "npm:name:dsh-*"],
        "search_shards": {"queries": sum(len(v) for v in shard_log.values()),
                         "saturated": len(saturated), "details": saturated[:20]},
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    # 审计修复（SOP §8.1 缩水保护）：keyword 全灭或总量骤降 → 不覆盖旧版，写 partial
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text())
            prev_n = prev.get("candidate_count", 0)
            prev_kw = prev.get("source_counts", {}).get("keyword", 0)
            cur_kw = source_counts.get("keyword", 0)
            if (prev_kw > 0 and cur_kw == 0) or (prev_n and len(candidates) < prev_n * DISCOVER_PARTIAL_RATIO):
                part = OUT.with_name("candidates.partial.json")
                doc["_partial_reason"] = f"shrink {prev_n}->{len(candidates)} keyword {prev_kw}->{cur_kw}"
                part.write_text(json.dumps(doc, ensure_ascii=False, indent=2))
                print(f"[discover] FAIL CLOSED：缩水（{prev_n}->{len(candidates)}，keyword {prev_kw}->{cur_kw}），保留旧版 → {part.name}", file=sys.stderr)
                return 25
        except Exception:
            pass
    scan_bundles_and_code(by_id, npm_pkg_names)
    atomic_write_json(OUT, doc)   # P3：唯一原子写（原 tmp+replace 手写副本）
    print(f"[discover] {len(candidates)} candidates → {OUT.relative_to(ROOT)}")
    print(f"[discover] sources: {source_counts}")
    unknown = sum(1 for c in candidates if c["id"].startswith("github:unknown:"))
    if unknown:
        print(f"[discover] {unknown} clone-only candidates lack a numeric id (network incomplete); they stay candidate, never listed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
