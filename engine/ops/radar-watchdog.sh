#!/usr/bin/env bash
# radar-watchdog.sh — 全链路看门狗：不只查"进程在"，还查"在干活"。
# 五层检测：进程存活 → 活性（最近有产出）→ 锁健康 → 数据前进 → 心跳必写。
# cron */5 调用（flock -w 60 等锁超时自动退出，不会堵死下轮）。
set -u
export PATH=$HOME/.local/bin:$HOME/.nvm/versions/node/v24.14.1/bin:$PATH
K8S=$HOME/dsh-k8s
REPO=$HOME/dsh-external-research
HB=$K8S/probe-heartbeat.json
LOCK=/tmp/radar-probe.lock
NOW=$(date +%s)
NOW_H=$(date +%H:%M:%S)

log(){ echo "[$NOW_H] $*"; }

# ---- 0) 清理超过 10 分钟的僵尸锁 ----
if [ -f "$LOCK" ]; then
  LOCK_AGE=$(( NOW - $(stat -c %Y "$LOCK" 2>/dev/null || echo $NOW) ))
  if [ $LOCK_AGE -gt 600 ]; then
    log "WARN 僵尸锁 ${LOCK_AGE}s，强制清理"
    rm -f "$LOCK"
  fi
fi

# ---- 活性检测函数：$1=组件名 $2=检查命令(输出秒龄) $3=阈值秒 ----
alive_check() {
  local name=$1 check=$2 threshold=$3
  local last_age
  last_age=$(eval "$check" 2>/dev/null | head -1)
  if [ -z "$last_age" ] || [ "$last_age" = "None" ]; then
    echo "$name: NO_DATA"
    return 2
  elif [ "$last_age" -gt "$threshold" ]; then
    echo "$name: STALE(${last_age}s)"
    return 1
  else
    echo "$name: ok(${last_age}s)"
    return 0
  fi
}

sec_since(){ local f="$1"; [ -f "$f" ] && echo $(( NOW - $(stat -c %Y "$f" 2>/dev/null || echo $NOW) )) || echo 999999; }

