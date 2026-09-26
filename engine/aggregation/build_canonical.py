#!/usr/bin/env python3
"""build_canonical.py — 统一聚合器：全部数据源 → generated/current/canonical.json。

P1 数据层收敛：原先埋在 scripts/gen_plugins_all.py main() 的数据半场（快照装载 /
canonical 归并 / 定位复核 / 登记兜底 / 改名跟随 / desc 回填重分类 / 统计）整体上移至此，
渲染半场在 engine/rendering/render_all.py，导出半场在 scripts/export-data.py——
三者共享 canonical.json 这一个事实源，Markdown 不再被反向解析。

快照装载（ADR-0002 落地）：基线 ⊕ 30 天窗口。data/snapshot-baseline.json 承载窗口外
全部历史轮的 (name,url) 合并条目与轮次元信息；无基线文件时自动回退全量扫描（与旧管线
行为一致，保证基线生成前后产物逐字节等价）。装载 IO 从 567 文件降为窗口数。

验收铁律：canonical ⊕ render_all 的 PLUGINS-ALL.md / catalog/all/*.md 与旧管线逐字节
一致；export-data 从 canonical 直出的 latest.json / plugins-all.json 与旧正则解析
逐字段一致（generated_at 除外）。
"""
import glob
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from radar.atomicio import atomic_write_json  # noqa: E402
from radar.sanitize import sanitize_desc, sanitize_name, url_guard  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
SNAP_DIR = ROOT / 'data' / 'snapshots'
BASELINE = ROOT / 'data' / 'snapshot-baseline.json'
LOCATE_CACHE = ROOT / 'data' / 'locate-cache.json'
DESC_CACHE = ROOT / 'data' / 'desc-cache.json'
REPO_MAP = ROOT / 'data' / 'repo-map.json'
URL_AUDIT = ROOT / 'data' / 'url-audit.json'
OUT = ROOT / 'generated' / 'current' / 'canonical.json'
WINDOW_DAYS = 30

REAL_URL_RE = re.compile(r'github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)')
CONFLICTING_VERDICTS = ('✅ 运行级可用', '❌ 运行级不兼容')

sys.path.insert(0, str(ROOT / 'scripts'))
from classify import classify  # noqa: E402


