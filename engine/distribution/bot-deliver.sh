#!/usr/bin/env bash
# bot-deliver.sh — 把 agent 测试结果以 bot PR 送到 dsh-external/awesome-dsh-plugins（不直推 main）。
# 用独立 worktree，不干扰 ~/dsh-external-research 的未提交 WIP。
set -uo pipefail
export PATH=$HOME/.local/bin:$PATH
RADAR=$HOME/dsh-plugin-radar
FRONT=$HOME/dsh-external-research
WT=/tmp/front-deliver
DATE=$(date +%F)
BR="bot/agent-test-$DATE"

cd "$RADAR"
# 确保已聚合（幂等）
if [ -f scripts/aggregate-agent-test.py ]; then python3 scripts/aggregate-agent-test.py >/dev/null 2>&1 || true;
else echo "[deliver] WARN 缺私有聚合器 aggregate-agent-test.py，跳过（engine/ops/private/MANIFEST.md）"; fi
REPORT="$RADAR/reports/$DATE/agent-test.md"
[ -f "$REPORT" ] || { echo "[deliver] 报告不存在: $REPORT"; exit 1; }

# 汇总数（写进 PR 描述）
SUMMARY=$(python3 - << "PY"
import json
d=json.load(open("generated/current/agent-results.json"))
res=d["results"]
fail=[r for r in res if r["category"]=="fail"]
clean=[r for r in fail if (r["last_error"] or "").strip().upper().startswith("FAIL")]
print("总 %d：✅可用 %d / ❌真不兼容 %d / ⚠️待定 %d"%(len(res),d["counts"]["pass"],len(clean),len(fail)-len(clean)))
# 流水线阶段快照（README 修改参考 · 与看板六段卡同源同口径）
import pathlib
def _tail(n):
    q = pathlib.Path.home() / ("dsh-k8s/metrics/%s.jsonl" % n)
    if not q.exists():
        return {}
    last = None
    for ln in q.read_text(errors="ignore").splitlines()[-5:]:
        if ln.strip():
            try:
                last = json.loads(ln)
            except Exception:
                pass
    return last or {}
ds, cl, ts, vs, dlv = _tail("discover"), _tail("clone"), _tail("test"), _tail("verdict"), _tail("deliver")
f_ = lambda x: "—" if x is None else x
print()
print("流水线阶段快照（README 修改参考 · 指标流 60s 采样）：")
print("① 搜索发现: 候选 %s（org %s · topic %s）· 缩水保护 %s · src: candidates.json · gh api" % (
    f_(ds.get("candidates")), f_(ds.get("org")), f_(ds.get("topic")),
    "触发" if ds.get("partial_flagged") else "未触发"))
print("② 克隆: %s（非插件 %s 已清 · 失败记录 %s）· src: .clones/ 目录实数" % (
    f_(cl.get("clones")), f_(cl.get("nonplugin")), f_(cl.get("fail_entries"))))
print("③ 验证: %s 个 dsh 插件（package.json name+entry）· src: .verified/ 标记文件" % f_(cl.get("plugins")))
print("④ k8s 测试: 完成 %s · 失败 %s · 累计派发 %s · src: kubectl 直查 · 独立于 driver" % (
    f_(ts.get("succeeded")), f_(ts.get("failed")), f_(ts.get("dispatched_total"))))
print("⑤ 判定: ✅%s / ❌%s / ⚠️%s · 总 %s · ⚠️占比 %s%% · src: .rt-agent/*.json 逐条" % (
    f_(vs.get("pass")), f_(vs.get("fail")), f_(vs.get("inc")), f_(vs.get("total")),
    round(vs.get("inc", 0) * 100 / vs["total"]) if vs.get("total") else "—"))
print("⑥ 交付: 本周期增量 %s/100 · open bot PR %s · src: last-delivered.json + gh pr 实查" % (
    f_(dlv.get("delta_since")), f_(dlv.get("open_bot_prs"))))

bd = d.get("by_domain") or {}
if bd:
    print()
    print("分类统计（README 功能领域，已测交集）：")
    for k, v in bd.items():
        warn = v.get("total",0) - v.get("pass",0) - v.get("fail",0)
        print("- %s：已测 %d（✅%d ❌%d ⚠️%d）" % (k, v.get("total",0), v.get("pass",0), v.get("fail",0), warn))
PY
)

