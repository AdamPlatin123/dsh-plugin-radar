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
  data/latest.json                   snapshot_run_id（OG 图缓存版本串）+ runner 版本指针
                                     （统计不再取此文件的 stats，一律从 rows 现算）

产物：
  src/data/meta.ts      轻数据（统计/域元数据/精选/合集/run_id）——入口 chunk
  src/data/plugins.ts   大表（列数组压缩，~9574 行）——独立懒加载 chunk

口径约定（站点对外数字一律从最终 rows 计算，不引用 data/latest.json 的统计）：
  stats          浏览页四档判定计数（ok/incompatible/pending/untested）逐行统计
  totalIndexed   全量索引数 = len(rows)（plugins-all.json 的 plugins[] 长度）
  totalBrowsable 默认可浏览数 = rows 中 verdict=ok 的行数（浏览页默认筛选口径）
  counts         各域计数，与浏览页默认口径一致（仅统计 verdict=ok 的行）
  curatedStatus  精选/整合包条目 → 是否进入 rows（indexed）+ 真实 verdict/休眠位；
                 未进入 rows 的给出监测态回退（monitor：unlocated/gone/ambiguous，
                 由 canonical 未定位条目的 search?q=owner-name URL 精确匹配得出）
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine/lib'))
from radar.repository_identity import RepositoryIdentities, dedupe_public_rows  # noqa: E402

VERDICTS = ['ok', 'incompatible', 'pending', 'untested', 'gone', 'ambiguous', 'unlocated']
# 浏览页四档（rows 只含这四档；gone/ambiguous/unlocated 为 canonical 监测态，不进数组）
BROWSABLE_VERDICTS = VERDICTS[:4]
# canonical locate 监测态 → 站点监测档位（精选/整合包回退展示用）
LOCATE_TO_MONITOR = {'unresolved': 'unlocated', 'empty_watch': 'gone', 'ambiguous_watch': 'ambiguous'}
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


def dedupe_curated(document: dict, group_key: str, identities: RepositoryIdentities) -> dict:
    """同一策展页面每个仓库身份仅保留首次出现，保留策展文案和分组顺序。"""
    seen = set()
    groups = []
    for group in document.get(group_key) or []:
        members = []
        for member in group.get('plugins') or []:
            key = identities.resolve(member['repo']).lower()
            if key not in seen:
                seen.add(key)
                members.append(member)
        if members:
            groups.append({**group, 'plugins': members})
    return {**document, group_key: groups}


