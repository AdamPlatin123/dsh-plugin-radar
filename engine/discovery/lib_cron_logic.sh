#!/usr/bin/env bash
# cron-check.sh 的变化检测与游标写入逻辑（P2a 拆出，供 scripts/selftest-cron-increment.sh
# 以 mock 的 remote_head 复用测试）。
#
# 依赖（调用方提供）：REPOS 数组（name|url 形态）、STATE 文件路径、remote_head() 函数。
# 历史教训：本逻辑曾引用从未定义的 REPOS 数组（实际构建的是 SCOPE_REPOS），bash 4.4+
# 下空数组静默展开，增量检测与游标更新整段空转、二轮起永远输出「无变化」——
# 拆出 + 三用例自测即防复发。

# 变化检测：设置全局 DETECTED（空=无变化；"all(首次)"；空格分隔的变化仓库名）
detect_changes() {
  DETECTED=""
  if [ -f "$STATE" ]; then
    for entry in "${REPOS[@]}"; do
      name="${entry%%|*}"; url="${entry#*|}"
      prev="$(jq -r --arg n "$name" '.[$n] // ""' "$STATE" 2>/dev/null || echo "")"
      cur="$(remote_head "$name" "$url")"
      if [ -z "$cur" ]; then
        echo "[跳过] $name：ls-remote 失败（离线/网络），保留上次状态"
      elif [ -z "$prev" ]; then
        DETECTED="$DETECTED $name"
        echo "[新增] $name：首次纳入检测（HEAD $cur）"
      elif [ "$cur" != "$prev" ]; then
        DETECTED="$DETECTED $name"
        echo "[变化] $name: $prev -> $cur"
      fi
    done
  else
    echo "[首次运行] 无状态文件，执行全量索引"
    DETECTED="all(首次)"
  fi
}

# 游标写入：推送成功后推进（SOP：已发布 SHA 确认后才更新 published cursor）
write_cursor() {
  {
    echo "{"
    first=1
    for entry in "${REPOS[@]}"; do
      name="${entry%%|*}"; url="${entry#*|}"
      cur="$(remote_head "$name" "$url")"
      [ -z "$cur" ] && cur="$(jq -r --arg n "$name" '.[$n] // ""' "$STATE" 2>/dev/null || echo "")"
      [ $first -eq 0 ] && echo ","
      printf '  "%s": "%s"' "$name" "$cur"
      first=0
    done
    echo ""
    echo "}"
  } > "$STATE.tmp" && mv "$STATE.tmp" "$STATE"
}
