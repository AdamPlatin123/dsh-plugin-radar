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
cd site
python3 scripts/build_data.py --root ..   # 先烘焙数据
npm install
npm run dev                               # http://localhost:5173/dsh-plugin-radar/
npm run build                             # vue-tsc 类型检查 + vite build
```

## 数据口径

- 大表 9574 行 = `data/plugins-all.json`（dsh-radar/v1 五字段）⊕ canonical 域分类
  （13 taxonomy）⊕ bundle/PR 标记；enrich 副表 = `data/plugins-enrich.json`
  （pushed_at/avatar/lang/license/topics，有则显示）。
- 统计与 run_id 锚取 `data/latest.json`；OG 图缓存版本串 = snapshot_run_id。
- **红线**：`site/dist` 绝不含 `data/snapshots/`（1.34GB）；CI 构建断言
  dist < 60MB。

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
