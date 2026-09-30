#!/usr/bin/env bash
# 等 finish-rerun.sh 进程退出（它自己会聚合+推个人仓库），然后 bot PR 交付到 awesome-dsh-plugins
while pgrep -f "bash ~/dsh-k8s/finish-rerun.sh|bash /home/adam/dsh-k8s/finish-rerun.sh" >/dev/null 2>&1; do sleep 60; done
sleep 5
K8S="${RADAR_K8S_DIR:-$HOME/dsh-k8s}"
if [ -f "$K8S/bot-deliver.sh" ]; then bash "$K8S/bot-deliver.sh";
else echo "[deliver-chain] WARN 缺私有件 $K8S/bot-deliver.sh，跳过（engine/ops/private/MANIFEST.md）"; fi
