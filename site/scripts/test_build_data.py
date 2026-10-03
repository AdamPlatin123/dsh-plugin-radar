#!/usr/bin/env python3
"""test_build_data.py — 站点数据烘焙回归测试（stdlib-only，离线）

对应 2026-10-02 维护评审的站点侧 P1 发现，任何回退都会使对应断言失败：

1. enrich 索引错位（历史缺陷）：rows 曾按 verdict=ok 过滤，enrich 却按未过滤
   行号生成，消费方 enrichAt(rowIndex(row)) 取到别的仓库的元数据
   （评审时 8,351 条中 7,679 条错位，首例 Python 仓库被显示为 JavaScript）。
   → 断言 ROWS 全量保留 + ENRICH 键与 flags&4 行严格对齐 + 元数据逐行归属正确。
2. 精选/整合包入口指向不存在的详情（404）。
   → 断言 curatedStatus 与最终 rows 对账：indexed=False ⇔ 不在 ROWS
     （视图据此分流到「监测态 + 源仓回退」，不渲染 404 详情路由）；
     未索引条目的 monitor 取自 canonical 未定位记录，无记录时为 null。
3. 对外统计取 latest.json 过时指针，与最终 rows 不可对账。
   → 断言 stats/totalIndexed/totalBrowsable/counts 一律从最终 rows 现算，
     不受 latest.json 里的诱导错误值影响（fixture 故意放错位统计）。

运行：python3 site/scripts/test_build_data.py（在仓库任意目录均可）
"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_data import build  # noqa: E402

# ── fixture（最小但覆盖全部修复点；latest.stats 为诱导错误值）──────────────
PLUGINS_ALL = {
    'schema': 'dsh-radar/v1', 'generated_at': '2026-10-02T00:00:00Z',
    'plugins': [
        # 前置 untested 行（历史 ok 过滤会剔除的首行 → enrich 错位高发位）
        {'repo': 'a/first-untested', 'name': 'first-untested', 'verdict': 'untested',
         'stars': None, 'desc': '前置未测行，无 enrich'},
        {'repo': 'b/second-ok', 'name': 'second-ok', 'verdict': 'ok',
         'stars': 10, 'desc': 'ok 行，enrich=Python'},
        # 评审首例同型：若错位，本行的 JavaScript 会挂到上一行
        {'repo': 'c/third-inc', 'name': 'third-inc', 'verdict': 'incompatible',
         'stars': 3, 'desc': '不兼容行，enrich=JavaScript'},
        {'repo': 'd/curated-ok', 'name': 'curated-ok', 'verdict': 'ok',
         'stars': 99, 'desc': '精选名单内的 ok 行'},
        {'repo': 'e/fifth-pending', 'name': 'fifth-pending', 'verdict': 'pending',
         'stars': 1, 'desc': 'pending 行'},
        {'repo': 'f/dormant-inc', 'name': 'dormant-inc', 'verdict': 'incompatible',
         'stars': 2, 'desc': '休眠（skip-list）行，PR 登记，合集成员'},
    ],
}
LATEST = {
    'schema': 'dsh-radar/v1', 'generated_at': '2026-10-02T00:51:25Z',
    'snapshot_run_id': 'TESTRUN20261002', 'total_listed': 4242,
    'stats': {'ok': 999, 'incompatible': 888, 'pending': 777, 'untested': 666},  # 诱导错误值
    'runner_versions': {'latest': '9.9.9-test'},
}
CANONICAL = {
    'schema': 'dsh-radar/canonical/v1', 'generated_at': '2026-10-02T00:00:00Z',
    'pr_names': ['dormant-inc'],
    'entries': [
        {'url': 'https://github.com/b/second-ok', 'domain': '💻 编码开发'},
        {'url': 'https://github.com/c/third-inc', 'domain': '🎨 主题皮肤', 'bundle': True},
        {'url': 'https://github.com/d/curated-ok', 'domain': '🎓 技能包'},
        {'url': 'https://github.com/f/dormant-inc', 'domain': '🛠 基建部署'},
        # 未定位条目：url 为 search?q=owner-name（'/' 已归一为 '-'）
        {'url': 'https://github.com/search?q=x-missing-gone', 'locate': 'empty_watch'},
        {'url': 'https://github.com/search?q=z-missing-unlocated', 'locate': 'unresolved'},
    ],
}
ENRICH = {
    'schema': 'dsh-radar/plugins-enrich/v1', 'generated_at': '2026-10-02T00:00:00Z',
    'entries': {
        'b/second-ok': {'pushed_at': '2026-09-01T00:00:00Z', 'avatar': 'https://ava.tar/b',
                        'lang': 'Python', 'license': 'MIT', 'topics': ['cli']},
        'c/third-inc': {'pushed_at': '2026-08-01T00:00:00Z', 'avatar': 'https://ava.tar/c',
                        'lang': 'JavaScript', 'license': 'Apache-2.0', 'topics': ['web']},
        # 前置行的 enrich（历史过滤会让它成为孤儿键，检验全量对齐）
        'a/first-untested': {'pushed_at': '2026-07-01T00:00:00Z', 'lang': 'Rust'},
    },
}
AWESOME = {
    'schema': 'dsh-radar/awesome/v1',
    'categories': [
        {'name': '测试类一', 'plugins': [
            {'repo': 'd/curated-ok', 'name': 'curated-ok', 'verdict': 'ok', 'desc': '已索引'},
            # 名单自带 verdict=ok 但实际未入索引：视图必须以 curatedStatus 为准
            {'repo': 'X/Missing-Gone', 'name': 'Missing-Gone', 'verdict': 'ok', 'desc': '空仓监测'},
            {'repo': 'y/missing-unknown', 'name': 'missing-unknown', 'verdict': None,
             'desc': 'canonical 无记录'},
        ]},
    ],
}
BUNDLES = {
    'schema': 'dsh-radar/bundles/v1',
    'forms': [
        {'name': '测试合集', 'plugins': [
            {'repo': 'f/dormant-inc', 'name': 'dormant-inc', 'verdict': 'incompatible',
             'desc': '已索引且休眠'},
            {'repo': 'Z/Missing-Unlocated', 'name': 'Missing-Unlocated', 'verdict': 'untested',
             'desc': '未定位'},
        ]},
    ],
}
SKIP_LIST = {'schema': 'dsh-radar/test-skip-list/v1', 'repos': ['f/dormant-inc']}


def _write(root: Path):
    (root / 'data').mkdir(parents=True)
    (root / 'generated' / 'current').mkdir(parents=True)
    (root / 'data' / 'plugins-all.json').write_text(json.dumps(PLUGINS_ALL), encoding='utf8')
    (root / 'data' / 'latest.json').write_text(json.dumps(LATEST), encoding='utf8')
    (root / 'data' / 'plugins-enrich.json').write_text(json.dumps(ENRICH), encoding='utf8')
    (root / 'data' / 'awesome-50.json').write_text(json.dumps(AWESOME), encoding='utf8')
    (root / 'data' / 'bundles.json').write_text(json.dumps(BUNDLES), encoding='utf8')
    (root / 'data' / 'test-skip-list.json').write_text(json.dumps(SKIP_LIST), encoding='utf8')
    (root / 'generated' / 'current' / 'canonical.json').write_text(
        json.dumps(CANONICAL), encoding='utf8')


def _load_export(path: Path, name: str):
    """从生成的 .ts 提取 `export const <name>[?: 类型] = <json>` 的 JSON 值"""
    m = re.search(rf'export const {name}(?::[^=]+)? = (.+?)\n', path.read_text(encoding='utf8'))
    assert m, f'{path} 中未找到 export const {name}'
    return json.loads(m.group(1))


class BuildDataRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='dsh-site-test-')
        root = Path(cls.tmp.name) / 'root'
        out = Path(cls.tmp.name) / 'out'
        _write(root)
        build(root, out)   # out_dir 指向临时目录：不污染 site/src/data 生成物
        cls.rows = _load_export(out / 'plugins.ts', 'ROWS')
        cls.enrich = _load_export(out / 'plugins.ts', 'ENRICH')
        cls.meta = _load_export(out / 'meta.ts', 'meta')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    # ── 发现 1：全量行 + enrich 对齐 ─────────────────────────────────
    def test_rows_full_no_verdict_filter(self):
        """全量保留：ROWS 行数 = plugins[] 长度，不按 ok 过滤（含 untested/pending 前置行）"""
        self.assertEqual(len(self.rows), len(PLUGINS_ALL['plugins']))
        self.assertEqual([r[2] for r in self.rows],
                         ['untested', 'ok', 'incompatible', 'ok', 'pending', 'incompatible'])

    def test_enrich_keys_align_with_flags(self):
        """ENRICH 键（行号，JSON 对象键=字符串）与 flags 位 4 的行严格一致——错位即失配"""
        flag_rows = {str(i) for i, r in enumerate(self.rows) if r[6] & 4}
        self.assertEqual(set(self.enrich.keys()), flag_rows)
        self.assertEqual(set(self.enrich.keys()), {'0', '1', '2'})   # 前置 untested 行也在内

    def test_enrich_belongs_to_its_row(self):
        """元数据逐行归属正确（评审首例：Python 仓库不得显示 JavaScript）"""
        def enrich_at(i):   # 模拟前端 enrichAt(rowIndex(row))
            e = self.enrich.get(str(i))
            return e or None
        by_repo = {r[0].lower(): i for i, r in enumerate(self.rows)}
        self.assertEqual(enrich_at(by_repo['a/first-untested'])[2], 'Rust')
        self.assertEqual(enrich_at(by_repo['b/second-ok'])[2], 'Python')
        self.assertEqual(enrich_at(by_repo['c/third-inc'])[2], 'JavaScript')

    # ── 发现 3：统计从最终 rows 现算，不引用 latest.json ───────────────
    def test_stats_computed_from_rows_not_latest(self):
        """四档统计与 rows 逐行对账，不受 latest.json 诱导错误值影响"""
        self.assertEqual(self.meta['stats'], {'ok': 2, 'incompatible': 2,
                                              'pending': 1, 'untested': 1})
        for k, wrong in LATEST['stats'].items():
            self.assertNotEqual(self.meta['stats'][k], wrong)

    def test_total_indexed_vs_browsable_split(self):
        """全量索引数与默认可浏览数（ok）分开，不混用 latest.total_listed"""
        self.assertEqual(self.meta['totalIndexed'], 6)
        self.assertEqual(self.meta['totalBrowsable'], 2)
        self.assertNotEqual(self.meta['totalIndexed'], LATEST['total_listed'])

    def test_domain_counts_browsable_scope(self):
        """各域计数与浏览页默认口径一致（仅 ok 行）"""
        c = self.meta['counts']
        self.assertEqual(c['coding'], 1)      # b/second-ok
        self.assertEqual(c['skill'], 1)       # d/curated-ok
        self.assertEqual(c['skin'], 0)        # c/third-inc 不兼容，不计入
        self.assertEqual(sum(c.values()), self.meta['totalBrowsable'])

    def test_runner_pointer_kept(self):
        """runner_versions.latest 指针保留（实测基线展示），run_id 锚不丢"""
        self.assertEqual(self.meta['runnerLatest'], '9.9.9-test')
        self.assertEqual(self.meta['runId'], 'TESTRUN20261002')

    # ── 发现 2：curated 状态与路由回退数据前提 ─────────────────────────
    def test_curated_status_matches_rows(self):
        """indexed ⇔ repo 在最终 ROWS（视图分流条件与数据一致，杜绝 404 死链）"""
        in_rows = {r[0].lower() for r in self.rows}
        for repo, st in self.meta['curatedStatus'].items():
            self.assertEqual(st['indexed'], repo in in_rows, repo)
            if st['indexed']:
                row = next(r for r in self.rows if r[0].lower() == repo)
                self.assertEqual(st['verdict'], row[2], repo)
                self.assertEqual(st['dormant'], bool(row[6] & 8), repo)

    def test_curated_monitor_fallback(self):
        """未索引条目的监测态取自 canonical 未定位记录；无记录为 null（视图显示无记录）"""
        cs = self.meta['curatedStatus']
        self.assertEqual(cs['x/missing-gone'],
                         {'indexed': False, 'verdict': None, 'dormant': False, 'monitor': 'gone'})
        self.assertEqual(cs['z/missing-unlocated']['monitor'], 'unlocated')
        self.assertIsNone(cs['y/missing-unknown']['monitor'])

    def test_curated_dormant_flag(self):
        """已索引条目的休眠位来自 skip-list（>30 天未更新且不兼容）"""
        self.assertTrue(self.meta['curatedStatus']['f/dormant-inc']['dormant'])
        self.assertFalse(self.meta['curatedStatus']['d/curated-ok']['dormant'])

    def test_curated_lists_passed_through_untouched(self):
        """策展名单原样透传（不增删、不改自带 verdict）——修 404 不得抹条目"""
        self.assertEqual(self.meta['featured'], AWESOME)
        self.assertEqual(self.meta['bundles'], BUNDLES)
        names = [m['repo'] for g in self.meta['bundles']['forms'] for m in g['plugins']]
        self.assertIn('Z/Missing-Unlocated', names)   # 大小写保持原样

    def test_curated_status_keys_normalized(self):
        """curatedStatus 键为小写 repo 全集（视图按 toLowerCase 查表）"""
        expected = {m['repo'].lower() for g in [*AWESOME['categories'], *BUNDLES['forms']]
                    for m in g['plugins']}
        self.assertEqual(set(self.meta['curatedStatus'].keys()), expected)

    # ── 行结构与 flags 位 ────────────────────────────────────────────
    def test_flags_bits(self):
        """flags 位：1=bundle 2=PR 登记 4=有 enrich 8=休眠"""
        by_repo = {r[0].lower(): r for r in self.rows}
        self.assertEqual(by_repo['c/third-inc'][6] & 1, 1)   # canonical bundle 标记
        self.assertEqual(by_repo['f/dormant-inc'][6] & 2, 2)  # pr_names 命中
        self.assertEqual(by_repo['b/second-ok'][6] & 4, 4)   # enrich 命中
        self.assertEqual(by_repo['f/dormant-inc'][6] & 8, 8)  # skip-list 命中
        self.assertEqual(by_repo['a/first-untested'][6], 4)

    def test_alias_duplicates_merge_before_enrich_flags_and_statistics(self):
        """旧导出仍有别名重复时，站点写入归一身份；整合包标签、元数据和统计都跟随最终行。"""
        with tempfile.TemporaryDirectory() as folder:
            root, out = Path(folder) / 'root', Path(folder) / 'out'
            _write(root)
            rows = {'plugins': [
                {'repo': 'old/desktop', 'name': 'desktop', 'verdict': 'ok', 'stars': 10, 'desc': 'desktop'},
                {'repo': 'new/desktop', 'name': 'desktop', 'verdict': 'incompatible', 'stars': 20, 'desc': 'desktop〔📦〕'},
                {'repo': 'independent/desktop', 'name': 'desktop', 'verdict': 'ok', 'stars': 30, 'desc': 'different project'},
            ]}
            (root / 'data/plugins-all.json').write_text(json.dumps(rows))
            (root / 'data/repository-identities.json').write_text(json.dumps({'entries': [{
                'canonical_id': 'github:1', 'full_name': 'new/desktop',
                'aliases': ['old/desktop'], 'checked_at': '2026-10-03'}]}))
            (root / 'data/plugins-enrich.json').write_text(json.dumps({'entries': {
                'old/desktop': {'lang': 'Rust', 'pushed_at': '2026-10-03T00:00:00Z'},
                'independent/desktop': {'lang': 'Python'},
            }}))
            (root / 'data/awesome-50.json').write_text(json.dumps({'categories': [{
                'name': 'desktop', 'plugins': [{'repo': 'old/desktop', 'name': 'desktop'}]}]}))
            (root / 'data/test-skip-list.json').write_text(json.dumps({'repos': ['old/desktop']}))
            build(root, out)
            final_rows = _load_export(out / 'plugins.ts', 'ROWS')
            meta = _load_export(out / 'meta.ts', 'meta')
            enrich = _load_export(out / 'plugins.ts', 'ENRICH')
            self.assertEqual([r[0] for r in final_rows], ['new/desktop', 'independent/desktop'])
            self.assertEqual(final_rows[0][2], 'pending')
            self.assertEqual(final_rows[0][3], 20)
            self.assertEqual(final_rows[0][6] & 13, 13)  # 整合包、有元数据、休眠位都归并
            self.assertEqual(enrich['0'][2], 'Rust')
            self.assertEqual(enrich['1'][2], 'Python')
            self.assertEqual(meta['totalIndexed'], 2)
            self.assertEqual(meta['totalBrowsable'], 1)
            self.assertEqual(meta['curatedStatus']['old/desktop']['verdict'], 'pending')
            self.assertEqual(meta['repoAliases']['old/desktop'], 'new/desktop')


if __name__ == '__main__':
    unittest.main(verbosity=2)
