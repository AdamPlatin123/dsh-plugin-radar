#!/usr/bin/env bash
# =============================================================================
# compare-mainline.sh — dsh-external 生态情报：与当日 mainline 快照的兼容性对比引擎
#
# 用法:
#   compare-mainline.sh [--scope <file>] [--dry-run] [--base <commit>]
#                       [--date <YYYY-MM-DD>] [--publish-issues] [--apply-fix]
#
# 选项:
#   --scope <file>       仅对比指定仓库清单（每行一个仓库名，# 注释；缺省为 15 仓库）
#   --dry-run            全程只读：不写报告 / CHANGELOG / 状态文件 / 软链 / 远程
#   --base <commit>      首次运行（无状态文件）时的 mainline 对比基线，默认 cab66cd
#   --date <YYYY-MM-DD>  报告日期目录，默认今天
#   --publish-issues     解析 actions/org-issues.md 草稿：默认仅打印将发布清单；
#                        非 dry-run 时逐条确认后 gh issue create（默认不执行远程写）
#   --apply-fix          输出待改 diff（如 catalog ref 滞后）；非 dry-run 时逐项确认后写本地 clone
#
# 退出码:
#   0 = 全部兼容        1 = 存在需适配        2 = 脚本错误        3 = 离线
#
# 依赖: bash / git / gh / jq（零第三方依赖；gh 仅 --publish-issues 用到）
# 私有约束: 本脚本产出内容脱敏 —— 不复制 issue 正文、真实密钥值、成员昵称。
# =============================================================================
set -uo pipefail

# ---- 常量 -------------------------------------------------------------------
MAINLINE_URL="https://github.com/dsh2026/test-AdamPlatin123"
ORG="dsh-external"
DEFAULT_REPOS=( issues dsh-live-stats dsh-working-activity plugin-registry sandbox-mxc \
                web-components dsh-opencode-server toybox ex-setting tg-bot \
                group-chat-diary dsh-skins dsh-coding-receipt qqbot dsh-subagent-tree )
# 非代码仓库（issue 跟踪 / 归档产物）：补丁、seam、peerDeps 维度记"不适用"
NONCODE_REPOS=( issues group-chat-diary )
# seam 符号 → 主仓库内代表路径（用于 prev/cur 两侧的存在性探测）
SEAM_SYMBOLS=( ThemeService settingsNamespace sessionProjections tuiPrompt slots session/event )
declare -A SEAM_PATH=(
  [ThemeService]="packages/client/ui-theme"
  [settingsNamespace]="packages/client/ui-settings"
  [sessionProjections]="packages/session-projection"
  [tuiPrompt]="packages/ui/tui"
  [slots]="packages/client/ui-slots"
  [session/event]="packages/session-persistence"
)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ---- 全局状态 ---------------------------------------------------------------
DRY_RUN=0
PUBLISH_ISSUES=0
APPLY_FIX=0
BASE_COMMIT="cab66cd"
DATE_ARG=""
SCOPE_FILE=""
VERBOSE=0

# 本次运行结果（跨函数共享）
MAINLINE=""            # mainline 工作树路径
MAINLINE_COMMIT=""     # 当日 mainline 完整 commit
MAINLINE_SHORT=""      # 短 commit
MAINLINE_BRANCH=""     # 快照分支名（不含 refs/remotes/origin/）
MAINLINE_LABEL=""      # 快照标签（如 20260804T143803Z-6feab99fdf）
PREV_COMMIT=""         # 上次记录 commit（首次 = --base）
STATE_FILE="$ROOT/.mainline-state.json"

declare -A ANCHOR_STR ANCHOR_TYPE ANCHOR_ST
# 普通 40 位 SHA（catalog pin，非 mainline/快照上下文），供 --apply-fix 定位旧 pin；不是锚定
declare -A CATALOG_REF
declare -A PATCH_ST     # OK / CONFLICT / 缺文件 / 无补丁 / 不适用
declare -A SEAM_ST      # "6/6 存在" / "缺: tuiPrompt" / 不适用
declare -A PEER_ST      # "2 项匹配" / "1 项不匹配" / 无 / 不适用
declare -A OVERALL      # 兼容 / 需适配 / 关注 / 占位 / 不适用 / 已删除 / 未知（待调研）/ 未知（无法确认）
REPO_GONE=()             # 本次运行确认已删除/迁移/改私有的仓库（git 404 + gh 404 双重确认，跳过不索引）
REPO_GONE_UNKNOWN=()     # git 报 repository not found 但 gh 交叉验证失败（网络/认证）→ 无法确认状态
declare -A REPO_HEAD    # 克隆 HEAD 短 commit

# ---- 小工具 -----------------------------------------------------------------
info()  { printf '[对比] %s\n' "$*"; }
warn()  { printf '[警告] %s\n' "$*" >&2; }
die()   { # $1=退出码 $2=消息
  local code="$1"; shift
  printf '[错误] %s\n' "$*" >&2
  exit "$code"
}

# 分类拉取失败：离线/认证 → 退出码 3；其他错误 → 退出码 2。
# 绝不静默降级为占位（新 clone 失败）或继续读旧缓存（fetch 失败）。
# 例外：repository not found（仓库被删除/迁移/改为私有）是确定性事实，不中断整体索引。
#   调用方在调用 fetch_fail 前先经 is_repo_gone() 拦截，标记"已删除"后跳过该仓库继续。
FETCH_ERR_NOT_FOUND=8
is_repo_gone() { # $1=git 错误输出 → 0=仓库不存在（应跳过） 1=其他
  printf '%s' "$1" | grep -qiE 'repository not found|not found|does not appear to be a git repository|404' \
    && ! printf '%s' "$1" | grep -qiE 'could not resolve host|connection (timed out|refused|reset)|unable to access' \
    && return 0
  return 1
}

fetch_fail() { # $1=对象（mainline/仓库名） $2=阶段 $3=git 输出
  local obj="$1" stage="$2" err="$3" first
  first="$(printf '%s' "$err" | sed '/^[[:space:]]*$/d' | head -1)"
  if is_repo_gone "$err"; then
    warn "仓库不存在（已删除/迁移/改为私有）→ 跳过并继续：$obj"
    return "$FETCH_ERR_NOT_FOUND"
  fi
  if printf '%s' "$err" | grep -qiE \
    'could not resolve host|connection (timed out|refused|reset)|network is unreachable|operation timed out|unable to access|authentication failed|access denied|access rights|permission denied|not authorized|403|terminal prompts disabled|connection reset by peer'; then
    die 3 "拉取 $obj 失败（$stage）：疑似离线/认证问题${first:+：$first}"
  fi
  die 2 "拉取 $obj 失败（$stage）${first:+：$first}"
}

# git 侧确认 repository not found（404）后，用 gh api 交叉验证，防网络/代理/认证误报：
#   gh 也 404            → 确认仓库已删除 → REPO_GONE（判定"已删除"）
#   gh 可访问（200）     → 仓库实际存在，git 侧疑似误报 → 脚本错误退出（exit 2）
#   gh 查询失败（网络等）→ 无法确认 → REPO_GONE_UNKNOWN（判定"未知（无法确认）"，而非"已删除"）
mark_repo_gone() { # $1=仓库名
  local name="$1" out rc
  out="$(timeout 30 gh api "repos/$ORG/$name" 2>&1)"; rc=$?
  if [ $rc -eq 0 ]; then
    die 2 "git 报仓库不存在但 gh api 可访问（$ORG/$name），git 侧疑似误报，请人工核查"
  fi
  if printf '%s' "$out" | grep -q 'HTTP 404'; then
    REPO_GONE+=("$name")
    warn "仓库不存在（git 404 + gh 404 双重确认）→ 标记已删除并跳过：$name"
  else
    REPO_GONE_UNKNOWN+=("$name")
    warn "git 404 但 gh api 交叉验证失败（无法确认仓库状态）→ 标记未知并跳过：$name"
  fi
}

# 逐项确认：提示与回答均走 /dev/tty（管道 / here-string 下 fd 0 非 TTY 也能交互）。
# 无可用 TTY 时拒绝执行写入（远程写 / 本地 clone 写）并说明原因，绝不静默通过。
confirm() { # $1=提示语 → 0=确认 1=拒绝
  local answer
  if ! printf '%s [y/N] ' "$1" > /dev/tty 2>/dev/null; then
    warn "无交互终端（/dev/tty 不可写），拒绝执行写入：$1"
    return 1
  fi
  if ! IFS= read -r answer < /dev/tty 2>/dev/null; then
    printf '\n' > /dev/tty 2>/dev/null
    warn "无交互终端（/dev/tty 不可读），拒绝执行写入：$1"
    return 1
  fi
  case "$answer" in y|Y) return 0 ;; *) return 1 ;; esac
}

