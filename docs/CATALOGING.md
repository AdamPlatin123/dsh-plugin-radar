# 插件分类标准（taxonomy v2 · 固定版）

> 本标准是 bot 提 PR、人工登记与自动分类器的**唯一分类依据**。13 类按下列顺序声明，规则引擎按声明顺序首个命中者胜。改动本文件需同步 `scripts/classify.py`（规则同源）。

## 类目与判定规则

| 顺序 | 类目 | 定义 | 关键词规则（名称/描述，不区分大小写） |
|---|---|---|---|
| 1 | 🎓 技能包 | 以 skill 形态提供能力：技能集合、技能分发、技能搜索 | `skill / 技能` |
| 2 | 🧠 记忆增强 | 跨会话/长期记忆、检索、蒸馏 | `mem(memory/memories) / 记忆 / recall / 遗忘 / 蒸馏 / distill` |
| 3 | 🎨 主题皮肤 | 仅改观感不改功能：主题、皮肤、CSS、像素装饰、贴纸表情 | `theme / skin / 皮肤 / 主题 / 像素 / 壁纸 / 外观 / css / sticker / 贴纸 / 表情包 / emoji` |
| 4 | 🛒 市场与管理 | 插件市场、包管理、健康检查、装卸载 | `market / store / registry / manager / 市场 / 商店 / 工坊 / workshop / health check / 健康检查 / 卸载 / installer / 包管理 / 插件浏览` |
| 5 | 🔌 Web UI 增强 | Web/TUI 界面功能：侧栏、输入、面板、批注、状态栏 | `web ui / webui / sidebar / 侧边栏 / 输入框 / input / 面板 / panel / 批注 / 状态栏 / dock / 气泡 / toast / 导航 / navbar` |
| 6 | 💻 编码开发 | 编码场景：代码、git、diff、终端、语言、构建、测试 | `code / 编码 / git / github / diff / 终端 / terminal / shell / lsp / 编译 / build / 测试 / test / review` |
| 7 | 🤖 Agent 能力 | agent 本体：子代理、规划执行、上下文、唤醒睡眠、审批 | `agent / 子代理 / subagent / 规划 / plan / 上下文 / context / 唤醒 / 自治 / loop / 预算 / budget / 审批 / approv` |
| 8 | 📡 消息通讯 | IM 与消息通道：微信/QQ/TG/飞书 bot、通知、消息 | `微信 / wechat / wecom / 飞书 / feishu / telegram / tg / qq / bot / 通知 / notify / 消息 / message / chat` |
| 9 | 🗂 文件数据 | 文件与数据：读写、爬取、数据库、文档解析、知识库 | `文件 / file / 数据 / data / 爬 / crawl / 数据库 / sqlite / 文档 / pdf / 知识库 / kb / rag / 索引 / ocr / csv` |
| 10 | 🎮 娱乐生活 | 摸鱼与趣味：游戏、宠物、音乐、行情 | `游戏 / game / 宠物 / pet / 鲸鱼 / whale / 音乐 / 股票 / 行情 / 摸鱼 / 旅行` |
| 11 | 🛠 基建部署 | 运行环境与分发：沙箱、远程、代理、监控、桌面端 | `沙箱 / sandbox / 部署 / deploy / 远程 / remote / ssh / docker / k8s / 监控 / monitor / 桌面 / desktop / 托盘 / tray / 更新 / update / 代理 / proxy / mcp` |
| 12 | 📚 学习研究 | 学习与探索：教程、指南、评测、研究 | `教程 / tutorial / 指南 / guide / 评测 / benchmark / 基准 / 研究 / research / 论文 / 学习` |
| 13 | ❓ 其他 | 兜底。提 PR 时请尽量避免使用 | — |

## 边界归属（常见争议）

- **技能 vs 插件**：以 skill 形态分发（.dsh/skills 目录、技能注册）→ 技能包；以 npm 包/plugin 形态 → 按功能归 5-12。
- **主题 vs UI 增强**：只换外观（皮肤/CSS/像素）→ 主题皮肤；增改功能（新面板/新交互）→ Web UI 增强。
- **通知 vs 消息通讯**：出站推送（notify）与 IM bot 统归消息通讯（生态内两者高度重叠，不拆）。
- **MCP/模型接入**：接入外部模型或 MCP 服务 → 基建部署；模型输出处理（vision/OCR 文档）→ 文件数据。
- **市场 vs 基建**：管理「插件本身」的装卸载/市场 → 市场与管理；运行环境/分发 → 基建部署。

