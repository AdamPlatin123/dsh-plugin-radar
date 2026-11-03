#!/usr/bin/env python3
"""validate_contracts.py — 稳定数据接口契约校验（P0 安全网）。

对 data/latest.json 与 data/plugins-all.json 执行 schema/radar-v1.schema.json
的正式契约校验（jsonschema draft-07），另加跨文件语义断言。

设计动机：runner_versions 曾以「合法 JSON 的 API 404 错误对象」身份混入稳定接口
随渲染链发布（try/except 只防解析失败、防不住错误内容）——契约校验进 CI 后此类
事故在合入前即被拦截。

用法：python3 scripts/validate_contracts.py [repo-root]
依赖：pip install jsonschema（仅 CI/开发环境需要；引擎运行时零依赖不变）
"""
import json
import sys
from collections import Counter
from pathlib import Path

SCHEMA_FILE = 'schema/radar-v1.schema.json'
TARGETS = [
    ('data/latest.json', '#/definitions/latest'),
    ('data/plugins-all.json', '#/definitions/plugins_all'),
]


def validate(root: Path) -> int:
    try:
        import jsonschema
    except ImportError:
        print('[contracts] 缺少 jsonschema：pip install jsonschema', file=sys.stderr)
        return 3

    schema = json.loads((root / SCHEMA_FILE).read_text(encoding='utf8'))
    resolver = jsonschema.RefResolver.from_schema(schema)
    failed = False
    docs = {}
    for rel, ref in TARGETS:
        path = root / rel
        if not path.exists():
            print(f'[contracts] 缺文件：{rel}', file=sys.stderr)
            failed = True
            continue
        doc = json.loads(path.read_text(encoding='utf8'))
        docs[rel] = doc
        validator = jsonschema.Draft7Validator(
            resolver.resolve(ref)[1], resolver=resolver)
        errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
        if errors:
            failed = True
            for e in errors[:10]:
                loc = '/'.join(str(p) for p in e.absolute_path) or '<root>'
                print(f'[contracts] {rel}#{loc}: {e.message}', file=sys.stderr)
        else:
            print(f'[contracts] {rel} 契约通过（{ref}）')

    # 策展深度条目 ⊕ plugin.schema.json（曾 23/24 因 runtime_test 未入 schema 被判违规——P2a 修正后应全绿）
    plugin_schema = json.loads((root / 'schema/plugin.schema.json').read_text(encoding='utf8'))
    pv = jsonschema.Draft7Validator(plugin_schema)
    n_plugin = n_plugin_bad = 0
    for p in sorted((root / 'catalog' / 'plugins').glob('*.json')):
        n_plugin += 1
        errs = sorted(pv.iter_errors(json.loads(p.read_text(encoding='utf8'))),
                      key=lambda e: list(e.absolute_path))
        if errs:
            n_plugin_bad += 1
            for e in errs[:3]:
                print(f'[contracts] catalog/plugins/{p.name}: {e.message}', file=sys.stderr)
    if n_plugin:
        print(f'[contracts] catalog/plugins {n_plugin - n_plugin_bad}/{n_plugin} 通过（plugin.schema.json）')
        failed = failed or bool(n_plugin_bad)

    # 最新快照 ⊕ snapshot.schema.json（快照为渲染层唯一输入，坏快照即坏清单）
    import glob as _glob
    snaps = sorted(_glob.glob(str(root / 'data' / 'snapshots' / '*.json')))
    if snaps:
        snap_schema = json.loads((root / 'schema/snapshot.schema.json').read_text(encoding='utf8'))
        sv = jsonschema.Draft7Validator(snap_schema)
        doc = json.loads(Path(snaps[-1]).read_text(encoding='utf8'))
        errs = sorted(sv.iter_errors(doc), key=lambda e: list(e.absolute_path))
        if errs:
            failed = True
            for e in errs[:5]:
                print(f'[contracts] {Path(snaps[-1]).name}: {e.message}', file=sys.stderr)
        else:
            print(f'[contracts] 最新快照 {Path(snaps[-1]).name} 通过（snapshot.schema.json）')
    else:
        print('[contracts] 无快照文件，跳过快照校验')

    # 跨文件语义断言：total_listed 必须等于清单实际条数
    latest = docs.get('data/latest.json')
    plugins = docs.get('data/plugins-all.json')
    if latest and plugins:
        n_claim, n_real = latest['total_listed'], len(plugins['plugins'])
        if n_claim != n_real:
            print(f'[contracts] latest.total_listed={n_claim} 与 plugins 实际 {n_real} 不符',
                  file=sys.stderr)
            failed = True
        else:
            print(f'[contracts] 跨文件一致：total_listed={n_claim}')
        # 语义门禁：schema 合法 ≠ 数量正确——四档须与 plugins[] 逐条计数一致
        # （曾以去重前计数发布，schema 全绿但四档漂移；监测三态 gone/ambiguous/
        #   unlocated 在数组之外，不参与此对账）
        counts = Counter(p['verdict'] for p in plugins['plugins'])
        verdict_bad = False
        for verdict in ('ok', 'incompatible', 'pending', 'untested'):
            # .get 链：latest 缺 stats 键（schema 已拦）时以 None 参与比较 → 判不符，不崩栈
            claimed = latest.get('stats', {}).get(verdict)
            if claimed != counts[verdict]:
                print(f'[contracts] stats.{verdict}={claimed} 与清单实际 {counts[verdict]} 不符',
                      file=sys.stderr)
                failed = True
                verdict_bad = True
        if not verdict_bad:
            print(f'[contracts] 四档对账：ok={counts["ok"]} incompatible={counts["incompatible"]} '
                  f'pending={counts["pending"]} untested={counts["untested"]}')
        failed = check_unlocated_ratio(latest) or failed
    failed = check_data_files(root) or failed
    return 1 if failed else 0


