# Tutor Module

> A student-centric tutoring platform that reads a batch's profile and **designs a syllabus from it** — deciding which topics to teach, how much weightage to give each, and how long each should take.

[![Python](https://img.shields.io/badge/Python-3.8.5-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.75.0-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Jinja2](https://img.shields.io/badge/Jinja2-3.1.1-B41717?logo=jinja&logoColor=white)](https://jinja.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Heroku](https://img.shields.io/badge/Deploy-Heroku-79589B?logo=heroku&logoColor=white)](https://www.heroku.com/)
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
- [API Reference](#api-reference)
- [Application Flow](#application-flow)
- [Getting Started](#getting-started)
- [Database Seeding](#database-seeding)
- [Deployment](#deployment)
- [How We Built It](#how-we-built-it)
- [Design Decisions & Trade-offs](#design-decisions--trade-offs)
- [Known Limitations](#known-limitations)
- [Future Work](#future-work)
- [Security Notice](#security-notice)
- [Contributing](#contributing)
- [License](#license)

---

## The Problem

A tutor taking on a new batch cannot answer three very basic questions before day one:

1. **Who am I actually teaching?** How many students are already from a CS/IT background versus coming from something else entirely?
2. **What should I teach?** A boilerplate syllabus assumes everyone starts from zero. If 19 out of 30 students already know Python, spending three weeks on it is wasted time.
3. **How long should each topic take, and in what order?**

Manual answers to these questions mean manually reading 30 resumes and building a spreadsheet. That's slow, subjective, and it doesn't repeat.

## The Idea

**Let the batch data drive the syllabus.**

The platform ingests a batch's profile sheet, and from the raw data alone derives a defensible teaching plan. It measures what the cohort already knows, drops topics that are already covered, and spends the remaining hours on the topics with the largest gaps. A tutor who has run the numbers walks into the first class with a plan instead of a guess.

The name for this in the codebase is **"Priorities"** — the logic in `Priorities.py` is organised into five numbered stages, each narrowing the syllabus down one step.

---

## How It Works — The 5-Stage Pipeline

The entire intelligence of the app lives in `Priorities.py`, structured as five sequential stages:

### Stage 1 — Profile the cohort

Two questions are answered here.

**How diverse is the batch?** Every student's `Graduation_Stream` is scanned. If it contains `"Computer"` or `"Information Technology"` the student is counted as CS/IT, otherwise as non-CS/IT. The tutor now knows whether they're teaching a homogeneous CS batch or a mixed one — which drives how much foundational material is needed.

**What does the cohort already know?** The `Tech_Stack_Certifications` column holds a comma-separated string per student (`"Python,SQL,Mongodb"`). The pipeline:

```
"Python,SQL,Mongodb"  →  split(',')  →  ['Python', 'SQL', 'Mongodb']
                      →  flatten     →  90 individual entries (with duplicates)
                      →  de-duplicate →  26 unique technologies
                      →  count each   →  {'Python': 19, 'SQL': 18, ...}
```

The count for each technology **is the number of students who already know it** — which is a direct measure of how much teaching that topic actually requires.

### Stage 2 — Shortlist the topics

A topic is shortlisted only if **5 or more students already know it**.

This is the core insight of the project, and it is worth stating plainly because it is counter-intuitive: *a topic is worth teaching only if many students already know it.* If nobody knows it, it is either irrelevant to the batch or belongs in a different course. If nearly everyone knows it, it is not worth class time. The sweet spot is the middle — a topic that a meaningful chunk of the batch is shaky on.

For the sample batch, 26 unique technologies collapse to **6 shortlisted topics**.

### Stage 3 — Assign weightage

Each shortlisted topic is mapped to a percentage of the syllabus based on how many students already know it. The heavier the existing knowledge, the more class time it deserves to bring everyone to the same level.

| Students who know it | Weightage | Rationale |
| :--- | :--- | :--- |
| 5 – 7 | 5% | Small gap, light touch |
| 10 – 13 | 10% | Noticeable gap |
| 15 – 18 | 30% | Large gap, majority shaky |
| 19 – 21 | 45% | Largest gap in the batch |
| 22 – 23 | 50% | Effectively a blank slate |

### Stage 4 — Convert weightage to time

Weightage is abstract; a tutor needs a calendar.

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

The repository ships a real 30-student batch file (`static/Fynd_Batch3.xlsx`). These are the **actual computed values** from running the pipeline over it — not illustrations.

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

### Backend

| Technology | Version | Role |
| :--- | :--- | :--- |
| **Python** | 3.8.5 | Runtime (pinned via `runtime.txt`) |
| **FastAPI** | 0.75.0 | Web framework, routing, form parsing, JSON APIs |
| **Uvicorn** | 0.17.6 | ASGI server |
| **Gunicorn** | 20.1.0 | Process manager — runs 3 Uvicorn workers |
| **Jinja2** | 3.1.1 | Server-side template rendering |
| **python-multipart** | 0.0.5 | Required by FastAPI for `Form(...)` handling |
| **MySQL Connector/Python** | 8.0.28 | Database driver |

### Data

| Technology | Version | Role |
| :--- | :--- | :--- |
| **MySQL** | 8.0 | Managed instance on Clever Cloud |
| **SQLAlchemy** | 1.4.32 | Engine + automatic table creation from the DataFrame |
| **pandas** | 1.3.5 | Excel ingestion, table creation, `to_sql` |
| **openpyxl** | 3.0.9 | `.xlsx` engine backend for pandas |

### Frontend

| Technology | Role |
| :--- | :--- |
| **CanvasJS** | Pie and doughnut charts for the batch visualisations |
| **jQuery** | 1.11.1 (via CanvasJS CDN) — DOM manipulation and chart binding |
| **Vanilla JS `fetch`** | Async calls from page to JSON API |
| **HTML5 Forms** | Native `POST`/`GET` form navigation between pages |

No frontend framework, no build step, no bundler, no `node_modules`. Pages are server-rendered Jinja templates that call the app's own JSON endpoints on load.

### Deployment

| Technology | Role |
| :--- | :--- |
| **Heroku** | Hosting — configured via `Procfile` |
| **Clever Cloud** | Hosted MySQL database |

---

## Architecture

```
                      ┌──────────────────────────┐
   Browser  ────────► │  Heroku / Uvicorn        │
                      │  Gunicorn (3 workers)    │
                      └────────────┬─────────────┘
                                   │
                      ┌────────────▼─────────────┐
                      │       main.py            │
                      │  ┌────────────────────┐  │
                      │  │  HTML routes       │──┼──► templates/*.html
                      │  │  (Jinja2 render)   │  │
                      │  ├────────────────────┤  │
                      │  │  JSON API routes   │──┼──► fetch() in browser
                      │  └────────────────────┘  │
                      └────────────┬─────────────┘
                                   │ import
                      ┌────────────▼─────────────┐
                      │    Priorities.py         │
                      │  ┌────────────────────┐  │
                      │  │ Stage 1  Profile   │  │
                      │  │ Stage 2  Shortlist │  │
                      │  │ Stage 3  Weightage │  │
                      │  │ Stage 4  Time      │  │
                      │  │ Stage 5  Records   │  │
                      │  └────────────────────┘  │
                      └────────────┬─────────────┘
                                   │ mysql.connector
                      ┌────────────▼─────────────┐
                      │      MySQL (Clever Cloud)│
                      │        table: test_3     │
                      │      30 student records  │
                      └──────────────────────────┘

              static/Fynd_Batch3.xlsx
                   (one-time seed source)
```

**One important structural note:** `Priorities.py` runs its queries and all five stages **at module import time**. Because `main.py` does `from Priorities import ...`, the entire dataset is read, analysed, and held in memory when the web server boots. This is why the JSON endpoints return plain pre-computed lists rather than querying per request — it is fast and simple, but it means the dataset is fixed until the server restarts, and it does not scale to a dynamic multi-batch system.

---

## Repository Structure

```
Tutor_Module/
├── main.py                    # FastAPI app — all routes, auth, CORS
├── Priorities.py              # The 5-stage algorithm + MySQL queries
├── requirements.txt           # Full dependency list (UTF-16 encoded)
├── runtime.txt                # Python 3.8.5 pin for Heroku
├── Procfile                   # gunicorn -w 3 -k uvicorn.workers.UvicornWorker main:app
├── .gitignore                 # __pycache__/, .idea/
│
├── static/
│   ├── Fynd_Batch3.xlsx           # Sample batch — 30 student records
│   └── Fynd_Batch3 - Copy.xlsx    # Working duplicate
│
└── templates/
    ├── index.html                         # Login page
    ├── output_selection.html             # Choose batch vs individual view
    ├── individual_student_entry.html      # Student lookup form
    ├── individual_student_details.html   # Single student record table
    ├── batch_details_one.html            # Charts: cohort split + tech frequency
    ├── batch_details_two.html            # Charts: shortlist + weightage/time tables
    └── main.js                           # Standalone fetch logic (early draft)
```

---

## Data Model

A single table, `test_3`, created automatically by `pandas.DataFrame.to_sql()`. The source spreadsheet header row becomes the column names:

| # | Column | Type | Example |
| :--: | :--- | :--- | :--- |
| 1 | `Serial_no` | int | `1` |
| 2 | `Name` | varchar | `Pranay Avinash Bhatkar` |
| 3 | `DOB` | varchar | `21/02/1997` |
| 4 | `Graduation_Stream` | varchar | `B.E. Electronics` |
| 5 | `Institute_University` | varchar | `Vidyalankar Institute of Technology/University of Mumbai` |
| 6 | `Post Graduation_Stream_(NA_if_not_applicable)` | varchar | `P.G Diploma/Big Data Analytics` |
| 7 | `Institute_University_(NA_if_not_applicable)` | varchar | `CDAC Acts/GOI` |
| 8 | `Tech_Stack_Certifications` | varchar | `Python,Big_data,PowerBi` |

`NA` is used as an explicit sentinel for students with no postgraduate degree. `Tech_Stack_Certifications` is a comma-delimited multi-value field — the single most important column in the schema, since every syllabus decision derives from it.

---

## API Reference

### JSON endpoints

These return computed results and are what the frontend's `fetch()` calls consume.

| Method | Endpoint | Returns | Example response |
| :--- | :--- | :--- | :--- |
| `GET` | `/Count` | CS/IT vs non-CS/IT split | `{"count": [14, 16]}` |
| `GET` | `/Tech_Stack_Certifications` | Unique tech list | `{"...": ["Python", "SQL", ...]}` |
| `GET` | `/Tech_Stack_Certifications_Known_By_Students` | Technology + student count | `{"subject_count": [("Python", 19), ...]}` |
| `GET` | `/Shortlisting_the_subjects` | Topics known by ≥ 5 students | `{"shortlist": [("Python", 19), ...]}` |
| `GET` | `/Weightage_per_Subject` | Syllabus weightage per topic | `{"weightage": [("Python", "45%"), ...]}` |
| `GET` | `/Time_Period_per_Subject` | Time allotted per topic | `{"Time": [("Python", "3_Weeks"), ...]}` |
| `GET` | `/individual_student_details` | One student's full record | `{"details": [["Serial_no", "1"], ...]}` |

### Page routes

| Method | Endpoint | Purpose | Template |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Login page | `index.html` |
| `POST` | `/input_details` | Validate tutor credentials | `output_selection.html` |
| `POST` | `/output_selection` | Branch: individual vs batch | depends on choice |
| `POST` | `/individual_student_records` | Validate student lookup | `individual_student_details.html` |
| `GET` | `/output` | Page 2 of batch view | `batch_details_two.html` |
| `GET` | `/previous_output` | Back to page 1 | `batch_details_one.html` |
| `GET` | `/selection_page` | Back to mode selection | `output_selection.html` |
| `GET` | `/individual_entry` | Back to student lookup | `individual_student_entry.html` |

Interactive API docs are available at `/docs` and `/redoc` while the app is running, courtesy of FastAPI's automatic OpenAPI generation.

---

## Application Flow

```
┌────────────────────┐
│  /  —  Login       │   Tutor enters credentials
│  "Management       │
│   System for       │
│   Tutors"         │
└─────────┬──────────┘
          │ POST /input_details
          ▼
┌────────────────────┐
│  Mode Selection    │   Choose a view:
└─────────┬──────────┘
     ┌────┴─────┐
     ▼          ▼
┌─────────┐  ┌──────────────────────────────┐
│ Batch   │  │  BATCH VIEW                  │
│ View    │  │  Page 1 →  Pie: cohort split  │
│         │  │            Pie: tech frequency│
│         │  │  [Next] →                     │
│         │  │  Page 2 →  Doughnut: shortlist│
│         │  │           Table: weightage     │
│         │  │           Table: time          │
│         │  │  [Previous] → back to page 1   │
└─────────┘  └──────────────────────────────┘
     │
     ▼
┌──────────────────────────────┐
│  INDIVIDUAL VIEW             │
│  Enter username + DOB        │
│  → validated against DB      │
│  → Field/Value table of the  │
│    matched student           │
└──────────────────────────────┘
```

Charts are rendered with **CanvasJS**, loaded from CDN, and populated by `fetch()` calls to the app's own JSON endpoints using `window.location.origin` as the base — so the same code works on localhost and on the deployed Heroku URL without changes.

---

## Getting Started

### Prerequisites

- Python 3.8+
- A MySQL database (local, or a managed instance)
- `pip` and `virtualenv`

### 1. Clone

```bash
git clone https://github.com/pranaybhatkar/Tutor_Module.git
cd Tutor_Module
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `requirements.txt` is saved as UTF-16, so some `pip` versions may misread it. If installation misbehaves, re-save the file as UTF-8 first.

### 4. Configure the database connection

Open `Priorities.py` and point the connector at your database. **Read the [Security Notice](#security-notice) before copying the credentials currently in this repository.**

```python
connector = mysql.connector.connect(
    host='localhost',
    database='Test_2',
    user='root',
    password='your_password'
)
```

### 5. Seed the database

See [Database Seeding](#database-seeding).

### 6. Run

```bash
uvicorn main:app --reload
```

Then open **http://127.0.0.1:8000**.

Interactive API docs: **http://127.0.0.1:8000/docs**

---

## Database Seeding

The table is created from the spreadsheet by pandas in one shot. These blocks ship **commented out** inside `Priorities.py` — uncomment them, run once, then re-comment:

```python
df = pd.read_excel('Fynd_Batch3.xlsx')

engine = create_engine("mysql://root:root@localhost/Test_2")
df.to_sql('test_3', con=engine, if_exists='append', index=False)

connector.commit()
```

- `read_excel()` — loads the batch sheet (requires `openpyxl`)
- `create_engine()` — URL format is `mysql://user:password@host/database`
- `to_sql(..., if_exists='append')` — creates `test_3` if absent, otherwise appends
- `index=False` — stops pandas adding its own index column
- `commit()` — persists; without it the data rolls back

Seeding twice will double your rows, since `append` is used.

---

## Deployment

### Heroku

Three files make this deployable as-is:

**`Procfile`**
```bash
web: gunicorn -w 3 -k uvicorn.workers.UvicornWorker main:app
```
Three Uvicorn workers under Gunicorn — the correct pattern for an ASGI app on a multi-dyno-free Heroku plan.

**`runtime.txt`**
```
python-3.8.5
```

**`requirements.txt`** — read automatically by the buildpack.

```bash
heroku create tutor-module
heroku addons:create clevertc-mysql
heroku config:set DB_HOST=... DB_NAME=... DB_USER=... DB_PASSWORD=...
git push heroku master
```

### Managed MySQL on Clever Cloud

The database in use is a Clever Cloud MySQL add-on, which supplies host, database name, user, and password as config vars — currently consumed directly inside `Priorities.py`. See [Security Notice](#security-notice).

---

## How We Built It

### Start with the data, then the algorithm

The project began in `Priorities.py` with **no web app at all** — the first priority was to prove the logic produced sensible output. `pandas` loaded the spreadsheet, `to_sql` created the table, and the five stages were written and verified in the terminal before a single line of FastAPI existed. Every stage `print()`s its result, and those print statements were the whole feedback loop during development.

This ordering mattered: the syllabus logic is the part that carries the actual idea, and it is completely independent of the delivery layer.

### Write it out longhand first

The code deliberately keeps its exploratory shape. You will see commented-out `print()` calls next to every block, alternative list-comprehension versions sitting beneath the loop-based ones, and long explanatory comments above each stage.

```python
# Longhand — nested loops, as first written
repetitive_subjects_list = []
for each_sub_list in subjects_list:
    for each_subject in each_sub_list:
        repetitive_subjects_list.append(each_subject)

# Equivalent comprehension
another_temp_list = [each_subject for each_sub_list in subjects_list
                     for each_subject in each_sub_list]
```

Both versions are kept. The longhand form documents the reasoning; the comprehension documents the idiom. This is the most verbose part of the codebase and it is intentional.

### Derive the threshold from the data, not from theory

No source said *"shortlist topics known by 5 or more students."* That number came from looking at the actual distribution — with 30 students, a cutoff of 5 isolated a meaningful middle band while discarding the long tail of one-off technologies (`PowerBi: 1`, `Cadence: 1`, `LT Spice: 3`). The weightage and time tables were then built around the counts that survived, which is why they sum to exactly 100% for this batch.

### Serve HTML over JSON APIs, not a SPA

Once the data pipeline worked, `main.py` wrapped it in two kinds of routes: page routes returning rendered Jinja templates, and JSON routes returning the computed lists. The templates then call the JSON routes with `fetch()` on `window.onload` and draw the results.

The payoff is that the analysis endpoints are independently useful — hit `/Weightage_per_Subject` directly and you get the syllabus as data, with no HTML involved. No frontend framework was needed to get there.

### Deploy early, deploy often

`Procfile` and `runtime.txt` were committed alongside the first working version rather than added at the end, which kept the Heroku deployment in a known-good state while the UI was being iterated on.

---

## Design Decisions & Trade-offs

| Decision | Rationale | Trade-off |
| :--- | :--- | :--- |
| Compute at import time | Endpoints are instant; total logic is visible in one file | Dataset frozen until restart; won't scale to many batches |
| `>= 5` shortlist cutoff | Empirical, derived from the real distribution | Not a general heuristic — a different batch size needs recalibration |
| Weightage buckets by student count | Translates a gap into concrete class time | Silent gaps between buckets (see below) |
| HTML forms for navigation | Zero frontend build tooling | Full page reloads; no client-side state |
| Server-rendered Jinja + `fetch()` | JSON endpoints stay reusable | Data rendered client-side anyway — a middle path between MPA and SPA |
| MySQL via `mysql.connector` | Real relational store, familiar tooling | Connection opened at import; no pooling |
| `pandas.to_sql()` seeding | Table shape stays defined by the spreadsheet | Header changes silently break column references |

---

## Known Limitations

Documented honestly, because several are visible in the code:

1. **Weightage buckets have gaps.** Ranges cover 5–7, 10–13, 15–18, 19–21, and 22–23. A subject known by **8, 9, 14, or 24+** students matches no bucket and is dropped without warning. On the sample batch nothing lands in a gap, but on other data it would.

2. **`Fields` in `main.py` is misaligned.** The list has `'Institute/University'` **twice**, while the real columns are `Institute_University` and `Institute_University_(NA_if_not_applicable)`. Zipping it against an 8-field record mislabels the final column.

3. **`for` / `else` in `/individual_student_records`.** The `else` belongs to the inner `for`, so an `HTTPException` is raised the first time a record fails to match. Student lookup effectively only works if the match is in the very first record examined.

4. **Duplicate function names.** `main.py` defines several functions all named `index`, and four all named `get_tech_stack_certifications`. FastAPI registers routes at decoration time so it still runs, but the names are meaningless for debugging.

5. **State lives in a module-level list.** `test = []` in `main.py` is mutated per request. Under Gunicorn's 3 workers each has its own copy, so a lookup can hit a different worker than the one holding the value.

6. **`DOB` is inconsistently typed.** Most rows store a string like `21/02/1997`, but at least one stores an Excel serial number (`35489`) — visible in the seed file.

7. **No tests, no CI, no linter.** Verification was manual via `print()` output.

8. **`main.js` is dead code.** The working fetch logic was inlined into the templates; `templates/main.js` is an earlier draft with hardcoded `localhost:8000` URLs, and the `<script>` tag referencing it in `index.html` is commented out.

---

## Future Work

- Move credentials to environment variables and add a `.env` / `pydantic-settings` config
- Replace the weightage ranges with a continuous formula so no count can fall through a gap
- Convert the nested-loop flat-map to `str.split(',')` + `set()` / `Counter()`
- Move computation out of module import into a service layer with caching
- Multi-batch support — one batch per course, selectable at login
- Parameterise the shortlist threshold instead of hardcoding `5`
- Correct the `Fields` alignment and rework student lookup with proper SQL
- Replace `print()` verification with a pytest suite over the pipeline
- CI with ruff + pytest on push
- Progress tracking — compare a mid-term assessment against the initial profile
- Move to server-side sessions with hashed passwords instead of the hardcoded check

---

## Security Notice

> ### Please read before reusing this code
>
> This repository is a learning project and its original state contains several
> genuine security problems. They are listed here rather than hidden.

1. **Live database credentials are hardcoded in `Priorities.py` and committed to a public repository.** The commit history still contains them. **Rotate that password now** — do not assume it is safe because the code is old. Then move to environment variables:
   ```python
   connector = mysql.connector.connect(
       host=os.environ['DB_HOST'],
       database=os.environ['DB_NAME'],
       user=os.environ['DB_USER'],
       password=os.environ['DB_PASSWORD'],
   )
   ```

2. **Tutor credentials are hardcoded** in `main.py` as a plaintext `username == 'admin' and password == 'password'` comparison. Replace with hashed passwords and server-side sessions.

3. **CORS is fully open** — `allow_origins` includes `"*"` alongside `allow_credentials=True`. This permits any origin to make credentialed requests. Restrict to the actual deployment origins and never combine `"*"` with credentials.

4. **The seed spreadsheet contains real personal data** — 30 students' full names, dates of birth, universities, and qualifications. If these are real people, remove the file from the repository and consider whether GitHub's cached or forked copies need handling.

5. **`individual_student_details` has no access control.** Once a lookup is cached in the `test` list, the record is served to whoever requests it.

None of these are theoretical. If this is still deployed anywhere, treat it as an open system until items 1–3 are fixed.

---

## Contributing

Contributions are welcome, particularly around the items in [Future Work](#future-work).

```bash
git checkout -b your-feature
# make changes
git commit -m "Describe your change"
git push origin your-feature
```

Please do not commit credentials, and avoid adding real personal data to test fixtures.

---

## License

Released under the MIT License. See [LICENSE](./LICENSE) for details.

---

## Acknowledgements

Built as a full-stack data-engineering project — the exercise was taking a raw spreadsheet of student résumés and turning it into a defensible, explainable teaching plan.