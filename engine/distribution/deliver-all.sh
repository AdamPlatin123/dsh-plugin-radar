#!/usr/bin/env bash
# deliver-all.sh — 拷结果 → 聚合 → 推个人仓库 → bot PR/update 到 awesome-dsh-plugins。可重复执行（同日 PR 幂等更新）。
set -uo pipefail
export PATH=$HOME/.local/bin:$PATH
RADAR=$HOME/dsh-plugin-radar; SRC=$HOME/dsh-external-research
cd "$RADAR"
rsync -a --delete "$SRC/.rt-agent/" "$RADAR/.rt-agent/"
if [ -f "$SRC/scripts/aggregate-agent-test.py" ]; then
  python3 "$SRC/scripts/aggregate-agent-test.py"
else echo "[deliver-all] WARN 缺私有聚合器 aggregate-agent-test.py，跳过聚合（engine/ops/private/MANIFEST.md）"; fi
# 显式 allowlist（SOP：禁 git add -A，防日志/临时/密钥入库——cron-check.sh 同款禁令）
git add -- .rt-agent
[ -d reports ] && git add -- reports
git -c user.name=AdamPlatin123 -c user.email=adam@local commit -q -m "agent-test: 结果更新 $(date +%F_%H:%M)（流式 pipeline / 重试2）" && git push -q origin main \
  && echo "[deliver-all] 个人仓库已推 $(date -Is)" || echo "[deliver-all] 个人仓库无变化或推送失败"
K8S="${RADAR_K8S_DIR:-$HOME/dsh-k8s}"
if [ -f "$K8S/bot-deliver.sh" ]; then bash "$K8S/bot-deliver.sh";
else echo "[deliver-all] WARN 缺私有件 bot-deliver.sh，跳过 bot 交付"; fi
