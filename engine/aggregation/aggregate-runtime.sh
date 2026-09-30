#!/usr/bin/env bash
# 聚合分片运行级测试结果 → 合并状态 + 生成最终报告
set -uo pipefail
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR" || exit 2
DATE="$(date +%Y-%m-%d)"
JQ="$HOME/.local/bin/jq"
MAIN="$REPO_DIR/.runtime-test-state.json"
echo '{}' > "$MAIN"
for f in "$REPO_DIR"/.runtime-test-state.*.json; do
  [ -f "$f" ] || continue
  "$JQ" -s '.[0] * .[1]' "$MAIN" "$f" > "$MAIN.part.$$" && mv "$MAIN.part.$$" "$MAIN"
done
TOTAL=$("$JQ" 'length' "$MAIN")
PASS=$("$JQ" -r '[.[].result] | map(select(startswith("✅"))) | length' "$MAIN")
FAIL=$("$JQ" -r '[.[].result] | map(select(startswith("⚠️"))) | length' "$MAIN")
ERR=$("$JQ" -r '[.[].result] | map(select(startswith("❌"))) | length' "$MAIN")
echo "[聚合] 共 $TOTAL：可用 $PASS / 加载失败 $FAIL / 运行报错 $ERR"
# 报告
REPORT="$REPO_DIR/reports/$DATE/runtime-test.md"
{
  echo "# 运行级真实测试（$DATE · Qwen3.6-35B 驱动 · 并行分片）"
  echo ""
  echo "| 插件 | 判定 |"
  echo "|---|---|"
  "$JQ" -r 'to_entries | sort_by(.key) | .[] | "| \(.key) | \(.value.result) |"' "$MAIN"
  echo ""
  echo "## 汇总"
  echo ""
  echo "- 共 $TOTAL：可用 $PASS / 加载失败 $FAIL / 运行报错 $ERR"
} > "$REPORT"
echo "[aggregate] 报告已写入 $REPORT"
