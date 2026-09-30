#!/usr/bin/env bash
# lib_patch.sh — compare-mainline 补丁与依赖探测层（P4a 拆出）：
# .mainline 补丁 git apply --check --3way、seam 存在性、workspace 版本、peerDeps 匹配。
# 依赖主壳的 MAINLINE/CLONES_DIR/SEAM_SYMBOLS（lib_anchor 定义）。
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
