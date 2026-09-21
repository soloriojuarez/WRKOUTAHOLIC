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
| Statistical inference | SciPy | Hypothesis testing (Welch's t-test), regression p-values/confidence intervals |

## Features

- **Log workouts** against a real exercise catalog (standard + niche lifts)
- **History view** via a full SQL JOIN across all three tables
- **Analytics tab**, including:
  - Estimated 1-rep-max trend per exercise (Epley formula)
  - Total training volume per session
  - Automatic **plateau detection** (no PR in last N sessions)
  - **Progressive overload trend** via NumPy linear regression, not just a chart to eyeball
  - **Muscle group volume balance** over the trailing 30 days, to flag training imbalances
- **Next Workout** tab: a greedy priority-queue algorithm (`heapq`) recommends the next
  session's exercises by always correcting the most under-trained muscle group first
- **Stats Lab** tab:
  - SQL window functions (`LAG`, `RANK`, moving average via `ROWS BETWEEN`) computed
    natively in SQLite, not pandas
  - Hypothesis testing: is the progressive-overload trend statistically significant
    (p-value + 95% CI via `scipy.stats.linregress`), and does rep range make a real
    difference to estimated 1RM (Welch's t-test) - explicitly flagged as an
    observational comparison, not a randomized experiment

## Metrics dictionary

Precise definitions and known limitations for every derived metric - the kind of
documentation a data team expects alongside the numbers themselves.

| Metric | Definition | Limitations / caveats |
|---|---|---|
| **Estimated 1RM** | Epley formula: `weight * (1 + reps / 30)` | Accuracy degrades above ~10-12 reps, where all 1RM formulas diverge from measured maxes |
| **Volume** | `weight x reps`, summed across all sets in a session | Doesn't account for exercise difficulty/leverage - 100 lbs on a Squat isn't equivalent effort to 100 lbs on a Landmine Press |
| **Progressive overload trend (slope)** | OLS regression slope of best-set est. 1RM vs. session index | A point estimate only - see "trend significance" below for whether it's distinguishable from noise |
| **Trend significance** | p-value and 95% CI on the regression slope (`scipy.stats.linregress`) | Assumes independent, identically distributed residuals; small-N sessions widen the CI a lot |
| **Plateau flag** | True if no new best-set PR in the last 4 sessions | Fixed lookback window (4) isn't tuned per exercise or training experience level |
| **Muscle group deficit** | `target% - actual%`, where target is an equal share across every muscle group in the catalog | Equal-share is a simplifying assumption - real programming often intentionally weights legs/back higher than arms |
| **Rep-range comparison p-value** | Welch's two-sample t-test on est. 1RM, low-rep (<=6) vs. high-rep (>=8) sets | **Observational, not randomized** - rep range is confounded with training time, so significance shows association, not causation |
| **Session-over-session % change / rolling avg / rank** | SQL window functions (`LAG`, `AVG() OVER (ROWS BETWEEN ...)`, `RANK`) over per-session volume | Rolling average window (3 sessions) is fixed, not adaptive to training frequency |

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
