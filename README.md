# Workout Analytics Tracker

An interactive workout tracker built to go beyond simple logging — every screen
is backed by real analysis of the underlying data, not just a table of numbers.
Built as a portfolio project to demonstrate applied data analysis: SQL schema
design, Python/Pandas data processing, and dashboard delivery.

## Why this project

Most workout trackers (e.g. Strong) log sets and lock analytics behind a paid
tier. This project does the opposite: analytics and insights are the point,
computed live from a relational database, and the exercise library includes
niche movements (Jefferson Curl, Sissy Squat, Copenhagen Plank, etc.) that
mainstream apps don't cover.

## Tech stack

| Layer | Tool | Purpose |
|---|---|---|
| Database | SQLite | Relational schema: `exercises`, `workouts`, `sets` with foreign keys |
| Data access | Python (`sqlite3`) | Parameterized queries, multi-table JOINs |
| Analysis | Pandas / NumPy | Aggregation, estimated 1RM (Epley formula), linear regression trend detection |
| Dashboard | Streamlit | Interactive web UI, no separate frontend framework needed |
| Charts | Plotly | Interactive line/bar charts |

## Features

- **Log workouts** against a real exercise catalog (standard + niche lifts)
- **History view** via a full SQL JOIN across all three tables
- **Analytics tab**, including:
  - Estimated 1-rep-max trend per exercise (Epley formula)
  - Total training volume per session
  - Automatic **plateau detection** (no PR in last N sessions)
  - **Progressive overload trend** via NumPy linear regression, not just a chart to eyeball
  - **Muscle group volume balance** over the trailing 30 days, to flag training imbalances

## Running it locally

```bash
pip install -r requirements.txt
python seed_data.py     # generates ~3 months of sample data
streamlit run app.py
```

## Project structure

```
workout_tracker/
├── schema.sql       # SQL table definitions
├── db.py            # database access layer (all raw SQL lives here)
├── analytics.py      # pandas/numpy analysis functions
├── seed_data.py      # generates realistic sample data
├── app.py            # Streamlit dashboard
└── requirements.txt
```

## Possible extensions

- Export analytics summaries to CSV/Excel for a "weekly report" use case
- Add a REST API layer (FastAPI) in front of the database
- Deploy the dashboard publicly via Streamlit Community Cloud
