"""Result types and report-row helpers shared by the checks, the engine and the report writer."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

REPORT_COLUMNS = ["Customer ID", "Column", "Source", "Target", "Status", "Check"]
RECORD_COLUMN = "(record)"  # used when a whole record is missing or extra


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    warning: bool = False  # reported for information only; never fails the run


@dataclass
class RunResult:
    config_name: str
    run_at: str
    source_rows: int
    target_rows: int
    source_keys: int
    target_keys: int
    checks: list[CheckResult]
    report: pd.DataFrame            # mismatch report, columns = REPORT_COLUMNS
    null_violations: pd.DataFrame
    duplicates: pd.DataFrame
    missing: pd.DataFrame           # missing in target and extra in target
    compared_cells: int
    failed_cells: int

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


def status_for(ok: bool) -> str:
    return "Pass" if ok else "Fail"


def report_row(key: str, column: str, source: str, target: str, status: str, check: str) -> dict:
    return {
        "Customer ID": key,
        "Column": column,
        "Source": source,
        "Target": target,
        "Status": status,
        "Check": check,
    }
