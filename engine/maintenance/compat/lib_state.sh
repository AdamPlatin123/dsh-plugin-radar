#!/usr/bin/env bash
# lib_state.sh — compare-mainline 自动执行层（P4a 拆出）：
# /dev/tty 逐项确认、org issue 草稿解析与发布、catalog pin 自动修复。
# 默认关闭（--publish-issues / --apply-fix 显式开启）。
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
