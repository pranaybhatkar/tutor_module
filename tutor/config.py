"""Configuration and the tunable decision tables for the syllabus pipeline.

Every magic number the pipeline depends on lives here, so the decision logic in
``analysis.py`` can be read without hunting for literals.

The weightage and time tables were originally derived empirically from a real
30-student batch. They are preserved here exactly as they were, with one
correction -- see ``WEIGHTAGE_BANDS``.
"""

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SPREADSHEET = DATA_DIR / "sample_batch_30.xlsx"
DB_PATH = DATA_DIR / "tutor.db"

SHEET_NAME = "sample_batch_30"
TABLE_NAME = "students"

# --------------------------------------------------------------------------- #
# Column names
# --------------------------------------------------------------------------- #

# The source spreadsheet headers are long and inconsistent. They are mapped to
# these canonical names on import, which also removes the ambiguity in the old
# ``Fields`` list where "Institute/University" appeared twice and the final
# column was mislabelled.
CANONICAL_COLUMNS = {
    "Serial_no": "serial_no",
    "Name": "name",
    "DOB": "dob",
    "Graduation_Stream": "graduation_stream",
    "Institute_University": "institution",
    "Post Graduation_Stream_(NA_if_not_applicable)": "post_graduation_stream",
    "Institute_University_(NA_if_not_applicable)": "post_graduation_institution",
    "Tech_Stack_Certifications": "tech_stack",
}

SENTINEL = "NA"

# --------------------------------------------------------------------------- #
# Stage 1 -- cohort profiling
# --------------------------------------------------------------------------- #

# A graduation stream containing any of these substrings counts as CS/IT.
CS_STREAM_KEYWORDS = ("Computer", "Information Technology")

# --------------------------------------------------------------------------- #
# Stage 2 -- shortlisting
# --------------------------------------------------------------------------- #

# The core heuristic: a topic is worth class time only if a meaningful slice of
# the batch is already shaky on it. Derived from the real distribution -- see
# the README for the reasoning.
SHORTLIST_THRESHOLD = 5

# --------------------------------------------------------------------------- #
# Stage 3 -- weightage
# --------------------------------------------------------------------------- #
# The original table had four holes in it. A topic known by 8, 9, 14, or 24+
# students matched no band at all and was silently dropped from the syllabus.
#
# The bands below are contiguous and exhaustive, so no count can fall between
# them. The five original bands are preserved exactly; each hole is filled by
# the nearest surviving band, which keeps every previously published result
# identical while removing the silent drops.
#
#   before            after
#   5  - 7   5%       5  - 7    5%
#   8  - 9   (hole)   8  - 14  10%
#   10 - 13  10%
#   14       (hole)   15 - 18  30%
#   15 - 18  30%
#   19 - 21  45%      19 - 21  45%
#   22 - 23  50%      22 +     50%
#   24 +     (hole)
WEIGHTAGE_BANDS = (
    (5, 7, "5%"),
    (8, 14, "10%"),
    (15, 18, "30%"),
    (19, 21, "45%"),
    (22, 10**6, "50%"),
)

# --------------------------------------------------------------------------- #
# Stage 4 -- time
# --------------------------------------------------------------------------- #

TIME_BANDS = {
    "5%": "3 Days",
    "10%": "1 Week",
    "30%": "2 Weeks",
    "45%": "3 Weeks",
    "50%": "4 Weeks",
}

# --------------------------------------------------------------------------- #
# Stage 5 -- individual lookup
# --------------------------------------------------------------------------- #

RECORD_FIELDS = (
    ("Serial No", "serial_no"),
    ("Name", "name"),
    ("Date of Birth", "dob"),
    ("Graduation Stream", "graduation_stream"),
    ("Institute / University", "institution"),
    ("Post Graduation Stream", "post_graduation_stream"),
    ("Post Graduation Institute", "post_graduation_institution"),
    ("Tech Stack / Certifications", "tech_stack"),
)