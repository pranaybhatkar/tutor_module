"""Tutor Module -- Streamlit application.

Replaces the original FastAPI + Jinja2 + CanvasJS stack. Every server-rendered
template and the hand-rolled fetch() JavaScript collapse into native Streamlit
widgets, which removes the CORS configuration, the canvas charting, and the
multi-page form navigation entirely.

Run locally::

    streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tutor import config
from tutor.analysis import (
    Syllabus,
    build_syllabus,
    format_record,
    split_tech_stack,
    stage_5_lookup,
)
from tutor.data import fetch_records

st.set_page_config(
    page_title="Tutor Module",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

PLOT_CONFIG = {"displayModeBar": False, "responsive": True}
PALETTE = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3"]


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #


@st.cache_data(show_spinner="Reading batch records...")
def load_syllabus() -> tuple[list[dict], Syllabus]:
    """Load records and run the pipeline once per session.

    ``st.cache_data`` replaces the original's import-time computation: the
    five stages now run on first request and are reused thereafter, instead of
    once per server boot.
    """
    records = fetch_records()
    return records, build_syllabus(records)


@st.cache_data(show_spinner=False)
def frequency_frame(counts: list[tuple[str, int]]) -> pd.DataFrame:
    return pd.DataFrame(counts, columns=["Technology", "Students"])


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #


def cohort_chart(profile) -> go.Figure:
    figure = go.Figure(
        go.Pie(
            labels=["CS/IT background", "Non-CS/IT background"],
            values=[profile.cs_it, profile.non_cs_it],
            hole=0.55,
            marker=dict(colors=PALETTE[:2], line=dict(width=2, color="white")),
            textinfo="label+value",
            hovertemplate="%{label}: %{value} students<extra></extra>",
        )
    )
    figure.update_layout(
        title="Cohort composition",
        margin=dict(t=50, b=10, l=10, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15),
    )
    return figure


def frequency_chart(counts: list[tuple[str, int]]) -> go.Figure:
    """Horizontal bar chart rather than the original pie chart.

    The original drew all 26 technologies as pie slices, which is unreadable
    past a handful of categories. Sorted bars stay legible at any length.
    """
    technologies = [name for name, _ in counts]
    students = [count for _, count in counts]

    figure = go.Figure(
        go.Bar(
            x=students,
            y=technologies,
            orientation="h",
            marker=dict(
                color=[
                    "#EF553B" if count >= config.SHORTLIST_THRESHOLD else "#8C9EFF"
                    for count in students
                ]
            ),
            hovertemplate="%{y}: %{x} students<extra></extra>",
        )
    )
    figure.update_layout(
        title="Technologies across the batch",
        xaxis_title="Students who already know it",
        yaxis=dict(autorange="reversed"),
        height=620,
        margin=dict(t=50, b=30, l=10, r=10),
    )
    return figure


def shortlist_chart(syllabus: Syllabus) -> go.Figure:
    """Doughnut of the shortlisted topics.

    Six categories is the right number for a pie, unlike the 26-case above.
    """
    topics = syllabus.topics
    figure = go.Figure(
        go.Pie(
            labels=[topic.name for topic in topics],
            values=[topic.weightage_value for topic in topics],
            hole=0.45,
            marker=dict(colors=PALETTE[: len(topics)], line=dict(width=2, color="white")),
            textinfo="label+percent",
            hovertemplate="%{label}: %{value}% of syllabus<extra></extra>",
        )
    )
    figure.update_layout(
        title="Weightage per shortlisted subject",
        margin=dict(t=50, b=10, l=10, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15),
    )
    return figure


def syllabus_frame(syllabus: Syllabus) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Subject": topic.name,
                "Students already knowing it": topic.students,
                "Weightage": topic.weightage_value,
                "Time allotted": topic.time,
            }
            for topic in syllabus.topics
        ]
    )


# --------------------------------------------------------------------------- #
# Views
# --------------------------------------------------------------------------- #


def render_batch_view(syllabus: Syllabus) -> None:
    profile = syllabus.profile

    st.subheader("Stage 1 · Profile the cohort")
    metric_columns = st.columns(3)
    metric_columns[0].metric("Total students", profile.total)
    metric_columns[1].metric("CS/IT background", profile.cs_it)
    metric_columns[2].metric("Non-CS/IT background", profile.non_cs_it)

    left, right = st.columns(2)
    with left:
        st.plotly_chart(cohort_chart(profile), config=PLOT_CONFIG, width="stretch")
        if profile.total:
            st.caption(
                f"{profile.cs_it_ratio:.0%} of the batch already holds a CS/IT degree."
            )
    with right:
        st.plotly_chart(
            frequency_chart(syllabus.technology_counts), config=PLOT_CONFIG, width="stretch"
        )

    st.divider()
    st.subheader("Stages 2–4 · The generated syllabus")

    st.caption(
        f"A topic is shortlisted when at least **{config.SHORTLIST_THRESHOLD} students** "
        "already know it — that is the band where the batch is genuinely uneven and "
        "class time actually changes the outcome."
    )

    chart_column, table_column = st.columns([1, 1.4])
    with chart_column:
        st.plotly_chart(shortlist_chart(syllabus), config=PLOT_CONFIG, width="stretch")
        st.metric("Total syllabus weightage", f"{syllabus.total_weightage}%")

    with table_column:
        st.dataframe(
            syllabus_frame(syllabus),
            width="stretch",
            hide_index=True,
            column_config={
                "Students already knowing it": st.column_config.NumberColumn(
                    "Students knowing it", format="%d"
                ),
                "Weightage": st.column_config.ProgressColumn(
                    "Weightage", format="%d%%", min_value=0, max_value=100
                ),
            },
        )
        st.caption(
            f"{len(syllabus.topics)} of {len(syllabus.technology_counts)} technologies "
            "on student résumés survive into the syllabus."
        )


def render_lookup_view(records: list[dict], syllabus: Syllabus) -> None:
    st.subheader("Stage 5 · Individual student record")

    with st.form("lookup_form", clear_on_submit=False):
        query_columns = st.columns(2)
        name = query_columns[0].text_input("Full name", placeholder="Enter full name")
        dob = query_columns[1].text_input("Date of birth", placeholder="DD/MM/YYYY")
        submitted = st.form_submit_button("Search", type="primary")

    with st.expander("Need a valid name and date of birth to try?"):
        st.info(
            f"Use the record for **{records[0]['name']}** — "
            f"born **{records[0]['dob']}** — to see a populated result."
        )

    if not submitted:
        st.caption("Enter both fields to look up a student.")
        return

    record = stage_5_lookup(records, name, dob)

    if record is None:
        st.error("No student matches that name and date of birth.")
        return

    st.success(f"Record found for {record['name']}.")

    label_column, value_column = st.columns([1, 2])
    with value_column:
        st.dataframe(
            pd.DataFrame(format_record(record), columns=["Field", "Value"]),
            width="stretch",
            hide_index=True,
        )
    with label_column:
        technologies = split_tech_stack(record.get("tech_stack", ""))
        st.metric("Technologies listed", len(technologies))
        st.caption(f"Serial no. {record.get('serial_no')}")


def render_about(syllabus: Syllabus) -> None:
    st.subheader("How this syllabus was produced")
    st.markdown(
        f"""
