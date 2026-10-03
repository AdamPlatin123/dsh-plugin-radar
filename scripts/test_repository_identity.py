#!/usr/bin/env python3
"""仓库改名/转移、同仓类型标签、判定冲突与写入唯一性回归（离线）。"""
import importlib.util
import itertools
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine/lib'))
from radar.repository_identity import RepositoryIdentities, dedupe_public_rows  # noqa: E402

spec = importlib.util.spec_from_file_location('identity_canonical', ROOT / 'engine/aggregation/build_canonical.py')
canonical = importlib.util.module_from_spec(spec)
spec.loader.exec_module(canonical)


def verified():
    return [
        {'canonical_id': 'github:1', 'full_name': 'a/dsh-desktop',
         'aliases': ['a/old-desktop'], 'checked_at': '2026-10-03'},
        {'canonical_id': 'github:2', 'full_name': 'new/deepseek-harness-desktop',
         'aliases': ['old/deepseek-harness-desktop'], 'checked_at': '2026-10-03'},
    ]


class RepositoryIdentityTests(unittest.TestCase):
    def test_export_normalizes_stale_canonical_rows_and_recounts(self):
        spec = importlib.util.spec_from_file_location('identity_export', ROOT / 'scripts/export-data.py')
        exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exporter)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'generated/current').mkdir(parents=True)
            (root / 'data').mkdir()
            (root / 'data/repository-identities.json').write_text(json.dumps({'entries': verified()}))
            (root / 'generated/current/canonical.json').write_text(json.dumps({'export': {
                'rows': [
                    {'repo': 'a/old-desktop', 'name': 'old', 'verdict': 'ok', 'stars': 10, 'desc': 'desktop'},
                    {'repo': 'a/dsh-desktop', 'name': 'new', 'verdict': 'incompatible', 'stars': 20, 'desc': 'desktop〔📦〕'},
                ], 'stats': {'ok': 1, 'incompatible': 1, 'pending': 0, 'untested': 0, 'gone': 5},
                'anchor_run_id': '20261003T000000Z'}}))
            stats, rows, anchor = exporter.from_canonical(root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['repo'], 'a/dsh-desktop')
            self.assertEqual(stats, {'ok': 0, 'incompatible': 0, 'pending': 1, 'untested': 0, 'gone': 5})
            self.assertEqual(anchor, '20261003T000000Z')

    def test_enrichment_persists_stable_identity_for_future_renames(self):
        spec = importlib.util.spec_from_file_location('identity_enrich', ROOT / 'scripts/enrich-repos.py')
        enrich = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(enrich)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'data').mkdir()
            (root / 'data/plugins-all.json').write_text(json.dumps({'plugins': [
                {'repo': 'old/desktop', 'stars': 20}]}))
            (root / 'data/enrich-cache.json').write_text(json.dumps({'entries': {
                'old/desktop': {'readme_image': 'https://example.org/image.png'}}}))
            with patch.multiple(enrich, ROOT=root, CACHE=root / 'data/enrich-cache.json',
                                SIDECAR=root / 'data/plugins-enrich.json', DRY=False), \
                    patch.object(enrich.ghql, 'resolve_token', return_value='offline'), \
                    patch.object(enrich.ghql, 'gql_batch', return_value={'old/desktop': {
                        'databaseId': 1, 'nameWithOwner': 'new/desktop', 'stargazerCount': 30}}), \
                    patch.object(enrich.time, 'sleep'):
                self.assertEqual(enrich.main(), 0)
            sidecar = json.loads((root / 'data/plugins-enrich.json').read_text())
            record = sidecar['entries']['old/desktop']
            self.assertEqual(record['canonical_id'], 'github:1')
            self.assertEqual(record['full_name'], 'new/desktop')
            self.assertTrue(record['identity_checked_at'])
            self.assertEqual(record['readme_image'], 'https://example.org/image.png')
            self.assertEqual(RepositoryIdentities.load(root).resolve('old/desktop'), 'new/desktop')

    def test_rename_transfer_case_and_separate_projects(self):
        ids = RepositoryIdentities(verified=verified())
        self.assertEqual(ids.resolve('A/OLD-DESKTOP'), 'a/dsh-desktop')
        self.assertEqual(ids.resolve('old/deepseek-harness-desktop'), 'new/deepseek-harness-desktop')
        self.assertEqual(ids.resolve('other/dsh-desktop'), 'other/dsh-desktop')
        self.assertEqual(ids.resolve('fork/old-desktop'), 'fork/old-desktop')

    def test_stable_id_follows_newer_metadata_and_retains_old_aliases(self):
        ids = RepositoryIdentities(
            repo_map={'old': {'full_name': 'old/deepseek-harness-desktop', 'canonical_id': 'github:2'}},
            enrich={'new/deepseek-harness-desktop': {
                'full_name': 'latest/dsh-desktop', 'canonical_id': 'github:2',
                'identity_checked_at': '2026-10-04T00:00:00Z'}},
            verified=verified(),
        )
        self.assertEqual(ids.resolve('old/deepseek-harness-desktop'), 'latest/dsh-desktop')
        self.assertEqual(ids.resolve('new/deepseek-harness-desktop'), 'latest/dsh-desktop')

    def test_invalid_or_ambiguous_identity_fails_closed(self):
        for entries in (
            [{'full_name': 'https://bad.example/repo', 'aliases': []}],
            [{'full_name': 'a/one', 'aliases': ['alias/repo']},
             {'full_name': 'b/two', 'aliases': ['alias/repo']}],
        ):
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                RepositoryIdentities(verified=entries)

    def test_public_rows_merge_bundle_label_stars_and_keep_conflict(self):
        ids = RepositoryIdentities(verified=verified())
        rows = [
            {'repo': 'a/old-desktop', 'name': 'old', 'stars': None, 'desc': 'desktop', 'verdict': 'ok'},
            {'repo': 'a/dsh-desktop', 'name': 'new', 'stars': 30, 'desc': 'desktop〔📦〕', 'verdict': 'incompatible'},
            {'repo': 'A/DSH-DESKTOP', 'name': 'new', 'stars': 20, 'desc': 'desktop〔PR〕', 'verdict': 'ok'},
        ]
        for order in itertools.permutations(rows):
            result = dedupe_public_rows(order, ids)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['verdict'], 'pending')
            self.assertEqual(result[0]['stars'], 30)
            self.assertIn('〔📦〕', result[0]['desc'])
            self.assertIn('〔PR〕', result[0]['desc'])
        self.assertEqual(rows[0]['repo'], 'a/old-desktop')

    def test_canonical_conflict_is_sticky_across_third_record(self):
        for verdicts in itertools.permutations(['✅ 运行级可用', '❌ 运行级不兼容', '✅ 运行级可用']):
            entries = [{'name': 'dsh-desktop', 'url': 'https://github.com/a/dsh-desktop',
                        'verdict': v, 'bundle': i == 1} for i, v in enumerate(verdicts)]
            result, _ = canonical.canonical_merge(entries, {}, {})
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['verdict'], '⚠️ 待定')
            self.assertTrue(result[0]['bundle'])

    def test_actual_build_merges_before_catalog_stats_and_export(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'data/snapshots').mkdir(parents=True)
            entries = [
                {'name': 'old-desktop', 'url': 'https://github.com/a/old-desktop',
                 'verdict': '✅ 运行级可用', 'star': 10},
                {'name': 'dsh-desktop', 'url': 'https://github.com/a/dsh-desktop',
                 'verdict': '❌ 运行级不兼容', 'star': 20, 'bundle': True},
                {'name': 'unresolved', 'url': 'https://github.com/search?q=unresolved',
                 'verdict': '✅ 运行级可用', 'star': 15},
                {'name': 'dsh-desktop', 'url': 'https://github.com/other/dsh-desktop',
                 'verdict': '✅ 运行级可用', 'star': 5},
            ]
            for entry in entries:
                entry.update(domain='🛠 基建部署', desc='desktop')
            (root / 'data/snapshots/20261003T000000Z.json').write_text(json.dumps({
                'schema': 'radar-snapshot/2', 'run_id': '20261003T000000Z',
                'generated_at': '2026-10-03T00:00:00Z', 'catalog_entries': entries}))
            (root / 'data/repository-identities.json').write_text(json.dumps({'entries': verified()}))
            (root / 'data/locate-cache.json').write_text(json.dumps({'entries': {
                'unresolved': {'status': 'found', 'full_name': 'a/old-desktop'}}}))
            (root / 'PLUGINS.md').write_text('| old | [old](https://github.com/a/old-desktop) | desktop |\n')
            replacements = {'ROOT': root, 'SNAP_DIR': root / 'data/snapshots',
                            'BASELINE': root / 'data/baseline.json', 'LOCATE_CACHE': root / 'data/locate-cache.json',
                            'DESC_CACHE': root / 'data/desc-cache.json', 'REPO_MAP': root / 'data/repo-map.json',
                            'URL_AUDIT': root / 'data/url-audit.json', 'OUT': root / 'generated/current/canonical.json',
                            'PLATFORM_REPOS': set()}
            with patch.multiple(canonical, **replacements):
                result = canonical.build(root)
            actual = result['entries']
            self.assertEqual(len(actual), 2)
            self.assertEqual({e['url'] for e in actual},
                             {'https://github.com/a/dsh-desktop', 'https://github.com/other/dsh-desktop'})
            merged = next(e for e in actual if '/a/' in e['url'])
            self.assertTrue(merged['bundle'])
            self.assertEqual(merged['verdict'], '⚠️ 待定')
            rows = result['export']['rows']
            self.assertEqual(len(rows), 2)
            self.assertEqual(result['global']['located'], 2)
            self.assertEqual(result['domain_stats']['🛠 基建部署']['total'], 2)
            self.assertEqual(Counter(r['verdict'] for r in rows), {'ok': 1, 'pending': 1})
            self.assertEqual(result['export']['stats']['pending'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