def bj(iso):
    """ISO 时间串 → 北京时间（UTC+8）；带时区偏移的输入按原偏移换算，避免二次加 8。"""
    dt = datetime.fromisoformat(str(iso).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M') + ' UTC+8'


def _read_json_safe(p, default):
    """缓存文件损坏（截断/无效 UTF-8/坏 JSON）时降级返回默认值，不阻断清单生成。"""
    try:
        return json.loads(Path(p).read_text())
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return default


def _merge_snapshot_files(files, merged, rounds):
    """files 须为新→旧序；(name,url) 同键以最新轮覆盖（setdefault），返回读取的文件数。"""
    n = 0
    for fp in files:
        try:
            d = json.loads(Path(fp).read_text())
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            continue   # 单文件截断/损坏跳过（镜像仓实测案例），不阻断清单生成
        if not str(d.get('schema', '')).startswith('radar-snapshot/'):
            continue
        n += 1
        rounds.append((d['run_id'], d.get('generated_at', '')))
        for e in d.get('catalog_entries') or []:
            merged.setdefault((e['name'], e.get('url', '')), dict(e))
    return n


def load_entries():
    """全部数据装载：现存快照全扫（新→旧）⊕ 基线补被裁历史。

    裁剪（rebaseline --prune）把 IO 边界交给磁盘：窗口外文件删除、其信息并入
    data/snapshot-baseline.json；本函数读现存全部文件 + 基线条目垫底（setdefault，
    现存总是更新）、基线轮次去重后续接（基线轮次恒旧于现存滞留文件）。
    无基线文件时退化为旧 load_snapshots() 全量行为（逐字节一致）。

    返回 (合并条目列表[保持旧管线遭遇序], [轮次(run_id, generated_at)], 读取文件数)。
    """
    files = sorted(glob.glob(str(SNAP_DIR / '*.json')), reverse=True)
    merged, rounds = {}, []
    n = _merge_snapshot_files(files, merged, rounds)
    if BASELINE.is_file():
        base = _read_json_safe(BASELINE, {}) or {}
        seen_rids = {rid for rid, _ in rounds}
        rounds += [tuple(r) for r in base.get('rounds', []) if r[0] not in seen_rids]
        for e in base.get('entries', []):
            merged.setdefault((e['name'], e.get('url', '')), dict(e))
    return list(merged.values()), rounds, n


def canonical_key(e, repo_map, locate):
    """条目 → 规范主键。真实 URL > repo-map local_key > locate-cache；均无则退回原始键。"""
    url = e.get('url') or ''
    if 'search?q=' not in url:
        m = REAL_URL_RE.search(url)
        if m:
            return ('repo', f"{m.group(1)}/{m.group(2)}".lower())
    name = e['name']
    r = repo_map.get(name)
    if r and r.get('full_name'):
        return ('repo', r['full_name'].lower())
    lc = locate.get(name) or {}
    if lc.get('status') == 'found' and lc.get('full_name'):
        return ('repo', lc['full_name'].lower())
    return ('raw', name.lower(), url)


def _ok_desc(d):
    d = (d or '').strip()
    return bool(d) and d != '—' and not d.startswith('http')


def merge_entry(a, b):
    """同 canonical 的更旧轮次 b 补齐/仲裁 a：URL 取真实、star 取大、desc 取有效、判定冲突降待定。"""
    out = dict(a)
    if 'search?q=' in (out.get('url') or '') and 'search?q=' not in (b.get('url') or ''):
        out['url'] = b['url']
    if (out.get('star') or 0) < (b.get('star') or 0):
        out['star'] = b['star']
    if not out.get('bundle') and b.get('bundle'):
        out['bundle'] = b['bundle']
    if not _ok_desc(out.get('desc')) and _ok_desc(b.get('desc')):
        out['desc'] = b['desc']
    if not out.get('domain') and b.get('domain'):
        out['domain'] = b['domain']
    va, vb = out.get('verdict'), b.get('verdict')
    if va != vb:
        if vb in CONFLICTING_VERDICTS and va not in CONFLICTING_VERDICTS:
            out['verdict'] = vb
        elif va in CONFLICTING_VERDICTS and vb not in CONFLICTING_VERDICTS:
            pass
        elif va in CONFLICTING_VERDICTS and vb in CONFLICTING_VERDICTS:
            out['verdict'] = '⚠️ 待定'
            out['verdict_conflict'] = f'{va} ↔ {vb}'
    return out


def canonical_merge(entries, repo_map, locate):
    """按 canonical 主键归并（装载产出的条目序近似新→旧）。返回 (归并条目, 统计)。"""
    groups, order, plain = {}, [], {}
    for e in entries:
        k = canonical_key(e, repo_map, locate)
        if k not in groups:
            groups[k] = dict(e)
            order.append(k)
        else:
            groups[k] = merge_entry(groups[k], e)
        if k[0] == 'repo':
            repo_part = k[1].split('/')[1]
            if e['name'].lower() == repo_part:
                plain.setdefault(k, e['name'])
    final = []
    for k in order:
        g = groups[k]
        if k in plain:
            g['name'] = plain[k]
        final.append(g)
    n_dedup = len(entries) - len(final)
    n_conflict = sum(1 for g in final if g.get('verdict_conflict'))
    return final, (n_dedup, n_conflict)


def pr_registered_names():
    names = set()
    for fp in glob.glob(str(ROOT / 'catalog' / 'plugins' / '*.json')):
        d = _read_json_safe(fp, None)
        if not isinstance(d, dict):
            continue
        full = d.get('repository', {}).get('full_name', '')
        if full:
            names.add(full.split('/')[-1])
    return names


def vc_local(entries, dom, verdict):
    return sum(1 for e in entries if e.get('domain') == dom and e.get('locate') == 'located'
               and e.get('verdict') == verdict)


DOMAIN_ORDER = ['🎓 技能包', '🧠 记忆增强', '🎨 主题皮肤', '🛒 市场与管理',
                '🔌 Web UI 增强', '💻 编码开发', '🤖 Agent 能力', '📡 消息通讯',
                '🗂 文件数据', '🎮 娱乐生活', '🛠 基建部署', '📚 学习研究', '❓ 其他']

# 导出契约映射（与 scripts/export-data.py 的 VERDICT_MAP/MARK 同源；标注见该文件）
EXPORT_VERDICT = {'✅ 运行级可用': 'ok', '❌ 运行级不兼容': 'incompatible',
                  '⚠️ 待定': 'pending', '⏳ 未测': 'untested'}


def build(root: Path = ROOT):
    """执行全部数据阶段，写 generated/current/canonical.json 并返回 canonical 文档。"""
    entries, rounds, n_files = load_entries()
    locate = (_read_json_safe(LOCATE_CACHE, {}) or {}).get('entries', {}) if LOCATE_CACHE.exists() else {}
    repo_map = (_read_json_safe(REPO_MAP, {}) or {}).get('entries', {}) if REPO_MAP.exists() else {}
    desc_cache = _read_json_safe(DESC_CACHE, {}) if DESC_CACHE.exists() else {}
    url_audit = (_read_json_safe(URL_AUDIT, {}) or {}).get('entries', {}) if URL_AUDIT.exists() else {}
    pr_names = pr_registered_names()

    entries, (n_dedup, n_conflict) = canonical_merge(entries, repo_map, locate)

    # 实时 star 映射（locate-cache 的 full_name → stargazerCount），对全部已定位条目生效
    live_star = {r['full_name'].lower(): r['star'] for r in locate.values()
                 if r.get('status') == 'found' and r.get('full_name') and isinstance(r.get('star'), int)}

    n_fix = n_empty = n_amb = n_unresolved = n_star = 0
    for e in entries:
        if 'search?q=' in (e.get('url') or ''):
            r = locate.get(e['name'], {})
            if r.get('status') == 'found':
                e['url'] = f"https://github.com/{r['full_name']}"
                e['locate'] = 'located'
                n_fix += 1
            elif r.get('status') == 'not_found':
                e['locate'] = 'empty_watch'
                n_empty += 1
            elif r.get('status'):
                e['locate'] = 'ambiguous_watch'
                n_amb += 1
            else:
                e['locate'] = 'unresolved'   # 新占位且无复核缓存
                n_unresolved += 1
        else:
            e['locate'] = 'located'
        # 消亡仓库降级（url-audit 判 gone：已删除/改名/转私有 → 空仓监测，不呈现链接）
        m0 = REAL_URL_RE.search(e.get('url') or '')
        if e['locate'] == 'located' and m0 \
                and url_audit.get(f"{m0.group(1)}/{m0.group(2)}".lower(), {}).get('status') == 'gone':
            e['locate'] = 'empty_watch'
            n_empty += 1
        # 实时 star 覆盖（含真实 URL 条目与合并条目；快照层 star 陈旧或为 0）
        m = REAL_URL_RE.search(e.get('url') or '')
        if m:
            ls = live_star.get(f"{m.group(1)}/{m.group(2)}".lower())
            if ls is not None:
                e['star'] = ls
                n_star += 1

    # 登记表兜底（#189）：PLUGINS.md 表行有、已定位集合没有的仓，按登记信息补行
    n_floor = n_floor_gone = 0
    reg_md = ROOT / 'PLUGINS.md'
    if reg_md.is_file():
        have = set()
        for e in entries:
            mh = REAL_URL_RE.search(e.get('url') or '')
            if mh:
                have.add(f"{mh.group(1)}/{mh.group(2)}".lower())
            have.add(e['name'].lower().replace('/', '-'))
        for line in reg_md.read_text().splitlines():
            rm = re.match(r'^\|\s*([^|]+?)\s*\|\s*\[[^\]]*\]\('
                          r'(https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)/?\)\s*\|\s*([^|]*)', line)
            if not rm:
                continue
            name, url, desc = rm.group(1).strip(), rm.group(2), rm.group(3).strip()
            full = url.split('github.com/')[1].strip('/').lower()
            if full in have:
                continue
            dom, _hit = classify(name, desc)
            fe = {'name': name or full.split('/')[1], 'url': f"https://github.com/{full}",
                  'star': live_star.get(full), 'verdict': '⏳ 未测',
                  'domain': dom, 'desc': desc or '—', 'locate': 'located'}
            if url_audit.get(full, {}).get('status') == 'gone':
                fe['locate'] = 'empty_watch'
                n_floor_gone += 1
            else:
                n_floor += 1
            entries.append(fe)
            have.add(full)

    # canonical 改名跟随（repo-map aliases → 引擎登记的最新全名；名称文本仅在等于旧仓名时改写）
    rm_canon = {}
    for v in repo_map.values():
        fn = (v.get('full_name') or '').strip()
        if not fn:
            continue
        for a in ([fn] + list(v.get('aliases') or [])):
            al = (a or '').strip().lower()
            if al and al != fn.lower():
                rm_canon[al] = fn
    n_rename = 0
    for e in entries:
        if e.get('locate') != 'located':
            continue
        m1 = REAL_URL_RE.search(e.get('url') or '')
        if not m1:
            continue
        cur = f"{m1.group(1)}/{m1.group(2)}".lower()
        canon = rm_canon.get(cur)
        if not canon or canon.lower() == cur:
            continue
        if e['name'].lower() == cur.split('/')[1]:
            e['name'] = canon.split('/')[1]
        e['url'] = f"https://github.com/{canon}"
        n_rename += 1

    # desc 回填（GitHub 描述缓存）+「其他」兜底重分类（taxonomy v2 规则，仅动其他类）
    n_desc = n_reclass = 0
    for e in entries:
        desc = (e.get('desc') or '').strip()
        if (not desc or desc == '—' or desc.startswith('http')) and e.get('locate') == 'located':
            full = e['url'].split('github.com/')[1].strip('/') if 'github.com/' in e.get('url', '') else ''
            if full.count('/') == 1 and desc_cache.get(full):
                e['desc'] = desc_cache[full]
                n_desc += 1
        if e.get('domain') == '❓ 其他':
            dom, _hit = classify(e['name'], e.get('desc') or '')
            if dom != '❓ 其他':
                e['domain'] = dom
                e['reclassed'] = True
                n_reclass += 1

    vc = Counter(e['verdict'] for e in entries if e['locate'] == 'located')
    v_all = Counter(e['verdict'] for e in entries)

    # ── 内容消毒（P2b，单一收口：render_all 与 export-data 同源消费）──────────
    # 换行/回车 → 空格（杀条目伪造）；desc 方括号转义（杀钓鱼链接注入）；
    # 真实 URL 过 GitHub 白名单，不过则降级为无链接条目。
    # 实测当前数据：name 零命中、URL 零违规（零漂移）；desc 方括号 16 条（有意变更）。
    n_sanitized = 0
    for e in entries:
        s_name = sanitize_name(e.get('name') or '')
        s_desc = sanitize_desc(e.get('desc') or '')
        if s_name != e.get('name') or s_desc != e.get('desc'):
            n_sanitized += 1
        e['name'], e['desc'] = s_name, s_desc
        u = e.get('url') or ''
        if 'search?q=' not in u and url_guard(u) is None:
            # 白名单外降级到歧义监测轨道：无链接、判定不展示（可见降级，非静默丢弃；
            # 复用既有渲染路径，不引入"空 URL 假链接"这类不变量破坏）
            e['locate'] = 'ambiguous_watch'
            n_sanitized += 1

    # ── 导出直出数据（供 export-data 消费，免 Markdown 反解析）─────────────────
    # 顺序契约 = 旧管线 catalog/all/*.md 按文件名字典序拼接 × 组内 (❌沉尾, star 降序)；
    # 只含 locate=located 条目（旧正则只匹配带真实链接的行）。
    export_rows = []
    for dom in sorted(DOMAIN_ORDER, key=lambda d: f"{d.split(' ', 1)[-1]}.md"):
        group = sorted([e for e in entries if e.get('domain') == dom],
                       key=lambda x: (x.get('verdict') == '❌ 运行级不兼容', -(x.get('star') or 0)))
        for e in group:
            if e.get('locate') != 'located':
                continue
            desc = (e.get('desc') or '—').strip()
            if desc.startswith('http'):
                desc = '—'
            pr = ' 〔PR〕' if e['name'] in pr_names else ''
            bundle = '〔📦〕' if e.get('bundle') else ''
            export_rows.append({
                'repo': e['url'].split('github.com/')[1],
                'name': e['name'],
                'verdict': EXPORT_VERDICT.get(e.get('verdict'), 'untested'),
                'stars': e.get('star') if isinstance(e.get('star'), int) else None,
                'desc': f'{desc}{pr}{bundle}',
            })
    # 同仓多键去重 + 判定仲裁（与旧导出路径逐字一致：定位修复发生在归并之后，
    # 占位条目修复出真实 URL 后可能与既有条目同仓——首个获胜、星数取大、ok/❌ 冲突降 pending）
    _by = {}
    for p in export_rows:
        k = p['repo'].lower()
        if k in _by:
            prev = _by[k]
            if prev['verdict'] != p['verdict'] and {prev['verdict'], p['verdict']} & {'ok', 'incompatible'}:
                prev['verdict'] = 'pending'
            if (p['stars'] or 0) > (prev['stars'] or 0):
                prev['stars'] = p['stars']
        else:
            _by[k] = p
    export_rows = list(_by.values())

    # stats 契约 = 旧 STAT_RE 序列（全量行 → 已定位行 → 监测行）的「后值覆盖」结果；
    # unlocated 旧管线仅在其行印出时存在（=0 时缺失），新管线恒定输出（P0 schema 要求七键齐）。
    export_stats = {
        'ok': vc.get('✅ 运行级可用', 0),
        'incompatible': vc.get('❌ 运行级不兼容', 0),
        'pending': vc.get('⚠️ 待定', 0),
        'untested': vc.get('⏳ 未测', 0),
        'gone': n_empty,
        'ambiguous': n_amb,
        'unlocated': n_unresolved,
    }

    doc = {
        'schema': 'radar-canonical/v1',
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'loader': {'files_read': n_files, 'window_days': WINDOW_DAYS,
                   'baseline_used': bool(BASELINE.is_file())},
        'rounds': rounds,
        'snapshot_run_id': rounds[0][0] if rounds else None,
        'entries': entries,
        'counts': {'total': len(entries), 'dedup': n_dedup, 'conflict': n_conflict,
                   'locate_fixed': n_fix, 'empty_watch': n_empty, 'ambiguous_watch': n_amb,
                   'unresolved': n_unresolved, 'live_star': n_star,
                   'floor_added': n_floor, 'floor_gone': n_floor_gone,
                   'rename_followed': n_rename, 'desc_backfilled': n_desc, 'reclassed': n_reclass,
                   'pr_registered': len(pr_names)},
        'stats_located': dict(vc), 'stats_all': dict(v_all), 'pr_names': sorted(pr_names),
        'domain_stats': {dom: {'total': sum(1 for e in entries if e.get('domain') == dom),
                               'ok': vc_local(entries, dom, '✅ 运行级可用'),
                               'bad': vc_local(entries, dom, '❌ 运行级不兼容'),
                               'inc': vc_local(entries, dom, '⚠️ 待定'),
                               'un': vc_local(entries, dom, '⏳ 未测'),
                               'watch': sum(1 for e in entries if e.get('domain') == dom
                                            and e.get('locate') != 'located')}
                         for dom in DOMAIN_ORDER},
        'global': {'un': vc.get('⏳ 未测', 0), 'located': sum(vc.values()), 'all': len(entries)},
        'export': {'rows': export_rows, 'stats': export_stats,
                   'anchor_run_id': rounds[0][0] if rounds else None},
    }
    atomic_write_json(OUT, doc)
    print(f'[build-canonical] {len(entries)} 条（去重 {n_dedup} · 冲突 {n_conflict} · 定位修复 {n_fix} · '
          f'空仓 {n_empty} · 歧义 {n_amb} · 未定位 {n_unresolved} · 实时星 {n_star}）'
          f'→ {OUT.relative_to(ROOT)}（快照读取 {n_files} 文件）')
    return doc


def main() -> int:
    build()
    return 0


if __name__ == '__main__':
    sys.exit(main())