# 独立 worktree，基于 dsh-ext/main 建分支
git -C "$FRONT" fetch dsh-ext main -q
SNAPSHOT_MODE=0
if git -C "$FRONT" cat-file -e "dsh-ext/main:scripts/render-readme-from-snapshot.py" 2>/dev/null; then
  SNAPSHOT_MODE=1
  echo "[deliver] 快照模式：main 已有 Bot B 渲染 workflow —— README/CHANGELOG/图 交由渲染 PR"
fi
git -C "$FRONT" fetch dsh-ext "+refs/heads/bot/*:refs/remotes/dsh-ext/bot/*" -q 2>/dev/null || true
rm -rf "$WT"
git -C "$FRONT" worktree prune 2>/dev/null || true
git -C "$FRONT" worktree add --detach "$WT" dsh-ext/main -q 2>/dev/null || { echo "[deliver] worktree 创建失败"; exit 1; }
cd "$WT"
git checkout -q -B "$BR"

mkdir -p "reports/$DATE"
cp "$REPORT" "reports/$DATE/agent-test.md"

# 文档数值面同步：CHANGELOG 运行级条目 + README 运行级实测行/链接（幂等：分支每次从 main 重建）
if [ "$SNAPSHOT_MODE" = 0 ]; then
python3 - "$DATE" << "DOC" || echo "[deliver] WARN 文档面同步失败（不影响报告交付）" >&2
import json, re, sys
from pathlib import Path
date = sys.argv[1]
d = json.loads(Path.home().glob("dsh-plugin-radar/generated/current/agent-results.json").__next__().read_text())
res = d["results"]
fail = [r for r in res if r["category"] == "fail"]
clean = [r for r in fail if (r.get("last_error") or "").strip().upper().startswith("FAIL")]
inc = len(fail) - len(clean)
total, npass = len(res), d["counts"]["pass"]

# 1) CHANGELOG：顶部插运行级条目（若 main 里已有同日运行级条目则跳过）
cl = Path("CHANGELOG.md")
if cl.exists():
    txt = cl.read_text()
    entry = (
        "## %s（运行级）\n"
        "- 运行级实测：总 %d：✅可用 %d / ❌真不兼容 %d / ⚠️待定 %d（k8s agent · dsh+Qwen · 公有生态口径）\n"
        "- 报告：[agent-test.md](reports/%s/agent-test.md)\n\n"
    ) % (date, total, npass, len(clean), inc, date)
    if "## %s（运行级）" % date not in txt:
        cl.write_text(entry + txt)

# 2) README：运行级实测行 + 运行实测链接
rd = Path("README.md")
if rd.exists():
    t = rd.read_text()
    t = re.sub(r"\| 运行级实测 \| [^|]*\|",
               "| 运行级实测 | ✅%d 可用 · %d 不兼容 · %d 待定（共 %d 个，k8s agent 口径）|" % (npass, len(clean), inc, total),
               t, count=1)
    t = re.sub(r"\[运行实测\]\(reports/[0-9-]+/[^)]*\)",
               "[运行实测](reports/%s/agent-test.md)" % date, t, count=1)
    rd.write_text(t)
DOC
fi  # SNAPSHOT_MODE=0 时跳过直改（Bot B 负责）
# PR 模板加 bot 豁免声明（幂等；随分支评审，不直推 main）
TPL=".github/PULL_REQUEST_TEMPLATE.md"
if [ -f "$TPL" ] && ! grep -q "Awesome-Radar-Bot" "$TPL"; then
  python3 - "$TPL" << "TPLDOC"
import sys
from pathlib import Path
f = Path(sys.argv[1])
t = f.read_text()
line = ("> 🤖 **bot 报告 PR 豁免**：`[Awesome-Radar-Bot]` 开头的运行级测试报告 PR 不适用本模板——"
        "走 reports/ 交付口径，正文自带统计、分类与来源，合并与否人工决定。\n\n")
i = t.find("-->")
f.write_text(t[:i + 3] + "\n" + line + t[i + 3:] if i >= 0 else line + t)
TPLDOC
  git add "$TPL"
fi
# 目录-运行级矛盾审计（纯新增文件；改写目录行留给人工策展）
python3 - "$DATE" << "AUDITDOC" || echo "[deliver] WARN 目录审计失败（不影响交付）" >&2
import json, re, sys
from pathlib import Path
date = sys.argv[1]

