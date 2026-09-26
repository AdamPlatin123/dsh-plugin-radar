#!/usr/bin/env python3
"""cadence.py v2 — 交付节奏引擎（只读 v2，游标只在 push+PR 全部确认后推进）。

数据源：.rt-agent-v2/results（schema v2 active 结果）+ legacy ledger（仅历史展示）。
触发：首次 / 距上次 ≥24h 且有增量 / 增量 ≥100。
交付：唯一 run worktree、参数数组 git（无 shell 拼接）、显式 allowlist 暂存；
公开产物过隐私门（schema 键白名单、绝对路径、内部 URL、秘密模式）；
任一门失败 → 不提交不推进游标。个人仓 + org bot PR 全部确认后才推进 delivery cursor。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
K8S = HOME / "dsh-k8s"
REPO = HOME / "dsh-external-research"
RESULTS = REPO / ".rt-agent-v2/results"
LEGACY = REPO / ".rt-agent-v2/legacy/ledger.json"
CURSOR = K8S / "state/delivery-cursor.json"
RADAR = HOME / "dsh-plugin-radar"
DAILY = 24 * 3600
BATCH = 100
PR_REPO = "AdamPlatin123/awesome-dsh-plugins"
BOT_LOGIN = "AdamPlatin123"   # 本管线 gh 认证账号：PR 作者必须是它才允许自动合并
GH_BIN = str(Path.home() / ".local/bin/gh") if (Path.home() / ".local/bin/gh").exists() else "gh"
ALLOWED_KEYS = {"local_key", "canonical_id", "status", "evidence_kind", "observed_at", "tries"}
SECRET_RE = re.compile(
    r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----|/token/[A-Za-z0-9]{8,}")
INTERNAL_RE = re.compile(r"https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)")
PATH_RE = re.compile(r"/home/[A-Za-z0-9._-]+")


import sys as _sys
_LIB = Path(__file__).resolve().parents[1] / 'lib'
if str(_LIB) not in _sys.path:
    _sys.path.insert(0, str(_LIB))
from radar.gitops import sh   # P3：git 子进程唯一实现（push 租约式）  # noqa: E402


def read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, json.JSONDecodeError, ValueError):
        return default


from radar.atomicio import atomic_write_json as atomic_write_  # P3：唯一原子写


def atomic_write(path, obj):
    atomic_write_(path, obj)


def load_active():
    out = {}
    for p in RESULTS.glob("*.json"):
        d = read_json(p)
        if isinstance(d, dict) and d.get("schema_version") == 2:
            out[d.get("local_key", p.stem)] = d
    return out


def public_row(lk, d):
    return {k: d.get(k) for k in ALLOWED_KEYS if k in d} | {"local_key": lk}


def privacy_gate(text: str) -> str | None:
    for name, rx in (("secret", SECRET_RE), ("internal-url", INTERNAL_RE), ("path", PATH_RE)):
        m = rx.search(text)
        if m:
            return f"{name}:{m.group(0)[:40]}"
    return None


def guarded_auto_merge(repo: str, pr_no: str, wt, expect_sha: str,
                       expect_files: list, author_login: str) -> bool:
    """守卫式自动合并（P4b 起委派唯一实现 engine/distribution/merge_guard.py；
    三重身份闸门 = head SHA 钉死 + 作者钉死 + 文件集合精确相等，历史演进见该文件头注）。"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import merge_guard as _mg
    ok, reason = _mg.verify(repo, pr_no, expect_sha, {author_login}, expect_files=expect_files, gh_bin=GH_BIN)
    if not ok:
        print(f"[cadence-v2] {repo} PR #{pr_no} 拒绝自动合并：{reason} → 留人工")
        return False
    print(f"[cadence-v2] {repo} PR #{pr_no} {reason}")
    merged, m_reason = _mg.merge(repo, pr_no, expect_sha, GH_BIN)
    print(f"[cadence-v2] {repo} PR #{pr_no} {m_reason}")
    return merged


