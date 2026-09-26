# DSH 插件雷达 · 总览与开源路线图

> 雷达（Radar）是本仓索引数据的**生产引擎**：一条从「发现候选插件」到「可读看板」的全自动管线。本文件说明它是什么、产出什么、以及分阶段开源的计划。架构细节见 [architecture.md](architecture.md)，数据格式见 [data-contracts.md](data-contracts.md)。

## 雷达是什么

DSH 插件生态没有中心化市场——插件以 GitHub 仓库和 npm 包的形式散落分布。雷达持续扫描这些来源，把「存在多少插件、各自质量如何、是否还在维护」变成本仓里可复核的数据：

| 管线环节 | 职责 | 本仓可见的产出 |
|---|---|---|
| 发现 | GitHub 搜索（递归时间分片）+ npm 注册表交叉路，汇聚候选仓库 | 候选池进入测试队列 |
| 登记 | 人工登记轨（`PLUGINS.md`）与自动快照轨取并集 | [PLUGINS.md](../../PLUGINS.md) |
| 测试 | 自托管集群内真实安装并加载每个插件，四层递进判定 | [reports/](../../reports/)、快照判定字段 |
| 聚合 | 三源归一同一仓库的身份（URL/星数/改名跟随），审计死链 | [data/repo-map.json](../../data/repo-map.json)、[data/url-audit.json](../../data/url-audit.json) |
| 渲染 | 从快照重建全部人读产物，双语同步 | [PLUGINS-ALL.md](../../PLUGINS-ALL.md)、[README.md](../../README.md)、[CHANGELOG.md](../../CHANGELOG.md) |
| 分发 | 机器可读快照推送 + GitHub Actions 自动渲染/星数日更 | [data/snapshots/](../../data/snapshots/)、[schema/](../../schema/) |

## 设计立场

- **真实安装优于静态扫描**：判定来自 `dsh plugin add` 的真实安装与加载路径，而非仅读 manifest。
- **结论可复核**：每条判定绑定输入哈希（仓库 head/tree/主线 SHA/契约版本），输入不变不重测、输入一变必重测；复核四路并行（自动/重试/申诉/交叉复验）。
- **登记即可见**：手工登记的插件不等待测试覆盖，渲染层立即收录并标注「未测」。
- **消亡有痕迹**：仓库删除/转私有不静默剔除，降级为「空仓监测」并保留历史行。

## 开源路线图

雷达按「先文档、后引擎、再测试源码」三阶段开源：

| 阶段 | 内容 | 状态 |
|---|---|---|
| Phase 1 | **文档先行**（本文件集）：管线架构、数据契约、判定语义全部公开 | ✅ 本次交付 |
| Phase 2 | **雷达引擎源码**：发现、聚合、渲染、分发四环的完整实现（渲染链已随 `scripts/` 在仓） | 已开源（engine/，2026-09 第二阶段） |
| Phase 3 | **测试引擎源码，双形态**：`轻量版`（无需 k8s——本地直接执行测试，clone 即可复现 L0–L2 判定）与 `服务器版`（k8s 集群形态：多 pod 并行、四层测试、复核调度） | 已开源（engine/，2026-09 第二阶段） |

Phase 2/3 的「稳定」判据：聚合键口径（canonical 归一）与测试契约版本（`RESULT_CONTRACT_REVISION`）进入无频繁变更的平缓期，避免开源首月即面对不兼容重构。

## 已开源的部分

以下能力已随本仓公开，可视为 Phase 2 的先行切片：

- `scripts/gen_plugins_all.py` — 聚合与 PLUGINS-ALL 生成（canonical 归一实现）
- `scripts/resolve_placeholders.py` — 占位键反查真实仓库与星数回填
- `scripts/render-readme-from-snapshot.py` — 快照到双语 README 的渲染
- `scripts/classify.py` — 与 [CATALOGING.md](../CATALOGING.md) 同源的分类规则引擎
- `scripts/refresh-stars.py` / `refresh-featured.py` — 星数日更与精选位刷新

> 2026-09-27：第二阶段引擎已开源并完成全量重构（ADR-0004）；演示站上线（ADR-0005）。
