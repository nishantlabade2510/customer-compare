"""End-to-end checks on the supplied sample workbooks.

The sample data has known defects (see README). These tests pin them down, so a
change to the rules that silently hides one of them fails the build.
"""

from pandas.testing import assert_frame_equal

from customer_compare.config import load_config
from customer_compare.engine import run_comparison
from customer_compare.sample_loader import load_workbook_to_sqlite
from tests.conftest import ROOT, SAMPLE_SOURCE, SAMPLE_TARGET


def test_excel_run_finds_every_seeded_defect():
    result = run_comparison(load_config(ROOT / "config/config.excel.yaml"))

    assert not result.passed
    assert result.source_rows == 30 and result.target_rows == 30
    assert result.source_keys == 30 and result.target_keys == 29

    checks = {c.name: c.passed for c in result.checks}
    assert checks["Row count"] is True             # equal counts hide the defects below
    assert checks["Distinct key count"] is False
    assert checks["Missing records"] is False
    assert checks["Extra records"] is True
    assert checks["Duplicate keys (target)"] is False
    assert checks["Duplicate keys (source)"] is True

    fails = result.report[result.report["Status"] == "Fail"]
    pairs = set(zip(fails["Customer ID"], fails["Column"]))
    assert pairs == {
        ("1002", "Balance"),       # 637.53 vs 687.53
        ("1007", "City"),          # toronto vs MONTREAL
        ("1009", "Balance"),       # 1600.24 vs NULL
        ("1012", "CustomerName"),  # Asha Kumar vs Asha Rao
        ("1015", "Email"),         # amit.khan@ vs Amit.Rao@
        ("1016", "Balance"),       # 2562.95 vs 2442.45
        ("1018", "DOB"),           # 2004-06-25 vs 1990-01-01
        ("1023", "Balance"),       # 3525.66 vs 3525.76
        ("1024", "Country"),       # canada vs NULL
        ("1005", "CustomerID"),    # duplicate row in target
        ("1030", "(record)"),      # missing in target
    }
    assert len(result.report) == 29 * 10 + 2   # 29 keys on both sides x 10 columns, plus missing and duplicate rows
    assert result.failed_cells == 9
    assert set(result.null_violations["Customer ID"]) == {"1009", "1024"}


def test_sqlite_path_produces_the_same_report_as_excel(tmp_path, monkeypatch):
    source_db, target_db = tmp_path / "source.db", tmp_path / "target.db"
    load_workbook_to_sqlite(SAMPLE_SOURCE, source_db, "customer_source")
    load_workbook_to_sqlite(SAMPLE_TARGET, target_db, "customer_target")
    monkeypatch.setenv("SOURCE_SQLITE_PATH", str(source_db))
    monkeypatch.setenv("TARGET_SQLITE_PATH", str(target_db))

    db_result = run_comparison(load_config(ROOT / "config/config.yaml"))
    excel_result = run_comparison(load_config(ROOT / "config/config.excel.yaml"))

    assert_frame_equal(db_result.report, excel_result.report)
    assert db_result.failed_cells == excel_result.failed_cells
