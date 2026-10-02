#!/usr/bin/env bash
# 更新 README 自动仪表盘节（<!-- AUTO:ecosystem --> 标记块），A 方向「仪表盘优先」：
#   徽章行 → 今日新增/修改仓库表 → 需适配表 → 跟踪中的 open PR 表
# 数据源：.last-changes.json（cron-check 写入的本次新增/修改）+ 最新报告 + gh PR 查询
# cron-check.sh 每次运行后调用；README 变化由 cron-check 统一 commit/push。
# 依赖：bash/git/gh/jq（gh 认证）
set -uo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_DIR" || exit 2
README="README.md"
[ -f "$README" ] || { echo "[错误] 找不到 README.md"; exit 2; }
if grep -q '<!-- README:layout:v2 -->' "$README"; then
  echo '[update-readme] 新布局由快照摘要渲染器维护，跳过旧仪表盘写入'
  exit 0
fi

# 1. 最新报告汇总（reports/<最新日期>/mainline-compat.md 首行兼容性）
LATEST_REPORT="$(ls -d reports/20*/ 2>/dev/null | sort | tail -1 | sed 's#/$##')"
DATE="$(basename "${LATEST_REPORT:-reports/unknown}")"
SUMMARY=""
if [ -n "$LATEST_REPORT" ] && [ -f "$LATEST_REPORT/mainline-compat.md" ]; then
  SUMMARY="$(grep -m1 '^- 兼容性：' "$LATEST_REPORT/mainline-compat.md" | sed 's/^- //' || true)"
fi
MAINLINE="$(jq -r '.lastMainlineCommit // "?"' .mainline-state.json 2>/dev/null | cut -c1-7)"
[ -z "$MAINLINE" ] && MAINLINE="?"

# 解析汇总数字：兼容性：X/Y 无需适配，Z 需适配（...）；其中关注 A、占位 B、不适用 C、已删除 D
COMPAT="?"; TOTAL="?"; ADAPT="?"; WATCH="?"; PLACE="?"; NA="?"; GONE="?"
if [ -n "$SUMMARY" ]; then
  COMPAT="$(printf '%s' "$SUMMARY" | sed -E 's#兼容性：([0-9]+)/[0-9]+.*#\1#')"
  TOTAL="$(printf '%s' "$SUMMARY" | sed -E 's#兼容性：[0-9]+/([0-9]+).*#\1#')"
  ADAPT="$(printf '%s' "$SUMMARY" | sed -E 's#.*，([0-9]+) 需适配.*#\1#')"
  WATCH="$(printf '%s' "$SUMMARY" | sed -E 's#.*关注 ([0-9]+).*#\1#')"
  PLACE="$(printf '%s' "$SUMMARY" | sed -E 's#.*占位 ([0-9]+).*#\1#')"
  NA="$(printf '%s' "$SUMMARY" | sed -E 's#.*不适用 ([0-9]+).*#\1#')"
  GONE="$(printf '%s' "$SUMMARY" | sed -E 's#.*已删除 ([0-9]+).*#\1#')"
  # 汇总数字校验：sed 提取结果必须匹配 ^[0-9]+$（sed 未命中时原样返回整行，非数字）
  # 任一数字非法 → 全部置 "?"（全部数字有效才渲染真实值，杜绝半成品数字上 README）
  valid=1
  for v in COMPAT TOTAL ADAPT WATCH PLACE NA GONE; do
    [[ "${!v}" =~ ^[0-9]+$ ]] || valid=0
  done
  if [ "$valid" -eq 0 ]; then
    COMPAT="?"; TOTAL="?"; ADAPT="?"; WATCH="?"; PLACE="?"; NA="?"; GONE="?"
  fi
fi

# 2. 今日新增/修改仓库（.last-changes.json；无则取空）
NEW_LIST=""; MOD_LIST=""
if [ -f .last-changes.json ]; then
  NEW_LIST="$(jq -r '.new_repos[]?' .last-changes.json 2>/dev/null || true)"
  MOD_LIST="$(jq -r '.changed_repos[]?' .last-changes.json 2>/dev/null || true)"
fi
NEW_ROWS=""; MOD_ROWS=""
[ -n "$NEW_LIST" ] && NEW_ROWS="$(printf '%s\n' "$NEW_LIST" | while IFS= read -r n; do [ -n "$n" ] && printf '| [%s](https://github.com/dsh-external/%s) | 🆕 新增 |\n' "$n" "$n"; done)"
[ -z "$NEW_ROWS" ] && NEW_ROWS=$'| （今日无新增） | |\n'
[ -n "$MOD_LIST" ] && MOD_ROWS="$(printf '%s\n' "$MOD_LIST" | while IFS= read -r n; do [ -n "$n" ] && printf '| [%s](https://github.com/dsh-external/%s) | ✏️ 修改 |\n' "$n" "$n"; done)"
[ -z "$MOD_ROWS" ] && MOD_ROWS=$'| （今日无修改） | |\n'