usage() {
  cat <<'EOF'
compare-mainline.sh — 与当日 mainline 快照的兼容性对比引擎

用法:
  compare-mainline.sh [--scope <file>] [--dry-run] [--base <commit>]
                      [--date <YYYY-MM-DD>] [--publish-issues] [--apply-fix]

选项:
  --scope <file>       仅对比指定仓库清单（每行一个仓库名，# 注释；缺省为 15 仓库）
  --dry-run            全程只读：不写报告 / CHANGELOG / 状态文件 / 软链 / 远程
  --base <commit>      首次运行（无状态文件）时的 mainline 对比基线，默认 cab66cd
  --date <YYYY-MM-DD>  报告日期目录，默认今天
  --publish-issues     解析 actions/org-issues.md 草稿：默认仅打印将发布清单；
                       非 dry-run 时逐条确认后 gh issue create
  --apply-fix          输出待改 diff（如 catalog ref 滞后）；非 dry-run 时逐项确认后写本地 clone
  -h, --help           显示本帮助

退出码:
  0 = 全部兼容    1 = 存在需适配    2 = 脚本错误    3 = 离线
EOF
}

# ---- 参数解析 ---------------------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)        DRY_RUN=1 ;;
    --publish-issues) PUBLISH_ISSUES=1 ;;
    --apply-fix)      APPLY_FIX=1 ;;
    --verbose)        VERBOSE=1 ;;
    --base)           BASE_COMMIT="${2:-}"; shift
                      [ -n "$BASE_COMMIT" ] || die 2 "--base 需要 commit 参数" ;;
    --date)           DATE_ARG="${2:-}"; shift
                      [ -n "$DATE_ARG" ] || die 2 "--date 需要 YYYY-MM-DD 参数" ;;
    --scope)          SCOPE_FILE="${2:-}"; shift
                      [ -n "$SCOPE_FILE" ] || die 2 "--scope 需要文件参数" ;;
    -h|--help)        usage; exit 0 ;;
    *)                die 2 "未知参数: $1（用 --help 查看用法）" ;;
  esac
  shift
done

