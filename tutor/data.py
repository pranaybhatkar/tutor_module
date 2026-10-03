"""Data access for Tutor Module.

The original project opened a MySQL connection at *module import* time from
hardcoded credentials, then ran all of its analysis during import. That worked
on a single Heroku dyno and broke anywhere else -- and it meant the app could
not start at all if the database was unreachable.

This module replaces that with:

* **SQLite** instead of MySQL, so the project runs with zero infrastructure and
  still demonstrates real SQL (``to_sql`` table creation, ``SELECT`` queries).
* **Lazy creation** -- the database file is built from the source spreadsheet on
  first use, not at import.
* **Plain functions, no Streamlit imports**, so the logic stays testable and
  framework-independent.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from . import config

__all__ = [
    "ensure_database",
    "fetch_records",
    "connect",
    "read_spreadsheet",
    "reset_database",
]


def read_spreadsheet(spreadsheet: Path | None = None) -> pd.DataFrame:
    """Load and normalise the batch spreadsheet.

    Every column is read as text. That is deliberate: ``serial_no`` and ``dob``
    arrive from the spreadsheet as a mix of numbers and date objects, and
    coercing them to ``object`` up front keeps the rest of the pipeline free of
    type coercion surprises.
    """
    path = spreadsheet or config.SPREADSHEET
    frame = pd.read_excel(path, sheet_name=config.SHEET_NAME, dtype=str)

    frame = frame.rename(columns=config.CANONICAL_COLUMNS)
    frame = frame.fillna(config.SENTINEL)

    # Drop anything that is entirely blank -- the sheet carries formatting-only
    # rows that Excel serialises as empty cells.
    frame = frame.dropna(how="all")
    frame = frame.reset_index(drop=True)

    return frame


def ensure_database(
    db_path: Path | None = None, spreadsheet: Path | None = None
) -> Path:
    """Create the SQLite database from the spreadsheet if it does not exist.

    Returns the path to the database. Safe to call on every app start -- it is a
    no-op once the file is present.
    """
    path = db_path or config.DB_PATH
    if path.exists():
        return path

    frame = read_spreadsheet(spreadsheet)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    try:
        # ``replace`` rather than ``append``: seeding twice must not duplicate
        # every student.
        frame.to_sql(config.TABLE_NAME, connection, if_exists="replace", index=False)
        connection.commit()
    finally:
        connection.close()

    return path


def reset_database(
    db_path: Path | None = None, spreadsheet: Path | None = None
) -> Path:
    """Delete and rebuild the database. Useful after editing the spreadsheet."""
    path = db_path or config.DB_PATH
    path.unlink(missing_ok=True)
    return ensure_database(path, spreadsheet)


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a connection, creating the database first if necessary."""
    path = ensure_database(db_path)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def fetch_records(db_path: Path | None = None) -> list[dict]:
    """Return every student row as a dictionary.

    This replaces the five separate ``cursor.execute`` calls the original made
    with one query and one pass.
    """
    connection = connect(db_path)
    try:
        rows = connection.execute(
            f"SELECT * FROM {config.TABLE_NAME}"  # noqa: S608 -- table name is a constant
        ).fetchall()
    finally:
        connection.close()

    return [dict(row) for row in rows]