# 2.5 完整仓库分群表（README 第一眼入口：全部仓库按判定状态分组列出）
#     数据源 = 最新 mainline-compat.md 矩阵；URL 支持 owner/name（外部仓库）
GROUP_BLOCK=""
if [ -n "$LATEST_REPORT" ] && [ -f "$LATEST_REPORT/mainline-compat.md" ]; then
  GROUP_OUTPUT="$(python3 - "$LATEST_REPORT/mainline-compat.md" <<'PYEOF'
import re, sys
path = sys.argv[1]
groups: dict[str, list[str]] = {}
order = ['兼容', '需适配', '关注', '待调研', '占位', '不适用', '已删除']
for line in open(path, encoding='utf-8'):
    m = re.match(r'^\|\s*([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?)\s*\|.*\|\s*([^|]+?)\s*\|$', line)
    if not m:
        continue
    name, verdict = m.group(1), m.group(2).strip()
    if '需适配' in verdict:
        g = '需适配'
    elif '兼容' in verdict:
        g = '兼容'
    elif '关注' in verdict:
        g = '关注'
    elif '占位' in verdict:
        g = '占位'
    elif '不适用' in verdict:
        g = '不适用'
    elif '已删除' in verdict:
        g = '已删除'
    else:
        g = '待调研'
    groups.setdefault(g, []).append(name)
out = []
for g in order:
    items = groups.get(g, [])
    if not items:
        continue
    if g == '待调研':
        out.append(f'\n<details><summary>待调研（{len(items)}）—— 点击展开</summary>\n')
    else:
        out.append(f'\n**{g}**（{len(items)}）\n')
    out.append('| 仓库 | 状态 |')
    out.append('|---|---|')
    for n in items:
        url = n if '/' in n else f'dsh-external/{n}'
        out.append(f'| [{n}](https://github.com/{url}) | {g} |')
    if g == '待调研':
        out.append('</details>')
# STATS 行：与分群表同源，供 README 顶部证据层使用（避免两处口径不一致）
stats = {g: len(groups.get(g, [])) for g in order}
print('STATS|' + '|'.join(f'{g}={stats[g]}' for g in order))
print('\n'.join(out))
PYEOF
)"
  GROUP_BLOCK="$(printf '%s' "$GROUP_OUTPUT" | grep -v '^STATS|')"
  # 解析同源统计覆盖顶部数字（矩阵逐行判定为准）
  _stats_line="$(printf '%s' "$GROUP_OUTPUT" | grep -m1 '^STATS|' | cut -d'|' -f2-)"
  if [ -n "$_stats_line" ]; then
    _parse() { printf '%s' "$_stats_line" | tr '|' '\n' | grep "^$1=" | cut -d= -f2; }
    for _pair in 兼容=COMPAT 需适配=ADAPT 关注=WATCH 待调研=UNKNOWN 占位=PLACE 不适用=NA 已删除=GONE; do
      _g="${_pair%%=*}"; _v="${_pair#*=}"
      _n="$(_parse "$_g")"
      [[ "$_n" =~ ^[0-9]+$ ]] && eval "$_v=$_n"
    done
    TOTAL=$((COMPAT + ADAPT + WATCH + UNKNOWN + PLACE + NA + GONE))
  fi
fi

# 3. 需适配仓库（从最新报告矩阵提取状态=需适配的行）
ADAPT_ROWS=""
if [ -n "$LATEST_REPORT" ] && [ -f "$LATEST_REPORT/mainline-compat.md" ]; then
  ADAPT_ROWS="$(grep -E '^\| .* \| 需适配[^|]* \|$' "$LATEST_REPORT/mainline-compat.md" | sed -E 's#^\| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$#| [\1](https://github.com/dsh-external/\1) | \2 | \6 |#' | head -20)"
fi
[ -z "$ADAPT_ROWS" ] && ADAPT_ROWS=$'| （暂无） | | |\n'

# 4. org open PR 列表（search API，全部仓库）
#    查询失败（gh/jq 缺失、超时、返回空）→ 不覆盖 README，echo 错误并 exit 1（不渲染假"暂无"）
PR_TOTAL="0"
PR_ROWS=""
for dep in gh jq; do
  command -v "$dep" >/dev/null 2>&1 || { echo "[错误] 缺少依赖: $dep（无法查询 open PR，跳过 README 更新）"; exit 1; }
done
PR_TOTAL="$(timeout 60 gh api "search/issues?q=org:dsh-external+type:pr+state:open&per_page=1" --jq '.total_count' 2>/dev/null || true)"
if ! [[ "$PR_TOTAL" =~ ^[0-9]+$ ]]; then
  echo "[错误] gh 查询 open PR 总数失败（超时/网络/认证），不覆盖 README（exit 1）"
  exit 1
fi
PR_LIST="$(timeout 90 gh api "search/issues?q=org:dsh-external+type:pr+state:open&per_page=100" 2>/dev/null || true)"
if [ -z "$PR_LIST" ]; then
  echo "[错误] gh 查询 open PR 列表失败（超时/网络/认证），不覆盖 README（exit 1）"
  exit 1
