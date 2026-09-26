#!/usr/bin/env bash
# 远程 omp/模型消耗监控（每日）：
#   1. 尝试读远程 ~/.omp/agent/agent.db 的 usage_history（订阅额度 used_fraction 趋势）
#   2. 库损坏 → 报告告警（不阻塞）
#   3. 记录本监控链 dsh 冒烟用量（logs/ 中 dsh run 的 usage 痕迹）
# 输出：reports/<日期>/omp-usage.md
# 用法：monitor-usage.sh（cron 每日 02:10 调用）
set -uo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR" || exit 2
DATE="$(date +%Y-%m-%d)"
LOG_DIR="$REPO_DIR/logs"

USAGE_STATE=""
DB_STATUS=""
declare -a PROVIDER_ROWS=()

# 1. 尝试读远程 usage_history（订阅额度）
python3 - "$REPO_DIR" > "$LOG_DIR/usage-read.txt" 2>&1 << 'PYEOF'
import sqlite3, sys
repo = sys.argv[1]
import os as _os
dbp = _os.environ.get("RADAR_LEGACY_KEY_DB") or _os.path.expanduser("~/.omp/agent/agent.db")
try:
    db = sqlite3.connect(dbp)
    ok = db.execute("PRAGMA integrity_check").fetchone()[0]
    if ok != "ok":
        print(f"DB_CORRUPT {ok}")
        sys.exit(0)
    rows = db.execute(
        "SELECT recorded_at, provider, label, used_fraction, status FROM usage_history ORDER BY recorded_at DESC LIMIT 10"
    ).fetchall()
    for r in rows:
        print(f"{r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]}")
except Exception as e:
    print(f"DB_ERROR {e}")
PYEOF
if grep -q "DB_CORRUPT\|DB_ERROR" "$LOG_DIR/usage-read.txt" 2>/dev/null; then
  DB_STATUS="⚠️ 远程 agent.db 损坏/不可读（$(head -1 "$LOG_DIR/usage-read.txt")）"
else
  DB_STATUS="✅ 可读（$(wc -l < "$LOG_DIR/usage-read.txt") 条最近记录）"
  while IFS= read -r line; do PROVIDER_ROWS+=("$line"); done < "$LOG_DIR/usage-read.txt"
fi

# 2. 本监控链 dsh 冒烟记录（从 cron 日志找 dsh run 痕迹——当前仅手动，记录计数）
SMOKE_COUNT="$(grep -l "dsh run\|计算 .*只回" "$LOG_DIR"/cron-*.log 2>/dev/null | wc -l)"
LAST_BUILD="$(grep -m1 "构建.*完成" "$LOG_DIR/build.log" 2>/dev/null | tail -1 || echo 无)"

# 3. 写报告
REPORT="$REPO_DIR/reports/$DATE/omp-usage.md"
mkdir -p "$REPO_DIR/reports/$DATE"
{
  echo "# 对端服务器模型消耗报告（$DATE）"
  echo ""
  echo "## 远程 omp 订阅额度"
  echo ""
  echo "- 状态：$DB_STATUS"
  echo ""
  if [ ${#PROVIDER_ROWS[@]} -gt 0 ]; then
    echo "| 记录时间 | provider | 标签 | 已用比例 | 状态 |"
    echo "|---|---|---|---|---|"
    for r in "${PROVIDER_ROWS[@]:-}"; do
      echo "| $(printf '%s' "$r" | sed 's/ | / | /g') |"
    done
  fi
  echo ""
  echo "## 监控链自身模型消耗"
  echo ""
  echo "- dsh run 冒烟痕迹：$SMOKE_COUNT 轮日志含"
  echo "- 最近构建：$LAST_BUILD"
  echo "- 说明：cron 全链路为纯脚本（0 LLM token）；模型消耗仅来自手动 dsh 冒烟测试"
  echo ""
  echo "## 备注"
  echo ""
  echo "- 远程 omp 订阅（GLM/DeepSeek）有效期至 2026-09-01；额度消耗以 provider 侧账单为准"
  echo "- agent.db usage_history 损坏时无法读取历史趋势，需 omp 侧修复（omp 不运行时 .recover）"
} > "$REPORT"
echo "[usage] 报告已写入 $REPORT"
exit 0
