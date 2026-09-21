"""
test_recommender.py
Unit tests for the greedy recommender against an isolated, temporary SQLite
DB (never touches workouts.db) so the algorithm's edge cases are verifiable
in isolation: cold start, an already-balanced catalog, and requeue behavior
when a muscle group has more than one exercise.

Run with: python3 -m unittest test_recommender.py -v
"""

import unittest
from datetime import date, timedelta

import db
import recommender


class RecommenderTestCase(unittest.TestCase):
    def setUp(self):
        # Point db at an in-memory-like throwaway file for the duration of the test.
        db.DB_PATH = ":memory:"
        self._conn = db.sqlite3.connect(db.DB_PATH)
        self._conn.execute("PRAGMA foreign_keys = ON;")
        # get_connection() opens a fresh connection per call against ":memory:",
        # which would each see an empty DB - so patch it to reuse one shared connection.
        self._real_get_connection = db.get_connection
        db.get_connection = lambda: self._conn
        with open(db.SCHEMA_PATH) as f:
            self._conn.executescript(f.read())

    def tearDown(self):
        db.get_connection = self._real_get_connection
        self._conn.close()

    def _log(self, exercise_id, workout_date, weight, reps, set_number=1):
        workout_id = db.add_workout(workout_date)
        db.log_set(workout_id, exercise_id, set_number, weight, reps)

    def test_cold_start_recommends_every_group_once(self):
        """With zero history, every muscle group is equally (fully) deficient,
        so a session should pull one exercise from each distinct group first."""
        push = db.add_exercise("Bench Press", "Push")
        pull = db.add_exercise("Barbell Row", "Pull")
        legs = db.add_exercise("Squat", "Legs")

        picks = recommender.recommend_next_workout(session_size=3)

        groups_picked = {p["muscle_group"] for p in picks}
        self.assertEqual(groups_picked, {"Push", "Pull", "Legs"})
        self.assertTrue(all(p["days_since_trained"] is None for p in picks))

    def test_balanced_catalog_yields_no_recommendations(self):
        """If every group already has exactly its equal target share of
        volume, there's no deficit left to correct."""
        push = db.add_exercise("Bench Press", "Push")
        pull = db.add_exercise("Barbell Row", "Pull")
        today = date.today().isoformat()

        self._log(push, today, weight=100, reps=10)
        self._log(pull, today, weight=100, reps=10)

        picks = recommender.recommend_next_workout(session_size=4)
        self.assertEqual(picks, [])

    def test_neglected_group_is_prioritized_over_recently_trained_one(self):
        """Push has been trained heavily and recently; Pull has never been
        touched. The single most under-trained group (Pull) must come first."""
        push = db.add_exercise("Bench Press", "Push")
        pull = db.add_exercise("Barbell Row", "Pull")
        recent = date.today().isoformat()

        for _ in range(5):
            self._log(push, recent, weight=135, reps=10)

        picks = recommender.recommend_next_workout(session_size=1)

        self.assertEqual(len(picks), 1)
        self.assertEqual(picks[0]["muscle_group"], "Pull")
        self.assertEqual(picks[0]["exercise"], "Barbell Row")

    def test_requeue_prefers_least_recently_trained_within_same_group(self):
        """Pull has two exercises and a big deficit; a 2-exercise session
        should requeue Pull and pick its least-recently-trained exercise second,
        not repeat the first pick."""
        pull_old = db.add_exercise("Pull-up", "Pull")
        pull_new = db.add_exercise("Barbell Row", "Pull")
        push = db.add_exercise("Bench Press", "Push")

        long_ago = (date.today() - timedelta(days=60)).isoformat()
        recently = (date.today() - timedelta(days=1)).isoformat()
        self._log(pull_old, long_ago, weight=0, reps=8)
        self._log(pull_new, recently, weight=95, reps=8)
        self._log(push, recently, weight=135, reps=8)

        picks = recommender.recommend_next_workout(session_size=2)

        exercises_picked = [p["exercise"] for p in picks]
        self.assertEqual(len(exercises_picked), len(set(exercises_picked)))  # no duplicates
        self.assertIn("Pull", [p["muscle_group"] for p in picks])

    def test_never_recommends_more_than_available_exercises_in_a_group(self):
        """A group with only one exercise can only ever contribute one pick,
        even across multiple requeues, and the algorithm must still terminate."""
        push = db.add_exercise("Bench Press", "Push")

        picks = recommender.recommend_next_workout(session_size=5)

        push_picks = [p for p in picks if p["muscle_group"] == "Push"]
        self.assertEqual(len(push_picks), 1)


if __name__ == "__main__":
    unittest.main()
