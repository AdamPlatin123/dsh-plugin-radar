#!/usr/bin/env bash
# 每日 02:00 cron + watch-mainline/hook 触发：
#   1) 动态发现 dsh-external org 新仓库（gh api），与已知仓库合并为检测范围
#   2) 检测 mainline + 全部仓库 HEAD 变化（真实 diff，--full 也计算，不再误报"全部修改"）
#   3) 有变化（或 --full 强制）→ 运行 mainline 兼容索引（--scope 动态清单）
#   4) 更新报告/README 并推送回 org repo；推送成功后才推进游标（SOP Phase 0）
# 用法：cron-check.sh [--full]  — --full 强制全量索引（cron 02:00 班次）
# 依赖：bash/git/gh/jq（gh 已认证，git credential 走 gh auth setup-git）
set -uo pipefail

# Radar v4 worker 门禁：非 worker 调用（cron/hook/手动）只入队，禁止直接写
if [ "${RADAR_INDEX_WORKER:-}" != "1" ]; then
  /home/adam/dsh-k8s/radar-index-request.py --reason manual --trigger cron-check-direct >/dev/null 2>&1 || true
  echo "[cron-check] 非 worker 调用：已入队，由 radar-index-worker.service 执行"
  exit 0
fi

# 互斥：flock 防止 hook 触发与 cron 定时班并发（曾实测 3 个 --full 同时跑竞态）
LOCK_FD=9
exec 9>/tmp/dsh-cron-check.lock
if ! flock -n 9; then
  echo "[互斥] 已有 cron-check 在运行，本轮退出"
  exit 0
fi

FULL=0
for _arg in "$@"; do [ "$_arg" = "--full" ] && FULL=1; done

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR" || exit 2
mkdir -p logs
LOG="logs/cron-$(date +%Y%m%d).log"
exec >> "$LOG" 2>&1

[ "$FULL" -eq 1 ] && echo "=== $(date -Is) cron-check 开始（--full 全量模式） ===" || echo "=== $(date -Is) cron-check 开始 ==="

# 0. 依赖预检
for dep in bash git gh jq; do
  command -v "$dep" >/dev/null 2>&1 || { echo "[错误] 缺少依赖: $dep"; exit 2; }
done

# 1. 拉取自身最新（引擎/脚本/README 更新随 org repo 同步）
#    SOP：拉取失败即失败——不在未知代码版本或脏工作树上继续执行（游标不推进）
if ! git pull dsh-ext main --ff-only 2>&1 | tail -1; then
  echo "[错误] git pull 自更新失败（离线/脏工作树/冲突），本轮终止，游标不推进"
  exit 20
fi

# 2. 已知仓库（调研基线 15 仓）+ 动态发现新仓库
# 已知仓库 = 已调研摘要清单（research/*.md 文件名，新增摘要自动同步；不再手工维护）
KNOWN_REPOS=()
for _f in research/*.md; do
  [ -f "$_f" ] || continue
  _n="${_f##*/}"; _n="${_n%.md}"
  [ -n "$_n" ] && KNOWN_REPOS+=( "$_n" )
done
SELF_REPO="awesome-dsh-plugins"   # 本仓库自身，不纳入索引

# 动态拉取 org 全部仓库名（失败则回退已知列表，不误报离线）
ORG_REPOS="$(timeout 60 gh api "orgs/dsh-external/repos?per_page=100&type=all" --paginate --jq '.[].name' 2>/dev/null || echo "")"
# topic 打标仓库（dsh-plugin / dsh-external 任一，不限 org；search API 不允许纯 qualifier OR，分两次查）
TOPIC_REPOS="$(timeout 90 gh api "search/repositories?q=topic:dsh-plugin&per_page=100" --jq '.items[].full_name' 2>/dev/null || echo "")"
TOPIC_REPOS+=$'\n'"$(timeout 90 gh api "search/repositories?q=topic:dsh-external&per_page=100" --jq '.items[].full_name' 2>/dev/null || echo "")"
# 动态发现的新仓库（在 gh api 调用前初始化空数组，避免 set -u 下未定义引用）
NEW_REPOS=()
if [ -z "$ORG_REPOS" ] && [ -z "$TOPIC_REPOS" ]; then
  echo "[提示] gh api 获取 org/topic 仓库失败，回退已知列表"
  SCOPE_REPOS=()
  for k in "${KNOWN_REPOS[@]}"; do SCOPE_REPOS+=( "dsh-external/$k" ); done
