#!/usr/bin/env bash
# 模型真实上限实测（二分逼近，以服务端实际响应为准，不假设）
# 输出上限：max_tokens 递增，观察 finish_reason=length/stop 与服务端 clamp/报错
# 输入上限：输入长度递增，观察是否 context length exceeded
# 用法：model-probe.sh
set -uo pipefail
[ -f "$HOME/.dsh-radar.env" ] && . "$HOME/.dsh-radar.env"

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"   # engine/ops → 仓库根
cd "$REPO_DIR" || exit 2
# 密钥经 secretsource 统一解析（env > ~/.radar-keys/deepseek > sqlite 兜底）；
# Authorization 头写 0600 临时文件经 curl -H @file 传递——密钥不进 argv/ps（P2b）
AUTH_HDR="$(mktemp)"
chmod 600 "$AUTH_HDR"
trap 'rm -f "$AUTH_HDR"' EXIT
python3 "$REPO_DIR/engine/lib/radar/secretsource.py" deepseek header > "$AUTH_HDR" 2>/dev/null || true
QW_URL="${DSH_QWEN_BASE_URL:-http://127.0.0.1:1/v1}/chat/completions"
OUT="$REPO_DIR/reports/$(date +%Y-%m-%d)/model-probe.md"
mkdir -p "$(dirname "$OUT")"
echo "# 模型上限实测（$(date +%Y-%m-%d)）" > "$OUT"

probe_output() { # $1=名称 $2=URL $3=auth头文件(空=无鉴权) $4=max_tokens
  local name="$1" url="$2" hdr="$3" mt="$4"
  local resp
  resp="$(timeout 300 curl -s -m 290 "$url" -H "Content-Type: application/json" \
    ${hdr:+-H @$hdr} \
    -d "$(python3 -c "import json,sys;print(json.dumps({'model':sys.argv[1],'messages':[{'role':'user','content':'从1开始依次输出数字，每个数字一行，越多越好'}],'max_tokens':int(sys.argv[2])}))" "$( [ "$name" = "deepseek" ] && echo deepseek-v4-flash || echo Qwen3.6-35B )" "$mt")" 2>/dev/null)"
  printf '%s' "$resp" | python3 -c "
import json,sys
d=json.load(sys.stdin)
if 'error' in d:
    print('ERROR:', str(d['error'])[:150])
else:
    u=d.get('usage',{})
    print('completion=%s finish=%s total=%s' % (u.get('completion_tokens'), d['choices'][0].get('finish_reason'), u.get('total_tokens')))
" 2>/dev/null || echo "NET_FAIL"
}

echo "== 输出上限（二分：从声明值附近试探，看服务端 clamp/报错） =="
echo "" >> "$OUT"
for mt in 100 2000 8192 16000 32000; do
  echo "[deepseek] max_tokens=$mt → $(probe_output deepseek https://api.deepseek.com/chat/completions "$AUTH_HDR" "$mt")"
  echo "- deepseek max_tokens=$mt → $(probe_output deepseek https://api.deepseek.com/chat/completions "$AUTH_HDR" "$mt")" >> "$OUT"
done
for mt in 100 2000 8192 16384 32768 60000; do
  echo "[qwen] max_tokens=$mt → $(probe_output qwen "$QW_URL" "" "$mt")"
  echo "- qwen max_tokens=$mt → $(probe_output qwen "$QW_URL" "" "$mt")" >> "$OUT"
done

echo "== 输入上限（递增，观察 context 报错） =="
python3 << 'PYEOF'
sizes = [8192, 32768, 65536, 131072, 262144, 524288]
payloads = {}
for n in sizes:
    payloads[n] = "填充文本，用于探测上下文窗口。" * (n // 12)
json.dump({str(k): v for k, v in payloads.items()}, open("/tmp/probe-in.json", "w"))
print("generated")
PYEOF
for size in 8192 32768 65536 131072 262144; do
  echo "[deepseek] 输入≈${size}字 → $(timeout 90 curl -s -m 80 https://api.deepseek.com/chat/completions -H @"$AUTH_HDR" -H "Content-Type: application/json" -d "$(python3 -c "import json;d=json.load(open('/tmp/probe-in.json'));print(json.dumps({'model':'deepseek-v4-flash','messages':[{'role':'user','content':d['$size'][:${size}]}],'max_tokens':10}))")" 2>/dev/null | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    print('ERROR:', str(d.get('error'))[:120] if 'error' in d else 'OK total=%s' % d.get('usage',{}).get('total_tokens'))
except: print('NET_FAIL')" 2>/dev/null)"
  echo "- deepseek 输入${size} → 见上" >> "$OUT"
done
for size in 65536 131072 262144 524288; do
  echo "[qwen] 输入≈${size}字 → $(timeout 180 curl -s -m 170 "$QW_URL" -H "Content-Type: application/json" -d "$(python3 -c "import json;d=json.load(open('/tmp/probe-in.json'));print(json.dumps({'model':'Qwen3.6-35B','messages':[{'role':'user','content':d['$size'][:${size}]}],'max_tokens':10}))")" 2>/dev/null | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    print('ERROR:', str(d.get('error'))[:120] if 'error' in d else 'OK total=%s' % d.get('usage',{}).get('total_tokens'))
except: print('NET_FAIL')" 2>/dev/null)"
  echo "- qwen 输入${size} → 见上" >> "$OUT"
done
echo "== DONE =="
echo "报告: $OUT"