## Bot 提 PR 时的提前归类流程

1. 登记 PR 前运行预归类器：`python3 scripts/classify.py "<插件名>" "<一句话描述>"`
2. 将输出的「建议分类」填入 PR 模板的**分类**字段；命中规则为空（兜底其他）时人工复核改名。
3. 规则与本文档同源（`scripts/classify.py` 的 `RULES`）；修改分类标准 = 改本文档 + 同步规则并重跑 `python3 scripts/render-readme-from-snapshot.py`。

## 静态证据（ENTRY / `static`）

`catalog/policy.json` 的 `admission.candidate_to_listed_requires` 已声明 `static_outcome_not_fail`，`schema/observation.schema.json` 也允许 `evidence.static` 取 `pass|warn|fail|not_run|inconclusive`。本节说明这个槽位的数据来源、字段与边界。

### 来源

- 只读**已发布到 npm 公共 registry** 的 tarball：`scripts/entry-precheck.py` 用 `npm view` 解析版本，用 `npm pack --ignore-scripts` 下载 tarball；registry 固定为 `https://registry.npmjs.org/`。
- 不 clone 源码仓、不访问 codeload、不安装 tarball、不执行其中任何代码；检查器以 `--no-exec` 运行。
- 归属校验：`npm view ... repository` 返回的仓库必须与 catalog 条目的 `repository.full_name` 一致；不一致、缺失或只有同名包时记 `not_run`（`npm_repository_mismatch` / `npm_repository_missing` / `catalog_repository_missing`），不把异仓同名包算成命中。
- 检查器固定为 `dsh-standards@1.6.8`，命令为
  `dsh-standards check <dir> --scope entry --entry-claim static --no-exec --json`。
- `.github/workflows/entry-precheck.yml` 按 `schedule`（每日 04:17 UTC）与 `workflow_dispatch` 运行脚本，`contents: read`，把 `data/entry-cache.json` 与 `reports/entry-precheck/` 作为构建 artifact 上传，**不提交、不写 main**。本 PR 不附带任何生成好的缓存或报告。

### 缓存字段

`data/entry-cache.json`，`schema: dsh-entry/v1`，`entries` 以 `github:<numeric-id>` 为键。每条包含：

| 字段 | 含义 |
| --- | --- |
| `id` / `full_name` / `package` | 目录条目身份与 npm 包名 |
| `checked_at` | 本轮检查时间（UTC） |
| `commit` | npm `gitHead`（可选，存在时才写） |
| `evidence_static` | `pass` / `warn` / `fail` / `not_run` / `inconclusive` |
| `raw` | 检查器原始 `conclusion.status` / `exitCode`，**仅供审计，不参与映射** |
| `entry_blocking` | `pass` / `checked[]` / `not_checked[]`（`coverage.entryBlocking` 子集） |
| `not_checked` | 报告顶层 `notChecked[]` 的检查 id |
| `not_run_reason` | 仅 `not_run` 时出现：`npm_404` / `timeout` / `checker_report_incomplete` 等 |
| `flow` / `boost` | 固定 `not_run` / `not_measured`（本轮不跑） |
| `disclaimer` | 来源边界声明 |

### 映射

纯函数在 `engine/lib/radar/entryevidence.py`：

1. `buckets.blocking` 非空，或 `coverage.entryBlocking.failed` 非空 → `fail`
2. 否则 `coverage.entryBlocking.pass === false` → `inconclusive`（覆盖不全，永不 `pass`）
3. 否则 `buckets.hygiene` 或 `buckets.partial` 非空 → `warn`
4. 否则 → `pass`；抓取/解析/超时 → `not_run`

**不读取 `conclusion.status`**：实测检查器可以在 `status=pass` 时仍报告 blocking 非空或覆盖未完成，照抄会过度声称。

### 消费与边界

- 本 PR **只提供 producer 与 artifact**：不修改 `engine/aggregation/normalize.py`、不修改 `aggregate.py`、不改变 `catalog/plugins/*.json` 或准入/排序/评分。把 artifact 接进管线是维护者的后续决定。
- 本证据是**信息性静态检查**：不代表安装或运行结果；`flow` / `boost` 仍未运行。
- 公开 npm 上不存在、不可访问，或回链对不上 catalog 仓库的包都会得到诚实的 `not_run`。当前 24 条里多数是 `@deepseek-ai/*` / `@dsh-external/*` 私有包；覆盖率低不是失败，也不通过 clone 源码来“补”覆盖。
