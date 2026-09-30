#!/usr/bin/env python3
"""rebaseline.py — ADR-0002 快照治理落地：基线固化 + 30 天窗口裁剪。

data/snapshots/ 曾以 567 份全量入库、渲染每轮全读（工作区 1.4G、IO 随轮数线性涨）。
本工具把窗口外全部历史轮的 (name,url) 合并结果固化为 data/snapshot-baseline.json，
装载侧（build_canonical.load_entries）此后只读「窗口文件 ⊕ 基线」。

正确性铁律：基线 ⊕ 窗口的重放结果必须与全量扫描逐项相等——本脚本固化前先做该断言，
不等则拒绝写基线（exit 20，fail-closed），因此裁剪旧快照不丢任何信息。

用法：
  python3 engine/aggregation/rebaseline.py            # 仅固化基线（不动快照文件）
  python3 engine/aggregation/rebaseline.py --prune    # 固化后 git rm 窗口外快照
季度重固化：窗口滚动导致新快照陆续越过 cutoff 后重跑即可（基线 = 旧基线 ⊕ 新越界轮）。
"""
import glob
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from radar.atomicio import atomic_write_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
SNAP_DIR = ROOT / 'data' / 'snapshots'
BASELINE = ROOT / 'data' / 'snapshot-baseline.json'
WINDOW_DAYS = 30


def cutoff_name():
    now = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    return now.strftime('%Y%m%dT%H%M%SZ')


def merge_files(files):
    """files 新→旧序；(name,url) 同键最新轮胜。返回 (merged dict, rounds, schema-valid 数)。"""
    merged, rounds, n = {}, [], 0
    for fp in files:
        try:
            d = json.loads(Path(fp).read_text())
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            continue
        if not str(d.get('schema', '')).startswith('radar-snapshot/'):
            continue
        n += 1
        rounds.append((d['run_id'], d.get('generated_at', '')))
        for e in d.get('catalog_entries') or []:
            merged.setdefault((e['name'], e.get('url', '')), dict(e))
    return merged, rounds, n


def main() -> int:
    cutoff = cutoff_name()
    files = sorted(glob.glob(str(SNAP_DIR / '*.json')), reverse=True)
    window = [f for f in files if Path(f).name >= cutoff]
    beyond = [f for f in files if Path(f).name < cutoff]
    if not beyond:
        print(f'[rebaseline] 窗口外无快照（cutoff={cutoff}），无需固化')
        return 0

    # 比较基准 = 现存全扫 ⊕ 旧基线（外审 P1：曾只比现存文件——首次裁剪后
    # 旧基线独有条目会让季度重固化永远 exit 20）
    full_merged, full_rounds, n_all = merge_files(files)
    _prev_baseline = {}
    if BASELINE.is_file():
        try:
            _prev_baseline = json.loads(BASELINE.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            # 既有基线损坏 = 历史可能在里面且已无处可寻（窗口外快照已裁剪）——fail-closed
            # 拒绝重建（二轮外审 P1：曾静默按空基线继续，可写入丢掉全部历史的"新基线"）
            print(f'[rebaseline] FAIL CLOSED: 既有基线损坏（{exc}）——历史无法核验，'
                  f'请从 git 历史恢复 data/snapshot-baseline.json 后重试', file=sys.stderr)
            return 20
    for _e in _prev_baseline.get('entries', []):
        full_merged.setdefault((_e['name'], _e.get('url', '')), dict(_e))

    # 基线若已存在（季度重固化），并入历史部分一起重固化
    baseline_entries, baseline_rounds = [], []
    if BASELINE.is_file():
        prev = _prev_baseline   # 前置校验已 fail-closed，此处必然可读
        baseline_entries = prev.get('entries', [])
        baseline_rounds = [tuple(r) for r in prev.get('rounds', [])]

    beyond_merged, beyond_rounds, n_beyond = merge_files(beyond)
    for e in baseline_entries:   # 旧基线的条目比一切现存文件都旧，垫底
        beyond_merged.setdefault((e['name'], e.get('url', '')), dict(e))
    beyond_rounds = beyond_rounds + [r for r in baseline_rounds if r not in beyond_rounds]

    # 重放等价断言：窗口 ⊕ 基线 == 全量扫描（fail-closed，不等不写）
    replay = dict()
    for e in merge_files(window)[0].values():
        replay[(e['name'], e.get('url', ''))] = e
    for e in beyond_merged.values():
        replay.setdefault((e['name'], e.get('url', '')), dict(e))
    if replay != full_merged:
        diff_k = [k for k in set(replay) ^ set(full_merged)][:5]
        print(f'[rebaseline] FAIL CLOSED: 重放与全量不一致（键差示例 {diff_k}，'
              f'replay={len(replay)} full={len(full_merged)}）', file=sys.stderr)
        return 20

    doc = {
        'schema': 'radar-snapshot-baseline/v1',
        'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'window_days': WINDOW_DAYS,
        'cutoff': cutoff,
        'rounds': beyond_rounds,
        'entry_count': len(beyond_merged),
        'replay_verified': True,
        'entries': list(beyond_merged.values()),
    }
    atomic_write_json(BASELINE, doc)
    print(f'[rebaseline] 基线固化：{len(beyond_merged)} 条 / {len(beyond_rounds)} 轮（窗口外 {n_beyond} 文件 ⊕ 旧基线'
          f'{len(baseline_entries)} 条）→ data/snapshot-baseline.json；重放等价断言通过（{len(full_merged)} 键全等）')

    if '--prune' in sys.argv:
        import subprocess
        pruned = [str(Path(f).resolve().relative_to(ROOT.resolve())) for f in beyond]
        r = subprocess.run(['git', 'rm', '-q', *pruned], cwd=ROOT)
        if r.returncode != 0:
            print('[rebaseline] git rm 失败——基线已固化，可手动重试', file=sys.stderr)
            return 21
        print(f'[rebaseline] 已裁剪窗口外快照 {len(pruned)} 份（git rm，待提交）')
    print(f'[rebaseline] 现存快照 {len(files)} 份：窗口内 {len(window)} · 窗口外 {len(beyond)}（保留供追溯至提交裁剪）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
