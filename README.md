# DSH Plugin Radar

<p align="center">
  <img src="assets/banner-radar.jpg" width="560" alt="DSH Plugin Radar banner"><br>
  <img src="assets/stickers/21-tests-passed.png" width="126" alt="测试通过">


</p>

<p align="center">
  <a href="https://trendshift.io/repositories/147500" title="GitHub Trending 日榜 #22 · 2026-08-14 · 全语言口径"><img src="https://trendshift.io/api/badge/trendshift/repositories/147500/daily" alt="Trendshift"></a>
</p>


**开源的 DeepSeek Harness 插件生态雷达——持续发现、运行级验证、15 分钟快照。自动生成 artifact同步在[PLUGINS-ALL.md](PLUGINS-ALL.md)中更新。**


安装前就知道哪个能用，不用自己踩坑。

[![confirmed](https://img.shields.io/badge/confirmed-1082-blue)](#精选插件榜) [![scan](https://img.shields.io/badge/scan-every_6h-green)](#当前生态快照) [![tested](https://img.shields.io/badge/tested-13334-orange)](#本仓库如何判定) [![dshfind](https://dshfind.com/api/badge/AdamPlatin123/dsh-plugin-radar?lang=zh)](https://dshfind.com/zh/plugins/AdamPlatin123/dsh-plugin-radar?ref=badge) [![license](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

[![运行级可用](https://img.shields.io/badge/运行级可用_8983-0.1.1--rc.2-brightgreen)](#2-看懂状态统一四档口径) [![待测](https://img.shields.io/badge/待测_1732-0.1.1--rc.2-lightgrey)](#2-看懂状态统一四档口径) [![需适配](https://img.shields.io/badge/需适配_2732-0.1.1--rc.2-yellow)](#2-看懂状态统一四档口径)



简体中文 | [English](README.en-US.md)

---

> 已索引 15443 repos · 克隆验证为 DSH 插件 2996 · 清单呈现 2943 · 当前版本 0.1.1-rc.2 实测 345 个 DSH 插件仓库

**架构原则：目录是构建产物（Catalog is a build artifact）。**

```text
Radar Engine（开源 → engine/）
     ↓
机器可读快照（data/snapshots/，每 15 分钟）
     ↓
目录渲染器（聚合 · 分类 · 双语渲染）
     ↓
┌─ PLUGINS-ALL.md 全量清单
├─ 精选插件榜 / 整合包
├─ 生态快照 / 兼容矩阵
└─ dshfind 等下游消费方
```

## 工作原理

> 数据截至快照 `20260906T183001Z`（2026-09-07 02:30:03 UTC+8 · 分类器 unified-v2-bridge）

<!-- AUTO:pipeline:START -->
```mermaid
flowchart TB
    subgraph Discovery["发现（每 6 小时 · probe 每 15 分钟 巡检触发）"]
        A1["GitHub Search<br/>topic ×2 + keyword ×3<br/>候选 18718 · 龄 65m"]
        A2["本地库补全 · 去重 repo id"]
        A3["私有 org 仓排除<br/>35s 错峰 · 403 退避 · dshow 黑名单"]
    end
    subgraph Validation["验证（driver 20s 流式循环）"]
        B1{"package.json<br/>name + main/exports/dsh?"}
    end
    B1 -->|"插件 1082"| C1["k8s 运行级测试<br/>一插件一 pod · 并发 10<br/>dsh agent + Qwen（de-stream）"]
    B1 -->|"非插件（累计删 0）"| B3["即删省空间"]
    C1 --> D1{"判定 · 总 13334"}
    D1 -->|"8983 / 2732"| E1["聚合 + README 分类统计"]
    D1 -->|"1619 环境类重试"| C1
    E1 --> E2["cadence 交付<br/>本周期增量 —/100<br/>双仓 bot PR（幂等 supersede）"]
    M["radar-probe 每 15 分钟 自愈<br/>7 指标流 × 60s · 完成累计 2"]
    M -.-> A1
    M -.-> C1
```
<!-- AUTO:pipeline:END -->

**🔌 开源计划 — 本页数据由「DSH 插件雷达」服务管线自动生产，服务雷达源码正在优化中，稳定后将分阶段开源：**

| 阶段 | 开源内容 | 状态 |
|---|---|---|
| Phase 1 | 管线文档：[总览与路线图](docs/radar/overview.md) · [架构](docs/radar/architecture.md) · [数据契约](docs/radar/data-contracts.md) | ✅ 已开源 |
| Phase 2 | 雷达引擎源码（发现 · 聚合 · 渲染 · 分发 + 运维自愈） | ✅ 已开源 → [engine/](engine/) |
| Phase 3 | 测试引擎源码：轻量版（无需 k8s · 本地直跑）· 服务器版（k8s 集群） | 🔜 稳定后开源 |

## 快速导航

| 你的目标 | 跳转入口 |
|---|---|
| 了解这个雷达系统本身 | [工作原理](#工作原理) · [架构原则](#工作原理) · [开源引擎源码 engine/](engine/) · [管线文档](docs/radar/overview.md) |
| 看精选插件 | [精选插件榜](#精选插件榜) — 人工策展 · 11 类 |
| 一把装好不挑单品 | [整合包](#-整合包) — 预设套件 / 能力合集 / 发行版 / 配方管理器 |
| 市场接入（引用可用性数据） | [数据接口 docs/api.md](docs/api.md) — 两个稳定 JSON · 无需申请 · 署名即可 |
| 按用途找一个插件 | [分类目录](#分类目录) — 13 类功能领域 · 逐插件明细见 [PLUGINS-ALL.md](PLUGINS-ALL.md)；[PLUGINS.md](PLUGINS.md) 为 PR 登记清单 |
| 浏览自动发现的全部仓库 | [ 当前生态快照](#当前生态快照) — 日期化兼容矩阵 |
| 了解最近发生了什么 | [ CHANGELOG](CHANGELOG.md) |
| 登记或提交插件 | [ 给插件开发者](#给插件开发者) · 加 `dsh-plugin` topic → 8h 自动收录 · [PR 模板](.github/PULL_REQUEST_TEMPLATE.md) |
| 了解本雷达与开源计划 | [ 雷达总览与路线图](docs/radar/overview.md) · 架构与数据契约见 [docs/radar/](docs/radar/) |
| 给插件使用者指南 | [ 给插件使用者](#给插件使用者) |
| 本仓库如何判定兼容性 | [ 本仓库如何判定](#本仓库如何判定) |
| 加入社群交流 | [ DSH 学习社区](#dsh-学习社区-dshfindcom) · [社区讨论群](#社区讨论群) |

> [!IMPORTANT]
> **收录不等于兼容，静态检查不等于运行可用，运行可用也不等于安全审计。**
> 本仓库提供可追溯的筛选信号，不代表 DSH 官方背书。安装第三方插件前，请检查插件源码、权限、依赖、许可证及测试日期。

## 🛒 生态目录（雷达生成的 artifact）

以下所有目录内容——精选榜、整合包、分类目录、兼容矩阵——均由上述雷达管线自动生产与刷新（精选榜与整合包成员为人工策展，星标与状态由 bot 持续更新）。
数据接口与下游接入见 **[🤝 市场与下游接入](#-市场与下游接入欢迎引用可用性数据)**。

<details>
<summary><b>📖 展开生态目录</b>（精选榜 56 款 · 整合包 16 个 · 13 域分页明细 17971 条）</summary>

### 精选插件榜

<!-- AUTO:featured:START -->

> 人工策展 56 款插件，按 11 类分组、类内按星标排序；星标每 6 小时自动刷新（成员调整请提 PR 修改 data/awesome-50.json）。数据截至 2026-09-06 23:32（UTC+8）。

### 🚀 智力增强 Booster（7）

- <img src="assets/tile-adapt.svg" alt="需适配" width="122" height="20"> **[dsh-routing-suite](https://github.com/yjh051108/dsh-routing-suite)** · 7109★ — 注入器 × 思维模式路由套装：免重启运行时注入器 + 任务感知推理模式路由预设（P1-P23 实测）
- <img src="assets/tile-test.svg" alt="待测试" width="122" height="20"> **[ouroboros](https://github.com/Q00/ouroboros)** · 5781★ — Agent OS：agent 自我变强、人只守底线——自进化运行时（5.7k★；rc.8 实测 ✅）
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[harmony-next.skills](https://github.com/linhay/harmony-next.skills)** · 343★ — 技能驱动的工作流增强
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[superpowers-dsh](https://github.com/LayneChai/superpowers-dsh)** · 86★ — TDD/调试/计划等开发技能集
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[forkprobe](https://github.com/Jayden-X-L/forkprobe)** · 72★ — 同一任务跑多个技能对比，自动选优
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-tool-turbo](https://github.com/Electricitysheep/dsh-tool-turbo)** · 7★ — 按轮次自动优化 reasoning_effort（推理力度）
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-reasoning-settings](https://github.com/JuneLearn/dsh-reasoning-settings)** · 6★ — 推理设置控制：让模型按任务切换思考档位

### 🖥 界面与工作台（7）

- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-web-ui](https://github.com/zhu1090093659/dsh-web-ui)** · 6998★ — Web UI 增强与皮肤合集：任务看板、Git 图、移动端、皮肤中心
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[DSH-better-sidebar](https://github.com/omdsh-dev/DSH-better-sidebar)** · 3368★ — 侧边栏变完整工作台：文件编辑/终端/Git/子代理，支持三方注册扩展页
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-genui](https://github.com/omdsh-dev/dsh-genui)** · 411★ — GenUI 内联组件：图表/表单/测验/3D 场景 + action 事件环
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-visualize](https://github.com/Nagi-ovo/dsh-visualize)** · 256★ — 对话中生成交互式可视化卡片
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-annotation](https://github.com/omdsh-dev/dsh-annotation)** · 110★ — 划选文字→批注→随消息发送，回复逐条对照
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[Liang-Saint-Slider](https://github.com/BruzWJ/Liang-Saint-Slider)** · 96★ — 模型与思考力度选择滑条
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-navbar](https://github.com/vlln/dsh-navbar)** · 55★ — 对话节点导航条：右缘节点串快速跳转（官方 bundle 插件）

### ⌨️ 终端与桌面端（5）

- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-desktop](https://github.com/anywhere-labs/dsh-desktop)** · 23934★ — 生态最高星桌面客户端（21.5k★，原 deepseek-harness-desktop 再改名）：万物皆插件、桌面本身也是插件（雷达重测中；rc.8 源码路径实测 ✅）
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[deepseek-harness-desktop](https://github.com/hairyf/deepseek-harness-desktop)** · 1725★ — Tauri 桌面版：5MB 安装包零环境配置，Win/macOS/Linux
- <img src="assets/tile-adapt.svg" alt="需适配" width="122" height="20"> **[Bigfish](https://github.com/turtle2209/Bigfish)** · 312★ — 第三方桌面端：内置 Node 运行时，双击即用
- <img src="assets/tile-test.svg" alt="待测试" width="122" height="20"> **[oh-dsh](https://github.com/hust-open-atom-club/oh-dsh)** · 303★ — 社区发行版：桌面/Web/TUI 三形态统一体验
- <img src="assets/tile-adapt.svg" alt="需适配" width="122" height="20"> **[dsh-tianshu-tui](https://github.com/huiliyi37/dsh-tianshu-tui)** · 262★ — 自研 ANSI 渲染的极简终端 UI

### 👁 视觉与多模态（4）

- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[modlens](https://github.com/liustack/modlens)** · 3889★ — 生态第一个视觉插件，视觉工作流的基准方案
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[agent-vision-toolkit](https://github.com/Anionex/agent-vision-toolkit)** · 1175★ — 通用 agent 视觉工具箱：多图理解/图片问答/前端 UI 还原/GUI 自动化（dsh-vision-toolkit 同作者）
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-vision-router](https://github.com/ysr666/dsh-vision-router)** · 1076★ — 内置免费视觉模型路由，给文本 agent 装眼睛
- <img src="assets/tile-adapt.svg" alt="需适配" width="122" height="20"> **[dsh-vision-toolkit](https://github.com/Anionex/dsh-vision-toolkit)** · 855★ — 带意图图片问答、长截图 OCR、UI 还原

### 🤖 Agent 能力与编排（7）

- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[distilly](https://github.com/titanwings/distilly)** · 24386★ — 把专家思维蒸馏为可复用 Skills 的平台（24k★，Agent 域之最，原名 colleague-skill；雷达判可用）
- <img src="assets/tile-test.svg" alt="待测试" width="122" height="20"> **[dsh-agent-teams](https://github.com/NanmiCoder/dsh-agent-teams)** · 1406★ — 多代理团队编排
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[helloagents](https://github.com/hellowind777/helloagents)** · 704★ — agent 能力合集
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[sandbase-harness](https://github.com/sandbaseai/sandbase-harness)** · 642★ — CMA 兼容开源 agent 运行时，任意模型可驱动
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[rea](https://github.com/morluto/rea)** · 396★ — 用 agent 逆向工程任何东西：从应用行为到原生二进制
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[open-record-replay](https://github.com/humblebanana/open-record-replay)** · 143★ — macOS 录制回放：把鼠标/键盘/UI 事件存为结构化轨迹供 agent 学习重放
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[axern](https://github.com/cofy-x/axern)** · 59★ — AI agent 开源沙箱：不可信代码执行与持久服务

### 💻 编码与生产力（5）

- <img src="assets/tile-test.svg" alt="待测试" width="122" height="20"> **[TokenTracker](https://github.com/xiufengsun/TokenTracker)** · 1526★ — 本地优先的 31 种编码工具 token 用量与成本追踪
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[api-relay-audit](https://github.com/toby-bridges/api-relay-audit)** · 824★ — AI API 中继/LLM 代理本地安全审计，产出 Markdown 报告（rc.8 实测 ✅）
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[claude-paper](https://github.com/alaliqing/claude-paper)** · 334★ — 跨 agent 论文工具箱：速读摘要/深度研读材料/代码演示 + 本地 Web 阅读器
- <img src="assets/tile-adapt.svg" alt="需适配" width="122" height="20"> **[mobius](https://github.com/nutshellai-tech/mobius)** · 296★ — 编码增强
- <img src="assets/tile-test.svg" alt="待测试" width="122" height="20"> **[dsh-remote](https://github.com/flymysql/dsh-remote)** · 59★ — 多机远程工作区：SSH 连接管理、远程目录→本地镜像→原生工作区收养、SFTP 双向同步与 rw_* 工具族

### 🧠 记忆与上下文（3）

- <img src="assets/tile-test.svg" alt="待测试" width="122" height="20"> **[EverOS](https://github.com/EverMind-AI/EverOS)** · 12740★ — 全 agent 便携记忆层：本地优先、Markdown-native（12.4k★ 记忆域之最；rc.8 实测 ✅）
- <img src="assets/tile-adapt.svg" alt="需适配" width="122" height="20"> **[mnemon](https://github.com/mnemon-dev/mnemon)** · 558★ — 跨 agent、本地优先的持久记忆
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-memory-evolve](https://github.com/csyangwen/dsh-memory-evolve)** · 286★ — 五轨记忆 + git 分支托管 + 后台自我进化

### 📡 消息通讯与 IM（4）

- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-lark](https://github.com/omdsh-dev/dsh-lark)** · 51★ — 飞书 IM bot 频道（官方渠道插件）
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-message-edit](https://github.com/Moeblack/dsh-message-edit)** · 49★ — 分支式消息编辑、reroll、重试、多版本
- <img src="assets/tile-test.svg" alt="待测试" width="122" height="20"> **[dsh-interconnect](https://github.com/Chinesezjc/dsh-interconnect)** · 35★ — 跨 DSH 实例消息/事件交接
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[ChatCCC](https://github.com/wzj998/ChatCCC)** · 22★ — 飞书/微信聊天控制 DSH / Claude Code

### 🗂 文件、数据与浏览（4）

- <img src="assets/tile-adapt.svg" alt="需适配" width="122" height="20"> **[dsh-browser](https://github.com/Lum1104/dsh-browser)** · 574★ — Chrome 侧栏扩展，让 DSH 直接操作浏览器
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-openpencil](https://github.com/ZSeven-W/dsh-openpencil)** · 163★ — OpenPencil 设计稿预览与编辑
- <img src="assets/tile-adapt.svg" alt="需适配" width="122" height="20"> **[dsh-web-search-pro](https://github.com/anweat/dsh-web-search-pro)** · 61★ — 增强型持久网页搜索
- <img src="assets/tile-test.svg" alt="待测试" width="122" height="20"> **[dsh-plugin-mineru](https://github.com/HuanLinOTO/dsh-plugin-mineru)** · 45★ — PDF/图片/Office 转结构化 Markdown

### 🛒 市场与管理（4）

- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-market](https://github.com/dsh-market/dsh-market)** · 3302★ — 持续收录 1000+ 插件的市场：中文搜索 + 五维评分
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-web-plugin-manager](https://github.com/LX2000WASD/dsh-web-plugin-manager)** · 67★ — Web UI 一键管理插件：启停/装卸/环境管理
- <img src="assets/tile-adapt.svg" alt="需适配" width="122" height="20"> **[dsh-plugin-check](https://github.com/omdsh-dev/dsh-plugin-check)** · 27★ — 插件健康检查：清单协议/patch 格式/构建陷阱
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[deepseek-plugin-store](https://github.com/Ericwong5021/deepseek-plugin-store)** · 25★ — 独立社区插件商店：发现/安装/提交经验证的插件

### 🎮 娱乐生活（6）

- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[petdex](https://github.com/crafter-station/petdex)** · 4048★ — 生态最高星桌宠图鉴
- <img src="assets/tile-test.svg" alt="待测试" width="122" height="20"> **[dsh-deep-whale](https://github.com/Small-tailqwq/dsh-deep-whale)** · 1941★ — 深海鲸鱼养成
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[openpets](https://github.com/alvinunreal/openpets)** · 1166★ — 本地优先桌面伴侣平台：动画宠物 + 插件 SDK（娱乐域第二位）
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-ads](https://github.com/Nagi-ovo/dsh-ads)** · 611★ — 把 DSH 变回 2005 门户网站：怀旧广告/小游戏/弹窗
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[whale-girl](https://github.com/vlln/whale-girl)** · 313★ — QQ 宠物形态桌宠：可拖拽/投喂/玩耍
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-kun-like-pet](https://github.com/liyupi/dsh-kun-like-pet)** · 89★ — 小坤桌宠：随 Agent 工作状态切换 9 种动作

> 兼容状态磁贴 = 雷达 k8s 运行级判定（🟩 已兼容 · 🟨 需适配 · ⬜ 待测试，三态等宽；四档口径见下文），右半为该轮 runner 测试版本（与 [data/radar-env.json](data/radar-env.json) 同源），**本列由 bot 按最新快照自动回写**，榜内成员走插队重测通道优先轮测；rc.8 + v4flash 源码路径重测（2026-08-21，50 仓 + 对方清单高星 22 仓）证据见 [data/rc8-retest-20260821/](data/rc8-retest-20260821/) 与 [PLUGINS-ALL.md](PLUGINS-ALL.md)；安装第三方插件前请审查源码并固定 commit。

<!-- AUTO:featured:END -->

## 📦 整合包

<!-- AUTO:bundles:START -->

> 人工策展 16 个整合包：内测成员作品置顶，其下按预设套件 / 能力合集 / 发行版 / 配方管理器四形态分组，类内按星标排序；星标每 6 小时自动刷新（成员调整请提 PR 修改 data/bundles.json）。数据截至 2026-09-06 23:32（UTC+8）。

### ⭐ 内测成员作品（1）

- <img src="assets/tile-test.svg" alt="待测试" width="122" height="20"> **[marisa-distro](https://github.com/LoserFox/marisa-distro)** · 10★ — 魔理沙整合发行版（内测成员作品）：DSH 0.1.0-rc.7 + 桌面壳 + 29 个插件 + MyGO 插件市场，Windows MSI/便携版/profile 三形态安装（v0.1.11，Release 带 SHA256 校验）

### 🎚 预设与配置套件（4）

- <img src="assets/tile-adapt.svg" alt="需适配" width="122" height="20"> **[dsh-routing-suite](https://github.com/yjh051108/dsh-routing-suite)** · 7109★ — 注入器 × 思维模式路由套装：免重启运行时注入器 + P1-P23 任务感知推理模式路由（rc.8 实测 ✅）
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-anchored-standard](https://github.com/xiaobright/dsh-anchored-standard)** · 3824★ — 两阶段预设：极简模式对齐启动 → 全量装载（rc.8 实测 ✅）
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-gitbash-preset](https://github.com/liceses/dsh-gitbash-preset)** · 135★ — Windows 一键「极简模式 Git Bash」预设：把自带极简模式的 bash 调用映射到 Git Bash
- <img src="assets/tile-test.svg" alt="待测试" width="122" height="20"> **[dsh-roleplay-preset](https://github.com/oliblue-evan/dsh-roleplay-preset)** · 19★ — 沉浸式角色扮演预设：零工具纯对话、酒馆式演出格式、文件记忆库

### 🧩 能力合集（8）

- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[Aegis](https://github.com/GanyuanRan/Aegis)** · 1170★ — 软件工程方法论技能包：baseline-first 规划、系统性重构（rc.8 实测 ✅）
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[helloagents](https://github.com/hellowind777/helloagents)** · 704★ — agent 能力合集（rc.8 实测 ✅）
- <img src="assets/tile-test.svg" alt="待测试" width="122" height="20"> **[DeepSec](https://github.com/Unclecheng-li/DeepSec)** · 398★ — AI 安全攻防一体化合集：Android · Web · Native · 协议 · 恶意代码 · AI 六域
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[harmony-next.skills](https://github.com/linhay/harmony-next.skills)** · 343★ — 技能驱动的工作流增强（rc.8 实测 ✅）
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-reverse-skill](https://github.com/dhicoc/dsh-reverse-skill)** · 118★ — 完整逆向工程技能合集（85 个 SKILL.md）
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[superpowers-dsh](https://github.com/LayneChai/superpowers-dsh)** · 86★ — TDD/调试/计划等开发技能集（rc.8 实测 ✅）
- <img src="assets/tile-ok.svg" alt="已兼容" width="122" height="20"> **[dsh-daily-kit](https://github.com/zhouwei713/dsh-daily-kit)** · 2★ — 日常插件集合：16 插件 monorepo + 4 bundle，含 596 单测
- <img src="assets/tile-test.svg" alt="待测试" width="122" height="20"> **[dsh-plugins](https://github.com/MkaliezZ/dsh-plugins)** · 0★ — DSH 插件家族索引：agentfuse / evidence-task-board / test-normalizer 等 16 插件合集（monorepo）

### 📀 发行版（2）

- <img src="assets/tile-test.svg" alt="待测试" width="122" height="20"> **[Bigfish](https://github.com/turtle2209/Bigfish)** · 312★ — 第三方桌面端发行版：内置 Node 运行时，双击即用（雷达判需适配——发行版形态非单插件安装）
- <img src="assets/tile-test.svg" alt="待测试" width="122" height="20"> **[oh-dsh](https://github.com/hust-open-atom-club/oh-dsh)** · 303★ — 社区发行版：桌面/Web/TUI 三形态统一体验

### 📑 配方管理器（1）

- <img src="assets/tile-adapt.svg" alt="需适配" width="122" height="20"> **[dsh-recipe](https://github.com/863683348/dsh-recipe)** · 1★ — 场景配方管理器（插件界的 dotfiles）：列出/搜索/安装插件组合（形态稀缺，豁免星标门槛）

> 磁贴口径同精选榜（三态 · 右半 runner 版本）；整合包安装方式以各仓库 README 为准（预设类多为 `dsh plugin add` 后在设置中启用，发行版类需按其自身安装器操作）。

<!-- AUTO:bundles:END -->

## 分类目录

<!-- AUTO:catalog:START -->

逐插件明细（判定 · 定位 · 星标）按域分页见 **[PLUGINS-ALL.md](PLUGINS-ALL.md)** 索引。

- **🎓 技能包**（26）— 可用 6 · 不兼容 1 · 待定 5 · 未测 11 · 监测 3 — [明细](catalog/all/技能包.md)
- **🧠 记忆增强**（46）— 可用 14 · 不兼容 5 · 待定 4 · 未测 2 · 监测 21 — [明细](catalog/all/记忆增强.md)
- **🎨 主题皮肤**（17）— 可用 8 · 不兼容 0 · 待定 1 · 未测 5 · 监测 3 — [明细](catalog/all/主题皮肤.md)
- **🛒 市场与管理**（308）— 可用 100 · 不兼容 20 · 待定 18 · 未测 8 · 监测 162 — [明细](catalog/all/市场与管理.md)
- **🔌 Web UI 增强**（2779）— 可用 1344 · 不兼容 403 · 待定 259 · 未测 17 · 监测 756 — [明细](catalog/all/Web%20UI%20增强.md)
- **💻 编码开发**（2156）— 可用 932 · 不兼容 354 · 待定 188 · 未测 19 · 监测 663 — [明细](catalog/all/编码开发.md)
- **🤖 Agent 能力**（2248）— 可用 814 · 不兼容 274 · 待定 166 · 未测 11 · 监测 983 — [明细](catalog/all/Agent%20能力.md)
- **📡 消息通讯**（718）— 可用 259 · 不兼容 114 · 待定 56 · 未测 4 · 监测 285 — [明细](catalog/all/消息通讯.md)
- **🗂 文件数据**（675）— 可用 270 · 不兼容 93 · 待定 57 · 未测 9 · 监测 246 — [明细](catalog/all/文件数据.md)
- **🎮 娱乐生活**（451）— 可用 174 · 不兼容 34 · 待定 30 · 未测 0 · 监测 213 — [明细](catalog/all/娱乐生活.md)
- **🛠 基建部署**（1358）— 可用 442 · 不兼容 133 · 待定 124 · 未测 4 · 监测 655 — [明细](catalog/all/基建部署.md)
- **📚 学习研究**（156）— 可用 36 · 不兼容 9 · 待定 8 · 未测 2 · 监测 101 — [明细](catalog/all/学习研究.md)
- **❓ 其他**（7193）— 可用 1837 · 不兼容 365 · 待定 256 · 未测 21 · 监测 4714 — [明细](catalog/all/其他.md)

<!-- AUTO:catalog:END -->

</details>

## 🤝 市场与下游接入（欢迎引用可用性数据）

插件市场、聚合站与社区清单（dsh-market、dshfind、awesome 列表等）**欢迎直接引用本雷达的运行级可用性数据**——两个稳定 JSON 接口，无需申请、署名即可：

```python
d = json.load(urllib.request.urlopen(
    "https://raw.githubusercontent.com/AdamPlatin123/dsh-plugin-radar/main/data/plugins-all.json"))
verdict = {p["repo"]: p["verdict"] for p in d["plugins"]}   # 9230 条 · 四档判定 + 星标 + 描述
```

三态磁贴资产可热链、动态徽章端点 schema、口径与署名规范见 **[docs/api.md](docs/api.md)**。

##  DSH 学习社区 dshfind.com

[dshfind.com](https://dshfind.com) — DSH 原理学习、插件市场与最佳实践社区：从 Cordis 论文逐章精读到插件自动聚合市场。

<a href="https://dshfind.com"><img src="assets/dshfind-zh.png" width="600" alt="dshfind.com — DSH 学习与分享社区"></a>

[ dshfind.com](https://dshfind.com) · [GitHub](https://github.com/hikariming/dshfind)

## 社区讨论群

DSH 插件社区讨论群（微信群）：插件作者、维护者与使用者都在这里，讨论插件开发、兼容性问题与新插件发布。

<img src="assets/community-discussion-20260905.jpg" width="350" alt="DSH 插件社区讨论群">

> **入群指引（长期有效）**：上方为微信群 7 天期分享码，过期后请[开一个新 issue](https://github.com/AdamPlatin123/dsh-plugin-radar/issues/new?title=%5B%E5%85%A5%E7%BE%A4%5D%E8%AF%B7%E6%B1%82%E6%96%B0%E7%9A%84%E7%A4%BE%E5%8C%BA%E7%BE%A4%E4%BA%8C%E7%BB%B4%E7%A0%81) 索取新码（标题注明「入群」），维护者会尽快更新图片。插件作者请在 issue 里附上你的插件仓库链接，方便对号。

> 二维码 7 天内有效（2026-09-05 前）。

## 给插件使用者

### 1. 找到候选插件

- 优先浏览[分类目录](#分类目录)与逐插件明细 [PLUGINS-ALL.md](PLUGINS-ALL.md)：自动发现并经运行级实测的全量清单，每条带判定、定位与星标。
- [PLUGINS.md](PLUGINS.md) 是经 PR 登记的社区登记清单（人工说明 + 运行级结果），适合核对作者已登记申报的插件，与自动发现互补。
- 若以上都没有，再从[当前生态快照](#当前生态快照)进入当日索引，搜索仓库名或关键词。
- 仓库无法公开访问、没有 README、没有许可证或长期无维护时，把它视为高风险候选，而不是“已验证插件”。

### 2. 看懂状态（统一四档口径）

全部条目使用**单一运行级口径**（k8s 容器实测，测试版本见下），四档互斥：

| 状态 | 它说明什么 | 它不说明什么 |
|---|---|---|
|  运行级可用 | 在记录的测试版本下真实加载并完成验证任务 | 不是完整功能测试、性能测试或安全审计 |
|  运行级不兼容 | 依赖装不上、只读沙箱、缺内部包等硬失败（3 次重试全败） | 不代表永远不可用；作者可能已在新版本修复 |
|  待定 | 测试环境故障，未完成判定 | **不是部分兼容**，待重测 |
| · 未测 | 尚未派发运行级测试 | 不应推断为兼容或不兼容 |

> [!NOTE]
> **测试版本**：dsh（容器内 agent）+ Qwen3.6-35B 驱动（经 de-stream 代理）· k8s 5 分片 · 以快照 `run_id` 锚定具体轮次（当前 `20260906T183001Z`）。DSH 的 npm 版本号未随快照记录，以 run_id 与 `reports/agent-test/` 日期交叉核对。
> **口径提示**：徽章与统计中的「已测 N」是单轮运行口径；分类目录与全量清单是跨轮累积口径，两者数字不同属正常。

每个结论都应同时看四项：**插件 commit、mainline commit、测试日期、测试层级**。缺少其中任一项时，降低对结果的信任等级。

### 3. 安装、验证和回滚

本目录不是包管理器，也没有被本仓库验证过的统一安装命令。请以插件自身 README 的安装方式为准，并建议按以下顺序操作：

1. 阅读插件的安装、配置、权限和卸载说明。
2. 固定插件版本或 commit，不直接依赖会漂移的默认分支。
3. 先在隔离 profile 或测试环境加载，不提供生产密钥和敏感数据。
4. 执行一个最小功能任务，记录 DSH 版本、插件版本和日志。
5. 保留原配置与锁文件；失败时能移除插件并恢复环境。

若插件安装或功能本身出错，请优先在插件仓库反馈；若目录链接、分类或状态证据有误，请在本仓库提交 issue 或 PR。

## 给插件开发者

### 最低收录条件

公开目录建议只列出普通访问者能够打开的仓库。自动发现候选至少应满足：

- 仓库公开可访问，并添加 `dsh-plugin` topic；
- 根目录存在合法的 `package.json` 和非空 `name`；
- 提供 `main`、`exports` 或明确的 `dsh` 集成入口；
- README 说明插件做什么、如何安装、如何卸载以及最小使用示例；
- 所有运行时依赖在 `dependencies` / `peerDependencies` 中显式声明；
- 声明支持的 DSH 版本、快照或已验证 commit；
- 提供许可证，并避免把密钥、个人信息或私有仓库内容提交到公开目录。

包名应使用你有权控制的命名空间。只有获得 `dsh-external` 维护权限的项目才应使用 `@dsh-external/*`；不要占用不属于你的组织或官方保留命名空间。

### 一个合格的插件 README 至少包含

| 章节 | 应回答的问题 |
|---|---|
| Overview | 插件解决什么问题？适合谁？ |
| Compatibility | 支持哪些 DSH 版本或 mainline commit？最后验证日期是什么？ |
| Install / Uninstall | 如何安装、升级、禁用和彻底移除？ |
| Quick start | 最小配置和一个可复现示例是什么？ |
| Configuration | 配置项、默认值、环境变量和敏感项有哪些？ |
| Permissions & data | 会访问哪些文件、网络、凭据或用户数据？ |
| Troubleshooting | 常见错误、日志位置和回滚方式是什么？ |
| Development | 如何构建、测试和贡献？ |
| License & security | 使用什么许可证？安全问题如何私下报告？ |

### 提交插件

1. 给插件仓库添加 `dsh-plugin` topic，等待下一次扫描。
2. 在 [PLUGINS.md](PLUGINS.md) 的合适分类追加插件名、仓库链接和一句话说明。
3. 对照上面的最低条件完成自检。
4. 使用 [PR 模板](.github/PULL_REQUEST_TEMPLATE.md) 提交变更，并附上测试环境与结果。

仅修正链接、分类、描述或状态证据时，也欢迎直接提交小型 PR。请不要在目录 PR 中复制私有 issue、密钥、成员信息或大段第三方内容。

**收录形态口径**：[PLUGINS.md](PLUGINS.md) 按安装形态分区——`🔌 单插件` / `🧰 插件集`（叠加式，经官方扩展点接入，运行级按实测四档）与 `🚢 发行版`（替换式，从源码运行的完整重发行，运行级标「源码运行」）。提交前请对号入座；功能领域分类（本页分类目录）由雷达分类器自动判定，与登记分区正交。

## 本仓库如何判定

| 层级 | 当前检查 | 合理结论 |
|---|---|---|
| L0 发现 | topic、仓库可见性、基本元数据 | 这是一个候选仓库 |
| L1 清单 | `package.json`、名称、入口字段 | 它“看起来可安装”，但还未证明能加载 |
| L2 静态兼容 | 补丁、扩展点（seam）、依赖版本范围 | 发现已知漂移信号，或暂未发现阻断信号 |
| L3 编译实验 | 在指定 workspace 中执行类型或语法检查 | 仅对该构建环境有效；缺依赖和环境问题需与真实 API 漂移分开 |
| L4 运行实测 | 安装、加载、最小任务或工具调用 | 在记录的环境和 commit 上观察到成功或失败 |

> [!NOTE]
> 首页不把以上层级合并成一个模糊的“兼容率”。静态通过、编译通过和运行通过使用不同字段与分母；完整证据保留在日期化报告中。

### 已知边界

- mainline 和插件都在快速变化，旧结论可能很快失效。
- 静态未发现问题不代表真实运行一定成功。
- 编译失败可能来自测试环境、缺失依赖或配置错误，不应自动等同于 API 不兼容。
- 运行成功只覆盖报告中的最小任务，不代表全部功能、平台和配置。
- 自动生成的 LLM 摘要只用于导航，不能替代原始矩阵和日志。

## 仓库结构

| 路径 | 内容 |
|---|---|
| `PLUGINS.md` | 人工分类和登记的精选入口 |
| `reports/<YYYY-MM-DD>/index.md` | 指定日期的完整扫描索引 |
| `reports/<YYYY-MM-DD>/mainline-compat.md` | 指定日期的静态兼容性矩阵 |
| `reports/<YYYY-MM-DD>/compile-compat.md` | 指定日期的编译与语法实验结果 |
| `reports/<YYYY-MM-DD>/runtime-test.md` | 指定日期的运行级测试结果 |
| `CHANGELOG.md` | 日期化生态变更摘要 |
| `docs/radar/` | 雷达总览、架构与数据契约（含开源路线图） |
| `docs/CATALOGING.md` | 插件分类标准（与 `scripts/classify.py` 同源） |
| `scripts/` | 发现、检查、测试和渲染脚本 |

<details>
<summary>维护者：README 自动生成约定</summary>

- 人工内容放在自动标记块之外；生成器只替换 `AUTO:ecosystem` 块。
- 首页只输出汇总和报告链接，不输出完整仓库表。
- 新增/修改项最多显示 10 条，其余链接到 `CHANGELOG.md`。
- 仓库链接必须使用扫描结果中的完整 `owner/name`，不得硬编码组织名。
- 自动块使用真实日期路径；另生成普通文件 `reports/LATEST.md` 作为可验证的稳定入口，不依赖目录符号链接。
- 报告缺失、为空或数字校验失败时显示“数据暂不可用”，不得沿用旧值或生成强结论。
- 运行结果与静态结果使用不同字段、不同分母，并展示测试覆盖数。

</details>

## 当前生态快照

<!-- AUTO:ecosystem:START -->
> 渲染于快照 20260906T183001Z（2026-09-07 02:30 UTC+8）· 数据源 data/snapshots/（渲染即对齐）

| 证据层 | 当前结果 |
|---|---:|
| 自动收录 全量索引 2943 · 收录（克隆验证）2996 · 当前版本（0.1.1-rc.2）已测 345 个仓库 |
| 运行级实测 | 8983 可用 · 2732 不兼容 · 1619 待定（共 13334 个，k8s agent 口径）|

[完整索引](PLUGINS-ALL.md) · [运行实测](reports/2026-08-27/agent-test-v2.md)

<!-- AUTO:ecosystem:END -->


## 项目边界与致谢

本仓库维护目录、检测规则和证据报告，不托管第三方插件代码。感谢所有提交插件、复现问题、修正元数据和维护测试链路的贡献者。

本仓库的目录内容与脚本采用 [MIT License](LICENSE)；第三方插件仍遵循各自仓库声明的许可证。

非常感谢各位一起参与内测的小伙伴们（合照仅为部分名单，还有更多朋友一起在内测中贡献力量）！

![DSH 内测群合照](assets/dsh-miji-heying.png)

Let's keep deep diving！
