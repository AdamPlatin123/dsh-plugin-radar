#!/usr/bin/env python3
"""build_data.py — 站点数据烘焙（P5）：仓库数据 → site/src/data/*.ts，构建期打进 bundle。

运行时零请求：站点部署本身挂数据变更触发面（site-build-deploy.yml 的 paths 过滤），
数据在 build 时固化，无 raw.githubusercontent 单点、首屏瞬时、可离线。

数据源（相对仓库根，参数 --root 默认上级目录）：
  generated/current/canonical.json   域分类（13 taxonomy）与 bundle/PR 标记（缺失时自动现算）
  data/plugins-all.json              dsh-radar/v1 全量清单（repo/name/verdict/stars/desc）
  data/plugins-enrich.json           P6 补采 sidecar（可选；pushed_at/avatar/topics/…）
  data/awesome-50.json               精选榜（11 类人工策展）
  data/bundles.json                  合集
  data/latest.json                   统计指针 + snapshot_run_id（OG 图缓存版本串）

产物：
  src/data/meta.ts      轻数据（统计/域元数据/精选/合集/run_id）——入口 chunk
  src/data/plugins.ts   大表（列数组压缩，~9574 行）——独立懒加载 chunk
"""
import argparse
import json
import sys
from pathlib import Path

VERDICTS = ['ok', 'incompatible', 'pending', 'untested', 'gone', 'ambiguous', 'unlocated']
# canonical 13 域（渲染顺序 = PLUGINS-ALL 口径）；slug 供 URL/键
DOMAINS = [
    ('skill', '🎓 技能包'), ('memory', '🧠 记忆增强'), ('skin', '🎨 主题皮肤'),
    ('market', '🛒 市场与管理'), ('webui', '🔌 Web UI 增强'), ('coding', '💻 编码开发'),
    ('agent', '🤖 Agent 能力'), ('comm', '📡 消息通讯'), ('data', '🗂 文件数据'),
    ('fun', '🎮 娱乐生活'), ('infra', '🛠 基建部署'), ('edu', '📚 学习研究'),
    ('other', '❓ 其他'),
]
DOMAIN_TITLE2SLUG = {t: s for s, t in DOMAINS}


def _load(p: Path, default):
    try:
        return json.loads(p.read_text(encoding='utf8'))
    except (OSError, json.JSONDecodeError):
        return default


def build(root: Path):
    site = Path(__file__).resolve().parent.parent
    out_dir = site / 'src' / 'data'
    out_dir.mkdir(parents=True, exist_ok=True)

    plugins_doc = _load(root / 'data' / 'plugins-all.json', {})
    rows = plugins_doc.get('plugins', [])
    latest = _load(root / 'data' / 'latest.json', {})
    awesome = _load(root / 'data' / 'awesome-50.json', {})
    bundles = _load(root / 'data' / 'bundles.json', {})

    # canonical（缺失时现场重算——CI 的渲染链先跑 gen_plugins_all 时已产）
    canon_path = root / 'generated' / 'current' / 'canonical.json'
    if not canon_path.is_file():
        sys.path.insert(0, str(root / 'engine' / 'aggregation'))
        sys.path.insert(0, str(root / 'engine' / 'lib'))
        from build_canonical import build as build_canonical
        build_canonical(root)
    canon = _load(canon_path, {})
    entry_by_repo, pr_names = {}, set(canon.get('pr_names') or [])
    for e in canon.get('entries', []):
        u = e.get('url') or ''
        if 'github.com/' in u and 'search?q=' not in u:
            k = u.split('github.com/')[1].strip('/').lower()
            # 先见者胜（与导出首条仲裁同向；已知限制：同仓多 canonical 条目时
            # name/desc/域取先见者而非逐字段仲裁，影响 ≤14 仓的展示分类，根治在
            # canonical 层合并——二轮外审 P2 注记）
            if k not in entry_by_repo:
                entry_by_repo[k] = e

    # P6 补采 sidecar（可选）
    enrich = _load(root / 'data' / 'plugins-enrich.json', {}).get('entries', {})

    # ── 大表（列数组）：[repo, name, verdict, stars, desc, domain, flags] ──
    # flags 位：1=bundle 2=PR 登记 4=有 enrich 元数据
    out_rows, missing_domain = [], 0
    for r in rows:
        repo_l = r['repo'].lower()
        e = entry_by_repo.get(repo_l) or {}
        dom = DOMAIN_TITLE2SLUG.get(e.get('domain') or '', 'other')
        if not e:
            missing_domain += 1
        flags = (1 if e.get('bundle') else 0) | (2 if r['name'] in pr_names else 0) \
            | (4 if repo_l in enrich else 0)
        out_rows.append([r['repo'], r['name'], r['verdict'],
                         r['stars'] if r['stars'] is not None else -1,
                         r['desc'], dom, flags])

    # ── enrich 副表（仅 flags&4 的行；键=行序 → 元数据紧凑数组）──
    enrich_rows = {}
    for i, r in enumerate(rows):
        en = enrich.get(r['repo'].lower())
        if en:
            enrich_rows[i] = [en.get('pushed_at') or '', en.get('avatar') or '',
                              en.get('lang') or '', en.get('license') or '',
                              list(en.get('topics') or [])[:5]]

    stats = latest.get('stats', {})
    meta = {
        'generatedAt': plugins_doc.get('generated_at', ''),
        'runId': latest.get('snapshot_run_id') or '',
        'stats': {k: stats.get(k, 0) for k in VERDICTS},
        'totalListed': latest.get('total_listed', len(rows)),
        'runnerLatest': (latest.get('runner_versions') or {}).get('latest', '')
        if isinstance(latest.get('runner_versions'), dict) else '',
        'domains': [{'slug': s, 'title': t} for s, t in DOMAINS],
        'featured': awesome,
        'bundles': bundles,
        'counts': {s: sum(1 for r in out_rows if r[5] == s) for s, _ in DOMAINS},
    }

    (out_dir / 'meta.ts').write_text(
        '// 构建期生成（site/scripts/build_data.py）——勿手改\n'
        'export const meta = ' + json.dumps(meta, ensure_ascii=False, separators=(',', ':')) + '\n',
        encoding='utf8')
    (out_dir / 'plugins.ts').write_text(
        '// 构建期生成（site/scripts/build_data.py）——勿手改；列数组压缩，独立 chunk 懒加载\n'
        'export const K = ["repo","name","verdict","stars","desc","domain","flags"] as const\n'
        'export const ROWS: (string | number)[][] = '
        + json.dumps(out_rows, ensure_ascii=False, separators=(',', ':')) + '\n'
        'export const ENRICH: Record<number, [string, string, string, string, string[]]> = '
        + json.dumps(enrich_rows, ensure_ascii=False, separators=(',', ':')) + '\n',
        encoding='utf8')
    print(f'[build-data] {len(out_rows)} 行（canonical 域命中 {len(out_rows) - missing_domain}，'
          f'enrich {len(enrich_rows)}）→ meta.ts + plugins.ts；run_id={meta["runId"]}')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(Path(__file__).resolve().parent.parent.parent))
    build(Path(ap.parse_args().root))
    return 0


if __name__ == '__main__':
    sys.exit(main())
