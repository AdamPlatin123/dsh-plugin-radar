#!/usr/bin/env bash
# auto-snapshot-push.sh — 全自动：生成快照 → 推 main（Bot A 全自动）
# 由 probe */15 调用；有增量才推（幂等，无增量跳过）
set -uo pipefail
export PATH=$HOME/.local/bin:$PATH
HOME_DIR=$HOME
SNAP_DIR=/tmp/snap-auto
STATE=$HOME_DIR/dsh-k8s/.last-auto-snapshot

# 并发防护：probe 每 15 分钟调用，高负载时上一轮可能未结束——共享 /tmp 载荷会被交叉读写
# （2026-08-19 事故：脚本同步载荷被快照路径 PUT 采用，11 份快照写入脚本内容）。单例 + 独占载荷双保险。
exec 9>/tmp/auto-snapshot-push.lock
flock -n 9 || { echo "[auto-snap] 上一轮仍在运行，跳过本轮"; exit 0; }
PAY_SNAP=$(mktemp /tmp/push-snap.XXXXXX.json)
PAY_MIRROR=$(mktemp /tmp/push-mirror.XXXXXX.json)
PAY_RAW=$(mktemp /tmp/push-raw.XXXXXX.bin)
PAY_B64=$(mktemp /tmp/push-b64.XXXXXX.txt)
trap 'rm -f "$PAY_SNAP" "$PAY_MIRROR" "$PAY_RAW" "$PAY_B64"' EXIT

# ① 生成快照
mkdir -p $SNAP_DIR/data/snapshots
cd $SNAP_DIR
K8S="${RADAR_K8S_DIR:-$HOME_DIR/dsh-k8s}"
[ -f "$K8S/gen-snapshot-v2.py" ] || { echo "[auto-snap] WARN 缺私有件 $K8S/gen-snapshot-v2.py，本轮跳过（engine/ops/private/MANIFEST.md）"; exit 0; }
python3 "$K8S/gen-snapshot-v2.py" 2>/dev/null | tail -1 || exit 0

