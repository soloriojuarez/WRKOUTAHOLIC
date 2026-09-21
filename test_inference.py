"""
test_inference.py
Unit tests for the statistical inference layer, against an isolated
temporary SQLite DB (same pattern as test_recommender.py). Uses fixed,
hand-picked data (verified independently against scipy.stats before being
hardcoded here) rather than randomized data, so significance outcomes are
deterministic instead of occasionally flaky.

Run with: python3 -m unittest test_inference.py -v
"""

import unittest
from datetime import date, timedelta

import db
import inference


class InferenceTestCase(unittest.TestCase):
    def setUp(self):
        db.DB_PATH = ":memory:"
        self._conn = db.sqlite3.connect(db.DB_PATH)
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._real_get_connection = db.get_connection
        db.get_connection = lambda: self._conn
        with open(db.SCHEMA_PATH) as f:
            self._conn.executescript(f.read())
        self.exercise_id = db.add_exercise("Bench Press", "Push")

    def tearDown(self):
        db.get_connection = self._real_get_connection
        self._conn.close()

    def _log(self, day_offset, weight, reps):
        workout_date = (date(2026, 1, 1) + timedelta(days=day_offset * 2)).isoformat()
        workout_id = db.add_workout(workout_date)
        db.log_set(workout_id, self.exercise_id, 1, weight, reps)

    # ---- trend_significance ----

    def test_trend_insufficient_sessions_returns_none(self):
        self._log(0, 100, 5)
        self._log(1, 105, 5)
        result = inference.trend_significance("Bench Press")
        self.assertIsNone(result["significant"])

    def test_trend_clear_linear_increase_is_significant(self):
        for i, weight in enumerate([100, 105, 110, 115, 120, 125]):
            self._log(i, weight, 5)
        result = inference.trend_significance("Bench Press")
        self.assertTrue(result["significant"])
        # est_1rm = weight * (1 + reps/30); with reps fixed at 5, a weight step
        # of 5/session scales to an est_1rm step of ~5 * (1 + 5/30) = 5.8333
        # (estimated_1rm() rounds to 1 decimal, so allow a small tolerance).
        self.assertAlmostEqual(result["slope"], 5.8333, delta=0.02)
        self.assertLess(result["p_value"], 0.05)

    def test_trend_noisy_flat_data_is_not_significant(self):
        for i, weight in enumerate([100, 130, 90, 120, 95, 115]):
            self._log(i, weight, 5)
        result = inference.trend_significance("Bench Press")
        self.assertFalse(result["significant"])
        self.assertGreaterEqual(result["p_value"], 0.05)

    # ---- rep_range_comparison ----

    def test_rep_range_insufficient_data_returns_none(self):
        self._log(0, 200, 5)  # only one low-rep set, no high-rep sets
        result = inference.rep_range_comparison("Bench Press")
        self.assertIsNone(result["significant"])

    def test_rep_range_clear_separation_is_significant(self):
        for i, (w, r) in enumerate([(200, 5), (202, 5), (198, 6)]):
            self._log(i, w, r)
        for i, (w, r) in enumerate([(100, 10), (102, 8), (98, 9)], start=10):
            self._log(i, w, r)

        result = inference.rep_range_comparison("Bench Press")
        self.assertTrue(result["significant"])
        self.assertLess(result["p_value"], 0.05)
        self.assertGreater(result["mean_est_1rm_low_rep"], result["mean_est_1rm_high_rep"])

    def test_rep_range_overlapping_data_is_not_significant(self):
        for i, (w, r) in enumerate([(100, 5), (110, 6), (90, 5)]):
            self._log(i, w, r)
        for i, (w, r) in enumerate([(90, 9), (105, 8), (95, 10)], start=10):
            self._log(i, w, r)

        result = inference.rep_range_comparison("Bench Press")
        self.assertFalse(result["significant"])
        self.assertGreaterEqual(result["p_value"], 0.05)


if __name__ == "__main__":
    unittest.main()
