#!/usr/bin/env python3
"""enrich-repos.py — 元数据补采管线（P6）：GraphQL 批量拉 pushed_at/avatar/topics/license/language。

配额经济学（与 scripts/refresh-stars.py 共用同一批请求形态）：GraphQL 限速按节点计
（1 repository 节点 = 1 点，字段数不计）——在既有 stargazerCount 批内扩字段，
配额零增量；全量一轮 9574 仓 ÷ 50/批 ≈ 192 请求。

分层节奏（fetched_at 年龄驱动，单文件全量存储）：
  T0 精选榜 55 + 策展 24（≈79 仓）：每轮必刷，并抓 README 首图（截图画廊数据源）
  T1 ★≥50：>20h 未刷则刷
  T2 ★≥10：>6 天未刷则刷
  T3 长尾：>25 天未刷则刷
限速感知：engine/lib/radar/ghql.py（余量 <500 睡至重置窗）。

产物：
  data/enrich-cache.json     内部缓存（含 fetched_at 年龄口径）
  data/plugins-enrich.json   对外 sidecar（dsh-enrich/v1，字段只增不删承诺）
用法：GH_TOKEN=… python3 scripts/enrich-repos.py [--dry]
"""
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'engine' / 'lib'))
from radar import ghql  # noqa: E402

DRY = '--dry' in sys.argv
CACHE = ROOT / 'data' / 'enrich-cache.json'
SIDECAR = ROOT / 'data' / 'plugins-enrich.json'
BATCH = 50

# GraphQL 扩展字段（stargazerCount 保持——与星标刷同批，可互替）
FIELDS = ('stargazerCount nameWithOwner pushedAt primaryLanguage{name} '
          'licenseInfo{spdxId} repositoryTopics(first:5){nodes{topic{name}}} '
          'owner{login avatarUrl(size:96)}')

T1_STARS, T2_STARS = 50, 10
T1_AGE, T2_AGE, T3_AGE = 20 / 24, 6.0, 25.0   # 天


def _load(p, default):
    try:
        return json.loads(p.read_text(encoding='utf8'))
    except (OSError, json.JSONDecodeError):
        return default


def _hours_since(ts: str) -> float:
    try:
        t = datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except ValueError:
        return 1e9
    return (datetime.now(timezone.utc) - t).total_seconds() / 3600


def first_readme_image(token: str, repo: str):
    """README 首图 → 绝对 URL（T0 画廊数据源；仅精选/策展 ~79 仓，1 请求/仓）。"""
    import urllib.request
    req = urllib.request.Request(
        f'https://api.github.com/repos/{repo}/readme',
        headers={'Authorization': f'Bearer {token}',
                 'Accept': 'application/vnd.github.raw',
                 'User-Agent': 'dsh-plugin-radar/enrich'})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read(200_000).decode('utf8', 'replace')
    except Exception:
        return ''
    # 首个图片引用：markdown ![alt](url) 或 HTML <img src>；相对路径解析为 raw HEAD URL
    m = re.search(r'!\[[^\]]*\]\(([^)\s]+)\)', body) \
        or re.search(r'<img[^>]+src=["\']([^"\']+)["\']', body)
    if not m:
        return ''
    src = m.group(1).strip()
    if src.startswith(('http://', 'https://', 'data:')):
        return src
    src = src.lstrip('./')
    return f'https://raw.githubusercontent.com/{repo}/HEAD/{src}' 


