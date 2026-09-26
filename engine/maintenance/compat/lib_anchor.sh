#!/usr/bin/env bash
# lib_anchor.sh — compare-mainline 锚定层（P4a 拆出）：
# 锚定探测/分类（对齐/落后/超前/未知）+ 综合判定阶梯（占位>需适配>关注>兼容）。
# 锚定规则 1-7 与 catalog ref 的区分见 anchor_detect 内注（M2 规则）。
# seam 符号常量随锚定层走（overall_judge 的 seam_hit 判定依赖）。
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
