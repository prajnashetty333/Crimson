"""
Automated Verification Test Suite for OvaCare AI Demo Patient Experience.

Verifies:
1. Demo seeding into the isolated demo database (with production guard).
2. Repeat seed execution without duplicate records (idempotency).
3. Cycle dates and derived cycle lengths ([28, 29, 27, 30, 28] days).
4. Prediction and uncertainty outputs (high confidence, 28-day baseline, regular).
5. Correct cycle-gap handling (Jordan Gap Demo 56d interval, clarification recalculation).
6. Wellbeing logs and valid field values (fatigue, cramps, flow, energy, stress, sleep).
7. NULL versus explicit symptom absence ('None' vs NULL distinction).
8. Supported insights produced by the deterministic engine (lower energy, cramps, stress-sleep).
9. Authenticated access and user-level data isolation.
10. Unified My Health Report generation (Category 1, 2, 3 segregation).
"""

import os
import sys
import unittest
from datetime import date

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import db
from db import (
    PROTECTED_PROD_DB_PATH,
    DEFAULT_DEMO_DB_PATH,
    init_demo_database,
    execute_query,
    execute_write,
    is_demo_mode,
    is_active_db_protected,
)
from seed_demo import (
    seed_demo_database,
    assert_safe_demo_target,
    MAYA_USER_ID,
    MAYA_EMAIL,
    MAYA_NAME,
    JORDAN_USER_ID,
    JORDAN_EMAIL,
    JORDAN_NAME,
    DEMO_PASSWORD_RAW,
)
from common.period_tracker import (
    calculate_period_prediction,
    update_cycle_clarification,
    recalculate_user_cycles,
)
from common.wellbeing_tracker import analyze_user_wellbeing_patterns
from common.doctor_summary import get_user_doctor_summary, render_doctor_summary_html
from app import app


