import os
import sys
import unittest
from datetime import datetime, date, timedelta

# Ensure backend directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import (
    app,
    generate_auth_token,
    execute_query,
    execute_write
)
from common.doctor_summary import (
    generate_doctor_summary,
    render_doctor_summary_html,
    get_user_doctor_summary
)


class TestDoctorSummaryPure(unittest.TestCase):
    """
    Unit tests verifying pure calculation, category segregation,
    and HTML generation for clinical doctor-visit summaries.
    """

    def setUp(self):
        self.sample_profile = {
            "username": "Jane Doe",
            "age": 28,
            "lifestyle": "Active",
            "has_pcos": True
        }
        self.sample_cycles = [
            {
                "cycle_id": "c1",
                "start_date": "2026-07-01",
                "end_date": "2026-07-06",
                "cycle_length": 29,
                "period_length": 5,
                "irregular": 0,
                "gap_type": None
            },
            {
                "cycle_id": "c2",
                "start_date": "2026-07-30",
                "end_date": "2026-08-04",
                "cycle_length": 30,
                "period_length": 5,
                "irregular": 0,
                "gap_type": None
            },
            {
                "cycle_id": "c3",
                "start_date": "2026-08-29",
                "end_date": "2026-09-03",
                "cycle_length": 28,
                "period_length": 5,
                "irregular": 0,
                "gap_type": None
            }
        ]
        self.sample_logs = [
            {
                "log_id": "l1",
                "date": "2026-07-01",
                "cycle_day": 1,
                "flow": "Medium",
                "cramps": "Moderate",
                "fatigue": "Mild",
                "mood": "Emotional",
                "stress": "Medium",
                "sleep_hours": 7.0,
                "energy_level": "Moderate",
                "notes": "Starting period, feeling tired."
            },
            {
                "log_id": "l2",
                "date": "2026-07-02",
                "cycle_day": 2,
                "flow": "Heavy",
                "cramps": "Severe",
                "fatigue": "Moderate",
                "mood": "Tired",
                "stress": "High",
                "sleep_hours": 6.0,
                "energy_level": "Low",
                "notes": "Need to rest today."
            },
            {
                "log_id": "l3",
                "date": "2026-07-15",
                "cycle_day": 15,
                "flow": None,
                "cramps": None,
                "fatigue": None,
                "mood": "Happy",
                "stress": "Low",
                "sleep_hours": 8.0,
                "energy_level": "High",
                "notes": None
            }
        ]

    def test_generate_doctor_summary_segregates_categories(self):
        summary = generate_doctor_summary(
            cycles=self.sample_cycles,
            wellness_logs=self.sample_logs,
            user_profile=self.sample_profile
        )

        # Verify all 3 top-level clinical categories are distinctly present
        self.assertIn("category_1_recorded_facts", summary)
        self.assertIn("category_2_statistical_estimates", summary)
        self.assertIn("category_3_user_reported_symptoms", summary)

        # Category 1 facts verification
        cat1 = summary["category_1_recorded_facts"]
        self.assertEqual(cat1["total_cycles_recorded"], 3)
        self.assertEqual(len(cat1["cycles"]), 3)
        self.assertEqual(cat1["menstrual_flow_records"]["flow_distribution"]["Heavy"], 1)
        self.assertEqual(cat1["menstrual_flow_records"]["flow_distribution"]["Medium"], 1)

        # Category 2 estimates verification
        cat2 = summary["category_2_statistical_estimates"]
        self.assertIn("average_cycle_length_days", cat2)
        self.assertIn("average_period_length_days", cat2)
        self.assertIn("predicted_next_cycle", cat2)
        self.assertIn("methodology_note", cat2)

        # Category 3 symptoms verification
        cat3 = summary["category_3_user_reported_symptoms"]
        self.assertEqual(cat3["total_days_logged"], 3)
        self.assertIn("symptom_frequency_breakdown", cat3)
        self.assertIn("recent_patient_notes", cat3)
        self.assertEqual(len(cat3["recent_patient_notes"]), 2)

    def test_untracked_symptoms_distinct_from_absence(self):
        summary = generate_doctor_summary(
            cycles=self.sample_cycles,
            wellness_logs=self.sample_logs,
            user_profile=self.sample_profile
        )
        cramps = summary["category_3_user_reported_symptoms"]["symptom_frequency_breakdown"]["cramps"]
        # Log l3 had cramps: None (untracked). It must be recorded under 'untracked', NOT 'None'
        self.assertEqual(cramps["untracked"], 1)
        self.assertEqual(cramps["Moderate"], 1)
        self.assertEqual(cramps["Severe"], 1)
        self.assertEqual(cramps["None"], 0)

    def test_empty_records_handled_gracefully(self):
        summary = generate_doctor_summary(
            cycles=[],
            wellness_logs=[],
            user_profile={}
        )
        self.assertEqual(summary["category_1_recorded_facts"]["total_cycles_recorded"], 0)
        self.assertEqual(summary["category_3_user_reported_symptoms"]["total_days_logged"], 0)
        self.assertEqual(summary["category_2_statistical_estimates"]["average_cycle_length_days"], 28.0)
        self.assertIsNotNone(summary["clinical_disclaimer"])
        self.assertTrue(len(summary["safety_guidance"]) > 0)

    def test_clinical_safety_and_disclaimer_present(self):
        summary = generate_doctor_summary(
            cycles=self.sample_cycles,
            wellness_logs=self.sample_logs,
            user_profile=self.sample_profile
        )
        self.assertIn("clinical_disclaimer", summary)
        self.assertIn("does not replace comprehensive medical history", summary["clinical_disclaimer"])
        self.assertIn("safety_guidance", summary)
        self.assertTrue(any("heavy menstrual bleeding" in s.lower() for s in summary["safety_guidance"]))
        self.assertTrue(any("severe pelvic" in s.lower() for s in summary["safety_guidance"]))

    def test_render_doctor_summary_html(self):
        summary = generate_doctor_summary(
            cycles=self.sample_cycles,
            wellness_logs=self.sample_logs,
            user_profile=self.sample_profile
        )
        html = render_doctor_summary_html(summary)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Jane Doe", html)
        self.assertIn("Category 1: Recorded Facts", html)
        self.assertIn("Category 2: Statistical Estimates", html)
        self.assertIn("Category 3: User-Reported Symptoms", html)
        self.assertIn("Clinical Notice & Non-Diagnostic Scope", html)
        self.assertIn("Print / Save as PDF", html)


