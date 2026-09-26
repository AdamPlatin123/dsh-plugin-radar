#!/usr/bin/env python3
"""render_all.py — 渲染半场：canonical.json → PLUGINS-ALL.md + catalog/all/*.md。

P1 数据层收敛：原 scripts/gen_plugins_all.py main() 的 Markdown 半场上移至此，
唯一输入为 engine/aggregation/build_canonical.py 产出的 canonical 文档
（dict 或 generated/current/canonical.json），不再自读快照/缓存——渲染与导出
同源，Markdown 从此是纯消费端。

副作用保留：tile_assets 磁贴生成（runner-smoke 冒烟断言依赖）。
返回值契约不变：{'domains': {...}, 'global': {...}}（render-readme-from-snapshot.py 消费）。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'aggregation'))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from build_canonical import DOMAIN_ORDER, bj, vc_local  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
CANON = ROOT / 'generated' / 'current' / 'canonical.json'
OUT = ROOT / 'PLUGINS-ALL.md'

MARK = {'✅ 运行级可用': '🟩 `[可用]`', '❌ 运行级不兼容': '🟨 `[不兼容]`',
        '⚠️ 待定': '⬜ `[待定]`', '⏳ 未测': '⬜ `[未测]`'}


def _version_key(t):
    m = re.match(r'(\d+)\.(\d+)\.(\d+)-rc\.(\d+)$', t)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))) if m else (0, 0, 0, 0)


def _runner_version_line(radar_ver):
    """测试版本累计行：runner-versions.json 多版本分解；缺文件时回退磁贴版本串。"""
    try:
        rv = json.loads((ROOT / 'data' / 'runner-versions.json').read_text())
        latest = rv.get('latest', radar_ver)   # 键缺失才回退磁贴版本——与旧口径逐字一致
        vd = ' · '.join(f"{t}（{sum(c.values())}）" for t, c in
                        sorted(rv.get('versions', {}).items(),
                               key=lambda kv: (kv[0] == latest, _version_key(kv[0])), reverse=True))
        return f"- 测试版本（多主线累计）：{vd}；最新 `{latest}`（烤入磁贴右段）"
    except Exception:
        return f"- 测试版本（多主线累计）：{radar_ver}；最新 `{radar_ver}`（烤入磁贴右段）"


def render(canonical=None) -> dict:
    if canonical is None:
        canonical = json.loads(CANON.read_text(encoding='utf8'))
    entries = canonical['entries']
    counts = canonical['counts']
    vc = canonical['stats_located']
    v_all = canonical['stats_all']
    pr_names = set(canonical.get('pr_names') or [])
    n_empty, n_amb = counts['empty_watch'], counts['ambiguous_watch']
    n_unresolved, n_fix = counts['unresolved'], counts['locate_fixed']

    radar_ver = ''
    try:
        import tile_assets
        tile_assets.write_tiles()
        radar_ver = tile_assets.current_version()
    except Exception:
        pass

    rounds = canonical.get('rounds') or []
    src = ' ⊕ '.join(f'`{rid}` {bj(ts)}' for rid, ts in rounds[:3])
    if len(rounds) > 3:
        src += f' 等 {len(rounds)} 轮'
    n_located = canonical['global']['located']

    L = []
    L.append('# 全量插件清单（统一四档口径）')
    L.append('')
    L.append(f'> 数据源：radar 快照并集（{src}）⊕ GitHub 定位复核缓存（data/locate-cache.json）。')
    L.append('> 呈现：分组列表（状态 · 名称 · ★星标 · 一句话说明），不使用大表格；〔📦〕= 整合包（根 dsh.bundle / workspaces 多子包）。')
    L.append('')
    L.append('## 统一度量衡')
    L.append('')
    L.append('**判定维度**（运行级四档；测试：dsh 容器 agent + Qwen3.6-35B · k8s 5 分片 · run_id 锚定轮次）：')
    L.append('')
    L.append(_runner_version_line(radar_ver))
    L.append(f'- 全量判定 {sum(v_all.values())}（全体条目，含监测/未定位；README 磁贴为单快照即时口径，与本清单并集归并口径的差源见附录）：'
             f'`[可用]`（{v_all.get("✅ 运行级可用", 0)}）/ `[不兼容]`（{v_all.get("❌ 运行级不兼容", 0)}）/ `[待定]`（{v_all.get("⚠️ 待定", 0)}）')
    L.append(f'- 已定位明细 {n_located}（本列表展示口径，另 {len(entries) - n_located} 条监测/未定位的判定暂不展示）：'
             f'`[可用]`（{vc.get("✅ 运行级可用", 0)}）/ `[不兼容]`（{vc.get("❌ 运行级不兼容", 0)}）/ `[待定]`（{vc.get("⚠️ 待定", 0)}）/ `[未测]`（{vc.get("⏳ 未测", 0)}）')
    L.append('')
    L.append('**定位维度**（与判定正交；监测类不显示对错判定，原始结果保留于快照层）：')
    L.append('')
    L.append(f'- `[空仓监测]`（{n_empty}）— GitHub 复核无此仓库；待重现后恢复判定显示')
    L.append(f'- `[歧义监测]`（{n_amb}）— 同名多仓无法锁定本体；锁定前不展示')
    if n_unresolved:
        L.append(f'- `[未定位]`（{n_unresolved}）— 新占位条目，待下一轮定位复核（scripts/resolve_placeholders.py）')
    L.append(f'- 定位复核累计修复 {n_fix} 个占位 URL')
    L.append('')
    L.append('> 〔PR〕= 经已合并 PR 正式登记；收录 ≠ 兼容 ≠ 运行可用 ≠ 安全审计。')
    L.append('')
    L.append(f'## 汇总：{len(entries)} 条（已定位 {n_located} · 监测/未定位 {len(entries) - n_located}）· PR 登记 {len(pr_names)} 个')
    L.append('')

    dom_dir = ROOT / 'catalog' / 'all'
    dom_dir.mkdir(parents=True, exist_ok=True)
    for dom in DOMAIN_ORDER:
        # 组内排序：星标降序；[不兼容] 整体沉组尾（组内仍按星标）——排除信息不占组头
        group = sorted([e for e in entries if e.get('domain') == dom],
                       key=lambda x: (x.get('verdict') == '❌ 运行级不兼容', -(x.get('star') or 0)))
        if not group:
            continue
        dl = [f'# {dom}（{len(group)}）', '',
              f'> 数据源与口径见 [PLUGINS-ALL.md](../../PLUGINS-ALL.md)（索引页）；磁贴图例同 README。', '']
        for e in group:
            name = e['name']
            star = e.get('star')
            star_part = f'★{star} ' if isinstance(star, int) else ''   # 星数未知留空不印 0（防污染排序，bot 日更补齐）
            desc = (e.get('desc') or '—').strip()
            if desc.startswith('http'):
                desc = '—'
            pr = ' 〔PR〕' if name in pr_names else ''
            loc = e.get('locate')
            if loc == 'empty_watch':
                dl.append(f'- `[空仓监测]` **{name}** — GitHub 无此仓库，判定暂不展示{pr}')
            elif loc == 'ambiguous_watch':
                dl.append(f'- `[歧义监测]` **{name}** — 同名多仓，判定暂不展示{pr}')
            elif loc == 'unresolved':
                dl.append(f'- `[未定位]` **{name}** — 占位待复核，判定暂不展示{pr}')
            else:
                bundle_part = '〔📦〕' if e.get('bundle') else ''   # 整合包（dsh.bundle / workspaces 结构）
                dl.append(f'- {MARK.get(e.get("verdict"), "⬜ `[未测]`")} [{name}]({e["url"]}) {star_part}— {desc}{pr}{bundle_part}')
        dom_slug = dom.split(' ', 1)[-1]
        dom_file = dom_dir / f'{dom_slug}.md'
        dom_file.write_text('\n'.join(dl).replace('](assets/', '](../../assets/') + '\n', encoding='utf8')
        g_ok = vc_local(entries, dom, '✅ 运行级可用')
        g_bad = vc_local(entries, dom, '❌ 运行级不兼容')
        g_inc = vc_local(entries, dom, '⚠️ 待定') + vc_local(entries, dom, '⏳ 未测')
        L.append(f'- **{dom}**（{len(group)}）— 🟩 {g_ok} · 🟨 {g_bad} · ⬜ {g_inc} — [明细]({dom_file.relative_to(ROOT).as_posix().replace(chr(32), "%20")})')
    L.append('')

    L.append('## 附录')
    L.append('')
    L.append('- 判定与定位正交；监测类条目的原始判定保留于 data/snapshots/，定位成功后自动恢复展示。')
    L.append('- 占位 URL 由发现管线 clone 库通道产生；定位复核：`python3 scripts/resolve_placeholders.py`（结果写 data/locate-cache.json，命中附实时 star）。')
    L.append('- 合并主键以 GitHub 仓库全名为准（真实 URL / data/repo-map.json / 定位缓存三源归一）：同一仓库的不同命名键合并为单条，判定冲突降级 [待定] 待重测仲裁。')
    L.append('- 口径对齐说明：README 磁贴/徽章与「运行级实测」行为单快照即时全量口径；本清单为多轮快照并集归并口径（同名多键合一、判定冲突降 [待定]、刷新随日更）。两者存在时滞与归并差，属设计特性；判定真相以 data/snapshots/ 逐轮快照为准。')
    L.append('')

    OUT.write_text('\n'.join(L) + '\n', encoding='utf8')
    print(f'[render-all] {len(entries)} 条 → {OUT.name}（空仓 {n_empty} / 歧义 {n_amb} / 未定位 {n_unresolved}）')
    return {'domains': canonical['domain_stats'], 'global': canonical['global']}


def main() -> int:
    render()
    return 0


if __name__ == '__main__':
    sys.exit(main())
