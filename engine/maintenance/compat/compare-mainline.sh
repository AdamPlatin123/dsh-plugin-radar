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
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"   # engine/maintenance/compat → 仓库根

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



# ---- 拆分库（P4a：原 1117 行单体的五层职能库，主壳只保留编排） ----
# 注意：source 必须在参数与清单解析之后——lib_fetch 含缓存目录初始化等顶层代码，
# 依赖 DRY_RUN/DATE/REPOS 已就位（与原单体自上而下的执行序一致）。
# shellcheck source=compat/lib_fetch.sh
source "$SCRIPT_DIR/lib_fetch.sh"
# shellcheck source=compat/lib_anchor.sh
source "$SCRIPT_DIR/lib_anchor.sh"
# shellcheck source=compat/lib_patch.sh
source "$SCRIPT_DIR/lib_patch.sh"
# shellcheck source=compat/lib_report.sh
source "$SCRIPT_DIR/lib_report.sh"
# shellcheck source=compat/lib_state.sh
source "$SCRIPT_DIR/lib_state.sh"

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