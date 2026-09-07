# PLUGINS.md — 插件登记清单（分类版）

> 想更快被收录？在对应类别的表格追加一行并提 PR。未登记的仓库只要打 `dsh-plugin` / `dsh-external` topic，会在每日 02:00 全量扫描时自动收录。
>
> 分类体系参考 dsh-external/hub（catalog v0.1）：🔌 单插件 / 🧰 插件集 / 🎓 技能 / 📡 远程渠道 / 🛠 基础设施 / 💬 社区 / 🔬 研究 / ❓ 未分类。
>
> 约定：插件名与 repo 名一致；scope 使用 `@dsh-external/*`（勿占用 `@deepseek-ai/*` 保留命名空间）；repo 打 `dsh-plugin` topic。

## 🔌 单插件

| 插件 | 仓库 | 说明 | 运行级 |
|---|---|---|---|
| dsh-wps | [zhengjy01/dsh-wps](https://github.com/zhengjy01/dsh-wps) | WPS / 金山文档云文档集成（官方 SkillHub MCP，mcp__wps__* 工具） | agent |
| dsh-vercel-mcp | [zhengjy01/dsh-vercel-mcp](https://github.com/zhengjy01/dsh-vercel-mcp) | Vercel MCP connection for DSH: official OAuth 2.0 client flow against mcp.vercel.com; Vercel platform tools under mcp__vercel__* | 待测 |
| dsh-worktree | [alpacachen/dsh-worktree](https://github.com/alpacachen/dsh-worktree) | DSH Web 极简 Git worktree 管理：一个按钮和一个对话框创建任务分支 worktree，并直接打开为 DSH Workspace；npm `@alpacachen/dsh-simple-worktree` 1.0.2 | 待测 |
| dsh-session-pin | [PerryLink/dsh-session-pin](https://github.com/PerryLink/dsh-session-pin) | 会话与工作区置顶（双面 host+client）：行级图钉与换色、会话头开关、已置顶面板、持久化 settings 命名空间；0.4.0 再加会话导航组织器——Pin 分组（boards）、标签与保存视图、会话健康摘要（只读脱敏）与 /goto 模糊跳转；全部浏览器本地零网络 | 待测 |
| dsh-session-explorer | [Zn-Dk/dsh-session-explorer](https://github.com/Zn-Dk/dsh-session-explorer) | 会话消息级全文检索浏览器：FTS5 trigram 按消息检索（用户/助手/系统注入/工具，可按类型筛选），fork/续接会话结果自动去重，只读上下文预览自动滚动定位、一键跳转真实会话，增量/全量重建索引 + 健康检查，中英双语跟随 Host locale | 待测 |
| dsh-agentfuse-plugin | [MkaliezZ/dsh-agentfuse-plugin](https://github.com/MkaliezZ/dsh-agentfuse-plugin) | 确定性 fail-closed 工具调用授权门：allow/block/ask 策略门 + 审批链延后 + agentfuse-evidence-schema 证据；配 dsh-policy-test 闭环回归；已获本雷达运行级 [可用] 判定 | ✅ |
| dsh-evidence-task-board | [MkaliezZ/dsh-evidence-task-board](https://github.com/MkaliezZ/dsh-evidence-task-board) | 持久化确定性任务状态原语（创建/状态/证据转移）；npm 包 @mkaliezz/dsh-task-board | 待测 |
| dsh-test-normalizer | [MkaliezZ/dsh-test-normalizer](https://github.com/MkaliezZ/dsh-test-normalizer) | pytest / Vitest / Jest / Cargo 测试结果归一化为稳定结构；npm 包 @mkaliezz/dsh-test-runner | 待测 |
| dsh-plugin-guard | [lxzy-7/dsh-plugin-guard](https://github.com/lxzy-7/dsh-plugin-guard) | 插件安装安全网：装/卸/开关插件前自动快照备份，启动健康检查失败自动回退最后良好快照并重试一次，设置>备份管理面板 + 双击一键回退脚本，事故报告自动触发 Agent 分析；零运行时依赖，引擎冒烟测试 + 三种安装布局实测通过 | ✅ |
| dsh-office | [Fayelin12/dsh-office](https://github.com/Fayelin12/dsh-office) | 办公室工作区/会话仪表盘：悬浮 6 列精灵面板，可视化工作区、会话、token 用量与子代理，内置 Agent 邮箱、飞书消息、会议日程、妙记逐字稿与办公室日志（web bundle，v0.3.0） | ✅ |
| deepseek-heartflow | [yun520-1/deepseek-heartflow](https://github.com/yun520-1/deepseek-heartflow) | 心虫（AGI 第1层辨别门禁）：47 维纯规则文本判别 heartflow_check 工具 + tools/post-execute 自动输出监督（block 拦截 / rewrite 提醒），引擎缺失 fail-closed；dsh.bundle manifest 可安装 | ✅ |
| dsh-session-tabs | [licat2023/dsh-session-tabs](https://github.com/licat2023/dsh-session-tabs) | 浏览器式会话标签页：顶部标签条从侧边栏右缘开始（不挤占侧边栏），点击切换/关闭/新建、中键关标签与侧边栏后台打开、鼠标侧键会话历史导航、运行状态点；纯客户端零网络零持久化 | 待测 |
| dsh-repo-context | [qing3a/dsh-repo-context](https://github.com/qing3a/dsh-repo-context) | 把 git 状态与仓库规范动态注入 system prompt（section/context/variable，官方 system-prompt 缝隙插件）；dsh-plugin-verify 0.1.2 实测 7/7 waterfall + 工具真实执行（R3 isError:false） | ✅ |
| dsh-event-auditor | [qing3a/dsh-event-auditor](https://github.com/qing3a/dsh-event-auditor) | Harness 事件流审计面板：观察事件类型/分发模式/计数/最近事件，settings 热改 + /audit 会话命令；已用 mock-llm 运行时验证（74 事件/12 waterfall） | ✅ |
| dsh-spend | [nonewind/dsh-spend](https://github.com/nonewind/dsh-spend) | Token 用量统计与预计费用：右下角悬浮窗，按模型/按天/按会话多维聚合，内置供应商知识库自动识别计费计划（web bundle） | ✅ |
| dsh-tokstat | [kongjianguan/dsh-tokstat](https://github.com/kongjianguan/dsh-tokstat) | DSH 使用量与性能统计：设置页「统计」面板（概览/模型/会话/请求，TTFT/TPS/Tokens/成本）+ Python TUI；Node half + client web bundle | ✅ |
| dsh-better-stats | [null5069/dsh-better-stats](https://github.com/null5069/dsh-better-stats) | DSH Web 输入框下方增强统计条：官方人民币计价（峰谷分时、官方价目自动同步）、多模型分账、实时计时、子代理树合并、余额直连、预算预警、流式成本估算；host + client web bundle，npm `dsh-better-stats` | 待测 |
| dsh-tray | [qing3a/dsh-tray](https://github.com/qing3a/dsh-tray) | DeepSeek Harness Windows 系统托盘插件（trayicon exe 宿主，无 native 编译）；菜单/通知/headless 降级，双 profile 已验证 | ✅ |
| dsh-lan-access | [Leon0555/dsh-lan-access](https://github.com/Leon0555/dsh-lan-access) | 局域网访问：Web GUI 绑定 0.0.0.0 + crypto.randomUUID polyfill（修复非安全上下文下 RPC 崩溃），npm 可装 | ✅ |
| dsh-full-remote | [JUANWANG-BUAA/dsh-full-remote](https://github.com/JUANWANG-BUAA/dsh-full-remote) | 令牌反向代理：改写 Host/Origin，远程恢复 `settings.*`/`credentials.*`/`host.listDirectory`（通用隧道会 403）；一次性扫码邀请、按设备会话；npm `dsh-full-remote` | ✅ |
| dsh-bash-terminal | [MAXeaglet/dsh-bash-terminal](https://github.com/MAXeaglet/dsh-bash-terminal) | Windows 三终端 shell 工具（PowerShell/Git Bash/WSL，默认终端由用户在设置中选择）+ 交互式 PTY 终端 + 官方沙箱对接；4 套件测试 + GitHub Actions CI 全绿 | ✅ |
| dsh-win32 | [sjh9714/dsh-win32](https://github.com/sjh9714/dsh-win32) | 在 Windows 上把 DSH 用起来：一行装好极简模式的持久 shell（Git Bash/ConPTY，沙箱内可用），npm 可装 | ✅ |
| dsh-artifact | [dsh-external/dsh-artifact](https://github.com/dsh-external/dsh-artifact) | 制品管理 | ✅ |
| dsh-condense | [JxaMe/dsh-condense](https://github.com/JxaMe/dsh-condense) | token 优化插件：屏蔽低信号读取、压缩大输出、哈希去重、smart_read 骨架化（tree-sitter）、BM25 检索、真实用量统计+持久化；npm `@jxame/dsh-condense` | ✅ |
| dsh-split-panes | [dsh-external/dsh-split-panes](https://github.com/dsh-external/dsh-split-panes) | 分屏面板 | ✅ |
| dsh-sentinel | [fuhefei/dsh-sentinel](https://github.com/fuhefei/dsh-sentinel) | 事件驱动唤醒 agent loop（文件/命令/http/进程/webhook 传感器） | ✅ |
| dsh-plugin-automations | [Sev7een/dsh-plugin-automations](https://github.com/Sev7een/dsh-plugin-automations) | Web 设置页定时任务：支持准点或 DeepSeek 谷时段执行、单次/每日重复，并持久化任务状态 | 待测 |
| dsh-tianshu-tui | [huiliyi37/dsh-tianshu-tui](https://github.com/huiliyi37/dsh-tianshu-tui) | DSH 的 TUI（终端界面） | ✅ |
| dsh-genui | [omdsh-dev/dsh-genui](https://github.com/omdsh-dev/dsh-genui) | GenUI 内联交互组件：dsh-ui fence 渲染图表/表单/测验/3D 场景，带 action 事件环 | ✅ |
| dsh-annotation | [omdsh-dev/dsh-annotation](https://github.com/omdsh-dev/dsh-annotation) | DSH Web 选中批注插件：选文字→批注→回车随消息发送，回复按 Annotation N 逐条对照（可悬浮芯片） | ✅ |
| dsh-ui-quote-selection | [nekogpt/dsh-ui-quote-selection](https://github.com/nekogpt/dsh-ui-quote-selection) | 在 DSH Web 中选中文字，一键引用到输入框；发送问题时自动附上完整原文 | ✅ |
| CiteCiter | [kirkchinese/CiteCiter](https://github.com/kirkchinese/CiteCiter) | 在 DSH Web 中选中已完成的助手回复，右键 `Citer!` 后从真实会话边界创建只读子会话，并在 details 侧栏流式解释；不写入父会话日志，支持 Markdown、代码、KaTeX、安全 SVG 与无网络 HTML 预览；npm `@kirkchinese/dsh-citeciter` 0.1.1，17 项测试及真实 registry 安装、浏览器 smoke 均通过 | 待测 |
| dsh-security-scan | [ben7am1n/dsh-security-scan](https://github.com/ben7am1n/dsh-security-scan) | Secret & dangerous-pattern scanner — API keys/tokens/private keys redacted; ignore lists; zero deps | ✅ |
| cordis-plugin-sofagent-audit | [KongFangXun/sofagent](https://github.com/KongFangXun/sofagent) | 变更机器审阅 harness：24 条 git diff 规则（密钥泄漏/越界改动/提示注入）+ HMAC 链审计记录 + 快照回滚 + MCP server（83 tools），git hook 即装（引擎内 engine/dsh-plugins/cordis-plugin-sofagent-audit 子包） | 待测 |
| dsh-email | [STARDUSTLC666/dsh-email](https://github.com/STARDUSTLC666/dsh-email) | 邮件工具插件：IMAP/SMTP 收/发/搜/列文件夹/附件下载（email_list/read/search/send/folders/attachment/health），since/until 时间范围过滤，内置 QQ/163/126/新浪/阿里/Gmail/Outlook/iCloud 预设，多账号与连接复用，发信默认走审批门；纯 Node 全平台 | ✅ |
| dsh-calendar | [STARDUSTLC666/dsh-calendar](https://github.com/STARDUSTLC666/dsh-calendar) | CalDAV 日历插件：查/建/改/删/搜日程 + calendar_health 自检（calendar_list/create/update/delete/search/health），Google/iCloud/Nextcloud/自定义端点，应用专用密码 | ✅ |
| dsh-dingtalk | [STARDUSTLC666/dsh-dingtalk](https://github.com/STARDUSTLC666/dsh-dingtalk) | 钉钉群机器人通知（dingtalk_notify/dingtalk_text/dingtalk_health），自定义机器人 webhook+加签，自检只查配置不发消息，零运行时依赖 | ✅ |
| dsh-slack | [STARDUSTLC666/dsh-slack](https://github.com/STARDUSTLC666/dsh-slack) | Slack 通知插件（slack_notify/channels/inbox/reply/health），Bot Token + 官方 Web API，Socket Mode 收件箱，健康自检汇总 token/appToken/默认频道 | ✅ |
| dsh-ffmpeg | [STARDUSTLC666/dsh-ffmpeg](https://github.com/STARDUSTLC666/dsh-ffmpeg) | 视频处理插件：ffmpeg_probe/cut/concat/encode/subtitle/extract/gif/frames/health 九工具（探测摘要/剪辑/拼接/转码/字幕烧录/抽帧/批量抽帧/GIF/自检），走官方 subprocess 服务、argv 数组无 shell 注入、零运行时依赖 | ✅ |
| dsh-docker | [STARDUSTLC666/dsh-docker](https://github.com/STARDUSTLC666/dsh-docker) | 容器管理插件：docker_ps/logs/inspect/exec/manage/health 六工具，官方 subprocess 服务、argv 无 shell 注入、exec 审批门、守护进程自检、零运行时依赖；npm 包为 scoped 名 @stardustlc/dsh-docker | ✅ |
| dsh-rss | [STARDUSTLC666/dsh-rss](https://github.com/STARDUSTLC666/dsh-rss) | RSS/Atom 订阅工具：九工具（含跨订阅搜索 rss_search、增量抓取、OPML 导入导出、自检），代理支持，纯 Node 全平台 | ✅ |
| dsh-cite | [STARDUSTLC666/dsh-cite](https://github.com/STARDUSTLC666/dsh-cite) | 参考文献：cite_lookup/format/bibtex/check/health，Crossref 查询与连通性自检，GB/T 7714 / APA / MLA / Chicago 与 BibTeX | ✅ |
| dsh-code-security | [STARDUSTLC666/dsh-code-security](https://github.com/STARDUSTLC666/dsh-code-security) | AI 代码安全审查：secure_scan/diff/fix_verify/report/export/baseline/deps/policy_*/health，40+ 确定性规则、密钥熵检测、SARIF 导出、基线接受与 SBOM-lite | ✅ |
| dsh-flakefinder | [STARDUSTLC666/dsh-flakefinder](https://github.com/STARDUSTLC666/dsh-flakefinder) | 测试稳定性：flaky_detect/history/quarantine/clear/report/health，重复运行识别 flaky 用例，隔离清单与历史，自检 python/pytest，零运行时依赖 | ✅ |
| dsh-turn-index | [Simon314620/dsh-turn-index](https://github.com/Simon314620/dsh-turn-index) | 对话轮次索引侧边栏：每轮提问一目了然，点击跳转 + 滚动联动高亮，双语纯客户端 | ✅ |
| dsh-outline | [urzeye/dsh-outline](https://github.com/urzeye/dsh-outline) | DSH Web 会话页实时大纲面板：「用户问题 + Markdown 标题（1~6 级）」大纲树，流式生成实时更新，点击节点定位高亮，支持展开层级调节、搜索与会话级收藏 | ✅ |
| dsh-sticky-note | [Meredith2328/dsh-sticky-note](https://github.com/Meredith2328/dsh-sticky-note) | 输入框工具栏快速便签：点子/感想/TODO，Markdown 预览、自动保存、一键发送、保留与自动清除 | ✅ |
| dsh-sidebar-mode | [Meredith2328/dsh-sidebar-mode](https://github.com/Meredith2328/dsh-sidebar-mode) | 侧边栏「新会话」按钮内嵌 Agent 预设快速切换：点击弹出预设菜单即点即用，与设置里的「Agent 预设」双向同步 | 待测 |
| dsh-oauth-mcp-client | [springbrand-lab/dsh-oauth-mcp-client](https://github.com/springbrand-lab/dsh-oauth-mcp-client) | 为 DSH 连接支持 OAuth 2.1 的 Streamable HTTP MCP 服务 | 待测 |
| dsh-balance | [TwotwoPiggy/dsh-balance](https://github.com/TwotwoPiggy/dsh-balance) | 在 DSH Web 聊天框底部实时估算对话 Token 消耗并显示您的 DeepSeek 账户余额 | ✅ |
| ds-api-usage | [Sev7een/ds-api-usage](https://github.com/Sev7een/ds-api-usage) | 在设置页展示 DeepSeek API 余额与最近 24 小时用量，包括估算消费、Token、请求次数和按小时时间线 | ✅ |
| falsify-dsh | [shi275773124/falsify-dsh](https://github.com/shi275773124/falsify-dsh) | 公开 Falsify CLI 适配器：裁决收据（lint / review --json / gate）。不是第二意见工作流；selftest ≠ claim-bearing | ✅ |
| billion-context-dsh | [Tyan66666/billion-context-dsh](https://github.com/Tyan66666/billion-context-dsh) | 模型驱动上下文压缩（ACP）：compress/decompress/search_context/acp_status 工具，模型决定何时压缩，移植自 billion-context-pi | ✅ |
| dsh-web-search-firecrawl | [yangzhe1003/dsh-web-search-firecrawl](https://github.com/yangzhe1003/dsh-web-search-firecrawl) | Firecrawl 搜索提供方：内置 web_search 工具接入 Firecrawl 搜索 API（npm @yangzhe1003/dsh-web-search-firecrawl） | ❌ |
| dsh-test-runner | [suimi8/dsh-test-runner](https://github.com/suimi8/dsh-test-runner) | 结构化测试运行工具 test_run：自动探测 vitest/jest/pytest/node:test，执行并解析失败摘要，避免模型阅读整段原始测试输出 | 待测 |
| dsh-agent-message | [GengDaPeng/dsh-agent-message](https://github.com/GengDaPeng/dsh-agent-message) | 跨会话 Agent 通信：让运行在同一 DeepSeek Harness 进程里的不同 Agent 会话互相收发消息 | 待测 |
| dsh-plugin-audit | [jkrandom-sudo/dsh-plugin-audit](https://github.com/jkrandom-sudo/dsh-plugin-audit) | 插件安全审计器：plugin_audit 静态权限画像（能力/凭证路径/外发主机，文件行号实证，只读契约）+ tools/pre-execute 运行时哨兵（凭证访问/非白名单外发/dotfile 写入 → 审批）；23 单测 + headless/web 真实 profile 双验证 | ✅ |
| dsh-claude-move | [PerryLink/dsh-claude-move](https://github.com/PerryLink/dsh-claude-move) | 从 Claude Code 全保真复制历史会话/记忆/技能/CLAUDE.md 到 DSH：全部导入会话归入独立 claudecode 工作区（workspaceMode 可切回按项目分组），复制式增量同步，中断工具调用自动修复（issue#1），Web 面板 + /claude-import-all + /resume-claude | ✅ |
| dsh-chat-import | [Nwflower/dsh-chat-import](https://github.com/Nwflower/dsh-chat-import) | 13 源全保真导入（Claude Code/Codex/ChatGPT/Cursor/Gemini/Reasonix/opencode/ZCode/Grok Build/OpenClaw/Pi/Hermes/Kimi）→ 可续聊 DSH 会话，反向 export_claude/sync_to_claude 写回 Claude Code；增量续写/幂等/上下文预算/Web 面板，npm dsh-chat-import | ✅ |
| claude2dsh | [kirkchinese/claude2dsh](https://github.com/kirkchinese/claude2dsh) | 将 Claude Code 会话、技能、记忆与插件资产导入为 DSH 原生可续聊会话，并支持导出/同步回 Claude Code JSONL；双向冲突检测 + 显式三路合并；Settings 配置页 | 待测 |
| dsh-session-pins | [alooshxl/dsh-session-pins](https://github.com/alooshxl/dsh-session-pins) | 在侧边栏持久置顶并快速打开可用普通会话；rc.6 归档项可识别、可移除但不可重新打开（无凭据运行级实测） | ✅ |
| dsh-cost-ledger | [suimi8/dsh-cost-ledger](https://github.com/suimi8/dsh-cost-ledger) | 跨会话持久成本账本：订阅 llm/stream 自动记录每次模型调用的 token 用量到 SQLite，内置 DeepSeek 官方 CNY 定价（可热改），提供 record_cost/query_cost/set_budget 三个 agent 工具 + /api/cost-ledger/* HTTP API 供 WebUI 仪表盘 | ✅ |
| dsh-mdbox | [Chi-hong22/dsh-mdbox](https://github.com/Chi-hong22/dsh-mdbox) | DSH Web 输入框 Markdown 编辑辅助：Shift+Enter 列表续行与空项退出、有序列表自动重编号、Tab/Shift+Tab 双向缩进；纯客户端零运行时依赖，不碰文件/网络/凭据 | 待测 |
| vpshub | [Sdongmaker/vpshub](https://github.com/Sdongmaker/vpshub) | DSH 的 VPS Hub:本地 SSH 台账(Orca 风格 ssh-config/manual + tombstone),8 个 vps_* 工具让 AI 发现/测试/执行/传输,密钥仅路径引用;ProxyJump/ProxyCommand、Windows 密钥认证、i18n 设置页 UI;npm 包 dsh-vps-hub(v0.1.8) | ✅ |
| dsh-latexcp | [Chi-hong22/dsh-latexcp](https://github.com/Chi-hong22/dsh-latexcp) | DSH Web 界面 LaTeX 公式复制插件：悬停 KaTeX 公式复制按钮，一键复制 TeX 源码（$…$ / \(…\) 两种格式 | 待测 |
| dsh-plugin-web-access | [junhongchashui/dsh-plugin-web-access](https://github.com/junhongchashui/dsh-plugin-web-access) | 纯本地按需网页访问：web_fetch 命令行抓取 + 无头浏览器（browser_open/snapshot/eval/screenshot）双通道，零 API Key，注册 ctx.web fetch provider | ✅ |
| dsh-web-access | [NexusAgentX/dsh-web-access](https://github.com/NexusAgentX/dsh-web-access) | 多提供方联网：web_search / fetch_content / source_check，注册 ctx.web 的 web-access 搜索/抓取提供方，Web 面板改配置与策展；npm `dsh-web-access` | ✅ |
| dsh-llm-fallback | [Visol-456/dsh-llm-fallback](https://github.com/Visol-456/dsh-llm-fallback) | LLM 回退链插件：请求本身永远是链头（聊天栏所选模型永不被改写），失败自动按备用顺序切换重试；Web UI 配置面板（provider/model 下拉选择、错误码、阈值、冷却，保存热生效）；dsh.bundle 一键激活；69 单测全绿 + Windows 实测 | ✅ |
| dsh-lens | [NexusAgentX/dsh-lens](https://github.com/NexusAgentX/dsh-lens) | 写/改文件时的实时代码反馈：LSP / linter / formatter / ast-grep / symbol_search，Web chip+dock；npm `dsh-lens` | ✅ |
| dsh-mnemon | [omdsh-dev/dsh-mnemon](https://github.com/omdsh-dev/dsh-mnemon) | Mnemon 深度集成的本地记忆系统：运行时热记忆 / 项目档案 / 长期记忆体三层存储，受监督写回、检索工具与 8 页 Web UI | ✅ |
| dsh-daily-brief | [Equinox7379/dsh-daily-brief](https://github.com/Equinox7379/dsh-daily-brief) | 回合日报：跨 live 会话统计回合/用户消息/助手回复/工具调用（daily_brief 工具，只读零依赖） | ✅ |
| dsh-config-watch | [Equinox7379/dsh-config-watch](https://github.com/Equinox7379/dsh-config-watch) | 配置漂移侦探：启动时快照 profile/插件清单并记录变更历史（config_changes 工具） | ❌ |
| dsh-turn-watchdog | [Equinox7379/dsh-turn-watchdog](https://github.com/Equinox7379/dsh-turn-watchdog) | 回合守夜人：检测疑似卡住的会话并注入警示（turn_watchdog_status 工具） | ✅ |
| dsh-session-repair | [Equinox7379/dsh-session-repair](https://github.com/Equinox7379/dsh-session-repair) | 会话日志修复：给未知事件类型补 ignorable 并按合规帧格式重写，修复 SessionFormatUnsupportedError（修复前自动备份） | 待测 |
| dsh-update-radar | [Equinox7379/dsh-update-radar](https://github.com/Equinox7379/dsh-update-radar) | 已装插件更新雷达：git 对比 link 插件本地与上游 HEAD，报告落后项（只读） | ✅ |
| dsh-skill-search | [Equinox7379/dsh-skill-search](https://github.com/Equinox7379/dsh-skill-search) | 按需技能搜索器：海量技能库零预加载，关键词搜索 SKILL.md（rg 快路径 + Node 兜底），AI 只读命中的那份 | ✅ |
| dsh-visual-plugin | [jyh20030112/dsh-visual-plugin](https://github.com/jyh20030112/dsh-visual-plugin) | DSH 视觉桥接插件：主模型无视觉时把用户图片转发到任意 OpenAI 兼容视觉模型（DeepSeek (Vision) 包装适配器 + Web 右侧面板配置/测试/历史），自动拦截描述并支持按问题定向提示词 | ✅ |
| dsh-vision-proxy | [Flyvhidbwo/dsh-vision-proxy](https://github.com/Flyvhidbwo/dsh-vision-proxy) | DeepSeek 大脑 + 自动识图：GUI 附加图片默认经官方 deepseek-v4-flash-vision-exp 原生识图转译（纯文本 V4-Pro 也能看图）；支持任意 OpenAI 兼容 VLM 与本地 Ollama | ✅ |
| DSH-Plugins-Marketplace | [bradeGithub/DSH-Plugins-Marketplace](https://github.com/bradeGithub/DSH-Plugins-Marketplace) | DSH 插件市场：聚合 GitHub `dsh-plugin` 话题插件，Web GUI 一键安装/更新/已安装识别（含预装插件自动比对），静态索引 CI 每 2 小时刷新，中英双语 | ✅ |
| dsh-doublecheck | [PerryLink/dsh-doublecheck](https://github.com/PerryLink/dsh-doublecheck) | 工程纪律插件：交付前三查——需求审讯（grill-requirements 技能）+ 红绿测试证据门 + 对抗评审 + 交付报告与逐维度核对（verify 工作流）；/doublecheck 会话命令、en/zh 双语、npm 已发布 0.6.0 | 待测 |
| dsh-git-plugin | [IT-coder-Yy/dsh-git-plugin](https://github.com/IT-coder-Yy/dsh-git-plugin) | 面向 DSH Web 的可视化 Git 工作台：查看仓库状态、Diff、分支、提交历史与贮藏，点击执行常用 Git 操作，并安全运行 AI 生成的分步骤 Git 提议；npm `dsh-easygit-plugin` 0.2.1，DSH 0.1.0-rc.6 实测 | 待测 |

| dsh-mcp-adapter | [NexusAgentX/dsh-mcp-adapter](https://github.com/NexusAgentX/dsh-mcp-adapter) | 一个 mcp 代理工具：按需 search/describe/call，不把每个 MCP schema 塞进上下文；Web `/mcp` 菜单可添加/连接/授权 | ✅ |
| dsh-mcp-skill-panel | [lilyblessing/dsh-mcp-skill-panel](https://github.com/lilyblessing/dsh-mcp-skill-panel) | MCP 与技能管理面板：MCP 服务器/Skill 实时启停释放上下文（停用态回填目录工具数）；可选 AI 中间层（mcp_search/mcp_call）按 server 状态过滤可见性、保活启用 + 空闲 30s 回收 | ✅ |
| logicprobe | [AmethystLuna/logicprobe](https://github.com/AmethystLuna/logicprobe) | 设计文档与重构计划声明核查：claim 枚举 + 代码库事实核对 + 状态机/数据模型逻辑原语验证，支持前后回归、幂等/单调/顺序/必达/原子性约束与并发风险挖掘，dsh 原生 bundle 注入核查纪律门 | ✅ |
| embedded-workbench | [AmethystLuna/embedded-workbench](https://github.com/AmethystLuna/embedded-workbench) | 嵌入式 C/C++ 固件工程插件：8 skills（FreeRTOS/Keil/ARMCLANG/HardFault/状态机/LVGL/架构），dsh 原生 bundle 注入会话启动纪律门（1% Rule / Red Flags / Plan Verification Gate） | ✅ |
| dsh-ci-doctor | [jkrandom-sudo/dsh-ci-doctor](https://github.com/jkrandom-sudo/dsh-ci-doctor) | CI 失败自动诊断：ci_watch 后台监视新增失败运行（基线对比/退避/可取消）+ ci_diagnose 日志签名提取分类（嫌疑文件/裁剪摘录/markdown 诊断卡）+ 失败签名账本去重复发；102 单测 + web profile 进程内 boot 19 项 + headless 真实模型回路实测（v0.1.2 审查修复版） | ✅ |

| dsh-hdc-bridge | [1na-ko/dsh-hdc-bridge](https://github.com/1na-ko/dsh-hdc-bridge) | 鸿蒙设备桥：hdc 设备闭环（截图/装包/日志/崩溃/UI 自动化）+ 官方优先 API 知识层（SDK .d.ts + 离线 Tier-1 随包）+ DevEco CLI 构建/签名/lint；无头 DSH 实例真实 E2E 已验证 | ✅ |
| deepseek-skin-studio | [JueMing2049/deepseek-skin-studio](https://github.com/JueMing2049/deepseek-skin-studio) | DSH 换肤工作室：一张图一套皮肤，三通道注入（书签/CDP/原生插件）+ 可视化工坊 + 13 套内置主题 + DSH-SKIN-SPEC 导出 | 待测 |
| dsh-agent-preset-recommender | [LeemanCheung/dsh-agent-preset-recommender](https://github.com/LeemanCheung/dsh-agent-preset-recommender) | 有界、隐私安全的本地扫描器：汇总 Codex、Claude Code、WorkBuddy、CodeBuddy 元数据，原子保存密钥化聚合证据，并确定性推荐 DSH 内置 preset 与可选能力；不保留正文、不联网、不修改 preset | 待测 |
| dsh-side-chat | [heartmove/dsh-side-chat](https://github.com/heartmove/dsh-side-chat) | DSH Web 侧边聊天：选中对话片段在右侧面板的侧边聊天提问（按会话隔离，继承主会话模型/思考难度/权限），AI 回复可原文或摘要带回主会话，问题弹框选项可一键带入 | 待测 |
| dsh-subagent-max | [aaravarr/dsh-subagent-max](https://github.com/aaravarr/dsh-subagent-max) | 子代理委派按次指定模型/提供商（host 侧 `subagent_with_model` 工具）+ 多面板实时流式子代理查看器（client 侧浮动面板 token 级流式输出、卡片网格、拖拽弹出、中英 i18n）；rc.6 headless 实测通过 | ✅ |
| dsh-permission-rules | [PerryLink/dsh-permission-rules](https://github.com/PerryLink/dsh-permission-rules) | Claude Code 风格声明式权限规则：按序 allow/deny/ask YAML 规则，在 tools/pre-execute 瀑布上匹配工具名/参数/工作区路径/agent 身份，带会话日志审计、干跑模式与热重载；npm 已发布 | 待测 |
| dsh-approve-for-me | [timeance/dsh-approve-for-me](https://github.com/timeance/dsh-approve-for-me) | DeepSeek Harness 沙箱扩权审批：Shell/PowerShell 字面命令前缀规则、固定高风险检查、可选无工具 LLM reviewer；成功仅授予一次 `allowed-once`，高危或不确定请求回原生人工审批，支持 Web/headless Profile | 待测 |
| dsh-plugin-marketplace | [Scorp1o117/dsh-plugin-marketplace](https://github.com/Scorp1o117/dsh-plugin-marketplace) | Web UI 内置插件市场：设置页直接浏览 github.com/topics/dsh-plugin，搜索/按 Star 排序/README 摘要；settings 通道一键安装并自动挂载 cordis.patch.yml；AI 解释；npm 已发布 | 待测 |
| dsh-soul-md | [Scorp1o117/dsh-soul-md](https://github.com/Scorp1o117/dsh-soul-md) | soul.md 风格人设 + 长期记忆：设置页输入人设卡名称和内容即可，文件由插件自动管理；按工作区指定人设、聊天框可给会话单独切人设；AI 可自行演化人设与记忆（soul_read/soul_update/memory_*）；npm 已发布 | 待测 |
| dsh-tdai-memory | [Scorp1o117/dsh-tdai-memory](https://github.com/Scorp1o117/dsh-tdai-memory) | TencentDB Agent Memory 的 DSH 移植：L0 对话捕获 → L1 结构化记忆提取 → L2 场景/L3 画像，自动召回注入 + 记忆/对话搜索工具；复用现有 ~/.memory-tencentdb 数据；附 Web UI 设置栏 | 待测 |
| dsh-tool-vision | [Scorp1o117/dsh-tool-vision](https://github.com/Scorp1o117/dsh-tool-vision) | 外置视觉模型插件：inspect_image 把本地图片或 http(s) 图片 URL 发给任意 OpenAI 兼容端点，视觉模型看图的文字回答直接带回对话；附 Web UI 设置栏 | ✅ |
| dsh-compressor | [lifeodyssey/dsh-compressor](https://github.com/lifeodyssey/dsh-compressor) | [Headroom](https://github.com/headroomlabs-ai/headroom) 的精简移植，在不影响模型上下文缓存以及 Agent 性能的情况下，压缩工具的输出，至多减少 20% 的上下文。 | 待测 |
| dsh-anchored-subagent | [GY-Bai/dsh-anchored-subagent](https://github.com/GY-Bai/dsh-anchored-subagent) | 让 DSH 主 agent 和子代理别一开口就 `Let me...`：首轮用 Minimal 开局进入满血状态，第二轮恢复全部工具；自定义子代理角色首轮先收起来，第二轮再放出来 | ✅ |
| dsh-smooth-stream | [Laplace-bit/dsh-smooth-stream](https://github.com/Laplace-bit/dsh-smooth-stream) | DSH Web 界面丝滑流式渲染：打字机跟随 token 到达、Markdown 边流边渲染、换行滑入、不闪烁，滚动归用户，尊重 prefers-reduced-motion | 待测 |

| dsh-background-agents | [PerryLink/dsh-background-agents](https://github.com/PerryLink/dsh-background-agents) | 交互式长会话后台 agent：官方 subagent 接缝上的可持久/可继续子 agent，Web UI 侧边栏实时进度、随时消息/打断、autoReport 进度注入、空闲归档；npm 0.5.0 已发布 | 待测 |
| dsh-talk | [PerryLink/dsh-talk](https://github.com/PerryLink/dsh-talk) | 语音优先会话闭环：作曲器麦克风按钮 + 浏览器/本地语音转写（Web Speech、FunASR、whisper.cpp），speak 工具朗读回复（browser、edge-tts、piper），事件播报带静音开关，说话打断 | 待测 |
| dsh-vision-tools | [moon09300731/dsh-vision-tools](https://github.com/moon09300731/dsh-vision-tools) | 视觉能力全家桶：vision_understand 工具（OpenAI 兼容视觉 API，默认免费智谱 GLM-4V-Flash）+ 粘贴/拖拽/按钮三入口识图 | 待测 |
| dsh-approval-gate | [moon09300731/dsh-approval-gate](https://github.com/moon09300731/dsh-approval-gate) | 自动审批门控：Flash 预判写入/命令是否不可回补，安全操作自动批准、危险操作转人工（fail-safe） | 待测 |
| dsh-routing-suite | [yjh051108/dsh-routing-suite](https://github.com/yjh051108/dsh-routing-suite) | 注入器 × 思维模式路由套装（3300+★ 正主仓，勿与同名仿品混）：免重启运行时注入器 + 任务感知推理模式路由预设（P1-P23 实测）；injector 子目录 `dsh plugin add` 安装 | 待测（registry 插队实测） |
| Bigfish | [turtle2209/Bigfish](https://github.com/turtle2209/Bigfish) | DeepSeek Harness 第三方桌面端：内置 Node 运行时双击即用（Top50 精选成员，registry 插队实测） | 待测（registry 插队实测） |
| dsh-open-file | [Hyp6666/dsh-open-file](https://github.com/Hyp6666/dsh-open-file) | DSH Web 工作区文件附件插件：多文件选择与全页拖放，读取文本、PDF、DOCX、PPTX、XLSX、ZIP 和图片，提供英中 OCR、页面渲染及 `file_inspect` / `file_read` / `file_ocr` / `file_render` 四个可追溯工具；npm `dsh-open-file` 0.1.1 | 待测 |
| dsh-agent-team-gui | [toolclub/dsh-agent-team-gui](https://github.com/toolclub/dsh-agent-team-gui) | 持久化多模型 Agent 小队：主 Agent 按成员特性动态编排有界 DAG，成员独立配置模型与工具策略；在 Settings/Composer 管理和选择小队，Run Center 支持追踪、重试与取消，并提供逐 Agent Token 成本洞察；v0.5.0 通过 117 Host + 62 Client 测试及 DSH rc.6 全新 Web profile 安装/浏览器冒烟 | 待测 |
| dsh-agent-team | [wowyuarm/dsh-agent-team](https://github.com/wowyuarm/dsh-agent-team) | 帮 human 有序管理任务、把 agents 用成真正的协作者：Workspace/Channel/Thread/Task 与受管 Agent 成员，append-only operation ledger 为唯一权威；Web Client Team mode 进入/刷新恢复/退出，普通 Session 不获得 Team tools；隔离 team-member preset 五工具（inbox/thread/message/claim/view）；npm @wowyuarm/dsh-agent-team 0.1.0，已认证 DSH 0.1.1-rc.2 | 待测 |
| dsh-ssh | [dmz2922990/dsh-ssh](https://github.com/dmz2922990/dsh-ssh) | SSH 主机管理 + 远程执行：ssh_host_list/add/update/remove/ssh_bash 五工具，主机台账持久化到 ~/.dsh/ssh-hosts.json，支持 agent/key/password 三种认证（password 走 SSH_ASKPASS，沙箱可用）；提供 Agent 预设与 Cordis 插件两种形态 | 待测 |
| dsh-mcp-list | [dmz2922990/dsh-mcp-list](https://github.com/dmz2922990/dsh-mcp-list) | 设置面板新增 MCP 页：按服务器分组列出全部已挂载 MCP 服务器与工具，扫描最近会话统计各工具调用次数，一键在系统编辑器打开 cordis.patch.yml 的 MCP 配置 | 待测 |
| dsh-thinkmeter | [dmz2922990/dsh-thinkmeter](https://github.com/dmz2922990/dsh-thinkmeter) | Think 思考行 Token 计量表：把聊天视图流式 Think 预览替换为实时 token 数显示（Thinking ≈ N tokens），落定时精确取 usage.reasoningTokens、缺失时启发式估算，点击可展开/收起完整思考文本（web client 插件，dsh.bundle 一键安装） | 待测 |
| dsh-mmx-bridge | [welsione/dsh-mmx-bridge](https://github.com/welsione/dsh-mmx-bridge) | MiniMax 多模态桥接插件：一个 mmx_bridge 工具覆盖图像理解（VLM）/文生图/文图生视频/语音合成/音乐生成/音频翻唱/联网搜索/用量查询，生成产物经 /mmx-files/ 同源内嵌图片预览与音视频播放器，附 Web 设置页管理卡片；零 npm 运行时依赖 | 待测 |
| dsh-model-router | [welsione/dsh-model-router](https://github.com/welsione/dsh-model-router) | 统一模型路由插件：一个逻辑 ModelID 汇聚多家供应商，首 token 前失败自动切换并冷却、健康度择优、按 purpose 三档分级（tier1/2/3）、每候选思考级别（reasoningEffort），设置面板自动保存即时生效；npm `@welsione/dsh-model-router` | 待测 |
| dsh-trading-toolkit | [kentleenot/dsh-trading-toolkit](https://github.com/kentleenot/dsh-trading-toolkit) | A股+美股行情工具箱：实时行情/OHLCV K线/ADX 三状态信号/回测预览，东方财富免 Key 直连，只读永不下单 | ? |
| dsh-univer-office | [dream-num/dsh-univer-office](https://github.com/dream-num/dsh-univer-office) | 为 DeepSeek Harness 打造一个真正的办公环境。Univer Office 插件将电子表格、文档、幻灯片、画布、多维表格等汇聚到同一个运行时——数据互联、修改经过校验、变更按版本管理，并以隔离工作树支持多 Agent 协作。 | 待测 |
| dsh-prompt-optimizer | [Y1X1n/dsh-prompt-optimizer](https://github.com/Y1X1n/dsh-prompt-optimizer) | 发送栏「优化」按钮一键分析并改写提示词草稿，SSE 流式逐段上屏；上下文感知双策略（无上下文按结构模板改写，有上下文先提炼目的再润色，已否决方向不重提），轻量记忆链延续多轮修改、发送即归零；斜杠命令前缀保留；dock 面板可替换/撤回/复制/重试，发送后自动关闭，实时显示阶段与用时；模型跟随会话（可固定 + 回退路由 failover），设置折叠卡含快速模式、推理钳档、Token 上限自适应、携带上下文等开关；55 例自动化测试 + GitHub Actions CI，rc.7 真实 profile 端到端实测 | 待测 |
| dsh-experts | [fuchao2pku/dsh-experts](https://github.com/fuchao2pku/dsh-experts) | DSH 设置页内置「专家市场」：浏览/搜索社区专家与专家团、查看详情并复制到输入框；默认消费 awesome-dsh-experts 目录（7 个种子专家/团），rc.6 web profile 实测 0 加载错误、27 测试全绿 | ✅ |
| dsh-desk-pet | [anneheartrecord/dsh-desk-pet](https://github.com/anneheartrecord/dsh-desk-pet) | macOS 桌宠：真的 AppKit 置顶窗口而不是页面里的挂件，全屏 Space 也盖得住；六种状态跟着本地 DSH 走（空闲／干活／等你确认／报错／刚跑完／打盹），原生右键菜单含免打扰与会话清单；自带的 skill 用你自己的画图工具和额度把一张照片扩成整套十八个姿势的皮肤，装在包外，升级不会删。跑系统自带的 Python 与 ctypes，零运行时依赖，不用 Electron。**仅 macOS** | 待测 |
| dsh-research-report | [PerryLink/dsh-research-report](https://github.com/PerryLink/dsh-research-report) | 证据账本与可验证报告引擎：内容寻址的声明-快照绑定与逐字节核查，产出带逐条判定与 SHA-256 清单封存的版本化报告；npm 0.1.0 已发布 | 待测 |
| dsh-socrates | [Cruciforms/dsh-socrates](https://github.com/Cruciforms/dsh-socrates) | 苏格拉底式澄清优先的深度研究插件：自适应多轮研究、交叉验证（声明级三分裁决+单跳回补）、程序化引用审计、学术三源（arXiv/PubMed/S2）、模型分层降本（Pro/Flash） | 待测 |
| dsh-plugin-hub | [Noob-stupid/dsh-plugin-hub](https://github.com/Noob-stupid/dsh-plugin-hub) | DSH 插件管理面板：一键启停 + 多源市场（GitHub/Gitee/自定义）+ 静态索引市场（500+ 插件/300 技能）+ 技能安装/停用 + 套装一键装配 + 框架升级适配 | 待测 |
| dsh-simple-wiki-memory | [rainow/dsh-simple-wiki-memory](https://github.com/rainow/dsh-simple-wiki-memory) | 简易 Wiki 持久记忆（DSWM）：一个索引文档自动注入 + 每主题一个 md 文件按需读取，省 token 轻量无压力；pending 准入→确认晋升→archive 归档三区 + memory-log 审计 + git 自动备份；纯 Markdown 所见即所得，跨 harness 共享 | 待测 |
| open-design | [nexu-io/open-design](https://github.com/nexu-io/open-design) | DSH 设计插件：开源 Claude Design 替代（Top50 精选成员，registry 插队实测） | 待测（registry 插队实测） |
| ouroboros | [Q00/ouroboros](https://github.com/Q00/ouroboros) | Agent OS：agent 自我变强、人只守底线（Top50 Booster 成员，registry 插队实测） | 待测（registry 插队实测） |
| dsh-anchored-standard | [xiaobright/dsh-anchored-standard](https://github.com/xiaobright/dsh-anchored-standard) | 两阶段 DSH 预设：极简模式对齐启动 → 全量装载（Top50 Booster 成员，registry 插队实测） | 待测（registry 插队实测） |
| EverOS | [EverMind-AI/EverOS](https://github.com/EverMind-AI/EverOS) | 全 agent 便携记忆层：本地优先 Markdown-native（Top50 成员，registry 插队实测） | 待测（registry 插队实测） |
| openpencil | [ZSeven-W/openpencil](https://github.com/ZSeven-W/openpencil) | OpenPencil 设计工具本体（DSH 适配器 dsh-openpencil 已另有条目；本体插队实测） | 待测（registry 插队实测） |
| EchoBird | [edison7009/EchoBird](https://github.com/edison7009/EchoBird) | 多引擎一键安装与模型切换（Top50 成员，registry 插队实测） | 待测（registry 插队实测） |
| Aegis | [GanyuanRan/Aegis](https://github.com/GanyuanRan/Aegis) | 软件工程方法论技能包：baseline-first 规划、系统性重构等技能（对方清单 1089★，rc.8 实测 ✅） | ✅ |
| api-relay-audit | [toby-bridges/api-relay-audit](https://github.com/toby-bridges/api-relay-audit) | 从 DSH 发起 AI API 中继/LLM 代理的本地安全审计，产出 Markdown 报告（797★，rc.8 实测 ✅） | ✅ |
| treg | [superdesigndev/treg](https://github.com/superdesigndev/treg) | 工具目录：可检索约 2600 个外部端点（SEO/SERP/外链/社媒/人脉挖掘，536★，rc.8 实测 ✅） | ✅ |
| superdesign-skill | [superdesigndev/superdesign-skill](https://github.com/superdesigndev/superdesign-skill) | UI 与营销图形设计技能（Superdesign 画布，读仓取上下文，436★，rc.8 实测 ✅） | ✅ |
| better-deepseek | [EdgeTypE/better-deepseek](https://github.com/EdgeTypE/better-deepseek) | Better DeepSeek Chrome 扩展桥接插件（398★，rc.8 实测 ✅） | ✅ |
| dsh-plugin-subscriptions | [V1ki/dsh-plugin-subscriptions](https://github.com/V1ki/dsh-plugin-subscriptions) | 把 ChatGPT(Codex)/Claude/Grok 订阅作为 DSH 的 LLM 供应商，含设置页管理（216★，rc.8 实测 ✅） | ✅ |
| modsearch | [liustack/modsearch](https://github.com/liustack/modsearch) | 纯文本 agent 的网页搜索桥：问 web 或 X，返回结构化 JSON 证据（modlens 同作者，205★，rc.8 实测 ✅） | ✅ |
| dsh-cost-meter | [Han-1413141/dsh-cost-meter](https://github.com/Han-1413141/dsh-cost-meter) | 按会话/按日 API 成本、预算与用量百分比、官方余额、历史看板（138★，rc.8 实测 ✅） | ✅ |
| TokenLedger | [zh667/TokenLedger](https://github.com/zh667/TokenLedger) | 侧栏用量面板：把 token 归因到实际服务请求的中继站（121★，rc.8 实测 ✅） | ✅ |
| dsh-easyrewrite | [Renzic-Stone/DSH-EasyRewrite](https://github.com/Renzic-Stone/DSH-EasyRewrite) | DSH Web 用户消息气泡内联编辑与撤回插件：惰性提交、无痕替换、版本翻页器、草稿自动备份、三语 i18n（中/英/日）；npm `dsh-easyrewrite`（dsh.bundle.patch → cordis.patch.yml，`dsh plugin add` 一键安装） | 待测 |
| tabbit-browser | [Tabbit-Browser/dsh-plugin](https://github.com/Tabbit-Browser/dsh-plugin) | 让 DSH Agent 通过 Tabbit 浏览器自带的 `tabbit-cli`（任务隔离的 Playwright CLI）控制真实网页、复用真实登录态，完成网页自动化、信息提取、QA 与基准测试；bundle 随安装自动注册 `tabbit-browser` skill（持久化任务空间、locator 与等待、截图、回执与恢复）+ `tabbit_browser_install` 环境预检工具（要求正式版 ≥ 1.9.0，缺失或过低时按系统地区后台下载国内 `tabbit.com` / 国际 `tabbit.ai` 对应安装包到 Downloads 并通知绝对路径）；MIT，npm `tabbit-browser` | 待测 |
| dsh-browser-firefox | [tuojc/dsh-browser-firefox](https://github.com/tuojc/dsh-browser-firefox) | Firefox 浏览器控制（插件 + Firefox 扩展两件套）：DSH 插件经 token 认证 WebSocket 驱动用户自己的 Firefox，文本优先工具集——快照/点击/输入/按键/滚动/导航/前进后退/标签栈/取文本/等待，截图仅作视觉兜底且看完即清理；每会话一个 tab group（新旧标签全归组、检测复用不出组），新 tab 自动跟随，Firefox MV3 CSP 下 evaluate 用预编译操作（无任意 JS）；自 Lum1104/dsh-browser（MIT）移植，Firefox 扩展已在 AMO 上架：[DSH 浏览器助手](https://addons.mozilla.org/en-GB/firefox/addon/dsh-%E6%B5%8F%E8%A7%88%E5%99%A8%E5%8A%A9%E6%89%8B/) | 待测 |
| dsh-score | [PerryLink/dsh-score](https://github.com/PerryLink/dsh-score) | 多维质量评分：对 DSH 插件/仓库按安装成功（消费 dsh-test-drive 结果）、维护活跃度、文档完整性、安全扫描、协议合规五维打分，产出 JSON/Markdown 排行榜，结论均有真实 CLI 证据与审计时间戳 | 待测 |
| dsh-test-drive | [PerryLink/dsh-test-drive](https://github.com/PerryLink/dsh-test-drive) | 隔离安装与冒烟实测驱动：把仓库或 npm 包装进一次性 DSH_HOME 配置，校验 bundle patch 层与启动日志，输出结构化通过/失败矩阵（JSON/Markdown）供评分管线消费，并隔离清理所有自有临时目录；npm dsh-test-drive 0.2.3 | 待测 |
| dsh-mask | [PerryLink/dsh-mask](https://github.com/PerryLink/dsh-mask) | PII 脱敏中间件：在模型边界前把姓名/电话/邮箱/身份证/银行卡/密钥/地址替换为占位符，展示层还原，明文绝不入会话日志；/mask 命令 + mask_test 工具；npm dsh-mask 0.1.4 已发布 | 待测 |
| dsh-fast | [PerryLink/dsh-fast](https://github.com/PerryLink/dsh-fast) | 只读性能诊断：会话加载/恢复耗时、spill 命中计数、压缩次数与触发、上下文注入体量（AGENTS.md/技能/工具 schema 的 token 占比）与 LLM 缓存命中率，经 /fast 命令与 fast_report 工具呈现，异步采样不阻塞模型路径；npm `dsh-fast` 0.1.3 | 待测 |
| dsh-data-quality | [PerryLink/dsh-data-quality](https://github.com/PerryLink/dsh-data-quality) | 确定性的数据画像、清洗与校验：data_profile / data_clean / data_verify 三个模型工具 + 冻结的跨插件 verifyCitations 引用核验契约，报告持久化到 data_quality 存储域；npm `dsh-data-quality` 已发布 0.1.3 | 待测 |
| meow-cachebilling | [Phant0Meow/dsh-meow-cachebilling](https://github.com/Phant0Meow/dsh-meow-cachebilling) | 喵账单：点开输入框旁的上下文圆环即见本轮账单——缓存命中/未命中/输出各花多少钱（¥），官方峰谷价与模型分价自动判定，仅 DeepSeek 官方 API 显示；lib 随 git 发布零构建直装 | 待测 |
| dsh-session-repair (Zn-Dk) | [Zn-Dk/dsh-session-repair](https://github.com/Zn-Dk/dsh-session-repair) | 会话日志诊断与安全修复：raw zstd/JSONL 工件校验、空 tool-call ID 链的确定性修复、单槽 pre-repair 备份与恢复、审计记录；Web「会话体检」面板 + 只读诊断工具 dsh_session_repair；npm `dsh-session-repair` 0.5.3 | 待测 |
| dsh-rss-daily | [shangjian2023/dsh-rss-daily](https://github.com/shangjian2023/dsh-rss-daily) | 每日定时抓取 46 个精选 RSS 源，由 dsh 内已配置的模型编辑成新闻简报，经 webhook 推送到企业微信/Telegram/Server酱/Bark/Gotify；错过时段自动补跑；Web 面板 + rss_daily agent 工具；npm `dsh-rss-daily` | 待测 |
| dsh-humanize | [Guard42/dsh-humanize](https://github.com/Guard42/dsh-humanize) | Humanize 模式 agent 预设：把多阶段目标编排为可恢复的 Flow（draft→check→lock→终局评审→run/resume），SHA-256 流锁身份 + HMAC 终局门禁 + 事件溯源断点续跑；15 个 flow_* 工具，纯 `node:` 内置零 npm 依赖，`dsh plugin add github:Guard42/dsh-humanize` 即装，v0.1.1 起兼容原版 harness 持久层（不写自定义会话事件） | 待测 |
| dsh-forge | [maxmilian/dsh-forge](https://github.com/maxmilian/dsh-forge) | 自建 Gitea / Forgejo 的只读工具，走两者共用的 REST API：实例版本、仓库列表、议题与 PR 搜索和读取、PR diff 与变更文件，以及 Actions 运行、任务与纯文本日志；11 个工具全部只读，npm `@maxhsu/dsh-forge` 0.3.3 | 待测 |
| dsh-backup | [xiaoyuyu6420/dsh-backup](https://github.com/xiaoyuyu6420/dsh-backup) | 一键备份与恢复 ~/.dsh 用户数据：定时自动备份（重启不中断）、sha256 完整性校验与轮换、宿主升级前自动快照、会话日志体检与定点修复（doctor）、DSH 起不来也能用的零依赖救援通道、凭据默认脱敏只存本机 vault、跨机云端同步；npm `@xiaoyuyu6420/dsh-backup` 0.9.0 | 待测 |
| weiwen-law-dsh | [Shaky77/weiwen-law-dsh](https://github.com/Shaky77/weiwen-law-dsh) | 通用型因果约束中间件（白箱呈现）：R→S→D→H→M 五元因果链白箱裁决引擎，给 DSH Agent 挂 6 白箱工具 + 3 道硬性闸门（模型之外、执行之内，不侵内 H）；跨 11 场景双模型决策层 100% 收敛、引擎确定性 100% 实测（npm test 44/44 基础版 + 活系统 101 单测全绿） | 待测 |
| dsh-personal-directive | [PerryLink/dsh-personal-directive](https://github.com/PerryLink/dsh-personal-directive) | 个人指令注入插件：Web 顶部运行时开关切换自定义系统提示词段，中性占位指令随包发布（Minglink/dsh-infinite-gen-1 的框架再版，上游归属保留） | 待测 |
| dsh-qqbot-panel | [zhengjy01/dsh-qqbot-panel](https://github.com/zhengjy01/dsh-qqbot-panel) | 为官方 @tencent-connect/dsh-qqbot 提供的可视化配置面板（管理凭据、访问模式与白名单、工作区选择、扫码绑定）。 | 待测 |
| dsh-ticktick | [PerryLink/dsh-ticktick](https://github.com/PerryLink/dsh-ticktick) | TickTick（滴答清单）任务桥：会话页头部任务面板与精选代理工具，走官方 TickTick MCP 端点 | 待测 |
## 🧰 插件集

| 插件 | 仓库 | 说明 | 运行级 |
|---|---|---|---|
| dsh-plugins | [MkaliezZ/dsh-plugins](https://github.com/MkaliezZ/dsh-plugins) | DSH 插件家族索引：16 个插件（fail-closed 授权安全线 / 策略测试与诊断 / 工作区生产力 / 运行时基础设施），统一 dsh-plugin topic | 待测 |
| dsh-subagent-tools | [lynx-gt/dsh-subagent-tools](https://github.com/lynx-gt/dsh-subagent-tools) | 子代理委派按次覆盖 model/provider/persona/toolFilter、@preset: 引用、provider/model 复合 id（bundle，不改官方文件）；rc.6 headless+web 实测通过 | ✅ |
| dsh-web-workbench | [yth1120/dsh-web-workbench](https://github.com/yth1120/dsh-web-workbench) | 官方 Web UI 增强套件：右侧工作台（Browser/File Viewer/Jobs/Activity/Review）、底部终端、问题历史时间轴；经官方 packages/* 扩展点接入（org 源仓私有，登记用公开镜像；Release v0.1.0） | 待测 |
| dsh-subagent-cwd | [lynx-gt/dsh-subagent-cwd](https://github.com/lynx-gt/dsh-subagent-cwd) | dsh-subagent-tools 加按次 cwd（子代理工作目录），附两处进程内 provider 补丁；rc.6 前台/后台 cwd 实测通过 | ✅ |
| dsh-update-notifier | [arvin-yd/dsh-update-notifier](https://github.com/arvin-yd/dsh-update-notifier) | DSH 本体版本徽标：常驻侧边栏 Settings 行右侧，三色状态点（红=有更新/绿=最新/黄=检查中或失败），点开五态弹窗（复制更新命令/忽略/稍后/立即检查），启动 10s 首查+6h 复查；零构建、29 单测、mock-llm headless L4 实测（mainline 47f9438，证据见 [VERIFICATION.md](https://github.com/arvin-yd/dsh-update-notifier/blob/main/VERIFICATION.md)） | ✅ |
| dsh-daily-kit | [zhouwei713/dsh-daily-kit](https://github.com/zhouwei713/dsh-daily-kit) | 日常插件集合 monorepo：16 个插件（审批门/桌面与Webhook通知/成本计量/会话导出/Ollama 本地模型/上下文水位/办公文档解析/本地文件夹索引/cron 全局调度/RSS与网页内容监控/日历/Gmail/待办/天气地点/票据识别/音视频转录）+ 4 个一键 bundle（dev-buddy/evidence-wall/inbox-zero/daily-briefing）；权限透明、读取优先、零 native 依赖，596 单测，dsh rc.6/rc.7 真实加载与 npm 安装实测通过 | ✅ |
| dsh-suite (STARDUSTLC666) | [STARDUSTLC666/dsh-suite](https://github.com/STARDUSTLC666/dsh-suite) | 与 18 个组件配套的组合补丁：统一注入办公流、媒体工坊、DevOps、通知与极简 PTC 预设的默认配置；组件需作为直接依赖一并安装；npm `@stardustlc/dsh-suite` | 待测 |

## 🎓 技能

| 插件 | 仓库 | 说明 | 运行级 |
|---|---|---|---|
| dsh-review-skills | [ben7am1n/dsh-review-skills](https://github.com/ben7am1n/dsh-review-skills) | Engineering-discipline skill pack — code-review, simplify, plan-then-execute, test-first, resolve-conflict; bundled ctx.skills provider | 待测 |
| project-blueprint | [shuguang1994/project-blueprint](https://github.com/shuguang1994/project-blueprint) | ❌ | ❌ |
| dsh-plugin-guide | [PerryLink/dsh-plugin-guide](https://github.com/PerryLink/dsh-plugin-guide) | DSH 插件开发知识库：官方约束、任务工作流、API 参考与社区踩坑，作为按需加载的智能体技能（bundle 可安装，注册 ctx.skills 技能） | 待测 |
| dsh-chinese-traditional-wisdom-skill | [dhicoc/dsh-chinese-traditional-wisdom-skill](https://github.com/dhicoc/dsh-chinese-traditional-wisdom-skill) | 中华传统智慧（玄枢）AI Agent 技能包：八字/紫微/六爻/梅花/奇门/风水/五运六气/体质全融合，本地确定性引擎 + 可视化 Dashboard；dsh.bundle manifest 可安装 | ✅ |
| dsh-skill-pack-security | [PerryLink/dsh-skill-pack-security](https://github.com/PerryLink/dsh-skill-pack-security) | 安全审计方法论技能包：八个 agent 技能（密钥扫描、依赖审计、供应链评审、提示注入审查、审计总编排、威胁建模、漏洞情报、事件响应），中英双版本；`dsh plugin add @perrylink/dsh-skill-pack-security-provider` 一键挂载 | 待测 |

## 📡 远程渠道

| 插件 | 仓库 | 说明 | 运行级 |
|---|---|---|---|
| dsh-telegram | [ben7am1n/dsh-telegram](https://github.com/ben7am1n/dsh-telegram) | Telegram runtime adapter — chat with dsh agents from Telegram; per-chat sessions, followup bridging, committed-text streaming, allowlist auth, zero runtime deps | 待测 |
| dsh-webhook-bridge | [ben7am1n/dsh-webhook-bridge](https://github.com/ben7am1n/dsh-webhook-bridge) | ✅ | ✅ |
| dsh-lark-bot | [PlutoKeating/dsh-lark-bot](https://github.com/PlutoKeating/dsh-lark-bot) | dsh-lark-bot：把 DeepSeek Harness (dsh) 桥接进飞书/Lark 的 bot — 标准 dsh profile bundle（`npx dsh-lark-bot@latest setup` 一行安装），扫码即用：流式卡片、git worktree 项目工作区、scope 并行任务、多角色 Agent、会话归档、lark_notify 跨会话通知、对话内模型/密钥管理、安全网守护（dsh 崩溃后飞书仍可自救，/safemode 仅核心自愈）（0.15.1） | ✅ |
| dsh-lark-link | [amlyczz/dsh-lark-link](https://github.com/amlyczz/dsh-lark-link) | High-reliability Feishu/Lark bridge — QR one-click auth, CardKit streaming, zero-loss persistent outbox (at-least-once), per-conversation DSH sessions, self-healing connection, media in/out, reusable DSH Web GUI | ✅ |
| dsh-feishu-bridge | [wz-heng/dsh-feishu-bridge](https://github.com/wz-heng/dsh-feishu-bridge) | 安全边界优先的飞书/Lark channel 桥：fail-closed 白名单（空名单拒绝所有人）、webhook 签名/时间戳/重放三重校验、一次性身份绑定卡片 nonce、远程 bash 工具审批闸门（超时即拒）；ws/webhook 双 transport，`dsh plugin add` 薄壳或独立进程两种装法；已向上游 lark-channel-sdk 负责任披露验签缺陷（issues #11/#12） | 待测 |
| dsh-wechat-bridge | [gtaifu/dsh-wechat-bridge](https://github.com/gtaifu/dsh-wechat-bridge) | WeChat bridge via official Tencent iLink bot API — QR-code login, one friend = one persistent agent session, zero runtime deps, no OpenClaw | ❌ |
| dsh-onebot | [mario841859784/dsh-onebot](https://github.com/mario841859784/dsh-onebot) | QQ 渠道插件（OneBot 11 / NapCat）：反向/正向 WS、dm/群聊访问策略与 @ 门控、入站图片/语音/视频/文件解析 + whisper 转写、t2i 文字图卡片、斜杠命令、loop 合并转发+撤回（99 测试全绿，真实 QQ 链路实测） | 待测 |
| dsh-session-hub | [Asaiuta/dsh-session-hub](https://github.com/Asaiuta/dsh-session-hub) | 多服务器 DSH 会话聚合与原生操控：网关+官方 UI 桥，一屏合并多个远程 dsh web 的会话，支持历史/prompt/取消/重命名/fork/模型选择/审批问答，并导入本机其他工具的历史会话 | 待测 |
| dsh-reach | [PerryLink/dsh-reach](https://github.com/PerryLink/dsh-reach) | 多通道决策与远程控制桥：把 DSH 的审批卡与提问卡推送到 IM 渠道（先微信），可在聊天中直接作答，带会话控制台、逐渠道安全与开放推送服务 | 待测 |
| dsh-wechat | [PerryLink/dsh-wechat](https://github.com/PerryLink/dsh-wechat) | 微信私聊消息桥接 DSH：文本、图片、文件与音视频双向传输 | 待测 |

## 🛠 基础设施

| 插件 | 仓库 | 说明 | 运行级 |
|---|---|---|---|
| dsh-work | [vibeinging/dsh-work](https://github.com/vibeinging/dsh-work) | 以 dsh 为骨、codex 为皮的桌面 app | 待测 |
| deepseek-harness-desktop | [chyra-moon/deepseek-harness-desktop](https://github.com/chyra-moon/deepseek-harness-desktop) | Windows 原生桌面外壳:1:1 官方 Web UI、内置服务器托管、托盘驻留与掉线自动恢复 | ✅ |
| dsh-remote-sandbox | [weijiafu14/dsh-remote-sandbox](https://github.com/weijiafu14/dsh-remote-sandbox) | 生产级远程执行世界：E2B 沙箱内纯 JS sidecar，fs/subprocess 单次往返、进程输出有界、心跳保活、崩溃透明恢复（resume/recreate）、tar 工作区同步；修复官方 e2b POC 两处 host 假设。43 项测试（含 6 项真机 E2E）全绿 | 已测 |
| pi2dsh | [weijiafu14/pi2dsh](https://github.com/weijiafu14/pi2dsh) | Pi 生态兼容层：用一个 DSH Host ABI 让未修改的 Pi 扩展包作为原生 DSH 插件运行，桥接工具、命令与 hooks、会话与子代理、模型 Provider 与 OAuth、MCP 及 Web UI；npm `pi2dsh`，持续以契约测试和真实 DSH E2E 验证 | ✅ |
| dsh-session-cleaner-cli | [ChenChen913/dsh-session-cleaner-cli](https://github.com/ChenChen913/dsh-session-cleaner-cli) | DSH 会话数据离线清理 CLI：按工作区交互/命令删除会话（回收站+恢复+自动备份）、同步工作区账目与投影缓存、修剪幽灵条目；零依赖 Node≥18，8 项端到端测试全绿 + CI | 待测 |
| dsh-suite | [whyihaveyou/dsh-suite](https://github.com/whyihaveyou/dsh-suite) | DSH 插件活目录 + 脚手架 + 内置插件商店：785+ 插件每小时刷新、每日兼容 CI 实测、中英双语可搜索目录站；含 create-dsh-plugin 脚手架与 plugin-manager / plugin-notify / plugin-session-export / plugin-team-board 五个 npm 包 | 已测 |
| dsh-change-budget | [Raphaelutumn/dsh-change-budget](https://github.com/Raphaelutumn/dsh-change-budget) | 为每个 DSH Agent 回合设置文件数、修改调用数与 UTF-8 载荷额度；在受支持的文件修改工具执行前阻止超额修改，并对并行调用同步预留额度 | 待测 |
| dshscan | [shaoshi20/dshscan](https://github.com/shaoshi20/dshscan) | DSH 插件安全审查器：风险评分/严重等级/证据/安装建议；静态+语义双通道、DSH 特有攻击面规则、npm 源码扫描与 audit、批量扫描、HTML 报告 + Web Dashboard（npm: @shaoshi/dshscan） | 待测 |
| dsh-local-ai | [PerryLink/dsh-local-ai](https://github.com/PerryLink/dsh-local-ai) | Ollama 本地模型接入：ollama_list/pull/remove/show 与健康检查，以官方 LlmAdapter 注册 Ollama 路由并按 model_route 规则（离线优先/长文本/隐私）分流、失败自动回退云端；/ollama 命令一键总览；npm dsh-local-ai 已发布 | 待测 |
| dsh-cert-mcp | [PerryLink/dsh-cert-mcp](https://github.com/PerryLink/dsh-cert-mcp) | DSH 插件认证注册表 MCP 服务器：查询认证、列出已认证插件、读取认证规范 | 待测 |
| dsh-wallpaper-engine | [elysia395/dsh-wallpaper-engine](https://github.com/elysia395/dsh-wallpaper-engine) | 把本机 Wallpaper Engine 壁纸渲染到 DSH Web 对话界面后方：视频原生播放、Web/HTML 走 iframe、Scene 壁纸由内置纯 JS 场景渲染器输出完整场景帧（对象树/纹理/粒子/shader 效果）；iOS 液态玻璃（配色/玻璃颜色/透明度/模糊统一调节）、一级液态玻璃设置页、壁纸选择弹窗、隐藏/恢复、倍速/翻转/亮度对比度饱和度、遮挡暂停省电三档、ffmpeg 抽帧转码帧率上限、自定义壁纸上传；设置持久化到宿主端文件，npm `dsh-plugin-wallpaper-engine` 0.7.0 | 待测 |
| dsh-theme-macintosh | [fengb3/dsh-theme-macintosh](https://github.com/fengb3/dsh-theme-macintosh) | 经典麦金塔 System 7 像素主题：ChiKareGo/Fusion Pixel 像素字体、桌面噪点画布、Finder 式会话侧栏、黑白按钮与弹窗、深浅色随官方外观切换、Kit 检视页；npm `dsh-theme-macintosh`，`dsh plugin add github:fengb3/dsh-theme-macintosh` 一键安装 | ✅(自报) |

## 📚 学习研究

| 插件 | 仓库 | 说明 | 运行级 |
|---|---|---|---|
| dsh-fund-research | [PerryLink/dsh-fund-research](https://github.com/PerryLink/dsh-fund-research) | 中国公募基金确定性研究：天天基金/东方财富公开数据采集（pingzhongdata JS 块、F10 持仓与经理页、个股估值 + push2delay 兜底主机），业绩拆解/持仓穿透/风格归因/经理画像纯函数计算，版本化 Markdown 报告附每个关键数字可回溯到 sha256 源快照的附录；npm dsh-fund-research 已发布；仅供研究，不构成投资建议 | 待测 |
## 🚢 发行版

完整替代/重发行形态（非 drop-in 插件，从源码运行）：

| 插件 | 仓库 | 说明 | 运行级 |
|---|---|---|---|
| deepseek-harness-ux | [ayuanwong/deepseek-harness-ux](https://github.com/ayuanwong/deepseek-harness-ux) | 面向长任务的 DeepSeek Harness Web UX 社区源码版：保留上游 agent/runtime 与插件架构，强化任务进度、运行详情、会话恢复、长文阅读、工作区与交付物体验；当前从源码运行，非独立 npm 插件（#152） | 源码运行 |

## ❓ 未分类

<!-- 新增条目示例（复制下面一行修改后插入对应分类表格末尾）：
| dsh-pr-checks | [pauloapoloni/dsh-pr-checks](https://github.com/pauloapoloni/dsh-pr-checks) | 打开 PR 的 GitHub Actions 检查状态与进度：按工作区/项目分组，侧边栏底部常驻展示；dsh bundle（host + web client），npm dsh-pr-checks 0.1.1，dsh 0.1.1-rc.2 实测，MIT | 待测 |
| dsh-verify | [263311487-ux/dsh-verify](https://github.com/263311487-ux/dsh-verify) | 真实浏览器验收测试：对 agent 交付的 Web 应用执行可证伪的端到端验收（CLI + MCP + DSH 插件三入口，dsh/plugin.mjs Cordis 可安装，npm `dsh-verify`） | 待测 |
| dsh-qingagent | [void2anything/dsh-qingagent](https://github.com/void2anything/dsh-qingagent) | 把开源 AI 写作客户端「青简 QingAgent」接进 DSH：对话里起草改稿，右侧宣纸面板排版渲染（mermaid/drawio/表格/KaTeX），每处修改先摆在纸上供审阅、提交才落稿（opt-out：撤销不要的，其余一次提交）；10 个 qing_ 宿主工具，npm `dsh-qingagent` 0.1.46（无 install 期脚本，lib 随 git 零构建直装）；需本机运行青简桌面客户端（qingagent.com，MIT） | 待测 |
| dsh-task-dispatcher | [zhengjy01/dsh-task-dispatcher](https://github.com/zhengjy01/dsh-task-dispatcher) | 滴答清单任务派发器：按间隔拉取今天到期任务（有变化才通知 flomo+macOS），可选自动执行（每任务一个 headless 会话）、执行会话工作区选择、dispatcher_report flomo 汇总工具与 Web 任务看板；npm `dsh-task-dispatcher` 0.1.0 | 待测 |
| dsh-sonarqube | [maxmilian/dsh-sonarqube](https://github.com/maxmilian/dsh-sonarqube) | SonarQube Community Build Web API 的只读工具：实例状态、分支或 PR 的质量阈、议题与安全热点搜索、单个热点详情，以及覆盖率、重复率或调用方指定的度量项；6 个工具全部只读，npm `dsh-sonarqube` 0.1.0 | 待测 |
| dsh-approval-hotkeys | [SiriLee/dsh-approval-hotkeys](https://github.com/SiriLee/dsh-approval-hotkeys) | 审批面板键盘快捷键：Enter 批准一次、Esc 拒绝、Esc 暂停键盘驱动审阅，审批/提问面板通用；npm `dsh-approval-hotkeys`，`dsh plugin add` 一键安装 | 待测 |
| my-plugin | [你的账号/my-plugin](https://github.com/你的账号/my-plugin) | 一句话功能描述 | 待测 |
-->

| 插件 | 仓库 | 说明 | 运行级 |
|---|---|---|---|
| dsh-plugin-workshop | [yyyyukari/dsh-plugin-workshop](https://github.com/yyyyukari/dsh-plugin-workshop) | 创意工坊式插件浏览器：侧栏常驻入口，搜索/最热/最新/近 7-90 天飙升榜、中文关键词映射、描述与 README 机翻、插件特征验证过滤、一键安装/更新/卸载，内置已安装插件管理（零服务器，GitHub 直连） | ✅ |
| dsh-file-review | [left0ver/dsh-file-review](https://github.com/left0ver/dsh-file-review) | 文件审查插件：diff 的形式查看文件的修改内容，方便对 agent 的修改进行审查 | ✅ |
| dsh-file-claim | [Nwflower/dsh-file-claim](https://github.com/Nwflower/dsh-file-claim) | 同一工作区并行多会话的文件认领与写入保护（claim/release、心跳 stale 接管、pending 三路合并） | ✅ |
| dsh-memento | [PerryLink/dsh-memento](https://github.com/PerryLink/dsh-memento) | 有界、分层、审批门、可审计的跨会话记忆接缝：ctx.memory 服务 + 本地 SQLite（零依赖）+ memory 工具 + 冻结快照注入；写必审批、模型可见 ⟺ 落盘；0.4.0 预演 dsh-memory-protocol v1——适配器注册表（mem0/Hermes/CLAUDE.md 转换）+ 可分发一致性套件 | ✅ |
| dsh-mcp-panel | [PerryLink/dsh-mcp-panel](https://github.com/PerryLink/dsh-mcp-panel) | 官方 MCP 客户端（dsh-mcp-client）管理控制台：/mcp 命令 + 设置页 MCP 页签提供服务器增删改（审批门 + 自动备份的只追加 profile 写入）、走官方工具管线的工具试用台、健康诊断与连接状态；npm 0.4.0，全量门禁绿（142 测试） | 待测 |
| dsh-auto-continue | [HsiangNianian/dsh-auto-continue](https://github.com/HsiangNianian/dsh-auto-continue) | DSH Web 请求中断自动续跑插件：回合因网络/超时等非人为原因失败后自动发送「继续」续跑（含宿主崩溃遗留回合扫描恢复），全部参数可在设置→插件配置中调整 | ✅ |
| sandbase-harness | [sandbaseai/sandbase-harness](https://github.com/sandbaseai/sandbase-harness) | DSH bundle for SandBase managed-agents, exposing agent discovery, durable sessions, streamed runs, artifacts, and cancellation over stdio MCP; verified against DSH 47f9438 | ✅ |
| sandbase-skills | [sandbaseai/sandbase-skills](https://github.com/sandbaseai/sandbase-skills) | Research and growth skill collection with an npm CLI that installs complete bundles into DSH native .dsh/skills discovery root; verified against DSH 47f9438 | 待测 |
| dsh-vision-router | [ysr666/dsh-vision-router](https://github.com/ysr666/dsh-vision-router) | 为纯文本 Agent 提供视觉能力：内置免 Key 视觉链 + 像素级视觉工具（看图问答、定位、裁剪、像素对比、取色、OCR、矢量化、抠图、截图）；粘贴图片即可用，无 Python，一条命令安装；dsh-plugin-verify 实测 7/7 waterfall + tools/result（isError:false，捕获 16 事件） | ✅ |
| dsh-pixel-ui | [zhang66633/dsh-pixel-ui](https://github.com/zhang66633/dsh-pixel-ui) | 像素风皮肤（Agent Xi 风格）：四主题一键切换 + fusion-pixel/Press Start 2P 像素字体 + CRT 质感，随时切回现代默认 UI | 待测 |
| dsh-plugin-installer | [zhang66633/dsh-plugin-installer](https://github.com/zhang66633/dsh-plugin-installer) | 插件商店 + 安装助手：Web GUI「插件商店」页签 + 内置安装技能（npm 直装 / GitHub clone 注册，18 个已知坑配方） | 待测 |
| dsh-malong-bridge | [wulun811/LiuHe](https://github.com/wulun811/LiuHe) | 六合工具集 DSH bundle：44 个 MCP 代码操作工具 + 动态 workspace 注入；npm 安装 @jieai/dsh-malong-bridge | 待测 |
| dsh-oai-oauth | [werifu/dsh-oai-oauth](https://github.com/werifu/dsh-oai-oauth) | OpenAI ChatGPT OAuth LLM 适配器：让 dsh 直接使用 ChatGPT 订阅（非 API Key）接入模型 | 待测 |
| dsh-whale-animation | [LeemanCheung/dsh-whale-animation](https://github.com/LeemanCheung/dsh-whale-animation) | DSH Web 回合状态旁的 60 帧随主题适配的单色鲸鱼深潜动画：传播式水面、无缝闭环、资源内嵌、`prefers-reduced-motion` 静态 PNG 回退，停止时完整清理 | 待测 |
| dsh-token-usage | [LeemanCheung/dsh-token-usage](https://github.com/LeemanCheung/dsh-token-usage) | 本地优先的四 bucket Token 可观测性：持久会话/provider/model/日期仪表盘、趋势、预算与异常信号、公开费率估算、安全聚合导出，以及显式触发的用量/会话轨迹分析 | 待测 |
| dsh-task-dag | [LeemanCheung/dsh-task-dag](https://github.com/LeemanCheung/dsh-task-dag) | 由投影驱动的会话子代理与持久工作流实时 DAG：状态与节点导航、深层链路确定性布局、适应/平移画布，以及当前会话内节点拖动重排；无并行数据库或 Host 轮询 | 待测 |
| dsh-qq2007-skin | [LeemanCheung/dsh-qq2007-skin](https://github.com/LeemanCheung/dsh-qq2007-skin) | DSH Web GUI 的 QQ 2007 风格皮肤：72 个原生主题 token、作用域三栏窗框、原创离线素材与像素伙伴、可选合成发送提示音、响应式/无障碍回退和可恢复设置开关 | 待测 |
| dsh-sql | [STARDUSTLC666/dsh-sql](https://github.com/STARDUSTLC666/dsh-sql) | 工程师级数据库：sql_list/query/exec/schema/stats/health 六工具，SQLite/MySQL/PostgreSQL 三引擎、多连接、只读模式与写审批门、行数钳制、库概览统计、查询结果 CSV/JSON 输出 | ✅ |
| dsh-feishucard | [cmfok/dsh-feishucard](https://github.com/cmfok/dsh-feishucard) | DSH ↔ 飞书桥（自研非 fork）：官方 SDK 长连接（无需公网）+ 流式回复卡片（过程话语内联/工具折叠面板/状态符号/限流退避熔断兜底），每聊天独立会话 + live 复用保上下文，配置独立 ~/.dsh-feishucard；npm dsh-feishucard v0.1.0，冒烟 18 项 + 实机链路实测通过 | ✅ |
| dsh-trajectory-reader | [flyingtimes/dsh-trajectory-reader](https://github.com/flyingtimes/dsh-trajectory-reader) | 轨迹解读标签页：按用户轮次解读助手行为（需求/思路/执行/结果），规则引擎 + 可选 LLM 叙述，文件/命令/错误一目了然，用户消息原样保留；dsh.bundle.patch 一键安装 | ✅ |
| dsh-remotion | [STARDUSTLC666/dsh-remotion](https://github.com/STARDUSTLC666/dsh-remotion) | Remotion 官方技能移植：React 编程式视频（动画/音频/字幕/3D/图表/字体），38 个规则文件，附 remotion_health 随包技能资源自检，技能可跨 harness | ✅ |
| dsh-hyperframes | [STARDUSTLC666/dsh-hyperframes](https://github.com/STARDUSTLC666/dsh-hyperframes) | HyperFrames by HeyGen 五件套：HTML 写视频、GSAP 动画、字幕、配音、音频响应、网址转视频，附 hyperframes_health 随包技能资源自检 | ✅ |
| dsh-voice | [STARDUSTLC666/dsh-voice](https://github.com/STARDUSTLC666/dsh-voice) | 语音双件套：voice_tts（edge-tts 免费微软神经语音）/ voice_stt（OpenAI 兼容 ASR）/ voice_list / voice_preview 音色批量试听 / voice_health 自检，WebSocket 直连，插件级代理 | ✅ |
| dsh-codex-port | [STARDUSTLC666/dsh-codex-port](https://github.com/STARDUSTLC666/dsh-codex-port) | 把 ~/.codex 官方插件（186 插件、583 技能）一键移植为 DSH 技能：codex_list/port/status/health，frontmatter 转换、幂等跳过、Codex 目录自检，技能可跨 harness | ✅ |
| dsh-dream | [STARDUSTLC666/dsh-dream](https://github.com/STARDUSTLC666/dsh-dream) | 做梦插件：会话回放（多帧 zstd 零依赖解析）→ 反思 → 梦境日记，dream_digest/save/journal/recall/health 五工具 + 做梦协议技能，记忆巩固向 | ✅ |
| dsh-ppt | [STARDUSTLC666/dsh-ppt](https://github.com/STARDUSTLC666/dsh-ppt) | PPT 技能 + 工具：一句话/文档 → HTML 放映 + PPTX 导出，5 套主题，中英双语，裸 SKILL.md 跨 harness | ✅ |
| dsh-minimal-ptc | [STARDUSTLC666/dsh-minimal-ptc](https://github.com/STARDUSTLC666/dsh-minimal-ptc) | 极简 PTC 模式 Agent 预设：一句 RL 对齐提示词 + PTC 全量工具，安装即物化到用户预设目录，不覆盖用户自建预设 | ✅ |
| ncm-player | [WolfGenerals/ncm-player](https://github.com/WolfGenerals/ncm-player) | 网易云音乐浮窗播放器：歌单/歌词/歌词翻译/播放队列/账号登录，适配皮肤主题 | 待测 |
| dsh-theme-eink-retro | [exoticknight/dsh-theme-eink-retro](https://github.com/exoticknight/dsh-theme-eink-retro) | DSH Web UI 纸墨风客户端主题：平衡模式保留语义状态色，沉浸模式采用黑白显示；设置可在浏览器本地切换与持久化 | ✅ |
| dsh-theme-plugin | [BeiZi6/dsh-theme-plugin](https://github.com/BeiZi6/dsh-theme-plugin) | DSH Web GUI 主题工作室：5 套内置预设（codex-warm / nord / solarized / graphite / stock）+ 完全可自定义的浅/深配色（强调色、背景、前景、UI 与代码字体、半透明侧栏、对比度），经官方 theme overrideTokens 即时热切换、localStorage 持久化，纯官方接缝无补丁文件 | 待测 |
| dsh-opencodego-usage | [BeiZi6/dsh-opencodego-usage](https://github.com/BeiZi6/dsh-opencodego-usage) | OpenCodeGo 剩余额度监视器：输入框右下角呼吸灯（按剩余额度绿/黄/红）+ 液态玻璃面板（滚动/周/月三窗口用量与重置时间），每 30 秒自动刷新，Key 自动读取 DSH 凭据（opencode-go 提供商）也可手动覆盖 | 待测 |
| dsh-usage-dashboard | [Cassius0924/dsh-usage-dashboard](https://github.com/Cassius0924/dsh-usage-dashboard) | DeepSeek 额度与用量仪表盘：悬浮额度窗 + 「额度」tab，余额可用天数、今日/本月消耗环比、模型/会话成本排行、缓存节省、2026-08-17 峰谷定价前后账单对比，估算算法与单价公开在 src/pricing.ts | 待测 |
| dsh-checkpoint-rewind | [PerryLink/dsh-checkpoint-rewind](https://github.com/PerryLink/dsh-checkpoint-rewind) | Claude Code /rewind 等价能力：每次变更型工具执行前捕获 git 优先工作区快照（stash create / commit-tree 未引用对象，copy 兜底），轮次边界 fork 会话，一条 /rewind 命令恢复文件并回退会话（三段式事务 + 保护检查点 + preview 只读预览 + 增量字节配额）；npm 可装，160 单测 + Win/Linux CI 全绿 | 待测 |
| dsh-composer-history | [PerryLink/dsh-composer-history](https://github.com/PerryLink/dsh-composer-history) | 终端风格作曲器输入历史：边缘优先方向键召回并精确还原草稿与光标、浏览器本地持久化历史、Ctrl+R 反向搜索、滑动上下文感知（压缩摘要加入召回与搜索）；dsh.bundle manifest 可安装；rc.6 headless --patch 加载实测通过 | 待测 |
| dsh-output-styles | [PerryLink/dsh-output-styles](https://github.com/PerryLink/dsh-output-styles) | Claude Code outputStyles 兼容的运行时输出风格切换：/style 命令、按会话持久化（output_style 域）、systemPrompt 注入、六个内置风格、自定义 Markdown/JSON 风格库与热重载、Web 选择器；npm dsh-output-styles 0.3.2；rc.6 真实 bundle 安装 + profile 加载实测通过（详见 PR 自检） | 待测 |
| dsh-auto-review | [PerryLink/dsh-auto-review](https://github.com/PerryLink/dsh-auto-review) | 审批链上的第二模型 AI 自动审查：只读审查子代理返回带理由的 allow/deny 结构化裁决，fail-closed 兜底，全量会话日志审计；Web 审查面板；npm 可装 | 待测 |
| dsh-image-gen | [LeemanCheung/dsh-image-gen](https://github.com/LeemanCheung/dsh-image-gen) | GPT Image 2 `image_gen`：默认复用 Codex 订阅 OAuth，也可显式使用 API Key；显影卡片、最多 3 张 API 实时局部图、持久附件回放/灯箱/下载、纯文本模型输出和受限的凭据安全请求 | 待测 |
| dsh-image-gen (shanliuling) | [shanliuling/dsh-image-gen](https://github.com/shanliuling/dsh-image-gen) | DSH 原生生图与图片编辑，支持对话直出与画廊查看 | 待测 |
| dsh-lsp-actions | [PerryLink/dsh-lsp-actions](https://github.com/PerryLink/dsh-lsp-actions) | LSP 动作面：诊断/格式化/补全/代码动作/符号/签名提示/inlay 提示/重命名 8 工具，官方 seam 优先 + 内置 stdio 客户端兜底；写入走 write-intent 与沙箱策略，其余只读；241 测试 + 真实 tsls e2e + CI 矩阵全绿，npm dsh-lsp-actions | 待测 |
| dsh-agfs | [openAGFS/dsh-agfs](https://github.com/openAGFS/dsh-agfs) | 文件浏览器 Web 插件（npm `@open-agfs/dsh-agfs`，`dsh plugin add` 一行安装）：宿主 webserver 同进程托管 React 前端 + REST API + `/dsh-agfs` 命令 + `browse_files`/`read_file` 模型工具；一键AI分析（右键建工作区并唤醒新会话，与手动创建一致的 agent preset 工具集）、本地打开（系统文件管理器）、三种显示尺寸、Win10 文件管理器主题（Segoe MDL2 Assets 官方图标）；109 单测 + 真实 Loader/HTTP 组合测试全绿，rc.6 web profile 实测通过（一键分析真实运行 55 次工具调用 0 错误） | ✅ |
| dsh-open-eyes | [Hyp6666/dsh-open-eyes](https://github.com/Hyp6666/dsh-open-eyes) | 让用户选择的多模态模型成为 DeepSeek 的眼睛：显式纯文本路由下桥接 WebUI 粘贴/拖入图片，并提供 vision_analyze；原生支持 OpenAI Responses、Chat Completions 与 Anthropic Messages，Credential Reference + workspace 边界；125 单测、Node 22/24 CI 与真实 tarball 临时 profile 安装/卸载通过 | 待测 |
| dsh-plugin | [plur-ai/dsh-plugin](https://github.com/plur-ai/dsh-plugin) | PLUR 持久记忆：engram 在每次 assembly 渲染进 system prompt（section 的 text 为函数），而非藏在工具调用后——记忆块被替换而非追加，上下文长度不随会话增长（实测 60 轮恒定）；全本地 BM25 + BGE 混合检索（RRF 融合，零 API 调用）、可编辑的纯 YAML 存储、按工作区划分 scope、/plur 与 /plur-memory 命令 | ✅ |
| dsh-industry-research | [PerryLink/dsh-industry-research](https://github.com/PerryLink/dsh-industry-research) | 行业与公司研究领域包：产业链结构模型（industry_map）、公开来源政策/新闻追踪（industry_track）、公司扫描卡片（company_scan）与可审计研究报告（industry_report，可选 ctx.researchReport 密封桥 + 内置 Markdown 兜底）；全部检索走官方 ctx.web，指标带来源引用，仅供研究不构成投资建议 | ✅ |
| cc-dsh-notifier | [baobaolaodie/cc-dsh-notifier](https://github.com/baobaolaodie/cc-dsh-notifier) | Windows 桌面通知:Claude Code hooks 与 dsh web/tui 双 surface 事件(权限请求/提问/工具报错/等待输入)→ 原生 Toast + 点击跳转;聚焦感知静默、多会话、tarball 零手工安装;Windows 10/11 专用 | 待测 |
| dsh-openviking | [Rxiain/dsh-openviking](https://github.com/Rxiain/dsh-openviking) | OpenViking 检索、资源管理、自动召回与会话记忆：memsearch/memfind 等 10 个工具、已索引仓库上下文注入、自动召回注入、会话同步+自动提交 | ✅ |
| dsh-capcheck | [heming-gmh/dsh-capcheck](https://github.com/heming-gmh/dsh-capcheck) | 装插件之前先看看它实际能碰到什么：静态分析 inject 声明、ctx 成员访问和依赖声明，对照能力分级表出报告，扫过的插件里 dsh-ssh 的远程命令执行绕过了官方审批沙箱、dshmarket 拿到了能启停其它插件的 Loader 控制权；优先扫真实发布的 npm tarball，因为很多插件的构建产物没提交到 GitHub 仓库 | ✅ |
| dsh-session-hotkeys | [YEYEYEYESHIFU/dsh-session-hotkeys](https://github.com/YEYEYEYESHIFU/dsh-session-hotkeys) | Web UI 会话快捷键：Alt+1-9 顺序切换、固定槽位三态、Alt+↑↓ 循环切换、高亮导航模式、归档/重命名/新建会话、可改键面板（键盘导航 + 内置诊断），Windows/macOS 双预设无冲突，npm 已发布 | 待测 |
| dsh-result-only-view | [YEYEYEYESHIFU/dsh-result-only-view](https://github.com/YEYEYEYESHIFU/dsh-result-only-view) | Web 对话「只看结果」开关：隐藏思考与工具调用过程，运行中仅保留一条实时状态行，回合结束显示「已处理 N 步」痕迹行可点击展开回看；中英双语，常规设置可配置痕迹行与 reduced-motion 光影策略；npm 已发布 | 待测 |
| dsh-quant-data-mcp | [helibeiqi/dsh-quant-data-mcp](https://github.com/helibeiqi/dsh-quant-data-mcp) | 零依赖 MCP stdio server 模板 + 开箱即用 A 股数据工具：无需 API Key、纯 NDJSON 协议、路径全走环境变量、可 `dsh plugin add` 一键挂载的 dsh bundle | 待测 |
| dsh-self-evolving | [timwhitez/dsh-self-evolving](https://github.com/timwhitez/dsh-self-evolving) | 证据优先的 DSH 自进化引擎（标准 Cordis controller/service）：有界生成 Cordis 候选插件，一次性真实 Loader 隔离准入，Harbor 评估，可崩溃恢复的 journal 谱系；291 单测 + 36 Loader E2E | 待测 |
| dsh-github | [PerryLink/dsh-github](https://github.com/PerryLink/dsh-github) | 官方级 GitHub CI 集成：composite action.yml、轮询 PR 评审机器人（幂等行内评论 + status-check 门禁）、/pr /review /issue 命令族与 12 个 PR/issue 工具，所有写入走人工审批门；npm @perrylink/dsh-github 0.6.1 | 待测 |
| dsh-headroom | [WanYanTianDe/dsh-headroom](https://github.com/WanYanTianDe/dsh-headroom) | Headroom 上下文压缩：历史区间压缩（替代 LLM 总结）+ 大工具输出压缩（超阈值自动瘦身）+ CCR 原文取回（headroom_retrieve 工具）；本地代理自动安装/生命周期管理 + 设置卡片；npm 已发布（@wanyantiande/dsh-headroom） | 待测 |
| dsh-click | [PerryLink/dsh-click](https://github.com/PerryLink/dsh-click) | Windows 优先的原生桌面控制：截图、无障碍树结构化读取、点击/输入/滚动/按键、应用启动，变更性操作过审批门禁、屏幕变化拒绝执行、操作前后校验进程身份 | 待测 |
| dsh-session-sync | [PerryLink/dsh-session-sync](https://github.com/PerryLink/dsh-session-sync) | 跨设备会话同步：专用 git 镜像 + 仅追加的双方保留冲突裁决（本地保留、远端留存 fork 文件，绝不静默覆盖），/sync 命令与 sync_status/sync_pull/sync_push 工具，自动推拉可配；49 测试 + 真实 git e2e 全绿，rc.6 --patch 加载实测通过 | 待测 |
| dsh-translate | [PerryLink/dsh-translate](https://github.com/PerryLink/dsh-translate) | 厂商参数翻译与确定性 JSON 修复：/translate 命令映射 11 家厂商的 13 个规范参数；post-execute 修复层 + fix_json 工具修复工具输出中的坏 JSON（转义/去尾逗号/截断闭合/null 占位补全），绝不编造数据 | 待测 |
| dsh-observe | [PerryLink/dsh-observe](https://github.com/PerryLink/dsh-observe) | 可观测性导出：session/event 流转为 OTLP traces+metrics 与 Langfuse 观测（turn/step/tool/LLM span、token/成本计数、脱敏 prompt/completion），异步批量 + 有界持久离线缓冲 + 退避重试，默认关闭显式开启 | 待测 |
| dsh-enhancement-suite | [Scorp1o117/dsh-enhancement-suite](https://github.com/Scorp1o117/dsh-enhancement-suite) | 四个 Scorp1o117 DSH 插件的官方总入口 + 一键安装器（list/install/update/doctor，--profile/--only/--dry-run）：零依赖，走官方 dsh plugin CLI 并安全自动挂载；npm 已发布 | 待测 |
| dsh-passwords | [slywalker2006/dsh-passwords](https://github.com/slywalker2006/dsh-passwords) | 登录网关（密码门）：让 dsh 安全远程访问——首次配置创建主账号、多用户管理、子用户权限/配额（工作区、token、时长、上传/git）、bcrypt + 静态加密、防爆破锁定、自动 HTTPS | ✅ |
| dsh-feishu | [PGZXB/dsh-feishu](https://github.com/PGZXB/dsh-feishu) | DeepSeek Harness 的飞书 UI：面板驱动控制台，卡内审批与提问，流式卡片，扫码一键配置 | 待测 |
| dsh-draw | [PerryLink/dsh-draw](https://github.com/PerryLink/dsh-draw) | 统一静态图像生成路由：单一 image_generate 工具 + 标准参数，配置驱动的 OpenAI 兼容引擎路由（OpenAI Images、智谱 CogView 及任意兼容端点）与健康感知回退，工作区持久附件结果、按会话配额记账、对话内结果卡片，API key 存为凭据引用 | 待测 |
| dsh-library | [PerryLink/dsh-library](https://github.com/PerryLink/dsh-library) | 本地优先文档知识库：library_add/remove/list、语义+关键词混合 library_search（多样性重排、相关性过滤、避免 lost-in-the-middle）、引用感知注入与 library_cite_check/diagnose，SQLite 索引 + 本地嵌入，零模型下载 | 待测 |
| dsh-budget | [PerryLink/dsh-budget](https://github.com/PerryLink/dsh-budget) | 成本治理：按模型/会话/天聚合 token 与费用计量，会话/日/月预算上限 + 阈值告警（桌面通知 + webhook）与超限 alert/block/degrade 策略，碳足迹估算、分模型延迟基准、Settings 预算页与 /budget 命令 | 待测 |
| dsh-defend | [PerryLink/dsh-defend](https://github.com/PerryLink/dsh-defend) | 注入/越狱/密钥泄露检测 + 危险删除门禁：Aho-Corasick 引擎在用户消息、工具参数、工具结果三处按 allow/ask/block 拦截（脱敏 defend/detection 审计事件、defend_report 工具、/defend 命令），并拒绝工作区外的递归删除命令 | 待测 |
| dsh-sessions-manager | [TOBYCAI/dsh-sessions-manager](https://github.com/TOBYCAI/dsh-sessions-manager) | 统一「会话管理」面板：归档/恢复/彻底删除/跨工作区移动/批量多选/工作区标签 + 每条会话详情（磁盘占用、轮次/步骤/消息、工具使用、write/edit 文件、血统）；卡片操作收敛为 ⋯ 菜单 | 待测 |
| dsh-peekfile-everything | [fastengiel-kurai/dsh-peekfile-everything](https://github.com/fastengiel-kurai/dsh-peekfile-everything) | DSH 全盘文件搜索与预览插件：统一搜索工作目录、WSL 和 Windows Everything 索引，支持本地多格式预览、路径接管、会话引用，并可与 Better Sidebar 配合管理工作目录内文件 | 待测 |
| Blue | [dsh-blue/blue](https://github.com/dsh-blue/blue) | 插件树式终端界面（TUI）：流式 markdown 会话流、工具卡片、模糊命令补全、主题热切换与 /btw 旁路提问，每个界面组件都是可热替换的 Cordis 插件；npm `@dsh-blue/blue`（`rc` 线，`dsh plugin --profile blue add @dsh-blue/blue@rc` 安装），双语文档站 dsh-blue.dev | 待测 |

| dsh-nuke-plugin | [beijingwahw/dsh-nuke-plugin](https://github.com/beijingwahw/dsh-nuke-plugin) | 事务化强力卸载引擎：validate/preview/execute/undo 四段式 + Saga 回滚、WAL 崩溃自恢复、hash chain 审计链、硬链接去重、贝叶斯先知推演（成功率/期望回收/最脆弱步骤）；21 工具 222 测试 MIT | 待测 |
| dsh-edit-approval | [SiriLee/dsh-edit-approval](https://github.com/SiriLee/dsh-edit-approval) | 写文件/工具调用前的逐处审批门：write/edit/stream 操作显示红绿行级 diff 后再放行，bash 命令审批（默认关）+ 可配置门控；npm `dsh-edit-approval`，`dsh plugin add` 一键安装 | 待测 |
| dsh-rewind | [SiriLee/dsh-rewind](https://github.com/SiriLee/dsh-rewind) | DSH Web 同窗口原地回退（Claude Code /rewind 语义）：每条用户消息旁 ↶ 按钮把模型上下文截断回任意一条消息，可选 Claude Code 风格文件回滚（磁盘持久化 before 备份）；npm `dsh-rewind-plugin`，`dsh plugin add` 一键安装 | 待测 |
