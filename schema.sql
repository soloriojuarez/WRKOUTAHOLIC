-- schema.sql
-- Relational schema for the workout analytics tracker.
-- Three tables: exercises (a catalog, including niche lifts), workouts
-- (one row per training session), and sets (one row per set performed,
-- linked to both a workout and an exercise).

CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    muscle_group TEXT NOT NULL,
    is_niche INTEGER NOT NULL DEFAULT 0  -- 1 = not typically found in mainstream apps
);

CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_date TEXT NOT NULL  -- ISO date, e.g. '2026-03-14'
);

CREATE TABLE IF NOT EXISTS sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    set_number INTEGER NOT NULL,
    weight REAL NOT NULL,   -- lbs
    reps INTEGER NOT NULL,
    FOREIGN KEY (workout_id) REFERENCES workouts (id),
    FOREIGN KEY (exercise_id) REFERENCES exercises (id)
);