def build(root: Path, out_dir: Path | None = None):
    site = Path(__file__).resolve().parent.parent
    out_dir = out_dir or site / 'src' / 'data'
    out_dir.mkdir(parents=True, exist_ok=True)

    plugins_doc = _load(root / 'data' / 'plugins-all.json', {})
    identities = RepositoryIdentities.load(root)
    rows = dedupe_public_rows(plugins_doc.get('plugins', []), identities)
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
            k = identities.resolve(u.split('github.com/')[1].strip('/')).lower()
            # canonical 已在写入前按身份合并；兼容旧生成物时额外合并类型标签。
            if k not in entry_by_repo:
                entry_by_repo[k] = dict(e)
            elif e.get('bundle'):
                entry_by_repo[k]['bundle'] = True

    # P6 补采 sidecar（可选）
    enrich = {}
    for repo, item in _load(root / 'data' / 'plugins-enrich.json', {}).get('entries', {}).items():
        key = identities.resolve(repo).lower()
        if key not in enrich or (item.get('pushed_at') or '') > (enrich[key].get('pushed_at') or ''):
            enrich[key] = item
    skip = {identities.resolve(repo).lower() for repo in
            _load(root / 'data' / 'test-skip-list.json', {}).get('repos', [])}
    bundle_repos = {identities.resolve(m['repo']).lower()
                    for group in bundles.get('forms') or [] for m in group.get('plugins') or []}

    # ── 大表（列数组）：[repo, name, verdict, stars, desc, domain, flags] ──
    # flags 位：1=bundle 2=PR 登记 4=有 enrich 元数据 8=休眠（>30天未更新且不兼容，暂停测试）
    out_rows, missing_domain = [], 0
    for r in rows:
        repo_l = r['repo'].lower()
        e = entry_by_repo.get(repo_l) or {}
        dom = DOMAIN_TITLE2SLUG.get(e.get('domain') or '', 'other')
        if not e:
            missing_domain += 1
        flags = (1 if e.get('bundle') or repo_l in bundle_repos or '〔📦〕' in r['desc'] else 0) | (2 if r['name'] in pr_names else 0) \
            | (4 if repo_l in enrich else 0) | (8 if repo_l in skip else 0)
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

    # ── 统计从最终 rows 现算（latest.json 的统计指针是导出侧口径，与本表可能错位，
    #     站点对外数字必须与构建产物逐行可对账）──
    verdict_counts = Counter(r[2] for r in out_rows)
    total_indexed = len(out_rows)
    total_browsable = verdict_counts.get('ok', 0)

    # ── 策展名单状态：精选/整合包条目是否进入最终 rows；未进入的给出监测态回退 ──
    # 状态保留原名单的全部地址；展示名单另按身份去重，首次出现的文案与分组不变。
    curated_repos: set = set()
    for group in [*(awesome.get('categories') or []), *(bundles.get('forms') or [])]:
        for m in group.get('plugins') or []:
            if m.get('repo'):
                curated_repos.add(m['repo'].lower())
    row_by_repo = {r[0].lower(): r for r in out_rows}
    # canonical 未定位条目 url 形如 github.com/search?q=owner-name（'/' 已归一为 '-'）；
    # 仅整串精确匹配，避免误挂到同名前缀的其他条目
    monitor_by_dash = {}
    for e in canon.get('entries', []):
        u = e.get('url') or ''
        if 'search?q=' in u:
            monitor_by_dash[u.split('search?q=')[1].strip('/').lower()] = e.get('locate') or ''
    curated_status = {}
    for repo_l in sorted(curated_repos):
        r = row_by_repo.get(identities.resolve(repo_l).lower())
        if r:
            curated_status[repo_l] = {'indexed': True, 'verdict': r[2],
                                      'dormant': bool(r[6] & 8), 'monitor': None}
        else:
            locate = monitor_by_dash.get(repo_l.replace('/', '-'), '')
            curated_status[repo_l] = {'indexed': False, 'verdict': None, 'dormant': False,
                                      'monitor': LOCATE_TO_MONITOR.get(locate)}

    meta = {
        'generatedAt': plugins_doc.get('generated_at', ''),
        'runId': latest.get('snapshot_run_id') or '',
        'stats': {v: verdict_counts.get(v, 0) for v in BROWSABLE_VERDICTS},
        'totalIndexed': total_indexed,
        'totalBrowsable': total_browsable,
        'runnerLatest': (latest.get('runner_versions') or {}).get('latest', '')
        if isinstance(latest.get('runner_versions'), dict) else '',
        'domains': [{'slug': s, 'title': t} for s, t in DOMAINS],
        'featured': dedupe_curated(awesome, 'categories', identities),
        'bundles': dedupe_curated(bundles, 'forms', identities),
        'counts': {s: sum(1 for r in out_rows if r[5] == s and r[2] == 'ok')
                   for s, _ in DOMAINS},
        'curatedStatus': curated_status,
        'repoAliases': identities.aliases,
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
    missing_curated = sum(1 for s in curated_status.values() if not s['indexed'])
    print(f'[build-data] {len(out_rows)} 行（canonical 域命中 {len(out_rows) - missing_domain}，'
          f'enrich {len(enrich_rows)}）→ meta.ts + plugins.ts；run_id={meta["runId"]}')
    print(f'[build-data] 口径：totalIndexed={total_indexed} totalBrowsable={total_browsable} '
          f'（stats={dict(meta["stats"])}）；策展 {len(curated_status)} 条中 {missing_curated} 条不在 rows（已带监测态回退）')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(Path(__file__).resolve().parent.parent.parent))
    build(Path(ap.parse_args().root))
    return 0


if __name__ == '__main__':
    sys.exit(main())
