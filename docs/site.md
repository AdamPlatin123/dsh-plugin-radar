# 站点（docs/site.md）

> 演示站 `https://adamplatin123.github.io/dsh-plugin-radar/` 的开发与运维说明。
> 决策依据见 [ADR-0005](adr/0005-site-and-og-images.md)。

## 结构

```
site/
├── scripts/build_data.py   # 构建期数据烘焙（canonical → src/data/*.ts）
├── src/
│   ├── lib/data.ts         # 大表 chunk 动态加载 + 筛选
│   ├── lib/og.ts           # OG 热链 URL + FNV 磁贴算法
│   ├── components/         # 卡片/徽章/磁贴/虚拟网格/筛选栏…
│   ├── views/              # 首页/浏览/详情/精选/合集/关于（全懒加载）
│   └── data/               # 生成物（gitignore，勿手改）
└── public/headers/         # L3 AI 头图（<domain>.webp，≤200KB/张；人工生成放入）
```

## 本地开发

```bash
cd /mnt/shared/_Projects/DSH-Plugin-Radar/site
python3 /mnt/shared/_Projects/DSH-Plugin-Radar/site/scripts/build_data.py --root /mnt/shared/_Projects/DSH-Plugin-Radar   # 先烘焙数据
npm install
npm run dev                               # http://localhost:5173/dsh-plugin-radar/
npm run build                             # vue-tsc 类型检查 + vite build
```

## 数据口径

- 大表全量行 = `data/plugins-all.json`（dsh-radar/v1 五字段）⊕ canonical 域分类
  （13 taxonomy）⊕ bundle/PR 标记；enrich 副表 = `data/plugins-enrich.json`
  （pushed_at/avatar/lang/license/topics，有则显示），键 = 大表行号，
  与 flags 位 4 严格对齐（回归测试守护，防评审 P1 的元数据错位复发）。
- **对外数字一律从最终 rows 现算**，不引用 `data/latest.json` 的统计指针
  （导出侧口径可能与本表错位）：`stats` 四档逐行计数；
  `totalIndexed` = 全量收录数（len(rows)）；`totalBrowsable` = ok 行数
  （浏览页默认筛选「运行级可用」，可切判定筛选看全量）；`counts` 各域计数
  与浏览页默认口径一致（仅 ok）。`latest.json` 仅取 `snapshot_run_id`
  （OG 图缓存版本串）与 `runner_versions.latest`（实测基线）。
- **策展回退**：`meta.curatedStatus` 记录精选/整合包每条是否进入 rows
  （indexed）及真实 verdict/休眠位；未进入的条目视图渲染「监测态
  （unlocated/gone/ambiguous，取自 canonical 未定位记录）+ 源 GitHub 仓回退」，
  不路由到详情页 404，也不从策展名单中抹除。
- **红线**：`site/dist` 绝不含 `data/snapshots/`（1.34GB）；CI 构建断言
  dist < 60MB。

## 回归测试

```bash
python3 /mnt/shared/_Projects/DSH-Plugin-Radar/site/scripts/test_build_data.py   # 站点烘焙不变量（离线 fixture，13 例）
```

覆盖：全量行不被 verdict 过滤、enrich 键与 flags 对齐且逐行归属正确、
统计从 rows 现算而非 latest 指针、totalIndexed/totalBrowsable 分离、
curatedStatus 与 rows 对账（indexed ⇔ 在表内）及未索引条目监测态回退、
策展名单原样透传。

## 部署与回滚

- 部署：`.github/workflows/site-build-deploy.yml`（artifact 型；触发面 =
  数据落地点 + `site/**`，每日 22:37 UTC 兜底）。
- 回滚：Actions 页面 → site-build-deploy → 上一成功 run → Re-run / Re-deploy
  上一 artifact（秒级，不碰代码）。
- 前置一次性配置：Settings → Pages → Source = **GitHub Actions**。

## 预览图三层

1. OG 热链（免 API，按仓库内容自动生成）
2. RepoTile 确定性磁贴（FNV 哈希 12 色暗色板 + 首字母 + 判定色条）
3. `public/headers/<domain>.webp` AI 头图（人工生成，命名即约定）
