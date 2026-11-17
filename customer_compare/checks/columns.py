"""Column-by-column comparison of shared records, plus the whitespace warning.

Only the first target row for a key is compared. Other copies of a duplicated key
are reported by the duplicate check.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import ColumnRule
from ..key_index import KeyIndex
from ..results import CheckResult, report_row, status_for
from ..values import display_value, has_padding, values_match


@dataclass
class ColumnOutcome:
    rows_by_key: dict[str, list[dict]]   # one list of report rows per shared key
    failed_cells: set[tuple[str, str]]   # (key, source column) pairs that failed
    compared: int
    failed: int


def compare_columns(idx: KeyIndex, columns: tuple[ColumnRule, ...]) -> ColumnOutcome:
    rows_by_key: dict[str, list[dict]] = {}
    failed_cells: set[tuple[str, str]] = set()
    compared = failed = 0

    for key in idx.shared_keys:
        source_row = idx.source_first[key]
        target_row = idx.target_first[key]
        key_rows = []
        for rule in columns:
            ok = values_match(
                source_row[rule.source],
                target_row[rule.target],
                transforms=rule.transforms,
                compare=rule.compare,
                tolerance=rule.tolerance,
            )
            compared += 1
            if not ok:
                failed += 1
                failed_cells.add((key, rule.source))
            key_rows.append(
                report_row(
                    key,
                    rule.source,
                    display_value(source_row[rule.source], rule.compare),
                    display_value(target_row[rule.target], rule.compare),
                    status_for(ok),
                    rule.check_label,
                )
            )
        rows_by_key[key] = key_rows

    return ColumnOutcome(rows_by_key, failed_cells, compared, failed)


def outcome_check(outcome: ColumnOutcome) -> CheckResult:
    return CheckResult(
        "Column values and transformations",
        outcome.failed == 0,
        f"{outcome.failed} of {outcome.compared} compared cells failed",
    )


def whitespace_check(idx: KeyIndex, columns: tuple[ColumnRule, ...]) -> CheckResult:
    """Informational: counts mapped text values with leading or trailing spaces."""
    source_padded = sum(
        has_padding(value)
        for column in {rule.source for rule in columns}
        for value in idx.source_all[column]
    )
    target_padded = sum(
        has_padding(value)
        for column in {rule.target for rule in columns}
        for value in idx.target_all[column]
    )
    return CheckResult(
        "Leading or trailing spaces",
        True,
        f"{source_padded} source and {target_padded} target value(s) padded with spaces",
        warning=source_padded + target_padded > 0,
    )
