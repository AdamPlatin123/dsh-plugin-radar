#!/usr/bin/env python3
"""刷新独立目录页的精选插件榜与整合包节（人工策展 + 自动刷新星标）。

精选榜成员来自 data/awesome-50.json、整合包来自 data/bundles.json（均人工策展，
本脚本只读不改成员）；逐仓库 REST 查询星标（跟随改名重定向），渲染分类表格，
只替换独立目录页的精选与整合包标记块。任一策展成员不可达或
查询失败即中止（成员是固定名单，消失/失联是异常信号，不写半截榜单）。

依赖：环境变量 GH_TOKEN（GitHub token，读公开仓库）；curl；python3。
用法：GH_TOKEN=... python3 scripts/refresh-featured.py [--dry]
"""
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY = '--dry' in sys.argv
CURATED = os.path.join(ROOT, 'data', 'awesome-50.json')
BUNDLES = os.path.join(ROOT, 'data', 'bundles.json')
REFRESH_LABEL = '每 6 小时自动刷新'
# 类目/形态英文名（双语标题副行；一行中文一行英文的 README 约定）
CAT_EN = {'🚀 智力增强 Booster': 'Intelligence Boosters', '🖥 界面与工作台': 'UI & Workbench',
          '⌨️ 终端与桌面端': 'Terminal & Desktop', '👁 视觉与多模态': 'Vision & Multimodal',
          '🤖 Agent 能力与编排': 'Agent Orchestration', '💻 编码与生产力': 'Coding & Productivity',
          '🧠 记忆与上下文': 'Memory & Context', '📡 消息通讯与 IM': 'Messaging & IM',
          '🗂 文件、数据与浏览': 'Files, Data & Browsing', '🛒 市场与管理': 'Marketplaces & Management',
          '🎮 娱乐生活': 'Fun & Life', '⭐ 内测成员作品': 'Insider Members', '🎚 预设与配置套件': 'Presets & Config Kits',
          '🧩 能力合集': 'Capability Collections', '📀 发行版': 'Distributions', '📑 配方管理器': 'Recipe Managers'}


def radar_verdicts():
    """Read verdicts from the final deduplicated public list."""
    path = os.path.join(ROOT, 'data', 'plugins-all.json')
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    return {p['repo'].lower(): p['verdict'] for p in data['plugins']}


def status_label(verdict):
    return {'ok': '[可用记录]', 'incompatible': '[不兼容记录]',
            'pending': '[待定]', 'untested': '[未测]'}.get(verdict, '[未索引]')


def replace_curated_blocks(text, featured, bundles):
    """Reject missing or ambiguous blocks; leave all unowned text untouched."""
    for key, block in [('featured', featured), ('bundles', bundles)]:
        start, end = f'<!-- AUTO:{key}:START -->', f'<!-- AUTO:{key}:END -->'
        if text.count(start) != 1 or text.count(end) != 1 or text.index(end) < text.index(start):
            raise ValueError(f'{key} 标记缺失、重复或次序错误')
        left, right = text.index(start), text.index(end) + len(end)
        text = text[:left] + block + text[right:]
    return text


TOKEN = os.environ.get('GH_TOKEN') or subprocess.run(
    ['gh', 'auth', 'token'], capture_output=True, text=True).stdout.strip()
if not TOKEN:
    sys.exit('[错误] 缺少 GH_TOKEN（且 gh auth token 不可用）')


def fetch(repo):
    """REST 查询单个仓库；跟随改名，返回 canonical full_name/star/描述，不可达返回 None。"""
    for attempt in range(2):
        p = subprocess.run(
            ['curl', '-sL', '--max-time', '25',
             '-H', f'Authorization: Bearer {TOKEN}',
             '-H', 'Accept: application/vnd.github+json',
             f'https://api.github.com/repos/{repo}'],
            capture_output=True, text=True)
        try:
            d = json.loads(p.stdout)
        except Exception:
            time.sleep(1)
            continue
        if 'id' in d and 'full_name' in d:
            if d.get('private') or d.get('archived'):
                return None
            return d['full_name'], d.get('stargazers_count', 0), (d.get('description') or '').strip()
        if d.get('message') == 'Not Found':
            return None
        time.sleep(1)
    return 'RETRY_FAIL', repo, ''


