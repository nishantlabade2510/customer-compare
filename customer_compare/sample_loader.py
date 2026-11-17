"""Loads an Excel workbook into a SQLite table.

Used to stand up the database side of the comparison locally and in CI, so the
DB path can be exercised without a database server.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd


def load_workbook_to_sqlite(xlsx_path: str | Path, db_path: str | Path, table: str) -> int:
    """Replace `table` in the SQLite file with the first sheet of the workbook. Returns row count."""
    frame = pd.read_excel(xlsx_path, dtype=object)
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as conn:
        frame.to_sql(table, conn, if_exists="replace", index=False)
    return len(frame)
