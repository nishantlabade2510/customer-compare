from pathlib import Path

import pandas as pd

from customer_compare.config import ColumnRule, Config, SideConfig
from customer_compare.engine import run_comparison


def make_config(**overrides) -> Config:
    base = dict(
        name="unit",
        source_key="CustomerID",
        target_key="CustomerID",
        source=SideConfig("source", "excel"),
        target=SideConfig("target", "excel"),
        columns=(
            ColumnRule("Name", "Name", transforms=("upper",)),
            ColumnRule("Balance", "Balance", compare="numeric"),
        ),
        not_null_source=(),
        not_null_target=("Name",),
        check_duplicates=True,
        report_passes=True,
        fail_on_mismatch=True,
        output_dir=Path("reports"),
        report_file="unit.xlsx",
        config_path=Path("config/unit.yaml"),
    )
    base.update(overrides)
    return Config(**base)


def failing_pairs(result):
    fails = result.report[result.report["Status"] == "Fail"]
    return set(zip(fails["Customer ID"], fails["Column"]))


def test_identical_datasets_pass():
    data = pd.DataFrame({"CustomerID": [1, 2], "Name": ["Ann", "Bob"], "Balance": ["10.00", "20"]})
    data_target = data.assign(Name=["ANN", "BOB"])
    result = run_comparison(make_config(), data, data_target)
    assert result.passed
    assert result.failed_cells == 0
    assert result.report["Status"].eq("Pass").all()


def test_missing_extra_duplicate_column_and_null_defects_are_reported():
    source = pd.DataFrame(
        {"CustomerID": [1, 2, 3, 4], "Name": ["Ann", "Bob", "Cid", "Dee"], "Balance": ["10.00", "20.00", "30.00", "40"]}
    )
    target = pd.DataFrame(
        {
            "CustomerID": ["1", "2", "2", "4", "5"],
            "Name": ["ANN", "BOB", "BOB", None, "EVE"],
            "Balance": [10, 21, 21, 40, 50],
        }
    )
    result = run_comparison(make_config(), source, target)

    assert not result.passed
    assert failing_pairs(result) == {
        ("2", "Balance"),        # 20.00 vs 21
        ("4", "Name"),           # NULL in target
        ("3", "(record)"),       # missing in target
        ("5", "(record)"),       # extra in target
        ("2", "CustomerID"),     # duplicate in target
    }
    assert len(result.missing) == 2
    assert len(result.duplicates) == 2
    assert result.compared_cells == 6
    assert result.failed_cells == 2
    checks = {c.name: c.passed for c in result.checks}
    assert checks["Row count"] is False           # 4 vs 5
    assert checks["Distinct key count"] is True   # 4 vs 4, hidden by the extra and missing rows
    assert checks["NULL constraints"] is False


def test_null_target_violation_not_repeated_when_column_already_fails():
    source = pd.DataFrame({"CustomerID": [1], "Name": ["Ann"], "Balance": ["10"]})
    target = pd.DataFrame({"CustomerID": [1], "Name": [None], "Balance": ["10"]})
    result = run_comparison(make_config(), source, target)
    name_rows = result.report[(result.report["Column"] == "Name")]
    assert len(name_rows) == 1
    assert name_rows.iloc[0]["Status"] == "Fail"
    assert len(result.null_violations) == 1


def test_failures_only_when_report_passes_disabled():
    source = pd.DataFrame({"CustomerID": [1, 2], "Name": ["Ann", "Bob"], "Balance": ["10", "20"]})
    target = pd.DataFrame({"CustomerID": [1, 2], "Name": ["ANN", "BOB"], "Balance": ["10", "99"]})
    result = run_comparison(make_config(report_passes=False), source, target)
    assert set(result.report["Status"]) == {"Fail"}
    assert len(result.report) == 1
