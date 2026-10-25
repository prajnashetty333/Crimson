import os
import unittest
from datetime import datetime, timedelta

from app import app
from db import init_test_database, execute_write, execute_query
from common.period_tracker import calculate_period_prediction
from common.doctor_summary import generate_doctor_summary, get_user_doctor_summary
from common.auth import generate_auth_token


class TestPCOSRefinements(unittest.TestCase):
    """
    Focused test suite verifying the refined PCOS-Aware Tracking features:
    1. Standard tracking remains functional.
    2. PCOS-aware tracking can be enabled and disabled.
    3. Mode selection does not force an irregularity classification.
    4. Diagnosis status is never inferred automatically.
    5. Irregular cycles alone never produce a PCOS diagnosis.
    6. Incomplete history and unresolved gaps retain their existing behavior.
    7. Predictions and uncertainty remain consistent with the existing engine.
    8. User settings persist correctly and remain isolated between accounts.
    9. Existing cycle, wellbeing, analytics and report features remain integrated.
    """

    @classmethod
    def setUpClass(cls):
        init_test_database()
        app.config['TESTING'] = True
        cls.client = app.test_client()

        cls.user_std_id = "usr_pcos_test_std"
        cls.user_pcos_id = "usr_pcos_test_aware"

        # Cleanup test accounts
        for uid in (cls.user_std_id, cls.user_pcos_id):
            execute_write("DELETE FROM wellness_logs WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM cycles WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM users WHERE user_id = :uid", {"uid": uid})

        # Seed Standard Tracking User
        execute_write(
            """
            INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos, pcos_diagnosis_status, role)
            VALUES (:uid, 'Standard User', 'std@ovacare.test', 'pwdhash', 27, 'Moderate', 0, 'prefer_not_to_say', 'member')
            """,
            {"uid": cls.user_std_id}
        )
        cls.token_std = generate_auth_token(cls.user_std_id)

        # Seed PCOS-Aware User
        execute_write(
            """
            INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos, pcos_diagnosis_status, role)
            VALUES (:uid, 'PCOS User', 'pcos@ovacare.test', 'pwdhash', 30, 'Active', 1, 'diagnosed', 'member')
            """,
            {"uid": cls.user_pcos_id}
        )
        cls.token_pcos = generate_auth_token(cls.user_pcos_id)

    @classmethod
    def tearDownClass(cls):
        for uid in (cls.user_std_id, cls.user_pcos_id):
            execute_write("DELETE FROM wellness_logs WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM cycles WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM users WHERE user_id = :uid", {"uid": uid})

    def tearDown(self):
        for uid in (self.user_std_id, self.user_pcos_id):
            execute_write("DELETE FROM wellness_logs WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM cycles WHERE user_id = :uid", {"uid": uid})

    # -------------------------------------------------------------------------
    # 1. Standard tracking remains functional
    # -------------------------------------------------------------------------
    def test_1_standard_tracking_remains_functional(self):
        """Standard tracking works normally with has_pcos=False."""
        # Post 3 regular cycles for standard user
        dates = ['2026-01-01', '2026-01-29', '2026-02-26']
        for d in dates:
            res = self.client.post(
                '/api/cycles',
                headers={"Authorization": f"Bearer {self.token_std}"},
                json={"start_date": d}
            )
            self.assertEqual(res.status_code, 201)

        pred_res = self.client.get(
            '/api/predictions',
            headers={"Authorization": f"Bearer {self.token_std}"}
        )
        self.assertEqual(pred_res.status_code, 200)
        data = pred_res.get_json()
        self.assertFalse(data['pcos_mode'])
        self.assertFalse(data['pcos_aware_tracking'])
        self.assertEqual(data['tracking_mode'], 'Standard Tracking')
        self.assertFalse(data['irregular'])
        self.assertEqual(data['regularity_assessment'], 'regular')
        self.assertEqual(data['average_cycle_length'], 28)

    # -------------------------------------------------------------------------
    # 2. PCOS-aware tracking can be enabled and disabled
    # -------------------------------------------------------------------------
    def test_2_pcos_aware_tracking_toggle(self):
        """PCOS-aware tracking can be toggled on and off via user profile PUT endpoint."""
        # Enable PCOS-Aware tracking
        res = self.client.put(
            f'/api/users/{self.user_std_id}',
            headers={"Authorization": f"Bearer {self.token_std}"},
            json={"has_pcos": True}
        )
        self.assertEqual(res.status_code, 200)
        updated = res.get_json()['user']
        self.assertTrue(updated['has_pcos'])

        # Disable PCOS-Aware tracking
        res2 = self.client.put(
            f'/api/users/{self.user_std_id}',
            headers={"Authorization": f"Bearer {self.token_std}"},
            json={"has_pcos": False}
        )
        self.assertEqual(res2.status_code, 200)
        updated2 = res2.get_json()['user']
        self.assertFalse(updated2['has_pcos'])

    # -------------------------------------------------------------------------
    # 3. Mode selection does not force an irregularity classification
    # -------------------------------------------------------------------------
    def test_3_mode_selection_does_not_force_irregularity(self):
        """Enabling PCOS-Aware tracking does not force regular cycles to be classified irregular."""
        cycles = [
            {"cycle_id": "c1", "start_date": "2026-03-01", "cycle_length": 28, "period_length": 5, "gap_type": None},
            {"cycle_id": "c2", "start_date": "2026-02-01", "cycle_length": 28, "period_length": 5, "gap_type": None},
            {"cycle_id": "c3", "start_date": "2026-01-04", "cycle_length": 28, "period_length": 5, "gap_type": None},
        ]
        pred = calculate_period_prediction(cycles, has_pcos=True)
        self.assertTrue(pred["pcos_aware_tracking"])
        self.assertEqual(pred["tracking_mode"], "PCOS-Aware Tracking")
        self.assertFalse(pred["irregular"], "PCOS mode must NOT force irregular=True on regular cycles")
        self.assertEqual(pred["regularity_assessment"], "regular")

    # -------------------------------------------------------------------------
    # 4. Diagnosis status is never inferred automatically
    # -------------------------------------------------------------------------
    def test_4_diagnosis_status_never_inferred_automatically(self):
        """Diagnosis status is separate from tracking mode and is never auto-inferred from symptoms or cycles."""
        # Create a user with prefer_not_to_say
        uid = "usr_test_no_infer"
        execute_write("DELETE FROM users WHERE user_id = :uid", {"uid": uid})
        execute_write(
            """
            INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos, pcos_diagnosis_status, role)
            VALUES (:uid, 'No Infer User', 'noinfer@ovacare.test', 'pwdhash', 25, 'Active', 0, 'prefer_not_to_say', 'member')
            """,
            {"uid": uid}
        )
        token = generate_auth_token(uid)

        # Log severe symptoms and irregular cycles
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {token}"}, json={"start_date": "2026-01-01"})
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {token}"}, json={"start_date": "2026-02-15"}) # 45 days
        self.client.post('/api/wellness-logs', headers={"Authorization": f"Bearer {token}"}, json={
            "date": "2026-02-15", "cramps": "Severe", "fatigue": "Severe", "flow": "Heavy"
        })

        # Enable PCOS-Aware tracking mode
        self.client.put(
            f'/api/users/{uid}',
            headers={"Authorization": f"Bearer {token}"},
            json={"has_pcos": True}
        )

        # Verify diagnosis status was NOT automatically changed to 'diagnosed'
        user_rows = execute_query("SELECT pcos_diagnosis_status FROM users WHERE user_id = :uid", {"uid": uid})
        self.assertEqual(user_rows[0]['pcos_diagnosis_status'], 'prefer_not_to_say')

        # User explicitly chooses 'suspected'
        res_explicit = self.client.put(
            f'/api/users/{uid}',
            headers={"Authorization": f"Bearer {token}"},
            json={"pcos_diagnosis_status": "suspected"}
        )
        self.assertEqual(res_explicit.status_code, 200)
        user_rows2 = execute_query("SELECT pcos_diagnosis_status FROM users WHERE user_id = :uid", {"uid": uid})
        self.assertEqual(user_rows2[0]['pcos_diagnosis_status'], 'suspected')

        # Cleanup
        execute_write("DELETE FROM wellness_logs WHERE user_id = :uid", {"uid": uid})
        execute_write("DELETE FROM cycles WHERE user_id = :uid", {"uid": uid})
        execute_write("DELETE FROM users WHERE user_id = :uid", {"uid": uid})

    # -------------------------------------------------------------------------
    # 5. Irregular cycles alone never produce a PCOS diagnosis
    # -------------------------------------------------------------------------
    def test_5_irregular_cycles_alone_never_produce_pcos_diagnosis(self):
        """Irregular cycles trigger non-diagnostic medical guidance, never a PCOS diagnosis."""
        cycles = [
            {"cycle_id": "c1", "start_date": "2026-04-10", "cycle_length": 42, "period_length": 5, "gap_type": None},
            {"cycle_id": "c2", "start_date": "2026-02-27", "cycle_length": 25, "period_length": 5, "gap_type": None},
            {"cycle_id": "c3", "start_date": "2026-02-02", "cycle_length": 38, "period_length": 5, "gap_type": None},
        ]
        pred = calculate_period_prediction(cycles, has_pcos=False)
        self.assertTrue(pred["irregular"])
        self.assertEqual(pred["regularity_assessment"], "irregular")

        # Must not claim "PCOS detected" or diagnose PCOS
        self.assertNotIn("PCOS detected", pred["regularity_message"])
        self.assertNotIn("You have PCOS", pred["regularity_message"])
        self.assertIn("There can be several reasons for this", pred["regularity_message"])
        self.assertIn("qualified healthcare professional", pred["regularity_message"])

    # -------------------------------------------------------------------------
    # 6. Incomplete history and unresolved gaps retain existing behavior
    # -------------------------------------------------------------------------
    def test_6_incomplete_history_and_unresolved_gaps(self):
        """Incomplete history does not become proof of irregularity; gaps are handled safely."""
        # Empty cycles
        pred_empty = calculate_period_prediction([], has_pcos=True)
        self.assertEqual(pred_empty["tracking_status"], "insufficient_history")
        self.assertEqual(pred_empty["regularity_assessment"], "insufficient_data")
        self.assertFalse(pred_empty["irregular"])

        # 1 cycle (cannot classify regularity)
        pred_single = calculate_period_prediction([
            {"cycle_id": "c1", "start_date": "2026-05-01", "cycle_length": None, "period_length": 5, "gap_type": None}
        ], has_pcos=True)
        self.assertEqual(pred_single["regularity_assessment"], "insufficient_data")
        self.assertFalse(pred_single["can_classify_regularity"])
        self.assertFalse(pred_single["irregular"])

        # Unclarified gap (>45 days)
        pred_gap = calculate_period_prediction([
            {"cycle_id": "c1", "start_date": "2026-05-01", "cycle_length": 55, "period_length": 5, "gap_type": None},
            {"cycle_id": "c2", "start_date": "2026-03-07", "cycle_length": 28, "period_length": 5, "gap_type": None},
            {"cycle_id": "c3", "start_date": "2026-02-07", "cycle_length": 28, "period_length": 5, "gap_type": None},
        ], has_pcos=True)
        self.assertTrue(pred_gap["has_unclarified_gap"])
        self.assertEqual(pred_gap["tracking_status"], "needs_clarification")
        self.assertEqual(pred_gap["prediction_confidence"], "moderate")
        # 55-day gap is safely excluded from average calculation
        self.assertEqual(pred_gap["average_cycle_length"], 28)

    # -------------------------------------------------------------------------
    # 7. Predictions and uncertainty remain consistent with existing engine
    # -------------------------------------------------------------------------
    def test_7_predictions_and_uncertainty_consistent_across_modes(self):
        """PCOS mode does NOT silently change calculation thresholds or manufacture missing cycle records."""
        cycles = [
            {"cycle_id": "c1", "start_date": "2026-04-01", "cycle_length": 30, "period_length": 5, "gap_type": None},
            {"cycle_id": "c2", "start_date": "2026-03-02", "cycle_length": 30, "period_length": 5, "gap_type": None},
            {"cycle_id": "c3", "start_date": "2026-01-31", "cycle_length": 30, "period_length": 5, "gap_type": None},
        ]
        pred_std = calculate_period_prediction(cycles, has_pcos=False)
        pred_pcos = calculate_period_prediction(cycles, has_pcos=True)

        self.assertEqual(pred_std["predicted_date"], pred_pcos["predicted_date"])
        self.assertEqual(pred_std["average_cycle_length"], pred_pcos["average_cycle_length"])
        self.assertEqual(pred_std["usable_intervals"], pred_pcos["usable_intervals"])
        self.assertEqual(pred_std["irregular"], pred_pcos["irregular"])
        self.assertEqual(pred_std["prediction_confidence"], pred_pcos["prediction_confidence"])

    # -------------------------------------------------------------------------
    # 8. User settings persist correctly and remain isolated between accounts
    # -------------------------------------------------------------------------
    def test_8_user_settings_persist_and_isolated(self):
        """User A settings cannot be read or modified by User B."""
        # User B (standard) tries to access User A's profile via PUT
        res_cross = self.client.put(
            f'/api/users/{self.user_pcos_id}',
            headers={"Authorization": f"Bearer {self.token_std}"},
            json={"has_pcos": False}
        )
        self.assertEqual(res_cross.status_code, 403)

        # Verify User A's data was not changed
        rows = execute_query(
            "SELECT has_pcos, pcos_diagnosis_status FROM users WHERE user_id = :uid",
            {"uid": self.user_pcos_id}
        )
        self.assertTrue(bool(rows[0]['has_pcos']))
        self.assertEqual(rows[0]['pcos_diagnosis_status'], 'diagnosed')

    # -------------------------------------------------------------------------
    # 9. Health report reflects tracking mode and diagnosis without claiming clinical diagnosis
    # -------------------------------------------------------------------------
    def test_9_health_report_tracking_mode_context(self):
        """Unified report includes tracking_mode and reported status, never claims app diagnosed PCOS."""
        summary = get_user_doctor_summary(self.user_pcos_id)
        patient_ctx = summary.get("patient_context", {})
        self.assertEqual(patient_ctx.get("tracking_mode"), "PCOS-Aware Tracking")
        self.assertEqual(patient_ctx.get("pcos_diagnosis_status"), "diagnosed")
        self.assertEqual(patient_ctx.get("pcos_diagnosis_display"), "Diagnosed by a healthcare professional")
        self.assertIn("clinical_disclaimer", summary)
        self.assertIn("does not provide medical diagnoses", summary["clinical_disclaimer"] + str(summary.get("safety_guidance")))


if __name__ == '__main__':
    unittest.main()
