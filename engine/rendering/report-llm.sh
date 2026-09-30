#!/usr/bin/env bash
# LLM 报告增强：用最好模型（deepseek-v4-pro）读当日兼容矩阵，
# 生成"开发者摘要与建议"（生态状态解读 + 需适配插件行动建议 + mainline 变更影响）
# 输出：reports/<日期>/mainline-summary.md（人工可读摘要，附在报告旁）
# 用法：report-llm.sh [--date YYYY-MM-DD]
# 集成：cron-check.sh 引擎完成后调用（异步后台）
set -uo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"   # engine/rendering → 仓库根
cd "$REPO_DIR" || exit 2
DATE="$(date +%Y-%m-%d)"
for a in "$@"; do [ "$a" = "--date" ] && shift; done
[ "${2:-}" != "" ] && DATE="${2:-}"
REPORT="$REPO_DIR/reports/$DATE/mainline-compat.md"
OUT="$REPO_DIR/reports/$DATE/mainline-summary.md"
[ -f "$REPORT" ] || { echo "[llm] 当日报告不存在: $REPORT"; exit 2; }

# 密钥经 secretsource 统一解析（env > ~/.radar-keys/deepseek > sqlite 兜底）；
# Authorization 头写 0600 临时文件经 curl -H @file 传递——密钥不进 argv/ps（P2b）
SECRETS="$REPO_DIR/engine/lib/radar/secretsource.py"
AUTH_HDR="$(mktemp)"
chmod 600 "$AUTH_HDR"
trap 'rm -f "$AUTH_HDR"' EXIT
python3 "$SECRETS" deepseek header > "$AUTH_HDR" 2>/dev/null \
  || { echo "[llm] deepseek key 不可用"; exit 2; }
[ -s "$AUTH_HDR" ] || { echo "[llm] deepseek key 不可用"; exit 2; }

# 提取报告核心（汇总行 + 需适配矩阵行 + 变更分析节）
python3 - "$REPORT" > /tmp/report-core.txt << 'PYEOF'
import sys, re
txt = open(sys.argv[1]).read()
lines = txt.split('\n')
core = []
in_matrix = False
for i, l in enumerate(lines):
    if '兼容性：' in l or 'mainline：' in l:
        core.append(l.strip())
    if l.startswith('| ') and ('需适配' in l or '兼容' in l or '关注' in l or '未知' in l) and '仓库' not in l:
        core.append(l.strip())
    if '## mainline' in l or '## 变更' in l:
        core.append('--- 变更分析 ---')
        for j in range(i+1, min(i+12, len(lines))):
            if lines[j].strip(): core.append(lines[j].strip()[:200])
        break
open('/tmp/report-core.txt','w').write('\n'.join(core[:60]))
print('core extracted', len(core))
PYEOF

PROMPT="你是 DSH 插件生态的资深技术顾问。以下是最新 mainline 兼容性扫描结果（DSH Plugin Radar 每日自动生成）。请用中文写一份 300-500 字的「开发者摘要与建议」，结构：\n1) 今日生态状态一句话（仓库数/兼容/需适配比例）\n2) 需适配插件清单的行动建议（每个 1 句：根因+修法）\n3) mainline 变更影响（如有变更分析：哪些插件受影响、如何提前适配）\n4) 一句话提醒（今天最该做的事）\n\n扫描结果：\n$(cat /tmp/report-core.txt)"

echo "[llm] 调用 deepseek-v4-pro 生成摘要..."
SUMMARY="$(timeout 180 curl -s -m 170 https://api.deepseek.com/chat/completions \
  -H @"$AUTH_HDR" -H "Content-Type: application/json" \
  -d "$(python3 -c "import json,sys;print(json.dumps({'model':'deepseek-v4-pro','messages':[{'role':'user','content':sys.argv[1]}],'max_tokens':2000}))" "$PROMPT")" 2>/dev/null \
  | python3 -c "import json,sys
try:
    d=json.load(sys.stdin)
    print(d['choices'][0]['message']['content'] or '')
except Exception as e: print('LLM_ERR', e)" 2>/dev/null)"

if printf '%s' "$SUMMARY" | grep -q "LLM_ERR"; then
  echo "[llm] 生成失败：$SUMMARY"
  exit 2
fi

{
  echo "# 开发者摘要与建议（$DATE · LLM 生成）"
  echo ""
  printf '%s\n' "$SUMMARY"
  echo ""
  echo "---"
  echo "> 由 DSH Plugin Radar 自动生成（deepseek-v4-pro）；数据源：[$DATE 兼容性报告](mainline-compat.md)"
} > "$OUT"
echo "[llm] 摘要已写入 $OUT"
exit 0
