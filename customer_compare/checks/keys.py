"""Missing, extra and duplicate business keys."""

from __future__ import annotations

import pandas as pd

from ..key_index import KEY_COLUMN, KeyIndex
from ..results import RECORD_COLUMN, CheckResult, report_row


# --- checks -----------------------------------------------------------------

def missing_and_extra_checks(idx: KeyIndex) -> list[CheckResult]:
    return [
        CheckResult("Missing records", not idx.missing_keys, f"{len(idx.missing_keys)} in source, not in target"),
        CheckResult("Extra records", not idx.extra_keys, f"{len(idx.extra_keys)} in target, not in source"),
    ]


def duplicate_checks(idx: KeyIndex) -> list[CheckResult]:
    return [
        CheckResult(
            "Duplicate keys (source)",
            not idx.duplicate_source_keys,
            f"{len(idx.duplicate_source_keys)} duplicated key(s)",
        ),
        CheckResult(
            "Duplicate keys (target)",
            not idx.duplicate_target_keys,
            f"{len(idx.duplicate_target_keys)} duplicated key(s)",
        ),
    ]


# --- report rows ------------------------------------------------------------

def missing_row(key: str) -> dict:
    return report_row(key, RECORD_COLUMN, "PRESENT", "MISSING", "Fail", "MISSING")


def extra_row(key: str) -> dict:
    return report_row(key, RECORD_COLUMN, "MISSING", "PRESENT", "Fail", "EXTRA")


def duplicate_row(idx: KeyIndex, key: str, key_column: str) -> dict:
    return report_row(
        key,
        key_column,
        f"{idx.source_counts.get(key, 0)} row(s)",
        f"{idx.target_counts.get(key, 0)} row(s)",
        "Fail",
        "DUPLICATE",
    )


# --- detail sheets ----------------------------------------------------------

def missing_records(idx: KeyIndex) -> pd.DataFrame:
    """Full records that exist on only one side."""
    return pd.concat(
        [
            _tagged(idx.source_valid, idx.source_valid[KEY_COLUMN].isin(idx.missing_keys), "Target", "Missing In"),
            _tagged(idx.target_valid, idx.target_valid[KEY_COLUMN].isin(idx.extra_keys), "Source", "Missing In"),
        ]
    ).reset_index(drop=True)


def duplicate_records(idx: KeyIndex) -> pd.DataFrame:
    """Every copy of a duplicated key, with the side it came from."""
    return pd.concat(
        [
            _tagged(idx.source_valid, idx.source_valid[KEY_COLUMN].isin(idx.duplicate_source_keys), "Source", "Side"),
            _tagged(idx.target_valid, idx.target_valid[KEY_COLUMN].isin(idx.duplicate_target_keys), "Target", "Side"),
        ]
    ).reset_index(drop=True)


def _tagged(frame: pd.DataFrame, mask: pd.Series, label: str, column_name: str) -> pd.DataFrame:
    part = frame[mask].drop(columns=KEY_COLUMN)
    part.insert(0, column_name, label)
    return part
