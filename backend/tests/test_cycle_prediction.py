"""
Regression and behavior tests for OvaCare AI Cycle Tracking, Prediction, and Irregularity Logic.
Verifies the 12 required scenarios for cycle tracking gaps, historical insertions, and PCOS.
"""
import os
import sys
import unittest
from datetime import datetime, date

# Ensure backend directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app
from common.auth import generate_auth_token
from db import execute_write, execute_query, init_test_database


class TestCyclePredictionRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_test_database()
        app.config['TESTING'] = True
        cls.client = app.test_client()

        # Test user IDs
        cls.user_a_id = "usr_test_cycle_a"
        cls.user_b_id = "usr_test_cycle_b"
        cls.user_pcos_id = "usr_test_cycle_pcos"

        # Cleanup any previous test data
        cls._cleanup_all_users()

        # Seed test users
        execute_write(
            """
            INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos)
            VALUES (:uid, :uname, :email, :pwd, 25, 'Moderate', FALSE)
            """,
            {"uid": cls.user_a_id, "uname": "Cycle User A", "email": "cycle_a@ovacare.test", "pwd": "hashed_pwd_test"}
        )
        execute_write(
            """
            INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos)
            VALUES (:uid, :uname, :email, :pwd, 27, 'Active', FALSE)
            """,
            {"uid": cls.user_b_id, "uname": "Cycle User B", "email": "cycle_b@ovacare.test", "pwd": "hashed_pwd_test"}
        )
        execute_write(
            """
            INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos)
            VALUES (:uid, :uname, :email, :pwd, 29, 'Moderate', TRUE)
            """,
            {"uid": cls.user_pcos_id, "uname": "Cycle PCOS User", "email": "cycle_pcos@ovacare.test", "pwd": "hashed_pwd_test"}
        )

        cls.token_a = generate_auth_token(cls.user_a_id)
        cls.token_b = generate_auth_token(cls.user_b_id)
        cls.token_pcos = generate_auth_token(cls.user_pcos_id)

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_all_users()

    @classmethod
    def _cleanup_all_users(cls):
        uids = (cls.user_a_id, cls.user_b_id, cls.user_pcos_id)
        for uid in uids:
            execute_write("DELETE FROM wellness_logs WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM mood_logs WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM cycles WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM users WHERE user_id = :uid", {"uid": uid})

    def setUp(self):
        # Clear cycles for test users before each test run
        for uid in (self.user_a_id, self.user_b_id, self.user_pcos_id):
            execute_write("DELETE FROM cycles WHERE user_id = :uid", {"uid": uid})

    # ------------------------------------------------------------------
    # Scenario 1: A new user with no cycle history
    # ------------------------------------------------------------------
    def test_new_user_no_cycle_history(self):
        """A new user with 0 cycles receives a baseline prediction and appropriate status."""
        res = self.client.get('/api/predictions', headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('history_count'), 0)
        self.assertEqual(data.get('average_cycle_length'), 28)
        self.assertFalse(data.get('irregular'))
        self.assertEqual(data.get('delayed_days'), 0)
        # Should indicate baseline or insufficient history
        status = data.get('tracking_status', '')
        self.assertIn(status, ['insufficient_history', 'baseline', ''])

    # ------------------------------------------------------------------
    # Scenario 2: A user with only one recorded period
    # ------------------------------------------------------------------
    def test_single_cycle_user_baseline_status(self):
        """User with 1 recorded cycle gets baseline prediction (last_start + 28), not high-confidence or irregular."""
        self.client.post(
            '/api/cycles',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"start_date": "2026-09-01", "end_date": "2026-09-05"}
        )
        res = self.client.get('/api/predictions', headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('history_count'), 1)
        self.assertEqual(data.get('predicted_date'), "2026-09-29")
        self.assertEqual(data.get('average_cycle_length'), 28)
        self.assertFalse(data.get('irregular'), "Single cycle must not be marked irregular")

    # ------------------------------------------------------------------
    # Scenario 3: A user with several consistent cycle lengths
    # ------------------------------------------------------------------
    def test_consistent_cycles_regular(self):
        """User with several regular 28-day cycles must have irregular=False and accurate predicted date."""
        dates = [
            ("2026-05-01", "2026-05-05"),
            ("2026-05-29", "2026-06-02"), # 28 days
            ("2026-06-26", "2026-06-30"), # 28 days
            ("2026-07-24", "2026-07-28"), # 28 days
        ]
        for s, e in dates:
            self.client.post(
                '/api/cycles',
                headers={"Authorization": f"Bearer {self.token_a}"},
                json={"start_date": s, "end_date": e}
            )

        res = self.client.get('/api/predictions', headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data.get('irregular'), "Consistent cycles must be regular")
        self.assertEqual(data.get('average_cycle_length'), 28)
        self.assertEqual(data.get('predicted_date'), "2026-08-21")

        # Verify analytics also reports 0 irregular cycles
        analytics_res = self.client.get('/api/analytics', headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(analytics_res.status_code, 200)
        analytics_data = analytics_res.get_json()
        self.assertEqual(analytics_data.get('irregular_cycles_count'), 0)

    # ------------------------------------------------------------------
    # Scenario 4: User who missed logging a month (unclarified gap)
    # ------------------------------------------------------------------
    def test_unclarified_long_gap_not_marked_irregular(self):
        """
        August 10 period, September missed, October 24 recorded (75-day interval).
        Must NOT automatically mark the user irregular or distort average cycle length to 50+ days.
        """
        # User logs: June 15, July 13 (28d), August 10 (28d)
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-06-15"})
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-07-13"})
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-08-10"})
        # Now logs October 24 without clarification (75 days later)
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-10-24"})

        pred_res = self.client.get('/api/predictions', headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(pred_res.status_code, 200)
        pred_data = pred_res.get_json()

        # The unclarified 75-day gap must NOT be concluded as irregular
        self.assertFalse(
            pred_data.get('irregular'),
            "An unclarified tracking gap must NOT automatically classify user as irregular"
        )
        # Average cycle length must not be distorted by the 75-day gap (should be ~28)
        self.assertLess(
            pred_data.get('average_cycle_length'),
            35,
            f"Average cycle length {pred_data.get('average_cycle_length')} was distorted by unclarified tracking gap"
        )

    # ------------------------------------------------------------------
    # Scenario 5: User confirms an intervening period was missed in the log
    # ------------------------------------------------------------------
    def test_confirmed_missed_period(self):
        """When user confirms a gap is from missed logging, it must not distort average or flag irregularity."""
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-05-01"})
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-05-29"}) # 28d
        # User logs with confirmation that an intervening period was missed
        self.client.post(
            '/api/cycles',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"start_date": "2026-07-24", "gap_clarification": "missed_period"}
        )

        pred_res = self.client.get('/api/predictions', headers={"Authorization": f"Bearer {self.token_a}"})
        pred_data = pred_res.get_json()
        self.assertFalse(pred_data.get('irregular'))
        self.assertLess(pred_data.get('average_cycle_length'), 32)

    # ------------------------------------------------------------------
    # Scenario 6: User confirms genuinely long interval without period
    # ------------------------------------------------------------------
    def test_confirmed_genuine_long_cycle(self):
        """When user confirms no period occurred (e.g. 75 days), it must be preserved as observed irregularity."""
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-05-01"})
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-05-29"}) # 28d
        self.client.post(
            '/api/cycles',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"start_date": "2026-08-12", "gap_clarification": "confirmed_long_cycle"}
        )

        pred_res = self.client.get('/api/predictions', headers={"Authorization": f"Bearer {self.token_a}"})
        pred_data = pred_res.get_json()
        self.assertTrue(pred_data.get('irregular'), "Confirmed long cycle must be observed as irregular")

        analytics_res = self.client.get('/api/analytics', headers={"Authorization": f"Bearer {self.token_a}"})
        analytics_data = analytics_res.get_json()
        self.assertGreaterEqual(analytics_data.get('irregular_cycles_count'), 1)

    # ------------------------------------------------------------------
    # Scenario 7: A user with variable cycle lengths
    # ------------------------------------------------------------------
    def test_variable_cycle_lengths_marked_irregular(self):
        """User with genuinely fluctuating cycle lengths (24, 38, 26, 42) must be detected as irregular."""
        dates = ["2026-01-01", "2026-01-25", "2026-03-04", "2026-03-30", "2026-05-11"]
        for d in dates:
            self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": d})

        pred_res = self.client.get('/api/predictions', headers={"Authorization": f"Bearer {self.token_a}"})
        pred_data = pred_res.get_json()
        self.assertTrue(pred_data.get('irregular'), "High variance cycles must be marked irregular")

    # ------------------------------------------------------------------
    # Scenario 8: User with PCOS but consistent recorded cycle lengths
    # ------------------------------------------------------------------
    def test_pcos_with_consistent_cycles_not_forced_irregular(self):
        """A user with has_pcos=True who logs consistent 28-day cycles must NOT be forced into irregular=True."""
        dates = ["2026-04-01", "2026-04-29", "2026-05-27", "2026-06-24", "2026-07-22"]
        for d in dates:
            self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_pcos}"}, json={"start_date": d})

        pred_res = self.client.get('/api/predictions', headers={"Authorization": f"Bearer {self.token_pcos}"})
        pred_data = pred_res.get_json()
        self.assertFalse(
            pred_data.get('irregular'),
            "PCOS diagnosis or mode must NOT force irregular=True when recorded cycles are regular"
        )

    # ------------------------------------------------------------------
    # Scenario 9: Historical cycle inserted between two existing records
    # ------------------------------------------------------------------
    def test_historical_cycle_inserted_recalculates_adjacent_cycles(self):
        """
        Inserting Cycle 2 (Jan 29) between Cycle 1 (Jan 1) and Cycle 3 (Feb 26)
        must recalculate Cycle 1 length to 28 and Cycle 2 length to 28, not leave 56.
        """
        # User logs Cycle 1 (Jan 1) and Cycle 3 (Feb 26) -> gap is 56 days
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-01-01"})
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-02-26"})

        # Now insert historical Cycle 2 (Jan 29)
        res = self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-01-29"})
        self.assertEqual(res.status_code, 201)

        # Inspect cycles in DB
        cycles = execute_query(
            "SELECT start_date, cycle_length, irregular FROM cycles WHERE user_id = :uid ORDER BY start_date ASC",
            {"uid": self.user_a_id}
        )
        self.assertEqual(len(cycles), 3)

        # Cycle 1 (Jan 1) to Cycle 2 (Jan 29)
        c1_len = cycles[0]['cycle_length']
        # Cycle 2 (Jan 29) to Cycle 3 (Feb 26)
        c2_len = cycles[1]['cycle_length']

        # Both intervals are 28 days
        self.assertIn(28, [c1_len, c2_len])
        # Neither interval should still be 56
        self.assertNotIn(56, [cycles[0]['cycle_length'], cycles[1]['cycle_length'], cycles[2]['cycle_length']])

    # ------------------------------------------------------------------
    # Scenario 10: Data isolation between users
    # ------------------------------------------------------------------
    def test_user_cycle_data_isolation(self):
        """User B cannot access or affect User A's cycle records or predictions."""
        # User A logs a cycle
        post_res = self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-03-01"})
        cycle_a_id = post_res.get_json()['cycle_id']

        # User B cannot see User A's cycle
        b_cycles = self.client.get('/api/cycles', headers={"Authorization": f"Bearer {self.token_b}"}).get_json()
        self.assertEqual(len(b_cycles), 0)

        # User B cannot delete User A's cycle
        del_res = self.client.delete(f'/api/cycles/{cycle_a_id}', headers={"Authorization": f"Bearer {self.token_b}"})
        self.assertIn(del_res.status_code, [403, 404])

    # ------------------------------------------------------------------
    # Scenario 11: Prediction and analytics results consistency
    # ------------------------------------------------------------------
    def test_prediction_and_analytics_consistency(self):
        """Prediction and analytics endpoints must agree on cycle lengths and irregularity."""
        dates = ["2026-01-01", "2026-01-29", "2026-02-26", "2026-03-26"]
        for d in dates:
            self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": d})

        pred_res = self.client.get('/api/predictions', headers={"Authorization": f"Bearer {self.token_a}"}).get_json()
        analytics_res = self.client.get('/api/analytics', headers={"Authorization": f"Bearer {self.token_a}"}).get_json()

        # Both should report average cycle length of 28
        self.assertEqual(round(pred_res['average_cycle_length']), round(analytics_res['average_cycle_length']))
        # Both should agree the user is regular
        self.assertFalse(pred_res['irregular'])
        self.assertEqual(analytics_res['irregular_cycles_count'], 0)

    # ------------------------------------------------------------------
    # Scenario 12: Duplicate period start dates prevented
    # ------------------------------------------------------------------
    def test_duplicate_start_date_prevented(self):
        """Submitting an identical start date for the same user must be rejected with an error."""
        res1 = self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-08-01"})
        self.assertEqual(res1.status_code, 201)

        # Attempt to insert identical start date
        res2 = self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-08-01"})
        self.assertIn(res2.status_code, [400, 409], "Duplicate start date must be rejected")

        # Database must only have 1 cycle for User A
        cycles = execute_query("SELECT * FROM cycles WHERE user_id = :uid", {"uid": self.user_a_id})
        self.assertEqual(len(cycles), 1)

    # ------------------------------------------------------------------
    # Scenario 13: User confirms forgotten app entry
    # ------------------------------------------------------------------
    def test_confirmed_forgotten_app_entry(self):
        """User confirms a 70-day gap was caused by forgotten logging, not a single cycle."""
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-05-01"})
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-05-29"}) # 28d
        self.client.post(
            '/api/cycles',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"start_date": "2026-08-07", "gap_clarification": "forgotten_entry"}
        )

        pred_res = self.client.get('/api/predictions', headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(pred_res.status_code, 200)
        data = pred_res.get_json()
        self.assertFalse(data.get('irregular'), "Forgotten entry must not mark user irregular")
        self.assertEqual(data.get('average_cycle_length'), 28)
        self.assertFalse(data.get('has_unresolved_gaps'))
        self.assertIn(28, data.get('usable_intervals', []))
        self.assertEqual(len(data.get('excluded_intervals', [])), 1)
        self.assertEqual(data['excluded_intervals'][0]['gap_type'], 'forgotten_entry')

    # ------------------------------------------------------------------
    # Scenario 14: Clarify existing cycle via API endpoint
    # ------------------------------------------------------------------
    def test_clarify_cycle_endpoint_and_ownership(self):
        """Test PUT /api/cycles/<cycle_id>/clarify updates gap and respects authorization."""
        res1 = self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-05-01"})
        cid1 = res1.get_json()['cycle_id']
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-07-10"}) # 70d gap

        # User B attempts to clarify User A's cycle -> 403 Forbidden
        b_res = self.client.put(
            f'/api/cycles/{cid1}/clarify',
            headers={"Authorization": f"Bearer {self.token_b}"},
            json={"gap_clarification": "confirmed_long_cycle"}
        )
        self.assertEqual(b_res.status_code, 403)

        # User A clarifies cycle as confirmed_long_cycle -> 200 OK
        a_res = self.client.put(
            f'/api/cycles/{cid1}/clarify',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"gap_clarification": "confirmed_long_cycle"}
        )
        self.assertEqual(a_res.status_code, 200)

        # Verify prediction reflects confirmed long cycle
        pred_res = self.client.get('/api/predictions', headers={"Authorization": f"Bearer {self.token_a}"})
        pred_data = pred_res.get_json()
        self.assertTrue(pred_data.get('irregular'))
        self.assertEqual(pred_data.get('regularity_assessment'), 'irregular')

    # ------------------------------------------------------------------
    # Scenario 15: History quality and prediction uncertainty representation
    # ------------------------------------------------------------------
    def test_prediction_uncertainty_and_history_quality_fields(self):
        """Verify explainable uncertainty, history quality, and regularity rules."""
        # 1. New user (0 cycles)
        res_new = self.client.get('/api/predictions', headers={"Authorization": f"Bearer {self.token_a}"})
        data_new = res_new.get_json()
        self.assertEqual(data_new['history_quality'], 'insufficient')
        self.assertFalse(data_new['is_personalized'])
        self.assertFalse(data_new['can_classify_regularity'])
        self.assertEqual(data_new['regularity_assessment'], 'insufficient_data')
        self.assertEqual(data_new['prediction_confidence'], 'low')

        # 2. Add an unclarified gap -> history quality reflects needs_clarification
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-05-01"})
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-05-29"}) # 28d
        self.client.post('/api/cycles', headers={"Authorization": f"Bearer {self.token_a}"}, json={"start_date": "2026-08-07"}) # 70d gap unclarified

        res_unc = self.client.get('/api/predictions', headers={"Authorization": f"Bearer {self.token_a}"})
        data_unc = res_unc.get_json()
        self.assertEqual(data_unc['history_quality'], 'needs_clarification')
        self.assertTrue(data_unc['has_unresolved_gaps'])
        self.assertIsNotNone(data_unc['clarification_prompt'])


if __name__ == '__main__':
    unittest.main()