RUN_FILE=$(ls -t data/snapshots/*.json 2>/dev/null | head -1)
[ -z "$RUN_FILE" ] && exit 0
RUN_ID=$(basename "$RUN_FILE" .json)

# ② 有增量才推（对比上次自动推的 run 的 verdict.total）
LAST_RUN=$(cat "$STATE" 2>/dev/null || echo "")
if [ "$RUN_ID" = "$LAST_RUN" ]; then
  echo "[auto-snap] $RUN_ID 已推过，跳过"
  exit 0
fi

CUR_TOTAL=$(python3 -c "import json; print(json.load(open('$RUN_FILE'))['verdict']['total'])" 2>/dev/null)
CUR_PLUG=$(python3 -c "import json; print(json.load(open('$RUN_FILE')).get('clone',{}).get('plugins',0))" 2>/dev/null || echo 0)
if [ -n "$LAST_RUN" ] && [ -f "$SNAP_DIR/data/snapshots/$LAST_RUN.json" ]; then
  LAST_TOTAL=$(python3 -c "import json; print(json.load(open('$SNAP_DIR/data/snapshots/$LAST_RUN.json'))['verdict']['total'])" 2>/dev/null || echo 0)
  LAST_PLUG=$(python3 -c "import json; print(json.load(open('$SNAP_DIR/data/snapshots/$LAST_RUN.json')).get('clone',{}).get('plugins',0))" 2>/dev/null || echo 0)
  DELTA=$((CUR_TOTAL - LAST_TOTAL))
  DELTA_P=$((CUR_PLUG - LAST_PLUG))
  # 下降立即推（批量复活/改判是必须渲染的真实状态，曾把负增量误当"未攒够"致渲染停摆）；正积累阈值 10
  # 2026-08-28：收录数（clone.plugins）任一方向变化都推——换锚重测是覆盖写，verdict.total 不动而内容在变
  if [ "$DELTA" -lt 0 ]; then
    echo "[auto-snap] 总量下降 $DELTA，立即推（状态变化）"
  elif [ "$DELTA_P" -ne 0 ]; then
    echo "[auto-snap] 收录数变化 $DELTA_P（$LAST_PLUG→$CUR_PLUG），立即推"
  elif [ "$DELTA" -lt 10 ]; then
    echo "[auto-snap] 增量 $DELTA < 10，暂不推（等积累）"
    exit 0
  fi
fi

# ③ 推 main（gh API）
REPO=dsh-external/awesome-dsh-plugins
CONTENT=$(base64 -w0 "$RUN_FILE")
python3 -c \
  "import base64,json; json.dump({'message':'auto: 快照 $RUN_ID（v2 桥接 · total=$CUR_TOTAL）','content':base64.b64encode(open('$RUN_FILE','rb').read()).decode(),'branch':'main'},open('$PAY_SNAP','w'))"
gh api -X PUT "repos/$REPO/contents/data/snapshots/$RUN_ID.json" \
  --input "$PAY_SNAP" --jq '.commit.sha[0:7]' 2>/dev/null && \
  { echo "$RUN_ID" > "$STATE"; echo "[auto-snap] $RUN_ID 已推 main"; } || \
  echo "[auto-snap] 推送失败"

# ④ 镜像双仓同步（公开仓 AdamPlatin123：快照+数据缓存 org→mirror，
#    触发镜像 readme-render workflow 自动渲染；失败不阻断 org 主链路，幂等重试）
MIRROR=AdamPlatin123/dsh-plugin-radar
sync_put() {  # $1=文件路径：org 内容转推镜像，sha 一致则跳过
  local p="$1" sha_o sha_m
  sha_o=$(gh api "repos/$REPO/contents/$p" --jq '.sha' 2>/dev/null)
  [ -n "$sha_o" ] || { echo "[mirror] org 无 $p，跳过"; return 0; }
  sha_m=$(gh api "repos/$MIRROR/contents/$p" --jq '.sha' 2>/dev/null)
  [ "$sha_o" = "$sha_m" ] && return 0
  # raw 通道下载（>1MB 文件 contents API 不回 content 字段；base64 内容不走 argv 防 128KB 上限）
  gh api "repos/$REPO/contents/$p" -H "Accept: application/vnd.github.raw" > "$PAY_RAW" 2>/dev/null
  [ -s "$PAY_RAW" ] || { echo "[mirror] $p 内容获取为空，跳过（防 0 字节落仓）"; return 1; }
  # 内容门禁：非空 ≠ 正确。org 侧曾把 GitHub API 404 响应体当作 runner-versions.json
  # 的文件内容入库，raw 下载非空、一路同步到镜像并随稳定接口发布——JSON 合法性 +
  # API 错误对象特征 + 关键文件形态三重拦截（P2a）
  case "$p" in
    *.json)
      if ! python3 -c '
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception as e:
    sys.exit(f"JSON 解析失败: {e}")
if isinstance(d, dict) and "message" in d and "documentation_url" in d:
    sys.exit("API 错误对象特征（message+documentation_url）——疑似 GitHub API 响应体误入库")
if sys.argv[2].endswith("runner-versions.json") and not (
        isinstance(d, dict) and d.get("schema") == "dsh-radar/runner-versions/v1" and "latest" in d):
    sys.exit("runner-versions.json 形态不符（需 schema=dsh-radar/runner-versions/v1 + latest 键）")
' "$PAY_RAW" "$p"; then
        echo "[mirror] $p 内容门禁拦截，跳过本轮同步（org 侧源头待修，sha 不推进下轮重查）"
        return 1
      fi
      ;;
  esac
  base64 -w0 "$PAY_RAW" > "$PAY_B64"
  python3 - "$PAY_B64" "$PAY_MIRROR" "$sha_m" "$p" <<'PYA'
import json, sys
b64, pay, sha, p = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
d = {"message": "data: 同步 " + p + "（org→mirror）", "content": open(b64).read().strip(), "branch": "main"}
if sha:
    d["sha"] = sha  # 更新已存在文件必须带 sha（否则 422）
json.dump(d, open(pay, "w"))
PYA
  if gh api -X PUT "repos/$MIRROR/contents/$p" --input "$PAY_MIRROR" >/dev/null 2>&1; then
    echo "[mirror] $p 已同步"
  else
    echo "[mirror] $p 同步失败（下轮 sha 对比重试）"
  fi
}
sync_put "data/snapshots/$RUN_ID.json"
for _f in data/locate-cache.json data/url-audit.json data/repo-map.json data/desc-cache.json data/runner-versions.json; do
  sync_put "$_f"
done
# 脚本权威反转（2026-09-05）：主仓 main 为唯一权威，.9 每轮拉取最新脚本再渲染；
# 不再向 org 推送脚本（旧环会用 .9 过期副本周期性回灌主仓，已三次冲掉拆分案）
# 转发壳 + 其 engine 依赖一并同步（外审 P1：壳新增 engine/lib 导入，旧同步清单
# 只有七个平铺脚本——未迁移布局的服务器拉到壳会 ModuleNotFoundError）
SCRIPTS="gen_plugins_all.py resolve_placeholders.py render-readme-from-snapshot.py classify.py gen-pipeline-diagram.py reconcile_catalog.py tile_assets.py"
ENGINE_FILES="lib/radar/__init__.py lib/radar/atomicio.py lib/radar/sanitize.py lib/radar/ghql.py lib/radar/gitops.py lib/radar/secretsource.py lib/radar/thresholds.py aggregation/build_canonical.py aggregation/rebaseline.py rendering/render_all.py"
for _f in $SCRIPTS; do
  for _base in "https://raw.githubusercontent.com/AdamPlatin123/dsh-plugin-radar/main" \
               "https://cdn.jsdelivr.net/gh/AdamPlatin123/dsh-plugin-radar@main"; do
    if curl -sf --max-time 20 "$_base/scripts/$_f" -o "$HOME/dsh-external-research/scripts/$_f"; then
      break
    fi
  done || echo "[scripts] 拉取 $_f 失败（沿用本地现行版）"
done
for _f in $ENGINE_FILES; do
  mkdir -p "$HOME/dsh-external-research/engine/$(dirname "$_f")"
  for _base in "https://raw.githubusercontent.com/AdamPlatin123/dsh-plugin-radar/main" \
               "https://cdn.jsdelivr.net/gh/AdamPlatin123/dsh-plugin-radar@main"; do
    if curl -sf --max-time 20 "$_base/engine/$_f" -o "$HOME/dsh-external-research/engine/$_f"; then
      break
    fi
  done || echo "[scripts] 拉取 engine/$_f 失败（沿用本地现行版）"
done

