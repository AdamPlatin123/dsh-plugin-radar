#!/usr/bin/env bash
# 兼容性疑点 → 对应 repo issue（不修复，只声明"可能存在问题"）
# 数据源：reports/<日期>/compile-compat.md 失败清单
# 用法：report-issues.sh [--apply] [--only-manual] [--limit N]
#   --apply        实际提交（默认 dry-run 只列清单）
#   --only-manual  只提交 API 漂移类（TS2339/TS2345/TS2322）——最尖锐
#   --limit N      最多提交 N 条
# 依赖：gh（认证，对 dsh-external/* 有 issue 创建权限）
set -uo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR" || exit 2
DATE="$(date +%Y-%m-%d)"
APPLY=0; ONLY_MANUAL=0; LIMIT=99999
for a in "$@"; do
  case "$a" in
    --apply) APPLY=1 ;;
    --only-manual) ONLY_MANUAL=1 ;;
    --limit) ;;
    *) [[ "$a" =~ ^[0-9]+$ ]] && LIMIT="$a" ;;
  esac
done

COMPAT="$(ls "$REPO_DIR"/reports/*/compile-compat.md 2>/dev/null | tail -1)"
[ -f "$COMPAT" ] || { echo "[错误] 找不到 compile-compat.md"; exit 2; }
MAINLINE_LABEL="$(grep -m1 "快照" "$COMPAT" | grep -oE "snapshots/[0-9TZ-]+" | head -1 || echo 最新快照)"

echo "=== $(date -Is) report-issues 开始（apply=$APPLY only-manual=$ONLY_MANUAL limit=$LIMIT） ==="

SUBMITTED=0; SKIPPED=0
declare -a PLANNED=()

# 逐失败行生成 issue 草稿
while IFS= read -r line; do
  name="$(printf '%s' "$line" | cut -d'|' -f2 | tr -d ' ')"
  err="$(printf '%s' "$line" | sed -E 's/^\| [^|]+ \| //' | cut -c1-200)"
  [ -z "$name" ] && continue
  # 跳过非插件/自身
  case "$name" in 插件|awesome-dsh-plugins|hub|marisa|toybox) continue ;; esac
  # only-manual：只保留 API 漂移类
  if [ "$ONLY_MANUAL" -eq 1 ]; then
    case "$err" in TS2339*|TS2345*|TS2322*) ;; *) continue ;; esac
  fi
  # 环境类（TS2307 解析 cordis/@deepseek-ai）标注"可能"而非"确定"
  SEVERITY="可能不兼容"
  case "$err" in
    TS2307*|TS6053*|TS5083*|TS5101*|TS2688*) SEVERITY="可能存在兼容性问题（环境/配置类，真实安装可解）" ;;
    TS2339*|TS2345*|TS2322*) SEVERITY="很可能不兼容（API 漂移）" ;;
  esac

  TITLE="[compat] 与最新 mainline（$MAINLINE_LABEL）$SEVERITY：$err"
  BODY="## 兼容性验证发现（自动报告，未修复）

在 [awesome-dsh-plugins](https://github.com/Zhidao-Lab-OSS/awesome-dsh-plugins) 的编译验证中发现本仓库可能存在问题：

- **mainline 基线**：$MAINLINE_LABEL
- **验证方式**：插件源码放入 mainline workspace 后 \`tsc --noEmit\`
- **首个错误**：\`$err\`

### 说明
- 本报告**只声明可能存在兼容性问题，不做修复**
- 错误分类：
  - TS2307/TS6053/TS5083/TS5101/TS2688 → 环境/配置类（tsconfig 解析、依赖、类型包），真实安装环境可能可解
  - TS2339/TS2345/TS2322 → API 漂移，**很可能真实不兼容**
- 完整验证数据：https://github.com/Zhidao-Lab-OSS/awesome-dsh-plugins/blob/main/reports/$(basename "$(dirname "$COMPAT")")/compile-compat.md

### 建议
请仓库维护者自查：更新 tsconfig 继承 / 补齐依赖 / 对照新 API 签名。"
  PLANNED+=("$name|$SEVERITY|$TITLE")
done < <(grep -E '^\| ' "$COMPAT" | grep -v '^|--' | sed -n '2,200p')

echo "[计划] ${#PLANNED[@]} 条待提交"
if [ "$APPLY" -eq 1 ]; then
  N=0
  for p in "${PLANNED[@]:-}"; do
    [ "$N" -ge "$LIMIT" ] && break
    name="${p%%|*}"; title="$(printf '%s' "$p" | cut -d'|' -f3-)"
    if gh issue create --repo "dsh-external/$name" --title "$title" --body "$(printf '%s' "$p" | cut -d'|' -f2)" >/dev/null 2>&1; then
      echo "[已提交] dsh-external/$name：$title"
      SUBMITTED=$((SUBMITTED+1))
    else
      echo "[失败] dsh-external/$name（可能无 issue 权限或仓库已删）"
      SKIPPED=$((SKIPPED+1))
    fi
    N=$((N+1))
  done
  echo "[完成] 提交 $SUBMITTED / 失败 $SKIPPED"
else
  for p in "${PLANNED[@]:-}"; do
    name="${p%%|*}"
    sev="$(printf '%s' "$p" | cut -d'|' -f2)"
    echo "- dsh-external/$name [$sev]"
  done | head -30
  echo "...（共 ${#PLANNED[@]} 条，--apply 才实际提交）"
fi
exit 0