class TestDemoPatient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize isolated demo database for tests
        cls.demo_db_path = os.path.abspath(os.path.join(BACKEND_DIR, "ovacare_demo_test.db"))
        # Seed test demo database
        seed_demo_database(target_db_path=cls.demo_db_path, reset_tables=True)
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        # Clean up temporary test demo db if needed
        pass

    def test_01_demo_seeding_in_isolated_database_rejects_production(self):
        """Verifies seeding targets isolated DB and strictly blocks execution on production DB."""
        # Must raise RuntimeError on protected production DB
        with self.assertRaises(RuntimeError) as ctx:
            assert_safe_demo_target(PROTECTED_PROD_DB_PATH)
        self.assertIn("CRITICAL SAFETY VIOLATION", str(ctx.exception))

        # Active DB must be the demo database, NOT the protected production DB
        self.assertNotEqual(db.get_active_db_path(), PROTECTED_PROD_DB_PATH)
        self.assertFalse(is_active_db_protected())

    def test_02_seed_idempotency_no_duplicates(self):
        """Running seed_demo_database multiple times refreshes records without creating duplicates."""
        initial_maya_cycles = len(execute_query("SELECT cycle_id FROM cycles WHERE user_id = :uid", {"uid": MAYA_USER_ID}))
        initial_maya_logs = len(execute_query("SELECT log_id FROM wellness_logs WHERE user_id = :uid", {"uid": MAYA_USER_ID}))
        initial_users = len(execute_query("SELECT user_id FROM users WHERE user_id IN (:m, :j)", {"m": MAYA_USER_ID, "j": JORDAN_USER_ID}))

        self.assertEqual(initial_users, 2)
        self.assertEqual(initial_maya_cycles, 6)
        self.assertGreaterEqual(initial_maya_logs, 30)

        # Run seeder a second time
        seed_demo_database(target_db_path=self.demo_db_path, reset_tables=False)

        second_maya_cycles = len(execute_query("SELECT cycle_id FROM cycles WHERE user_id = :uid", {"uid": MAYA_USER_ID}))
        second_maya_logs = len(execute_query("SELECT log_id FROM wellness_logs WHERE user_id = :uid", {"uid": MAYA_USER_ID}))
        second_users = len(execute_query("SELECT user_id FROM users WHERE user_id IN (:m, :j)", {"m": MAYA_USER_ID, "j": JORDAN_USER_ID}))

        self.assertEqual(second_users, initial_users, "Seeding must not duplicate user records")
        self.assertEqual(second_maya_cycles, initial_maya_cycles, "Seeding must not duplicate cycle records")
        self.assertEqual(second_maya_logs, initial_maya_logs, "Seeding must not duplicate wellness logs")

    def test_03_cycle_dates_and_derived_lengths(self):
        """Maya Demo must have 6 chronologically sorted cycles with intervals [28, 29, 27, 30, 28]."""
        cycles = execute_query(
            "SELECT start_date, end_date, cycle_length, period_length, irregular FROM cycles WHERE user_id = :uid ORDER BY start_date ASC",
            {"uid": MAYA_USER_ID}
        )
        self.assertEqual(len(cycles), 6)
        lengths = [c['cycle_length'] for c in cycles if c['cycle_length'] is not None]
        self.assertEqual(lengths, [28, 29, 27, 30, 28])

        # Ongoing cycle has cycle_length = None
        self.assertIsNone(cycles[-1]['cycle_length'])
        self.assertFalse(any(c['irregular'] for c in cycles), "All physiological intervals are within variance")

    def test_04_prediction_and_uncertainty_outputs(self):
        """Tests high-confidence next period prediction and regularity for Maya Demo."""
        cycles = execute_query(
            "SELECT * FROM cycles WHERE user_id = :uid ORDER BY start_date ASC",
            {"uid": MAYA_USER_ID}
        )
        pred = calculate_period_prediction(cycles, has_pcos=False)

        self.assertEqual(pred['average_cycle_length'], 28)
        self.assertEqual(pred['average_period_length'], 5)
        self.assertEqual(pred['prediction_confidence'], 'high')
        self.assertEqual(pred['regularity_assessment'], 'regular')
        self.assertFalse(pred['irregular'])
        self.assertFalse(pred['has_unclarified_gap'])
        self.assertEqual(pred['predicted_date'], "2026-11-04")
        self.assertEqual(pred['history_quality'], 'established')

    def test_05_correct_cycle_gap_handling(self):
        """Jordan Gap Demo has a 56d unclarified gap; updates dynamically upon user clarification."""
        j_cycles = execute_query(
            "SELECT cycle_id, start_date, cycle_length, gap_type FROM cycles WHERE user_id = :uid ORDER BY start_date ASC",
            {"uid": JORDAN_USER_ID}
        )
        self.assertEqual(len(j_cycles), 5)

        # Cycle 1 interval to Cycle 2 is 56 days (> 45 days)
        c1 = j_cycles[0]
        self.assertEqual(c1['cycle_length'], 56)
        self.assertEqual(c1['gap_type'], 'unclarified_gap')

        # Prediction before clarification flags the gap
        pred_before = calculate_period_prediction(j_cycles, has_pcos=False)
        self.assertTrue(pred_before['has_unclarified_gap'])
        self.assertEqual(pred_before['history_quality'], 'needs_clarification')
        self.assertEqual(pred_before['prediction_confidence'], 'moderate')

        # Clarify gap as 'confirmed_long_cycle'
        success, msg, code = update_cycle_clarification(JORDAN_USER_ID, c1['cycle_id'], 'confirmed_long_cycle')
        self.assertTrue(success)
        self.assertEqual(code, 200)

        # Recalculated prediction reflects confirmed long cycle
        j_cycles_after = execute_query(
            "SELECT * FROM cycles WHERE user_id = :uid ORDER BY start_date ASC",
            {"uid": JORDAN_USER_ID}
        )
        pred_after = calculate_period_prediction(j_cycles_after, has_pcos=False)
        self.assertEqual(pred_after['regularity_assessment'], 'irregular')
        self.assertEqual(pred_after['prediction_confidence'], 'uncertain')

        # Reset gap back to 'unclarified_gap' for demo stability
        update_cycle_clarification(JORDAN_USER_ID, c1['cycle_id'], 'unclarified_gap')

    def test_06_wellbeing_logs_valid_field_values(self):
        """Wellness logs must use valid enum options and realistic sleep ranges."""
        logs = execute_query(
            "SELECT mood, stress, sleep_hours, cramps, fatigue, flow, energy_level FROM wellness_logs WHERE user_id = :uid",
            {"uid": MAYA_USER_ID}
        )
        valid_moods = {"Happy", "Calm", "Emotional", "Irritated", "Tired", "Anxious", None}
        valid_stresses = {"Low", "Medium", "High", None}
        valid_severities = {"None", "Mild", "Moderate", "Severe", None}
        valid_flows = {"None", "Light", "Medium", "Heavy", None}
        valid_energies = {"High", "Moderate", "Low", "Very Low", None}

        for log in logs:
            self.assertIn(log['mood'], valid_moods)
            self.assertIn(log['stress'], valid_stresses)
            self.assertIn(log['cramps'], valid_severities)
            self.assertIn(log['fatigue'], valid_severities)
            self.assertIn(log['flow'], valid_flows)
            self.assertIn(log['energy_level'], valid_energies)
            if log['sleep_hours'] is not None:
                self.assertGreaterEqual(log['sleep_hours'], 4.0)
                self.assertLessEqual(log['sleep_hours'], 12.0)

    def test_07_null_versus_explicit_symptom_absence(self):
        """Verifies database contains both explicit 'None' records and unrecorded NULL records."""
        explicit_none_cramps = execute_query(
            "SELECT COUNT(*) as count FROM wellness_logs WHERE user_id = :uid AND cramps = 'None'",
            {"uid": MAYA_USER_ID}
        )[0]['count']
        unrecorded_cramps = execute_query(
            "SELECT COUNT(*) as count FROM wellness_logs WHERE user_id = :uid AND cramps IS NULL",
            {"uid": MAYA_USER_ID}
        )[0]['count']

        self.assertGreater(explicit_none_cramps, 0, "Must have explicit 'None' cramps logs")
        self.assertGreater(unrecorded_cramps, 0, "Must have unrecorded NULL cramps logs")

    def test_08_supported_insights_produced_by_engine(self):
        """Pattern engine must produce supported patterns for lower energy, cramps, and stress-sleep."""
        cycles = execute_query(
            "SELECT * FROM cycles WHERE user_id = :uid ORDER BY start_date ASC",
            {"uid": MAYA_USER_ID}
        )
        logs = execute_query(
            "SELECT * FROM wellness_logs WHERE user_id = :uid ORDER BY date ASC",
            {"uid": MAYA_USER_ID}
        )
        report = analyze_user_wellbeing_patterns(cycles, logs)
        self.assertEqual(report['status'], 'ready')

        patterns = {p['pattern_id']: p for p in report['patterns']}

        # Supported Pattern 1: Lower Energy
        self.assertEqual(patterns['premenstrual_lower_energy']['evidence_status'], 'supported')
        self.assertTrue(patterns['premenstrual_lower_energy']['is_recurring'])

        # Supported Pattern 2: Cramps
        self.assertEqual(patterns['menstrual_cramps']['evidence_status'], 'supported')
        self.assertTrue(patterns['menstrual_cramps']['is_recurring'])

        # Supported Pattern 3: Stress-Sleep
        self.assertEqual(patterns['stress_sleep_correlation']['evidence_status'], 'supported')
        self.assertTrue(patterns['stress_sleep_correlation']['is_recurring'])

        # Non-recurring Pattern: Emotional Shifts (demonstrates honesty, 20% recurrence rate)
        self.assertEqual(patterns['premenstrual_emotional_shifts']['evidence_status'], 'non_recurring')
        self.assertFalse(patterns['premenstrual_emotional_shifts']['is_recurring'])

    def test_09_authenticated_access_and_isolation(self):
        """Tests demo login authentication endpoint and user-level data isolation."""
        # Dedicated Demo Login endpoint
        res = self.client.post('/api/auth/demo', json={"email": MAYA_EMAIL})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("token", data)
        self.assertEqual(data['user']['username'], MAYA_NAME)
        self.assertEqual(data['user']['email'], MAYA_EMAIL)
        self.assertTrue(data['user']['is_demo'])

        token = data['token']
        headers = {"Authorization": f"Bearer {token}"}

        # Query user cycles via authenticated API
        cycles_res = self.client.get('/api/cycles', headers=headers)
        self.assertEqual(cycles_res.status_code, 200)
        cycles_data = cycles_res.get_json()
        self.assertIsInstance(cycles_data, list)
        self.assertEqual(len(cycles_data), 6)
        # All cycles must belong to Maya Demo
        self.assertTrue(all(c['user_id'] == MAYA_USER_ID for c in cycles_data))

    def test_10_my_health_report_generation(self):
        """Unified My Health Report correctly outputs Category 1, 2, 3 data and HTML print format."""
        summary = get_user_doctor_summary(MAYA_USER_ID)

        # Metadata
        self.assertEqual(summary['patient_context']['username'], MAYA_NAME)
        self.assertEqual(summary['patient_context']['age'], 24)
        self.assertEqual(summary['patient_context']['tracking_mode'], 'Standard Tracking')

        # Category 1: Recorded Facts
        self.assertEqual(summary['category_1_recorded_facts']['total_cycles_recorded'], 6)
        self.assertGreater(summary['category_1_recorded_facts']['menstrual_flow_records']['total_flow_entries_logged'], 10)

        # Category 2: Statistical Estimates
        self.assertEqual(round(summary['category_2_statistical_estimates']['average_cycle_length_days']), 28)
        self.assertEqual(round(summary['category_2_statistical_estimates']['average_period_length_days']), 5)
        self.assertTrue(summary['category_2_statistical_estimates']['regularity_supported_by_data'])

        # Category 3: User-Reported Symptoms
        self.assertGreater(summary['category_3_user_reported_symptoms']['total_days_logged'], 30)

        # Clinical Disclaimer
        self.assertIn("patient-entered", summary['clinical_disclaimer'].lower())
        self.assertIn("non_diagnostic_disclaimer", summary['important_information'])

        # HTML Rendering
        html = render_doctor_summary_html(summary)
        self.assertIn("My Health Report", html)
        self.assertIn("Maya Demo", html)
        self.assertIn("Category 1", html)
        self.assertIn("Recorded Facts", html)
        self.assertIn("Category 2", html)
        self.assertIn("Statistical Estimates", html)
        self.assertIn("Category 3", html)
        self.assertIn("User-Reported Symptoms", html)


if __name__ == '__main__':
    unittest.main()