def main():
    data = json.loads(Path(CURATED).read_text(encoding='utf-8'))
    bdata = json.loads(Path(BUNDLES).read_text(encoding='utf-8'))
    rv = radar_verdicts()
    print(f'[verdict] 已定位去重清单 {len(rv)} 条；未收录成员标为未索引')
    cats = data['categories']
    forms = bdata['forms']
    repos = [p['repo'] for c in cats for p in c['plugins']]
    brepos = [p['repo'] for f in forms for p in f['plugins']]
    # 成员数随实测口径动态变化（rc.8 重测通过者）；下限防 JSON 误删，去重防误加
    if len(repos) < 20:
        sys.exit(f'[中止] 策展成员仅 {len(repos)} 个（<20），疑似 JSON 损坏，需人工校对')
    if len(set(repos)) != len(repos):
        sys.exit('[中止] 策展成员存在重复仓库，JSON 需人工校对')
    if len(brepos) < 5:
        sys.exit(f'[中止] 整合包成员仅 {len(brepos)} 个（<5），疑似 JSON 损坏，需人工校对')
    if len(set(brepos)) != len(brepos):
        sys.exit('[中止] 整合包成员存在重复仓库，JSON 需人工校对')

    with ThreadPoolExecutor(max_workers=16) as ex:
        results = list(ex.map(fetch, repos + brepos))
    stars, fails = {}, []
    for repo, r in zip(repos + brepos, results):
        if r is None:
            fails.append(f'{repo}(不可达/私有/归档)')
        elif r[0] == 'RETRY_FAIL':
            fails.append(f'{repo}(网络失败)')
        else:
            stars[repo] = r[1]
    print(f'[fetch] 成功 {len(stars)}/{len(repos) + len(brepos)}')
    if fails:
        sys.exit(f'[中止] 策展成员查询失败 {len(fails)} 个: {fails[:5]}')

    ts = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M')
    total = sum(len(c['plugins']) for c in cats)
    parts = [
        '<!-- AUTO:featured:START -->', '',
        f'> 人工策展 {total} 款插件，按 11 类分组、类内按星标排序；星标{REFRESH_LABEL}'
        f'（成员调整请提 PR 修改 data/awesome-50.json）。数据截至 {ts}（UTC+8）。',
        f'> *Human-curated {total} plugins in 11 groups, star-sorted within each; stars auto-refresh every 6 hours '
        f'(membership via PR to data/awesome-50.json). As of {ts} (UTC+8).*',
        '',
    ]
    for c in cats:
        ranked = sorted(c['plugins'], key=lambda p: (-stars[p['repo']], p['repo'].lower()))
        parts.append(f"### {c['name']}（{len(ranked)}）")
        parts.append(f"*{CAT_EN.get(c['name'], '')} ({len(ranked)})*")
        parts.append('')
        # 列表布局（非表格）：GitHub 表格对单元格图片强制 max-width:100%+height:auto 缩放无法规避；
        # 列表行内图片保持原尺寸，磁贴开头统一 108px 亦使全页文本列自然对齐
        for p in ranked:
            t = status_label(rv.get(p['repo'].lower()))
            parts.append(f"- {t} **[{p['name']}](https://github.com/{p['repo']})** · {stars[p['repo']]}★"
                         f" — {p['desc'].replace('|', '\\|')}")
        parts.append('')
    parts.append('> 状态来自公开清单的历史归并记录，未索引成员不推断兼容性；'
                 '逐条测试版本证据尚未完整公开。安装前请检查原仓库说明。')
    block = '\n'.join(parts) + '\n\n<!-- AUTO:featured:END -->'

    # ── 整合包节（AUTO:bundles）：四形态，类内星标降序 ──
    btotal = len(brepos)
    bparts = [
        '<!-- AUTO:bundles:START -->', '',
        f'> 人工策展 {btotal} 个整合包：内测成员作品置顶，其下按预设套件 / 能力合集 / 发行版 / 配方管理器四形态分组，'
        f'类内按星标排序；星标{REFRESH_LABEL}（成员调整请提 PR 修改 data/bundles.json）。数据截至 {ts}（UTC+8）。',
        f'> *Human-curated {btotal} bundles: insider picks pinned on top, then presets / collections / distributions / '
        f'recipe managers, star-sorted; auto-refreshed every 6 hours. As of {ts} (UTC+8).*',
        '',
    ]
    for f in forms:
        ranked = sorted(f['plugins'], key=lambda p: (-stars[p['repo']], p['repo'].lower()))
        bparts.append(f"### {f['name']}（{len(ranked)}）")
        bparts.append(f"*{CAT_EN.get(f['name'], '')} ({len(ranked)})*")
        bparts.append('')
        for p in ranked:
            t = status_label(rv.get(p['repo'].lower()))
            bparts.append(f"- {t} **[{p['name']}](https://github.com/{p['repo']})** · {stars[p['repo']]}★"
                          f" — {p['desc'].replace('|', '\\|')}")
        bparts.append('')
    bparts.append('> 状态口径同精选榜；整合包安装、权限与卸载方式以各仓库说明为准。')
    bparts.append('> *Statuses follow the same historical-record scale as the featured board; install per each bundle\'s own README '
                  '(presets: `dsh plugin add` then enable in settings; distributions: use their installers).*')
    bblock = '\n'.join(bparts) + '\n\n<!-- AUTO:bundles:END -->'

    changed = False
    for name in ['docs/catalog-highlights.md']:
        path = os.path.join(ROOT, name)
        text = Path(path).read_text(encoding='utf-8')
        new = replace_curated_blocks(text, block, bblock)
        if new != text:
            if not DRY:
                Path(path).write_text(new, encoding='utf-8')
            changed = True
            print(f'[write] {name}')
    if not changed:
        print('[noop] 榜单无变化')
    top = max(repos, key=lambda r: stars[r])
    btop = max(brepos, key=lambda r: stars[r])
    print(f'[done] 精选 {len(repos)} 款 · 整合包 {len(brepos)} 个 · 榜首 {top} {stars[top]}⭐ · 整合包之首 {btop} {stars[btop]}⭐')


if __name__ == '__main__':
    main()