def load_bot_env():
    """加载 GitHub App 安装令牌（org 推送/PR 需要 bot 身份；个人账号无 org 写权限）。
    凭据只进进程环境，不落任何日志。"""
    env_file = Path.home() / ".radar-bot.env"
    if not env_file.exists():
        return
    try:
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()
        r = subprocess.run(["bash", str(Path.home() / "dsh-k8s/bot-app/radar-bot-token.sh")],
                           capture_output=True, text=True, timeout=30)
        tok = (r.stdout or "").strip()
        # 2026-08-15：GitHub App 安装已无 org 仓访问权（API 404）；个人令牌具备
        # org push 权限（admin），统一走已存的 gh 个人凭据。提交仍署名 Awesome-Radar-Bot。
        if tok:
            os.environ.pop("GH_TOKEN", None)
            print("[cadence-v2] credential mode: stored personal gh auth "
                  "(bot installation lost org access)")
    except Exception as e:
        print(f"[cadence-v2] bot token load failed, personal fallback: {type(e).__name__}")


ORG_REPO = "dsh-external/awesome-dsh-plugins"
FORCE = "--force" in sys.argv  # 测试/手动：跳过触发判定


def org_deliver(date: str, md_text: str, reason: str) -> bool:
    """私有 org 仓全自提：worktree -> 报告文件 -> PR -> 守卫式自动合并。
    守卫：PR 文件白名单 reports/** 之外一律不自动合并（留人工）。"""
    import shutil as _sh
    import uuid as _u
    wt = K8S / f"runs/cadence-org-{now_ts()}-{_u.uuid4().hex[:6]}"
    r = sh(["git", "worktree", "add", "--detach", str(wt), "dsh-ext/main"], cwd=REPO)
    if r.returncode != 0:
        print("[cadence-v2] org worktree failed → cursor kept")
        return False
    try:
        branch = f"bot/agent-test-v2-{date}"
        sh(["git", "checkout", "-q", "-B", branch], cwd=wt)
        target = wt / f"reports/{date}"
        target.mkdir(parents=True, exist_ok=True)
        atomic_write(target / "agent-test-v2.md", md_text)
        r = sh(["git", "add", f"reports/{date}/agent-test-v2.md"], cwd=wt)
        r = sh(["git", "-c", "user.name=Awesome-Radar-Bot",
                "-c", "user.email=radar-bot@awesome-dsh-plugins.local",
                "commit", "-q", "-m", f"bot: agent 运行级测试报告 v2 {date}"], cwd=wt)
        if r.returncode != 0:
            print("[cadence-v2] org commit failed → cursor kept")
            return False
        r = sh(["git", "push", "-q", "--force-with-lease", "dsh-ext",
                f"{branch}:{branch}"], cwd=wt, timeout=180)
        if r.returncode != 0:
            print("[cadence-v2] org push failed → cursor kept")
            return False
        # 关闭被取代的旧 org bot PR
        prs = sh([GH_BIN, "pr", "list", "--repo", ORG_REPO, "--state", "open",
                  "--json", "number,headRefName", "--limit", "20"], cwd=wt, timeout=60)
        try:
            for pr in json.loads(prs.stdout or "[]"):
                if str(pr.get("headRefName", "")).startswith("bot/agent-test-v2-") \
                        and pr.get("headRefName") != branch:
                    sh([GH_BIN, "pr", "close", str(pr["number"]), "--repo", ORG_REPO,
                        "--comment", "被当日新报告取代（v2 supersede）"], cwd=wt, timeout=60)
        except json.JSONDecodeError:
            pass
        body_file = wt / ".pr-body.txt"
        body_file.write_text(f"运行级测试报告 v2 · 触发：{reason}\n"
                             f"自动合并守卫：仅 reports/** 白名单")
        r = sh([GH_BIN, "pr", "create", "--repo", ORG_REPO, "--base", "main",
                "--head", branch,
                "--title", f"[Awesome-Radar-Bot] agent 运行级测试报告 v2 {date}",
                "--body-file", str(body_file)], cwd=wt, timeout=120)
        pr_no = ""
        if r.returncode == 0:
            pr_no = (r.stdout or "").strip().split("/")[-1]
        else:
            r2 = sh([GH_BIN, "pr", "list", "--repo", ORG_REPO, "--head", branch,
                     "--state", "open", "--json", "number", "-q", ".[0].number"],
                    cwd=wt, timeout=60)
            pr_no = (r2.stdout or "").strip()
        if not pr_no.isdigit():
            print("[cadence-v2] org PR create failed → cursor kept")
            return False
        # 统一身份闸门（与个人仓同一函数）：SHA 钉死 + 作者钉死 + 文件钉死
        head_sha = sh(["git", "rev-parse", "HEAD"], cwd=wt, timeout=30).stdout.strip()
        if not guarded_auto_merge(ORG_REPO, pr_no, wt, expect_sha=head_sha,
                                  expect_files=[f"reports/{date}/agent-test-v2.md"],
                                  author_login=BOT_LOGIN):
            return False
        return True
    finally:
        sh(["git", "worktree", "remove", "--force", str(wt)], cwd=REPO)


