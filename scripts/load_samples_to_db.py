"""Create data/source.db and data/target.db from the sample workbooks.

Used for local runs and in CI. In a real pipeline the databases already exist and
this script is not needed.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from customer_compare.sample_loader import load_workbook_to_sqlite  # noqa: E402


def main() -> int:
    samples = ROOT / "data" / "samples"
    source_rows = load_workbook_to_sqlite(
        samples / "customer_SOURCE_DATA.xlsx", ROOT / "data" / "source.db", "customer_source"
    )
    target_rows = load_workbook_to_sqlite(
        samples / "customer_TARGET_DATA.xlsx", ROOT / "data" / "target.db", "customer_target"
    )
    print(f"Loaded customer_source ({source_rows} rows) and customer_target ({target_rows} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
