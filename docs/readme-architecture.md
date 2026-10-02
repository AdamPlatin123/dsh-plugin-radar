# README 信息架构与自动更新契约

日期：2026-10-03。

## 定位与阅读顺序

项目首页将 DSH Plugin Radar 定位为面向 DeepSeek Harness 插件生态的持续发现、兼容性记录与数据分发基础设施。

阅读顺序为：项目价值 → 浏览、接入与登记入口 → 数据状态 → 判定依据 → 工作原理 → 接入示例 → 贡献与社区。正文以中文为主，首屏提供英文概述。完整榜单、运维指标和详细契约通过专用入口展开。

| 资产 | 职责 |
|---|---|
| [README](https://github.com/AdamPlatin123/dsh-plugin-radar/blob/main/README.md) | 价值主张、阅读导航、同口径摘要与社区入口 |
| [雷达横幅](https://raw.githubusercontent.com/AdamPlatin123/dsh-plugin-radar/main/assets/banner-radar.jpg) | 首屏品牌识别，动态数量不写入图片 |
| [浏览站点](https://adamplatin123.github.io/dsh-plugin-radar/) | 搜索、筛选、插件详情、精选与整合包 |
| [精选与整合包目录](https://github.com/AdamPlatin123/dsh-plugin-radar/blob/main/docs/catalog-highlights.md) | GitHub 阅读回退，保留人工策展名单和迁移时的推荐动态 |
| [完整目录](https://github.com/AdamPlatin123/dsh-plugin-radar/blob/main/PLUGINS-ALL.md) | 自动归并生成的完整记录 |
| [API 文档](https://github.com/AdamPlatin123/dsh-plugin-radar/blob/main/docs/api.md) | 数据字段、历史归并语义、缓存与可用性契约 |
| [社群二维码](https://raw.githubusercontent.com/AdamPlatin123/dsh-plugin-radar/main/assets/community-discussion-20261002.jpg) | 社区入口；更新日与有效期由人工维护，过期提供联系群主的指引 |

架构图说明快照同步、多源聚合和目录、JSON、站点之间的关系。社区登记直接参与聚合；未被测试覆盖的登记条目标为未测。展示补充数据独立接入站点。生产测试引擎尚未开源，首页不将公开引擎等同于完整测试复现能力。

## 摘要写入所有权

首页以 `README:layout:v2` 标记新布局。自动更新只拥有唯一的一对 `AUTO:summary:START` / `AUTO:summary:END` 标记之间的文本。

- [快照渲染器](https://github.com/AdamPlatin123/dsh-plugin-radar/blob/main/scripts/render-readme-from-snapshot.py)重建聚合与完整目录，从最终去重明细计算四档摘要，并核对聚合统计。摘要时间来自对应锚点快照，不使用每次执行的时钟时间。
- 摘要标记缺失、重复或反向时，在生成前返回非零；数据格式错误、重复仓库、非法档位、计数或快照锚点不一致时保留当前 README。
- 相同输入的摘要渲染逐字节一致，摘要之外的定位、链接、架构图、接入说明与二维码保持原样。
- [公开数据导出](https://github.com/AdamPlatin123/dsh-plugin-radar/blob/main/scripts/export-data.py)仍消费同一个聚合模型。统计与明细必须逐档对账；数组外监测计数不计入已定位清单总数。
- 对未带新布局标记的历史首页，快照渲染器保留原有兼容路径。

## 其他写入器

| 写入器 | 新布局下的行为 |
|---|---|
| [精选刷新器](https://github.com/AdamPlatin123/dsh-plugin-radar/blob/main/scripts/refresh-featured.py) | 只替换独立目录页的精选、整合包区块；缺失或歧义标记拒绝写入。状态取自去重后的公开清单，未索引成员不回落到人工种子判定 |
| [精选工作流](https://github.com/AdamPlatin123/dsh-plugin-radar/blob/main/.github/workflows/refresh-featured.yml) | 提交并按已有配置镜像独立目录，不复制整个项目首页 |
| [旧仪表盘](https://github.com/AdamPlatin123/dsh-plugin-radar/blob/main/engine/rendering/update-readme.sh) | 检测新布局后跳过旧首页写入 |
| [旧目录注入器](https://github.com/AdamPlatin123/dsh-plugin-radar/blob/main/engine/rendering/gen-catalog.sh) | 检测新布局后跳过旧首页写入 |
| [旧管线图生成器](https://github.com/AdamPlatin123/dsh-plugin-radar/blob/main/scripts/gen-pipeline-diagram.py) | 检测新布局后跳过，保留人工维护的静态架构图 |

迁移保留社区推荐区块的原始日期与动态数据链接；本仓推荐采集任务不负责更新这个 Markdown 归档。不把历史动态标为当前自动更新内容。私有生产脚本不在本仓验证范围，仍须遵守首页写入所有权。

## 接口可用性与证据

公开 JSON 由 GitHub Raw 托管，无需密钥；接入文档建议后台统一缓存、条件请求、请求超时、有限退避重试和保留上次成功数据。镜像可能延迟，跨文件一致性需固定同一完整 Git 提交后逐档对账。

这些是下游接入约定，不代表仓库部署了缓存代理、防攻击服务或已验证的实时镜像切换。站点插件数据在构建期打包，短时 JSON 故障与已经部署的浏览体验分别说明。

兼容性状态采用历史归并口径；公开明细尚未提供完整逐条插件提交、被测版本、时间与日志。精选目录使用文字状态，不通过全局版本磁贴暗示逐条证据完整。

## 验证要求

维护回归覆盖摘要幂等、摘要外内容保持、标记拒绝、重复仓库、非法档位、错计数与错锚点拒绝、策展区块所有权和旧图生成器保护。CI 冒烟直接调用快照渲染器，再导出并校验数据契约，验证真实产物链。

二维码原图保持字节不变；已核对图片注明的 2026-10-09 前有效期，不将图片验证等同于实际微信入群验证。
