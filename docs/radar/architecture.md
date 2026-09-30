# 雷达架构

> 六层管线的实现说明。部署拓扑（节点地址、代理、凭据）不随文档开源；本文只描述与仓内产物对应的机制本身。术语与 [overview.md](overview.md) 一致。

## 发现层

候选仓库来自两条互补的路：

- **GitHub 搜索路**：按星数区间检索，命中过多时递归下钻时间分片（年→月→日→时），饱和分片显式记录，不静默截断。
- **npm 交叉路**：检索 npm 注册表中 `dsh-*` 命名与 `dsh-plugin` 关键词的包，经 `package.repository` 字段映射回 GitHub 仓库——这条路覆盖 GitHub 搜索盲区（不发 README、纯包发布）的作者。

两路均有单轮新增上限，防止候选池瞬时打爆测试队列；发现失败不阻塞其他层（fail-open），但会留痕。

## 登记层

两条登记轨并行，渲染层取**并集**：

- **手工登记轨**：`PLUGINS.md` 单插件表一行即一条登记，人工提交（guard 审查惯例同先例）。
- **快照自动轨**：测试引擎产出的判定快照。

登记即可见：表行存在而快照未覆盖的仓库按登记信息补行，标注 `[未测]`；已消亡的登记仓进空仓监测，不剔除。

## 测试层

自托管集群（kind）内按 pod 逐仓库执行，pod 自备源码并源自克隆被测仓库，四层递进、失败短路：

| 层级 | 内容 | 失败归类 |
|---|---|---|
| L0 | 静态检查（manifest、结构） | ❌ fail |
| L1 | 真实安装（`dsh plugin add`） | 安装类失败归 ⚠️ infra（冷却重试），仅运行时崩溃判 ❌ |
| L2 | 插件加载（`dsh plugin list` 确认） | 同上 |
| L3 | 对话级实测（本地化模型驱动的行为验证） | 证据落盘当日报告 |

判定语义（自上而下短路）：

- `pass` / `fail` — 终态结论；
- `infra-fail` — 环境问题（网络、权限、磁盘），冷却后重试，不计入插件质量；
- `not-published` — 归 `skipped`，不占用结论位；
- `inconclusive` — 限时重试，超时转终态。

**输入哈希（conclusive 语义）**：`input_hash = sha256(canonical_id + head + tree + 主线SHA + RESULT_CONTRACT_REVISION)`。任一因子变化即触发重测；全部不变则沿用既有结论。契约版本号升级会触发全量重测——这是判定口径演进的显式机制。

**复核四路**：输入哈希变化自动重测、inconclusive 限时重试、issue 申诉快捷复测、跨环境交叉复验（证人样本仅供复核，不直接改判）。

## 聚合层

同一仓库可能在多条轨道、多种键名（登记轨的仓库名、快照轨的 `owner-repo` 形态名、改名前旧名）下出现。聚合以 **GitHub 仓库全名三源归一**合并：

1. 真实 URL（最高优先）；
2. `data/repo-map.json`（canonical_id ↔ 全名映射，含改名 aliases）;
3. `data/locate-cache.json`（定位缓存）。

合并规则：URL 取真实值、星数取实时值、✅/❌ 冲突降 `[待定]`、⚠️ 测不出不参与冲突。改名跟随：星标刷新捕获 `nameWithOwner` 变化时联动改写链接、同名文本与星数，旧名进 aliases。

**死链审计**（`data/url-audit.json`）：对全部呈现过的仓库 URL 做存在性审计，gone 判定带 7 天 TTL 防抖；消亡仓库降 `[空仓监测]` 不再呈现链接。私有 org 仓在认证身份下可见、匿名 404，审计口径判 located 而非 gone。

## 渲染层

全部人读产物从 **canonical 单一事实源**重建而非增量维护（2026-09-27 P1 数据层收敛：`engine/aggregation/build_canonical.py` 产 canonical.json，Markdown 不再被反向解析）：

- `gen_plugins_all.py` — 聚合归一 + PLUGINS-ALL 生成 + 登记表兜底补行；
- `resolve_placeholders.py` — 占位键反查、星数回填、批量补齐星缓存；
- `render-readme-from-snapshot.py` — 双语 README 与 CHANGELOG 渲染；
- `classify.py` — 分类规则引擎（与 [CATALOGING.md](../CATALOGING.md) 声明同源，声明顺序首个命中者胜）。

判定标记语义：✅ 通过 / ❌ 失败 / ⚠️ 环境未测出 / `[待定]` 结论冲突 / `[未测]` 登记未覆盖 / `[空仓监测]` 仓库消亡。

## 分发层

- **快照推送**：机器可读快照（`data/snapshots/`）按轮次提交，schema 见 [schema/](../../schema/)；
- **自动渲染**：GitHub Actions 在快照推送后重建 README/PLUGINS-ALL/CHANGELOG（产物白名单守卫 + 自动合并）；
- **星数日更**：每日定时刷新全部呈现星数，捕获改名；
- **三仓分工**：本仓（引擎镜像仓）= 引擎开源副本 + 站点宿主 + 数据镜像；组织仓为管线仓（快照生产）；个人 awesome 仓为清单仓（登记表）。数据单向流：管线仓→本仓→Pages 站点（ADR-0001 2026-09-27 修订）。

## 运行节奏

| 节拍 | 动作 |
|---|---|
| 每轮（分钟级） | 巡检 + 派发测试 + 心跳写盘 |
| 每日 | 星数/改名刷新、链接审计复核、自动渲染兜底 |
| 每轮手动 sync | PLUGINS-ALL 提交更新（区别于自动渲染白名单） |

单例锁保证派发与推送互斥；「提交消息与 diff 文件不符」「渲染无变化」分别作为载荷串写与链路冻结的故障指纹，监控按此设防。

## 数据层收敛（2026-09-27 P1，ADR-0004）

```
快照(窗口) ⊕ snapshot-baseline ⊕ 登记轨 ⊕ 定位/描述缓存
            └────────────┬────────────┘
                         ▼
        engine/aggregation/build_canonical.py
                         ▼
        generated/current/canonical.json（radar-canonical/v1）
        ├── engine/rendering/render_all.py → PLUGINS-ALL.md + catalog/all/
        ├── scripts/export-data.py        → latest.json + plugins-all.json（dsh-radar/v1）
        ├── site/scripts/build_data.py    → Pages 站点 bundle
        └── compat/lib_report.sh          → mainline-compat.json
```

快照装载 = 现存文件全扫 ⊕ 基线垫底（ADR-0002 落地：基线固化带重放等价断言，
窗口外快照已裁剪，工作区 IO 有界）。