class TestDoctorSummaryAPI(unittest.TestCase):
    """
    Integration tests for GET /api/reports/doctor-summary endpoint.
    Verifies authentication, JSON response structure, HTML export,
    and user-level data isolation.
    """

    @classmethod
    def setUpClass(cls):
        from db import init_test_database
        init_test_database()
        app.config['TESTING'] = True
        cls.client = app.test_client()

        cls.user_a_id = "usr_doc_test_a"
        cls.user_b_id = "usr_doc_test_b"

        # Cleanup
        execute_write("DELETE FROM wellness_logs WHERE user_id IN (:ua, :ub)", {"ua": cls.user_a_id, "ub": cls.user_b_id})
        execute_write("DELETE FROM cycles WHERE user_id IN (:ua, :ub)", {"ua": cls.user_a_id, "ub": cls.user_b_id})
        execute_write("DELETE FROM users WHERE user_id IN (:ua, :ub)", {"ua": cls.user_a_id, "ub": cls.user_b_id})

        # Insert User A
        execute_write(
            """
            INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos)
            VALUES (:uid, 'Patient Alpha', 'alpha@ovacare.test', 'pwd_hash', 29, 'Active', TRUE)
            """,
            {"uid": cls.user_a_id}
        )

        # Insert User B
        execute_write(
            """
            INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos)
            VALUES (:uid, 'Patient Beta', 'beta@ovacare.test', 'pwd_hash', 34, 'Sedentary', FALSE)
            """,
            {"uid": cls.user_b_id}
        )

        # Seed cycles for User A
        execute_write(
            """
            INSERT INTO cycles (cycle_id, user_id, start_date, end_date, cycle_length, period_length, irregular)
            VALUES ('cyc_a1', :uid, '2026-06-01', '2026-06-05', 30, 5, 0)
            """,
            {"uid": cls.user_a_id}
        )
        execute_write(
            """
            INSERT INTO cycles (cycle_id, user_id, start_date, end_date, cycle_length, period_length, irregular)
            VALUES ('cyc_a2', :uid, '2026-07-01', '2026-07-06', 30, 5, 0)
            """,
            {"uid": cls.user_a_id}
        )

        # Seed a log for User A
        execute_write(
            """
            INSERT INTO wellness_logs (log_id, user_id, date, cycle_day, mood, stress, sleep_hours, cramps, flow, notes)
            VALUES ('log_a1', :uid, '2026-07-01', 1, 'Calm', 'Low', 7.5, 'Mild', 'Medium', 'First day of cycle')
            """,
            {"uid": cls.user_a_id}
        )

        # Generate tokens
        cls.token_a = generate_auth_token(cls.user_a_id)
        cls.token_b = generate_auth_token(cls.user_b_id)

    @classmethod
    def tearDownClass(cls):
        execute_write("DELETE FROM wellness_logs WHERE user_id IN (:ua, :ub)", {"ua": cls.user_a_id, "ub": cls.user_b_id})
        execute_write("DELETE FROM cycles WHERE user_id IN (:ua, :ub)", {"ua": cls.user_a_id, "ub": cls.user_b_id})
        execute_write("DELETE FROM users WHERE user_id IN (:ua, :ub)", {"ua": cls.user_a_id, "ub": cls.user_b_id})

    def test_unauthenticated_returns_401(self):
        res = self.client.get('/api/reports/doctor-summary')
        self.assertEqual(res.status_code, 401)

    def test_authenticated_returns_200_json(self):
        res = self.client.get(
            '/api/reports/doctor-summary',
            headers={'Authorization': f'Bearer {self.token_a}'}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("category_1_recorded_facts", data)
        self.assertIn("category_2_statistical_estimates", data)
        self.assertIn("category_3_user_reported_symptoms", data)
        self.assertEqual(data["patient_context"]["username"], "Patient Alpha")
        self.assertTrue(data["patient_context"]["has_pcos_reported"])
        self.assertEqual(data["category_1_recorded_facts"]["total_cycles_recorded"], 2)

    def test_authenticated_returns_html_print_format(self):
        res = self.client.get(
            '/api/reports/doctor-summary?format=html',
            headers={'Authorization': f'Bearer {self.token_a}'}
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/html', res.content_type)
        html_str = res.get_data(as_text=True)
        self.assertIn("Patient Alpha", html_str)
        self.assertIn("Clinical Visit Summary", html_str)
        self.assertIn("Print / Save as PDF", html_str)

    def test_user_data_isolation(self):
        # User B has 0 cycles and 0 logs
        res = self.client.get(
            '/api/reports/doctor-summary',
            headers={'Authorization': f'Bearer {self.token_b}'}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["patient_context"]["username"], "Patient Beta")
        self.assertFalse(data["patient_context"]["has_pcos_reported"])
        # Should see 0 cycles, not User A's 2 cycles
        self.assertEqual(data["category_1_recorded_facts"]["total_cycles_recorded"], 0)
        self.assertEqual(data["category_3_user_reported_symptoms"]["total_days_logged"], 0)


if __name__ == '__main__':
    unittest.main()
