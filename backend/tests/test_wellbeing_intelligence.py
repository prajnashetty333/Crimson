"""
Unit and Integration Tests for OvaCare AI Wellbeing Intelligence Engine.

Verifies:
1. Empty history (0 cycles, 0 logs)
2. Insufficient history (single cycle, insufficient logged days)
3. Positive recurring patterns (premenstrual fatigue across 3 cycles, cramps across 2 cycles)
4. Non-recurring patterns (isolated occurrence failing 66% threshold)
5. Missing metrics vs explicit absence (unrecorded fields are not treated as symptom-free)
6. Unreliable cycle windows (unclarified gaps >45d, erratic cycle lengths)
7. Non-causal, non-diagnostic wording and transparent evidence denominators
8. Cross-user data isolation in database queries
"""

import os
import sys
import unittest
from datetime import date, timedelta

# Ensure backend root is on sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from common.wellbeing_tracker import (
    assign_logs_to_cycles,
    classify_log_phase_window,
    evaluate_cycle_window_metric,
    analyze_user_wellbeing_patterns,
    get_user_wellbeing_insights,
    DEFAULT_WELLBEING_CONFIG,
)
from db import execute_write, execute_query, init_test_database


class TestWellbeingIntelligencePureFunctions(unittest.TestCase):
    """Verifies deterministic pattern detection logic independently of database."""

    def test_empty_history(self):
        """0 cycles and 0 logs returns insufficient_data with clear guidance."""
        res = analyze_user_wellbeing_patterns([], [])
        self.assertEqual(res["status"], "insufficient_data")
        self.assertEqual(res["cycles_evaluated_count"], 0)
        self.assertEqual(res["total_wellness_logs"], 0)
        self.assertEqual(len(res["patterns"]), 0)
        self.assertTrue(len(res["insufficient_data_reasons"]) > 0)

    def test_single_cycle_insufficient_for_recurring_claim(self):
        """1 cycle with premenstrual fatigue cannot claim a recurring pattern."""
        cycles = [
            {"cycle_id": "c1", "start_date": "2026-05-01", "cycle_length": 28, "period_length": 5, "gap_type": "normal"},
            {"cycle_id": "c2", "start_date": "2026-05-29", "cycle_length": None, "period_length": 5, "gap_type": "normal"}
        ]
        # Logs on premenstrual days of Cycle 1 (e.g. May 24, 25, 26)
        logs = [
            {"date": "2026-05-24", "fatigue": "Moderate", "mood": "Tired", "stress": "Medium", "sleep_hours": 7.0},
            {"date": "2026-05-25", "fatigue": "Severe", "mood": "Tired", "stress": "High", "sleep_hours": 6.0},
            {"date": "2026-05-26", "fatigue": "Moderate", "mood": "Calm", "stress": "Low", "sleep_hours": 7.5},
        ]
        res = analyze_user_wellbeing_patterns(cycles, logs)
        energy_pattern = next((p for p in res["patterns"] if p["pattern_id"] == "premenstrual_lower_energy"), None)
        self.assertIsNotNone(energy_pattern)
        self.assertEqual(energy_pattern["evidence_status"], "insufficient_data")
        self.assertFalse(energy_pattern["is_recurring"])
        self.assertIn("At least 2 distinct cycles", energy_pattern["status_reason"])
        self.assertEqual(energy_pattern["cycles_observed"], 1)
        self.assertEqual(energy_pattern["total_cycles_evaluated"], 1)

    def test_recurring_premenstrual_fatigue_across_three_cycles(self):
        """
        User logs fatigue on premenstrual days across 3 consecutive cycles.
        Must generate a supported recurring pattern with exact evidence denominators.
        """
        cycles = [
            {"cycle_id": "c1", "start_date": "2026-01-01", "cycle_length": 28, "period_length": 5, "gap_type": "normal"},
            {"cycle_id": "c2", "start_date": "2026-01-29", "cycle_length": 28, "period_length": 5, "gap_type": "normal"},
            {"cycle_id": "c3", "start_date": "2026-02-26", "cycle_length": 28, "period_length": 5, "gap_type": "normal"},
            {"cycle_id": "c4", "start_date": "2026-03-26", "cycle_length": None, "period_length": 5, "gap_type": "normal"}
        ]
        logs = [
            # Cycle 1 premenstrual: Jan 25, Jan 26 (C2 starts Jan 29)
            {"date": "2026-01-25", "fatigue": "Moderate", "mood": "Tired", "stress": "Low", "sleep_hours": 7.0},
            {"date": "2026-01-26", "fatigue": "Severe", "mood": "Calm", "stress": "Medium", "sleep_hours": 6.5},
            # Cycle 2 premenstrual: Feb 22, Feb 23 (C3 starts Feb 26)
            {"date": "2026-02-22", "fatigue": "Moderate", "mood": "Tired", "stress": "Low", "sleep_hours": 7.0},
            {"date": "2026-02-23", "fatigue": "Moderate", "mood": "Emotional", "stress": "High", "sleep_hours": 6.0},
            # Cycle 3 premenstrual: Mar 22, Mar 23 (C4 starts Mar 26)
            {"date": "2026-03-22", "fatigue": "Severe", "mood": "Tired", "stress": "Medium", "sleep_hours": 6.5},
            {"date": "2026-03-23", "fatigue": "Moderate", "mood": "Tired", "stress": "Low", "sleep_hours": 7.0},
        ]
        res = analyze_user_wellbeing_patterns(cycles, logs)
        self.assertEqual(res["status"], "ready")
        energy_pattern = next(p for p in res["patterns"] if p["pattern_id"] == "premenstrual_lower_energy")
        self.assertEqual(energy_pattern["evidence_status"], "supported")
        self.assertTrue(energy_pattern["is_recurring"])
        self.assertEqual(energy_pattern["cycles_observed"], 3)
        self.assertEqual(energy_pattern["total_cycles_evaluated"], 3)
        self.assertEqual(energy_pattern["relevant_logged_days"], 6)
        self.assertEqual(energy_pattern["recurrence_percentage"], 100.0)
        self.assertTrue(energy_pattern["is_window_estimated"])
        # Non-causal wording verification
        self.assertIn("In 3 of your last 3 logged cycles, you reported lower energy", energy_pattern["description"])
        self.assertNotIn("caused", energy_pattern["description"].lower())
        self.assertNotIn("pms", energy_pattern["description"].lower())

    def test_non_recurring_pattern_below_threshold(self):
        """
        User reports fatigue in 1 cycle, but high energy / no fatigue in Cycle 2 and 3.
        Must report non_recurring (33.3% < 66% threshold).
        """
        cycles = [
            {"cycle_id": "c1", "start_date": "2026-01-01", "cycle_length": 28, "period_length": 5, "gap_type": "normal"},
            {"cycle_id": "c2", "start_date": "2026-01-29", "cycle_length": 28, "period_length": 5, "gap_type": "normal"},
            {"cycle_id": "c3", "start_date": "2026-02-26", "cycle_length": 28, "period_length": 5, "gap_type": "normal"},
            {"cycle_id": "c4", "start_date": "2026-03-26", "cycle_length": None, "period_length": 5, "gap_type": "normal"}
        ]
        logs = [
            # Cycle 1: reported fatigue
            {"date": "2026-01-25", "fatigue": "Severe", "mood": "Tired"},
            {"date": "2026-01-26", "fatigue": "Moderate", "mood": "Tired"},
            # Cycle 2: explicitly reported no fatigue
            {"date": "2026-02-22", "fatigue": "None", "mood": "Happy"},
            {"date": "2026-02-23", "fatigue": "None", "mood": "Calm"},
            # Cycle 3: explicitly reported no fatigue
            {"date": "2026-03-22", "fatigue": "None", "mood": "Calm"},
            {"date": "2026-03-23", "fatigue": "None", "mood": "Happy"},
        ]
        res = analyze_user_wellbeing_patterns(cycles, logs)
        energy_pattern = next(p for p in res["patterns"] if p["pattern_id"] == "premenstrual_lower_energy")
        self.assertEqual(energy_pattern["evidence_status"], "non_recurring")
        self.assertFalse(energy_pattern["is_recurring"])
        self.assertEqual(energy_pattern["cycles_observed"], 1)
        self.assertEqual(energy_pattern["total_cycles_evaluated"], 3)
        self.assertAlmostEqual(energy_pattern["recurrence_percentage"], 33.3, places=1)
        self.assertIn("does not meet the 66% threshold", energy_pattern["status_reason"])

    def test_missing_metrics_not_treated_as_absence(self):
        """
        Unrecorded metric fields (None / missing key) must NOT be counted as 'no symptom'.
        If user only logs sleep, fatigue is treated as unrecorded (0 valid logs).
        """
        logs = [
            {"date": "2026-01-25", "sleep_hours": 7.5},  # no fatigue/mood key
            {"date": "2026-01-26", "sleep_hours": 8.0, "fatigue": None},  # explicit None
        ]
        has_occ, valid_logs, pos_count = evaluate_cycle_window_metric(logs, "lower_energy")
        self.assertEqual(valid_logs, 0, "Missing fields must not count as valid logged days for this metric")
        self.assertEqual(pos_count, 0)
        self.assertFalse(has_occ)

    def test_unreliable_cycle_windows_prevent_claims(self):
        """
        If all cycles are unclarified gaps (>45d), engine must declare unreliable_history
        rather than forcing inaccurate phase window claims.
        """
        cycles = [
            {"cycle_id": "c1", "start_date": "2026-01-01", "cycle_length": 70, "period_length": 5, "gap_type": "unclarified_gap"},
            {"cycle_id": "c2", "start_date": "2026-03-12", "cycle_length": 75, "period_length": 5, "gap_type": "unclarified_gap"}
        ]
        logs = [
            {"date": "2026-03-08", "fatigue": "Severe", "mood": "Tired"},
            {"date": "2026-03-09", "fatigue": "Severe", "mood": "Tired"},
            {"date": "2026-03-10", "fatigue": "Severe", "mood": "Tired"}
        ]
        res = analyze_user_wellbeing_patterns(cycles, logs)
        self.assertEqual(res["status"], "unreliable_history")
        self.assertEqual(res["reliable_cycles_count"], 0)
        self.assertEqual(len(res["patterns"]), 0)
        self.assertIn("unclarified tracking gaps", res["insufficient_data_reasons"][0])

    def test_menstrual_cramps_pattern_across_two_cycles(self):
        """Two cycles with cramps during early menstrual days (Days 1-5) generates supported pattern."""
        cycles = [
            {"cycle_id": "c1", "start_date": "2026-04-01", "cycle_length": 28, "period_length": 5, "gap_type": "normal"},
            {"cycle_id": "c2", "start_date": "2026-04-29", "cycle_length": 28, "period_length": 5, "gap_type": "normal"},
            {"cycle_id": "c3", "start_date": "2026-05-27", "cycle_length": None, "period_length": 5, "gap_type": "normal"}
        ]
        logs = [
            # Cycle 1 Day 1 & Day 2 (Apr 1, Apr 2)
            {"date": "2026-04-01", "cramps": "Moderate"},
            {"date": "2026-04-02", "cramps": "Mild"},
            # Cycle 2 Day 1 & Day 2 (Apr 29, Apr 30)
            {"date": "2026-04-29", "cramps": "Severe"},
            {"date": "2026-04-30", "cramps": "Moderate"}
        ]
        res = analyze_user_wellbeing_patterns(cycles, logs)
        cramps_pattern = next(p for p in res["patterns"] if p["pattern_id"] == "menstrual_cramps")
        self.assertEqual(cramps_pattern["evidence_status"], "supported")
        self.assertTrue(cramps_pattern["is_recurring"])
        self.assertEqual(cramps_pattern["cycles_observed"], 2)
        self.assertEqual(cramps_pattern["total_cycles_evaluated"], 2)
        self.assertEqual(cramps_pattern["relevant_logged_days"], 4)
        self.assertFalse(cramps_pattern["is_window_estimated"])  # Menstrual window is anchored on actual start dates


