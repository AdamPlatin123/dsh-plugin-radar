# 数据接口（For Marketplaces & 下游消费方）

欢迎插件市场、聚合站与社区清单（dsh-market、dshfind、awesome 列表等）**引用本雷达的运行级可用性数据**。两个稳定 JSON 接口，无需申请、无需 key，署名即可。

## 端点

| 文件 | 内容 | 体积 | 更新节奏 |
|---|---|---:|---|
| [`data/latest.json`](../data/latest.json) | 快照指针 + 四档统计（轮询友好，小文件） | <1KB | 每轮快照（约 15 分钟） |
| [`data/plugins-all.json`](../data/plugins-all.json) | **已定位**扁平清单（repo / verdict / stars / desc；监测/未定位仅入统计不入数组） | ~2MB | 每轮渲染提交后 |

Raw 直链模式：

```
https://raw.githubusercontent.com/AdamPlatin123/dsh-plugin-radar/main/data/latest.json
https://raw.githubusercontent.com/AdamPlatin123/dsh-plugin-radar/main/data/plugins-all.json
```

（CDN 回退可换 `https://cdn.jsdelivr.net/gh/AdamPlatin123/dsh-plugin-radar@main/data/...`）

## Schema（`dsh-radar/v1`）

**latest.json**

```json
{
  "schema": "dsh-radar/v1",
  "generated_at": "2026-10-02T00:00:00Z",
  "snapshot_run_id": "20261001T174501Z",
  "stats": {"ok": 8351, "incompatible": 3156, "pending": 1814, "untested": 41,
             "gone": 842, "ambiguous": 105, "unlocated": 1},
  "total_listed": 13362,
  "runner_versions": {},
  "data": {
    "plugins_all": "data/plugins-all.json",
    "snapshots_dir": "data/snapshots/"
  }
}
```

上例仅说明结构，不承诺当前数量或生成时间。`total_listed` 等于已定位且按仓库去重后的 `plugins[]` 长度，也等于四档 `ok + incompatible + pending + untested` 之和。`gone/ambiguous/unlocated` 为数组外监测计数，不参与该加总。版本源不可用时 `runner_versions` 为空对象，不应推断测试版本。

**plugins-all.json**（`plugins[]` 数组，每条）

```json
{"repo": "owner/name", "name": "显示名", "verdict": "ok",
 "stars": 48288, "desc": "一句话描述"}
```

- `verdict ∈ ok | incompatible | pending | untested | gone | ambiguous | unlocated`
  （运行级四档 + 定位监测三态；当前已定位明细数组含前四档，监测三态单独计数。`ok` 为历史归并中的可用结论，不能解释为已在全局最新 runner 下验证。）
- `stars` 为 `null` 表示未知（缺值，非 0）
- **口径承诺**：字段只增不删；判定真相以 `data/snapshots/` 逐轮快照为准（本接口为多轮并集归并口径）

发布说明：2026-10-02 维护修复将四档统计改为在最终仓库去重和冲突仲裁之后计数，字段名和数组结构不变，数量与明细逐条对账。公开接口尚未为每条记录提供完整的插件 commit、测试版本、时间和日志；全局版本指针不能替代逐条证据。

## 徽章（单插件可用性磁贴）

仓内三态磁贴资产可直接热链（版本号随 runner 升级自动换新）：

```
https://raw.githubusercontent.com/AdamPlatin123/dsh-plugin-radar/main/assets/tile-ok.svg      🟩已兼容
https://raw.githubusercontent.com/AdamPlatin123/dsh-plugin-radar/main/assets/tile-adapt.svg   🟨需适配
https://raw.githubusercontent.com/AdamPlatin123/dsh-plugin-radar/main/assets/tile-test.svg    ⬜待测试
```

动态 shields 端点徽章（市场侧自托管 JSON 时）：

```markdown
![radar](https://img.shields.io/endpoint?url=<你的-endpoint.json>)
```

endpoint.json 遵循 shields schema：`{"schemaVersion": 1, "label": "radar", "message": "已兼容", "color": "brightgreen", "labelColor": "#97CA00"}`

## 接入三行示例

```python
import json, urllib.request
d = json.load(urllib.request.urlopen(
    "https://raw.githubusercontent.com/AdamPlatin123/dsh-plugin-radar/main/data/plugins-all.json"))
verdict = {p["repo"]: p["verdict"] for p in d["plugins"]}
print(verdict.get("omdsh-dev/DSH-better-sidebar"))   # → 'ok'
```

## 署名与许可

- 数据与代码均为 MIT；引用时建议标注「兼容性数据来自 [DSH Plugin Radar](https://github.com/AdamPlatin123/dsh-plugin-radar)」并链接快照 `run_id` 以锚定轮次
- 收录 ≠ 兼容 ≠ 运行可用 ≠ 安全审计——请在市场侧保留此口径提示
- 判定为 `incompatible` 的多数属「需构建授权」类（allowBuilds），并非插件损坏，展示时建议区分

## 快照窗口口径（2026-09-27 起）

`data/snapshots/` 保留 30 天窗口；更早轮次固化于 `data/snapshot-baseline.json`
（并集，含轮次元信息）。回溯性以基线保证；每季度重固化。

## 补采 sidecar：data/plugins-enrich.json（dsh-enrich/v1）

键同 plugins-all 的 repo；字段：`stars / pushed_at / avatar / lang / license /
topics(≤5) / readme_image(仅精选与策展仓)`。与全量清单正交、字段只增不删；
由 `enrich-metadata` 工作流日更（与星标刷同批 GraphQL，配额零增量）。

## 休眠名单：data/test-skip-list.json（radar-test-skip/v1）

`repos` 为 repo 全名小写数组（判定口径见 CONTEXT.md「休眠测试策略」）；
enrich-metadata 工作流日更刷新。测试调度方可据此跳过派发。
