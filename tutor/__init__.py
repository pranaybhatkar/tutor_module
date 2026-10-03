"""Tutor Module -- a student-centric tutoring platform that designs a syllabus
from the batch's own profile data.

Modules
-------
config     Tunable decision tables (weightage bands, thresholds, paths)
data       SQLite loading and spreadsheet ingestion
analysis   The five-stage syllabus pipeline
"""

from .analysis import Syllabus, build_syllabus, stage_5_lookup
from .data import ensure_database, fetch_records

__all__ = [
    "Syllabus",
    "build_syllabus",
    "ensure_database",
    "fetch_records",
    "stage_5_lookup",
]

__version__ = "2.0.0"