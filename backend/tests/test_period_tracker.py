"""
Unit and integration tests for backend/common/period_tracker.py.
Verifies period tracker business logic independently of Flask request contexts,
and tests the regression cases specified in the refactoring requirements.
"""

import os
import sys
import unittest
from datetime import date, datetime

# Ensure backend root is on sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from common.period_tracker import (
    calculate_intervals,
    validate_cycle_inputs,
    calculate_period_prediction,
    calculate_cycle_analytics_metrics,
    log_cycle,
    delete_user_cycle,
    update_cycle_clarification,
    recalculate_user_cycles,
    get_user_typical_cycle_lengths,
    normalize_gap_clarification,
    PHYSIOLOGICAL_CYCLE_MAX,
    STANDARD_CYCLE_BASELINE,
)
from db import execute_query, execute_write, init_test_database


class TestPeriodTrackerPureFunctions(unittest.TestCase):
    """Verifies period tracker functions that can be tested independently of Flask and the database."""

    def test_calculate_intervals_aug_sep_oct_dates(self):
        """
        Regression Case 1: Consecutive recorded starts on August 10, September 9,
        and October 24, 2026 must produce intervals of 30 days and 45 days.
        """
        # Test with string dates
        date_strs = ["2026-08-10", "2026-09-09", "2026-10-24"]
        intervals = calculate_intervals(date_strs)
        self.assertEqual(intervals, [30, 45])

        # Test with date objects
        date_objs = [date(2026, 8, 10), date(2026, 9, 9), date(2026, 10, 24)]
        intervals_objs = calculate_intervals(date_objs)
        self.assertEqual(intervals_objs, [30, 45])

        # Test with datetime objects
        dt_objs = [datetime(2026, 8, 10), datetime(2026, 9, 9), datetime(2026, 10, 24)]
        self.assertEqual(calculate_intervals(dt_objs), [30, 45])

    def test_calculate_intervals_sorting_and_edges(self):
        """Interval calculation should sort unordered dates and handle short/empty input."""
        unordered = ["2026-10-24", "2026-08-10", "2026-09-09"]
        self.assertEqual(calculate_intervals(unordered), [30, 45])
        self.assertEqual(calculate_intervals([]), [])
        self.assertEqual(calculate_intervals(["2026-08-10"]), [])

    def test_validate_cycle_inputs_format_and_bounds(self):
        """Validates date formats, required fields, and start/end relationships."""
        # Missing start date
        _, _, err, code = validate_cycle_inputs(None)
        self.assertEqual(code, 400)
        self.assertIn("Missing required field", err)

        # Malformed start date
        _, _, err, code = validate_cycle_inputs("not-a-date")
        self.assertEqual(code, 400)
        self.assertIn("YYYY-MM-DD", err)

        # End date before start date
        _, _, err, code = validate_cycle_inputs("2026-08-10", "2026-08-05")
        self.assertEqual(code, 400)
        self.assertIn("earlier than start date", err)

        # Valid inputs
        s_date, e_date, err, code = validate_cycle_inputs("2026-08-10", "2026-08-15")
        self.assertIsNone(err)
        self.assertIsNone(code)
        self.assertEqual(s_date, date(2026, 8, 10))
        self.assertEqual(e_date, date(2026, 8, 15))

    def test_calculate_period_prediction_empty_and_baseline(self):
        """Empty cycle history returns baseline prediction without marking irregular."""
        pred = calculate_period_prediction([], has_pcos=False)
        self.assertEqual(pred["history_count"], 0)
        self.assertEqual(pred["average_cycle_length"], STANDARD_CYCLE_BASELINE)
        self.assertFalse(pred["irregular"])
        self.assertEqual(pred["tracking_status"], "insufficient_history")
        self.assertFalse(pred["pcos_mode"])

    def test_calculate_period_prediction_pcos_regular_not_forced_irregular(self):
        """PCOS profile preserves pcos_mode=True but does NOT force irregular=True on regular cycles."""
        cycles = [
            {"start_date": "2026-06-24", "cycle_length": None, "period_length": 5, "gap_type": None},
            {"start_date": "2026-05-27", "cycle_length": 28, "period_length": 5, "gap_type": None},
            {"start_date": "2026-04-29", "cycle_length": 28, "period_length": 5, "gap_type": None},
            {"start_date": "2026-04-01", "cycle_length": 28, "period_length": 5, "gap_type": None},
        ]
        pred = calculate_period_prediction(cycles, has_pcos=True)
        self.assertTrue(pred["pcos_mode"])
        self.assertFalse(pred["irregular"], "PCOS mode must not force irregular=True when intervals are regular")
        self.assertEqual(pred["average_cycle_length"], 28)
        self.assertEqual(pred["tracking_status"], "complete")

    def test_calculate_cycle_analytics_metrics_pure(self):
        """Analytics metrics calculation excludes unclarified gaps from cycle average."""
        cycles_db = [
            {"cycle_length": 28, "period_length": 5, "irregular": False, "gap_type": None},
            {"cycle_length": 30, "period_length": 5, "irregular": False, "gap_type": None},
            {"cycle_length": 75, "period_length": 5, "irregular": False, "gap_type": "unclarified_gap"},
            {"cycle_length": None, "period_length": 5, "irregular": False, "gap_type": None},
        ]
        metrics = calculate_cycle_analytics_metrics(cycles_db)
        self.assertEqual(metrics["average_cycle_length"], 29.0)
        self.assertEqual(metrics["average_period_length"], 5.0)
        self.assertEqual(metrics["irregular_cycles_count"], 0)

    def test_distinguish_all_gap_types_and_intervals(self):
        """
        Milestone 1 requirement:
        Distinguish confirmed usable intervals, unclarified gaps, forgotten entries,
        missed periods, and confirmed genuine long cycles.
        """
        # 1. Normal usable interval (28 days)
        cycles_regular = [
            {"start_date": "2026-05-29", "cycle_length": None, "period_length": 5, "gap_type": None},
            {"start_date": "2026-05-01", "cycle_length": 28, "period_length": 5, "gap_type": None},
            {"start_date": "2026-04-03", "cycle_length": 28, "period_length": 5, "gap_type": None},
        ]
        pred_reg = calculate_period_prediction(cycles_regular)
        self.assertEqual(pred_reg["usable_intervals"], [28, 28])
        self.assertEqual(len(pred_reg["excluded_intervals"]), 0)
        self.assertFalse(pred_reg["has_unresolved_gaps"])
        self.assertIsNone(pred_reg["clarification_prompt"])

        # 2. Unclarified long gap (70 days)
        cycles_unclarified = [
            {"start_date": "2026-07-10", "cycle_length": None, "period_length": 5, "gap_type": None},
            {"start_date": "2026-05-01", "cycle_length": 70, "period_length": 5, "gap_type": "unclarified_gap"},
            {"start_date": "2026-04-03", "cycle_length": 28, "period_length": 5, "gap_type": None},
        ]
        pred_unc = calculate_period_prediction(cycles_unclarified)
        self.assertEqual(pred_unc["usable_intervals"], [28])
        self.assertEqual(len(pred_unc["excluded_intervals"]), 1)
        self.assertTrue(pred_unc["excluded_intervals"][0]["requires_clarification"])
        self.assertTrue(pred_unc["has_unresolved_gaps"])
        self.assertIsNotNone(pred_unc["clarification_prompt"])
        self.assertEqual(pred_unc["average_cycle_length"], 28)
        self.assertFalse(pred_unc["irregular"], "Unclarified gap must not mark user irregular")

        # 3. User-confirmed forgotten app entry (70 days)
        cycles_forgotten = [
            {"start_date": "2026-07-10", "cycle_length": None, "period_length": 5, "gap_type": None},
            {"start_date": "2026-05-01", "cycle_length": 70, "period_length": 5, "gap_type": "forgotten_entry"},
            {"start_date": "2026-04-03", "cycle_length": 28, "period_length": 5, "gap_type": None},
        ]
        pred_forg = calculate_period_prediction(cycles_forgotten)
        self.assertEqual(pred_forg["usable_intervals"], [28])
        self.assertEqual(len(pred_forg["excluded_intervals"]), 1)
        self.assertFalse(pred_forg["excluded_intervals"][0]["requires_clarification"])
        self.assertFalse(pred_forg["has_unresolved_gaps"])
        self.assertEqual(pred_forg["average_cycle_length"], 28)
        self.assertFalse(pred_forg["irregular"], "Forgotten entry must not mark user irregular")

        # 4. User-confirmed missed period (56 days)
        cycles_missed = [
            {"start_date": "2026-06-26", "cycle_length": None, "period_length": 5, "gap_type": None},
            {"start_date": "2026-05-01", "cycle_length": 56, "period_length": 5, "gap_type": "missed_period"},
            {"start_date": "2026-04-03", "cycle_length": 28, "period_length": 5, "gap_type": None},
        ]
        pred_miss = calculate_period_prediction(cycles_missed)
        self.assertEqual(pred_miss["usable_intervals"], [28])
        self.assertEqual(len(pred_miss["excluded_intervals"]), 1)
        self.assertFalse(pred_miss["excluded_intervals"][0]["requires_clarification"])
        self.assertFalse(pred_miss["has_unresolved_gaps"])
        self.assertEqual(pred_miss["average_cycle_length"], 28)
        self.assertFalse(pred_miss["irregular"])

        # 5. User-confirmed genuine long cycle (50 days)
        cycles_long = [
            {"start_date": "2026-06-20", "cycle_length": None, "period_length": 5, "gap_type": None},
            {"start_date": "2026-05-01", "cycle_length": 50, "period_length": 5, "gap_type": "confirmed_long_cycle"},
            {"start_date": "2026-04-03", "cycle_length": 28, "period_length": 5, "gap_type": None},
        ]
        pred_long = calculate_period_prediction(cycles_long)
        self.assertIn(50, pred_long["usable_intervals"])
        self.assertEqual(len(pred_long["excluded_intervals"]), 0)
        self.assertTrue(pred_long["irregular"], "Confirmed long cycle must be observed as irregular")
        self.assertEqual(pred_long["regularity_assessment"], "irregular")

    def test_history_quality_and_regularity_classification_rules(self):
        """
        Milestone 1 requirement:
        Define clear rules for when there is insufficient evidence to classify regularity
        or produce a personalized estimate.
        """
        # 0 cycles -> insufficient history, cannot classify regularity
        pred0 = calculate_period_prediction([])
        self.assertEqual(pred0["history_quality"], "insufficient")
        self.assertFalse(pred0["is_personalized"])
        self.assertFalse(pred0["can_classify_regularity"])
        self.assertEqual(pred0["regularity_assessment"], "insufficient_data")
        self.assertEqual(pred0["prediction_confidence"], "low")

        # 1 cycle -> insufficient completed intervals
        pred1 = calculate_period_prediction([
            {"start_date": "2026-05-01", "cycle_length": None, "period_length": 5, "gap_type": None}
        ])
        self.assertEqual(pred1["history_quality"], "insufficient")
        self.assertFalse(pred1["is_personalized"])
        self.assertFalse(pred1["can_classify_regularity"])
        self.assertEqual(pred1["regularity_assessment"], "insufficient_data")
        self.assertEqual(pred1["prediction_confidence"], "low")

        # 2 cycles (1 completed interval) -> limited history, cannot yet classify regularity
        pred2 = calculate_period_prediction([
            {"start_date": "2026-05-29", "cycle_length": None, "period_length": 5, "gap_type": None},
            {"start_date": "2026-05-01", "cycle_length": 28, "period_length": 5, "gap_type": None}
        ])
        self.assertEqual(pred2["history_quality"], "limited")
        self.assertTrue(pred2["is_personalized"])
        self.assertFalse(pred2["can_classify_regularity"])
        self.assertEqual(pred2["regularity_assessment"], "insufficient_data")
        self.assertEqual(pred2["prediction_confidence"], "moderate")

        # 4 cycles (3 regular intervals) -> established history, can classify regularity
        pred4 = calculate_period_prediction([
            {"start_date": "2026-07-24", "cycle_length": None, "period_length": 5, "gap_type": None},
            {"start_date": "2026-06-26", "cycle_length": 28, "period_length": 5, "gap_type": None},
            {"start_date": "2026-05-29", "cycle_length": 28, "period_length": 5, "gap_type": None},
            {"start_date": "2026-05-01", "cycle_length": 28, "period_length": 5, "gap_type": None}
        ])
        self.assertEqual(pred4["history_quality"], "established")
        self.assertTrue(pred4["is_personalized"])
        self.assertTrue(pred4["can_classify_regularity"])
        self.assertEqual(pred4["regularity_assessment"], "regular")
        self.assertEqual(pred4["prediction_confidence"], "high")


