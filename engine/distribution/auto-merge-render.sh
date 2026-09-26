#!/usr/bin/env bash
# auto-merge-render.sh — Bot B 渲染 PR 自动合并（P4b 起委派 merge_guard 三重闸门）
# 由 readme-render-watch.sh 在 PR 创建后调用：auto-merge-render.sh <branch> <pushed-sha>
# <pushed-sha> = 推送方捕获的分支 commit——缺省即拒绝自动合并（fail-closed，
# 不降级为仅文件校验：同名伪装分支可塞白名单文件绕过）
set -uo pipefail
export PATH=$HOME/.local/bin:$PATH
REPO=dsh-external/awesome-dsh-plugins
BR="${1:?用法: auto-merge-render.sh <branch> <pushed-sha>}"
SHA="${2:-}"
GUARD="$(cd "$(dirname "$0")" && pwd)/merge_guard.py"

N=$(gh pr list --repo "$REPO" --state open --head "$BR" --json number --jq '.[0].number' 2>/dev/null)
[ -n "$N" ] || { echo "[auto-merge] 无 open PR"; exit 0; }
if [ -z "$SHA" ]; then
  echo "[auto-merge] 未传推送 SHA——拒绝自动合并 #$N（留人工）"
  exit 0
fi
python3 "$GUARD" --repo "$REPO" --pr "$N" --expect-sha "$SHA" \
  --author AdamPlatin123 --allow-file README.md --allow-file CHANGELOG.md || true
