# Tutor Module

> A student-centric tutoring platform that reads a batch's profile and **designs a syllabus from it** — deciding which topics to teach, how much weightage to give each, and how long each should take.

[![Live Demo](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://tutormodule-pranay-b-portfolio.streamlit.app)

**[Try it live →](https://tutormodule-pranay-b-portfolio.streamlit.app)** · **[Architecture diagram →](https://pranaybhatkar.github.io/tutor_module/architecture.html)**

[![Streamlit](https://img.shields.io/badge/Streamlit-1.65-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![pandas](https://img.shields.io/badge/pandas-3.0-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![pytest](https://img.shields.io/badge/tests-60%20passing-42A5F5?logo=pytest&logoColor=white)](tests/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## Table of Contents

- [The Problem](#the-problem)
- [The Idea](#the-idea)
- [How It Works — The 5-Stage Pipeline](#how-it-works--the-5-stage-pipeline)
- [Verified Output on the Sample Batch](#verified-output-on-the-sample-batch)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Repository Structure](#repository-structure)
- [Data Model](#data-model)
- [Getting Started](#getting-started)
- [Deployment](#deployment)
- [Project Evolution — FastAPI → Streamlit](#project-evolution--fastapi--streamlit)
- [Testing](#testing)
- [Design Decisions & Trade-offs](#design-decisions--trade-offs)
- [Known Limitations](#known-limitations)
- [Future Work](#future-work)
- [Data Privacy](#data-privacy)
- [Security Notice](#security-notice)
- [Contributing](#contributing)
- [License](#license)

---

## The Problem

A tutor taking on a new batch cannot answer three very basic questions before day one:

1. **Who am I actually teaching?** How many students are already from a CS/IT background versus coming from something else entirely?
2. **What should I teach?** A boilerplate syllabus assumes everyone starts from zero. If 19 of 30 students already know Python, spending three weeks on it is wasted time.
3. **How long should each topic take, and in what order?**

Manual answers mean manually reading 30 résumés and building a spreadsheet. That's slow, subjective, and it doesn't repeat.

## The Idea

**Let the batch data drive the syllabus.**

The platform ingests a batch's profile sheet, and from the raw data alone derives a defensible teaching plan. It measures what the cohort already knows, drops topics that are already covered, and spends the remaining hours on the topics with the largest gaps. A tutor who has run the numbers walks into the first class with a plan instead of a guess.

The name for this in the codebase is **"Priorities"** — the pipeline was originally organised into five numbered stages, and that naming survives the rewrite.

---

## How It Works — The 5-Stage Pipeline

All of the intelligence lives in [`tutor/analysis.py`](tutor/analysis.py).

### Stage 1 — Profile the cohort

**How diverse is the batch?** Every student's `graduation_stream` is scanned. If it contains `"Computer"` or `"Information Technology"` the student counts as CS/IT, otherwise as non-CS/IT. The tutor now knows whether they're teaching a homogeneous CS batch or a mixed one.

**What does the cohort already know?** The `tech_stack` column holds a comma-separated string per student (`"Python,SQL,Mongodb"`):

```
"Python,SQL,Mongodb"  →  split(',')  →  ['Python', 'SQL', 'Mongodb']
                      →  flatten     →  90 individual entries (with duplicates)
                      →  count each   →  {'Python': 19, 'SQL': 18, ...}
```

The count for each technology **is the number of students who already know it** — a direct measure of how much teaching that topic requires.

### Stage 2 — Shortlist the topics

A topic is shortlisted only if **5 or more students already know it**.

This is the core insight, and it is worth stating plainly because it is counter-intuitive: *a topic is worth teaching only if many students already know it.* If nobody knows it, it either doesn't belong in this course or belongs elsewhere. If nearly everyone knows it, it isn't worth class time. The sweet spot is the middle — a topic that a meaningful chunk of the batch is shaky on.

For the sample batch, 26 unique technologies collapse to **6 shortlisted topics**.

### Stage 3 — Assign weightage

Each shortlisted topic maps to a percentage of the syllabus based on how many students already know it.

| Students who know it | Weightage |
| :--- | :--- |
| 5 – 7 | 5% |
| 8 – 14 | 10% |
| 15 – 18 | 30% |
| 19 – 21 | 45% |
| 22 + | 50% |

### Stage 4 — Convert weightage to time

| Weightage | Time allotted |
| :--- | :--- |
| 5% | 3 Days |
| 10% | 1 Week |
| 30% | 2 Weeks |
| 45% | 3 Weeks |
| 50% | 4 Weeks |

### Stage 5 — Retrieve individual records

The same data supports per-student lookup, so a tutor can pull up one learner's full academic and technical profile on demand.

### The pipeline visually

```
   Student Records  (30 rows)
          │
          ▼
  ┌───────────────────────┐
  │  1. PROFILE          │  CS/IT vs Non-CS/IT split
  │                      │  + technology frequency map
  └───────────┬───────────┘
              ▼  26 unique technologies
  ┌───────────────────────┐
  │  2. SHORTLIST         │  keep topics known by >= 5 students
  └───────────┬───────────┘
              ▼  6 topics
  ┌───────────────────────┐
  │  3. WEIGHTAGE         │  student count  →  % of syllabus
  └───────────┬───────────┘
              ▼  6 topics weighted
  ┌───────────────────────┐
  │  4. TIME              │  weightage  →  days/weeks
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │  5. INDIVIDUAL LOOKUP │  single-student record fetch
  └───────────────────────┘
```

---

## Verified Output on the Sample Batch

The repository ships a 30-student batch file ([`data/sample_batch_30.xlsx`](data/sample_batch_30.xlsx)). These are the **actual computed values**, locked in by the test suite — not illustrations.

### Cohort split

| Metric | Value |
| :--- | ---: |
| CS/IT background | 14 |
| Non-CS/IT background | 16 |
| **Total students** | **30** |

An almost perfectly even split — the batch is genuinely mixed, so foundational material is warranted.

### Technology frequency — all 26

| Technology | Students | | Technology | Students |
| :--- | ---: | :-- | :--- | ---: |
| Python | 19 | | R | 4 |
| SQL | 18 | | Java | 3 |
| Mongodb | 11 | | React | 3 |
| Linux | 5 | | NodeJS | 3 |
| PLSQL | 5 | | HTML | 3 |
| Flask | 5 | | C++ | 3 |
| Big_data | 1 | | LT Spice | 3 |
| PowerBi | 1 | | CSS | 2 |
| PHP | 1 | | GCP | 2 |
| Software Testing (Manual & Automation) | 1 | | Docker | 2 |
| Full-Stack Development | 1 | | C# | 2 |
| Software Testing | 1 | | AWS | 1 |
| Cadence | 1 | | C | 1 |

### Final generated syllabus

Six topics survive Stages 2–4, and the weightages sum to exactly **100%**:

| Subject | Students already know it | Weightage | Time allotted |
| :--- | ---: | :---: | :--- |
| Python | 19 | 45% | 3 Weeks |
| SQL | 18 | 30% | 2 Weeks |
| Mongodb | 11 | 10% | 1 Week |
| Linux | 5 | 5% | 3 Days |
| PLSQL | 5 | 5% | 3 Days |
| Flask | 5 | 5% | 3 Days |
| **Total** | | **100%** | **~9 Weeks** |

### What this tells a tutor

> Almost half the batch already writes Python, and another 60% already know SQL — so **7 of the 9 weeks should not be spent on fundamentals the class already has**. Instead, spend a third of a term on Python, two weeks on SQL, and use the remainder to build out MongoDB, Linux, Flask, and PL/SQL from the ground up. Nineteen of the 26 technologies that appear on student résumés never make it into the syllabus at all.

---

## Tech Stack

### Application

| Technology | Role |
| :--- | :--- |
| **Python 3.11** | Runtime |
| **Streamlit 1.65** | UI framework, charting, caching, app lifecycle |
| **Plotly 7.1** | Interactive donut, bar and doughnut charts |
| **pandas 3.0** | Spreadsheet ingestion, table creation |
| **openpyxl** | `.xlsx` engine |
| **SQLite** | On-disk relational store, built automatically on first run |
| **pytest 9** | Test suite |

### What the stack used to be

| Removed | Why |
| :--- | :--- |
| FastAPI + Uvicorn + Gunicorn | Stateless-serverless hosting doesn't fit a stateful, import-time-computing app — see [Project Evolution](#project-evolution--fastapi--streamlit) |
| Jinja2 templates (×7) | Streamlit renders natively |
| CanvasJS + jQuery (CDN) | Streamlit bundles the charting layer |
| Hand-written `fetch()` JavaScript | Native widget reruns replace it |
| `mysql-connector-python` | No external database means nothing to configure or leak |
| `mysqlclient`, `Scrapy`, `Twisted`, the Zope stack (~150 packages) | Environment dump artefact; never imported |

---

## Architecture

> **📐 [Interactive runtime architecture diagram →](https://pranaybhatkar.github.io/tutor_module/architecture.html)**
>
> A standalone, explorable HTML diagram covering the runtime: **11 components**, one
> primary request path, external dependencies, and **two trust boundaries** (the hosted
> container, and the ephemeral SQLite store nested inside it). Every component carries
> click-through source links to the exact lines in this repository, pinned to commit
> [`5b08ad7`](https://github.com/pranaybhatkar/tutor_module/tree/5b08ad7fe862c969176d2c5d7b2bd32e256b6df9).
>
> It is a single self-contained file with no external scripts or fonts, served
> as-is through GitHub Pages, so the link above renders it directly. The source is
> [`docs/architecture.html`](https://github.com/pranaybhatkar/tutor_module/blob/master/docs/architecture.html)
> if you would rather read or download it.

```
┌──────────────────────────────────────────────────────────┐
│  Streamlit runtime (serverless or local)                 │
└───────────────────────┬──────────────────────────────────┘
                        │
             ┌──────────▼──────────┐
             │       app.py       │  UI only:
             │                     │  metrics · charts · forms
             └──────────┬──────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
┌───────▼────────────────┐   ┌──────────▼──────────────┐
│  tutor/analysis.py     │   │   tutor/data.py         │
│  ─────────────────     │   │  ──────────────────     │
│  Stage 1  Profile      │   │  read_spreadsheet()     │
│  Stage 2  Shortlist    │   │  ensure_database()      │
│  Stage 3  Weightage    │   │  fetch_records()        │
│  Stage 4  Time         │   └──────────┬──────────────┘
│  Stage 5  Lookup       │              │
│                        │     ┌────────▼─────────┐
│  pure functions,       │     │  SQLite          │
│  no I/O, no framework  │     │  data/tutor.db   │
└────────────────────────┘     │  table: students │
                               └────────┬─────────┘
                                        │
                               ┌────────▼─────────────┐
                               │ data/sample_batch_30 │
                               │        .xlsx         │
                               │   (seed source)      │
                               └──────────────────────┘

              tutor/config.py  ── all decision tables live here
```

**Two structural improvements over the original:**

1. **No work at import time.** The original opened a database connection and ran all five stages when `main.py` was imported, so the app could not start if the database was unreachable. Now `data.py` builds the database lazily on first use and `analysis.py` is pure — no I/O, no framework imports, directly testable.

2. **Computed once per session.** `@st.cache_data` runs the pipeline on first request and reuses the result, replacing once-per-server-boot.

---

## Repository Structure

```
tutor_module/
├── app.py                        # Streamlit entry point — UI only
├── requirements.txt              # 5 real dependencies
├── .streamlit/
│   └── config.toml               # headless mode + theme
│
├── tutor/                        # the application package
│   ├── __init__.py
│   ├── config.py                 # ⭐ all decision tables live here
│   ├── data.py                   # spreadsheet → SQLite → records
│   └── analysis.py               # ⭐ the five-stage pipeline
│
├── data/
│   ├── sample_batch_30.xlsx      # 30 student records (anonymised)
│   └── tutor.db                  # generated on first run — gitignored
│
├── scripts/
│   └── sanitize_source_data.py   # one-time anonymisation migration
│
├── tests/
│   ├── test_pipeline.py          # 44 tests — algorithm + data hygiene
│   └── test_app.py               # 16 tests — end-to-end UI
│
├── docs/
│   └── architecture.html         # interactive runtime architecture diagram
│
└── README.md
```

---

## Data Model

A single SQLite table, `students`, created automatically by `pandas.DataFrame.to_sql()` on first run. The spreadsheet header maps to canonical column names on import:

| # | Column | Source header | Example |
| :--: | :--- | :--- | :--- |
| 1 | `serial_no` | `Serial_no` | `1` |
| 2 | `name` | `Name` | `Pranay Avinash Bhatkar` |
| 3 | `dob` | `DOB` | `21/02/1997` |
| 4 | `graduation_stream` | `Graduation_Stream` | `B.E. Electronics` |
| 5 | `institution` | `Institute_University` | `Vidyalankar Institute of Technology` |
| 6 | `post_graduation_stream` | `Post Graduation_Stream_(NA_if_not_applicable)` | `P.G Diploma/Big Data Analytics` |
| 7 | `post_graduation_institution` | `Institute_University_(NA_if_not_applicable)` | `CDAC Acts/GOI` |
| 8 | `tech_stack` | `Tech_Stack_Certifications` | `Python,Big_data,PowerBi` |

`NA` is the explicit sentinel for "not applicable". `tech_stack` is a comma-delimited multi-value field — the single most important column in the schema, since every syllabus decision derives from it.

---

## Getting Started

### Prerequisites

Python 3.9 or newer. Nothing else — no database server, no Node, no Docker.

### 1. Clone and set up

```bash
git clone https://github.com/pranaybhatkar/tutor_module.git
cd tutor_module

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run

```bash
streamlit run app.py
```

Open **http://localhost:8501**.

The SQLite database is created from the spreadsheet on first start and reused after that. It is gitignored, so every fresh clone rebuilds it.

### 3. Reset after editing the spreadsheet

```python
from tutor.data import reset_database
reset_database()
```

### 4. Run the tests

```bash
python -m pytest -v
```

---

## Deployment

### Streamlit Community Cloud (recommended, free)

**This app is deployed there:** [tutormodule-pranay-b-portfolio.streamlit.app](https://tutormodule-pranay-b-portfolio.streamlit.app)

To deploy your own fork:

1. Fork or push the code to GitHub.
2. Go to **[share.streamlit.io](https://share.streamlit.io)**.
3. **Sign in with GitHub** and authorise Streamlit.
4. Pick your repository, branch `master`, main file `app.py`.
5. Set the Python version to `3.11` under *Advanced settings*.
6. Click **Deploy**.

Streamlit detects `requirements.txt` and `.streamlit/config.toml` automatically and builds a container for you.

`data/tutor.db` is gitignored, so the deployed app builds its own database from the spreadsheet on first request — nothing to provision.

> **Note:** Community Cloud apps sleep after ~12 hours without traffic, so the first
> page load after a long gap takes 30–90 seconds to wake up. Peak memory usage for this
> app is ~117 MB against the 1 GB per-app limit.

### Any other host

```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

Works on Render, Railway, Fly.io, or any VM with Python. Add a `Dockerfile` if your platform prefers one.

---

## Project Evolution — FastAPI → Streamlit

The first version was a **FastAPI + Jinja2 + CanvasJS** application deployed on Heroku. It worked, and it is preserved in git history. This version keeps the algorithm and replaces the delivery layer.

### Why it moved

| Constraint | Problem |
| :--- | :--- |
| **Heroku free tier** | The dyno shut down; the app now 404s |
| **Import-time computation** | `main.py` did `from Priorities import …`, which opened a MySQL connection and ran all five stages at boot. Unreachable database ⇒ the app never started, with no fallback |
| **Module-level mutable state** | `test = []` was mutated per request. Under `gunicorn -w 3` each worker held its own copy, so a lookup could hit a worker that never saw the value |
| **Serverless incompatibility** | The import-time DB work and per-request state make this a poor fit for edge platforms like Vercel, where functions are stateless and invocation-scoped |
| **No database infrastructure** | Hardcoded MySQL credentials meant the project could not run anywhere without those exact credentials |

### What changed

| Before | After |
| :--- | :--- |
| `main.py` — routes, auth, CORS, templates | `app.py` — UI only |
| `Priorities.py` — SQL + logic + `print` | `tutor/analysis.py` — pure functions |
| Hardcoded MySQL at import | `tutor/data.py` — lazy SQLite |
| Magic numbers inline | `tutor/config.py` — one decision table |
| 7 Jinja templates + `main.js` | Native Streamlit widgets |
| `requirements.txt` — 150 packages, UTF-16 | 5 dependencies |
| No tests | 60 tests |
| Bundled decision tables | Contiguous bands (bug fix, below) |

### Bugs fixed along the way

1. **Weightage gaps.** The original bands were `5–7`, `10–13`, `15–18`, `19–21`, `22–23`. A topic known by **8, 9, 14, or 24+** students matched nothing and was silently dropped from the syllabus with no error. The bands are now contiguous and exhaustive; every previously published result is unchanged.
2. **Broken student lookup.** A `for`/`else` whose `else` bound to the inner loop raised an `HTTPException` on the first non-matching record — so lookup only worked if the student was in record one.
3. **Mislabelled record fields.** The `Fields` list contained `'Institute/University'` twice while the real columns were `Institute_University` and `Institute_University_(NA_if_not_applicable)`, so zipping mislabelled the final column.
4. **Quadratic counting.** `list.count()` inside a loop over every unique subject became a single `Counter` pass.
5. **Mixed date types.** Most `DOB` values were `DD/MM/YYYY` strings, but row 7 held a raw Excel serial (`35489`). All dates are normalised to text on import.
6. **Double-seeded rows.** `to_sql(if_exists="append")` duplicated every student if the seed ran twice. Now `replace`.

---

## Testing

```bash
python -m pytest -v
# 60 passed
```

| Suite | Tests | Covers |
| :--- | ---: | :--- |
| `test_pipeline.py` | 44 | All five stages against the real dataset, plus regression tests for every bug listed above |
| `test_app.py` | 16 | The real `app.py` driven headlessly via `AppTest` — metrics, charts, tables, both views, and every lookup path |

The UI tests execute the actual application script, so a broken chart or an unhandled exception fails in CI rather than in front of a viewer.

---

## Design Decisions & Trade-offs

| Decision | Rationale | Trade-off |
| :--- | :--- | :--- |
| SQLite over MySQL | Zero infrastructure, still real SQL via `to_sql` and `SELECT` | Single-writer; not a multi-user server |
| `>= 5` shortlist cutoff | Empirical, derived from the real distribution | Needs recalibration for a different batch size |
| Bars not a pie for 26 categories | The original drew 26 pie slices — unreadable | Loses the "part of a whole" read, but gains clarity |
| Donut for the 6 shortlisted topics | Six slices is exactly where a pie still works | — |
| No login gate | A hardcoded `admin`/`password` check was security theatre; this is a public demo | Student records are readable by anyone who finds the app |
| Pipeline in a pure module | Testable without a database or a browser | Slightly more files than one big script |
| Decision tables in `config.py` | Tunables readable in one place without reading logic | One extra import |
| `Counter` over `list.count()` | O(n) instead of O(n²) | — |

---

## Known Limitations

1. **The heuristic is calibrated to a 30-student batch.** The `>= 5` cutoff and the weightage bands were derived from one dataset. A 200-student batch would need different thresholds.

2. **No authentication.** The original had a hardcoded credential check; removing it made the app honestly open rather than falsely closed. Anyone with the URL can look up any student. Add Streamlit's `[client] cookieSecret`-backed login before using this with real data.

3. **Static dataset.** The spreadsheet is read once per session. There is no upload, no per-course storage, no way to analyse a second batch in the same deployment.

4. **Weightage bands are a step function.** Counts 8–14 all get 10% regardless of whether there are 8 or 14 students. A continuous formula would be smoother but would change every published figure.

5. **Technology names are unnormalised.** `Python` and `python`, or `React` and `ReactJS`, would count as two topics. The shipped data is consistent; hand-entered data may not be.

6. **`NA` is overloaded.** It means both "no postgraduate degree" and "blank cell".

7. **No CI.** The test suite runs locally but nothing enforces it on push yet.

8. **`scripts/sanitize_source_data.py` is not re-runnable.** It is a one-time migration; the pre-sanitisation file lives in git history.

---

## Future Work

- [ ] Upload a batch spreadsheet through the UI instead of shipping it in the repo
- [ ] Multi-batch support — one batch per course, selectable at login
- [ ] Parameterise the shortlist threshold rather than hardcoding `5`
- [ ] Technology synonym/normalisation table (`ReactJS` → `React`)
- [ ] Continuous weightage function with a sanity check that totals 100%
- [ ] Export the generated syllabus to PDF or ICS calendar
- [ ] Mid-term assessment vs. the initial profile, to show whether the plan worked
- [ ] GitHub Actions running `pytest` on every push
- [ ] `ruff` + `mypy` in CI
- [ ] Optional password gate via Streamlit secrets

---

## Data Privacy

The original spreadsheet contained **30 real students' full names, dates of birth, universities and qualifications**, and was committed to a public repository.

Under the agreed **Option A** policy, [`data/sample_batch_30.xlsx`](data/sample_batch_30.xlsx) was migrated as follows:

| Rows | Treatment |
| :--- | :--- |
| `serial_no = 1` | **Left completely intact** — the repository owner's own record, kept so the project demonstrates a real end-to-end result |
| `serial_no = 2…30` | `name` → `Student 002…030`, `dob` → synthetic date |

Every field the algorithm reads — `graduation_stream`, `tech_stack`, `institution`, `post_graduation_stream` — was carried over **verbatim**. That is what guarantees the results in this README are identical before and after: **14 / 16**, **Python 19**, **SQL 18**, **100% weightage**. `tests/test_pipeline.py` asserts every one of those numbers, plus that no real name survives.

All dates of birth were also normalised to `DD/MM/YYYY`, which fixed the Excel-serial bug described above.

The migration is reproducible from [`scripts/sanitize_source_data.py`](scripts/sanitize_source_data.py).

> **Git history still contains the original file.** Sanitising the current tree does not remove past commits. Erasing it requires rewriting history or starting a fresh repository — see [Security Notice](#security-notice).

---

## Security Notice

The credentials that were hardcoded in the original `Priorities.py` **are gone from the current tree.** They are gone from `main.py` too, along with the `admin`/`password` check and the wide-open CORS configuration that combined `allow_origins=["*"]` with `allow_credentials=True`.

**But git history still contains all of it.** If those credentials were ever live — and the MySQL password was exposed on a public repository for the lifetime of the project — treat them as compromised:

1. **Rotate the MySQL password.** It was public. Assume it is compromised regardless of how long ago it was committed.
2. **Rewrite history or start a new repository** if the original spreadsheet should no longer be retrievable. `git filter-repo` on the commits that touched `static/Fynd_Batch3.xlsx` is the usual approach — but this rewrites every commit hash, so anyone with a clone must re-clone.
3. **Confirm the Clever Cloud and Heroku instances are shut down.** The Heroku app now 404s; the MySQL add-on may still exist and still be billable.

`git log --all -- static/Fynd_Batch3.xlsx` shows the commits holding the original file.

---

## Contributing

```bash
git checkout -b your-feature
# make changes
python -m pytest -v        # please keep the suite green
git commit -m "Describe your change"
git push origin your-feature
```

Two conventions worth preserving:

- **Tunable values belong in `tutor/config.py`.** Thresholds and decision tables should be readable without opening the logic.
- **No personal data in test fixtures.** Use synthetic records.

---

## License

Released under the MIT License. See [LICENSE](./LICENSE).

---

## Acknowledgements

Built as a full-stack data-engineering project: take a raw spreadsheet of student résumés and turn it into a defensible, explainable teaching plan — then rebuild the thing so anyone can run it with one command.