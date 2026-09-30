#!/usr/bin/env bash
# lib_report.sh — compare-mainline 报告层（P4a 拆出）：
# mainline 自身变更分析（seam prev/cur 对比）、兼容性矩阵报告、仓库详情、
# 当日索引、CHANGELOG、状态文件。P4a 新增 mainline-compat.json 结构化产物
# （矩阵数据的机器可读版，供后续消费；不影响既有 Markdown 产物字节）。
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

  # ---- 矩阵行 ----（同步收集结构化行，供 mainline-compat.json——P4a 增产物，
  #      机器可读版兼容矩阵，Shell mainline 栈自此不再只有 Markdown 输出）
  local json_rows="" jrow
  for name in "${REPOS[@]}"; do
    row="| $name | ${ANCHOR_ST[$name]:-未知} | ${PATCH_ST[$name]:-无补丁} | ${SEAM_ST[$name]:-不适用} | ${PEER_ST[$name]:-无} | ${OVERALL[$name]} |"
    matrix_rows="$matrix_rows
$row"
    jrow="$(jq -cn --arg n "$name" --arg a "${ANCHOR_ST[$name]:-未知}" --arg p "${PATCH_ST[$name]:-无补丁}" \
              --arg s "${SEAM_ST[$name]:-不适用}" --arg d "${PEER_ST[$name]:-无}" --arg o "${OVERALL[$name]}" \
              --arg h "${REPO_HEAD[$name]:-}" --arg ac "${ANCHOR_STR[$name]:-}" \
              '{name:$n,anchor:$a,anchor_commit:$ac,patch:$p,seam:$s,peer:$d,overall:$o,head:$h}')" \
      || die 2 "构建结构化矩阵行失败: $name"
    json_rows="$json_rows$jrow\n"
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

  # ---- 结构化产物 mainline-compat.json（P4a 增产物：矩阵 + 版本锚的机器可读版）----
  if [ "$DRY_RUN" -eq 0 ]; then
    local json_tmp
    json_tmp="$(mktemp)" || die 2 "创建 JSON 临时文件失败"
    printf '%b' "$json_rows" | jq -cn \
      --arg date "$DATE" --arg ms "$MAINLINE_SHORT" --arg mc "$MAINLINE_COMMIT" \
      --arg ml "$MAINLINE_LABEL" --arg prev "$PREV_COMMIT" \
      '[inputs] | {schema:"radar-mainline-compat/v1", date:$date,
                    mainline:{short:$ms, commit:$mc, label:$ml}, prev:$prev, repos:.}' \
      > "$json_tmp" || die 2 "构建 mainline-compat.json 失败（jq）"
    jq -e . "$json_tmp" >/dev/null 2>&1 || die 2 "mainline-compat.json 非法 JSON（fail-closed，不落盘）"
    mv "$json_tmp" "$REPORTS_DIR/mainline-compat.json" || die 2 "写入 mainline-compat.json 失败"
    info "结构化矩阵 → $REPORTS_DIR/mainline-compat.json"
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
