# 雷达引擎源码（第二阶段开源 · 2026-09-27 P1–P4 全量重构后布局）

本目录是「DSH 插件雷达」的**生产引擎源码**——发现、聚合、渲染、分发四个域，外加公共库层、运维自愈与目录维护。这些脚本不是示例：它们在真实服务器上持续运转，产出了你在本仓库 README 里看到的全部数字。

## 目录 ↔ 管线映射

| 目录 | 域 | 内容 |
|---|---|---|
| `lib/radar/` | 公共层 | 唯一实现：atomicio 原子写 · secretsource 密钥（env > `~/.radar-keys/` > sqlite 兜底，header 文件传 curl）· ghql GraphQL 客户端（urllib 直连，限速感知）· gitops（push 只允许 `--force-with-lease`）· thresholds · sanitize 消毒 |
| `discovery/` | 发现 | `discover.py`（GitHub topic×2 + keyword×3、403 退避）· `cron-check.sh`（编排：增量检测逻辑在 `lib_cron_logic.sh`，回归用 `scripts/selftest-cron-increment.sh`）· `watch-*.sh` |
| `aggregation/` | 聚合 | `build_canonical.py`（**统一聚合器** → `generated/current/canonical.json` 单一事实源，三条数据路径的收敛点）· `rebaseline.py`（ADR-0002 基线固化+窗口裁剪，重放等价断言 fail-closed）· `aggregate.py`（发现轨统计，dashboard/probe 消费）· `normalize.py` |
| `rendering/` | 渲染 | `render_all.py`（canonical → PLUGINS-ALL.md + catalog/all）· `gen-catalog.sh`（读 `data/domain-map.json`，支持 `--offline` 缓存）· `update-readme.sh` · `report-llm.sh` |
| `distribution/` | 分发 | `merge_guard.py`（**唯一自动合并门控**：head SHA+作者+文件集合三重闸门，回归 `scripts/selftest-merge-guard.sh`）· `cadence.py` · `bot-deliver.sh` / `deliver-*.sh` · `auto-snapshot-push.sh`（含内容门禁：JSON 合法性+API 错误对象+关键文件形态）· `auto-merge-render.sh` |
| `maintenance/` | 目录维护 | `compat/`（compare-mainline 五库化：编排壳 + `lib_{fetch,anchor,patch,report,state}.sh`；`lib_report` 增产 `mainline-compat.json`；原 1117 行单体留名 `legacy-compare-mainline.sh` 双轨观察）· `build-mainline.sh` · `check-ref-lag.sh` · `fix-plugin.sh` · `report-*.sh` |
| `ops/` | 运维自愈 | `radar-probe.sh`（15 分钟心跳）· `radar-watchdog.sh`（看门狗+私有件自检）· `dashboard.py`（`RADAR_DASH_PORT`，默认 8898）· `model-*.sh` · `monitor-usage.sh` · `private/MANIFEST.md`（私有件契约清单） |

## 运行环境契约

**环境变量**（脚本零硬编码凭证）：

```bash
GH_TOKEN                 # GitHub 读写（发现+bot 交付；缺省回落 gh auth token）
DEEPSEEK_API_KEY         # LLM 摘要（或 ~/.radar-keys/deepseek，0600；再兜底 sqlite）
DSH_QWEN_BASE_URL        # de-stream 模型端点（本地 127.0.0.1 形态）
RADAR_K8S_DIR            # 私有件根目录（默认 ~/dsh-k8s）
RADAR_DASH_PORT          # 面板端口（默认 8898）
```

**期望目录布局**（生产形态）：

```
~/dsh-external-research/   # 本仓库 clone（引擎从这里运行；scripts/ 为转发壳，crontab 旧路径不断）
~/dsh-k8s/                 # 私有件（k8s 挂具/探针/bot；契约与降级行为见 engine/ops/private/MANIFEST.md）
```

**crontab 样例**（真实生产节奏）：

```cron
*/15 * * * * flock -n /tmp/radar-probe.lock    -c "bash ~/dsh-k8s/radar-probe.sh    >> ~/dsh-k8s/probe.log 2>&1"
*/5  * * * * flock -w 60 /tmp/radar-watchdog.lock -c "bash ~/dsh-k8s/radar-watchdog.sh >> ~/dsh-k8s/watchdog.log 2>&1"
17   */4 * * * flock -n /tmp/radar-discover.lock -c "cd ~/dsh-external-research && python3 engine/discovery/discover.py >> ~/dsh-k8s/discover.log 2>&1"
```

## 诚实边界

- **第三阶段（k8s 运行级验证器）未含在本目录**：一插件一 pod 的隔离测试引擎、L0–L3 分层判定、`input_hash` 增量重测属于第三阶段，稳定后开源轻量版与服务器版。
- 脚本为服务器生产形态（bash + python 混合、经 dirname 相对路径互调；`./scripts/*.sh` 扁平引用已清零）；包化 CLI（`dsh-radar discover/scan/report`）在路线图上。
- 私有件（`~/dsh-k8s`）全部引用点带在场守卫：缺件显式 WARN 安全降级，开源副本可运行到「仅缺私有件功能」。
- 设计文档：[docs/radar/architecture.md](../docs/radar/architecture.md)（六层管线）· [docs/radar/data-contracts.md](../docs/radar/data-contracts.md)（数据契约）· [docs/adr/0004](../docs/adr/0004-full-refactor.md)（重构决议）· 服务器迁移手册 [docs/RUNBOOK.md](../docs/RUNBOOK.md)。