# ---- 1) driver：进程 + 活性（pipeline.log 最近写入）----
DRV_P=$(pgrep -f "pipeline-drive[r]" | head -1)
DRV_AGE=$(sec_since "$K8S/state/pipeline-state.json")  # 每 cycle 必写，比 stdout 缓冲的 log 可靠
DRV_STATUS="down"
if [ -n "$DRV_P" ]; then
  DRV_STATUS="up"
  # 活性：pipeline.log 超过 10 分钟没写 = 可能卡死
  if [ "$DRV_AGE" -gt 600 ]; then
    # 但如果没有待办（全部测完）driver 睡着是正常的
    PEND=$(ls "$REPO/.clones/.verified/.plugins.txt" 2>/dev/null | head -1; python3 -c "
import json,os
from pathlib import Path
repo=Path('$REPO')
pl=repo/'.clones/.verified/.plugins.txt'
rt=repo/'.rt-agent'
plugins=set(pl.read_text().split()) if pl.exists() else set()
tested={p.stem for p in rt.glob('*.json')} if rt.exists() else set()
print(len(plugins-tested))
" 2>/dev/null | tail -1)
    RUN_PODS=$(kubectl -n dsh-test get pods -l app=dsh-agent-test --field-selector=status.phase=Running -o name 2>/dev/null | wc -l)
    if [ "$PEND" = "0" ] && [ "$RUN_PODS" = "0" ]; then
      DRV_STATUS="idle(正常等新仓)"
    else
      log "WARN driver 进程在但 ${DRV_AGE}s 无活动，待测=$PEND pod=$RUN_PODS → 强杀重启"
      kill "$DRV_P" 2>/dev/null; sleep 2
      setsid nohup flock -n /tmp/radar-driver.single env PYTHONUNBUFFERED=1 python3 "$K8S/pipeline-driver.py" --converge >> "$K8S/pipeline.log" 2>&1 < /dev/null 4>&- 5>&- 6>&- 7>&- 8>&- 9>&- &
      DRV_STATUS="killed+restarted"
    fi
  fi
else
  # driver 不在 → 检查是否有活干
  PEND=$(python3 -c "
import json,os
from pathlib import Path
repo=Path('$REPO')
cands=set()
try:
  for c in json.load(open(repo/'generated/current/candidates.json'))['candidates']:
    fn=c.get('full_name') or ''
    if fn and '/' in fn and not fn.startswith('github:'): cands.add(fn.split('/')[-1])
except: pass
clones={d.name for d in (repo/'.clones').iterdir() if d.is_dir() and not d.name.startswith('.')} if (repo/'.clones').exists() else set()
pl=repo/'.clones/.verified/.plugins.txt'
plugins=set(pl.read_text().split()) if pl.exists() else set()
tested={p.stem for p in (repo/'.rt-agent').glob('*.json')} if (repo/'.rt-agent').exists() else set()
work = len(cands-clones) + len(plugins-tested)
print(work)
" 2>/dev/null | tail -1)
  if [ "${PEND:-0}" -gt 0 ] 2>/dev/null || [ "${PEND:-0}" != "0" ]; then
    log "driver down 且有活($PEND)，拉起"
    setsid nohup flock -n /tmp/radar-driver.single env PYTHONUNBUFFERED=1 python3 "$K8S/pipeline-driver.py" --converge >> "$K8S/pipeline.log" 2>&1 < /dev/null 4>&- 5>&- 6>&- 7>&- 8>&- 9>&- &
    DRV_STATUS="restarted"
  else
    DRV_STATUS="down(无待办)"
  fi
fi

# ---- 2) dashboard：进程 + HTTP 活性 ----
DASH_P=$(pgrep -f "dashboard.p[y]" | head -1)
DASH_STATUS="down"
if [ -n "$DASH_P" ]; then
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" -m 3 http://127.0.0.1:${RADAR_DASH_PORT:-8898}/ 2>/dev/null)
  if [ "$HTTP" = "200" ]; then
    DASH_STATUS="up(http:200)"
  else
    log "WARN dashboard 进程在但 HTTP=$HTTP，重启"
    kill "$DASH_P" 2>/dev/null; sleep 1
    setsid nohup python3 "$K8S/dashboard.py" >> "$K8S/dashboard.out" 2>&1 < /dev/null &
    DASH_STATUS="restarted(http:$HTTP)"
  fi
else
  log "dashboard down，拉起"
  setsid nohup python3 "$K8S/dashboard.py" >> "$K8S/dashboard.out" 2>&1 < /dev/null &
  DASH_STATUS="restarted"
fi

# ---- 3) cadence：进程 + 日志活性 ----
CAD_P=$(pgrep -f "cadence-loo[p]" | head -1)
CAD_STATUS="down"
if [ -n "$CAD_P" ]; then
  CAD_AGE=$(sec_since "$K8S/cadence.log")
  if [ "$CAD_AGE" -gt 3600 ]; then
    log "WARN cadence 进程在但 ${CAD_AGE}s 无日志（10 分钟间隔应更频繁）→ 重启"
    kill "$CAD_P" 2>/dev/null; sleep 1
    setsid nohup bash "$K8S/cadence-loop.sh" > /dev/null 2>&1 < /dev/null &
    CAD_STATUS="restarted(stale:${CAD_AGE}s)"
  else
    CAD_STATUS="up(${CAD_AGE}s)"
  fi
else
  log "cadence down，拉起"
  setsid nohup bash "$K8S/cadence-loop.sh" > /dev/null 2>&1 < /dev/null &
  CAD_STATUS="restarted"
fi

# ---- 4) metrics：进程 + 最新文件活性 ----
MET_P=$(pgrep -f "metrics-loo[p]" | head -1)
MET_STATUS="down"
if [ -n "$MET_P" ]; then
  MET_AGE=$(sec_since "$K8S/metrics/system.jsonl")
  if [ "$MET_AGE" -gt 300 ]; then
    log "WARN metrics 进程在但 ${MET_AGE}s 无数据 → 重启"
    kill "$MET_P" 2>/dev/null; sleep 1
    setsid nohup bash "$K8S/metrics-loop.sh" > /dev/null 2>&1 < /dev/null &
    MET_STATUS="restarted(stale:${MET_AGE}s)"
  else
    MET_STATUS="up(${MET_AGE}s)"
  fi
else
  log "metrics down，拉起"
  setsid nohup bash "$K8S/metrics-loop.sh" > /dev/null 2>&1 < /dev/null &
  MET_STATUS="restarted"
fi

# ---- 5) 发现段：candidates 过期刷新 ----
CAND_AGE=$(sec_since "$REPO/generated/current/candidates.json")
CAND_AGE_H=$(( CAND_AGE / 3600 ))
if [ "$CAND_AGE_H" -ge 6 ]; then
  log "发现段陈旧 ${CAND_AGE_H}h，重跑"
  (cd "$REPO" && timeout 120 python3 scripts/discover.py >> "$K8S/probe.log.discover" 2>&1 \
    && python3 - "$REPO/generated/current/candidates.json" > /tmp/to-clone.new << 'PY'
import json, sys, os
from pathlib import Path
repo = Path(os.path.expanduser("~/dsh-external-research"))
d = json.load(open(sys.argv[1]))
clones = {x.name for x in (repo/".clones").iterdir() if x.is_dir() and not x.name.startswith(".")} if (repo/".clones").exists() else set()
for c in d.get("candidates", []):
    fn = c.get("full_name") or ""
    if not fn or "/" not in fn or fn.startswith("github:"): continue
    if fn.split("/")[-1] in clones: continue
    print(fn + "\t" + (c.get("url") or "https://github.com/" + fn + ".git"))
PY
  ) && mv /tmp/to-clone.new /tmp/to-clone.txt && log "to-clone 刷新: $(wc -l < /tmp/to-clone.txt) 条"
fi

# ---- 6) 心跳（必写，不静默失败）----
python3 - "$HB" "$NOW" "$DRV_STATUS" "$DASH_STATUS" "$CAD_STATUS" "$MET_STATUS" "$CAND_AGE_H" << 'PYW'
import json, sys, os, glob
from pathlib import Path
hb, now, drv, dash, cad, met, age = sys.argv[1:8]
repo = Path(os.path.expanduser("~/dsh-external-research"))
rt = repo/".rt-agent"
results = len(list(rt.glob("*.json"))) if rt.exists() else 0
plugins = 0
pl = repo/".clones/.verified/.plugins.txt"
if pl.exists(): plugins = len(set(pl.read_text().split()))
data = {"ts": __import__("datetime").datetime.fromtimestamp(int(now)).isoformat(),
        "driver": drv, "dashboard": dash, "cadence": cad, "metrics": met,
        "candidates_age_h": int(age), "results": results,
        "plugins_verified": plugins, "pending": max(0, plugins - results)}
Path(hb).write_text(json.dumps(data, ensure_ascii=False))
PYW

log "心跳 driver=$DRV_STATUS dash=$DASH_STATUS cad=$CAD_STATUS met=$MET_STATUS cand=${CAND_AGE_H}h"
