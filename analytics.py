"""
analytics.py
This is the core "data analysis" layer - it turns raw sets/workouts/exercises
rows into the same kind of derived metrics a business analyst produces from
transactional data: aggregates, trends, and flags worth acting on.

Techniques used:
- Pandas groupby/aggregation (volume, best-set-per-session)
- Estimated 1-rep-max via the Epley formula (a standard strength metric)
- NumPy linear regression (polyfit) to quantify a trend, not just eyeball it
- Simple rule-based insight generation (plateau detection, muscle balance)
"""

import pandas as pd
import numpy as np
from db import get_sets_for_exercise, get_all_sets_with_details


def _sets_to_df(rows, columns):
    return pd.DataFrame(rows, columns=columns)


def estimated_1rm(weight: float, reps: int) -> float:
    """Epley formula: est. 1-rep max from a submaximal set."""
    return round(weight * (1 + reps / 30), 1)


def exercise_history_df(exercise_name: str) -> pd.DataFrame:
    rows = get_sets_for_exercise(exercise_name)
    df = _sets_to_df(rows, ["workout_date", "set_number", "weight", "reps"])
    if df.empty:
        return df
    df["workout_date"] = pd.to_datetime(df["workout_date"])
    df["est_1rm"] = df.apply(lambda r: estimated_1rm(r["weight"], r["reps"]), axis=1)
    return df


def best_set_over_time(exercise_name: str) -> pd.DataFrame:
    """Best estimated 1RM achieved per session (mirrors the 'Best Set' chart)."""
    df = exercise_history_df(exercise_name)
    if df.empty:
        return df
    return df.groupby("workout_date", as_index=False)["est_1rm"].max()


def volume_over_time(exercise_name: str) -> pd.DataFrame:
    """Total volume (weight x reps, summed across sets) per session."""
    df = exercise_history_df(exercise_name)
    if df.empty:
        return df
    df["volume"] = df["weight"] * df["reps"]
    return df.groupby("workout_date", as_index=False)["volume"].sum()


def progressive_overload_trend(exercise_name: str) -> dict:
    """
    Fits a linear trend line to best-set-per-session using numpy.polyfit.
    Returns the slope (lbs of est. 1RM gained per session) and a plain-English read.
    """
    df = best_set_over_time(exercise_name)
    if len(df) < 3:
        return {"slope": None, "message": "Not enough sessions yet to detect a trend."}

    x = np.arange(len(df))
    y = df["est_1rm"].values
    slope, intercept = np.polyfit(x, y, 1)

    if slope > 0.5:
        message = f"Trending up: est. 1RM is climbing ~{slope:.1f} lbs per session."
    elif slope < -0.5:
        message = f"Trending down: est. 1RM has dropped ~{abs(slope):.1f} lbs per session."
    else:
        message = "Flat: strength has plateaued over recent sessions."

    return {"slope": round(float(slope), 2), "message": message}


def detect_plateau(exercise_name: str, lookback_sessions: int = 4) -> bool:
    """True if no new best-set PR has been hit in the last N sessions."""
    df = best_set_over_time(exercise_name)
    if len(df) < lookback_sessions + 1:
        return False
    running_max = df["est_1rm"].cummax()
    recent = df.tail(lookback_sessions)
    recent_running_max = running_max.tail(lookback_sessions)
    return bool((recent["est_1rm"].values <= recent_running_max.values).all() and
                recent["est_1rm"].max() <= running_max.iloc[-lookback_sessions - 1])


def muscle_group_balance(days: int = 30) -> pd.DataFrame:
    """Total volume per muscle group in the trailing N days - flags imbalance
    (e.g. lots of push volume, almost no pull volume)."""
    rows = get_all_sets_with_details()
    df = _sets_to_df(rows, ["workout_date", "exercise", "muscle_group", "set_number", "weight", "reps"])
    if df.empty:
        return df
    df["workout_date"] = pd.to_datetime(df["workout_date"])
    df["volume"] = df["weight"] * df["reps"]
    cutoff = df["workout_date"].max() - pd.Timedelta(days=days)
    recent = df[df["workout_date"] >= cutoff]
    summary = recent.groupby("muscle_group", as_index=False)["volume"].sum()
    summary = summary.sort_values("volume", ascending=False)
    total = summary["volume"].sum()
    summary["pct_of_total"] = (summary["volume"] / total * 100).round(1)
    return summary


def personal_records(exercise_name: str) -> dict:
    df = exercise_history_df(exercise_name)
    if df.empty:
        return {}
    best_row = df.loc[df["est_1rm"].idxmax()]
    return {
        "date": best_row["workout_date"].date().isoformat(),
        "weight": best_row["weight"],
        "reps": int(best_row["reps"]),
        "est_1rm": best_row["est_1rm"],
    }
