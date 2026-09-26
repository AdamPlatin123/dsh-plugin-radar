# B 线实施计划（第一批：不依赖环境的改造）

- 依据：`docs/superpowers/specs/2026-08-24-multi-axis-verdict-design.md`（含 autoplan 终门四决策）
- 代码落点：152 副本 ``~/dsh-k8s`（私有测试台，见 engine/ops/private/MANIFEST.md）`（未来部署版）；数据/schema 落本机渲染仓
- 原则：每项独立可验证；不依赖旧机（失联中）与 152 装机

## B1. 冻结自动墓碑（⑤状态机的第一步）

**改动**：`pipeline-driver.py`（152 副本）的墓碑终局路径——`classification: nonplugin` 直写改为
`classification: needs-review` 停留（新状态），只记录不生效；新增 `RADAR_TOMBSTONE_FREEZE=1` 环境开关
（默认开——部署后自动墓碑即刻停摆，人工 gate 机制另批实施）。

**涉及**：
- collect_results 的 not-published/no-plugin-structure 分支（现直降 nonplugin）
- build_repo_map 的墓碑复活段（对 needs-review 同样适用）
- current_due 过滤（needs-review 不入 due——等价于 nonplugin 的队列效果，但语义可逆、可审计）

**验证**：`py_compile` + 代码走查（旧机不可跑实例）。

## B2. 双沙箱 manifest 参数化（④的代码部分）

**改动**：`pipeline-driver.py` 的 `build_pod_manifest` 增加 `sandbox_class` 参数
（`install` | `runtime`）：
- install 类：不注入 QWEN_BASE_URL/DEEPSEEK_API_KEY 等凭证 env、无 out hostPath 回写
  （结果经独立中转）、egress 注解标注白名单意图（网络策略实施等 A 线装机）
- runtime 类：现状 + 显式凭证清单注释（当前凭证注入点逐一标注，为 A 线收紧做地图）

**涉及**：build_pod_manifest 签名/runner_env 分支/volumes 分支；dispatch 按 L 阶段选 class
（第一刀：全部 runtime，install 类待②复测轮启用——先把参数与分离面备好）。

**验证**：py_compile + 手工构造两种 manifest dry-run（在 152 上待装机后补 kubectl 服务端校验）。

## B3. legacy 哨兵基线（0.5 步）

**产出**（本机渲染仓 `data/sentinel/`）：
1. `sentinel-baseline.json`：从最新快照判定中选 ~24 个已知结论条目——
   good：npm/github/tarball/allowBuilds/web-load 各 ~4；bad：unbuilt-source/no-plugin-structure/
   clone-fail/boot-crash 各 ~2。每条含 local_key、预期结论、形态标签。
2. `sentinel-check.py`：对比 results 目录与基线——输出 mismatch 列表；exit 1 当 mismatch>0
   （供 watchdog/run 启动时调用：哨兵不符 → 拒绝墓碑与发布）。

**验证**：本机以快照数据自检（哨兵条目全部可从快照判定解析）。

## B4. 契约 v4 事件 schema 定稿（D1 事件流版）

**产出**：本机仓 `schema/event-contract-v4.md`（设计文档，实施时转 JSON Schema）：
- 三类事件：`install_attempt` / `boot_attempt` / `function_probe`（各含完整上下文：environment
  /install/provenance 字段组，即 spec §5 清单按事件重组）
- 判定不进 schema——事件是事实，五轴是派生视图（渲染层实现）
- 事件不可变：append-only，修正=新事件带 supersedes 指针
- RESULT_CONTRACT_REVISION=4 时 input_hash 锚事件流版本

**验证**：以 #2582 四个分歧插件为例做事件序列演算（dsh-context 应产出两条 install_attempt
[npm=pass, git=fail] 而非一个判定）。

## 执行序

B4 → B1 → B2 → B3（schema 先定字段，B1/B2 的注释引用它；B3 独立收尾）。
