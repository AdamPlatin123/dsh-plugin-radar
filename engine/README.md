# 雷达引擎源码（第二阶段开源）

本目录是「DSH 插件雷达」的**生产引擎源码**——发现、聚合、渲染、分发四个域，外加运维自愈与目录维护。这些脚本不是示例：它们在真实服务器上持续运转，产出了你在本仓库 README 里看到的全部数字（候选 15900+、收录 7096、运行级实测 10025）。

## 目录 ↔ 管线映射

| 目录 | 域 | 内容 |
|---|---|---|
| `discovery/` | 发现 | `discover.py`（GitHub topic×2 + keyword×3 全量发现、403 退避、错峰）· `watch-npm.sh` / `watch-mainline.sh`（npm 与主线 watch）· `cron-check.sh` |
| `aggregation/` | 聚合 | `aggregate.py` / `normalize.py`（快照聚合与判定归一）· `aggregate-runtime.sh` |
| `rendering/` | 渲染 | `gen-catalog.sh`（分类目录生成）· `update-readme.sh` · `check-placeholders.sh`（占位符校验）· `report-llm.sh` |
| `distribution/` | 分发 | `bot-deliver.sh` / `deliver-chain.sh` / `deliver-all.sh`（双仓幂等交付）· `auto-snapshot-push.sh` / `auto-merge-render.sh`（org→mirror 快照同步 + 渲染门控合并）· `cadence.py`（周期交付判定，含输出密钥擦洗） |
| `ops/` | 运维自愈 | `radar-probe.sh`（15 分钟七指标心跳）· `radar-watchdog.sh`（5 分钟看门狗）· `dashboard.py`（RADAR_DASH_PORT，默认 8898 面板）· `model-probe.sh` / `model-compare.sh`（模型探针）· `monitor-usage.sh` |
| `maintenance/` | 目录维护 | mainline 构建/对比/滞后检查 · `fix-plugin.sh` · issue 起草与上报三件套 |

## 运行环境契约

**环境变量**（脚本不含任何硬编码凭证）：

```bash
GH_TOKEN             # GitHub 读写 token（发现 + bot 交付）
DSH_QWEN_BASE_URL    # de-stream 代理的模型端点（本地 127.0.0.1 形态）
DEEPSEEK_API_KEY     # 冒烟测试用（可为占位 none，走本地代理时）
```

**期望目录布局**（生产形态）：

```
~/dsh-external-research/   # 本仓库 clone（引擎 scripts 从此处运行）
~/dsh-k8s/                 # k8s 挂具与探针/看门狗（含 bot token 装载器，不入仓）
```

**crontab 样例**（真实生产节奏）：

```cron
*/15 * * * * flock -n /tmp/radar-probe.lock    -c "bash ~/dsh-k8s/radar-probe.sh    >> ~/dsh-k8s/probe.log 2>&1"
*/5  * * * * flock -w 60 /tmp/radar-watchdog.lock -c "bash ~/dsh-k8s/radar-watchdog.sh >> ~/dsh-k8s/watchdog.log 2>&1"
17   */4 * * * flock -n /tmp/radar-discover.lock -c "cd ~/dsh-external-research && python3 scripts/discover.py >> ~/dsh-k8s/discover.log 2>&1"
```

## 诚实边界

- **第三阶段（k8s 运行级验证器）未含在本目录**：一插件一 pod 的隔离测试引擎、L0–L3 分层判定、`input_hash` 增量重测属于第三阶段，稳定后开源轻量版（本地直跑）与服务器版。
- 脚本为服务器生产形态（bash + python 混合、按绝对布局引用），包化 CLI（`dsh-radar discover/scan/report`）在路线图上。
- 设计文档见 [docs/radar/architecture.md](../docs/radar/architecture.md) 与 [docs/radar/data-contracts.md](../docs/radar/data-contracts.md)；多轴判定改造设计见 [docs/superpowers/specs/](../docs/superpowers/specs/)。
