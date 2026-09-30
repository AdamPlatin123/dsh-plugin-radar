#!/usr/bin/env bash
# selftest-cron-increment.sh — cron-check.sh 增量检测三用例回归（P2a）。
#
# 背景：变化检测曾引用未定义的 REPOS 数组，bash 4.4+ 空数组静默展开为空，
# 增量检测与游标更新整段空转（二轮起永远「无变化」）。本自测以 mock 的
# remote_head 驱动 lib_cron_logic.sh，覆盖三条路径：
#   用例① 首跑（无状态文件）→ all(首次)
#   用例② 状态文件与远端一致 → 无变化
#   用例③ 远端 HEAD 变化 → 精确检出变化仓库；游标随 write_cursor 推进
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LIB="$SCRIPT_DIR/../engine/discovery/lib_cron_logic.sh"
command -v jq >/dev/null 2>&1 || { echo "[selftest] 缺依赖 jq"; exit 2; }
[ -f "$LIB" ] || { echo "[selftest] 缺 $LIB"; exit 2; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export STATE="$TMP/state.json"
HEADS="$TMP/heads"   # mock 远端 HEAD 表：每行 name<TAB>sha

remote_head() {   # mock：读表，模拟 ls-remote（表内无此名=离线空输出）
  awk -F'\t' -v n="$1" '$1 == n {print $2; found=1; exit} END {if (!found) exit 1}' "$HEADS" 2>/dev/null || true
}

# shellcheck source=../engine/discovery/lib_cron_logic.sh
source "$LIB"

REPOS=( "mainline|https://example.invalid/mainline" "dsh-external/alpha|https://example.invalid/a" "dsh-external/beta|https://example.invalid/b" )
fails=0

# ── 用例①：首跑（无状态文件）──────────────────────────────────────────
rm -f "$STATE"
printf 'mainline\tsha-m1\ndsh-external/alpha\tsha-a1\ndsh-external/beta\tsha-b1\n' > "$HEADS"
detect_changes
if [ "$DETECTED" = "all(首次)" ]; then echo "[用例① PASS] 首跑 → all(首次)"; else echo "[用例① FAIL] 首跑 → '$DETECTED'"; fails=$((fails+1)); fi

# ── 用例②：状态与远端一致 → 无变化 ───────────────────────────────────
write_cursor   # 首跑后推进游标
detect_changes
if [ -z "$DETECTED" ]; then echo "[用例② PASS] 无变化 → 空"; else echo "[用例② FAIL] 应无变化，实测 '$DETECTED'"; fails=$((fails+1)); fi

# ── 用例③：alpha 的 HEAD 变化 + 新仓 gamma 首次纳入 → 精确检出 ─────────
printf 'mainline\tsha-m1\ndsh-external/alpha\tsha-a2\ndsh-external/beta\tsha-b1\ndsh-external/gamma\tsha-g1\n' > "$HEADS"
REPOS+=( "dsh-external/gamma|https://example.invalid/g" )
detect_changes
if [[ "$DETECTED" == *"dsh-external/alpha"* && "$DETECTED" == *"dsh-external/gamma"* && "$DETECTED" != *"beta"* ]]; then
  echo "[用例③ PASS] 精确检出变化（alpha）+ 新增（gamma），beta 未误报"
else
  echo "[用例③ FAIL] 检出结果 '$DETECTED'"; fails=$((fails+1))
fi
write_cursor   # 游标推进到新基线
if jq -e --arg a sha-a2 '.["dsh-external/alpha"] == $a' "$STATE" >/dev/null; then
  echo "[用例③ PASS] 游标已推进（alpha → sha-a2）"
else
  echo "[用例③ FAIL] 游标未推进"; fails=$((fails+1))
fi

# ── 用例④（回归）：离线仓保留旧状态，不误报变化 ───────────────────────
printf 'mainline\tsha-m1\ndsh-external/alpha\tsha-a2\n' > "$HEADS"   # beta/gamma 表中删除=离线
detect_changes
if [[ "$DETECTED" != *"beta"* && "$DETECTED" != *"gamma"* ]]; then
  echo "[用例④ PASS] 离线仓（ls-remote 空）不误报、保留旧状态"
else
  echo "[用例④ FAIL] 离线仓被误报：'$DETECTED'"; fails=$((fails+1))
fi

echo "────"
if [ "$fails" -eq 0 ]; then echo "[selftest] 全部通过（4 用例）"; exit 0; else echo "[selftest] $fails 个用例失败"; exit 1; fi