def now_ts():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def main() -> int:
    load_bot_env()
    now = time.time()
    cur = load_active()
    legacy = read_json(LEGACY, {"records": {}}).get("records", {})
    cursor = read_json(CURSOR, {})
    prev_keys = set(cursor.get("delivered_keys", []))
    new_keys = [k for k in cur if k not in prev_keys]
    delta = len(new_keys)
    last_t = cursor.get("time", 0)
    if FORCE:
        reason = f"forced (delta {delta})"
    elif not last_t:
        reason = "first-delivery"
    elif delta >= BATCH:
        reason = f"delta {delta} >= {BATCH}"
    elif (now - last_t) >= DAILY and delta >= 1:
        reason = f"24h with delta {delta}"
    else:
        age_h = (now - last_t) / 3600 if last_t else -1
        print(f"[cadence-v2] not due: delta={delta} age={age_h:.1f}h "
              f"active={len(cur)} legacy={len(legacy)}")
        return 0

    # ---- 聚合（隐私门内）----
    counts = {"pass": 0, "fail": 0, "inconclusive": 0, "skipped": 0}
    rows = []
    for lk, d in sorted(cur.items()):
        counts[d.get("status", "inconclusive")] = counts.get(d.get("status", "inconclusive"), 0) + 1
        rows.append(public_row(lk, d))
    aggregate = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "counts": {**counts, "total": len(cur)},
                 "legacy_records": len(legacy),
                 "results": rows}
    text = json.dumps(aggregate, ensure_ascii=False, indent=1)
    violation = privacy_gate(text)
    if violation:
        print(f"[cadence-v2] PRIVACY GATE FAILED: {violation} → delivery aborted, cursor kept")
        return 1

    date = datetime.now().strftime("%F")
    md = [f"# agent 运行级测试报告（v2）{date}",
          "", f"- 触发：{reason}",
          f"- active 结果：{len(cur)}（pass {counts['pass']} / fail {counts['fail']} / "
          f"inconclusive {counts['inconclusive']} / skipped {counts['skipped']}）",
          f"- legacy 历史记录（仅展示，不作为当前结论）：{len(legacy)}",
          "", "| 插件 | 状态 | 证据 |", "|---|---|---|"]
    for r in rows[:200]:
        md.append(f"| {r['local_key']} | {r['status']} | {r.get('evidence_kind')} |")
    md_text = "\n".join(md)
    if privacy_gate(md_text):
        print("[cadence-v2] PRIVACY GATE FAILED (markdown) → aborted")
        return 1

    # ---- 个人仓镜像 ----
    RADAR.mkdir(parents=True, exist_ok=True)
    out_dir = RADAR / "generated/current"
    out_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(out_dir / "agent-results-v2.json", aggregate)
    reports = RADAR / f"reports/{date}"
    reports.mkdir(parents=True, exist_ok=True)
    atomic_write(reports / "agent-test-v2.md", {"text": md_text} and md_text)
    r = sh(["git", "add", "generated/current/agent-results-v2.json",
            f"reports/{date}/agent-test-v2.md"], cwd=RADAR)
    if r.returncode != 0:
        print("[cadence-v2] personal repo add failed → cursor kept")
        return 1
    sh(["git", "-c", "user.name=AdamPlatin123", "-c", "user.email=adam@local",
        "commit", "-m", f"agent-test v2 cadence {date} ({reason})"], cwd=RADAR)
    r = sh(["git", "push", "-q", "origin", "main"], cwd=RADAR, timeout=180)
    if r.returncode != 0:
        print(f"[cadence-v2] personal push failed: {(r.stderr or '')[:120]} → cursor kept")
        return 1

    # ---- org bot PR（唯一 run worktree + allowlist 暂存）----
    branch = f"bot/agent-test-v2-{date}"
    wt = K8S / f"runs/cadence-{now:.0f}-{uuid.uuid4().hex[:6]}"
    r = sh(["git", "worktree", "add", "--detach", str(wt), "origin/main"], cwd=REPO)
    if r.returncode != 0:
        sh(["git", "worktree", "remove", "--force", str(wt)], cwd=REPO)
        print("[cadence-v2] worktree failed → cursor kept")
        return 1
    try:
        r = sh(["git", "checkout", "-q", "-B", branch], cwd=wt)
        target = wt / f"reports/{date}"
        target.mkdir(parents=True, exist_ok=True)
        atomic_write(target / "agent-test-v2.md", md_text)
        allowlist = [f"reports/{date}/agent-test-v2.md"]
        r = sh(["git", "add", *allowlist], cwd=wt)
        r = sh(["git", "-c", "user.name=Awesome-Radar-Bot",
                "-c", "user.email=radar-bot@awesome-dsh-plugins.local",
                "commit", "-q", "-m", f"bot: agent 运行级测试报告 v2 {date}"], cwd=wt)
        if r.returncode != 0:
            print("[cadence-v2] org commit failed → cursor kept")
            return 1
        # bot 报告分支为可弃产物（v1 同语义）：推到 PR 目标仓（origin=个人仓），
        # PR 必须开在分支实际所在的仓库
        r = sh(["git", "push", "-q", "--force-with-lease", "origin",
                f"{branch}:{branch}"], cwd=wt, timeout=180)
        if r.returncode != 0:
            print("[cadence-v2] org push failed → cursor kept")
            return 1
        body_file = wt / ".pr-body.txt"
        body_file.write_text(f"总 {len(cur)}：pass {counts['pass']} / fail {counts['fail']} / "
                             f"待定 {counts['inconclusive']}\n触发：{reason}\n新增 {delta}\n"
                             f"legacy 历史展示 {len(legacy)} 条（evidence_kind=legacy-unpinned）")
        r = sh([GH_BIN, "pr", "create", "--repo", PR_REPO, "--base", "main",
                "--head", branch, "--title", f"[Awesome-Radar-Bot] agent 运行级测试报告 v2 {date}",
                "--body-file", str(body_file)], cwd=wt, timeout=120)
        pr_no = (r.stdout or "").strip().split("/")[-1] if r.returncode == 0 else ""
        if not pr_no.isdigit():
            # 可能已存在同分支 PR —— 查证后视为待合并目标
            r2 = sh([GH_BIN, "pr", "list", "--repo", PR_REPO, "--head", branch,
                     "--state", "open", "--json", "number", "-q", ".[0].number"], cwd=wt, timeout=60)
            pr_no = (r2.stdout or "").strip()
        if not pr_no.isdigit():
            print("[cadence-v2] PR create failed → cursor kept")
            return 1
        # 个人仓同样守卫式自动合并（2026-08-16 用户决策，取代旧「人工决定」；
        # 身份闸门：仅当 PR head == 本管线刚推的 commit、作者 == 认证账号、文件 == 产物）
        head_sha = sh(["git", "rev-parse", "HEAD"], cwd=wt, timeout=30).stdout.strip()
        if not guarded_auto_merge(PR_REPO, pr_no, wt, expect_sha=head_sha,
                                  expect_files=[f"reports/{date}/agent-test-v2.md"],
                                  author_login=BOT_LOGIN):
            return 1
    finally:
        sh(["git", "worktree", "remove", "--force", str(wt)], cwd=REPO)

    # 私有 org 仓全自提（PR + 守卫式自动合并）；失败则游标保持，下轮重试
    if not org_deliver(date, md_text, reason):
        return 1

    atomic_write(CURSOR, {"time": now, "delivered_keys": sorted(cur.keys()),
                          "reason": reason, "counts": counts,
                          "delivered_at": datetime.now(timezone.utc).isoformat()})
    print(f"[cadence-v2] delivered: {reason}; active={len(cur)} delta={delta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
