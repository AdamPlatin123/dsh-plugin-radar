"""Static (ENTRY) evidence mapping — pure functions, no I/O.

Turns a ``dsh-conformance/1`` report produced by::

    dsh-standards check <dir> --scope entry --entry-claim static --no-exec --json

into the single value the radar observation schema permits for
``evidence.static`` (see ``schema/observation.schema.json``).

Design rules
------------
* The mapping is intentionally conservative.  Only a report that explicitly
  says entry-blocking coverage passed, has no blocking/failed check and no
  hygiene/partial bucket entry, may map to ``pass``.
* ``conclusion.status`` is **never** an input.  The checker can emit
  ``status: "pass"`` while blocking checks are non-empty or while
  entry-blocking coverage is incomplete; copying that field would over-claim.
* A missing, truncated or malformed report maps to ``not_run``.  Callers that
  fetch or execute the checker are expected to map their own failures to
  ``not_run`` as well (see ``scripts/entry-precheck.py``).
"""

from __future__ import annotations

from typing import Any

SCHEMA = "dsh-conformance/1"

#: Values accepted by ``schema/observation.schema.json`` for ``evidence.*``.
STATIC_VALUES = ("pass", "warn", "fail", "not_run", "inconclusive")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def report_shape_ok(report: Any) -> bool:
    """Return True when *report* is a complete ``dsh-conformance/1`` document.

    This is a shape gate, not a verdict.  A report that does not carry the
    buckets/entryBlocking fields the mapping relies on is treated as
    unparseable (``not_run``) rather than guessed at.
    """
    if not isinstance(report, dict) or report.get("schema") != SCHEMA:
        return False
    buckets = report.get("buckets")
    coverage = report.get("coverage")
    if not isinstance(buckets, dict) or not isinstance(coverage, dict):
        return False
    blocking = coverage.get("entryBlocking")
    if not isinstance(blocking, dict):
        return False
    if not isinstance(blocking.get("pass"), bool):
        return False
    for key in ("failed", "checked", "notChecked"):
        if not isinstance(blocking.get(key), list):
            return False
    for key in ("blocking", "hygiene", "partial"):
        if not isinstance(buckets.get(key), list):
            return False
    return True


def map_static(report: Any) -> str:
    """Map a checker report to ``pass|warn|fail|not_run|inconclusive``.

    The order is fixed by the product rules:

    1. any blocking bucket item or any failed entry-blocking check -> ``fail``
    2. otherwise, ``coverage.entryBlocking.pass is False`` -> ``inconclusive``
       (an incomplete coverage set can never become ``pass``)
    3. otherwise, any hygiene/partial bucket item -> ``warn``
    4. otherwise -> ``pass``

    ``conclusion.status`` is deliberately ignored (see module docstring).
    """
    if not report_shape_ok(report):
        return "not_run"

    buckets = report["buckets"]
    entry_blocking = report["coverage"]["entryBlocking"]

    if buckets["blocking"] or entry_blocking["failed"]:
        return "fail"
    if entry_blocking["pass"] is False:
        return "inconclusive"
    if buckets["hygiene"] or buckets["partial"]:
        return "warn"
    return "pass"


def entry_blocking(report: Any) -> dict:
    """Extract the entry-blocking summary stored in the cache.

    ``pass`` is ``False`` when the report is unusable, so consumers never
    mistake a missing report for a successful coverage set.
    """
    if not report_shape_ok(report):
        return {"pass": False, "checked": [], "not_checked": []}
    blocking = report["coverage"]["entryBlocking"]
    return {
        "pass": bool(blocking["pass"]),
        "checked": _unique_strings(blocking["checked"]),
        "not_checked": _unique_strings(blocking["notChecked"]),
    }


def not_checked(report: Any) -> list[str]:
    """Return every check id the report lists as not checked (top level)."""
    if not isinstance(report, dict):
        return []
    items = report.get("notChecked")
    if not isinstance(items, list):
        return []
    out: list[str] = []
    for item in items:
        if isinstance(item, dict):
            check_id = item.get("id")
            if isinstance(check_id, str) and check_id not in out:
                out.append(check_id)
    return out


def raw_summary(report: Any, process_exit: int | None = None) -> dict:
    """Return the audit-only ``raw`` block stored next to the mapped value.

    ``raw.status`` is the checker's own conclusion status.  It is recorded for
    auditing only; :func:`map_static` must not read it.
    """
    status = "unknown"
    exit_code = process_exit if _is_int(process_exit) else None
    if isinstance(report, dict):
        conclusion = report.get("conclusion")
        if isinstance(conclusion, dict):
            value = conclusion.get("status")
            if isinstance(value, str):
                status = value
            code = conclusion.get("exitCode")
            if _is_int(code):
                exit_code = code
    return {"status": status, "exit_code": exit_code}


def _unique_strings(values: Any) -> list[str]:
    out: list[str] = []
    if not isinstance(values, list):
        return out
    for value in values:
        if isinstance(value, str) and value not in out:
            out.append(value)
    return out
