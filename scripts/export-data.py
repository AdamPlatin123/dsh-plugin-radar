#!/usr/bin/env python3
"""export-data.py — 稳定数据接口导出（issue #252；P1 起改从 canonical 直出）。

历史：本文件曾用三条正则（ROW_RE/STAT_RE/ANCHOR_RE）从渲染后的 PLUGINS-ALL.md 与
catalog/all/*.md 反向解析——给人看的 Markdown 成了机器接口的事实上游，四套统计口径
漂移的根源之一。P1 数据层收敛后，导出改读 generated/current/canonical.json 的
export 段（build_canonical 预计算：行序=域文件字典序×组内排序，stats=旧正则
「后值覆盖」语义的等价直算），与旧路径逐字段一致；canonical 缺失时自动先跑 build。

  --from-markdown  走旧正则路径，仅用于等价性验收对照（新旧并跑 diff）。

口径承诺（schema dsh-radar/v1，权威契约 schema/radar-v1.schema.json，CI 经
scripts/validate_contracts.py 校验）：字段只增不删；stars 为 null 表示未知
（不参与排序的缺值，非 0）；verdict ∈ ok/incompatible/pending/untested/gone/
ambiguous/unlocated（与 PLUGINS-ALL 判定档位一一对应）。

用法：python3 scripts/export-data.py [repo-root] [--from-markdown]（渲染链每次提交后调用）
"""
import json
import re
import sys
import time
from pathlib import Path

SCHEMA = 'dsh-radar/v1'
VERDICT_MAP = {
    '可用': 'ok', '不兼容': 'incompatible', '待定': 'pending', '未测': 'untested',
    '空仓监测': 'gone', '歧义监测': 'ambiguous', '未定位': 'unlocated',
}
ROW_RE = re.compile(
    r'^- (?:[^\[`]* )?`\[([^\]]+)\]` \[([^\]]+)\]\((https://github\.com/[^\s)]+)\)(?: (★?\d+))?(?: — ?(.*))?$')
STAT_RE = re.compile(r'`\[([^\]]+)\]`（(\d+)）')
ANCHOR_RE = re.compile(r'`(\d{8}T\d{6}Z)`')


def from_markdown(root: Path):
    """旧路径：正则反解析渲染产物（验收对照用，勿在新链路调用）。"""
    text = (root / 'PLUGINS-ALL.md').read_text(encoding='utf8')
    domain_texts = sorted((root / 'catalog' / 'all').glob('*.md'))
    rows_text = '\n'.join(p.read_text(encoding='utf8') for p in domain_texts) if domain_texts else text
    stats = {VERDICT_MAP[k]: int(v) for k, v in STAT_RE.findall(text)}
    anchor = ANCHOR_RE.search(text)
    plugins = []
    for line in rows_text.splitlines():
        m = ROW_RE.match(line.strip())
        if not m:
            continue
        verdict_cn, name, url, stars, desc = m.groups()
        plugins.append({
            'repo': url.split('github.com/')[1],
            'name': name,
            'verdict': VERDICT_MAP.get(verdict_cn, verdict_cn),
            'stars': int(stars.lstrip('★')) if stars else None,
            'desc': (desc or '').strip(),
        })
    _dedupe_arbitrate(plugins)
    return stats, plugins, (anchor.group(1) if anchor else None)


def _dedupe_arbitrate(plugins):
    """同仓多键去重 + 判定仲裁（codex 评审 #4；canonical 路径已天然唯一，此处仅供旧路径）。"""
    _by = {}
    for p in plugins:
        k = p['repo'].lower()
        if k in _by:
            prev = _by[k]
            if prev['verdict'] != p['verdict'] and {prev['verdict'], p['verdict']} & {'ok', 'incompatible'}:
                prev['verdict'] = 'pending'   # 互斥冲突降待定（对齐 gen_plugins_all 仲裁规则）
            if (p['stars'] or 0) > (prev['stars'] or 0):
                prev['stars'] = p['stars']
        else:
            _by[k] = p
    plugins[:] = list(_by.values())
    _keys = [p['repo'].lower() for p in plugins]
    assert len(_keys) == len(set(_keys)), f'导出仓库键不唯一: {len(_keys)} 行 {len(set(_keys))}'


def from_canonical(root: Path):
    """新路径：canonical.export 段直出（顺序与口径在 build_canonical 内与旧正则等价计算）。"""
    canon_path = root / 'generated' / 'current' / 'canonical.json'
    if not canon_path.is_file():
        sys.path.insert(0, str(root / 'engine' / 'aggregation'))
        from build_canonical import build
        build(root)
    doc = json.loads(canon_path.read_text(encoding='utf8'))
    export = doc['export']
    plugins = [dict(r) for r in export['rows']]
    _keys = [p['repo'].lower() for p in plugins]
    assert len(_keys) == len(set(_keys)), f'导出仓库键不唯一: {len(_keys)} 行 {len(set(_keys))}'
    return export['stats'], plugins, export['anchor_run_id']


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    legacy = '--from-markdown' in sys.argv
    root = Path(args[0]) if args else Path('.')
    stats, plugins, anchor = from_markdown(root) if legacy else from_canonical(root)

    try:
        runner_versions = json.loads((root / 'data' / 'runner-versions.json').read_text(encoding='utf8'))
        # 出口门禁：API 错误对象是合法 JSON，try/except 防不住——稳定接口绝不发布错误内容
        if isinstance(runner_versions, dict) and 'message' in runner_versions and 'documentation_url' in runner_versions:
            print('[export] WARN runner-versions.json 为 API 错误对象，按空处理', file=sys.stderr)
            runner_versions = {}
    except Exception:
        runner_versions = {}
    latest = {
        'schema': SCHEMA,
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'snapshot_run_id': anchor,
        'stats': stats,
        'total_listed': len(plugins),
        'runner_versions': runner_versions,
        'data': {
            'plugins_all': 'data/plugins-all.json',
            'snapshots_dir': 'data/snapshots/',
        },
    }
    (root / 'data').mkdir(exist_ok=True)
    (root / 'data' / 'latest.json').write_text(
        json.dumps(latest, ensure_ascii=False, indent=1) + '\n', encoding='utf8')
    (root / 'data' / 'plugins-all.json').write_text(
        json.dumps({'schema': SCHEMA, 'generated_at': latest['generated_at'], 'plugins': plugins},
                   ensure_ascii=False, indent=1) + '\n', encoding='utf8')
    print(f'[export] latest.json 统计={stats}｜plugins-all.json {len(plugins)} 条'
          f'（{"旧正则对照" if legacy else "canonical 直出"}）')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