# 聚合缓存形态门禁（2026-10-14 事故）：org→mirror 同步把 GitHub API 404 响应体当作文件
# 内容入库，四个缓存被覆盖为 127 字节错误对象，定位全失效（收录 13268→9122、
# unlocated 0→14379）。schema 只覆盖 latest/plugins-all，缓存坏了契约校验照样全绿。
# 值为必需顶层键（其中 entries 须为非空 dict）；None 表示扁平 {owner/repo: 文本}。
# 只校验存在的文件：缺文件由消费方各自的在场守卫处理，不在此判失败。
CACHE_SHAPES = {
    'data/locate-cache.json': ('resolved_at', 'entries'),
    'data/url-audit.json': ('checked_at', 'entries'),
    'data/repo-map.json': ('exported_at', 'entries'),
    'data/desc-cache.json': None,
}
# 未定位占比上限：事故前长期 0–7 条（<0.1%），事故时 14379/23484（61%）。
MAX_UNLOCATED_RATIO = 0.05


def is_api_error_object(doc) -> bool:
    """GitHub API 错误响应体特征（与 auto-snapshot-push.sh 内容门禁同口径）。"""
    return isinstance(doc, dict) and 'message' in doc and 'documentation_url' in doc


def check_data_files(root: Path) -> bool:
    """data/*.json 一律须为合法 JSON 且非 API 错误对象；聚合缓存另验形态。返回是否失败。"""
    failed = False
    for path in sorted((root / 'data').glob('*.json')):
        rel = path.relative_to(root).as_posix()
        try:
            doc = json.loads(path.read_text(encoding='utf8'))
        except (OSError, ValueError) as e:
            print(f'[contracts] {rel}: JSON 解析失败（{e}）', file=sys.stderr)
            failed = True
            continue
        if is_api_error_object(doc):
            print(f'[contracts] {rel}: 内容是 GitHub API 错误对象（message+documentation_url）'
                  f'——疑似 API 响应体误入库', file=sys.stderr)
            failed = True
            continue
        if rel not in CACHE_SHAPES:
            continue
        keys = CACHE_SHAPES[rel]
        if not isinstance(doc, dict) or not doc:
            reason = '须为非空对象'
        elif keys is None:
            reason = None if all(isinstance(v, str) for v in doc.values()) else '值须全为字符串'
        elif missing := [k for k in keys if k not in doc]:
            reason = f'缺顶层键 {missing}'
        elif not isinstance(doc['entries'], dict) or not doc['entries']:
            reason = 'entries 须为非空对象'
        else:
            reason = None
        if reason:
            print(f'[contracts] {rel}: 缓存形态不符——{reason}', file=sys.stderr)
            failed = True
    if not failed:
        print('[contracts] data/*.json 无 API 错误对象；在场聚合缓存形态通过')
    return failed


def check_unlocated_ratio(latest: dict) -> bool:
    """未定位占比超限即判失败（缓存失效的直接症状）。返回是否失败。"""
    stats = latest.get('stats', {})
    unlocated = stats.get('unlocated') or 0
    universe = (latest.get('total_listed') or 0) + unlocated + \
        (stats.get('gone') or 0) + (stats.get('ambiguous') or 0)
    ratio = unlocated / universe if universe else 0.0
    if ratio > MAX_UNLOCATED_RATIO:
        print(f'[contracts] 未定位占比 {ratio:.1%}（{unlocated}/{universe}）超过上限 '
              f'{MAX_UNLOCATED_RATIO:.0%}——定位缓存疑似失效', file=sys.stderr)
        return True
    print(f'[contracts] 未定位占比 {ratio:.2%}（{unlocated}/{universe}）')
    return False


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
    return validate(root)


if __name__ == '__main__':
    raise SystemExit(main())
