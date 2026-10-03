"""Test suite for the Tutor Module pipeline.

The original project shipped with no tests -- verification was a pile of
``print`` statements. These tests lock in the numbers published in the README,
which matters because the anonymisation of the source spreadsheet had to leave
every algorithmic result untouched.

Run with::

    python -m pytest -v
"""

from __future__ import annotations

import datetime as dt
import re

import pytest

from tutor import config
from tutor.analysis import (
    Topic,
    build_syllabus,
    split_tech_stack,
    stage_2_shortlist,
    stage_3_weightage,
    stage_5_lookup,
    stage_1_profile,
)
from tutor.data import fetch_records

DATE_PATTERN = re.compile(r"^\d{2}/\d{2}/\d{4}$")


@pytest.fixture(scope="module")
def records() -> list[dict]:
    return fetch_records()


@pytest.fixture(scope="module")
def syllabus(records: list[dict]):
    return build_syllabus(records)


# --------------------------------------------------------------------------- #
# Stage 1 -- cohort profile
# --------------------------------------------------------------------------- #


def test_cohort_split(syllabus) -> None:
    """The README publishes a 14 / 16 split across 30 students."""
    profile = syllabus.profile
    assert profile.total == 30
    assert profile.cs_it == 14
    assert profile.non_cs_it == 16
    assert profile.cs_it + profile.non_cs_it == profile.total


def test_unique_technology_count(syllabus) -> None:
    assert len(syllabus.technology_counts) == 26


@pytest.mark.parametrize(
    ("technology", "expected"),
    [
        ("Python", 19),
        ("SQL", 18),
        ("Mongodb", 11),
        ("Linux", 5),
        ("PLSQL", 5),
        ("Flask", 5),
        ("PowerBi", 1),
        ("C", 1),
    ],
)
def test_technology_frequency(syllabus, technology: str, expected: int) -> None:
    counts = dict(syllabus.technology_counts)
    assert counts.get(technology) == expected


def test_counts_are_sorted_descending(syllabus) -> None:
    counts = [count for _, count in syllabus.technology_counts]
    assert counts == sorted(counts, reverse=True)


# --------------------------------------------------------------------------- #
# Stage 2 -- shortlist
# --------------------------------------------------------------------------- #


def test_shortlist_size(syllabus) -> None:
    assert len(syllabus.shortlist) == 6


def test_shortlist_honours_threshold(records: list[dict]) -> None:
    _, counts = stage_1_profile(records)
    shortlist = stage_2_shortlist(counts)
    assert all(topic.students >= config.SHORTLIST_THRESHOLD for topic in shortlist)


# --------------------------------------------------------------------------- #
# Stage 3 -- weightage
# --------------------------------------------------------------------------- #


def test_weightage_mapping(syllabus) -> None:
    expected = {
        "Python": "45%",
        "SQL": "30%",
        "Mongodb": "10%",
        "Linux": "5%",
        "PLSQL": "5%",
        "Flask": "5%",
    }
    actual = {topic.name: topic.weightage for topic in syllabus.topics}
    assert actual == expected


def test_weightage_totals_one_hundred_percent(syllabus) -> None:
    assert syllabus.total_weightage == 100


def test_weightage_bands_are_contiguous() -> None:
    """Regression test for the silent-drop bug.

    The original band table skipped 8-9, 14, and 24+. A topic known by one of
    those counts matched nothing and vanished from the syllabus with no error.
    """
    bands = sorted(config.WEIGHTAGE_BANDS)

    assert bands[0][0] <= config.SHORTLIST_THRESHOLD, (
        "the lowest band must start at or below the shortlist threshold, "
        "otherwise shortlisted topics fall through the first gap"
    )

    for (_, previous_high, _), (next_low, _, _) in zip(bands, bands[1:]):
        assert next_low == previous_high + 1, (
            f"gap between bands: {previous_high} -> {next_low}"
        )