[[ "$BASE_COMMIT" =~ ^[0-9a-f]{7,40}$ ]] || die 2 "--base 必须是 git commit（7-40 位十六进制）: $BASE_COMMIT"
DATE="${DATE_ARG:-$(date +%F)}"
[[ "$DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || die 2 "日期格式必须为 YYYY-MM-DD: $DATE"

# ---- 仓库清单 ---------------------------------------------------------------
REPOS=()
if [ -n "$SCOPE_FILE" ]; then
  if [ -f "$SCOPE_FILE" ]; then SCOPE_PATH="$SCOPE_FILE"
  elif [ -f "$ROOT/$SCOPE_FILE" ]; then SCOPE_PATH="$ROOT/$SCOPE_FILE"
  else die 2 "找不到 --scope 文件: $SCOPE_FILE"
  fi
  while IFS= read -r line; do
    line="${line%%#*}"          # 去注释
    line="${line//[[:space:]]/}" # 去空白
    [ -n "$line" ] || continue
    # H2 防路径逃逸：仓库名仅允许 [a-zA-Z0-9._-]+（org 内）或 owner/name（topic 外部仓库）
    [[ "$line" =~ ^[a-zA-Z0-9._-]+$ || "$line" =~ ^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$ ]] || die 2 "非法仓库名（仅允许 [a-zA-Z0-9._-] 或 owner/name）: $line"
    [ "$line" != "." ] && [ "$line" != ".." ] || die 2 "非法仓库名（不允许 . 或 ..）: $line"
    REPOS+=( "$line" )
  done < "$SCOPE_PATH"
  [ "${#REPOS[@]}" -gt 0 ] || die 2 "--scope 文件未包含任何仓库名"
else
  REPOS=( "${DEFAULT_REPOS[@]}" )
fi

# ---- 依赖与网络预检 -----------------------------------------------------------
check_deps() {
  local missing=()
  for bin in bash git gh jq; do
    command -v "$bin" >/dev/null 2>&1 || missing+=( "$bin" )
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    die 2 "缺少依赖: ${missing[*]}（需要 bash/git/gh/jq，均为标准 CLI）"
  fi
}

check_network() {
  if ! git ls-remote --heads "$MAINLINE_URL" 'refs/heads/snapshots/*' >/dev/null 2>&1; then
    die 3 "网络预检失败：无法访问 $MAINLINE_URL（git ls-remote 失败，判定离线）"
  fi
}

# ---- 缓存目录 ---------------------------------------------------------------
# dry-run 全程只读：缓存（.mainline/.clones）放到临时目录，结束即删
CACHE_DIR="$ROOT"
if [ "$DRY_RUN" -eq 1 ]; then
  CACHE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/mainline-dryrun.XXXXXX")" \
    || die 2 "创建 dry-run 临时缓存目录失败"
  trap 'rm -rf "$CACHE_DIR"' EXIT
fi
MAINLINE="$CACHE_DIR/.mainline"
CLONES_DIR="$CACHE_DIR/.clones"
REPORTS_DIR="$ROOT/reports/$DATE"
mkdir -p "$CLONES_DIR" || die 2 "创建克隆缓存目录失败: $CLONES_DIR"

# ---- 1. 拉取 mainline（快照全部分支，取最新） -------------------------------
mainline_fetch() {
  local merr
  if [ ! -d "$MAINLINE/.git" ]; then
    info "克隆 mainline（blob:none，仅元数据）..."
    merr="$(mktemp)"
    if ! git clone --quiet --filter=blob:none --no-checkout "$MAINLINE_URL" "$MAINLINE" 2>"$merr"; then
      fetch_fail "mainline" "clone" "$(cat "$merr")"
    fi
    rm -f "$merr"
    chmod 700 "$MAINLINE" 2>/dev/null || true
  fi
  info "拉取 mainline 快照分支..."
  merr="$(mktemp)"
  if ! git -C "$MAINLINE" fetch --quiet origin '+refs/heads/snapshots/*:refs/remotes/origin/snapshots/*' 2>"$merr"; then
    fetch_fail "mainline" "fetch" "$(cat "$merr")"
  fi
  rm -f "$merr"
  local branch
  branch="$(git -C "$MAINLINE" for-each-ref --sort=-refname \
             --format='%(refname:short)' 'refs/remotes/origin/snapshots/*' | head -1)"
  [ -n "$branch" ] || die 2 "mainline 无快照分支（refs/heads/snapshots/* 为空）"
  MAINLINE_BRANCH="${branch#origin/}"
  MAINLINE_COMMIT="$(git -C "$MAINLINE" rev-parse "$branch")" || die 2 "解析快照分支失败"
  MAINLINE_SHORT="${MAINLINE_COMMIT:0:7}"
  MAINLINE_LABEL="${MAINLINE_BRANCH#snapshots/}"
  MAINLINE_LABEL="${MAINLINE_LABEL%-[0-9a-f]*}"   # 去掉尾部 hash 后缀，对齐契约展示约定
  info "mainline 当日: $MAINLINE_SHORT（$MAINLINE_LABEL）"
  git -C "$MAINLINE" checkout --quiet -f -B mainline-check "$branch" 2>/dev/null \
    || git -C "$MAINLINE" checkout --quiet -f "$branch" \
    || die 2 "切换到快照分支失败"
}

# ---- 2. 克隆/更新 15 仓库 ----------------------------------------------------
repo_fetch() {
  # name 支持 bare（org 内，补 dsh-external 前缀）或 full_name（owner/name，topic 打标的外部仓库）
  local name="$1" bare="${1##*/}" dir="" url="" lsref merr head dir_real clones_real
  case "$name" in */*) ;; *) name="dsh-external/$name" ;; esac
  dir="$CLONES_DIR/$bare"
  url="https://github.com/$name.git"
  # H2 防路径逃逸：仓库名白名单（允许点，仍拒绝 . / ..）+ realpath 校验 .clones/<bare> 仍在 .clones/ 内
  [[ "$bare" =~ ^[a-zA-Z0-9._-]+$ ]] || die 2 "非法仓库名: $name"
  [ "$bare" != "." ] && [ "$bare" != ".." ] || die 2 "非法仓库名（不允许 . 或 ..）: $name"
  dir_real="$(realpath -m "$dir")"
  clones_real="$(realpath -m "$CLONES_DIR")"
  case "$dir_real" in
    "$clones_real"/*) ;;  # 正常：克隆目录在 .clones/ 下
    *) die 2 "仓库克隆路径逃逸（$dir_real 不在 $clones_real 内）: $name" ;;
  esac
  # H3 先探测远端 ref：clone/fetch 网络/认证错误在动手前就暴露，空仓与拉取失败从此区分
  lsref="$(git ls-remote --heads "$url" 2>&1)"     || { sleep 4; lsref="$(git ls-remote --heads "$url" 2>&1)"; }     || { fetch_fail "$name" "ls-remote" "$lsref" || { mark_repo_gone "$name"; return 0; }; }
  if [ -z "$lsref" ]; then
    # 空仓：远端可达但无任何 ref（clone 成功但 ls-remote 无 ref）→ 占位，非拉取失败
    if [ ! -d "$dir/.git" ]; then
      merr="$(mktemp)"
      if ! git clone --quiet --depth 1 "$url" "$dir" >/dev/null 2>"$merr"; then
        sleep 4
        if ! git clone --quiet --depth 1 "$url" "$dir" >/dev/null 2>"$merr"; then
          fetch_fail "$name" "clone(空仓初始化)" "$(cat "$merr")" || { mark_repo_gone "$name"; return 0; }
        fi
      fi
      rm -f "$merr"
    fi
    REPO_HEAD[$name]=""
    return 0
  fi
  merr="$(mktemp)"
  if [ ! -d "$dir/.git" ]; then
    if ! git clone --quiet --depth 1 "$url" "$dir" >/dev/null 2>"$merr"; then
      sleep 4
      if ! git clone --quiet --depth 1 "$url" "$dir" >/dev/null 2>"$merr"; then
        fetch_fail "$name" "clone" "$(cat "$merr")" || { mark_repo_gone "$name"; return 0; }
      fi
    fi
  else
    if ! git -C "$dir" fetch --quiet --depth 1 origin HEAD >/dev/null 2>"$merr"; then
      sleep 4
      if ! git -C "$dir" fetch --quiet --depth 1 origin HEAD >/dev/null 2>"$merr"; then
        fetch_fail "$name" "fetch" "$(cat "$merr")" || { mark_repo_gone "$name"; return 0; }
      fi
    fi
    git -C "$dir" reset --hard --quiet FETCH_HEAD >/dev/null 2>&1 \
      || die 2 "重置 $name 到 FETCH_HEAD 失败"
  fi
  rm -f "$merr"
  head="$(git -C "$dir" rev-parse --short HEAD 2>/dev/null)" \
    || die 2 "$name 克隆/更新后无 HEAD（异常，非空仓）"
  REPO_HEAD[$name]="$head"
  return 0
}

# ---- 3. 索引：research 集成点 + 克隆证据 --------------------------------------
# 锚定探测：research 集成点节 + 克隆 README → 输出 ANCHOR_STR / ANCHOR_TYPE / CATALOG_REF。
# M2：仅在与 mainline/快照上下文明确关联的位置提取锚定（README 的 snapshot-<date> 标签、
# 快照分支引用、补丁头注明的基线 commit、行内含 mainline/快照/snapshot/harness 的 commit 引用）；
# 普通 40 位 SHA（如插件发布 pin）归入 CATALOG_REF（catalog ref），不当锚定。
anchor_detect() {
  local name="$1" txt="" readme="" probe="" h="" hs="" pf base ctxline plain ctx_anchor
  ANCHOR_STR[$name]=""; ANCHOR_TYPE[$name]=""; CATALOG_REF[$name]=""
  txt="$(sed -n '/^## *与 DeepSeek Harness 主仓库的集成点/,/^## /p' "$ROOT/research/$name.md" 2>/dev/null)"
  if [ -d "$CLONES_DIR/$name/.git" ]; then
    readme="$(cat "$CLONES_DIR/$name"/README* 2>/dev/null)"
  fi
  probe="$txt"$'\n'"$readme"

  # ---- catalog ref：非锚定的普通 40 位 SHA（插件发布 pin 等），供 --apply-fix 定位旧 pin ----
  ctxline="$(printf '%s' "$probe" | grep -iE 'mainline|快照|snapshot|harness')"
  # 预取上下文行会被提取为锚定的 hash（规则 1-2）：与锚定同名的 hash 不当作 catalog ref
  ctx_anchor="$(printf '%s' "$probe" | grep -oE 'snapshot-[0-9]{8}T[0-9]{6}Z-([0-9a-f]{7,40})' | grep -oE '[0-9a-f]{7,40}$' | head -1)"
  [ -n "$ctx_anchor" ] || ctx_anchor="$(printf '%s' "$ctxline" | grep -oE '(commit|master|main|基线)[ /:`]*[0-9a-f]{7,40}' | grep -oE '[0-9a-f]{7,40}$' | head -1)"
  [ -n "$ctx_anchor" ] || ctx_anchor="$(printf '%s' "$ctxline" | grep -oE '\b[0-9a-f]{40}\b' | head -1)"
  plain="$(printf '%s' "$probe" | grep -viE 'mainline|快照|snapshot|harness' | grep -oE '\b[0-9a-f]{40}\b' | sort -u | head -1)"
  if [ -n "$plain" ] && [ "$plain" != "$ctx_anchor" ]; then
    CATALOG_REF[$name]="$plain"
  fi

  # ---- 锚定提取（仅 mainline/快照上下文）----
  # 1) snapshot-<ts>-<hash> 完整标签：尾部 hash 即快照 commit（最权威）
  h="$(printf '%s' "$probe" | grep -oE 'snapshot-[0-9]{8}T[0-9]{6}Z-([0-9a-f]{7,40})' | grep -oE '[0-9a-f]{7,40}$' | head -1)"
  if [ -n "$h" ]; then ANCHOR_STR[$name]="$h"; ANCHOR_TYPE[$name]="commit"; return 0; fi
  # 2) 上下文行内的 commit 引用（行含 mainline/快照/snapshot/harness 词）
  ctxline="$(printf '%s' "$probe" | grep -iE 'mainline|快照|snapshot|harness')"
  h="$(printf '%s' "$ctxline" | grep -oE '(commit|master|main|基线)[ /:`]*[0-9a-f]{7,40}' | grep -oE '[0-9a-f]{7,40}$' | head -1)"
  if [ -n "$h" ]; then ANCHOR_STR[$name]="$h"; ANCHOR_TYPE[$name]="commit"; return 0; fi
  h="$(printf '%s' "$ctxline" | grep -oE '\b[0-9a-f]{40}\b' | head -1)"
  if [ -n "$h" ]; then ANCHOR_STR[$name]="$h"; ANCHOR_TYPE[$name]="commit"; return 0; fi
  # 3) snapshot-<ts> 标签（无 hash）
  h="$(printf '%s' "$probe" | grep -oE 'snapshot-[0-9]{8}T[0-9]{6}Z' | head -1)"
  if [ -n "$h" ]; then ANCHOR_STR[$name]="$h"; ANCHOR_TYPE[$name]="label"; return 0; fi
  # 4) "快照 <ts>" / "snapshot <ts>"（允许空格/冒号/反引号分隔）
  h="$(printf '%s' "$probe" | grep -oE '(快照|snapshot)[ ：`]*[0-9]{8}T[0-9]{6}Z' | grep -oE '[0-9]{8}T[0-9]{6}Z' | head -1)"
  if [ -n "$h" ]; then ANCHOR_STR[$name]="$h"; ANCHOR_TYPE[$name]="label"; return 0; fi
  # 5) 快照分支引用（snapshots/<label>；带 -<hash> 后缀时取 hash）
  h="$(printf '%s' "$probe" | grep -oE '(refs/remotes/origin/)?snapshots/[0-9A-Za-z-]+' | grep -oE '[0-9A-Za-z-]+$' | head -1)"
  if [ -n "$h" ]; then
    hs="${h##*-}"
    if [[ "$hs" =~ ^[0-9a-f]{7,40}$ ]]; then
      ANCHOR_STR[$name]="$hs"; ANCHOR_TYPE[$name]="commit"; return 0
    fi
    ANCHOR_STR[$name]="$h"; ANCHOR_TYPE[$name]="label"; return 0
  fi
  # 6) 补丁头注明的基线 commit（patches/*.patch 内 40 位 hash）
  for pf in "$CLONES_DIR/$name"/patches/*.patch; do
    [ -f "$pf" ] || continue
    base="$(grep -oE '\b[0-9a-f]{40}\b' "$pf" | head -1)"
    if [ -n "$base" ]; then ANCHOR_STR[$name]="$base"; ANCHOR_TYPE[$name]="commit"; return 0; fi
  done
  # 7) 兜底：非上下文中的 "commit <hash>" 短引用 → catalog ref（非锚定）
  h="$(printf '%s' "$probe" | grep -viE 'mainline|快照|snapshot|harness' | grep -oE 'commit[ :`]*[0-9a-f]{7,40}' | grep -oE '[0-9a-f]{7,40}$' | head -1)"
  if [ -n "$h" ] && [ -z "${CATALOG_REF[$name]}" ]; then CATALOG_REF[$name]="$h"; fi
  ANCHOR_STR[$name]="未知"
  ANCHOR_TYPE[$name]="unknown"
  [ -n "${CATALOG_REF[$name]}" ] && ANCHOR_TYPE[$name]="catalog"
}

# 锚定分类：对齐 / 落后 / 超前 / 未知（不同谱系）
anchor_classify() {
  local name="$1" a="" t=""
  a="${ANCHOR_STR[$name]:-}"
  t="${ANCHOR_TYPE[$name]:-}"
  ANCHOR_ST[$name]=""
  # catalog ref：插件自身发布 pin，与 mainline 谱系无关，不参与对齐/落后判定
  if [ "$t" = "catalog" ]; then
    ANCHOR_ST[$name]="未知（catalog ref，非 mainline 锚定）"
    return 0
  fi
  [ "$a" = "未知" ] && { ANCHOR_ST[$name]="未知"; return 0; }
  if [ "$t" != "commit" ]; then
    ANCHOR_ST[$name]="未知（非 commit 锚定: $a）"
    return 0
  fi
  if [ "$a" = "$MAINLINE_COMMIT" ]; then ANCHOR_ST[$name]="对齐"; return 0; fi
  if git -C "$MAINLINE" merge-base --is-ancestor "$a" "$MAINLINE_COMMIT" 2>/dev/null; then
    ANCHOR_ST[$name]="落后"
  elif git -C "$MAINLINE" merge-base --is-ancestor "$MAINLINE_COMMIT" "$a" 2>/dev/null; then
    ANCHOR_ST[$name]="超前"
  else
    ANCHOR_ST[$name]="未知（不同谱系）"
  fi
}

# 补丁检查：对 .mainline/ 逐个 git apply --check --3way
patch_check() {
  local name="$1" dir=""
  dir="$CLONES_DIR/$name"
  local patch_dir="$dir/patches"
  local out rc f
  PATCH_ST[$name]="无补丁"
  [ -d "$patch_dir" ] || return 0
  local files=()
  for f in "$patch_dir"/*.patch; do [ -f "$f" ] && files+=( "$f" ); done
  [ "${#files[@]}" -gt 0 ] || return 0
  local any_conflict=0 any_missing=0 applied=0
  for f in "${files[@]}"; do
    out="$(git -C "$MAINLINE" apply --check --3way "$f" 2>&1)"; rc=$?
    if [ $rc -eq 0 ]; then applied=$((applied+1))
    elif printf '%s' "$out" | grep -q 'No such file or directory'; then any_missing=1
    else any_conflict=1; fi
    [ "$VERBOSE" -eq 1 ] && printf '  %s => rc=%d\n%s\n' "$(basename "$f")" "$rc" "$out" | head -8
  done
  if [ $any_missing -eq 1 ]; then PATCH_ST[$name]="缺文件（${#files[@]} 个补丁中 $applied 个 OK）"
  elif [ $any_conflict -eq 1 ]; then PATCH_ST[$name]="CONFLICT（${#files[@]} 个补丁中 $applied 个 OK）"
  else PATCH_ST[$name]="OK（${#files[@]} 个补丁全部干净应用）"; fi
}

# seam 存在性：cur 用工作树 grep；mainline 两提交侧的符号级对比见 mainline_diff_analyze（git grep）
seam_check() {
  local name="$1" sym missing=() present=0 total=${#SEAM_SYMBOLS[@]}
  local n
  for sym in "${SEAM_SYMBOLS[@]}"; do
    n="$(grep -rlF -- "$sym" "$MAINLINE/packages" 2>/dev/null | wc -l)"
    if [ "$n" -gt 0 ]; then present=$((present+1)); else missing+=( "$sym" ); fi
  done
  if [ "${#missing[@]}" -eq 0 ]; then SEAM_ST[$name]="$present/$total 存在"
  else SEAM_ST[$name]="缺: ${missing[*]}"; fi
}

# workspace 版本查找：在 .mainline/packages/*/*/package.json 按包名找 version
workspace_version() {
  local f v
  for f in "$MAINLINE"/packages/*/*/package.json; do
    [ -f "$f" ] || continue
    v="$(jq -r --arg n "$1" 'select(.name==$n) | .version' "$f" 2>/dev/null)"
    if [ -n "$v" ] && [ "$v" != "null" ]; then printf '%s' "$v"; return 0; fi
  done
  return 1
}

# peerDeps/deps 提取：打印 "name<TAB>range<TAB>peer|dep"
extract_dsh_deps() {
  local dir="$1" f
  while IFS= read -r f; do
    jq -r '.peerDependencies // {} | to_entries[] | select((.key|ascii_downcase|contains("dsh"))) | [(.key),(.value),"peer"] | join("\t")' "$f" 2>/dev/null
    jq -r '.dependencies // {} | to_entries[] | select((.key|ascii_downcase|contains("dsh"))) | [(.key),(.value),"dep"] | join("\t")' "$f" 2>/dev/null
  done < <(find "$dir" -name package.json -not -path '*/node_modules/*' -not -path '*/.git/*' 2>/dev/null)
}

peer_check() {
  local name="$1" dir="" line dep range kind wsver verdict
  dir="$CLONES_DIR/$name"
  local total=0 mism=0 miss_detail=""
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    dep="${line%%$'\t'*}"; rest="${line#*$'\t'}"; range="${rest%%$'\t'*}"
    total=$((total+1))
    wsver="$(workspace_version "$dep")"
    if [ -z "$wsver" ]; then verdict="外部（非 workspace 包）"
    elif [[ "$range" == workspace:* || "$range" == link:* || "$range" == "*" ]]; then verdict="匹配（workspace 协议）"
    elif [[ "$range" == *"$wsver"* ]]; then verdict="匹配"
    else verdict="不匹配"; mism=$((mism+1)); miss_detail="$miss_detail $dep=$range↔$wsver"; fi
    [ "$VERBOSE" -eq 1 ] && printf '  peerDeps %s %s => %s\n' "$dep" "$range" "$verdict"
  done < <(extract_dsh_deps "$dir")
  if [ "$total" -eq 0 ]; then PEER_ST[$name]="无 dsh-* 依赖"
  elif [ "$mism" -eq 0 ]; then PEER_ST[$name]="$total 项匹配"
  else PEER_ST[$name]="$total 项中 $mism 不匹配:$miss_detail"; fi
}

# seam 符号 → 检索关键词（判断该面是否与本仓库相关）
seam_keyword() {
  case "$1" in
    ThemeService)     echo "theme" ;;
    settingsNamespace) echo "settings" ;;
    sessionProjections) echo "projection" ;;
    tuiPrompt)        echo "tui" ;;
    slots)            echo "slots" ;;
    session/event)    echo "session/event" ;;
    *)                echo "$1" ;;
  esac
}

