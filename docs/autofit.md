# dsh-autofit：雷达的客户端

> 独立仓库：**[AdamPlatin123/dsh-autofit](https://github.com/AdamPlatin123/dsh-autofit)** · npm：**[`dsh-autofit`](https://www.npmjs.com/package/dsh-autofit)** · MIT

雷达在服务器上对全生态做 L0–L3 运行级实测，回答"这个插件在测试环境里能不能跑"。**dsh-autofit 把同一套判定搬到你自己的 DSH 里**，回答"它在**我这台机器、这个 DSH 版本**上能不能跑，不能的话能不能修好"。

*Radar answers "does this plugin run" across the ecosystem; dsh-autofit answers "does it run on **my** DSH, and can it be fixed if not" — inside your own DSH.*

## 它做什么

| 能力 | 说明 |
|---|---|
| **装之前先试装** | 在临时 profile 里真实安装（L1）并启动加载（L2，host 与 client 两端）；你的 profile 不会被改动。通过了才提供安装 |
| **不兼容就自动修** | 逐轮套用修复规则 → 重新打包 → 再试装：只放宽宿主报出的版本声明、旧 patch 写法、schema 的 `additionalProperties`、工具的 `output` 声明、已知服务改名；修复版通过后才可安装，原包从不修改 |
| **任何入口装进来的都补测** | 不管从官方「发现」、其他市场还是命令行装入，约 1 分钟内后台自动试装一次，结果显示在插件详情页 |
| **插件目录** | 插件页「Autofit」标签：awesome 索引 + 雷达判定，每张卡片都能「Install with autofix」 |
| **静态画像** | 安装前告诉你插件类型（普通扩展 / 长驻服务 / 替代前端 / 宿主外壳）、应装进哪个 profile、对 profile 的影响（禁用或改写了哪些核心组件、是否改动沙箱与审批设置） |

## 安装

```sh
dsh plugin --profile web add dsh-autofit     # 或在插件页「Add plugin」里输入 dsh-autofit
```

DSH Desktop：在 Desktop 插件页「Add plugin」里输入 `dsh-autofit`（Desktop 只允许通过自己的界面安装插件）。

只用命令行：`npx dsh-autofit probe <插件>`（试装）· `npx dsh-autofit fix <插件>`（试装并自动修复）。

## 跨版本实测（2026-11-06，容器内、断网）

| DSH | 入口 | 检查接口 |
|---|---|---|
| 0.2.1-rc.2 · 0.2.1-rc.5 · 0.2.2-alpha.3 · 0.2.2-rc.1 | 插件页 Autofit 标签 + 添加菜单 + 详情区块 | ✅ |
| 0.1.7 · 0.2.0 | 插件页 → Autofit Installer 页面 + 详情区块 | ✅ |
| 0.1.5 | 设置 → 插件 → Autofit 标签 | ✅ |

| DSH Desktop | 内置运行时 | 实测 |
|---|---|---|
| 2.0.22-next / 2.0.22-beta.1 | 0.2.2-rc.1 | 完整 L1/L2 ✅ |
| 2.0.18 | 0.2.1-rc.2 | 完整 L1/L2 ✅ |
| 2.0.12 | 0.1.5-rc.2 | 有系统 Node 时完整 ✅，否则仅 L1 |

Desktop 的界面层（菜单与标签页）尚未完成无头自动化验证。

## 自动修复实测（DSH 0.2.1-rc.2）

9 个真实插件：**自动修好 5 个**（dsh-period-report、@kevinsales/dsh-insurance-actuary、dsh-voice-webspeech、dsh-web-access、@deepseek-harness-tui/dsh-tui 0.11.1）；dsh-vscode-workbench 在用户批准 `node-pty` 构建脚本后修好；其余 3 个如实标为"需要读代码修复"，修复版不提供安装。

## 实测中发现、官方升级指南与社区升级卡都没有记录的破坏性变更

- `@deepseek-ai/dsh-tools` 要求 JSON Schema 每个 object 节点显式写 `additionalProperties`；
- 注册工具必须声明 `output { schema, render }`；
- client 资源旧路由 `/plugins/client-assets` 移除，依赖脚本相对路径拼资源地址的插件会 404；
- 0.2.2 中 `@deepseek-ai/dsh-tools` 不再导出 `TOOL_RUNTIME_SCHEDULER`（dsh-chat-import 0.22.2 在 0.2.2-alpha.3 上加载失败，0.26.4 已修复）。

## 与雷达数据的关系

雷达的判定在 autofit 里只是参考信号：雷达的测试基线可能落后于你的 DSH 版本（实测中雷达标为"不兼容"的多个插件在新版本上可以正常加载），作者声明的版本范围也常常偏保守。以你本机的试装结果为准。
