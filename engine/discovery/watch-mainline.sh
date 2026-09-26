#!/usr/bin/env bash
# 高频 watcher：每 30 分钟检测核心 repo（mainline 快照）更新，变化即触发全量索引
# 轻量：仅 ls-remote 最新快照分支对比，无变化零成本
set -uo pipefail
REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"   # engine/discovery → 仓库根
cd "$REPO_DIR" || exit 2
STATE=".watch-mainline.state"
SNAP="$(timeout 30 git ls-remote https://github.com/dsh2026/test-AdamPlatin123 "refs/heads/snapshots/*" 2>/dev/null | sort -k2 | tail -1 | awk '{print $1}')"
[ -z "$SNAP" ] && { echo "[watch] 离线，跳过"; exit 0; }
PREV="$(cat "$STATE" 2>/dev/null || echo "")"
if [ "$SNAP" != "$PREV" ]; then
  echo "[watch] 核心 repo 更新（$PREV → $SNAP）→ 触发全量"
  echo "$SNAP" > "$STATE"
  # flock 与 cron 班互斥；后台执行
  LOCK_FD=9
  exec 9>/tmp/dsh-cron-check.lock
  if flock -n 9; then
    setsid nohup bash -lc "cd '$REPO_DIR' && engine/discovery/cron-check.sh --full" >> logs/watch.log 2>&1 < /dev/null &
    flock -u 9
  else
    echo "[watch] 已有索引在跑，跳过"
  fi
else
  echo "[watch] 无变化"
fi
exit 0