class TestPeriodTrackerDatabaseIntegration(unittest.TestCase):
    """Tests cycle logging, deletion, and recalculation against the test database."""

    @classmethod
    def setUpClass(cls):
        init_test_database()
        cls.user_id = "usr_tracker_test"
        cls._cleanup()
        execute_write(
            """
            INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos)
            VALUES (:uid, 'Tracker User', 'tracker_test@ovacare.app', 'pwd', 26, 'Moderate', FALSE)
            """,
            {"uid": cls.user_id}
        )

    @classmethod
    def tearDownClass(cls):
        cls._cleanup()

    @classmethod
    def _cleanup(cls):
        execute_write("DELETE FROM cycles WHERE user_id = :uid", {"uid": cls.user_id})
        execute_write("DELETE FROM users WHERE user_id = :uid", {"uid": cls.user_id})

    def setUp(self):
        execute_write("DELETE FROM cycles WHERE user_id = :uid", {"uid": self.user_id})

    def test_aug_sep_oct_consecutive_intervals_and_ongoing_latest(self):
        """
        Regression Case 1 & 2:
        - Consecutive recorded starts on August 10, September 9, and October 24, 2026,
          producing intervals of 30 days and 45 days.
        - The most recent cycle having no completed interval yet (cycle_length is None).
        """
        cid1, err1, code1 = log_cycle(self.user_id, "2026-08-10", "2026-08-15")
        self.assertEqual(code1, 201)

        cid2, err2, code2 = log_cycle(self.user_id, "2026-09-09", "2026-09-14")
        self.assertEqual(code2, 201)

        cid3, err3, code3 = log_cycle(self.user_id, "2026-10-24", "2026-10-29")
        self.assertEqual(code3, 201)

        cycles = execute_query(
            "SELECT cycle_id, start_date, cycle_length, irregular, gap_type FROM cycles WHERE user_id = :uid ORDER BY start_date ASC",
            {"uid": self.user_id}
        )
        self.assertEqual(len(cycles), 3)

        # August 10 to September 9 = 30 days
        self.assertEqual(str(cycles[0]["start_date"])[:10], "2026-08-10")
        self.assertEqual(cycles[0]["cycle_length"], 30)

        # September 9 to October 24 = 45 days
        self.assertEqual(str(cycles[1]["start_date"])[:10], "2026-09-09")
        self.assertEqual(cycles[1]["cycle_length"], 45)

        # Most recent cycle (October 24) must have no completed interval yet
        self.assertEqual(str(cycles[2]["start_date"])[:10], "2026-10-24")
        self.assertIsNone(cycles[2]["cycle_length"])
        self.assertFalse(cycles[2]["irregular"])

    def test_duplicate_start_date_rejection_in_log_cycle(self):
        """Regression Case 5: Duplicate cycle start dates must return 409 Conflict."""
        _, _, code1 = log_cycle(self.user_id, "2026-08-10")
        self.assertEqual(code1, 201)

        _, err2, code2 = log_cycle(self.user_id, "2026-08-10")
        self.assertEqual(code2, 409)
        self.assertIn("already exists", err2)

    def test_delete_cycle_and_recalculate(self):
        """Deleting an intervening cycle recalculates surrounding intervals."""
        log_cycle(self.user_id, "2026-01-01")
        cid2, _, _ = log_cycle(self.user_id, "2026-01-29")
        log_cycle(self.user_id, "2026-02-26")

        # Delete the middle cycle
        success, msg, code = delete_user_cycle(self.user_id, cid2)
        self.assertTrue(success)
        self.assertEqual(code, 200)

        remaining = execute_query(
            "SELECT cycle_id, start_date, cycle_length FROM cycles WHERE user_id = :uid ORDER BY start_date ASC",
            {"uid": self.user_id}
        )
        self.assertEqual(len(remaining), 2)
        # Jan 1 to Feb 26 is 56 days
        self.assertEqual(remaining[0]["cycle_length"], 56)
        # Most recent is ongoing
        self.assertIsNone(remaining[1]["cycle_length"])

    def test_update_cycle_clarification_integration(self):
        """
        Milestone 1 requirement:
        Verify updating gap clarification on an existing cycle (e.g. to forgotten_entry),
        recalculating cycles, and enforcing user ownership security.
        """
        # User logs: Cycle 1 (May 1), Cycle 2 (July 10) -> 70-day gap initially unclarified
        cid1, _, code1 = log_cycle(self.user_id, "2026-05-01")
        self.assertEqual(code1, 201)
        cid2, _, code2 = log_cycle(self.user_id, "2026-07-10")
        self.assertEqual(code2, 201)

        c1 = execute_query("SELECT gap_type, cycle_length, irregular FROM cycles WHERE cycle_id = :cid", {"cid": cid1})[0]
        self.assertEqual(c1["gap_type"], "unclarified_gap")
        self.assertEqual(c1["cycle_length"], 70)
        self.assertFalse(c1["irregular"], "Unclarified gap must not be marked irregular")

        # Clarify gap as forgotten entry
        success, msg, code = update_cycle_clarification(self.user_id, cid1, "forgotten_entry")
        self.assertTrue(success)
        self.assertEqual(code, 200)

        c1_updated = execute_query("SELECT gap_type, cycle_length, irregular FROM cycles WHERE cycle_id = :cid", {"cid": cid1})[0]
        self.assertEqual(c1_updated["gap_type"], "forgotten_entry")
        self.assertFalse(c1_updated["irregular"])

        # Attempt to clarify as another user -> must be rejected (403 Forbidden)
        success_other, msg_other, code_other = update_cycle_clarification("usr_other_intruder", cid1, "confirmed_long_cycle")
        self.assertFalse(success_other)
        self.assertEqual(code_other, 403)

        # Attempt to provide invalid clarification -> must return 400
        success_inv, msg_inv, code_inv = update_cycle_clarification(self.user_id, cid1, "invalid_choice")
        self.assertFalse(success_inv)
        self.assertEqual(code_inv, 400)

    def test_clarification_transition_lifecycle(self):
        """
        Review verification:
        Confirm that changing a clarification dynamically updates interval classification,
        database flags, and recalculates dependent predictions and analytics consistently
        across unclarified_gap, confirmed_long_cycle, missed_period, and forgotten_entry.
        """
        cid1, _, _ = log_cycle(self.user_id, "2026-01-01")
        cid2, _, _ = log_cycle(self.user_id, "2026-03-12") # 70d gap
        cid3, _, _ = log_cycle(self.user_id, "2026-04-09") # 28d

        # 1. Initially unclarified
        c1 = execute_query("SELECT gap_type, irregular FROM cycles WHERE cycle_id = :cid", {"cid": cid1})[0]
        self.assertEqual(c1["gap_type"], "unclarified_gap")
        self.assertFalse(c1["irregular"])

        cycles = execute_query("SELECT * FROM cycles WHERE user_id = :uid ORDER BY start_date DESC", {"uid": self.user_id})
        pred1 = calculate_period_prediction(cycles)
        self.assertTrue(pred1["has_unresolved_gaps"])
        self.assertFalse(pred1["irregular"])
        self.assertEqual(pred1["usable_intervals"], [28])
        self.assertEqual(len(pred1["excluded_intervals"]), 1)
        self.assertTrue(pred1["excluded_intervals"][0]["requires_clarification"])

        # 2. Transition to confirmed_long_cycle
        update_cycle_clarification(self.user_id, cid1, "confirmed_long_cycle")
        c1 = execute_query("SELECT gap_type, irregular FROM cycles WHERE cycle_id = :cid", {"cid": cid1})[0]
        self.assertEqual(c1["gap_type"], "confirmed_long_cycle")
        self.assertTrue(c1["irregular"])

        cycles = execute_query("SELECT * FROM cycles WHERE user_id = :uid ORDER BY start_date DESC", {"uid": self.user_id})
        pred2 = calculate_period_prediction(cycles)
        self.assertFalse(pred2["has_unresolved_gaps"])
        self.assertTrue(pred2["irregular"])
        self.assertEqual(pred2["regularity_assessment"], "irregular")
        self.assertIn(70, pred2["usable_intervals"])
        self.assertEqual(len(pred2["excluded_intervals"]), 0)

        # 3. Transition to missed_period
        update_cycle_clarification(self.user_id, cid1, "missed_period")
        c1 = execute_query("SELECT gap_type, irregular FROM cycles WHERE cycle_id = :cid", {"cid": cid1})[0]
        self.assertEqual(c1["gap_type"], "missed_period")
        self.assertFalse(c1["irregular"])

        cycles = execute_query("SELECT * FROM cycles WHERE user_id = :uid ORDER BY start_date DESC", {"uid": self.user_id})
        pred3 = calculate_period_prediction(cycles)
        self.assertFalse(pred3["has_unresolved_gaps"])
        self.assertFalse(pred3["irregular"])
        self.assertEqual(pred3["usable_intervals"], [28])
        self.assertEqual(len(pred3["excluded_intervals"]), 1)
        self.assertEqual(pred3["excluded_intervals"][0]["gap_type"], "missed_period")
        self.assertFalse(pred3["excluded_intervals"][0]["requires_clarification"])

        # 4. Transition to forgotten_entry
        update_cycle_clarification(self.user_id, cid1, "forgotten_entry")
        c1 = execute_query("SELECT gap_type, irregular FROM cycles WHERE cycle_id = :cid", {"cid": cid1})[0]
        self.assertEqual(c1["gap_type"], "forgotten_entry")
        self.assertFalse(c1["irregular"])

        cycles = execute_query("SELECT * FROM cycles WHERE user_id = :uid ORDER BY start_date DESC", {"uid": self.user_id})
        pred4 = calculate_period_prediction(cycles)
        self.assertFalse(pred4["has_unresolved_gaps"])
        self.assertFalse(pred4["irregular"])
        self.assertEqual(pred4["usable_intervals"], [28])
        self.assertEqual(len(pred4["excluded_intervals"]), 1)
        self.assertEqual(pred4["excluded_intervals"][0]["gap_type"], "forgotten_entry")
        self.assertFalse(pred4["excluded_intervals"][0]["requires_clarification"])

        # 5. Transition back to unclarified_gap
        update_cycle_clarification(self.user_id, cid1, "unclarified_gap")
        c1 = execute_query("SELECT gap_type, irregular FROM cycles WHERE cycle_id = :cid", {"cid": cid1})[0]
        self.assertEqual(c1["gap_type"], "unclarified_gap")
        self.assertFalse(c1["irregular"])

        cycles = execute_query("SELECT * FROM cycles WHERE user_id = :uid ORDER BY start_date DESC", {"uid": self.user_id})
        pred5 = calculate_period_prediction(cycles)
        self.assertTrue(pred5["has_unresolved_gaps"])
        self.assertFalse(pred5["irregular"])
        self.assertTrue(pred5["excluded_intervals"][0]["requires_clarification"])


if __name__ == "__main__":
    unittest.main()

