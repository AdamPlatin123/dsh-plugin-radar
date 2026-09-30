# 私有件契约清单（engine/ops/private/MANIFEST.md）

> 开源副本的诚实边界（P2c）：以下组件属未开源的 `~/dsh-k8s`（服务器私有件，第三阶段开源计划内），
> 仓库内引擎脚本对它们的全部引用点均已加**在场守卫**——缺失时显式 WARN 并安全降级/跳过，
> 开源副本可独立运行到「仅缺私有件功能」的程度。私有件根目录可用环境变量
> `RADAR_K8S_DIR` 覆盖（默认 `$HOME/dsh-k8s`）。

| 私有件 | 引用点 | 契约（输入 → 输出） | 缺失时行为 |
|---|---|---|---|
| `radar-index-request.py` | `engine/discovery/cron-check.sh`（worker 门禁） | `--reason --trigger` → 入队一条索引请求 | WARN 后按「已入队」退出（开源副本手动直跑走 `RADAR_INDEX_WORKER=1`） |
| `gen-snapshot-v2.py` | `engine/distribution/auto-snapshot-push.sh`（①生成快照） | 无参 → `$SNAP_DIR/data/snapshots/<run_id>.json`（radar-snapshot/2） | WARN 后本轮跳过（exit 0，不推） |
| `aggregate-agent-test.py` | `engine/distribution/deliver-all.sh`、`bot-deliver.sh` | 读 `.rt-agent/` 流式结果 → `reports/<日期>/agent-test.md` | WARN 后跳过聚合；deliver-all 继续提交已有结果 |
| `bot-deliver.sh`（服务器版） | `engine/distribution/deliver-all.sh`、`deliver-chain.sh` | 读当日报告 → 双仓 bot PR | WARN 后跳过 bot 交付 |
| `finish-rerun.sh` | `engine/distribution/deliver-chain.sh`（仅 pgrep 等待） | 自聚合+推个人仓 | pgrep 无进程即自然通过，无需守卫 |
| `radar-bot-token.sh` | `engine/distribution/cadence.py:135`（bot-app 令牌装载） | 无参 → stdout 令牌 | try/except 已兜底（空令牌→个人 gh 凭据路径） |
| `pipeline-driver.py` / `cadence-loop.sh` / `metrics-loop.sh` | `engine/ops/radar-watchdog.sh`（活性拉起） | 常驻驱动/交付/指标循环 | 启动自检逐件 WARN；拉起命令对缺失文件自然失败且日志可见 |
| `readme-render-watch.sh` | `engine/ops/radar-probe.sh:11`（探测目标） | 渲染链观察器 | 探测 down 分支已有，无阻断 |
| `state/`（pipeline-state.json 等） | `engine/ops/dashboard.py`（面板数据） | 私有引擎状态目录 | dashboard 按缺文件降级显示 |

**服务器 ↔ 开源副本布局对应**：服务器 `~/dsh-external-research/scripts/*.sh`（扁平）= 本仓
`engine/<域>/`；`auto-snapshot-push.sh` 每轮从本仓 main 的 `scripts/` 拉取转发壳保持服务器
crontab 路径稳定。引擎内互调一律 dirname 相对路径（如 `$SCRIPT_DIR/../maintenance/compare-mainline.sh`），
不再出现 `./scripts/*.sh` 扁平引用（2026-09-26 P2c 清零，鉴定报告「开源副本不可独立运行」项）。
