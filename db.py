"""
db.py
Database access layer. Wraps raw SQL against a local SQLite file so the
rest of the app never writes ad-hoc queries. Demonstrates: table creation,
parameterized inserts, and multi-table JOINs.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "workouts.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Create tables if they don't exist yet."""
    with get_connection() as conn:
        with open(SCHEMA_PATH) as f:
            conn.executescript(f.read())


def add_exercise(name: str, muscle_group: str, is_niche: bool = False) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO exercises (name, muscle_group, is_niche) VALUES (?, ?, ?)",
            (name, muscle_group, int(is_niche)),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM exercises WHERE name = ?", (name,)).fetchone()
        return row[0]


def add_workout(workout_date: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO workouts (workout_date) VALUES (?)", (workout_date,)
        )
        conn.commit()
        return cur.lastrowid


def log_set(workout_id: int, exercise_id: int, set_number: int, weight: float, reps: int):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO sets (workout_id, exercise_id, set_number, weight, reps)
               VALUES (?, ?, ?, ?, ?)""",
            (workout_id, exercise_id, set_number, weight, reps),
        )
        conn.commit()


def get_all_exercises():
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, name, muscle_group, is_niche FROM exercises ORDER BY name"
        ).fetchall()


def get_sets_for_exercise(exercise_name: str):
    """JOIN sets -> workouts -> exercises to get a full history for one lift."""
    query = """
        SELECT w.workout_date, s.set_number, s.weight, s.reps
        FROM sets s
        JOIN workouts w ON s.workout_id = w.id
        JOIN exercises e ON s.exercise_id = e.id
        WHERE e.name = ?
        ORDER BY w.workout_date, s.set_number
    """
    with get_connection() as conn:
        return conn.execute(query, (exercise_name,)).fetchall()


def get_all_sets_with_details():
    """Full JOIN across all three tables - the base dataset analytics.py works from."""
    query = """
        SELECT w.workout_date, e.name AS exercise, e.muscle_group,
               s.set_number, s.weight, s.reps
        FROM sets s
        JOIN workouts w ON s.workout_id = w.id
        JOIN exercises e ON s.exercise_id = e.id
        ORDER BY w.workout_date
    """
    with get_connection() as conn:
        return conn.execute(query).fetchall()
