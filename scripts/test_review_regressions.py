#!/usr/bin/env python3
"""test_review_regressions.py — 评审回归检查（数据口径 / 渲染稳定性 / 契约语义门禁）。

覆盖维护评审回归与 README 摘要、策展区块所有权和旧写入器保护：
  1. 站点烘焙全量保留行（不过滤 verdict）+ enrich 行索引与最终输出行一一对应
  2. 渲染器无有效快照：显式退出码 1 且不写任何文件（安全停旧，不得 NoneType 崩栈）
  3. 渲染器坏 schema 快照：同上优雅报错，不得 KeyError 崩栈
  4. 同一快照两次渲染逐字节一致（旧表尾部空行须被消费，不得逐轮累积）
  5. 契约校验器除 schema/数组长度外校验四档计数与 plugins[] 实际计数一致
     （schema 合法 ≠ 语义正确；自洽数据须放行，不误伤）
  6. 格式名正确但关键字段缺失、数组根及未知版本快照均保留旧 README 并非零退出

运行：python3 scripts/test_review_regressions.py（离线；依赖 jsonschema，与 CI 一致）
"""
import contextlib
import importlib.util
import io
import json
import re
import tempfile
import types
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf8')


class ReviewRegressions(unittest.TestCase):
    def summary_fixture(self):
        canonical = {'schema': 'radar-canonical/v1', 'export': {
            'anchor_run_id': '20261003T000000Z',
            'rows': [{'repo': 'a/one', 'verdict': 'ok'},
                     {'repo': 'b/two', 'verdict': 'pending'}],
            'stats': {'ok': 1, 'incompatible': 0, 'pending': 1, 'untested': 0},
        }}
        snapshot = {'run_id': '20261003T000000Z', 'generated_at': '2026-10-03T00:00:00Z'}
        text = ('<!-- README:layout:v2 -->\nstatic prefix\n'
                '<!-- AUTO:summary:START -->\nstale data\n<!-- AUTO:summary:END -->\n'
                'static suffix with architecture and QR\n')
        return text, canonical, snapshot

    def test_summary_preserves_unowned_text_and_is_idempotent(self):
        module = load_module('summary_stable', 'scripts/render-readme-from-snapshot.py')
        text, canonical, snapshot = self.summary_fixture()
        rendered = module.render_summary(text, canonical, snapshot)
        self.assertEqual(module.render_summary(rendered, canonical, snapshot), rendered)
        start, end = '<!-- AUTO:summary:START -->', '<!-- AUTO:summary:END -->'
        self.assertEqual(text.split(start)[0], rendered.split(start)[0])
        self.assertEqual(text.split(end)[1], rendered.split(end)[1])
        self.assertIn('| 全量记录 | 2 |', rendered)
        self.assertIn('| 可用记录 | 1 |', rendered)
        self.assertIn('| 待定记录 | 1 |', rendered)
        self.assertIn('2026-10-03 08:00:00 UTC+8', rendered)

    def test_summary_rejects_ambiguous_or_reversed_markers(self):
        module = load_module('summary_markers', 'scripts/render-readme-from-snapshot.py')
        text, canonical, snapshot = self.summary_fixture()
        start, end = '<!-- AUTO:summary:START -->', '<!-- AUTO:summary:END -->'
        for invalid in ('no markers', text.replace(end, ''), text + start,
                        text + end, end + '\n' + start):
            with self.subTest(text=invalid), self.assertRaises(ValueError):
                module.render_summary(invalid, canonical, snapshot)

    def test_summary_rejects_bad_counts_duplicate_repos_and_anchor(self):
        module = load_module('summary_counts', 'scripts/render-readme-from-snapshot.py')
        for defect in ('counts', 'duplicate', 'anchor', 'verdict'):
            text, canonical, snapshot = self.summary_fixture()
            if defect == 'counts':
                canonical['export']['stats']['ok'] = 9
            elif defect == 'duplicate':
                canonical['export']['rows'][1]['repo'] = 'A/ONE'
            elif defect == 'anchor':
                snapshot['run_id'] = '20261002T000000Z'
            else:
                canonical['export']['rows'][1]['verdict'] = 'gone'
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                module.render_summary(text, canonical, snapshot)

    def test_missing_summary_stops_before_generation_and_keeps_readme(self):
        module = load_module('summary_missing', 'scripts/render-readme-from-snapshot.py')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            module.ROOT, module.SNAP_DIR = root, root / 'data/snapshots'
            write_json(module.SNAP_DIR / '20261003T000000Z.json', {
                'schema': 'radar-snapshot/2', 'run_id': '20261003T000000Z',
                'generated_at': '2026-10-03T00:00:00Z', 'catalog_entries': [],
                'verdict': {}, 'discovery': {}, 'clone': {}, 'test': {}, 'deliver': {},
            })
            readme = root / 'README.md'
            readme.write_text('<!-- README:layout:v2 -->\nkeep existing content\n')
            original = readme.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(module.main(), 1)
            self.assertEqual(readme.read_bytes(), original)
            self.assertFalse((root / 'generated').exists())

    def test_curated_refresh_preserves_other_sections(self):
        with patch.dict('os.environ', {'GH_TOKEN': 'offline-test'}):
            module = load_module('curated_blocks', 'scripts/refresh-featured.py')
        text = ('prefix\n<!-- AUTO:featured:START -->old<!-- AUTO:featured:END -->\n'
                'middle\n<!-- AUTO:bundles:START -->old<!-- AUTO:bundles:END -->\nsuffix')
        featured = '<!-- AUTO:featured:START -->new featured<!-- AUTO:featured:END -->'
        bundles = '<!-- AUTO:bundles:START -->new bundles<!-- AUTO:bundles:END -->'
        rendered = module.replace_curated_blocks(text, featured, bundles)
        self.assertTrue(rendered.startswith('prefix\n'))
        self.assertTrue(rendered.endswith('\nsuffix'))
        self.assertIn('\nmiddle\n', rendered)
        self.assertEqual(module.replace_curated_blocks(rendered, featured, bundles), rendered)
        for invalid in (text.replace('<!-- AUTO:bundles:END -->', ''), text + featured,
                        text.replace('<!-- AUTO:bundles:START -->old<!-- AUTO:bundles:END -->',
                                     '<!-- AUTO:bundles:END --><!-- AUTO:bundles:START -->')):
            with self.subTest(text=invalid), self.assertRaises(ValueError):
                module.replace_curated_blocks(invalid, featured, bundles)

    def test_legacy_diagram_writer_cannot_replace_new_architecture(self):
        module = load_module('diagram_guard', 'scripts/gen-pipeline-diagram.py')
        with tempfile.TemporaryDirectory() as folder:
            readme = Path(folder) / 'README.md'
            readme.write_text('<!-- README:layout:v2 -->\n```mermaid\nflowchart TB\n```\n')
            original = readme.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()):
                module.inject(readme, 'old live diagram')
                module.refresh_badges(readme, {})
            self.assertEqual(readme.read_bytes(), original)

    def test_curated_job_writes_dedicated_page_and_keeps_readme(self):
        with patch.dict('os.environ', {'GH_TOKEN': 'offline-test'}):
            module = load_module('curated_job', 'scripts/refresh-featured.py')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            module.ROOT, module.DRY = str(root), False
            write_json(root / 'data/plugins-all.json',
                       json.loads((ROOT / 'data/plugins-all.json').read_text()))
            readme = root / 'README.md'
            readme.write_bytes(b'keep project homepage\n')
            target = root / 'docs/catalog-highlights.md'
            target.parent.mkdir()
            target.write_text((ROOT / 'docs/catalog-highlights.md').read_text())
            def offline_fetch(repo):
                return repo, 123, 'offline fixture'
            with patch.object(module, 'fetch', side_effect=offline_fetch), \
                    contextlib.redirect_stdout(io.StringIO()):
                module.main()
            self.assertEqual(readme.read_bytes(), b'keep project homepage\n')
            self.assertIn('123★', target.read_text())
            self.assertNotIn('tile-ok.svg', target.read_text())
            before_failure = target.read_bytes()
            with patch.object(module, 'fetch', return_value=None), \
                    contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                module.main()
            self.assertEqual(target.read_bytes(), before_failure)

    def test_baked_rows_keep_all_verdicts_and_enrich_index_aligned(self):
        """站点大表全量保留各档行；enrich 副表键=行序，元数据必须取自该行自身的仓库。

        历史缺陷：先按 verdict=ok 过滤输出行、却按未过滤行号生成 enrich，
        导致元数据整体错位（7,679 条错配）。当前行为已改为全量保留
        （不可回退），本测试同时钉住两点：行不丢档、索引不错位。
        """
        module = load_module('site_build_review', 'site/scripts/build_data.py')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            site = root / 'site'
            module.__file__ = str(site / 'scripts' / 'build_data.py')
            rows = [dict(repo=repo, name=repo, verdict=verdict, stars=1, desc='')
                    for repo, verdict in [('a/pending', 'pending'), ('b/ok', 'ok'), ('c/ok', 'ok')]]
            write_json(root / 'data/plugins-all.json', {'plugins': rows})
            write_json(root / 'generated/current/canonical.json', {'entries': []})
            write_json(root / 'data/plugins-enrich.json', {'entries': {
                'a/pending': {'lang': 'Python'}, 'b/ok': {'lang': 'TypeScript'},
                'c/ok': {'lang': 'Rust'},
            }})
            with contextlib.redirect_stdout(io.StringIO()):
                module.build(root)
            text = (site / 'src/data/plugins.ts').read_text()
            rows_out = json.loads(re.search(r'export const ROWS:.*? = (.*)', text)[1])
            enrich = json.loads(re.search(r'export const ENRICH:.*? = (.*)', text)[1])
            # 全量保留：pending 行也在输出中，顺序与输入一致
            self.assertEqual([r[0] for r in rows_out], ['a/pending', 'b/ok', 'c/ok'])
            # 索引对齐：第 i 条元数据来自第 i 行自身的仓库（含非 ok 行）
            self.assertEqual(set(enrich), {'0', '1', '2'})
            self.assertEqual(enrich['0'][2], 'Python')
            self.assertEqual(enrich['1'][2], 'TypeScript')
            self.assertEqual(enrich['2'][2], 'Rust')

    def test_missing_snapshot_exits_without_writing(self):
        """无快照目录：安全停旧 = 打印后返回非零，且不读写任何 README。"""
        module = load_module('render_missing_review', 'scripts/render-readme-from-snapshot.py')
        with tempfile.TemporaryDirectory() as folder:
            module.ROOT = module.SNAP_DIR = Path(folder)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(), 1)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_wrong_schema_snapshot_exits_without_writing(self):
        """快照 schema 名错误（非 radar-snapshot/*）：优雅返回非零，不得 KeyError 崩栈。"""
        module = load_module('render_invalid_review', 'scripts/render-readme-from-snapshot.py')
        with tempfile.TemporaryDirectory() as folder:
            module.ROOT = module.SNAP_DIR = Path(folder)
            write_json(Path(folder) / '20261001T000000Z.json', {'schema': 'error/v1'})
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(), 1)
            self.assertFalse((Path(folder) / 'README.md').exists())

    def test_same_snapshot_render_is_byte_stable(self):
        """同一快照两次渲染逐字节一致：旧版本表尾部的多余空行必须被消费。"""
        module = load_module('render_stable_review', 'scripts/render-readme-from-snapshot.py')
        generator = types.ModuleType('gen_plugins_all')
        generator.main = lambda: {'domains': {'other': {'total': 0}}, 'global': {'un': 0}}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            module.ROOT, module.SNAP_DIR = root, root / 'data/snapshots'
            write_json(module.SNAP_DIR / '20261001T000000Z.json', {
                'schema': 'radar-snapshot/2', 'run_id': '20261001T000000Z',
                'generated_at': '2026-10-01T00:00:00Z', 'catalog_entries': [],
                'verdict': {}, 'discovery': {}, 'clone': {}, 'test': {}, 'deliver': {},
            })
            write_json(root / 'data/runner-versions.json', {
                'latest': '0.1.5-rc.3',
                'versions': {'0.1.5-rc.3': {'ok': 5, 'fail': 1, 'inc': 0}},
            })
            (root / 'README.md').write_text(
                '# Radar\n\n[![confirmed](badge/confirmed-1)](#stats)\n\n'
                '**判定按 runner 版本分离 / verdicts by runner version：**\n\n'
                '| **累计 / cumulative** | **0** | **0** | **0** | **0** |\n\n\n'
                '---\n\n## 工作原理\n'
                '> 渲染于快照 20260930T000000Z（旧数据）\n'
                '> 按版本分解 / by runner version：old\n\n'
                '> *Rendered from snapshot old*\n', encoding='utf8')
            with patch.dict('sys.modules', {'gen_plugins_all': generator}), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(), 0)
                first = (root / 'README.md').read_bytes()
                self.assertEqual(module.main(), 0)
                self.assertEqual((root / 'README.md').read_bytes(), first)

    def test_malformed_snapshot_preserves_existing_readme(self):
        module = load_module('render_malformed_review', 'scripts/render-readme-from-snapshot.py')
        for doc in ([1], {'schema': 'radar-snapshot/2'},
                    {'schema': 'radar-snapshot/9', 'run_id': 'unknown'}):
            with self.subTest(snapshot=doc), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                module.ROOT, module.SNAP_DIR = root, root / 'data/snapshots'
                write_json(module.SNAP_DIR / '20261001T000000Z.json', doc)
                readme = root / 'README.md'
                readme.write_bytes(b'keep existing content\n')
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(module.main(), 1)
                self.assertEqual(readme.read_bytes(), b'keep existing content\n')

    def test_contract_rejects_wrong_counts_with_matching_array_length(self):
        """四档语义门禁：schema 合法、total_listed 相符、但 stats.ok 虚报 → 必须失败；
        自洽数据（四档与数组逐条计数一致）→ 必须放行，不误伤。"""
        module = load_module('contracts_review', 'scripts/validate_contracts.py')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'schema').symlink_to(ROOT / 'schema', target_is_directory=True)
            (root / 'data').mkdir()
            # 合成自洽数据（schema 要求 plugins ≥1000 条）
            plugins = [{'repo': f'u{i % 50}/r{i}', 'name': f'n{i}',
                        'verdict': 'ok' if i % 2 else ('pending' if i % 7 == 0 else 'incompatible'),
                        'stars': i, 'desc': ''}
                       for i in range(1200)]
            cnt = Counter(p['verdict'] for p in plugins)
            latest = {
                'schema': 'dsh-radar/v1', 'generated_at': '2026-10-01T00:00:00Z',
                'snapshot_run_id': '20261001T000000Z',
                'stats': {'ok': cnt['ok'], 'incompatible': cnt['incompatible'],
                          'pending': cnt['pending'], 'untested': cnt['untested'],
                          'gone': 0, 'ambiguous': 0, 'unlocated': 0},
                'total_listed': len(plugins), 'runner_versions': {},
                'data': {'plugins_all': 'data/plugins-all.json', 'snapshots_dir': 'data/snapshots/'},
            }
            write_json(root / 'data/plugins-all.json',
                       {'schema': 'dsh-radar/v1', 'generated_at': '2026-10-01T00:00:00Z',
                        'plugins': plugins})
            # 对照组：自洽数据放行（仅校验 latest/plugins_all，无 catalog/快照目录）
            write_json(root / 'data/latest.json', latest)
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(module.validate(root), 0)
            # 实验组：schema 仍合法、total_listed 仍相符，仅 stats.ok 虚报 +1
            latest['stats'] = {**latest['stats'], 'ok': latest['stats']['ok'] + 1}
            write_json(root / 'data/latest.json', latest)
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(module.validate(root), 1)


if __name__ == '__main__':
    unittest.main()