# 综合判定（优先级：占位 > 需适配 > 关注 > 兼容/不适用；未建模仓库不自动判兼容）
overall_judge() {
  local name="$1"
  local is_noncode=0 n sym kw txt seam_hit=0 no_patch=0 no_anchor=0
  for g in "${REPO_GONE[@]:-}"; do [ "$g" = "$name" ] && { OVERALL[$name]="已删除"; return 0; }; done
  for g in "${REPO_GONE_UNKNOWN[@]:-}"; do [ "$g" = "$name" ] && { OVERALL[$name]="未知（无法确认）"; return 0; }; done
  for n in "${NONCODE_REPOS[@]}"; do [ "$n" = "$name" ] && is_noncode=1; done
  # 空仓库（占位）
  if [ -z "${REPO_HEAD[$name]:-}" ]; then OVERALL[$name]="占位"; return 0; fi
  if [ $is_noncode -eq 1 ]; then OVERALL[$name]="不适用"; return 0; fi
  # 未建模仓库（无 research/<name>.md）：不自动判兼容 —— 无补丁且无锚定时标记"未知（待调研）"
  if [ ! -f "$ROOT/research/$name.md" ]; then
    case "${PATCH_ST[$name]:-}" in 无补丁|"") no_patch=1 ;; esac
    case "${ANCHOR_STR[$name]:-}" in ""|未知) no_anchor=1 ;; esac
    if [ "$no_patch" -eq 1 ] && [ "$no_anchor" -eq 1 ]; then
      OVERALL[$name]="未知（待调研）"
      return 0
    fi
  fi
  # seam 缺失面是否与仓库集成点相关（避免 tuiPrompt 缺失误伤所有仓库）
  if [[ "${SEAM_ST[$name]}" == 缺:* ]]; then
    txt="$(sed -n '/^## *与 DeepSeek Harness 主仓库的集成点/,/^## /p' "$ROOT/research/$name.md" 2>/dev/null)"
    for sym in "${SEAM_SYMBOLS[@]}"; do
      [[ "${SEAM_ST[$name]}" == *"$sym"* ]] || continue
      kw="$(seam_keyword "$sym")"
      if printf '%s' "$txt" | grep -qi "$kw"; then seam_hit=1; fi
    done
  fi
  case "${PATCH_ST[$name]}" in
    CONFLICT*) OVERALL[$name]="需适配"; return 0 ;;
    缺文件*)   OVERALL[$name]="需适配"; return 0 ;;
  esac
  case "${ANCHOR_ST[$name]}" in
    落后)
      # 锚定滞后不再直接判需适配：相关 seam 缺失仍升级为需适配，否则仅关注
      if [ $seam_hit -eq 1 ]; then OVERALL[$name]="需适配（滞后 mainline，相关 seam 缺失）"; return 0; fi
      OVERALL[$name]="关注（锚定滞后 mainline）"; return 0 ;;
  esac
  if [ $seam_hit -eq 1 ] || [[ "${PEER_ST[$name]}" == *不匹配* ]]; then
    OVERALL[$name]="关注"; return 0
  fi
  OVERALL[$name]="兼容"
}

