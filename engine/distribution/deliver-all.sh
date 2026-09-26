#!/usr/bin/env bash
# deliver-all.sh — 拷结果 → 聚合 → 推个人仓库 → bot PR/update 到 awesome-dsh-plugins。可重复执行（同日 PR 幂等更新）。
set -uo pipefail
export PATH=$HOME/.local/bin:$PATH
RADAR=$HOME/dsh-plugin-radar; SRC=$HOME/dsh-external-research
cd "$RADAR"
rsync -a --delete "$SRC/.rt-agent/" "$RADAR/.rt-agent/"
python3 scripts/aggregate-agent-test.py
# 显式 allowlist（SOP：禁 git add -A，防日志/临时/密钥入库——cron-check.sh 同款禁令）
git add -- .rt-agent
[ -d reports ] && git add -- reports
git -c user.name=AdamPlatin123 -c user.email=adam@local commit -q -m "agent-test: 结果更新 $(date +%F_%H:%M)（流式 pipeline / 重试2）" && git push -q origin main \
  && echo "[deliver-all] 个人仓库已推 $(date -Is)" || echo "[deliver-all] 个人仓库无变化或推送失败"
bash ~/dsh-k8s/bot-deliver.sh
