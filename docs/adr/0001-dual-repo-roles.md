# 双仓角色正名：清单仓 + 管线仓

雷达生态由两个仓库构成，历史上以「主仓（org）/镜像（mirror）」称呼，但事实权威早已漂移：社区登记 PR 全部合并在个人仓。2026-08-27 正名：**AdamPlatin123/awesome-dsh-plugins = 清单仓**（社区登记 PR 的合并地、PLUGINS.md 权威登记表、面向读者的门面）；**dsh-external/awesome-dsh-plugins = 管线仓**（快照生产、渲染源、测试档案）。数据流为管线仓→清单仓单向同步（快照/缓存/渲染脚本），登记表只在清单仓维护。两机 remote 命名统一为 front（清单仓）/ data（管线仓），org 仓内 2026-08-21 前的旧 PLUGINS.md 头部加指向指引后不再维护。

> **2026-09-27 修订**：角色正名维持，另增第三仓——引擎镜像仓（AdamPlatin123/dsh-plugin-radar）：引擎开源副本 + 站点宿主 + 管线数据镜像（org→mirror）。详见 CONTEXT.md「三仓角色」。