class TestWellbeingIntelligenceDatabaseIntegration(unittest.TestCase):
    """Verifies database-backed helper get_user_wellbeing_insights with user isolation."""

    @classmethod
    def setUpClass(cls):
        init_test_database()
        cls.user_a = "usr_wb_test_a"
        cls.user_b = "usr_wb_test_b"
        cls._cleanup()

        # Seed test users
        execute_write(
            "INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos) VALUES (:uid, 'User A', 'wba@test.app', 'hash', 26, 'Active', 0)",
            {"uid": cls.user_a}
        )
        execute_write(
            "INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos) VALUES (:uid, 'User B', 'wbb@test.app', 'hash', 28, 'Moderate', 0)",
            {"uid": cls.user_b}
        )

    @classmethod
    def tearDownClass(cls):
        cls._cleanup()

    @classmethod
    def _cleanup(cls):
        for uid in (cls.user_a, cls.user_b):
            execute_write("DELETE FROM wellness_logs WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM mood_logs WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM cycles WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM users WHERE user_id = :uid", {"uid": uid})

    def setUp(self):
        for uid in (self.user_a, self.user_b):
            execute_write("DELETE FROM wellness_logs WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM cycles WHERE user_id = :uid", {"uid": uid})

    def test_database_helper_and_user_isolation(self):
        """User A has recurring premenstrual fatigue, User B has no logs. User B cannot see User A data."""
        # Seed User A cycles
        execute_write(
            "INSERT INTO cycles (cycle_id, user_id, start_date, cycle_length, period_length, irregular, gap_type) VALUES ('cyc_a1', :uid, '2026-01-01', 28, 5, 0, 'normal')",
            {"uid": self.user_a}
        )
        execute_write(
            "INSERT INTO cycles (cycle_id, user_id, start_date, cycle_length, period_length, irregular, gap_type) VALUES ('cyc_a2', :uid, '2026-01-29', 28, 5, 0, 'normal')",
            {"uid": self.user_a}
        )
        execute_write(
            "INSERT INTO cycles (cycle_id, user_id, start_date, cycle_length, period_length, irregular, gap_type) VALUES ('cyc_a3', :uid, '2026-02-26', NULL, 5, 0, 'normal')",
            {"uid": self.user_a}
        )

        # Seed User A logs (premenstrual fatigue in Cycle 1 and Cycle 2)
        execute_write(
            "INSERT INTO wellness_logs (log_id, user_id, date, cycle_day, fatigue, mood, stress, sleep_hours) VALUES ('l1', :uid, '2026-01-25', 25, 'Severe', 'Tired', 'Low', 7.0)",
            {"uid": self.user_a}
        )
        execute_write(
            "INSERT INTO wellness_logs (log_id, user_id, date, cycle_day, fatigue, mood, stress, sleep_hours) VALUES ('l2', :uid, '2026-01-26', 26, 'Moderate', 'Tired', 'Medium', 6.5)",
            {"uid": self.user_a}
        )
        execute_write(
            "INSERT INTO wellness_logs (log_id, user_id, date, cycle_day, fatigue, mood, stress, sleep_hours) VALUES ('l3', :uid, '2026-02-22', 25, 'Severe', 'Tired', 'Low', 7.0)",
            {"uid": self.user_a}
        )
        execute_write(
            "INSERT INTO wellness_logs (log_id, user_id, date, cycle_day, fatigue, mood, stress, sleep_hours) VALUES ('l4', :uid, '2026-02-23', 26, 'Moderate', 'Emotional', 'High', 6.0)",
            {"uid": self.user_a}
        )

        # Query User A
        res_a = get_user_wellbeing_insights(self.user_a)
        self.assertEqual(res_a["status"], "ready")
        self.assertEqual(res_a["total_wellness_logs"], 4)
        p_a = next(p for p in res_a["patterns"] if p["pattern_id"] == "premenstrual_lower_energy")
        self.assertEqual(p_a["evidence_status"], "supported")
        self.assertTrue(p_a["is_recurring"])
        self.assertEqual(p_a["cycles_observed"], 2)

        # Query User B (must have 0 logs and insufficient_data)
        res_b = get_user_wellbeing_insights(self.user_b)
        self.assertEqual(res_b["status"], "insufficient_data")
        self.assertEqual(res_b["total_wellness_logs"], 0)
        self.assertEqual(len(res_b["patterns"]), 0)


