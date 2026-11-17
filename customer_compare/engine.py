"""Runs a comparison end to end: load, index keys, run each check, assemble the report.

The individual checks live in customer_compare/checks/. This module only decides
the order, combines the results, and builds the report rows in key order.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from .checks import columns as column_checks
from .checks import counts
from .checks import keys as key_checks
from .checks import nulls
from .config import Config, ConfigError
from .connectors import load_side
from .key_index import KeyIndex, build_key_index
from .results import REPORT_COLUMNS, RunResult, CheckResult

NULL_COLUMNS = ["Side", "Customer ID", "Column", "Check"]


def run_comparison(
    cfg: Config,
    source_df: pd.DataFrame | None = None,
    target_df: pd.DataFrame | None = None,
) -> RunResult:
    """Run all checks. DataFrames can be passed in directly (the unit tests do this)."""
    source = load_side(cfg.source) if source_df is None else source_df
    target = load_side(cfg.target) if target_df is None else target_df
    _validate_columns(cfg, source, target)

    idx = build_key_index(cfg, source, target)
    outcome = column_checks.compare_columns(idx, cfg.columns)
    violations = nulls.find_violations(idx, cfg.not_null_source, cfg.not_null_target)
    null_rows = nulls.target_report_rows(idx, violations, cfg.columns, outcome.failed_cells)

    rows = _report_rows(cfg, idx, outcome.rows_by_key, null_rows)
    if not cfg.report_passes:
        rows = [row for row in rows if row["Status"] == "Fail"]

    return RunResult(
        config_name=cfg.name,
        run_at=datetime.now().isoformat(timespec="seconds"),
        source_rows=len(idx.source_all),
        target_rows=len(idx.target_all),
        source_keys=len(idx.source_keys),
        target_keys=len(idx.target_keys),
        checks=_checks(cfg, idx, outcome, violations),
        report=pd.DataFrame(rows, columns=REPORT_COLUMNS),
        null_violations=pd.DataFrame(violations, columns=NULL_COLUMNS),
        duplicates=key_checks.duplicate_records(idx),
        missing=key_checks.missing_records(idx),
        compared_cells=outcome.compared,
        failed_cells=outcome.failed,
    )


def _checks(cfg: Config, idx: KeyIndex, outcome, violations: list[dict]) -> list[CheckResult]:
    """Checks in the order they appear in the summary sheet."""
    results = [counts.row_count_check(idx), counts.distinct_key_check(idx)]
    results += key_checks.missing_and_extra_checks(idx)
    if cfg.check_duplicates:
        results += key_checks.duplicate_checks(idx)
    results.append(column_checks.whitespace_check(idx, cfg.columns))
    results.append(column_checks.outcome_check(outcome))
    results.append(nulls.check(violations))
    return results


def _report_rows(cfg: Config, idx: KeyIndex, rows_by_key: dict, null_rows: dict) -> list[dict]:
    """Walks every key in order, so each customer's rows appear together."""
    rows: list[dict] = []
    for key in idx.all_keys_sorted:
        if key in rows_by_key:
            rows += rows_by_key[key]
        elif key in idx.missing_keys:
            rows.append(key_checks.missing_row(key))
        else:
            rows.append(key_checks.extra_row(key))
        rows += null_rows.get(key, [])
        if cfg.check_duplicates and key in idx.duplicate_keys:
            rows.append(key_checks.duplicate_row(idx, key, cfg.source_key))
    return rows


def _validate_columns(cfg: Config, source: pd.DataFrame, target: pd.DataFrame) -> None:
    needed_source = [cfg.source_key, *cfg.not_null_source, *(rule.source for rule in cfg.columns)]
    needed_target = [cfg.target_key, *cfg.not_null_target, *(rule.target for rule in cfg.columns)]
    for label, frame, needed in (("source", source, needed_source), ("target", target, needed_target)):
        absent = sorted({column for column in needed if column not in frame.columns})
        if absent:
            raise ConfigError(f"{label} is missing column(s): {', '.join(absent)}")
