"""Writes the mismatch report (Excel and CSV) and a JSON run summary."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .config import Config
from .results import RunResult

FAIL_FILL = PatternFill("solid", fgColor="F8D7DA")
PASS_FILL = PatternFill("solid", fgColor="D4EDDA")
WARN_FILL = PatternFill("solid", fgColor="FFF3CD")
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(bold=True, color="FFFFFF")


def write_reports(result: RunResult, cfg: Config) -> dict[str, Path]:
    out_dir = cfg.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    xlsx_path = out_dir / cfg.report_file
    csv_path = xlsx_path.with_suffix(".csv")
    json_path = out_dir / f"{xlsx_path.stem}_summary.json"

    report = result.report
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        _summary_frame(result).to_excel(writer, sheet_name="Summary", index=False)
        report.to_excel(writer, sheet_name="Mismatch Report", index=False)
        report[report["Status"] == "Fail"].to_excel(writer, sheet_name="Failures Only", index=False)
        result.missing.to_excel(writer, sheet_name="Missing Records", index=False)
        result.duplicates.to_excel(writer, sheet_name="Duplicates", index=False)
        result.null_violations.to_excel(writer, sheet_name="NULL Violations", index=False)
    _style_workbook(xlsx_path)

    report.to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(_json_summary(result), indent=2), encoding="utf-8")
    return {"excel": xlsx_path, "csv": csv_path, "json": json_path}


def _summary_frame(result: RunResult) -> pd.DataFrame:
    failed_checks = sum(not check.passed for check in result.checks)
    rows = [
        {"Check": "Run", "Result": "", "Detail": f"{result.config_name} at {result.run_at}"},
        {
            "Check": "Overall",
            "Result": "Pass" if result.passed else "Fail",
            "Detail": f"{failed_checks} of {len(result.checks)} checks failed",
        },
    ]
    rows += [
        {"Check": check.name, "Result": _result_label(check), "Detail": check.detail}
        for check in result.checks
    ]
    return pd.DataFrame(rows, columns=["Check", "Result", "Detail"])


def _result_label(check) -> str:
    if check.warning:
        return "Warn"
    return "Pass" if check.passed else "Fail"


def _json_summary(result: RunResult) -> dict:
    return {
        "run": result.config_name,
        "run_at": result.run_at,
        "passed": result.passed,
        "source_rows": result.source_rows,
        "target_rows": result.target_rows,
        "source_distinct_keys": result.source_keys,
        "target_distinct_keys": result.target_keys,
        "compared_cells": result.compared_cells,
        "failed_cells": result.failed_cells,
        "checks": [
            {"name": c.name, "passed": c.passed, "warning": c.warning, "detail": c.detail}
            for c in result.checks
        ],
    }


def _style_workbook(path: Path) -> None:
    workbook = load_workbook(path)
    for sheet in workbook.worksheets:
        for cell in sheet[1]:
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = Alignment(vertical="center")
        sheet.freeze_panes = "A2"
        if sheet.max_row > 1:
            sheet.auto_filter.ref = sheet.dimensions
        for index, column in enumerate(sheet.iter_cols(min_row=1, max_row=sheet.max_row), start=1):
            width = max((len(str(c.value)) for c in column if c.value is not None), default=8)
            sheet.column_dimensions[get_column_letter(index)].width = min(max(width + 2, 10), 60)

        status_index = _header_index(sheet, "Status") or _header_index(sheet, "Result")
        if status_index:
            for row in sheet.iter_rows(min_row=2):
                value = str(row[status_index - 1].value)
                fill = (
                    FAIL_FILL if value == "Fail"
                    else WARN_FILL if value == "Warn"
                    else PASS_FILL if value == "Pass"
                    else None
                )
                if fill is not None:
                    for cell in row:
                        cell.fill = fill
    workbook.save(path)


def _header_index(sheet, name: str) -> int | None:
    for index, cell in enumerate(sheet[1], start=1):
        if cell.value == name:
            return index
    return None