class TestWellbeingAPIIntegration(unittest.TestCase):
    """Verifies API endpoints for GET /api/analytics and POST /api/logs."""

    @classmethod
    def setUpClass(cls):
        init_test_database()
        from app import app
        from common.auth import generate_auth_token
        app.config['TESTING'] = True
        cls.client = app.test_client()

        cls.user_a = "usr_api_wb_a"
        cls.user_b = "usr_api_wb_b"
        cls._cleanup()

        execute_write(
            "INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos) VALUES (:uid, 'User API A', 'api_a@test.app', 'hash', 25, 'Active', 0)",
            {"uid": cls.user_a}
        )
        execute_write(
            "INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos) VALUES (:uid, 'User API B', 'api_b@test.app', 'hash', 27, 'Moderate', 0)",
            {"uid": cls.user_b}
        )

        cls.token_a = generate_auth_token(cls.user_a)
        cls.token_b = generate_auth_token(cls.user_b)

    @classmethod
    def tearDownClass(cls):
        cls._cleanup()

    @classmethod
    def _cleanup(cls):
        for uid in (cls.user_a, cls.user_b):
            execute_write("DELETE FROM wellness_logs WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM mood_logs WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM cycles WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM users WHERE user_id = :uid", {"uid": uid})

    def setUp(self):
        for uid in (self.user_a, self.user_b):
            execute_write("DELETE FROM wellness_logs WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM mood_logs WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM cycles WHERE user_id = :uid", {"uid": uid})

    def test_analytics_includes_wellbeing_patterns_and_retains_keys(self):
        """GET /api/analytics returns wellbeing_patterns while preserving all existing response keys."""
        res = self.client.get('/api/analytics', headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # All existing keys preserved
        expected_keys = {
            "average_cycle_length", "average_period_length", "total_cycles_logged",
            "irregular_cycles_count", "cycle_history", "mood_frequencies",
            "symptoms_frequencies", "recent_trends", "insights", "wellbeing_patterns"
        }
        for k in expected_keys:
            self.assertIn(k, data, f"Missing key: {k}")

        wb = data["wellbeing_patterns"]
        self.assertIn("status", wb)
        self.assertIn("patterns", wb)

    def test_analytics_empty_and_insufficient_history(self):
        """User with no logs gets explicit insufficient_data status in wellbeing_patterns."""
        res = self.client.get('/api/analytics', headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(res.status_code, 200)
        wb = res.get_json()["wellbeing_patterns"]
        self.assertEqual(wb["status"], "insufficient_data")
        self.assertEqual(wb["total_wellness_logs"], 0)
        self.assertTrue(len(wb["insufficient_data_reasons"]) > 0)

    def test_cross_user_isolation_in_analytics(self):
        """User B cannot see User A's logs or wellbeing pattern data."""
        # User A logs cycles and logs
        execute_write(
            "INSERT INTO cycles (cycle_id, user_id, start_date, cycle_length, period_length, irregular, gap_type) VALUES ('cyc_a1', :uid, '2026-01-01', 28, 5, 0, 'normal')",
            {"uid": self.user_a}
        )
        execute_write(
            "INSERT INTO cycles (cycle_id, user_id, start_date, cycle_length, period_length, irregular, gap_type) VALUES ('cyc_a2', :uid, '2026-01-29', 28, 5, 0, 'normal')",
            {"uid": self.user_a}
        )
        execute_write(
            "INSERT INTO wellness_logs (log_id, user_id, date, cycle_day, fatigue, mood) VALUES ('log_a1', :uid, '2026-01-25', 25, 'Severe', 'Tired')",
            {"uid": self.user_a}
        )

        # User B queries analytics
        res_b = self.client.get('/api/analytics', headers={"Authorization": f"Bearer {self.token_b}"})
        self.assertEqual(res_b.status_code, 200)
        data_b = res_b.get_json()
        self.assertEqual(data_b["total_cycles_logged"], 0)
        self.assertEqual(data_b["wellbeing_patterns"]["total_wellness_logs"], 0)
        self.assertEqual(len(data_b["wellbeing_patterns"]["patterns"]), 0)

    def test_valid_and_invalid_energy_levels(self):
        """POST /api/logs accepts valid energy_level and rejects invalid with 400."""
        # Valid values
        for valid_val in ("High", "Moderate", "Low", "Very Low"):
            res = self.client.post(
                '/api/logs',
                headers={"Authorization": f"Bearer {self.token_a}"},
                json={"date": "2026-06-01", "energy_level": valid_val}
            )
            self.assertEqual(res.status_code, 200, f"Failed for valid energy: {valid_val}")

        # Invalid value
        res_inv = self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": "2026-06-02", "energy_level": "Supercharged"}
        )
        self.assertEqual(res_inv.status_code, 400)
        self.assertIn("Invalid energy_level", res_inv.get_json()["error"])

    def test_optional_notes_storage_and_retrieval(self):
        """POST /api/logs supports optional notes and returns them on GET /api/logs."""
        res_post = self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": "2026-06-03", "notes": "Felt refreshed after morning walk.", "mood": "Calm"}
        )
        self.assertEqual(res_post.status_code, 200)

        res_get = self.client.get('/api/logs', headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(res_get.status_code, 200)
        logs = res_get.get_json()
        target = next((l for l in logs if l["date"] == "2026-06-03"), None)
        self.assertIsNotNone(target)
        self.assertEqual(target["notes"], "Felt refreshed after morning walk.")
        self.assertEqual(target["mood"], "Calm")

    def test_omitted_fields_not_converted_to_none_string(self):
        """When cramps/fatigue/flow are omitted on a new record, they are stored as NULL, not 'None' string."""
        res_post = self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": "2026-06-04", "mood": "Happy"}
        )
        self.assertEqual(res_post.status_code, 200)

        row = execute_query(
            "SELECT cramps, fatigue, flow FROM wellness_logs WHERE user_id = :uid AND date = '2026-06-04'",
            {"uid": self.user_a}
        )[0]
        self.assertIsNone(row["cramps"], "Omitted cramps must be stored as None/NULL, not 'None'")
        self.assertIsNone(row["fatigue"], "Omitted fatigue must be stored as None/NULL, not 'None'")
        self.assertIsNone(row["flow"], "Omitted flow must be stored as None/NULL, not 'None'")

    def test_existing_log_omitted_fields_preserved_on_update(self):
        """Updating an existing log with only mood preserves previously saved cramps and notes."""
        # 1. Initial log with cramps and notes
        self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": "2026-06-05", "cramps": "Moderate", "notes": "Resting with tea", "energy_level": "Low"}
        )

        # 2. Update with ONLY mood
        res_update = self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": "2026-06-05", "mood": "Calm"}
        )
        self.assertEqual(res_update.status_code, 200)

        # 3. Verify previously saved fields are NOT erased
        row = execute_query(
            "SELECT mood, cramps, notes, energy_level FROM wellness_logs WHERE user_id = :uid AND date = '2026-06-05'",
            {"uid": self.user_a}
        )[0]
        self.assertEqual(row["mood"], "Calm")
        self.assertEqual(row["cramps"], "Moderate", "Omitted cramps on update must be preserved")
        self.assertEqual(row["notes"], "Resting with tea", "Omitted notes on update must be preserved")
        self.assertEqual(row["energy_level"], "Low", "Omitted energy_level on update must be preserved")

    def test_mood_logs_consistency_on_update(self):
        """Updating daily mood updates the existing mood_log record rather than inserting duplicates."""
        # Initial log
        self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": "2026-06-06", "mood": "Happy"}
        )
        count1 = execute_query(
            "SELECT COUNT(*) as count FROM mood_logs WHERE user_id = :uid AND date = '2026-06-06'",
            {"uid": self.user_a}
        )[0]["count"]
        self.assertEqual(count1, 1)

        # Update log
        self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": "2026-06-06", "mood": "Tired"}
        )
        mood_rows = execute_query(
            "SELECT mood FROM mood_logs WHERE user_id = :uid AND date = '2026-06-06'",
            {"uid": self.user_a}
        )
        self.assertEqual(len(mood_rows), 1, "Must NOT create duplicate mood_logs on update")
        self.assertEqual(mood_rows[0]["mood"], "Tired", "Mood log must be updated to new value")

    def test_delete_wellness_log_success_and_cross_user(self):
        """DELETE /api/logs/<log_id> deletes the log and cleans up mood_logs, enforcing authorization."""
        res_create = self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": "2026-06-07", "mood": "Calm", "cramps": "Mild"}
        )
        self.assertEqual(res_create.status_code, 200)
        log_id = res_create.get_json()["log_id"]

        # User B cannot delete User A's log
        res_del_b = self.client.delete(
            f'/api/logs/{log_id}',
            headers={"Authorization": f"Bearer {self.token_b}"}
        )
        self.assertEqual(res_del_b.status_code, 403)

        # User A can delete own log
        res_del_a = self.client.delete(
            f'/api/logs/{log_id}',
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res_del_a.status_code, 200)

        # Verify record is gone from DB
        logs_remain = execute_query("SELECT * FROM wellness_logs WHERE log_id = :lid", {"lid": log_id})
        self.assertEqual(len(logs_remain), 0)
        mood_remain = execute_query(
            "SELECT * FROM mood_logs WHERE user_id = :uid AND date = '2026-06-07'",
            {"uid": self.user_a}
        )
        self.assertEqual(len(mood_remain), 0)

        # Deleting non-existent log returns 404
        res_del_404 = self.client.delete(
            f'/api/logs/{log_id}',
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res_del_404.status_code, 404)


if __name__ == "__main__":
    unittest.main()