# 解析 worktree 里的 README 目录段
rows = {}
cat = None
for line in Path("README.md").read_text(errors="ignore").splitlines():
    m = re.search(r"<h3>([^<（]+)（\d+）</h3>", line)
    if m:
        cat = m.group(1).strip()
        continue
    m = re.match(r"\|\s*\[([^\]]+)\]\(([^)]*)\)\s*\|\s*([^|]*)\|\s*([^|]*)\|", line)
    if m and cat:
        rows[m.group(1).strip()] = {"cat": cat, "url": m.group(2).strip(), "verdict": m.group(4).strip()}

# 运行级结论 + 原因
rt = {}
res_file = Path.home() / "dsh-plugin-radar/generated/current/agent-results.json"
for r in json.loads(res_file.read_text())["results"]:
    rt[r["plugin"]] = r

# archived 标记（candidates.json 离线可得）
arch = set()
cand_file = Path.home() / "dsh-external-research/generated/current/candidates.json"
if cand_file.exists():
    for c in json.loads(cand_file.read_text()).get("candidates", []):
        if c.get("archived"):
            arch.add(c.get("full_name", "").split("/")[-1])

hard = [(k, v) for k, v in rows.items() if k in rt and "兼容" in v["verdict"] and rt[k]["category"] == "fail"]
good = [(k, v) for k, v in rows.items() if k in rt and ("适配" in v["verdict"] or "关注" in v["verdict"]) and rt[k]["category"] == "pass"]
arch_hits = sorted(k for k in rows if k in arch)

out = ["# 目录 × 运行级 矛盾审计（%s）" % date, "",
       "口径：README 兼容性列为静态四维编辑口径；运行级为 k8s agent 实测（公有生态）。",
       "交集 %d / 目录 %d。改写目录行属人工策展，本报告仅呈证据。" % (len([k for k in rows if k in rt]), len(rows)), "",
       "## 🔴 README 标「兼容」但运行级 ❌（%d）" % len(hard), "",
       "| 插件 | 分类 | 静态结论 | 运行级原因 |", "|---|---|---|---|"]
for k, v in hard:
    out.append("| %s | %s | %s | %s |" % (k, v["cat"], v["verdict"], (rt[k].get("last_error") or "")[:80]))
out += ["", "## 🟢 README 标「需适配/关注」但运行级 ✅（%d）" % len(good), "",
        "| 插件 | 分类 | 静态结论 |", "|---|---|---|"]
for k, v in good:
    out.append("| %s | %s | %s |" % (k, v["cat"], v["verdict"]))
if arch_hits:
    out += ["", "## ⚰ 已归档仓库仍在目录（%d）" % len(arch_hits), "", ", ".join(arch_hits)]
out += ["", "## 未覆盖", "", "目录中 %d 条无运行级数据（多为私有 org 仓，不在公有测试口径）。" % (len(rows) - len([k for k in rows if k in rt]))]
ap = Path("reports/%s/catalog-audit.md" % date)
ap.parent.mkdir(parents=True, exist_ok=True)
ap.write_text("\n".join(out) + "\n")
print("[audit] %s 矛盾: 红 %d / 绿 %d / 归档 %d" % (ap, len(hard), len(good), len(arch_hits)))
AUDITDOC
# 活数字图刷新（E 方案：拓扑=脚本常量 + 计数=指标流；失败可见不阻断）
if [ "$SNAPSHOT_MODE" = 0 ] && [ -f "$HOME/dsh-k8s/gen-pipeline-diagram.py" ]; then
  python3 "$HOME/dsh-k8s/gen-pipeline-diagram.py" README.md \
    || echo "[deliver] WARN 活数字图刷新失败（不影响交付）" >&2
