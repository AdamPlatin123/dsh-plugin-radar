#!/usr/bin/env python3
"""dormant_policy.py — 休眠测试策略（2026-09-28 用户指令）：

    「超过 1 个月未更新且与近期 DSH 版本不兼容的仓库，暂停测试直到下次更新」

判定口径（仓内可得的最强代理）：
  - 未更新 >30 天 = plugins-enrich 的 pushed_at 距今 >30 天（enrich 日更，
    pushed_at 变化即视为"有更新"→ 下轮自动复活，无需人工除名）；
  - 不兼容 = 清单 verdict == incompatible（该仓在其最近一次实测中不通过）。
  两条件同时满足才入名单（保守：任一不满足、或 enrich 缺 pushed_at（175 仓
  已删/私有）、或未定位条目——一律继续测试）。

产物 data/test-skip-list.json（radar-test-skip/v1）：
  服务器测试调度器（pipeline-driver）可直接消费——命中名单的仓库跳过派发；
  站点与导出层仅做展示标注，不改判定语义与七档统计口径。

用法：python3 engine/aggregation/dormant_policy.py [--root <仓库根>]
（enrich-metadata 日更后接跑；也可独立运行）
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from radar.atomicio import atomic_write_json  # noqa: E402

DORMANT_DAYS = 30


def _load(p: Path, default):
    try:
        return json.loads(p.read_text(encoding='utf8'))
    except (OSError, json.JSONDecodeError):
        return default


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    root = Path(args[0]) if args else Path(__file__).resolve().parent.parent.parent
    rows = _load(root / 'data' / 'plugins-all.json', {}).get('plugins', [])
    enrich = _load(root / 'data' / 'plugins-enrich.json', {}).get('entries', {})
    now = datetime.now(timezone.utc)

    dormant, n_stale = [], 0
    for r in rows:
        repo = r['repo'].lower()
        en = enrich.get(repo) or {}
        pushed = en.get('pushed_at') or ''
        try:
            age_days = (now - datetime.fromisoformat(pushed.replace('Z', '+00:00'))).days
        except ValueError:
            continue   # 无 pushed_at：无法判更新态，保守继续测试
        if age_days > DORMANT_DAYS:
            n_stale += 1
            if r['verdict'] == 'incompatible':
                dormant.append(repo)

    doc = {
        'schema': 'radar-test-skip/v1',
        'generated_at': now.isoformat(timespec='seconds'),
        'policy': f'pushed_at > {DORMANT_DAYS}d 且 verdict == incompatible —— 暂停测试直到下次更新'
                  f'（enrich 日更刷新 pushed_at，更新即自动复活）',
        'dormant_days': DORMANT_DAYS,
        'counts': {
            'skip_total': len(dormant),
            'stale_over_30d': n_stale,
            'incompatible_total': sum(1 for r in rows if r['verdict'] == 'incompatible'),
            'listed_total': len(rows),
        },
        'repos': sorted(dormant),
    }
    atomic_write_json(root / 'data' / 'test-skip-list.json', doc, indent=1)
    c = doc['counts']
    print(f'[dormant] 休眠名单 {c["skip_total"]} 仓（>30d 未更新 {c["stale_over_30d"]} ∩ '
          f'incompatible {c["incompatible_total"]}；占 incompatible '
          f'{c["skip_total"] * 100 // max(1, c["incompatible_total"])}%）→ data/test-skip-list.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
