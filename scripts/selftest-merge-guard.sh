#!/usr/bin/env bash
# selftest-merge-guard.sh — 三重闸门四用例回归（P4b）。
# 以 mock gh（读 $MOCK_DIR/pr.json 应答 pr view；记录 merge 调用到 $MOCK_DIR/merged）
# 驱动 engine/distribution/merge_guard.py：SHA 不符 / 作者不符 / 文件不符 / 全过（--dry）。
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GUARD="$ROOT/engine/distribution/merge_guard.py"
command -v python3 >/dev/null || exit 2

MOCK_DIR="$(mktemp -d)"
trap 'rm -rf "$MOCK_DIR"' EXIT
cat > "$MOCK_DIR/gh" <<EOF
#!/usr/bin/env bash
# mock gh：pr view 回 canned JSON；pr merge 记录并置 merged 标记
if [ "\$1 \$2 \$3" = "pr merge --help" ]; then echo "  --match-head-commit <commit SHA>"; exit 0; fi
if [ "\$1 \$2" = "pr view" ]; then cat "$MOCK_DIR/pr.json"; exit 0; fi
if [ "\$1 \$2" = "pr merge" ]; then echo merge-called >> "$MOCK_DIR/merged"; exit 0; fi
exit 9
EOF
chmod +x "$MOCK_DIR/gh"

GOOD_SHA=0123456789abcdef0123456789abcdef01234567
make_pr() {  # $1=head $2=login $3=files(json array)
  printf '{"headRefOid":"%s","author":{"login":"%s"},"files":[%s]}' "$1" "$2" "$3" > "$MOCK_DIR/pr.json"
}
FILES_OK='"{"path":"README.md"}","{"path":"CHANGELOG.md"}"'
# 注：gh 真实返回 files=[{"path":"README.md"},...]；此处字面构造
FILES_OK='{"path":"README.md"},{"path":"CHANGELOG.md"}'

run() { python3 "$GUARD" --repo o/r --pr 7 --gh-bin "$MOCK_DIR/gh" "$@"; }
fails=0

# 用例① head SHA 不符 → 拒绝（exit 1）
make_pr "ffffffffffffffffffffffffffffffffffffffff" AdamPlatin123 "$FILES_OK"
out=$(run --expect-sha "$GOOD_SHA" --author AdamPlatin123 --expect-file README.md --expect-file CHANGELOG.md --dry) \
  && { echo "[① FAIL] 应拒绝"; fails=$((fails+1)); } || true
echo "$out" | grep -q "head SHA 不符" && echo "[① PASS] SHA 钉死拦截" || { echo "[① FAIL] $out"; fails=$((fails+1)); }

# 用例② 作者不符 → 拒绝
make_pr "$GOOD_SHA" "evil-clone" "$FILES_OK"
out=$(run --expect-sha "$GOOD_SHA" --author AdamPlatin123 --expect-file README.md --expect-file CHANGELOG.md --dry) || true
echo "$out" | grep -q "作者" && echo "[② PASS] 作者钉死拦截" || { echo "[② FAIL] $out"; fails=$((fails+1)); }

# 用例③ 文件集合不符（伪装分支塞白名单外文件）→ 拒绝
make_pr "$GOOD_SHA" AdamPlatin123 '{"path":"README.md"},{"path":"evil.sh"}'
out=$(run --expect-sha "$GOOD_SHA" --author AdamPlatin123 --expect-file README.md --expect-file CHANGELOG.md --dry) || true
echo "$out" | grep -q "文件集合" && echo "[③ PASS] 文件集合精确匹配拦截" || { echo "[③ FAIL] $out"; fails=$((fails+1)); }

# 用例④ 全过（--dry，不触发 merge）
rm -f "$MOCK_DIR/merged"
make_pr "$GOOD_SHA" AdamPlatin123 "$FILES_OK"
out=$(run --expect-sha "$GOOD_SHA" --author AdamPlatin123 --expect-file README.md --expect-file CHANGELOG.md --dry) \
  && echo "[④ PASS] 三重闸门通过（--dry）" || { echo "[④ FAIL] $out"; fails=$((fails+1)); }
[ -f "$MOCK_DIR/merged" ] && { echo "[④ FAIL] --dry 不应合并"; fails=$((fails+1)); }

# 用例⑤ glob 匹配（catalog/all/* 目录产物，精确集模式）
make_pr "$GOOD_SHA" AdamPlatin123 '{"path":"catalog/all/编码开发.md"},{"path":"catalog/all/其他.md"}'
out=$(run --expect-sha "$GOOD_SHA" --author AdamPlatin123 --expect-file 'catalog/all/*' --dry) \
  && echo "[⑤ PASS] glob 文件集匹配" || { echo "[⑤ FAIL] $out"; fails=$((fails+1)); }

# 用例⑥ 允许集模式：PR 文件 ∈ 清单即可，清单无需全出现（渲染 PR 本轮磁贴未变属正常）
make_pr "$GOOD_SHA" AdamPlatin123 '{"path":"README.md"}'
out=$(run --expect-sha "$GOOD_SHA" --author AdamPlatin123 --allow-file README.md --allow-file CHANGELOG.md --allow-file 'assets/*' --dry) \
  && echo "[⑥ PASS] 允许集子集通过" || { echo "[⑥ FAIL] $out"; fails=$((fails+1)); }

# 用例⑦ 允许集模式：清单外文件仍拒绝
make_pr "$GOOD_SHA" AdamPlatin123 '{"path":"README.md"},{"path":"evil.sh"}'
out=$(run --expect-sha "$GOOD_SHA" --author AdamPlatin123 --allow-file README.md --dry) || true
echo "$out" | grep -q "允许清单外" && echo "[⑦ PASS] 允许集拦截清单外文件" || { echo "[⑦ FAIL] $out"; fails=$((fails+1)); }

# 用例⑧ 双模式同给/都不给 → 参数错误（exit 2）
run --expect-sha "$GOOD_SHA" --author AdamPlatin123 --dry >/dev/null 2>&1
[ $? -eq 2 ] && echo "[⑧ PASS] 缺文件模式参数报错" || { echo "[⑧ FAIL] 应 exit 2"; fails=$((fails+1)); }

# 用例⑨ 身份白名单 any-of：经典 bot 格式也过
make_pr "$GOOD_SHA" "github-actions[bot]" "$FILES_OK"
out=$(run --expect-sha "$GOOD_SHA" --author "app/github-actions" --author "github-actions[bot]" --expect-file README.md --expect-file CHANGELOG.md --dry) \
  && echo "[⑨ PASS] 身份白名单 any-of（github-actions[bot]）" || { echo "[⑨ FAIL] $out"; fails=$((fails+1)); }

# 用例⑩ 排队合并语义：--auto 受理即成功（不再因 state=OPEN 误报失败）
rm -f "$MOCK_DIR/merged"
make_pr "$GOOD_SHA" AdamPlatin123 "$FILES_OK"
out=$(run --expect-sha "$GOOD_SHA" --author AdamPlatin123 --expect-file README.md --expect-file CHANGELOG.md) \
  && echo "[⑩ PASS] --auto 受理视为成功（head 已钉死）" || { echo "[⑩ FAIL] $out"; fails=$((fails+1)); }

echo "────"
[ "$fails" -eq 0 ] && { echo "[selftest] 全部通过（10 用例）"; exit 0; } || { echo "[selftest] $fails 个失败"; exit 1; }
