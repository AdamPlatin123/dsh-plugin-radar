# 雷达数据契约

> 雷达产出物的机器可读格式。schema 是权威：[schema/plugin.schema.json](../../schema/plugin.schema.json)、[schema/summary.schema.json](../../schema/summary.schema.json)、[schema/observation.schema.json](../../schema/observation.schema.json)。

## 快照（data/snapshots/）

每轮管线产出一份带 UTC 时间戳的快照，是渲染层唯一输入。快照内条目按 canonical 仓库身份去重；历史快照保留供追溯，最新一份即当前口径。

## 缓存（data/*.json）

| 文件 | 语义 | 失效口径 |
|---|---|---|
| `repo-map.json` | canonical_id ↔ GitHub 全名映射，含改名 aliases；条目可带 `checked_at`（扫描主机观测到该全名的时刻），身份归一时与 enrich 的 `identity_checked_at` 比较新旧 | 扫描主机每日导出，只增不减 |
| `locate-cache.json` | 占位键（`owner-repo`）→ 真实仓库定位结果，附实时星数 | 定期复核刷新 |
| `url-audit.json` | 仓库存在性审计：真实 URL ∪ 定位命中 ∪ 手工区链接 | gone 判定 7 天 TTL 防抖 |
| `desc-cache.json` | 仓库描述缓存 | 跟随快照轮次 |
| `curated-overrides.json` | 人工覆写（精选位、置顶等） | 人工维护 |
| `awesome-50.json` | 精选榜单数据 | 由 `refresh-featured.py` 维护 |

## PLUGINS-ALL 行格式

每行一个插件：名称（链接真实仓库）、分类、判定标记、星数（裸数字，无 ★ 前缀）、描述。判定标记集合与冲突降级规则见 [architecture.md](architecture.md) 渲染层一节。

## 结果契约版本

`RESULT_CONTRACT_REVISION` 是测试判定的格式版本号，参与输入哈希。升级即全量重测——消费者据此判定历史结论是否可比。

## reports/

按日期组织的测试报告目录：当日对话级实测（L3）证据、申诉复核记录。报告是判定的证据链，渲染层「运行实测」链接只指向当日报告。
