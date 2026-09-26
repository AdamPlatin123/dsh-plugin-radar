# ADR-0004：全量重构——canonical 单一事实源 + lib 层 + 唯一门控

日期：2026-09-27 ｜ 状态：已实施（P0–P4）

## 背景

2026-09-26 架构鉴定（12-agent 勘察 + 对抗验证）证实三类系统性债务：
数据供给三条路径并存（快照渲染器 / Shell mainline 栈 / Python summary 栈）且
aggregate.py「唯一来源」宣言落空；公共惯用法（原子写/密钥读取/阈值/合并门控）
多处复制且强度不一；增量检测死代码、404 错误对象入库、schema 零执行、
开源副本不可独立运行等高危缺陷。

## 决定

1. **canonical 单一事实源**（`engine/aggregation/build_canonical.py` →
   `generated/current/canonical.json`）：三条数据路径收敛为一条——
   渲染（render_all）/ 导出（export-data）/ 站点烘焙（site build_data）同源消费。
   验收标准：新旧管线产物逐字节一致（PLUGINS-ALL.md 13 域文件全等、
   latest/plugins-all.json 逐字段等价、generated_at 除外）。
2. **快照治理落地（ADR-0002 兑现）**：`rebaseline.py` 固化窗口外历史为
   `data/snapshot-baseline.json`（重放等价断言 fail-closed），裁剪 568→473 份。
3. **公共 lib 层**（`engine/lib/radar/`）：原子写（atomicio）、密钥解析
   （secretsource，env > 0600 keyfile > sqlite 兜底，header 文件传 curl）、
   GraphQL 客户端（ghql，urllib 直连 token 不进 argv）、git 封装（gitops，
   push 只允许 --force-with-lease）、阈值（thresholds）、消毒（sanitize）。
4. **唯一合并门控**（`engine/distribution/merge_guard.py`）：head SHA 钉死 +
   作者钉死 + 文件集合精确匹配（glob），四处强度不一的实现全部收敛；
   缺推送 SHA 即拒绝自动合并（fail-closed，不降级）。
5. **compare-mainline 拆分**：1117 行单体 → compat/ 编排壳 + 五职能库，
   函数清单与 dry-run 输出与原单体逐一致；新增 mainline-compat.json
   结构化产物。原件留名 legacy-* 双轨观察一个周期。
6. **安全网先行**（P0）：alerts + data-freshness 工作流 + radar-v1 契约
   schema + CI 校验（`scripts/validate_contracts.py`）。

## 被否方案

- 「aggregate.py 改读 canonical」：summary.json 统计的是发现轨候选仓人群
  （dashboard/probe 消费），与公开清单人群不同——强行合流会错换语义；
  改为修正其 docstring 与实际消费方对齐。
- 「保留 gh-pages 分支部署」：bot 每日多提交会把分支历史撑到 GB 级；
  artifact 型发布原子且可秒级回滚（见 ADR-0005）。

## 影响

引擎互调一律 dirname 相对路径（`./scripts/*.sh` 扁平引用清零）；
服务器 crontab 路径经 scripts/ 转发壳保持稳定（迁移手册 docs/RUNBOOK.md）。