1. **Profile** — `{syllabus.profile.total}` students split by graduation stream into
   CS/IT and non-CS/IT, and every technology on their résumés tallied. The tally for a
   topic *is* the number of students who already know it.
2. **Shortlist** — keep only topics known by **≥ {config.SHORTLIST_THRESHOLD}** students.
   A topic nobody knows does not belong to this course; a topic everyone knows does not
   need a classroom.
3. **Weightage** — map student count to a percentage of the syllabus.
4. **Time** — convert weightage into days and weeks.
5. **Records** — look up one student on demand.

The decision tables live in [`tutor/config.py`](https://github.com/pranaybhatkar/Tutor_Module/blob/master/tutor/config.py)
so the logic can be changed without touching the pipeline.
"""
    )


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #


def main() -> None:
    st.title("🎓 Tutor Module")
    st.caption("A student-centric tutoring platform that designs the syllabus from the batch itself.")

    try:
        records, syllabus = load_syllabus()
    except FileNotFoundError as error:
        st.error(f"Could not load the batch spreadsheet: {error}")
        st.stop()
    except Exception as error:  # noqa: BLE001 -- surface anything, but readably
        st.error(f"Failed to build the syllabus: {error}")
        st.code(str(error), language="text")
        st.stop()

    if not records:
        st.warning("The batch spreadsheet contains no student records.")
        st.stop()

    with st.sidebar:
        st.markdown("### Navigation")
        mode = st.radio(
            "Choose a view",
            ("Batch analysis", "Student lookup"),
            label_visibility="collapsed",
        )
        st.divider()
        st.caption(
            f"**{syllabus.profile.total}** students · "
            f"**{len(syllabus.technology_counts)}** technologies · "
            f"**{len(syllabus.topics)}** shortlisted"
        )

    if mode == "Batch analysis":
        render_batch_view(syllabus)
    else:
        render_lookup_view(records, syllabus)

    with st.expander("How this works"):
        render_about(syllabus)


if __name__ == "__main__":
    main()