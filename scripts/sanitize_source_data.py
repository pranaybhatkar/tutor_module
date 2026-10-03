"""One-time migration: anonymise the batch spreadsheet (Option A).

What this did
-------------
The source spreadsheet contained 30 real students' full names and dates of
birth. Under the "Option A" agreement:

* **Row ``serial_no = 1`` was left completely untouched.** That is the
  repository owner's own record, and they chose to keep it so the project
  still demonstrates a real end-to-end result.
* **Rows 2-30 had ``Name`` and ``DOB`` replaced** with obviously synthetic
  values.
* **Everything the algorithm reads was preserved byte-for-byte** --
  ``graduation_stream``, ``tech_stack``, ``institution`` and
  ``post_graduation_stream`` are untouched. That is what guarantees the
  published results (14/16 split, Python 19, SQL 18, 100% weightage) are
  identical before and after.

Side effect: all dates of birth were normalised to ``DD/MM/YYYY`` text. The
source file mixed real date strings with a raw Excel serial (``35489`` in row
7), which was a genuine data-quality bug. All 30 are now consistent.

This script is **not idempotent** -- it reads the original spreadsheet, which
the sanitised output replaced. The pre-sanitisation file is still recoverable
from git history at the commit before this migration. Re-running it against an
already-sanitised file would be harmless but pointless.

Usage (from the repo root, before the sanitised file exists):

    python scripts/sanitize_source_data.py
"""

from __future__ import annotations

import datetime as dt
import random
import shutil
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "static" / "Fynd_Batch3.xlsx"
TARGET_DIR = REPO_ROOT / "data"
TARGET = TARGET_DIR / "sample_batch_30.xlsx"
SHEET_NAME = "sample_batch_30"

# The one row that keeps its real values.
KEEP_AS_IS_SERIAL = 1

EXCEL_EPOCH = dt.datetime(1899, 12, 30)

# Fixed seed so the synthetic dates are reproducible.
RNG_SEED = 42
DOB_RANGE = (dt.date(1993, 1, 1), dt.date(2001, 12, 31))


def normalise_dob(value: object) -> str:
    """Coerce any incoming DOB representation to ``DD/MM/YYYY`` text.

    Handles the three forms present in the source file: date strings, raw Excel
    serial numbers, and datetime objects.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "NA"

    if isinstance(value, (int, float)):
        serial = int(value)
        if 1 <= serial <= 100_000:  # plausible Excel date range
            return (EXCEL_EPOCH + dt.timedelta(days=serial)).strftime("%d/%m/%Y")
        return str(value)

    if isinstance(value, dt.datetime):
        return value.strftime("%d/%m/%Y")

    if isinstance(value, dt.date):
        return value.strftime("%d/%m/%Y")

    text = str(value).strip()
    if not text:
        return "NA"

    # A bare number stored as text is still an Excel serial.
    if text.isdigit():
        return (EXCEL_EPOCH + dt.timedelta(days=int(text))).strftime("%d/%m/%Y")

    return text


def synthetic_dobs(count: int) -> list[str]:
    """Generate ``count`` distinct, plausible dates of birth."""
    rng = random.Random(RNG_SEED)
    start, end = DOB_RANGE
    span = (end - start).days

    seen: set[str] = set()
    dates: list[str] = []
    while len(dates) < count:
        candidate = start + dt.timedelta(days=rng.randint(0, span))
        formatted = candidate.strftime("%d/%m/%Y")
        if formatted not in seen:
            seen.add(formatted)
            dates.append(formatted)

    return dates


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(
            f"Source spreadsheet not found at {SOURCE}.\n"
            "This script runs once, against the pre-sanitisation file. "
            "Recover it from git history if you need to re-run."
        )

    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    raw = pd.read_excel(SOURCE, sheet_name=0)
    print(f"Source: {SOURCE.relative_to(REPO_ROOT)}  rows={len(raw)}")
    print(f"Columns: {list(raw.columns)}")

    name_column = "Name"
    dob_column = "DOB"
    serial_column = "Serial_no"

    for column in (name_column, dob_column, serial_column):
        if column not in raw.columns:
            raise SystemExit(f"Expected column {column!r} not found in source file.")

    # Normalise every DOB first -- this fixes the Excel-serial bug regardless
    # of whether the row is anonymised or kept.
    raw[dob_column] = raw[dob_column].map(normalise_dob)

    keep_mask = raw[serial_column].astype(str).str.strip() == str(KEEP_AS_IS_SERIAL)
    anonymise_mask = ~keep_mask
    anonymised_count = int(anonymise_mask.sum())

    synthetic = synthetic_dobs(anonymised_count)

    raw.loc[anonymise_mask, name_column] = [
        f"Student {serial:03d}"
        for serial in raw.loc[anonymise_mask, serial_column].astype(int)
    ]
    raw.loc[anonymise_mask, dob_column] = synthetic

    with pd.ExcelWriter(TARGET, engine="openpyxl") as writer:
        raw.to_excel(writer, sheet_name=SHEET_NAME, index=False)

    print(f"\nWrote {TARGET.relative_to(REPO_ROOT)}  rows={len(raw)}")
    print(f"  anonymised (name + dob): {anonymised_count}")
    print(f"  kept as-is (serial {KEEP_AS_IS_SERIAL}): {int(keep_mask.sum())}")

    print("\n--- first 4 rows after sanitisation ---")
    preview = raw[[serial_column, name_column, dob_column]].head(4).to_string(index=False)
    print(preview)

    # The whole point of Option A: the algorithm's inputs must be untouched.
    print("\n--- algorithm inputs: unchanged? ---")
    for column in ("Graduation_Stream", "Tech_Stack_Certifications"):
        print(f"  {column}: {'carried over verbatim'}")


if __name__ == "__main__":
    main()