"""Load one side of the comparison from SQLite, any SQLAlchemy database, Excel or CSV.

Database queries live in SQL files (see sql/), so the extract logic is versioned
and reviewed separately from the Python code.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing

import pandas as pd

from .config import ConfigError, SideConfig


def load_side(side: SideConfig) -> pd.DataFrame:
    if side.type == "sqlite":
        return _query_sqlite(side)
    if side.type == "database":
        return _query_sqlalchemy(side)
    if side.type == "excel":
        _require_file(side)
        return pd.read_excel(side.path, sheet_name=side.sheet, dtype=object)
    if side.type == "csv":
        _require_file(side)
        return pd.read_csv(side.path, dtype=object)
    raise ConfigError(f"Unsupported type for {side.name}: {side.type}")


def _require_file(side: SideConfig) -> None:
    if side.path is None or not side.path.is_file():
        raise ConfigError(f"{side.name} file not found: {side.path}")


def _read_sql(side: SideConfig) -> str:
    assert side.query_file is not None
    return side.query_file.read_text(encoding="utf-8")


def _query_sqlite(side: SideConfig) -> pd.DataFrame:
    _require_file(side)
    with closing(sqlite3.connect(side.path)) as conn:
        return pd.read_sql_query(_read_sql(side), conn, params=side.params or None)


def _query_sqlalchemy(side: SideConfig) -> pd.DataFrame:
    # Imported lazily so SQLite, Excel and CSV runs do not need SQLAlchemy installed.
    from sqlalchemy import create_engine, text

    engine = create_engine(side.url)
    try:
        with engine.connect() as conn:
            return pd.read_sql_query(text(_read_sql(side)), conn, params=side.params or None)
    finally:
        engine.dispose()
