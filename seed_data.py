"""
seed_data.py
Populates the database with ~3 months of realistic, randomized workout
history so the dashboard has something meaningful to show immediately.
Includes both standard lifts and niche exercises that mainstream apps
(e.g. Strong) typically don't have in their default library.
"""

import random
from datetime import date, timedelta
import db

random.seed(42)

STANDARD_EXERCISES = [
    ("Squat", "Legs", False),
    ("Bench Press", "Push", False),
    ("Deadlift", "Pull", False),
    ("Overhead Press", "Push", False),
    ("Barbell Row", "Pull", False),
    ("Pull-up", "Pull", False),
]

NICHE_EXERCISES = [
    ("Jefferson Curl", "Posterior Chain", True),
    ("Sissy Squat", "Legs", True),
    ("Reverse Nordic Curl", "Legs", True),
    ("Copenhagen Plank", "Core/Adductors", True),
    ("Zercher Squat", "Legs", True),
    ("Landmine Press", "Push", True),
    ("Tibialis Raise", "Legs", True),
    ("Scapular Pull-up", "Pull", True),
    ("Cossack Squat", "Legs", True),
]

ALL_EXERCISES = STANDARD_EXERCISES + NICHE_EXERCISES

# Rough realistic starting weight ranges (lbs) per exercise
START_WEIGHT = {
    "Squat": 135, "Bench Press": 115, "Deadlift": 155, "Overhead Press": 65,
    "Barbell Row": 95, "Pull-up": 0,  # bodyweight
    "Jefferson Curl": 45, "Sissy Squat": 0, "Reverse Nordic Curl": 0,
    "Copenhagen Plank": 0, "Zercher Squat": 95, "Landmine Press": 35,
    "Tibialis Raise": 20, "Scapular Pull-up": 0, "Cossack Squat": 25,
}


def build():
    db.init_db()

    exercise_ids = {}
    for name, group, niche in ALL_EXERCISES:
        exercise_ids[name] = db.add_exercise(name, group, niche)

    start_date = date(2026, 3, 1)
    end_date = date(2026, 5, 31)

    current_weight = dict(START_WEIGHT)
    day = start_date
    session_count = 0

    while day <= end_date:
        # Train roughly 3-4 days a week
        if day.weekday() in (0, 1, 3, 5):  # Mon, Tue, Thu, Sat
            workout_id = db.add_workout(day.isoformat())
            session_count += 1

            # Pick 3-4 exercises for this session
            todays_lifts = random.sample(list(current_weight.keys()), k=4)

            for ex_name in todays_lifts:
                exercise_id = exercise_ids[ex_name]

                # Slow upward drift with noise, occasional deload dip
                drift = random.uniform(-2, 3)
                if random.random() < 0.08:  # occasional deload/off day
                    drift -= random.uniform(5, 10)
                current_weight[ex_name] = max(0, current_weight[ex_name] + drift)

                num_sets = random.choice([3, 4])
                for set_num in range(1, num_sets + 1):
                    weight = round(max(0, current_weight[ex_name] + random.uniform(-5, 5)), 1)
                    reps = random.choice([5, 6, 8, 8, 10])
                    db.log_set(workout_id, exercise_id, set_num, weight, reps)

        day += timedelta(days=1)

    print(f"Seeded {session_count} workout sessions across {len(ALL_EXERCISES)} exercises.")


if __name__ == "__main__":
    build()
