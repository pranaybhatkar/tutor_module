"""End-to-end tests that drive the real Streamlit app.

The original project had no UI tests at all. These run the actual ``app.py``
headlessly through Streamlit's ``AppTest`` harness, which executes the script and
lets us assert on what a user would see -- so a broken chart or an unhandled
exception fails here rather than in front of a viewer.

A note on form interaction: values typed into widgets inside ``st.form`` are
discarded when the script re-runs. They only reach the script on submit. So the
inputs must be set, the button clicked, and ``run()`` called exactly once --
interleaving ``.run()`` between the ``set_value`` calls silently discards them.

Run with::

    python -m pytest tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

# AppTest resolves relative paths against the *calling* file, so anchor to the
# repository root explicitly.
APP_PATH = Path(__file__).resolve().parent.parent / "app.py"

VALID_NAME = "Pranay Avinash Bhatkar"
VALID_DOB = "21/02/1997"


def _load(mode: str | None = None) -> AppTest:
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    if mode is not None:
        app = app.radio[0].set_value(mode).run()
    return app


def _search(app: AppTest, name: str, dob: str) -> AppTest:
    """Fill the lookup form and submit it in a single interaction batch."""
    app.text_input[0].set_value(name)
    app.text_input[1].set_value(dob)
    app.button[0].click()
    return app.run()


@pytest.fixture(scope="module")
def app() -> AppTest:
    return _load()


# --------------------------------------------------------------------------- #
# Batch analysis view
# --------------------------------------------------------------------------- #


def test_app_runs_without_exceptions(app: AppTest) -> None:
    assert not app.exception, [str(e.value) for e in app.exception]


def test_title_renders(app: AppTest) -> None:
    assert any("Tutor Module" in title.value for title in app.title)


def test_navigation_offers_both_views(app: AppTest) -> None:
    options = [option for radio in app.radio for option in radio.options]
    assert "Batch analysis" in options
    assert "Student lookup" in options


def test_cohort_metrics_match_the_dataset(app: AppTest) -> None:
    """Metrics render as strings, which is how Streamlit surfaces them."""
    values = {metric.label: metric.value for metric in app.metric}
    assert values["Total students"] == "30"
    assert values["CS/IT background"] == "14"
    assert values["Non-CS/IT background"] == "16"


def test_total_weightage_is_one_hundred(app: AppTest) -> None:
    values = {metric.label: metric.value for metric in app.metric}
    assert values["Total syllabus weightage"] == "100%"


def test_three_charts_render(app: AppTest) -> None:
    # cohort donut, frequency bars, shortlist doughnut
    assert len(app.get("plotly_chart")) == 3


def test_syllabus_table_lists_six_subjects(app: AppTest) -> None:
    frame = next(
        element.value
        for element in app.dataframe
        if "Subject" in list(element.value.columns)
    )
    assert len(frame) == 6
    assert set(frame["Subject"]) == {"Python", "SQL", "Mongodb", "Linux", "PLSQL", "Flask"}
    assert frame["Weightage"].sum() == 100


def test_about_expander_is_present(app: AppTest) -> None:
    assert any("How this works" in element.label for element in app.expander)


def test_no_deprecation_warnings_in_app_code(app: AppTest) -> None:
    """Guard against re-introducing removed Streamlit APIs."""
    source = APP_PATH.read_text(encoding="utf-8")
    assert "use_container_width" not in source
    assert "st.cache(" not in source


# --------------------------------------------------------------------------- #
# Student lookup view
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def lookup_app() -> AppTest:
    return _load("Student lookup")


def test_lookup_view_loads(lookup_app: AppTest) -> None:
    assert not lookup_app.exception, [str(e.value) for e in lookup_app.exception]
    assert [element.label for element in lookup_app.text_input] == [
        "Full name",
        "Date of birth",
    ]
    assert any(button.label == "Search" for button in lookup_app.button)


def test_valid_lookup_succeeds(lookup_app: AppTest) -> None:
    result = _search(lookup_app, VALID_NAME, VALID_DOB)
    assert not result.exception, [str(e.value) for e in result.exception]
    assert any("Record found" in message.value for message in result.success)
    assert result.dataframe, "a matched record should render a detail table"


def test_matched_record_shows_the_field_table(lookup_app: AppTest) -> None:
    result = _search(lookup_app, VALID_NAME, VALID_DOB)
    columns = [list(element.value.columns) for element in result.dataframe]
    assert ["Field", "Value"] in columns


def test_wrong_date_of_birth_is_rejected(lookup_app: AppTest) -> None:
    result = _search(lookup_app, VALID_NAME, "01/01/1900")
    assert any("No student matches" in message.value for message in result.error)


def test_unknown_student_is_rejected(lookup_app: AppTest) -> None:
    result = _search(lookup_app, "Nobody At All", VALID_DOB)
    assert any("No student matches" in message.value for message in result.error)


def test_empty_submission_is_rejected(lookup_app: AppTest) -> None:
    result = _search(lookup_app, "", "")
    assert any("No student matches" in message.value for message in result.error)


def test_anonymised_record_is_searchable(lookup_app: AppTest) -> None:
    """A synthetic record must resolve, proving the anonymised data still works.

    Student 015's date of birth is read from the app's own hint data so the
    test does not hardcode a value that sanitisation may change.
    """
    import pandas as pd

    from tutor.data import fetch_records

    target = next(record for record in fetch_records() if record["name"] == "Student 015")

    result = _search(lookup_app, target["name"], target["dob"])
    assert not result.exception, [str(e.value) for e in result.exception]
    assert any("Record found" in message.value for message in result.success)

    # And the technology count metric should be populated.
    labels = {metric.label for metric in result.metric}
    assert "Technologies listed" in labels