# ---- 4. mainline 自身变更分析 -------------------------------------------------
declare -A SEAM_PREV SEAM_CUR
BASELINE_AVAILABLE=1    # PREV_COMMIT 对象是否可解析（缺失 → 基线不可用，seam 变化无法对比）

# seam 符号在指定 commit 内是否出现：git grep 探测（0=出现 1=未出现 2=探测失败/对象不可读）
seam_in_commit() { # $1=commit $2=符号
  local rc
  git -C "$MAINLINE" grep -qF "$2" "$1" -- packages/ >/dev/null 2>&1
  rc=$?
  if [ "$rc" -eq 0 ]; then return 0
  elif [ "$rc" -eq 1 ]; then return 1
  else return 2; fi
}

mainline_diff_analyze() {
  local sym rc
  # 基线对象存在性：PREV_COMMIT 缺失 → 无法对比（基线不可用），不据此误判破坏性变更
  if ! git -C "$MAINLINE" cat-file -e "$PREV_COMMIT^{commit}" 2>/dev/null; then
    warn "mainline 基线 $PREV_COMMIT 对象不存在，seam 变化对比不可用（基线不可用）"
    BASELINE_AVAILABLE=0
  fi
  for sym in "${SEAM_SYMBOLS[@]}"; do
    if [ "$BASELINE_AVAILABLE" -eq 1 ]; then
      seam_in_commit "$PREV_COMMIT" "$sym"; rc=$?
      if [ "$rc" -eq 0 ]; then SEAM_PREV[$sym]=1
      elif [ "$rc" -eq 2 ]; then SEAM_PREV[$sym]=""; warn "seam 符号 $sym 在 $PREV_COMMIT 探测失败（对象不可读）"
      else SEAM_PREV[$sym]=0; fi
    else
      SEAM_PREV[$sym]=""
    fi
    seam_in_commit "$MAINLINE_COMMIT" "$sym"; rc=$?
    if [ "$rc" -eq 0 ]; then SEAM_CUR[$sym]=1
    elif [ "$rc" -eq 2 ]; then SEAM_CUR[$sym]=""; warn "seam 符号 $sym 在 $MAINLINE_COMMIT 探测失败（对象不可读）"
    else SEAM_CUR[$sym]=0; fi
  done
}

# ---- 5-6. 报告 / 更新 ---------------------------------------------------------
build_reports() {
  local name row
  local matrix_rows="" detail_all="" sugg_plugin="" sugg_main=""
  local ok=0 adapt=0 watch=0 placeholder=0 na=0 gone=0 unknown=0
  local adapt_names=""

  for name in "${REPOS[@]}"; do
    case "${OVERALL[$name]}" in
      兼容) ok=$((ok+1)) ;;
      需适配*) adapt=$((adapt+1)); adapt_names="$adapt_names $name" ;;
      关注) watch=$((watch+1)) ;;
      占位) placeholder=$((placeholder+1)) ;;
      不适用) na=$((na+1)) ;;
      已删除) gone=$((gone+1)) ;;
      未知*) unknown=$((unknown+1)) ;;
    esac
  done
  adapt_names="$(printf '%s' "$adapt_names" | xargs)"

  # ---- 矩阵行 ----
  for name in "${REPOS[@]}"; do
    row="| $name | ${ANCHOR_ST[$name]:-未知} | ${PATCH_ST[$name]:-无补丁} | ${SEAM_ST[$name]:-不适用} | ${PEER_ST[$name]:-无} | ${OVERALL[$name]} |"
    matrix_rows="$matrix_rows
$row"
  done

  # ---- mainline 变更分析内容 ----
  local changes="" deleted_pkgs="" added_files="" removed_patches="" seam_delta=""
  local diffstat prev_n cur_n
  deleted_pkgs="$(git -C "$MAINLINE" diff --name-status "$PREV_COMMIT" "$MAINLINE_COMMIT" -- packages/ 2>/dev/null \
    | awk '$1=="D"{print $2}' | sed -E 's#(packages/[^/]+/[^/]+)/.*#\1#' | sort -u)"
  # M3 删包判定：仅当目标提交中包目录或 manifest 已不存在才算整包删除（单文件删除不算）
  local pkg_del="" p
  for p in $deleted_pkgs; do
    # 候选必须是 prev 提交中的真实包目录（含 package.json），排除 packages/ 根下散文件
    git -C "$MAINLINE" cat-file -e "$PREV_COMMIT:$p/package.json" 2>/dev/null || continue
    # 目标提交仍有残留（目录与 manifest 都在）→ 只是包内删了部分文件
    if git -C "$MAINLINE" ls-tree -d "$MAINLINE_COMMIT" "$p" 2>/dev/null | grep -q . \
       && git -C "$MAINLINE" cat-file -e "$MAINLINE_COMMIT:$p/package.json" 2>/dev/null; then
      continue
    fi
    pkg_del="$pkg_del
$p"
  done
  deleted_pkgs="$(printf '%s' "$pkg_del" | sed '/^$/d' | sort -u)"
  added_files="$(git -C "$MAINLINE" diff --name-status "$PREV_COMMIT" "$MAINLINE_COMMIT" -- packages/ 2>/dev/null \
    | awk '$1=="A"{print $2}' | head -15)"
  removed_patches="$(git -C "$MAINLINE" diff --name-status "$PREV_COMMIT" "$MAINLINE_COMMIT" -- patches/ 2>/dev/null \
    | awk '$1=="D"{print $2}')"
  diffstat="$(git -C "$MAINLINE" diff --stat "$PREV_COMMIT" "$MAINLINE_COMMIT" -- packages/ patches/ pnpm-workspace.yaml 2>/dev/null | tail -n +1)"

  SUMMARY_BULLETS=""   # 供 CHANGELOG 使用的变更摘要（全局）
  # 关键变更条目（≥3）
  prev_n="${SEAM_PREV[tuiPrompt]}"; cur_n="${SEAM_CUR[tuiPrompt]}"
  if [ "${prev_n:-0}" -gt 0 ] && [ "${cur_n:-0}" -eq 0 ]; then
    changes="$changes
- **TUI 组件包移除**：packages/ui/tui 的 tuiPrompt 符号从 mainline 消失（出现 → 消失），pi-tui 补丁与相关 Agent Notes 归档。"
  fi
  if [ "$BASELINE_AVAILABLE" -eq 0 ]; then
    changes="$changes