def main() -> int:
    token = ghql.resolve_token()
    if not token:
        sys.exit('[enrich] 缺少 GH_TOKEN（且 gh auth token 不可用）')
    plugins = _load(ROOT / 'data' / 'plugins-all.json', {}).get('plugins', [])
    cache = _load(CACHE, {})
    entries = cache.get('entries', {})

    # T0 名单：精选 + 策展
    t0 = set()
    for c in _load(ROOT / 'data' / 'awesome-50.json', {}).get('categories', []):
        t0.update(m['repo'].lower() for m in c.get('plugins', []))
    for p in (ROOT / 'catalog' / 'plugins').glob('*.json'):
        d = _load(p, {})
        fn = (d.get('repository') or {}).get('full_name', '')
        if fn:
            t0.add(fn.lower())

    due, tiers = [], {'t0': 0, 't1': 0, 't2': 0, 't3': 0}
    for r in plugins:
        repo, stars = r['repo'].lower(), r.get('stars') or 0
        age_h = _hours_since((entries.get(repo) or {}).get('fetched_at', ''))
        if repo in t0:
            tier = 't0'
        elif stars >= T1_STARS and age_h > T1_AGE * 24:
            tier = 't1'
        elif stars >= T2_STARS and age_h > T2_AGE * 24:
            tier = 't2'
        elif age_h > T3_AGE * 24:
            tier = 't3'
        else:
            continue
        tiers[tier] += 1
        due.append((repo, tier))
    print(f'[enrich] 待刷 {len(due)}（{tiers}）｜缓存既有 {len(entries)}')

    n_ok = n_miss = 0
    for i in range(0, len(due), BATCH):
        batch = due[i:i + BATCH]
        nodes = ghql.gql_batch(
            [(r.split('/')[0], r.split('/')[1]) for r, _ in batch],
            token=token, fields=FIELDS)
        for repo, tier in batch:
            node = nodes.get(repo)
            if node is None:
                n_miss += 1
                continue
            topics = [t['topic']['name'] for t in
                      ((node.get('repositoryTopics') or {}).get('nodes') or []) if t.get('topic')]
            prev_img = entries.get(repo, {}).get('readme_image', '')   # 旧图先捕获（外审 P2：整条重建曾把旧图丢掉）
            entries[repo] = {
                'stars': node.get('stargazerCount'),
                'pushed_at': node.get('pushedAt') or '',
                'avatar': ((node.get('owner') or {}).get('avatarUrl') or ''),
                'lang': ((node.get('primaryLanguage') or {}) or {}).get('name') or '',
                'license': ((node.get('licenseInfo') or {}) or {}).get('spdxId') or '',
                'topics': topics[:5],
                'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            }
            if prev_img:
                entries[repo]['readme_image'] = prev_img   # 旧图回填；T0 阶段仅成功抓到新图时替换
            n_ok += 1
        print(f'[enrich] {min(i + BATCH, len(due))}/{len(due)}（本批命中 {len(nodes)}/{len(batch)}）')
        time.sleep(0.4)

    # T0 的 README 首图（画廊数据源；失败不阻断）
    n_img = 0
    for repo, tier in due:
        if tier != 't0' or repo not in entries:
            continue
        img = first_readme_image(token, repo)
        if img:
            entries[repo]['readme_image'] = img   # 仅成功时替换（外审 P2：整条覆盖曾把失败轮的旧图一并丢掉）
            n_img += 1
        elif 'readme_image' in entries[repo]:
            n_img += 1   # 沿用既有图计入覆盖统计
    print(f'[enrich] T0 README 首图 {n_img}/{tiers["t0"]}')

    if DRY:
        print('[enrich] --dry：不写盘')
        return 0

    cache_doc = {'schema': 'dsh-enrich/v1', 'updated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                 'entry_count': len(entries), 'entries': entries}
    (ROOT / 'data').mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(cache_doc, ensure_ascii=False, indent=1) + '\n', encoding='utf8')
    # 对外 sidecar：剥内部年龄口径（fetched_at），承诺字段只增不删
    sidecar_entries = {k: {kk: vv for kk, vv in v.items() if kk != 'fetched_at'}
                       for k, v in entries.items()}
    SIDECAR.write_text(json.dumps(
        {'schema': 'dsh-enrich/v1', 'generated_at': cache_doc['updated_at'],
         'entry_count': len(sidecar_entries), 'entries': sidecar_entries},
        ensure_ascii=False, indent=1) + '\n', encoding='utf8')
    print(f'[enrich] 缓存 {len(entries)} 条 → data/enrich-cache.json｜sidecar → data/plugins-enrich.json'
          f'（命中 {n_ok} · 缺失 {n_miss}）')
    return 0


if __name__ == '__main__':
    main()
