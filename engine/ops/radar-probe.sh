#!/usr/bin/env bash
# radar-probe.sh — 巡检：组件拉起 + Bot A 自推快照 + Bot B 渲染检测
set -uo pipefail
export PATH=$HOME/.local/bin:$PATH
K8S=$HOME/dsh-k8s

# 0) Bot A 全自动：有增量 → 快照上 main
bash $K8S/auto-snapshot-push.sh >> $K8S/auto-snap.log 2>&1

# 0.5) Bot B 渲染：main 新快照 → 渲染 PR → 自动合并
bash $K8S/readme-render-watch.sh >> $K8S/render-watch.log 2>&1

# 1) 组件拉起
for C in "metrics-loo[p]" "cadence-loo[p]" "dashboar[d].py" "pipeline-driver.p[y]"; do
  pgrep -f "$C" >/dev/null || {
    echo "[probe] $C 死亡，拉起"
    case "$C" in
      metrics-loo[p]) systemctl --user start radar-metrics.timer 2>/dev/null || setsid nohup python3 $K8S/metrics-probe.py >> $K8S/metrics/loop.log 2>&1 < /dev/null & ;;
      cadence-loo[p]) setsid nohup bash $K8S/cadence-loop.sh >> $K8S/cadence.log 2>&1 < /dev/null & ;;
      dashboar[d].py) setsid nohup python3 $K8S/dashboard.py > $K8S/dashboard.out 2>&1 < /dev/null & ;;
      driver-disabled-20260827) true;; # pipeline-driver.p[y]) systemctl --user start radar-pipeline.service 2>/dev/null || setsid nohup flock -n /tmp/radar-driver.single env PYTHONUNBUFFERED=1 python3 $K8S/pipeline-driver.py --converge --capacity 6 >> $K8S/pipeline.log 2>&1 < /dev/null & ;;
    esac
    sleep 2
  }
done

# 2) 心跳
echo "[$(date +%H:%M:%S)] 心跳 ok：driver=$(pgrep -f pipeline-driver.py >/dev/null && echo up || echo down) dash=$(curl -s -m 3 -o /dev/null -w "%{http_code}" http://127.0.0.1:${RADAR_DASH_PORT:-8898}/) met=$(pgrep -f metrics-probe >/dev/null && echo up || echo down)"

# 3) watchdog 心跳新鲜度兜底：watchdog 由 cron */5 调用并写 probe-heartbeat.json；
#    若心跳超 15 分钟未更新（cron 丢失/挂起），此处主动补跑一次 watchdog
HB=$K8S/probe-heartbeat.json
if [ -f "$HB" ]; then
  HB_AGE=$(( $(date +%s) - $(stat -c %Y "$HB" 2>/dev/null || date +%s) ))
  if [ "$HB_AGE" -gt 900 ]; then
    echo "[probe] WARN watchdog 心跳过期 ${HB_AGE}s，主动补跑 watchdog"
    flock -w 60 /tmp/radar-watchdog.lock -c "bash $K8S/radar-watchdog.sh >> $K8S/watchdog.log 2>&1" || true
  fi
fi

