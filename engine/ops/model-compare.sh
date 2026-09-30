#!/usr/bin/env bash
# 模型效果比对：同一任务跑 deepseek-v4-flash（旧）vs Qwen3.6-35B（新，内网）
# 输出：reports/<日期>/model-compare.md
# 用法：model-compare.sh "测试任务"
set -uo pipefail
[ -f "$HOME/.dsh-radar.env" ] && . "$HOME/.dsh-radar.env"

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"   # engine/ops → 仓库根
cd "$REPO_DIR" || exit 2
DATE="$(date +%Y-%m-%d)"
TASK="${1:-用中文解释什么是 goroutine 泄漏，并给出一个最小复现示例}"

# deepseek key 经 secretsource 统一解析（env > ~/.radar-keys/deepseek > sqlite 兜底）；
# Authorization 头写 0600 临时文件经 curl -H @file 传递——密钥不进 argv/ps（P2b）
AUTH_HDR="$(mktemp)"
chmod 600 "$AUTH_HDR"
trap 'rm -f "$AUTH_HDR"' EXIT
python3 "$REPO_DIR/engine/lib/radar/secretsource.py" deepseek header > "$AUTH_HDR" 2>/dev/null || true

echo "=== $(date -Is) model-compare 开始 ==="
echo "[任务] $TASK"

# 1. deepseek-v4-flash（旧模型，计费）
echo "[调用] deepseek-v4-flash..."
DS_OUT="$(timeout 60 curl -s -m 55 https://api.deepseek.com/chat/completions \
  -H @"$AUTH_HDR" -H "Content-Type: application/json" \
  -d "$(python3 -c "import json,sys; print(json.dumps({'model':'deepseek-v4-flash','messages':[{'role':'user','content':sys.argv[1]}],'max_tokens':65536}))" "$TASK")" 2>&1)"
DS_TXT="$(printf '%s' "$DS_OUT" | python3 -c "import json,sys
try:
    d=json.load(sys.stdin); print(d['choices'][0]['message']['content'] or '')
except Exception as e: print('ERR', e)" 2>/dev/null)"
DS_LEN="${#DS_TXT}"

# 2. Qwen3.6-35B（新模型，内网零费用）
echo "[调用] Qwen3.6-35B..."
QW_OUT="$(timeout 90 curl -s -m 85 ${DSH_QWEN_BASE_URL:-http://127.0.0.1:1/v1}/chat/completions \
  -H "Content-Type: application/json" \
  -d "$(python3 -c "import json,sys; print(json.dumps({'model':'Qwen3.6-35B','messages':[{'role':'user','content':sys.argv[1]}],'max_tokens':65536}))" "$TASK")" 2>&1)"
QW_TXT="$(printf '%s' "$QW_OUT" | python3 -c "import json,sys
try:
    d=json.load(sys.stdin); m=d['choices'][0]['message']; c=m.get('content') or ''; r=m.get('reasoning') or ''
    print((c or r[-1200:]) if (c or r) else '') 
except Exception as e: print('ERR', e)" 2>/dev/null)"
QW_LEN="${#QW_TXT}"

echo "[结果] deepseek ${DS_LEN}字 / qwen ${QW_LEN}字"

# 3. 写报告
REPORT="$REPO_DIR/reports/$DATE/model-compare.md"
mkdir -p "$REPO_DIR/reports/$DATE"
{
  echo "# 模型效果比对（$DATE）"
  echo ""
  echo "- 任务：$TASK"
  echo ""
  echo "## deepseek-v4-flash（旧，计费）— ${DS_LEN} 字"
  echo ""
  echo '```'
  printf '%s' "$DS_TXT"
  echo '```'
  echo ""
  echo "## Qwen3.6-35B（新，内网零费用）— ${QW_LEN} 字"
  echo ""
  echo '```'
  printf '%s' "$QW_TXT"
  echo '```'
  echo ""
  echo "## 比对要点（待多模型审查）"
  echo ""
  echo "- 正确性：两模型是否都答对核心概念"
  echo "- 完整性：覆盖深度 vs 遗漏"
  echo "- 代码示例：可运行性/简洁性"
  echo "- 延迟：deepseek vs qwen（内网）"
} > "$REPORT"
echo "[compare] 报告已写入 $REPORT"
exit 0
