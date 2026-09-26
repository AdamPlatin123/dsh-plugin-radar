#!/usr/bin/env bash
# lib_fetch.sh — compare-mainline 拉取层（P4a 自 1117 行单体拆出）：
# 依赖/网络预检、缓存目录、mainline 快照拉取、15 仓克隆更新、repo-gone 双重确认。
# 由 compare-mainline.sh source；依赖主壳的全局变量与 info/warn/die。
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