fi
while IFS=$'\t' read -r repo num title updated; do
  [ -n "$repo" ] || continue
  PR_ROWS+="| [$repo](https://github.com/dsh-external/$repo) | [#$num](https://github.com/dsh-external/$repo/pull/$num) | $title | $updated |"$'\n'
done < <(printf '%s' "$PR_LIST" | jq -r '.items[] | [((.repository_url | split("/") | .[length-1])), (.number|tostring), .title, (.updated_at[0:10])] | @tsv' 2>/dev/null)
if [ "$PR_TOTAL" -gt 0 ] && [ -z "$PR_ROWS" ]; then
  echo "[错误] open PR 总数非 0 但列表解析为空（jq 解析失败），不覆盖 README（exit 1）"
  exit 1
fi
[ -z "$PR_ROWS" ] && PR_ROWS="| （暂无 open PR） | | | |"$'\n'

# 5. 组装标记块（证据层汇总：首页只出汇总+链接，不出完整表）
# 运行级数字从 .support-status.json 统计；证据不足 = 总数 - 已判定
UNKNOWN="?"
if [[ "$TOTAL" =~ ^[0-9]+$ ]] && [[ "$COMPAT" =~ ^[0-9]+$ ]] && [[ "$ADAPT" =~ ^[0-9]+$ ]] \
  && [[ "$WATCH" =~ ^[0-9]+$ ]] && [[ "$PLACE" =~ ^[0-9]+$ ]] && [[ "$NA" =~ ^[0-9]+$ ]] && [[ "$GONE" =~ ^[0-9]+$ ]]; then
  UNKNOWN=$((TOTAL - COMPAT - ADAPT - WATCH - PLACE - NA - GONE))
fi
RT_PASS="?"; RT_FAIL="?"; RT_TESTED="?"
if [ -f .support-status.json ]; then
  RT_PASS="$(jq -r '[.[].support] | map(select(. == "✅ 可用")) | length' .support-status.json 2>/dev/null || echo "?")"
  RT_FAIL="$(jq -r '[.[].support] | map(select(startswith("⚠️") or startswith("❌"))) | length' .support-status.json 2>/dev/null || echo "?")"
  RT_TESTED="$(jq 'length' .support-status.json 2>/dev/null || echo "?")"
fi

BLOCK="<!-- AUTO:ecosystem:START -->
> 更新于 $(date +%Y-%m-%d\ %H:%M) · 每 8 小时刷新 · mainline \`$MAINLINE\`

| 证据层 | 当前结果 |
|---|---:|
| 自动收录 | $TOTAL 个仓库 |
| 静态综合判定 | $COMPAT 兼容 · $WATCH 关注 · $ADAPT 需适配 |
| 证据不足 | $UNKNOWN 待调研 |
| 其他 | $PLACE 占位 · $NA 不适用 · $GONE 已删除 |
| 运行级实测 | $RT_PASS 可用 · $RT_FAIL 失败（共测试 $RT_TESTED 个） |
| 正在跟踪的 PR | $PR_TOTAL |

[完整索引](reports/$DATE/index.md) · [静态矩阵](reports/$DATE/mainline-compat.md) · [编译实验](reports/$DATE/compile-compat.md) · [运行实测](reports/$DATE/runtime-test.md)

**插件目录**（$TOTAL 个仓库 · 按判定状态分群）
${GROUP_BLOCK}

**今日新增 / 修改**（完整变更见 [CHANGELOG](CHANGELOG.md)）

| 仓库 | 类型 |
|---|---|
${NEW_ROWS}
${MOD_ROWS}

**⚠️ 需适配**（完整矩阵见 [mainline-compat.md](reports/$DATE/mainline-compat.md)）

| 插件 | 锚定 | 判定 |
|---|---|---|
${ADAPT_ROWS}

**🐙 正在跟踪的 open PR**

| 仓库 | PR | 标题 | 更新 |
|---|---|---|---|
${PR_ROWS}
<!-- AUTO:ecosystem:END -->"

# 6. 替换 README 标记块（不存在则追加到末尾）
python3 - "$README" "$BLOCK" <<'PYEOF'
import sys
path, block = sys.argv[1], sys.argv[2]
with open(path, encoding='utf-8') as f:
    content = f.read()
start_marker = '<!-- AUTO:ecosystem:START -->'
end_marker = '<!-- AUTO:ecosystem:END -->'
if start_marker in content:
    start = content.index(start_marker)
    end = content.index(end_marker) + len(end_marker)
    new = content[:start] + block + content[end:]
else:
    new = content.rstrip() + '\n\n## 生态状态（自动更新）\n\n' + block + '\n'
with open(path, 'w', encoding='utf-8') as f:
    f.write(new)
print('README 自动仪表盘已更新')
PYEOF

# 7. 分类目录块（参考 hub 九类体系，随 README 更新一并刷新）
"$(dirname "$0")/gen-catalog.sh" >/dev/null 2>&1 || true
exit 0
