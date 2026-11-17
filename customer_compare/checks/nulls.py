"""NOT NULL constraints on the source and target sides."""

from __future__ import annotations

from ..config import ColumnRule
from ..key_index import KEY_COLUMN, KeyIndex
from ..results import CheckResult, report_row
from ..values import display_value, is_null


def find_violations(idx: KeyIndex, not_null_source: tuple[str, ...], not_null_target: tuple[str, ...]) -> list[dict]:
    """One entry per NULL that breaks a constraint. Checked on all rows, including NULL keys."""
    violations = []
    for side, frame, columns in (
        ("Source", idx.source_all, not_null_source),
        ("Target", idx.target_all, not_null_target),
    ):
        for column in columns:
            for _, record in frame[frame[column].map(is_null)].iterrows():
                violations.append(
                    {
                        "Side": side,
                        "Customer ID": record[KEY_COLUMN] or "NULL",
                        "Column": column,
                        "Check": "NOT_NULL",
                    }
                )
    return violations


def check(violations: list[dict]) -> CheckResult:
    return CheckResult("NULL constraints", not violations, f"{len(violations)} violation(s)")


def target_report_rows(
    idx: KeyIndex,
    violations: list[dict],
    columns: tuple[ColumnRule, ...],
    failed_cells: set[tuple[str, str]],
) -> dict[str, list[dict]]:
    """Report rows for target NULLs that the column comparison has not already flagged."""
    rule_by_target = {rule.target: rule for rule in columns}
    rows: dict[str, list[dict]] = {}
    for violation in violations:
        key = violation["Customer ID"]
        if violation["Side"] != "Target" or key == "NULL":
            continue
        rule = rule_by_target.get(violation["Column"])
        label = rule.source if rule else violation["Column"]
        if (key, label) in failed_cells:
            continue
        source_text = (
            display_value(idx.source_first[key][rule.source], rule.compare)
            if rule and key in idx.source_first
            else "-"
        )
        rows.setdefault(key, []).append(report_row(key, label, source_text, "NULL", "Fail", "NOT_NULL"))
    return rows
