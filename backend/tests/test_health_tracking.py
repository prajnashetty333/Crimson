import os
import sys
import unittest
from datetime import datetime, timedelta

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


class TestHealthTracking(unittest.TestCase):
    """
    Step 3 Verification:
    Unified Physical & Emotional Health Tracking tests covering:
    - Combined daily health logging
    - Missing optional fields handling
    - Input validation and bounds checking
    - Cycle-phase context (available vs uncertain/unavailable)
    - Supportive wellbeing feedback (rule-based, no medical/diagnostic claims)
    - Authentication and user ownership enforcement
    """

    @classmethod
    def setUpClass(cls):
        from db import init_test_database
        init_test_database()
        app.config['TESTING'] = True
        cls.client = app.test_client()

        # Create two test users: User A and User B
        cls.user_a_id = "usr_test_health_a"
        cls.user_b_id = "usr_test_health_b"

        execute_write("DELETE FROM wellness_logs WHERE user_id IN (:ua, :ub)", {"ua": cls.user_a_id, "ub": cls.user_b_id})
        execute_write("DELETE FROM mood_logs WHERE user_id IN (:ua, :ub)", {"ua": cls.user_a_id, "ub": cls.user_b_id})
        execute_write("DELETE FROM cycles WHERE user_id IN (:ua, :ub)", {"ua": cls.user_a_id, "ub": cls.user_b_id})
        execute_write("DELETE FROM users WHERE user_id IN (:ua, :ub)", {"ua": cls.user_a_id, "ub": cls.user_b_id})

        execute_write(
            """
            INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos)
            VALUES (:uid, :uname, :email, :pwd, 26, 'Active', FALSE)
            """,
            {"uid": cls.user_a_id, "uname": "Health User A", "email": "health_a@ovacare.test", "pwd": "hash_pwd_test_123"}
        )
        execute_write(
            """
            INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos)
            VALUES (:uid, :uname, :email, :pwd, 28, 'Moderate', FALSE)
            """,
            {"uid": cls.user_b_id, "uname": "Health User B", "email": "health_b@ovacare.test", "pwd": "hash_pwd_test_123"}
        )

        cls.token_a = generate_auth_token(cls.user_a_id)
        cls.token_b = generate_auth_token(cls.user_b_id)

    @classmethod
    def tearDownClass(cls):
        execute_write("DELETE FROM wellness_logs WHERE user_id IN (:ua, :ub)", {"ua": cls.user_a_id, "ub": cls.user_b_id})
        execute_write("DELETE FROM mood_logs WHERE user_id IN (:ua, :ub)", {"ua": cls.user_a_id, "ub": cls.user_b_id})
        execute_write("DELETE FROM cycles WHERE user_id IN (:ua, :ub)", {"ua": cls.user_a_id, "ub": cls.user_b_id})
        execute_write("DELETE FROM users WHERE user_id IN (:ua, :ub)", {"ua": cls.user_a_id, "ub": cls.user_b_id})

    def setUp(self):
        # Clean logs and cycles for test users before each test
        execute_write("DELETE FROM wellness_logs WHERE user_id IN (:ua, :ub)", {"ua": self.user_a_id, "ub": self.user_b_id})
        execute_write("DELETE FROM mood_logs WHERE user_id IN (:ua, :ub)", {"ua": self.user_a_id, "ub": self.user_b_id})
        execute_write("DELETE FROM cycles WHERE user_id IN (:ua, :ub)", {"ua": self.user_a_id, "ub": self.user_b_id})

    # ------------------------------------------------------------------
    # 1. Combined Daily Health Log & Optional Fields
    # ------------------------------------------------------------------

    def test_save_log_with_all_fields_succeeds(self):
        """User records mood, physical symptoms, energy level, and personal notes together."""
        # Add a reference cycle for User A: started 2 days ago
        two_days_ago = (datetime.now().date() - timedelta(days=2)).isoformat()
        execute_write(
            """
            INSERT INTO cycles (cycle_id, user_id, start_date, cycle_length, period_length, irregular)
            VALUES ('cyc_test_1', :uid, :start_date, 28, 5, FALSE)
            """,
            {"uid": self.user_a_id, "start_date": two_days_ago}
        )

        log_payload = {
            "date": datetime.now().date().isoformat(),
            "mood": "Calm",
            "stress": "Low",
            "sleep_hours": 8.0,
            "cramps": "Mild",
            "fatigue": "None",
            "flow": "Medium",
            "energy_level": "Moderate",
            "notes": "Had a relaxing morning walk and chamomile tea."
        }
        res = self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json=log_payload
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("log_id", data)
        self.assertEqual(data["cycle_day"], 3)
        self.assertIn("Wellness log saved successfully", data.get("message", ""))

        # Verify DB persistence of all physical and emotional metrics
        db_logs = execute_query("SELECT * FROM wellness_logs WHERE log_id = :lid", {"lid": data["log_id"]})
        self.assertEqual(len(db_logs), 1)
        db_log = db_logs[0]
        self.assertEqual(db_log["mood"], "Calm")
        self.assertEqual(db_log["stress"], "Low")
        self.assertEqual(db_log["sleep_hours"], 8.0)
        self.assertEqual(db_log["cramps"], "Mild")
        self.assertEqual(db_log["fatigue"], "None")
        self.assertEqual(db_log["flow"], "Medium")
        self.assertEqual(db_log["energy_level"], "Moderate")
        self.assertEqual(db_log["notes"], "Had a relaxing morning walk and chamomile tea.")
        self.assertEqual(db_log["cycle_day"], 3)

    def test_save_log_missing_optional_fields_succeeds(self):
        """Omitting optional fields leaves them as NULL in the database, preserving missing-value distinction."""
        log_payload = {
            "date": datetime.now().date().isoformat()
        }
        res = self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json=log_payload
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("log_id", data)

        db_logs = execute_query("SELECT * FROM wellness_logs WHERE log_id = :lid", {"lid": data["log_id"]})
        self.assertEqual(len(db_logs), 1)
        # Verify unrecorded fields remain NULL, never coerced to string 'None'
        self.assertIsNone(db_logs[0]["energy_level"])
        self.assertIsNone(db_logs[0]["notes"])
        self.assertIsNone(db_logs[0]["mood"])
        self.assertIsNone(db_logs[0]["stress"])
        self.assertIsNone(db_logs[0]["sleep_hours"])
        self.assertIsNone(db_logs[0]["cramps"])
        self.assertIsNone(db_logs[0]["fatigue"])
        self.assertIsNone(db_logs[0]["flow"])

    def test_update_existing_daily_log_preserves_uniqueness(self):
        """Logging on the same date updates the existing entry rather than creating duplicates."""
        today = datetime.now().date().isoformat()
        res1 = self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": today, "mood": "Happy", "energy_level": "High"}
        )
        self.assertEqual(res1.status_code, 200)
        log_id1 = res1.get_json()["log_id"]

        # Update later in the day with additional fields
        res2 = self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": today, "mood": "Calm", "energy_level": "Moderate", "notes": "Evening update"}
        )
        self.assertEqual(res2.status_code, 200)
        log_id2 = res2.get_json()["log_id"]
        self.assertEqual(log_id1, log_id2)

        # Confirm only 1 log exists for this user and date
        all_logs = execute_query(
            "SELECT * FROM wellness_logs WHERE user_id = :uid AND date = :date",
            {"uid": self.user_a_id, "date": today}
        )
        self.assertEqual(len(all_logs), 1)
        self.assertEqual(all_logs[0]["mood"], "Calm")
        self.assertEqual(all_logs[0]["energy_level"], "Moderate")
        self.assertEqual(all_logs[0]["notes"], "Evening update")

    # ------------------------------------------------------------------
    # 2. Input Validation & Error Handling
    # ------------------------------------------------------------------

    def test_invalid_date_returns_400(self):
        """Missing or malformed date must return 400."""
        # Missing date
        res = self.client.post('/api/logs', headers={"Authorization": f"Bearer {self.token_a}"}, json={})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Missing required field: date", res.get_json()["error"])

        # Malformed date
        res2 = self.client.post('/api/logs', headers={"Authorization": f"Bearer {self.token_a}"}, json={"date": "invalid-date"})
        self.assertEqual(res2.status_code, 400)
        self.assertIn("YYYY-MM-DD", res2.get_json()["error"])

    def test_invalid_energy_level_returns_400(self):
        """Invalid energy level option must be rejected."""
        res = self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": "2026-10-24", "energy_level": "SuperCharged"}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid energy_level", res.get_json()["error"])

    def test_valid_energy_levels_accepted(self):
        """All supported energy levels (High, Moderate, Low, Very Low) are accepted."""
        for level in ["High", "Moderate", "Low", "Very Low"]:
            res = self.client.post(
                '/api/logs',
                headers={"Authorization": f"Bearer {self.token_a}"},
                json={"date": "2026-10-24", "energy_level": level}
            )
            self.assertEqual(res.status_code, 200)
            db_log = execute_query(
                "SELECT energy_level FROM wellness_logs WHERE user_id = :uid AND date = '2026-10-24'",
                {"uid": self.user_a_id}
            )[0]
            self.assertEqual(db_log["energy_level"], level)

    def test_notes_whitespace_handling(self):
        """Empty or whitespace-only notes are normalized to None."""
        res = self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": "2026-10-24", "notes": "   "}
        )
        self.assertEqual(res.status_code, 200)
        db_log = execute_query(
            "SELECT notes FROM wellness_logs WHERE user_id = :uid AND date = '2026-10-24'",
            {"uid": self.user_a_id}
        )[0]
        self.assertIsNone(db_log["notes"])

    # ------------------------------------------------------------------
    # 3. Cycle Day Calculation Context
    # ------------------------------------------------------------------

    def test_cycle_day_null_when_no_cycles_exist(self):
        """When user has no recorded cycle data, cycle_day must be None."""
        res = self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": "2026-10-24", "mood": "Calm"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsNone(data["cycle_day"])

        db_log = execute_query("SELECT cycle_day FROM wellness_logs WHERE log_id = :lid", {"lid": data["log_id"]})[0]
        self.assertIsNone(db_log["cycle_day"])

    def test_cycle_day_calculated_from_most_recent_cycle_start(self):
        """When cycles exist, cycle_day is calculated as (log_date - start_date) + 1."""
        execute_write(
            """
            INSERT INTO cycles (cycle_id, user_id, start_date, cycle_length, period_length, irregular)
            VALUES ('cyc_recent', :uid, '2026-10-10', 28, 5, FALSE)
            """,
            {"uid": self.user_a_id}
        )
        res = self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": "2026-10-14", "mood": "Happy"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        # Oct 10 to Oct 14: (14 - 10) + 1 = 5
        self.assertEqual(data["cycle_day"], 5)

    # ------------------------------------------------------------------
    # 4. Authentication, Privacy & Ownership Scoping
    # ------------------------------------------------------------------

    def test_unauthenticated_requests_rejected_401(self):
        """Endpoints reject unauthenticated requests with 401."""
        res_post = self.client.post('/api/logs', json={"date": "2026-10-24"})
        self.assertEqual(res_post.status_code, 401)

        res_get = self.client.get('/api/logs')
        self.assertEqual(res_get.status_code, 401)

        res_del = self.client.delete('/api/logs/log_dummy')
        self.assertEqual(res_del.status_code, 401)

    def test_user_id_in_payload_cannot_spoof_ownership(self):
        """Passing another user's user_id in the body is ignored; log is bound to authenticated user."""
        res = self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": "2026-10-24", "user_id": self.user_b_id, "mood": "Calm"}
        )
        self.assertEqual(res.status_code, 200)
        log_id = res.get_json()["log_id"]

        db_log = execute_query("SELECT user_id FROM wellness_logs WHERE log_id = :lid", {"lid": log_id})[0]
        self.assertEqual(db_log["user_id"], self.user_a_id)
        self.assertNotEqual(db_log["user_id"], self.user_b_id)

    def test_cross_user_log_deletion_prevented_403(self):
        """User B cannot delete User A's logs."""
        # Create a log for User A
        res = self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": "2026-10-24", "mood": "Calm", "notes": "User A secret note"}
        )
        log_id = res.get_json()["log_id"]

        # User B attempts to delete User A's log
        res_del = self.client.delete(f'/api/logs/{log_id}', headers={"Authorization": f"Bearer {self.token_b}"})
        self.assertEqual(res_del.status_code, 403)
        self.assertIn("Unauthorized", res_del.get_json().get("error", ""))

        # User A CAN delete their own log
        res_own_del = self.client.delete(f'/api/logs/{log_id}', headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(res_own_del.status_code, 200)
        self.assertIn("deleted successfully", res_own_del.get_json().get("message", ""))

        # Verify DB records deleted
        remaining_logs = execute_query("SELECT * FROM wellness_logs WHERE log_id = :lid", {"lid": log_id})
        self.assertEqual(len(remaining_logs), 0)

    def test_get_logs_scoped_to_current_user_and_supports_date_filters(self):
        """GET /api/logs returns only authenticated user's logs and supports date filtering."""
        self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": "2026-10-15", "mood": "Happy"}
        )
        self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"date": "2026-10-20", "mood": "Calm"}
        )
        self.client.post(
            '/api/logs',
            headers={"Authorization": f"Bearer {self.token_b}"},
            json={"date": "2026-10-20", "mood": "Anxious"}
        )

        # Scoping check: User A receives only their 2 logs
        res_a = self.client.get('/api/logs', headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(res_a.status_code, 200)
        logs_a = res_a.get_json()
        self.assertEqual(len(logs_a), 2)
        self.assertTrue(all(log["user_id"] == self.user_a_id for log in logs_a))

        # Filter check: date >= 2026-10-18
        res_filter = self.client.get('/api/logs?start_date=2026-10-18', headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(res_filter.status_code, 200)
        filtered = res_filter.get_json()
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["date"], "2026-10-20")


if __name__ == '__main__':
    unittest.main()
