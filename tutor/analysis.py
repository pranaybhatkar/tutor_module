"""The five-stage syllabus pipeline.

Carried over from ``Priorities.py`` with the stage names intact so the lineage
is obvious:

    Stage 1  Profile    -- who is in the batch, what do they already know
    Stage 2  Shortlist  -- which topics are worth class time
    Stage 3  Weightage  -- how much of the syllabus each topic deserves
    Stage 4  Time       -- how long that weightage takes on a calendar
    Stage 5  Records    -- pull up one student's full profile

What changed, and why
---------------------
* No ``print`` calls. Every stage returns a value; the UI renders it.
* No module-level database work. Call :func:`build_syllabus` with records.
* The weightage gap bug is fixed (see :mod:`tutor.config`).
* Type hints and dataclasses replace loose tuples and parallel lists.
* ``list.count`` inside a loop (quadratic) became a single ``Counter`` pass.

The underlying heuristic is unchanged, so every result published in the README
is still produced by this code.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from . import config

__all__ = [
    "Syllabus",
    "CohortProfile",
    "Topic",
    "split_tech_stack",
    "stage_1_profile",
    "stage_2_shortlist",
    "stage_3_weightage",
    "stage_4_time",
    "stage_5_lookup",
    "build_syllabus",
]


@dataclass(frozen=True)
class CohortProfile:
    """Stage 1 output -- the shape of the batch."""

    total: int
    cs_it: int
    non_cs_it: int

    @property
    def cs_it_ratio(self) -> float:
        return self.cs_it / self.total if self.total else 0.0


@dataclass(frozen=True)
class Topic:
    """A technology and everything the pipeline concluded about it."""

    name: str
    students: int
    weightage: str = ""
    time: str = ""

    @property
    def weightage_value(self) -> int:
        return int(self.weightage.rstrip("%")) if self.weightage else 0


@dataclass
class Syllabus:
    """Everything the UI needs, computed once."""

    profile: CohortProfile
    technology_counts: list[tuple[str, int]]
    shortlist: list[Topic]
    topics: list[Topic] = field(default_factory=list)

    @property
    def total_weightage(self) -> int:
        return sum(topic.weightage_value for topic in self.topics)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def split_tech_stack(value: str) -> list[str]:
    """Turn ``"Python,SQL,Mongodb"`` into ``["Python", "SQL", "Mongodb"]``.

    Surrounding whitespace is stripped and blanks dropped, which the original
    did not do -- harmless for the shipped data, but it is what you hit the
    moment someone types ``"Python, SQL"`` into the spreadsheet.
    """
    if not value or value == config.SENTINEL:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


# --------------------------------------------------------------------------- #
# Stage 1 -- profile the cohort
# --------------------------------------------------------------------------- #


def stage_1_profile(records: list[dict]) -> tuple[CohortProfile, list[tuple[str, int]]]:
    """Answer the two questions a tutor asks before day one.

    1. How diverse is the batch? Count CS/IT against non-CS/IT graduates.
    2. What does the cohort already know? Tally every technology across the
       batch -- the tally for a topic *is* the number of students who know it,
       which is a direct measure of how much teaching it needs.

    Returns the cohort profile and a technology frequency table, both sorted so
    the UI has a stable, meaningful order.
    """
    cs_it = 0
    technologies: Counter[str] = Counter()

    for record in records:
        stream = (record.get("graduation_stream") or "").strip()
        if any(keyword in stream for keyword in config.CS_STREAM_KEYWORDS):
            cs_it += 1

        technologies.update(split_tech_stack(record.get("tech_stack") or ""))

    total = len(records)
    profile = CohortProfile(
        total=total,
        cs_it=cs_it,
        non_cs_it=total - cs_it,
    )

    # Most-known first; alphabetical within a tie so the order never wobbles.
    counts = sorted(technologies.items(), key=lambda item: (-item[1], item[0]))

    return profile, counts


# --------------------------------------------------------------------------- #
# Stage 2 -- shortlist the topics
# --------------------------------------------------------------------------- #


def stage_2_shortlist(technology_counts: list[tuple[str, int]]) -> list[Topic]:
    """Keep only topics a meaningful slice of the batch is already shaky on.

    Counter-intuitive but deliberate: a topic is worth class time only if many
    students already know it. If nobody knows it, it does not belong to this
    course. If nearly everyone knows it, it does not need a classroom.
    """
    return [
        Topic(name=name, students=students)
        for name, students in technology_counts
        if students >= config.SHORTLIST_THRESHOLD
    ]


# --------------------------------------------------------------------------- #
# Stage 3 -- weightage
# --------------------------------------------------------------------------- #


def stage_3_weightage(shortlist: list[Topic]) -> list[Topic]:
    """Map student count to a percentage of the syllabus.

    The heavier the existing knowledge, the more class time the topic needs to
    bring the whole batch to the same level.
    """
    weighted: list[Topic] = []

    for topic in shortlist:
        for low, high, weightage in config.WEIGHTAGE_BANDS:
            if low <= topic.students <= high:
                weighted.append(
                    Topic(name=topic.name, students=topic.students, weightage=weightage)
                )
                break
        else:  # pragma: no cover -- unreachable while the bands are contiguous
            raise ValueError(
                f"No weightage band covers {topic.students} students "
                f"for {topic.name!r}; check tutor.config.WEIGHTAGE_BANDS"
            )

    return weighted


# --------------------------------------------------------------------------- #
# Stage 4 -- time
# --------------------------------------------------------------------------- #


def stage_4_time(weighted: list[Topic]) -> list[Topic]:
    """Convert weightage into something a tutor can put on a calendar."""
    return [
        Topic(
            name=topic.name,
            students=topic.students,
            weightage=topic.weightage,
            time=config.TIME_BANDS[topic.weightage],
        )
        for topic in weighted
    ]


# --------------------------------------------------------------------------- #
# Stage 5 -- individual lookup
# --------------------------------------------------------------------------- #


def stage_5_lookup(records: list[dict], name: str, dob: str) -> dict | None:
    """Find one student by name and date of birth.

    Replaces the original lookup, which used a ``for``/``else`` whose ``else``
    belonged to the inner loop -- so it raised an exception the first time any
    record failed to match, making lookup work only if the student happened to
    be in the very first record examined.

    Matching is case-insensitive and whitespace-tolerant, since both fields are
    typed by hand.
    """
    if not name or not dob:
        return None

    wanted_name = name.strip().casefold()
    wanted_dob = dob.strip().casefold()

    for record in records:
        if (record.get("name") or "").strip().casefold() == wanted_name and (
            record.get("dob") or ""
        ).strip().casefold() == wanted_dob:
            return record

    return None


def format_record(record: dict) -> list[tuple[str, str]]:
    """Flatten a record into labelled ``(field, value)`` pairs for display."""
    return [(label, str(record.get(key, ""))) for label, key in config.RECORD_FIELDS]


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


def build_syllabus(records: list[dict]) -> Syllabus:
    """Run Stages 1-4 over a set of records.

    Stage 5 is a lookup, not part of the pipeline, so it stays separate.
    """
    profile, technology_counts = stage_1_profile(records)
    shortlist = stage_2_shortlist(technology_counts)
    weighted = stage_3_weightage(shortlist)
    topics = stage_4_time(weighted)

    return Syllabus(
        profile=profile,
        technology_counts=technology_counts,
        shortlist=shortlist,
        topics=topics,
    )