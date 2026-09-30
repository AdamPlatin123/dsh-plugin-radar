# ADR-0005：演示站与三层预览图

日期：2026-09-27 ｜ 状态：已实施（P5–P6）

## 背景

README 36K 中四成是自动渲染的目录内容、四套统计口径并存——展示形态已到
Markdown 上限。决定挂 GitHub Pages 演示站（CurseForge 式卡片墙/筛选/详情页），
并为 9574 张卡片解决「按内容自动配预览图」。

## 决定

1. **Vite + Vue3 SPA，代码在本仓 `site/`，artifact 型 Pages 部署**
   （`actions/deploy-pages`，不用 gh-pages 分支——理由见 ADR-0004 被否方案）。
   一次性操作：仓库 Settings → Pages → Source = GitHub Actions。
2. **构建期数据烘焙，运行时零请求**：部署本身挂数据变更触发面，
   `site/scripts/build_data.py` 在 build 时把 canonical 固化进 bundle——
   无 raw CDN 单点、首屏瞬时、可离线。大表列数组压缩为独立 chunk（543KB gzip，
   仅 /browse 加载），入口 64KB gzip。
3. **三层预览图**：
   - L1 热链 `https://opengraph.githubassets.com/{run_id}/{owner}/{repo}`——
     GitHub 按仓库内容自动生成的 OG 卡（有自定义社交预览图则用之），免 API、
     零存储；`run_id` 作缓存版本串，每数据轮自然换新。lazy + no-referrer +
     固定宽高比占位防 CLS。
   - L2 兜底 `RepoTile.vue`：纯前端确定性 SVG——仓库名 FNV-1a 哈希取 12 色
     暗色板 + 首字母 + 判定色条（算法与 `scripts/tile_assets.py` 的确定性语义
     同源）。零网络零存储，OG 失效永远在线。
   - L3 精修：精选 Top50 卡头图与分类页头图 AI 生成，入
     `site/public/headers/<domain>.webp`（≤200KB/张），管线只留目录与命名约定。
4. **元数据补采**（`scripts/enrich-repos.py`，dsh-enrich/v1 sidecar）：
   与星标刷同一批 GraphQL 请求扩字段（节点计费、字段不计——配额零增量），
   分层节奏 T0 精选/策展每轮+README 首图、T1 ★≥50 日更、T2 ★≥10 周更、
   T3 长尾月更；限速感知（余量<500 睡至重置窗）。

## 被否方案

- 全量抓取 OG 卡缓存进仓：9574 图约 0.5–1GB 逼近 Pages 1GB 上限，同步与
  维护成本高；热链 + 本地兜底已覆盖其价值。
- 纯确定性 SVG 生成（全部磁贴）：稳定但「参考内容」意味最弱。
- 9000+ 详情页 Astro 预渲染：构建慢、搜索筛选仍需 hydration，工程复杂度
  高于 SPA 直载。

## 影响

dsh-radar/v1 五字段结构不动（兼容承诺）；补采字段只进 plugins-enrich sidecar。
站点 Lighthouse 目标：移动端 Performance ≥90 / A11y ≥95 / SEO ≥95。