else
  SCOPE_REPOS=()
  for k in "${KNOWN_REPOS[@]}"; do SCOPE_REPOS+=( "dsh-external/$k" ); done
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    full="dsh-external/$name"
    [ "$name" = "$SELF_REPO" ] && continue
    found=0
    for k in "${SCOPE_REPOS[@]}"; do [ "$k" = "$full" ] && found=1 && break; done
    if [ "$found" -eq 0 ]; then
      NEW_REPOS+=( "$full" )
      SCOPE_REPOS+=( "$full" )
    fi
  done <<< "$ORG_REPOS"
  while IFS= read -r full; do
    [ -n "$full" ] || continue
    [ "${full##*/}" = "$SELF_REPO" ] && continue
    found=0
    for k in "${SCOPE_REPOS[@]}"; do [ "$k" = "$full" ] && found=1 && break; done
    if [ "$found" -eq 0 ]; then
      # 验证为「能安装的插件」才纳入（package.json name+main/exports 或 dsh 集成；排除 awesome/合影/占位）
      PKG_OK="$(timeout 30 gh api "repos/$full/contents/package.json" --jq '.content' 2>/dev/null | base64 -d 2>/dev/null || echo "")"
      if [ -n "$PKG_OK" ] && printf '%s' "$PKG_OK" | jq -e '.name and (.main or .exports or .dsh)' >/dev/null 2>&1; then
        NEW_REPOS+=( "$full" )
        SCOPE_REPOS+=( "$full" )
      else
        echo "[跳过] $full：非插件仓库（无 package.json 或无可安装入口）"
        echo "$full" >> .non-plugin-repos.txt
      fi
    fi
  done <<< "$TOPIC_REPOS"
  if [ "${#NEW_REPOS[@]}" -gt 0 ]; then
    echo "[新仓库] 发现 ${#NEW_REPOS[@]} 个未索引仓库: ${NEW_REPOS[*]}"
  else
    echo "[新仓库] 无新增仓库（org $(echo "$ORG_REPOS" | wc -l | tr -d ' ') 个 + topic $(echo "$TOPIC_REPOS" | wc -l | tr -d ' ') 个）"
  fi
fi
: > .scope-current.txt
for r in "${SCOPE_REPOS[@]}"; do echo "$r" >> .scope-current.txt; done

# 探测表：name|url 形态（detect_changes/write_cursor 按此拆分）。
# mainline = 主线快照仓，URL 与 compare-mainline.sh 的 MAINLINE_URL 同源——改一处必改两处。
# 修复注记：此前本表从未构建（变化检测循环引用未定义的 REPOS，bash 4.4+ 静默空转，
# 增量检测整段死代码）——P2a 修复并配 scripts/selftest-cron-increment.sh 三用例回归。
REPOS=( "mainline|https://github.com/dsh2026/test-AdamPlatin123" )
for r in "${SCOPE_REPOS[@]}"; do
  REPOS+=( "$r|https://github.com/$r" )
done


# 远端 HEAD 探测：mainline 取最新快照分支（与 compare-mainline.sh 实际索引的快照一致），
# 其余仓库取 HEAD。快照分支名含 ISO 时间戳，字典序即时间序。
remote_head() { # $1=仓库名 $2=远端 URL → 输出当前 commit（失败为空）
  local name="$1" url="$2"
  if [ "$name" = "mainline" ]; then
    timeout 20 git ls-remote "$url" 'refs/heads/snapshots/*' 2>/dev/null \
      | LC_ALL=C sort -k2 | tail -1 | awk '{print $1}'
  else
    timeout 20 git ls-remote "$url" HEAD 2>/dev/null | awk '{print $1}'
  fi
}

# 3. 检测 mainline + 全部 scope 仓库的 HEAD 变化（逻辑在 lib_cron_logic.sh，供自测 mock）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib_cron_logic.sh
source "$SCRIPT_DIR/lib_cron_logic.sh"
STATE=".cron-state.json"
detect_changes
MODIFIED="$DETECTED"   # 真实 HEAD 变化集合（无论 --full 与否都计算，避免全量误报"全部修改"）
# --full 决定是否强制全量索引，但不影响"真实修改"集合
if [ "$FULL" -eq 1 ]; then
  echo "[全量] --full 模式：强制全量索引；真实修改仅 ${MODIFIED:-无}"
  CHANGED="all(全量)"
elif [ -n "$MODIFIED" ]; then
  CHANGED="$MODIFIED"
else
  CHANGED=""
fi

# 3.5 记录本次新增/修改仓库（供 README 自动仪表盘渲染）
#     新增 = 本次发现的 NEW_REPOS；修改 = 真实 HEAD 变化（CHANGED_REPOS），不再因 --full 把全部记成修改
CHANGED_REPOS=()
for _c in $MODIFIED; do
  [ "$_c" = "all(首次)" ] && continue
  _is_new=0
  for _n in "${NEW_REPOS[@]:-}"; do [ "$_n" = "$_c" ] && _is_new=1 && break; done
  [ "$_is_new" -eq 0 ] && CHANGED_REPOS+=( "$_c" )
done
{
  printf '{"date":"%s","new_repos":[' "$(date +%Y-%m-%d)"
  _first=1
  for _n in "${NEW_REPOS[@]:-}"; do
    [ $_first -eq 0 ] && printf ','
    printf '"%s"' "$_n"
    _first=0
  done
  printf '],"changed_repos":['
  _first=1
  for _c in "${CHANGED_REPOS[@]:-}"; do
    [ $_first -eq 0 ] && printf ','
    printf '"%s"' "$_c"
    _first=0
  done
  printf ']}'
} > .last-changes.json.tmp && mv .last-changes.json.tmp .last-changes.json

