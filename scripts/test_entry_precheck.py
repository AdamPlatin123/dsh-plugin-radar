#!/usr/bin/env python3
"""Offline regressions for the ENTRY static evidence producer + consumer.

No network, no npm, no checker installation: the mapping, cache document,
script no-op path and cache merge rules are all exercised locally.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine" / "lib"))
from radar.entryevidence import (  # noqa: E402
    STATIC_VALUES,
    entry_blocking,
    map_static,
    not_checked,
    raw_summary,
    report_shape_ok,
)

PRE_CHECK = ROOT / "scripts" / "entry-precheck.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


precheck = load_module(PRE_CHECK, "entry_precheck")


def report(
    *,
    status: str = "pass",
    blocking: list | None = None,
    hygiene: list | None = None,
    partial: list | None = None,
    pass_: bool = True,
    failed: list | None = None,
    checked: list | None = None,
    blocking_not_checked: list | None = None,
    top_not_checked: list | None = None,
) -> dict:
    return {
        "schema": "dsh-conformance/1",
        "buckets": {
            "blocking": blocking or [],
            "hygiene": hygiene or [],
            "partial": partial or [],
        },
        "coverage": {
            "entryBlocking": {
                "pass": pass_,
                "failed": failed or [],
                "checked": checked if checked is not None else ["C-1.1", "C-1.2", "C-1.4"],
                "notChecked": blocking_not_checked if blocking_not_checked is not None else ["C-3.1"],
            }
        },
        "conclusion": {"status": status, "exitCode": 0 if status in ("pass", "warn") else 1},
        "notChecked": top_not_checked or [],
    }


class EvidenceMappingTests(unittest.TestCase):
    def test_status_pass_with_blocking_is_fail_not_pass(self):
        # Real reports can say status=pass while blocking is non-empty; the
        # conclusion status must never be copied into evidence.
        rep = report(status="pass", blocking=[{"id": "DSC-01", "result": "FAIL"}])
        self.assertEqual(map_static(rep), "fail")
        self.assertEqual(raw_summary(rep)["status"], "pass")

    def test_failed_entry_blocking_is_fail(self):
        self.assertEqual(map_static(report(failed=["C-1.2"])), "fail")

    def test_incomplete_entry_blocking_is_inconclusive_never_pass(self):
        rep = report(status="pass", pass_=False, hygiene=[{"id": "DSC-02"}])
        self.assertEqual(map_static(rep), "inconclusive")

    def test_missing_or_malformed_report_is_not_run(self):
        for value in (None, {}, [], {"schema": "dsh-conformance/1"}, report()["buckets"]):
            with self.subTest(value=value):
                self.assertEqual(map_static(value), "not_run")
                self.assertFalse(report_shape_ok(value))

    def test_hygiene_and_partial_warn(self):
        self.assertEqual(map_static(report(hygiene=[{"id": "DSC-11"}])), "warn")
        self.assertEqual(map_static(report(partial=[{"id": "DSC-04"}])), "warn")

    def test_clean_coverage_passes(self):
        self.assertEqual(map_static(report()), "pass")

    def test_entry_blocking_and_not_checked_extraction(self):
        rep = report(
            pass_=False,
            blocking_not_checked=["C-3.1", "C-3.2"],
            top_not_checked=[{"id": "C-3"}, {"id": "C-14"}, {"id": "C-4"}],
        )
        self.assertEqual(
            entry_blocking(rep),
            {"pass": False, "checked": ["C-1.1", "C-1.2", "C-1.4"],
             "not_checked": ["C-3.1", "C-3.2"]},
        )
        self.assertEqual(not_checked(rep), ["C-3", "C-14", "C-4"])


class CacheDocumentTests(unittest.TestCase):
    PKG = {"id": "github:1001", "full_name": "acme/dsh-demo", "package": "dsh-demo"}
    PKG2 = {"id": "github:1002", "full_name": "acme/dsh-other", "package": "dsh-other"}

    def test_cache_schema_and_entry_fields(self):
        checked = precheck.make_checked_entry(
            self.PKG,
            "2026-11-07T00:00:00Z",
            report(blocking=[{"id": "DSC-01"}]),
            process_exit=1,
            commit="a" * 40,
        )
        self.assertEqual(checked["evidence_static"], "fail")
        self.assertEqual(checked["raw"], {"status": "pass", "exit_code": 0})
        self.assertEqual(checked["flow"], "not_run")
        self.assertEqual(checked["boost"], "not_measured")
        self.assertEqual(checked["commit"], "a" * 40)

        empty = precheck.make_not_run_entry(
            self.PKG2, "2026-11-07T00:00:00Z", "npm_404"
        )
        doc = precheck.build_cache_doc(
            {checked["id"]: checked, empty["id"]: empty},
            "2026-11-07T00:00:00Z",
        )
        self.assertEqual(doc["schema"], "dsh-entry/v1")
        self.assertEqual(doc["registry"], "https://registry.npmjs.org/")
        self.assertEqual(doc["standards"], "dsh-standards@1.6.8")
        entries = doc["entries"]
        self.assertEqual(set(entries), {"github:1001", "github:1002"})
        required = {
            "id", "full_name", "package", "checked_at", "evidence_static",
            "raw", "entry_blocking", "not_checked", "flow", "boost", "disclaimer",
        }
        for entry in entries.values():
            self.assertTrue(required <= set(entry), required - set(entry))
            self.assertIn(entry["evidence_static"], STATIC_VALUES)
            self.assertEqual(entry["flow"], "not_run")
            self.assertEqual(entry["boost"], "not_measured")
            self.assertEqual(set(entry["entry_blocking"]), {"pass", "checked", "not_checked"})
            self.assertEqual(set(entry["raw"]), {"status", "exit_code"})
        self.assertEqual(empty["evidence_static"], "not_run")
        self.assertEqual(empty["raw"], {"status": "not_run", "exit_code": None})
        self.assertEqual(empty["not_run_reason"], "npm_404")
        # The document must survive a JSON round-trip (cache is JSON on disk).
        self.assertEqual(json.loads(json.dumps(doc)), doc)

    def test_report_document_counts(self):
        good = precheck.make_checked_entry(self.PKG, "2026-11-07T00:00:00Z", report())
        bad = precheck.make_not_run_entry(self.PKG, "2026-11-07T00:00:00Z", "timeout")
        doc = precheck.build_report_doc(
            {"github:1": good, "github:2": bad}, "2026-11-07T00:00:00Z"
        )
        self.assertEqual(doc["schema"], "dsh-entry-report/v1")
        self.assertEqual(doc["counts"]["pass"], 1)
        self.assertEqual(doc["counts"]["not_run"], 1)

    def test_catalog_skips_empty_or_invalid_package(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "catalog/plugins").mkdir(parents=True)
            (root / "catalog/plugins/1.json").write_text(json.dumps({
                "id": "github:1",
                "repository": {"full_name": "a/b"},
                "package": {"name": "dsh-demo"},
            }))
            (root / "catalog/plugins/2.json").write_text(json.dumps({
                "id": "github:2",
                "repository": {"full_name": "c/d"},
                "package": {"name": ""},
            }))
            self.assertEqual(
                precheck.catalog_packages(root),
                [{"id": "github:1", "full_name": "a/b", "repository": "a/b", "package": "dsh-demo"}],
            )


class ScriptExitTests(unittest.TestCase):
    def test_no_selected_packages_exits_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, str(PRE_CHECK), "--root", folder, "--limit", "0"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("nothing to do", result.stdout)
            self.assertFalse((Path(folder) / "data/entry-cache.json").exists())

    def test_missing_catalog_exits_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, str(PRE_CHECK), "--root", folder],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


class RepositoryBacklinkTests(unittest.TestCase):
    def test_parses_common_npm_repository_forms(self):
        self.assertEqual(
            precheck.repository_full_name({"url": "git+https://github.com/Owner/Repo.git"}),
            "Owner/Repo",
        )
        self.assertEqual(precheck.repository_full_name("https://github.com/owner/repo"), "owner/repo")
        self.assertEqual(precheck.repository_full_name("github:owner/repo"), "owner/repo")
        self.assertIsNone(precheck.repository_full_name(None))
        self.assertIsNone(precheck.repository_full_name("https://gitlab.com/a/b"))

    def test_match_is_case_insensitive_and_requires_both_sides(self):
        self.assertTrue(precheck.repositories_match("Owner/Repo", "owner/repo"))
        self.assertFalse(precheck.repositories_match("a/b", "a/c"))
        self.assertFalse(precheck.repositories_match("", "a/b"))
        self.assertFalse(precheck.repositories_match("a/b", None))

    def test_mismatched_repository_is_not_run(self):
        pkg = {
            "id": "github:1",
            "full_name": "me/repo",
            "repository": "me/repo",
            "package": "dsh-demo",
        }
        original = precheck._resolve_package
        precheck._resolve_package = lambda *args, **kwargs: (
            {"version": "1.0.0", "commit": None, "repository": "other/repo"},
            None,
        )
        try:
            with tempfile.TemporaryDirectory() as folder:
                entry = precheck.check_package(
                    pkg, Path(folder), Path("/bin/true"), 5, {}, "2026-11-07T00:00:00Z"
                )
        finally:
            precheck._resolve_package = original
        self.assertEqual(entry["evidence_static"], "not_run")
        self.assertEqual(entry["not_run_reason"], "npm_repository_mismatch")

class MergeSafetyTests(unittest.TestCase):
    PKG = {"id": "github:2001", "full_name": "acme/dsh-demo", "package": "dsh-demo"}

    def checked(self, checked_at: str, status: str = "pass") -> dict:
        return precheck.make_checked_entry(self.PKG, checked_at, report(status=status))

    def test_transient_failure_keeps_previous_evidence(self):
        prev = self.checked("2026-11-07T00:00:00Z")
        new = precheck.make_not_run_entry(self.PKG, "2026-11-08T00:00:00Z", "timeout")
        self.assertIs(precheck.merge_entry(prev, new), prev)

    def test_permanent_downgrade_is_recorded(self):
        prev = self.checked("2026-11-07T00:00:00Z")
        new = precheck.make_not_run_entry(self.PKG, "2026-11-08T00:00:00Z", "npm_404")
        self.assertIs(precheck.merge_entry(prev, new), new)

    def test_identical_payload_keeps_checked_at(self):
        prev = self.checked("2026-11-07T00:00:00Z")
        same = self.checked("2026-11-08T00:00:00Z")
        merged = precheck.merge_entry(prev, same)
        self.assertIs(merged, prev)
        self.assertEqual(merged["checked_at"], "2026-11-07T00:00:00Z")

    def test_changed_payload_updates_checked_at(self):
        prev = self.checked("2026-11-07T00:00:00Z", status="pass")
        changed = self.checked("2026-11-08T00:00:00Z", status="warn")
        merged = precheck.merge_entry(prev, changed)
        self.assertIs(merged, changed)

    def test_latest_checked_at_wins(self):
        entries = {
            "a": {"checked_at": "2026-11-07T00:00:00Z"},
            "b": {"checked_at": "2026-11-09T00:00:00Z"},
        }
        self.assertEqual(precheck.latest_checked_at(entries, "fallback"), "2026-11-09T00:00:00Z")


if __name__ == "__main__":
    unittest.main(verbosity=2)
