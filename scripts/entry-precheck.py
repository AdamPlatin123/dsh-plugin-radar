#!/usr/bin/env python3
"""Entry static precheck — the producer for the ``static`` evidence axis.

For every ``catalog/plugins/*.json`` entry whose ``package.name`` is non-empty,
this script looks the package up on the **public npm registry only** and checks
the **published tarball** with a pinned ``dsh-standards@1.6.8``::

    dsh-standards check <dir> --scope entry --entry-claim static --no-exec --json

The source repository is never cloned (no GitHub API, no codeload, no git).
The tarball is never installed and nothing in it is executed: ``npm pack`` runs
with ``--ignore-scripts`` and the checker runs with ``--no-exec``.

Outputs:

* ``data/entry-cache.json`` — ``schema: dsh-entry/v1``, entries keyed by
  ``github:<numeric-id>``.  ``normalize.py`` reads ``evidence_static`` from it;
  the workflow uploads it as a build artifact (no commit).
* ``reports/entry-precheck/latest.json`` — the same facts plus run counts, for
  human auditing; also uploaded as an artifact.

Non-blocking by design: every path returns exit code 0.  A single package
failure (404, timeout, malformed checker output, …) becomes ``not_run``.

``flow`` and ``boost`` are fixed constants here.  This script measures neither;
it does not decide admission, order or scores.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CACHE_REL = Path("data") / "entry-cache.json"
REPORT_REL = Path("reports") / "entry-precheck" / "latest.json"

sys.path.insert(0, str(ROOT / "engine" / "lib"))
from radar.atomicio import atomic_write_json  # noqa: E402
from radar.entryevidence import (  # noqa: E402
    STATIC_VALUES,
    entry_blocking,
    map_static,
    not_checked,
    raw_summary,
    report_shape_ok,
)

REGISTRY = "https://registry.npmjs.org/"
STANDARDS_VERSION = "1.6.8"
STANDARDS_SPEC = f"dsh-standards@{STANDARDS_VERSION}"
CACHE_SCHEMA = "dsh-entry/v1"
REPORT_SCHEMA = "dsh-entry-report/v1"

FLOW = "not_run"
BOOST = "not_measured"
DISCLAIMER = (
    "Static-only inspection of the published npm tarball; no source clone, "
    "install, or execution. Informational evidence, not a review outcome."
)

_PACKAGE_NAME_RE = re.compile(r"^(?:@[A-Za-z0-9._~-]+/)?[A-Za-z0-9._~-]+$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


# --------------------------------------------------------------------------- #
# catalog + cache documents
# --------------------------------------------------------------------------- #
def catalog_packages(root: Path) -> list[dict]:
    """Read catalog/plugins/*.json, keeping entries with a package name."""
    packages: list[dict] = []
    seen: set[str] = set()
    for path in sorted((root / "catalog" / "plugins").glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf8"))
        except (OSError, ValueError):
            continue
        if not isinstance(doc, dict):
            continue
        package = (doc.get("package") or {}).get("name")
        package = package.strip() if isinstance(package, str) else ""
        if not package or not _PACKAGE_NAME_RE.fullmatch(package):
            continue
        repo = doc.get("repository") or {}
        entry_id = doc.get("id")
        if not isinstance(entry_id, str):
            entry_id = f"github:{path.stem}"
        if not re.fullmatch(r"github:[0-9]+", entry_id):
            continue
        if entry_id in seen:
            continue
        seen.add(entry_id)
        packages.append(
            {
                "id": entry_id,
                "full_name": repo.get("full_name") if isinstance(repo.get("full_name"), str) else "",
                "repository": repo.get("full_name") if isinstance(repo.get("full_name"), str) else "",
                "package": package,
            }
        )
    return packages


def repository_full_name(value: Any) -> str | None:
    """Normalize an npm ``repository`` value to ``owner/repo``."""
    if isinstance(value, dict):
        value = value.get("url")
    if not isinstance(value, str):
        return None
    text = value.strip().removesuffix(".git").rstrip("/")
    if text.startswith("git+"):
        text = text[4:]
    match = re.search(r"github\.com[/:]([^/\s]+)/([^/\s]+)$", text)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    match = re.match(r"github:([^/\s]+)/([^/\s]+)$", text)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    return None


def repositories_match(expected: str, actual: str | None) -> bool:
    if not expected or not actual:
        return False
    return expected.strip().lower() == actual.strip().lower()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _base_entry(pkg: dict, checked_at: str) -> dict:
    return {
        "id": pkg["id"],
        "full_name": pkg.get("full_name", ""),
        "package": pkg["package"],
        "checked_at": checked_at,
        "evidence_static": "not_run",
        "raw": {"status": "not_run", "exit_code": None},
        "entry_blocking": {"pass": False, "checked": [], "not_checked": []},
        "not_checked": [],
        "flow": FLOW,
        "boost": BOOST,
        "disclaimer": DISCLAIMER,
    }


def make_not_run_entry(pkg: dict, checked_at: str, reason: str) -> dict:
    entry = _base_entry(pkg, checked_at)
    entry["not_run_reason"] = reason
    return entry


def make_checked_entry(
    pkg: dict,
    checked_at: str,
    report: dict,
    process_exit: int | None = None,
    commit: str | None = None,
) -> dict:
    """Build a cache entry from a valid checker report.

    ``raw.status`` is recorded for audit only; the mapped ``evidence_static``
    comes exclusively from :func:`radar.entryevidence.map_static`.
    """
    entry = _base_entry(pkg, checked_at)
    entry["evidence_static"] = map_static(report)
    entry["raw"] = raw_summary(report, process_exit)
    entry["entry_blocking"] = entry_blocking(report)
    entry["not_checked"] = not_checked(report)
    if isinstance(commit, str) and _COMMIT_RE.fullmatch(commit):
        entry["commit"] = commit
    return entry


def build_cache_doc(entries: dict, generated_at: str) -> dict:
    return {
        "schema": CACHE_SCHEMA,
        "generated_at": generated_at,
        "registry": REGISTRY,
        "standards": STANDARDS_SPEC,
        "disclaimer": DISCLAIMER,
        "entries": {key: entries[key] for key in sorted(entries)},
    }


def build_report_doc(entries: dict, generated_at: str) -> dict:
    counts = {value: 0 for value in STATIC_VALUES}
    for entry in entries.values():
        value = entry.get("evidence_static")
        if value in counts:
            counts[value] += 1
    return {
        "schema": REPORT_SCHEMA,
        "generated_at": generated_at,
        "registry": REGISTRY,
        "standards": STANDARDS_SPEC,
        "counts": counts,
        "entries": [entries[key] for key in sorted(entries)],
        "disclaimer": DISCLAIMER,
    }


#: Failures that may be transient. A downgrade to ``not_run`` for one of
#: these keeps the previous evidence instead of erasing a good result.
TRANSIENT_REASONS = frozenset(
    {
        "checker_unavailable",
        "network_error",
        "timeout",
        "npm_registry_error",
        "tarball_download_failed",
    }
)


def _payload(entry: dict) -> dict:
    """Entry content without the wall-clock ``checked_at``."""
    return {key: value for key, value in entry.items() if key != "checked_at"}


def merge_entry(previous: dict | None, new: dict) -> dict:
    """Merge one fresh result into the cache without inventing freshness.

    * A transient failure never overwrites a previous real result.
    * Identical content keeps the old ``checked_at`` so a re-run does not make
      the cache look newer than the evidence.
    """
    if isinstance(previous, dict):
        if (
            new.get("evidence_static") == "not_run"
            and new.get("not_run_reason") in TRANSIENT_REASONS
            and previous.get("evidence_static") != "not_run"
        ):
            return previous
        if _payload(previous) == _payload(new):
            return previous
    return new


def latest_checked_at(entries: dict, fallback: str) -> str:
    stamps = [entry.get("checked_at") for entry in entries.values() if isinstance(entry, dict)]
    stamps = [stamp for stamp in stamps if isinstance(stamp, str) and stamp]
    return max(stamps) if stamps else fallback


def load_cache_entries(path: Path) -> dict:
    """Merge base: keep previous entries so a filtered run does not delete them."""
    try:
        doc = json.loads(path.read_text(encoding="utf8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(doc, dict) or doc.get("schema") != CACHE_SCHEMA:
        return {}
    entries = doc.get("entries")
    if not isinstance(entries, dict):
        return {}
    return {
        key: value
        for key, value in entries.items()
        if isinstance(key, str) and key.startswith("github:") and isinstance(value, dict)
    }


# --------------------------------------------------------------------------- #
# npm / tarball / checker plumbing
# --------------------------------------------------------------------------- #
def _text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf8", errors="replace")
    return value or ""


def _run(cmd: list[str], *, cwd: Path, env: dict, timeout: int) -> tuple[subprocess.CompletedProcess, bool]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc, False
    except subprocess.TimeoutExpired as exc:
        proc = subprocess.CompletedProcess(
            cmd, 124, _text(exc.stdout), _text(exc.stderr)
        )
        return proc, True
    except OSError as exc:
        return subprocess.CompletedProcess(cmd, 127, "", str(exc)), False


def npm_env(workdir: Path) -> dict:
    """Environment that pins npm to the public registry and disables scripts.

    A private ``~/.npmrc`` (tokens, scoped registries) is deliberately not
    inherited.  No credentials are read or written.
    """
    user_npmrc = workdir / "empty-user.npmrc"
    global_npmrc = workdir / "empty-global.npmrc"
    user_npmrc.write_text("", encoding="utf8")
    global_npmrc.write_text("", encoding="utf8")
    env = os.environ.copy()
    for key in list(env):
        if key.lower().startswith("npm_config_"):
            env.pop(key, None)
    env.update(
        {
            "NPM_CONFIG_REGISTRY": REGISTRY,
            "NPM_CONFIG_USERCONFIG": str(user_npmrc),
            "NPM_CONFIG_GLOBALCONFIG": str(global_npmrc),
            "NPM_CONFIG_CACHE": str(workdir / "npm-cache"),
            "NPM_CONFIG_AUDIT": "false",
            "NPM_CONFIG_FUND": "false",
            "NPM_CONFIG_UPDATE_NOTIFIER": "false",
            "NPM_CONFIG_LOGLEVEL": "error",
            "NPM_CONFIG_IGNORE_SCRIPTS": "true",
        }
    )
    return env


def _npm_failure(proc: subprocess.CompletedProcess) -> str:
    text = f"{_text(proc.stdout)}\n{_text(proc.stderr)}".lower()
    if "e404" in text or "404 not found" in text:
        return "npm_404"
    if "etimedout" in text or "econnreset" in text or "enotfound" in text:
        return "network_error"
    return "npm_error"


def _resolve_package(pkg_name: str, workdir: Path, env: dict, timeout: int) -> tuple[dict | None, str | None]:
    proc, timed_out = _run(
        ["npm", "view", pkg_name, "version", "gitHead", "repository", "--json", f"--registry={REGISTRY}"],
        cwd=workdir,
        env=env,
        timeout=timeout,
    )
    if timed_out:
        return None, "timeout"
    if proc.returncode != 0:
        return None, _npm_failure(proc)
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return None, "parse_failed"
    if isinstance(data, str):
        version, commit, repo = data, None, None
    elif isinstance(data, dict):
        version, commit = data.get("version"), data.get("gitHead")
        repo = repository_full_name(data.get("repository"))
    else:
        return None, "parse_failed"
    if not isinstance(version, str) or not version:
        return None, "version_missing"
    if not isinstance(commit, str) or not _COMMIT_RE.fullmatch(commit):
        commit = None
    return {"version": version, "commit": commit, "repository": repo}, None


def _pack_package(
    pkg_name: str, version: str, workdir: Path, env: dict, timeout: int
) -> tuple[Path | None, str | None]:
    pack_dir = workdir / "tarball"
    pack_dir.mkdir(parents=True, exist_ok=True)
    proc, timed_out = _run(
        [
            "npm",
            "pack",
            "--ignore-scripts",
            "--json",
            "--pack-destination",
            str(pack_dir),
            f"--registry={REGISTRY}",
            f"{pkg_name}@{version}",
        ],
        cwd=workdir,
        env=env,
        timeout=timeout,
    )
    if timed_out:
        return None, "timeout"
    if proc.returncode != 0:
        return None, _npm_failure(proc)
    filename = ""
    try:
        data = json.loads(proc.stdout)
        if isinstance(data, list) and data and isinstance(data[0], dict):
            filename = data[0].get("filename") or ""
    except ValueError:
        pass
    tarballs: list[Path] = []
    if isinstance(filename, str) and filename and Path(filename).name == filename:
        candidate = pack_dir / filename
        if candidate.is_file():
            tarballs = [candidate]
    if not tarballs:
        tarballs = sorted(pack_dir.glob("*.tgz"))
    if not tarballs:
        return None, "tarball_missing"
    return tarballs[0], None


def _extract_package(tarball: Path, dest: Path) -> tuple[Path | None, str | None]:
    dest.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(tarball, "r:gz") as archive:
            archive.extractall(dest, filter="data")
    except (OSError, tarfile.TarError) as exc:
        return None, f"extract_failed:{type(exc).__name__}"
    package_dir = dest / "package"
    if (package_dir / "package.json").is_file():
        return package_dir, None
    for child in sorted(dest.iterdir()):
        if child.is_dir() and (child / "package.json").is_file():
            return child, None
    return None, "package_json_missing"


def ensure_standards(workdir: Path, env: dict, timeout: int) -> Path | None:
    """Return the pinned checker binary, installing it locally if needed."""
    override = os.environ.get("DSH_STANDARDS_BIN")
    if override:
        path = Path(override)
        if not path.is_file():
            return None
        proc, timed_out = _run(
            [str(path), "--version"], cwd=workdir, env=env, timeout=min(timeout, 30)
        )
        if timed_out or proc.returncode != 0 or STANDARDS_VERSION not in proc.stdout:
            print(
                f"[entry-precheck] DSH_STANDARDS_BIN is not {STANDARDS_VERSION}; ignoring",
                file=sys.stderr,
            )
            return None
        return path
    prefix = workdir / "standards"
    binary = prefix / "node_modules" / ".bin" / "dsh-standards"
    if binary.is_file():
        return binary
    proc, timed_out = _run(
        [
            "npm",
            "install",
            "--prefix",
            str(prefix),
            "--no-save",
            "--ignore-scripts",
            "--no-audit",
            "--no-fund",
            STANDARDS_SPEC,
        ],
        cwd=workdir,
        env=env,
        timeout=max(timeout, 120),
    )
    if timed_out or proc.returncode != 0:
        print(
            f"[entry-precheck] cannot install {STANDARDS_SPEC}: "
            f"{'timeout' if timed_out else _text(proc.stderr).strip()[:300]}",
            file=sys.stderr,
        )
        return None
    return binary if binary.is_file() else None


def _safe_dir_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value)


def check_package(
    pkg: dict,
    workdir: Path,
    standards_bin: Path,
    timeout: int,
    env: dict,
    checked_at: str,
) -> dict:
    """Check one package.  Never raises: every failure becomes ``not_run``."""
    try:
        return _check_package(pkg, workdir, standards_bin, timeout, env, checked_at)
    except Exception as exc:  # noqa: BLE001 - one bad package must not stop the run
        print(
            f"[entry-precheck] {pkg['id']} crashed ({type(exc).__name__}); recording not_run",
            file=sys.stderr,
        )
        traceback.print_exc()
        return make_not_run_entry(pkg, checked_at, f"unexpected_{type(exc).__name__}")


def _check_package(
    pkg: dict,
    workdir: Path,
    standards_bin: Path,
    timeout: int,
    env: dict,
    checked_at: str,
) -> dict:
    package_name = pkg["package"]
    pkg_work = workdir / _safe_dir_name(pkg["id"])
    pkg_work.mkdir(parents=True, exist_ok=True)

    resolved, reason = _resolve_package(package_name, workdir, env, timeout)
    if reason or resolved is None:
        return make_not_run_entry(pkg, checked_at, reason or "version_missing")

    expected_repo = pkg.get("repository") or ""
    actual_repo = resolved.get("repository")
    if not expected_repo:
        return make_not_run_entry(pkg, checked_at, "catalog_repository_missing")
    if not actual_repo:
        return make_not_run_entry(pkg, checked_at, "npm_repository_missing")
    if not repositories_match(expected_repo, actual_repo):
        return make_not_run_entry(pkg, checked_at, "npm_repository_mismatch")

    tarball, reason = _pack_package(package_name, resolved["version"], pkg_work, env, timeout)
    if reason or tarball is None:
        return make_not_run_entry(pkg, checked_at, reason or "tarball_missing")

    package_dir, reason = _extract_package(tarball, pkg_work / "unpacked")
    if reason or package_dir is None:
        return make_not_run_entry(pkg, checked_at, reason or "package_json_missing")

    try:
        manifest = json.loads((package_dir / "package.json").read_text(encoding="utf8"))
    except (OSError, ValueError):
        return make_not_run_entry(pkg, checked_at, "package_json_unreadable")
    if not isinstance(manifest, dict) or manifest.get("name") != package_name:
        return make_not_run_entry(pkg, checked_at, "package_name_mismatch")

    proc, timed_out = _run(
        [
            str(standards_bin),
            "check",
            str(package_dir),
            "--scope",
            "entry",
            "--entry-claim",
            "static",
            "--no-exec",
            "--json",
        ],
        cwd=workdir,
        env=env,
        timeout=timeout,
    )
    if timed_out:
        return make_not_run_entry(pkg, checked_at, "checker_timeout")
    try:
        report = json.loads(proc.stdout)
    except ValueError:
        return make_not_run_entry(pkg, checked_at, "checker_parse_failed")
    if not report_shape_ok(report):
        return make_not_run_entry(pkg, checked_at, "checker_report_incomplete")
    return make_checked_entry(pkg, checked_at, report, proc.returncode, resolved["commit"])


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ENTRY static evidence precheck (non-blocking)")
    parser.add_argument("--root", default=str(ROOT), help="repository root (default: this checkout)")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="ID|REPO|PACKAGE",
        help="only these catalog entries (repeatable); default: all",
    )
    parser.add_argument("--limit", type=int, default=None, help="max packages to check (0 = none)")
    parser.add_argument("--timeout", type=int, default=60, help="per-command timeout in seconds")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    workdir: Path | None = None
    try:
        packages = catalog_packages(root)
        if args.only:
            wanted = {item.strip().lower() for item in args.only if item.strip()}
            packages = [
                pkg
                for pkg in packages
                if pkg["id"].lower() in wanted
                or pkg.get("full_name", "").lower() in wanted
                or pkg["package"].lower() in wanted
            ]
        if args.limit is not None:
            packages = packages[: max(0, args.limit)]
        if not packages:
            print("[entry-precheck] no catalog packages selected; nothing to do")
            return 0

        workdir = Path(tempfile.mkdtemp(prefix="dsh-entry-precheck-"))
        env = npm_env(workdir)
        standards_bin = ensure_standards(workdir, env, args.timeout)
        checked_at = _now()
        entries = load_cache_entries(root / CACHE_REL)
        if standards_bin is None:
            # Do not erase previous evidence: a failed checker install is not a
            # finding about any package.
            print(
                f"[entry-precheck] {STANDARDS_SPEC} unavailable; leaving the cache untouched",
                file=sys.stderr,
            )
            return 0

        for index, pkg in enumerate(packages, start=1):
            print(f"[entry-precheck] {index}/{len(packages)} {pkg['id']} {pkg['package']}")
            entry = check_package(pkg, workdir, standards_bin, args.timeout, env, checked_at)
            entries[pkg["id"]] = merge_entry(entries.get(pkg["id"]), entry)
            current = entries[pkg["id"]]
            print(
                f"[entry-precheck]   -> {current['evidence_static']} "
                f"({current.get('not_run_reason', 'checked')})"
            )

        generated_at = latest_checked_at(entries, checked_at)
        atomic_write_json(root / CACHE_REL, build_cache_doc(entries, generated_at))
        atomic_write_json(root / REPORT_REL, build_report_doc(entries, generated_at))
        print(
            f"[entry-precheck] wrote {CACHE_REL} + {REPORT_REL} "
            f"({len(entries)} entr{'y' if len(entries) == 1 else 'ies'})"
        )
        return 0
    except Exception:  # noqa: BLE001 - non-blocking contract: always exit 0
        print("[entry-precheck] unexpected failure (non-blocking; exit 0)", file=sys.stderr)
        traceback.print_exc()
        return 0
    finally:
        if workdir is not None:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