@pytest.mark.parametrize("students", [5, 6, 7, 8, 9, 10, 13, 14, 15, 18, 19, 21, 22, 23, 24, 30, 100])
def test_every_shortlisted_count_receives_a_weightage(students: int) -> None:
    """No count between the threshold and the top of the scale may be dropped."""
    weighted = stage_3_weightage([Topic(name="Probe", students=students)])
    assert len(weighted) == 1
    assert weighted[0].weightage in config.TIME_BANDS


# --------------------------------------------------------------------------- #
# Stage 4 -- time
# --------------------------------------------------------------------------- #


def test_time_mapping(syllabus) -> None:
    expected = {
        "Python": "3 Weeks",
        "SQL": "2 Weeks",
        "Mongodb": "1 Week",
        "Linux": "3 Days",
        "PLSQL": "3 Days",
        "Flask": "3 Days",
    }
    actual = {topic.name: topic.time for topic in syllabus.topics}
    assert actual == expected


def test_every_weightage_has_a_time_band() -> None:
    for _, _, weightage in config.WEIGHTAGE_BANDS:
        assert weightage in config.TIME_BANDS


# --------------------------------------------------------------------------- #
# Stage 5 -- individual lookup
# --------------------------------------------------------------------------- #


def test_lookup_finds_a_student_beyond_the_first_record(records: list[dict]) -> None:
    """Regression test for the ``for``/``else`` bug.

    The original implementation raised on the first non-matching record, so
    lookup only ever worked if the student was in record one. Take the very
    last student, which the original could never have reached.
    """
    target = records[-1]
    found = stage_5_lookup(records, target["name"], target["dob"])
    assert found is not None
    assert found["serial_no"] == target["serial_no"]


def test_lookup_is_case_and_whitespace_insensitive(records: list[dict]) -> None:
    target = records[3]
    scrambled = f"  {target['name'].swapcase()} "
    assert stage_5_lookup(records, scrambled, target["dob"]) is not None


def test_lookup_rejects_wrong_dob(records: list[dict]) -> None:
    target = records[5]
    assert stage_5_lookup(records, target["name"], "01/01/1900") is None


def test_lookup_returns_none_for_empty_input(records: list[dict]) -> None:
    assert stage_5_lookup(records, "", "") is None
    assert stage_5_lookup(records, "Nobody", "") is None


# --------------------------------------------------------------------------- #
# Data hygiene
# --------------------------------------------------------------------------- #


def test_tech_stack_splitting() -> None:
    assert split_tech_stack("Python,SQL,Mongodb") == ["Python", "SQL", "Mongodb"]
    assert split_tech_stack("Python, SQL ,Mongodb") == ["Python", "SQL", "Mongodb"]
    assert split_tech_stack("NA") == []
    assert split_tech_stack("") == []


def test_all_dates_of_birth_are_normalised(records: list[dict]) -> None:
    """The source file mixed date strings with a raw Excel serial (35489)."""
    for record in records:
        assert DATE_PATTERN.match(record["dob"]), (
            f"serial {record['serial_no']} has a non-normalised DOB: {record['dob']!r}"
        )
        parsed = dt.datetime.strptime(record["dob"], "%d/%m/%Y")
        assert 1990 <= parsed.year <= 2005


def test_anonymisation_removed_personal_names(records: list[dict]) -> None:
    """Option A: only serial 1 keeps a real name; the other 29 are synthetic."""
    for record in records:
        serial = int(record["serial_no"])
        if serial == 1:
            continue
        assert record["name"] == f"Student {serial:03d}", (
            f"serial {serial} still carries a real name: {record['name']!r}"
        )


def test_anonymisation_left_algorithm_inputs_untouched(syllabus) -> None:
    """The guarantee that made anonymisation safe."""
    assert syllabus.profile.cs_it == 14
    assert dict(syllabus.technology_counts)["Python"] == 19
    assert dict(syllabus.technology_counts)["SQL"] == 18


def test_record_count_matches_the_spreadsheet(records: list[dict]) -> None:
    assert len(records) == 30
    assert [int(record["serial_no"]) for record in records] == list(range(1, 31))