echo "[状态] .last-changes.json 已记录（新增 ${#NEW_REPOS[@]} / 修改 ${#CHANGED_REPOS[@]}）"

# 4. 有变化 → 运行 mainline 兼容索引（动态 scope）
if [ -n "$CHANGED" ]; then
  echo "[索引] 变化仓库:$CHANGED"
  ./scripts/compare-mainline.sh --scope .scope-current.txt
  rc=$?
  echo "[索引] compare-mainline.sh 退出码 $rc"

  # 引擎失败（退出码 >1 = 脚本错误/离线）→ 不 commit、不更新 README、不写状态文件，
  # 原样退出，留待下次 cron 重试（避免把失败误当成功推进基线）
  if [ "$rc" -gt 1 ]; then
    rm -f .last-changes.json   # 撤销本次生成的仪表盘数据，README 不引用失败结果
    echo "[错误] compare-mainline.sh 失败（退出码 $rc），跳过提交/README/状态写入，下次 cron 重试"
    exit "$rc"
  fi

  # 4.6 引擎完成后：LLM 生成开发者摘要（同步；失败/超时记录为事实，不伪造成功）
  echo "[LLM] 生成开发者摘要（同步）..."
  if timeout 600 ./scripts/report-llm.sh >> logs/llm.log 2>&1; then
    echo "[LLM] 摘要完成"
  else
    echo "[LLM] 摘要失败/超时（rc=$?），已记录，不伪造成功"
  fi

  # 4.5 全量模式：同步构建最新 mainline 验证可编译性（产物随本轮提交，杜绝跨轮混批）
  if [ "$FULL" -eq 1 ] && [ -x ./scripts/build-mainline.sh ]; then
    echo "[构建] mainline 构建（同步，最长 1800s）..."
    if timeout 1800 ./scripts/build-mainline.sh >> logs/build.log 2>&1; then
      echo "[构建] 完成"
    else
      echo "[构建] 失败/超时（rc=$?），报告已记录失败事实"
    fi
  fi

# 5. 提交：逐 repo 独立 commit + 聚合产物一个 commit
DATE_DIR="reports/$(date +%Y-%m-%d)"
REPO_COMMITS=0
# 5.1 变化仓库的详情文件逐个 commit（追踪每 repo 兼容性变化）
for _n in ${CHANGED_REPOS[@]:-}; do
  _f="$DATE_DIR/$_n.md"
  if [ -f "$_f" ] && ! git diff --quiet -- "$_f"; then
    git add "$_f"
    git -c user.name="dsh-ecosystem-bot" -c user.email="bot@dsh-external.local" \
      commit -q -m "index: $_n 兼容性更新（$(date +%Y-%m-%d_%H%M)）" && REPO_COMMITS=$((REPO_COMMITS+1))
  fi
done
# 5.2 聚合产物一个 commit —— 显式 allowlist（SOP：禁 git add -A，防日志/临时/密钥入库）
#     allowlist = 报告目录 + 产品文档 + 已跟踪状态文件
for _p in reports README.md CHANGELOG.md PLUGINS.md .support-status.json .runtime-test-state.json; do
  [ -e "$_p" ] && git add -- "$_p"
done
if git diff --cached --quiet; then
  echo "[提交] 无新内容，跳过 commit"
else
  git -c user.name="dsh-ecosystem-bot" -c user.email="bot@dsh-external.local" \
    commit -q -m "chore: 聚合产物更新 $(date +%Y-%m-%d_%H%M) — 变化:$CHANGED（repo 级 $REPO_COMMITS 个）" \
    && echo "[提交] repo 级 $REPO_COMMITS 个 + 聚合 1 个"
fi
else
  echo "[无变化] 全部仓库 HEAD 未变，跳过索引"
fi

# 5.5 每次运行后更新 README 自动状态节（兼容性汇总 + 跟踪中的 PR）
echo "[README] 更新自动状态节..."
if ./scripts/update-readme.sh >/dev/null 2>&1; then
  if ! git diff --quiet -- README.md; then
    git add README.md
    git -c user.name="dsh-ecosystem-bot" -c user.email="bot@dsh-external.local" \
      commit -m "chore: README 生态状态更新 $(date +%Y-%m-%d_%H%M)（兼容性汇总 + PR 跟踪）" || echo "[提示] README commit 失败"
  else
    echo "[README] 无变化（状态与 PR 列表未变）"
  fi
else
  echo "[README] 更新失败（gh 离线或解析错误），下次重试"
fi

# 5.6 推送：dsh-ext（org 主仓）为发布目标，失败即终止且不推进游标；origin 为备份尽力推送
if ! git push dsh-ext main 2>&1 | tail -2; then
  echo "[错误] push dsh-ext 失败——发布未确认，游标不推进，下次 cron 重试"
  exit 50
fi

# 6. 更新状态文件（仅在推送成功后推进游标——SOP：已发布 SHA 确认后才更新 published cursor）
write_cursor

echo "=== $(date -Is) cron-check 结束 ==="
exit 0
