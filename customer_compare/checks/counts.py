"""Row count and distinct key count checks."""

from __future__ import annotations

from ..key_index import KeyIndex
from ..results import CheckResult


def row_count_check(idx: KeyIndex) -> CheckResult:
    source_rows, target_rows = len(idx.source_all), len(idx.target_all)
    return CheckResult("Row count", source_rows == target_rows, f"source={source_rows}, target={target_rows}")


def distinct_key_check(idx: KeyIndex) -> CheckResult:
    # Compared separately from row count: equal row counts can hide a missing row plus a duplicate.
    source_keys, target_keys = len(idx.source_keys), len(idx.target_keys)
    return CheckResult(
        "Distinct key count",
        source_keys == target_keys,
        f"source={source_keys}, target={target_keys}",
    )