- **基线不可用**：上次对比基线 \`$PREV_COMMIT\` 对象在 mainline 本地不存在，seam 符号变化与 diff 对比无法执行。"
  fi
  if git -C "$MAINLINE" cat-file -e "$MAINLINE_COMMIT:packages/client/connection/src/websocket-downlink.ts" 2>/dev/null; then
    changes="$changes
- **WebSocket 下行通道新增**：packages/client/connection/src/websocket-downlink.ts 及其测试进入 mainline（架构 note 2026-08-04-websocket-downlink-carrier），远程通道类插件可对齐。"
  fi
  local ws_added
  ws_added="$(git -C "$MAINLINE" diff "$PREV_COMMIT" "$MAINLINE_COMMIT" -- pnpm-workspace.yaml 2>/dev/null | grep -E '^\+' | grep -vE '^\+\+\+' | grep -E '@|workspace' | head -5)"
  if [ -n "$ws_added" ]; then
    changes="$changes
- **workspace catalog 变更**：pnpm-workspace.yaml 增补条目（$([ "$VERBOSE" -eq 1 ] && printf '%s' "$ws_added" | tr '\n' ';' || echo 见 diffstat)）。"
  fi
  if [ -n "$removed_patches" ]; then
    changes="$changes
- **host 补丁移除**：$(printf '%s' "$removed_patches" | tr '\n' ' ')。"
  fi
  local dcount acount
  dcount="$(printf '%s' "$deleted_pkgs" | sed '/^$/d' | wc -l)"
  acount="$(printf '%s' "$added_files" | sed '/^$/d' | wc -l)"
  changes="$changes
- **包级变化**：packages/ 下删除 $dcount 个包目录、新增 $acount 个文件（diffstat 见下）。"
  # 供 CHANGELOG 的简短摘要（取前 4 条，去掉 markdown 强调）
  SUMMARY_BULLETS="$(printf '%s' "$changes" | sed '/^$/d' | sed -E 's/^- \*\*([^*]+)\*\*：/\1：/' | head -4 | tr '\n' ' ')"

  # seam 符号变化表（存在性：出现 / 消失；基线不可用或探测失败时如实标注）
  local seam_lines="" state="" prev_v="" cur_v=""
  for sym in "${SEAM_SYMBOLS[@]}"; do
    prev_n="${SEAM_PREV[$sym]}"; cur_n="${SEAM_CUR[$sym]}"
    if [ "$BASELINE_AVAILABLE" -eq 0 ]; then
      state="基线不可用（$PREV_COMMIT 对象缺失）"; prev_v="—"; cur_v="—"
    elif [ -z "$prev_n" ] || [ -z "$cur_n" ]; then
      state="未知（探测失败）"; prev_v="—"; cur_v="—"
    elif [ "$prev_n" -eq 1 ] && [ "$cur_n" -eq 1 ]; then state="出现 → 出现（稳定）"; prev_v="出现"; cur_v="出现"
    elif [ "$prev_n" -eq 1 ] && [ "$cur_n" -eq 0 ]; then state="出现 → 消失（破坏性）"; prev_v="出现"; cur_v="消失"
    elif [ "$prev_n" -eq 0 ] && [ "$cur_n" -eq 1 ]; then state="消失 → 出现（新增）"; prev_v="消失"; cur_v="出现"
    else state="消失 → 消失"; prev_v="消失"; cur_v="消失"; fi
    seam_lines="$seam_lines
| \`$sym\` | $prev_v | $cur_v | $state |"
  done

  # 破坏性变更清单
  local breaking="" sym
  for sym in "${SEAM_SYMBOLS[@]}"; do
    if [ "${SEAM_PREV[$sym]:-0}" -gt 0 ] && [ "${SEAM_CUR[$sym]:-0}" -eq 0 ]; then
      breaking="$breaking
- \`$sym\`（${SEAM_PATH[$sym]}）：随 mainline 消失，依赖该面的插件需改适配。"
    fi
  done
  [ -z "$breaking" ] && breaking="
- 本日快照未发现 seam 符号级破坏。"
  if [ -n "$deleted_pkgs" ]; then
    breaking="$breaking
- 删除的包目录：$(printf '%s' "$deleted_pkgs" | tr '\n' ' ')。"
  fi

  # ---- 插件侧建议（每仓库 1-3 条，共 ≥15） ----
  for name in "${REPOS[@]}"; do
    sugg_plugin="$sugg_plugin
### $name"
    case "${OVERALL[$name]}" in
      占位)
        sugg_plugin="$sugg_plugin
- 占位仓库（0 commit），无集成点可对比；建议首个 commit 落地后再纳入兼容跟踪。"
        case "$name" in
          dsh-opencode-server) sugg_plugin="$sugg_plugin
- 定位与 TUI 移除直接相关（opencode 替换 TUI），值得跟踪首 commit。"
          ;;
          dsh-coding-receipt) sugg_plugin="$sugg_plugin
- 输入来自 DSH session log，建议在 mainline 会话持久化格式稳定后实现。"
          ;;
        esac
        ;;
      不适用)
        sugg_plugin="$sugg_plugin
- 非代码仓库（issue 跟踪 / 归档产物），无代码级集成，不参与补丁/seam 对比。"
        ;;
      需适配*)
        sugg_plugin="$sugg_plugin
- 需适配：锚定 ${ANCHOR_STR[$name]}（${ANCHOR_ST[$name]}）、补丁状态「${PATCH_ST[$name]}」；建议以当日 snapshot HEAD（$MAINLINE_SHORT）为新基线重新锚定/rebuild 补丁。"
        [ "${PATCH_ST[$name]}" = "无补丁" ] || sugg_plugin="$sugg_plugin
- 补丁冲突/缺文件点集中在 mainline 变更分析节列出的破坏面，优先把集成改到稳定 seam（slots/sessionProjections/ThemeService）上。"
        ;;
      关注)
        sugg_plugin="$sugg_plugin
- 关注：seam 或 peerDeps 存在不匹配（seam: ${SEAM_ST[$name]}；peer: ${PEER_ST[$name]}），建议确认所依赖的宿主面当日是否仍满足。"
        ;;
      未知*)
        sugg_plugin="$sugg_plugin
- 未建模/状态未知：尚无 research/$name.md 调研摘要（或 git/gh 无法确认仓库状态），不做兼容性结论；建议先完成调研建模或人工核查后再纳入兼容跟踪。"
        ;;
      *)
        sugg_plugin="$sugg_plugin
- 兼容：锚定 ${ANCHOR_STR[$name]}（${ANCHOR_ST[$name]}）、补丁「${PATCH_ST[$name]}」，当日 mainline 可干净集成。"
        if [ "${PATCH_ST[$name]}" != "无补丁" ]; then
          sugg_plugin="$sugg_plugin
- 建议把补丁基线从 ${ANCHOR_STR[$name]} 显式记录到 README/补丁头，快照一漂即可自动预警。"
        fi
        ;;
    esac
  done

  # ---- 主仓库侧建议（≥3） ----
  sugg_main="
### 主仓库侧（dsh2026/test-AdamPlatin123）
- 快照分支与 master 不同谱系（如 web-components 锚定的 master b4b67f0 不在 snapshots 分支历史内），外围仓库无法自动判定前后关系；建议在每个快照分支 README/发布说明中公告 HEAD commit 与变更清单。
- seam 公共面本日保持稳定（slots/sessionProjections/ThemeService/settingsNamespace/session event 全部存在）；建议把公共 seam 面列入快照 release notes 的稳定性承诺。
- TUI 移除属破坏性变更（packages/ui/tui 全删、pi-tui 补丁移除、tuiPrompt 符号消失）；建议在快照说明中列出删除的公共包与替代面，供外围仓库提前适配。
- 新增 WebSocket 下行通道（connection/websocket-downlink）；建议补充协议文档，供 qqbot/tg-bot 等远程通道插件对齐。"
  if [ "$DRY_RUN" -eq 0 ]; then
    # 落盘报告到临时文件再原子移动，避免半成品
    local tmpf
    tmpf="$(mktemp)" || die 2 "创建主报告临时文件失败"
    {
      printf '# mainline 兼容性报告（%s）\n\n' "$DATE"
      printf -- '- mainline：`%s`（snapshots/%s）\n' "$MAINLINE_SHORT" "$MAINLINE_LABEL"
      printf -- '- 上次对比：`%s`\n' "$PREV_COMMIT"
      printf -- '- 兼容性：%s/%s 无需适配，%s 需适配（%s）；其中关注 %s、占位 %s、不适用 %s、已删除 %s、未知 %s\n\n' \
        "$(( ${#REPOS[@]} - adapt - gone - unknown ))" "${#REPOS[@]}" "$adapt" "${adapt_names:-无}" "$watch" "$placeholder" "$na" "$gone" "$unknown"
      printf '## 兼容性矩阵\n\n| 仓库 | 锚定 | 补丁 | seam | peerDeps | 综合判定 |\n|---|---|---|---|---|---|%s\n\n' "$matrix_rows"
      printf '## mainline 变更分析（%s → %s）\n\n' "$PREV_COMMIT" "$MAINLINE_SHORT"
      printf '### 关键变更\n%s\n\n' "$changes"
      printf '### 删除 / 新增包\n\n删除的包目录：%s\n\n新增文件：\n```\n%s\n```\n\n' \
        "$(printf '%s' "$deleted_pkgs" | sed '/^$/d' | tr '\n' ' ' | xargs)" "$added_files"
      printf '### seam 符号变化\n\n| 符号 | prev 存在性 | cur 存在性 | 变化 |\n|---|---|---|---|%s\n\n' "$seam_lines"
      printf '### diffstat（packages/ patches/ workspace）\n\n```\n%s\n```\n\n' "$diffstat"
      printf '## 破坏性变更清单\n%s\n\n' "$breaking"
      printf '## 插件侧建议（按仓库）\n%s\n\n' "$sugg_plugin"
      printf '## 主仓库侧建议\n%s\n' "$sugg_main"
    } > "$tmpf" || die 2 "写入主报告临时文件失败"
    mkdir -p "$REPORTS_DIR" || die 2 "创建报告目录失败: $REPORTS_DIR"
    mv "$tmpf" "$REPORTS_DIR/mainline-compat.md" || die 2 "写入主报告失败: $REPORTS_DIR/mainline-compat.md"
  fi

  # ---- 各仓库详情 + 当日索引 ----
  # M4：详情只保留本次生成的证据（锚定/补丁/seam/peerDeps/判定）+ 指向 research 的相对链接，
  #     不嵌入 research/<name>.md 正文（复制正文属信息泄露面，且与只读资产职责重复）
  local detail=""
  for name in "${REPOS[@]}"; do
    detail="$(printf '# %s — 与 mainline 兼容性对比（%s）\n\n' "$name" "$DATE")"
    # 仓库名可点击跳转 GitHub；research 摘要链接仅在存在时输出（避免死链）
    if [ -f "$ROOT/research/$name.md" ]; then
      detail="$detail> [打开仓库](https://github.com/$ORG/$name) · 调研摘要（只读资产，本报告不复制其正文）：[research/$name.md](../../research/$name.md)\n\n"
    else
      detail="$detail> [打开仓库](https://github.com/$ORG/$name) · 深度摘要待调研（当前为引擎自动判定）\n\n"
    fi

    detail="$detail
## 克隆证据

- 克隆 HEAD：${REPO_HEAD[$name]:-（空仓库）}
- 锚定：${ANCHOR_STR[$name]}（${ANCHOR_TYPE[$name]}，${ANCHOR_ST[$name]}）
- 补丁：${PATCH_ST[$name]}
- seam：${SEAM_ST[$name]}
- peerDeps：${PEER_ST[$name]}

## 四维对比

| 维度 | 结果 |
|---|---|
| 锚定 vs 当日 mainline | ${ANCHOR_ST[$name]} |
| 补丁 apply --check --3way | ${PATCH_ST[$name]} |
| seam 符号存在性 | ${SEAM_ST[$name]} |
| peerDeps 范围 vs mainline 实际 | ${PEER_ST[$name]} |
| **综合判定** | **${OVERALL[$name]}** |

## 建议

- ${OVERALL[$name]}：当日 mainline（$MAINLINE_SHORT，snapshots/$MAINLINE_LABEL）对比结论见上表；详细建议汇总于 [mainline-compat.md](mainline-compat.md)。
"
    if [ "$DRY_RUN" -eq 0 ]; then
      printf '%s' "$detail" > "$REPORTS_DIR/$name.md" || die 2 "写入详情报告失败: $name.md"
    fi
    detail_all="$detail_all
- [${name}.md](${name}.md) — ${OVERALL[$name]} · [仓库](https://github.com/$ORG/$name)"
  done

  local index_txt
  index_txt="$(printf '# 当日索引（%s）\n\n' "$DATE")"
  index_txt="$index_txt
- [主报告 mainline-compat.md](mainline-compat.md)（兼容性矩阵 + mainline 变更分析 + 双方建议）
- mainline：\`$MAINLINE_SHORT\`（snapshots/$MAINLINE_LABEL），上次 \`$PREV_COMMIT\`
- [开发者摘要](mainline-summary.md)（LLM 生成，存在时） · [返回 CHANGELOG](../../CHANGELOG.md)

## 仓库详情
$detail_all

## 相关资产

- [research/](../../research/) — $(ls "$ROOT"/research/*.md 2>/dev/null | wc -l | tr -d ' ') 份静态调研摘要（只读）
- [cross-analysis/summary.md](../../cross-analysis/summary.md) — 生态全景聚合报告
"
  if [ "$DRY_RUN" -eq 0 ]; then
    printf '%s' "$index_txt" > "$REPORTS_DIR/index.md" || die 2 "写入当日索引失败: $REPORTS_DIR/index.md"
  fi

  # 汇总打印
  info "兼容性汇总：${#REPOS[@]} 仓库 → 无需适配 $(( ${#REPOS[@]} - adapt - gone - unknown )) / 需适配 $adapt（${adapt_names:-无}）/ 关注 $watch / 占位 $placeholder / 不适用 $na / 已删除 $gone / 未知 $unknown"
}

update_changelog() {
  local entry changes_head adapt_names="" n adapt=0
  for n in "${REPOS[@]}"; do
    case "${OVERALL[$n]}" in
      需适配*) adapt_names="$adapt_names $n"; adapt=$((adapt+1)) ;;
    esac
  done
  adapt_names="$(printf '%s' "$adapt_names" | xargs)"
  changes_head="较上次 $PREV_COMMIT：${SUMMARY_BULLETS:-有 3 项关键变更}"
  entry="## $DATE
- mainline：\`$MAINLINE_SHORT\`（snapshots/$MAINLINE_LABEL）—— $changes_head
- 兼容状态：$(( ${#REPOS[@]} - adapt )) / ${#REPOS[@]} 兼容，$adapt 需适配（${adapt_names:-无}）
- 报告：[mainline-compat.md](reports/$DATE/mainline-compat.md) · [当日索引](reports/$DATE/index.md)"
  local changelog="$ROOT/CHANGELOG.md" tmp
  tmp="$(mktemp)" || die 2 "创建 CHANGELOG 临时文件失败"
  if [ -f "$changelog" ]; then
    { printf '%s\n\n' "$entry"; cat "$changelog"; } > "$tmp" || die 2 "写入 CHANGELOG 临时文件失败"
  else
    printf '# CHANGELOG\n\n%s\n' "$entry" > "$tmp" || die 2 "写入 CHANGELOG 失败"
  fi
  mv "$tmp" "$changelog" || die 2 "更新 CHANGELOG 失败: $changelog"
}

write_state() {
  local state="{}" name
  for name in "${REPOS[@]}"; do
    state="$(printf '%s' "$state" | jq -c --arg n "$name" --arg ac "${ANCHOR_STR[$name]:-未知}" --arg st "${OVERALL[$name]:-未知}" '. + {($n): {anchoredCommit:$ac, status:$st}}')" \
      || die 2 "构建状态数据失败"
  done
  # M5：状态文件走临时文件 + 原子 rename，任一步失败即脚本错误退出
  jq -n --arg lc "$MAINLINE_COMMIT" --arg ld "$DATE" --arg prev "$PREV_COMMIT" \
    --argjson repos "$state" \
    '{lastMainlineCommit:$lc, lastDate:$ld, previousCommit:$prev, repos:$repos}' > "$STATE_FILE.tmp" \
    || die 2 "写入状态临时文件失败: $STATE_FILE.tmp"
  mv "$STATE_FILE.tmp" "$STATE_FILE" || die 2 "更新状态文件失败: $STATE_FILE"
}

# ---- 7. 自动执行（默认关闭） ---------------------------------------------------
# 解析 actions/org-issues.md（DocsWorker 实际格式："## 草稿 N（Px）" + "**标题**：\`title\`" + "**正文**："）
# 输出: repo<TAB>title<TAB>正文（H6：完整正文块，仅预览环节截断；tab 转空格保 TSV 可解析）
parse_org_issues() {
  local file="$ROOT/actions/org-issues.md"
  [ -f "$file" ] || { warn "未找到 actions/org-issues.md，--publish-issues 无可发布草稿"; return 1; }
  local line repo title="" body="" in_body=0
  # 目标仓库：从文件头部 "dsh-external/<repo>" 提取，缺省 issues
  repo="$(grep -oE 'dsh-external/[a-zA-Z0-9._-]+' "$file" | head -1 | sed 's#dsh-external/##')"
  [ -n "$repo" ] || repo="issues"
  emit() { # 输出当前草稿：完整正文（去首行累积空行、tab→空格、换行转义为 \n 保持单行 TSV），不截断
    if [ $in_body -eq 1 ] && [ -n "$title" ]; then
      local b="${body#$'\n'}"
      b="${b//$'\t'/    }"
      b="${b//$'\n'/\\n}"
      printf '%s\t%s\t%s\n' "$repo" "$title" "$b"
    fi
  }
  while IFS= read -r line; do
    case "$line" in
      '## 草稿'*|'## draft'*|'## Draft'*)
        emit; title=""; body=""; in_body=0
        ;;
      '**标题**'*)
        title="${line#*\*\*标题\*\*：}"; title="${title#\`}"; title="${title%\`}"
        in_body=0
        ;;
      '**正文**'*)
        in_body=1; body=""
        ;;
      '---'*)
        emit; title=""; body=""; in_body=0
        ;;
      *)
        [ $in_body -eq 1 ] && body="$body
$line"
        ;;
    esac
  done < "$file"
  # 文件末尾草稿收尾
  emit
}

publish_issues() {
  local items item repo title body rest rc
  items="$(parse_org_issues)" || { [ $? -eq 1 ] && return 0; }
  [ -n "$items" ] || { warn "actions/org-issues.md 无未勾选草稿（- [ ]）"; return 0; }
  info "将发布 issue 清单（共 $(printf '%s\n' "$items" | sed '/^$/d' | wc -l) 条）："
  while IFS= read -r item; do
    [ -n "$item" ] || continue
    rest="${item#*$'\t'}"; body="${rest#*$'\t'}"
    body="${body//\\n/$'\n'}"
    printf '  - [%s] %s\n    正文预览（截断，发布为完整正文）: %.120s\n' "${item%%$'\t'*}" "${rest%%$'\t'*}" "$body"
  done <<< "$items"
  if [ "$DRY_RUN" -eq 1 ]; then
    info "dry-run：仅打印清单，不执行 gh issue create"
    return 0
  fi
  # H4：确认提示/回答从 /dev/tty 读取；无 TTY 时拒绝远程写（confirm 内说明）
  rc=0
  while IFS= read -r item; do
    [ -n "$item" ] || continue
    rest="${item#*$'\t'}"; repo="${item%%$'\t'*}"; title="${rest%%$'\t'*}"; body="${rest#*$'\t'}"
    body="${body//\\n/$'\n'}"   # 还原正文换行（H6：发布完整正文）
    [ "$repo" = "未指定" ] && { warn "跳过无仓库归属草稿: $title"; continue; }
    if ! confirm "发布到 $ORG/$repo：$title"; then
      warn "跳过发布（未确认/无 TTY）: $title"
      continue
    fi
    gh issue create --repo "$ORG/$repo" --title "$title" --body "$body" \
      && info "已发布: $ORG/$repo #$title" || { warn "发布失败: $title"; rc=1; }
  done <<< "$items"
  return $rc
}

# 找出待修 fix：克隆 README/catalog 中引用旧 catalog pin（普通 40 位 SHA）的文件。
# H5：目标 ref = 各插件仓库自身完整 40 位 HEAD（不可变 ref 协议要求），不是 mainline 短 SHA；
# 路径以相对 .clones/<name>/ 保存，apply 时不再二次拼接。
find_fixes() {
  local name dir old full_head rel f tmp patch
  local fixes=""
  for name in "${REPOS[@]}"; do
    old="${CATALOG_REF[$name]:-}"
    [ -n "$old" ] || continue                    # 仅修 catalog pin；mainline 锚定/无 pin 不动
    dir="$CLONES_DIR/$name"
    [ -d "$dir/.git" ] || continue
    [[ "$old" =~ ^[0-9a-f]{40}$ ]] || continue
    full_head="$(git -C "$dir" rev-parse HEAD 2>/dev/null)" || continue
    case "$full_head" in
      "$old") continue ;;                         # 已 pin 到自身 HEAD，无需修复
    esac
    # 只在 README 与 catalog 类文件中找旧 pin 引用
    while IFS= read -r f; do
      grep -qF "$old" "$f" 2>/dev/null || continue
      tmp="$(mktemp)"
      sed "s/$old/$full_head/g" "$f" > "$tmp"
      patch="$(diff -u "$f" "$tmp" | sed '1,2d')"
      if [ -n "$patch" ]; then
        rel="${f#$dir/}"
        fixes="$fixes
FIX>$name>$rel>$full_head
$patch"
      fi
      rm -f "$tmp"
    done < <(find "$dir" -maxdepth 2 \( -name 'README*' -o -name 'catalog*.json' -o -name '*.json' \) -not -path '*/node_modules/*' -not -path '*/.git/*' 2>/dev/null)
  done
  printf '%s' "$fixes"
}

apply_fix() {
  local fixes="$1"
  [ -n "$fixes" ] || { info "--apply-fix：未发现可自动修复项（无旧 catalog pin 引用）"; return 0; }
  info "待修 diff（各插件仓库自身 40 位 HEAD 替换旧 pin）："
  printf '%s\n' "$fixes"
  if [ "$DRY_RUN" -eq 1 ]; then
    info "dry-run：仅输出 diff，不写入"
    return 0
  fi
  # 解析 "FIX>name>rel>head" 头 + diff 块，逐项确认（H4：确认从 /dev/tty 读；H5：写入相对 .clones/ 路径）
  local current_name="" current_file="" current_head="" buf="" line rest rest2 target
  apply_one() { # 确认并写入当前块
    if [ -n "$buf" ] && [ -n "$current_file" ]; then
      target="$CLONES_DIR/$current_name/$current_file"
      if confirm "将 $current_head 写入 $current_name/$current_file"; then
        sed -i "s/${CATALOG_REF[$current_name]:-}/$current_head/g" "$target" \
          && info "已更新: $current_name/$current_file（本地 clone，不影响远程）" \
          || warn "更新失败: $current_name/$current_file"
      else
        warn "跳过修复（未确认/无 TTY）: $current_name/$current_file"
      fi
    fi
  }
  while IFS= read -r line; do
    if [[ "$line" == FIX\>* ]]; then
      apply_one                       # 上一块收尾
      rest="${line#FIX>}"; current_name="${rest%%>*}"
      rest2="${rest#*>}"; current_file="${rest2%%>*}"; current_head="${rest2#*>}"
      buf=""
    else
      buf="$buf
$line"
    fi
  done <<< "$fixes"
  apply_one                           # 最后一块收尾
}

# =============================================================================
# 主流程
# =============================================================================
check_deps
check_network
info "开始对比：$DATE（dry-run=$DRY_RUN，scope=${#REPOS[@]} 仓库）"

# 状态文件 → 上次 commit（M1：dry-run 同样读取——只禁写不禁读，用真实上次基线；状态无效即 exit 2）
if [ -f "$STATE_FILE" ]; then
  PREV_COMMIT="$(jq -r '.lastMainlineCommit // empty' "$STATE_FILE" 2>/dev/null)" \
    || die 2 "状态文件解析失败（jq 不可读或非 JSON）: $STATE_FILE"
  [ -n "$PREV_COMMIT" ] || die 2 "状态文件缺少 lastMainlineCommit 字段: $STATE_FILE"
  [[ "$PREV_COMMIT" =~ ^[0-9a-f]{7,40}$ ]] || die 2 "状态文件 lastMainlineCommit 非法: $PREV_COMMIT"
fi
[ -n "${PREV_COMMIT:-}" ] || PREV_COMMIT="$BASE_COMMIT"
info "mainline 对比基线（上次记录 / --base）: $PREV_COMMIT"

mainline_fetch

# 逐仓库索引 + 对比
for name in "${REPOS[@]}"; do
  info "索引 $name ..."
  repo_fetch "$name" || true
  anchor_detect "$name"
  anchor_classify "$name"
  if [ -z "${REPO_HEAD[$name]:-}" ]; then
    PATCH_ST[$name]="不适用（空仓库）"; SEAM_ST[$name]="不适用（空仓库）"; PEER_ST[$name]="不适用"
  elif [ "${NONCODE_REPOS[*]}" != "${NONCODE_REPOS[*]//$name/}" ]; then
    PATCH_ST[$name]="不适用"; SEAM_ST[$name]="不适用"; PEER_ST[$name]="不适用"
  else
    patch_check "$name"
    seam_check "$name"
    peer_check "$name"
  fi
  overall_judge "$name"
  info "  $name => 锚定=${ANCHOR_ST[$name]} 补丁=${PATCH_ST[$name]} 判定=${OVERALL[$name]}"
done

mainline_diff_analyze

if [ "$DRY_RUN" -eq 1 ]; then
  info "dry-run：跳过报告 / CHANGELOG / 软链 / 状态写入（全程只读）"
else
  build_reports
  # M5：软链走临时文件 + 原子 rename，失败即脚本错误退出
  link_tmp="$(mktemp -u "$ROOT/reports/.latest.XXXXXX")"
  ln -s "$DATE" "$link_tmp" && mv -Tf "$link_tmp" "$ROOT/reports/latest" \
    || die 2 "创建 reports/latest 软链失败"
  info "reports/latest -> $DATE"
  update_changelog
  info "CHANGELOG.md 已更新"
  write_state
  info ".mainline-state.json 已写入（lastMainlineCommit=$MAINLINE_COMMIT, lastDate=$DATE）"
fi

# 可选自动执行
if [ "$PUBLISH_ISSUES" -eq 1 ]; then
  info "=== --publish-issues ==="
  publish_issues
fi
if [ "$APPLY_FIX" -eq 1 ]; then
  info "=== --apply-fix ==="
  apply_fix "$(find_fixes)"
fi

# 退出码：0=全部兼容 1=存在需适配 2=脚本错误 3=离线
ADAPT=0
for name in "${REPOS[@]}"; do
  case "${OVERALL[$name]}" in 需适配*) ADAPT=1;; esac
done
# mainline 破坏性变更（seam 存在→缺失）也视为需适配
for sym in "${SEAM_SYMBOLS[@]}"; do
  if [ "${SEAM_PREV[$sym]:-0}" -gt 0 ] && [ "${SEAM_CUR[$sym]:-0}" -eq 0 ]; then ADAPT=1; fi
done
if [ "$ADAPT" -eq 1 ]; then
  info "结论：存在需适配项 → 退出码 1"
  exit 1
fi
info "结论：全部兼容 → 退出码 0"
exit 0