fi
# Bot A：交付快照入仓（data/snapshots/，统一分类器 v1 —— Bot B 的渲染输入兼备份）
if [ -f "$HOME/dsh-k8s/gen-snapshot-catalog.py" ]; then
  python3 "$HOME/dsh-k8s/gen-snapshot-catalog.py"     || echo "[deliver] WARN 快照生成失败（不影响交付）" >&2
  git add data/snapshots/*.json 2>/dev/null || true
fi
if [ "$SNAPSHOT_MODE" = 1 ]; then
  git add "reports/$DATE/agent-test.md" "reports/$DATE/catalog-audit.md"
else
  git add "reports/$DATE/agent-test.md" "reports/$DATE/catalog-audit.md" CHANGELOG.md README.md
fi
git -c user.name=dsh-ecosystem-bot -c user.email=bot@dsh-external.local \
  commit -q -m "bot: agent 运行级测试报告 $DATE（dsh+Qwen k8s，来源 dsh-plugin-radar）"
git push -q --force-with-lease dsh-ext "$BR"

# 已有同分支 PR 则不重复开
gh pr view --repo dsh-external/awesome-dsh-plugins "$BR" >/dev/null 2>&1 || \
gh pr create --repo dsh-external/awesome-dsh-plugins \
  --base main --head "$BR" \
  --title "bot: agent 运行级测试报告 $DATE" \
  --body "$SUMMARY

来源：AdamPlatin123/dsh-plugin-radar（radar 后端，含原始结果与聚合脚本）。
PR 类别：bot 运行级测试报告（豁免插件登记模板）。\n本 PR 只含聚合报告；原始 per-plugin 结果留在后端仓库。合并与否由人工决定。" \
  && echo "[deliver] PR 已创建"


# 双仓交付：同时 PR 到个人镜像 AdamPlatin123/awesome-dsh-plugins
git push -q --force-with-lease origin "$BR" 2>/dev/null
gh pr view --repo AdamPlatin123/awesome-dsh-plugins "$BR" >/dev/null 2>&1 || \
gh pr create --repo AdamPlatin123/awesome-dsh-plugins --base main --head "$BR" \
  --title "bot: agent 运行级测试报告 $DATE" \
  --body "$SUMMARY

来源：AdamPlatin123/dsh-plugin-radar。PR 类别：bot 运行级测试报告（豁免插件登记模板）。同内容 PR：dsh-external/awesome-dsh-plugins。"

# 已有 PR 正文刷新：每次交付重算数值 + 分类表（先按 head 分支解析编号，再按编号 edit）
BODY_ORG="$SUMMARY

来源：AdamPlatin123/dsh-plugin-radar（radar 后端，含原始结果与聚合脚本）。
本 PR 只含聚合报告；原始 per-plugin 结果留在后端仓库。合并与否由人工决定。"
BODY_MIRROR="$SUMMARY

来源：AdamPlatin123/dsh-plugin-radar。PR 类别：bot 运行级测试报告（豁免插件登记模板）。同内容 PR：dsh-external/awesome-dsh-plugins。"
refresh_pr() {  # $1=repo $2=body
  N=$(gh pr list --repo "$1" --state open --head "$BR" --json number --jq ".[0].number" 2>/dev/null || true)
  if [ -n "$N" ]; then
    gh pr edit --repo "$1" "$N" --body "$2" >/dev/null 2>&1 || true
    echo "[deliver] PR 正文已刷新 $1#$N"
  fi
}
refresh_pr dsh-external/awesome-dsh-plugins "$BODY_ORG"
refresh_pr AdamPlatin123/awesome-dsh-plugins "$BODY_MIRROR"

# AUTO_MERGE_GUARD（P4b 升级）：三重身份闸门统一走 merge_guard.py——
# head SHA 钉死（捕获自本管线推送，防同名伪装分支劫持）+ 作者钉死 + 文件集合精确匹配；
# 此前仅"前缀白名单"校验，为四处实现中最弱
if [ "$SNAPSHOT_MODE" = 1 ]; then
  GUARD="$RADAR/engine/distribution/merge_guard.py"
  PUSH_SHA="$(git -C "$WT" rev-parse HEAD 2>/dev/null || true)"
  if [ -z "$PUSH_SHA" ] || [ ! -f "$GUARD" ]; then
    echo "[deliver] 无法捕获推送 SHA 或缺 merge_guard——拒绝自动合并（fail-closed，留人工）"
  else
    for R in dsh-external/awesome-dsh-plugins AdamPlatin123/awesome-dsh-plugins; do
      N=$(gh pr list --repo "$R" --state open --head "$BR" --json number --jq '.[0].number' 2>/dev/null)
      [ -n "$N" ] || continue
      python3 "$GUARD" --repo "$R" --pr "$N" --expect-sha "$PUSH_SHA" \
        --author AdamPlatin123 --expect-file 'data/snapshots/*' --expect-file 'reports/*' || true
    done
  fi
fi

cd /
git -C "$FRONT" worktree remove --force "$WT" 2>/dev/null
echo "[deliver] 完成 $SUMMARY"
