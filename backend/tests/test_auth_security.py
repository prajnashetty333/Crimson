import os
import sys
import unittest
from unittest.mock import patch
from itsdangerous import URLSafeTimedSerializer

# Ensure backend directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import (
    app,
    load_secret_key,
    is_development_mode,
    is_production_mode,
    generate_auth_token,
    verify_auth_token,
    admin_required,
    DEV_FALLBACK_SECRET,
    auth_serializer,
)


class TestSecretKeyConfiguration(unittest.TestCase):
    """
    Verifies SECRET_KEY loading under the explicit-development-opt-in model.

    The dev fallback is ONLY allowed when APP_ENV=development is set explicitly.
    Any unspecified environment must enforce the same strict requirements as production.
    """

    # ------------------------------------------------------------------
    # Scenario 1: Explicit development mode — no production secret needed
    # ------------------------------------------------------------------

    def test_explicit_dev_mode_allows_fallback_when_no_secret_set(self):
        """APP_ENV=development with no SECRET_KEY must use the dev fallback (not raise)."""
        with patch.dict(os.environ, {"APP_ENV": "development"}, clear=True):
            self.assertTrue(is_development_mode())
            key = load_secret_key()
            self.assertEqual(key, DEV_FALLBACK_SECRET)

    def test_explicit_dev_mode_uses_provided_secret(self):
        """APP_ENV=development with a custom SECRET_KEY must use that key."""
        with patch.dict(os.environ, {"APP_ENV": "development", "SECRET_KEY": "my-local-test-secret"}, clear=True):
            key = load_secret_key()
            self.assertEqual(key, "my-local-test-secret")

    # ------------------------------------------------------------------
    # Scenario 2: Production mode — missing or weak secret must be rejected
    # ------------------------------------------------------------------

    def test_production_mode_missing_secret_fails_startup(self):
        """APP_ENV=production with no SECRET_KEY must abort startup with RuntimeError."""
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=True):
            self.assertTrue(is_production_mode())
            with self.assertRaises(RuntimeError) as ctx:
                load_secret_key()
            self.assertIn("SECRET_KEY environment variable is required", str(ctx.exception))

    def test_production_mode_empty_secret_fails_startup(self):
        """APP_ENV=production with whitespace-only SECRET_KEY must abort startup."""
        with patch.dict(os.environ, {"APP_ENV": "production", "SECRET_KEY": "   "}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                load_secret_key()
            self.assertIn("SECRET_KEY environment variable is required", str(ctx.exception))

    def test_production_mode_dev_fallback_secret_rejected(self):
        """APP_ENV=production using the dev fallback value must be rejected."""
        with patch.dict(os.environ, {"APP_ENV": "production", "SECRET_KEY": DEV_FALLBACK_SECRET}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                load_secret_key()
            self.assertIn("Predictable or placeholder SECRET_KEY detected", str(ctx.exception))

    def test_production_mode_env_example_placeholder_rejected(self):
        """APP_ENV=production using the .env.example placeholder must be rejected."""
        placeholder = "replace-with-a-secure-random-secret-key-in-production"
        with patch.dict(os.environ, {"APP_ENV": "production", "SECRET_KEY": placeholder}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                load_secret_key()
            self.assertIn("Predictable or placeholder SECRET_KEY detected", str(ctx.exception))

    def test_production_mode_short_secret_rejected(self):
        """APP_ENV=production with a key shorter than 32 characters must be rejected."""
        short_key = "too-short"
        with patch.dict(os.environ, {"APP_ENV": "production", "SECRET_KEY": short_key}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                load_secret_key()
            self.assertIn("SECRET_KEY is too weak", str(ctx.exception))

    # ------------------------------------------------------------------
    # Scenario 3: Unspecified environment — must NOT silently use dev fallback
    # ------------------------------------------------------------------

    def test_unspecified_env_no_secret_fails_startup(self):
        """With no APP_ENV and no SECRET_KEY, startup must fail (not silently use dev fallback)."""
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_development_mode(), "Unspecified env must not be treated as development")
            self.assertTrue(is_production_mode(), "Unspecified env must be treated as production-like")
            with self.assertRaises(RuntimeError) as ctx:
                load_secret_key()
            self.assertIn("SECRET_KEY environment variable is required", str(ctx.exception))

    def test_unspecified_env_with_dev_fallback_value_rejected(self):
        """Unspecified env with the known dev fallback value as SECRET_KEY must be rejected."""
        with patch.dict(os.environ, {"SECRET_KEY": DEV_FALLBACK_SECRET}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                load_secret_key()
            self.assertIn("Predictable or placeholder SECRET_KEY detected", str(ctx.exception))

    def test_unspecified_env_short_secret_rejected(self):
        """Unspecified env with a short SECRET_KEY must be rejected."""
        with patch.dict(os.environ, {"SECRET_KEY": "weakkey"}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                load_secret_key()
            self.assertIn("SECRET_KEY is too weak", str(ctx.exception))

    # ------------------------------------------------------------------
    # Scenario 4: Valid production secret is accepted
    # ------------------------------------------------------------------

    def test_production_strong_secret_accepted(self):
        """APP_ENV=production with a 64-char hex secret must be accepted."""
        strong_key = "c8f12a9e40b719d3f56e01289456abcedf0123456789abcdef0123456789abcd"
        with patch.dict(os.environ, {"APP_ENV": "production", "SECRET_KEY": strong_key}, clear=True):
            key = load_secret_key()
            self.assertEqual(key, strong_key)

    def test_unspecified_env_strong_secret_accepted(self):
        """Unspecified APP_ENV with a strong SECRET_KEY must be accepted (treated as production-like)."""
        strong_key = "c8f12a9e40b719d3f56e01289456abcedf0123456789abcdef0123456789abcd"
        with patch.dict(os.environ, {"SECRET_KEY": strong_key}, clear=True):
            key = load_secret_key()
            self.assertEqual(key, strong_key)


class TestTokenSigningAndVerification(unittest.TestCase):
    """Verifies token generation, signature verification, expiration, and tampering rejection."""

    def test_generate_and_verify_valid_token(self):
        """A valid token must verify and decode the exact user_id."""
        user_id = "usr_0a1d06594447"
        token = generate_auth_token(user_id)
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 20)

        verified_id = verify_auth_token(token)
        self.assertEqual(verified_id, user_id)

    def test_verify_tampered_token_payload_rejected(self):
        """Tampering with characters in the token payload must be rejected."""
        token = generate_auth_token("usr_patient_123")
        # Tamper with the start of the token
        tampered_token = ("b" if token[0] != "b" else "a") + token[1:]
        self.assertIsNone(verify_auth_token(tampered_token))

    def test_verify_tampered_token_signature_rejected(self):
        """Tampering with characters in the token signature must be rejected."""
        token = generate_auth_token("usr_patient_123")
        # Tamper with the end of the token
        tampered_token = token[:-2] + ("xx" if token[-2:] != "xx" else "yy")
        self.assertIsNone(verify_auth_token(tampered_token))

    def test_verify_token_signed_with_different_key_rejected(self):
        """A token signed with an unauthorized secret key must be rejected."""
        foreign_serializer = URLSafeTimedSerializer("unauthorized-foreign-attacker-secret-key-999", salt="ovacare-auth-token-v1")
        forged_token = foreign_serializer.dumps({"user_id": "usr_patient_123"})
        self.assertIsNone(verify_auth_token(forged_token))

    def test_verify_token_signed_with_different_salt_rejected(self):
        """A token signed with a different salt must be rejected."""
        foreign_serializer = URLSafeTimedSerializer(DEV_FALLBACK_SECRET, salt="wrong-salt")
        forged_token = foreign_serializer.dumps({"user_id": "usr_patient_123"})
        self.assertIsNone(verify_auth_token(forged_token))

    def test_verify_invalid_and_malformed_tokens_rejected(self):
        """Malformed, empty, or non-string tokens must return None without raising uncaught exceptions."""
        self.assertIsNone(verify_auth_token(""))
        self.assertIsNone(verify_auth_token("not-a-token"))
        self.assertIsNone(verify_auth_token("header.payload.signature"))
        self.assertIsNone(verify_auth_token(None))
        self.assertIsNone(verify_auth_token(12345))

    def test_verify_token_expiration_enforced(self):
        """Expired tokens must be strictly rejected (returns None)."""
        token = generate_auth_token("usr_patient_123")
        # Verify with max_age=-1 to simulate an expired token
        self.assertIsNone(verify_auth_token(token, max_age=-1))


class TestAuthenticationMiddleware(unittest.TestCase):
    """Verifies @token_required decorator, header extraction, and endpoint protection."""

    def setUp(self):
        from db import init_test_database, execute_write
        init_test_database()
        app.config['TESTING'] = True
        self.client = app.test_client()
        execute_write(
            "INSERT OR IGNORE INTO users (user_id, username, email, password, age, lifestyle, has_pcos) "
            "VALUES (:uid, :name, :email, :pwd, 25, 'Active', 0)",
            {"uid": "usr_demo_patient", "name": "Test Patient", "email": "test_patient@example.com", "pwd": "hash"}
        )

    def test_protected_endpoint_missing_auth_header_returns_401(self):
        """Requests without Authorization header must be rejected with 401."""
        response = self.client.get('/api/cycles')
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn("Authorization token required", data.get("error", ""))

    def test_protected_endpoint_malformed_auth_header_returns_401(self):
        """Requests with non-Bearer Authorization headers must be rejected with 401."""
        response = self.client.get('/api/cycles', headers={"Authorization": "Basic dXNlcjpwYXNz"})
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn("Authorization token required", data.get("error", ""))

    def test_protected_endpoint_invalid_token_returns_401(self):
        """Requests with an invalid token string must return 401."""
        response = self.client.get('/api/cycles', headers={"Authorization": "Bearer invalid.garbage.token"})
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn("Invalid or expired token", data.get("error", ""))

    def test_protected_endpoint_tampered_token_returns_401(self):
        """Requests with a tampered token must return 401."""
        valid_token = generate_auth_token("usr_demo_patient")
        tampered = valid_token[:-4] + "zzzz"
        response = self.client.get('/api/cycles', headers={"Authorization": f"Bearer {tampered}"})
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn("Invalid or expired token", data.get("error", ""))

    def test_protected_endpoint_expired_token_returns_401(self):
        """Requests with an expired token must return 401 Invalid or expired token."""
        valid_token = generate_auth_token("usr_demo_patient")
        with patch('app.DEFAULT_TOKEN_MAX_AGE', -1):
            response = self.client.get('/api/cycles', headers={"Authorization": f"Bearer {valid_token}"})
            self.assertEqual(response.status_code, 401)
            data = response.get_json()
            self.assertIn("Invalid or expired token", data.get("error", ""))

    def test_protected_endpoint_valid_token_for_existing_user_succeeds(self):
        """Requests with a valid token for an existing user must succeed (200 OK)."""
        valid_token = generate_auth_token("usr_demo_patient")
        response = self.client.get('/api/cycles', headers={"Authorization": f"Bearer {valid_token}"})
        self.assertEqual(response.status_code, 200)

    def test_protected_endpoint_valid_token_for_nonexistent_user_returns_401(self):
        """A valid token for a user ID that does not exist in the database must return 401."""
        token_ghost = generate_auth_token("usr_non_existent_ghost_99999")
        response = self.client.get('/api/cycles', headers={"Authorization": f"Bearer {token_ghost}"})
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn("User account no longer exists", data.get("error", ""))

    def test_cross_user_profile_access_forbidden_403(self):
        """Authenticated user cannot view another user's profile (ownership enforcement)."""
        valid_token = generate_auth_token("usr_demo_patient")
        # Attempt to access another user's profile
        other_user_id = "usr_other_patient_999"
        response = self.client.get(f'/api/users/{other_user_id}', headers={"Authorization": f"Bearer {valid_token}"})
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertIn("Forbidden", data.get("error", ""))


class TestAdminEndpointAuthorization(unittest.TestCase):
    """
    Verifies role-based access control on /api/admin/stats:
    - Missing, invalid, or expired tokens return 401.
    - Standard authenticated users (role='member') return 403 Forbidden.
    - Admin users (role='admin') receive 200 OK with expected platform metrics.
    """

    @classmethod
    def setUpClass(cls):
        from db import init_test_database, execute_write
        init_test_database()
        app.config['TESTING'] = True
        cls.client = app.test_client()

        cls.member_id = "usr_test_member_auth"
        cls.admin_id = "usr_test_admin_auth"

        # Ensure clean state in isolated test database
        execute_write("DELETE FROM users WHERE user_id IN (:mid, :aid)", {"mid": cls.member_id, "aid": cls.admin_id})

        execute_write(
            "INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos, role) "
            "VALUES (:uid, :name, :email, :pwd, 24, 'Active', 0, 'member')",
            {"uid": cls.member_id, "name": "Standard Member", "email": "member_auth@test.local", "pwd": "hash"}
        )
        execute_write(
            "INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos, role) "
            "VALUES (:uid, :name, :email, :pwd, 35, 'Moderate', 0, 'admin')",
            {"uid": cls.admin_id, "name": "Administrator", "email": "admin_auth@test.local", "pwd": "hash"}
        )

        cls.member_token = generate_auth_token(cls.member_id)
        cls.admin_token = generate_auth_token(cls.admin_id)

    @classmethod
    def tearDownClass(cls):
        from db import execute_write
        execute_write("DELETE FROM users WHERE user_id IN (:mid, :aid)", {"mid": cls.member_id, "aid": cls.admin_id})

    def test_admin_stats_unauthenticated_returns_401(self):
        """Unauthenticated GET /api/admin/stats must return 401 Unauthorized."""
        response = self.client.get('/api/admin/stats')
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn("Authorization token required", data.get("error", ""))

    def test_admin_stats_invalid_token_returns_401(self):
        """GET /api/admin/stats with an invalid token string must return 401."""
        response = self.client.get('/api/admin/stats', headers={"Authorization": "Bearer invalid.token.value"})
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn("Invalid or expired token", data.get("error", ""))

    def test_admin_stats_expired_token_returns_401(self):
        """GET /api/admin/stats with an expired admin token must return 401."""
        with patch('app.DEFAULT_TOKEN_MAX_AGE', -1):
            response = self.client.get('/api/admin/stats', headers={"Authorization": f"Bearer {self.admin_token}"})
            self.assertEqual(response.status_code, 401)
            data = response.get_json()
            self.assertIn("Invalid or expired token", data.get("error", ""))

    def test_admin_stats_standard_user_forbidden_403(self):
        """Authenticated non-admin user must be rejected with 403 Forbidden."""
        response = self.client.get('/api/admin/stats', headers={"Authorization": f"Bearer {self.member_token}"})
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertIn("Administrator privileges required", data.get("error", ""))

    def test_admin_stats_valid_admin_access_allowed_200(self):
        """Authenticated admin user must receive 200 OK and aggregate statistics."""
        response = self.client.get('/api/admin/stats', headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("total_users", data)
        self.assertIn("total_cycles", data)
        self.assertIn("total_logs", data)
        self.assertIn("average_cycle_length", data)
        self.assertIn("pcos_ratio_percentage", data)
        self.assertIn("pcos_cycle_analysis", data)
        self.assertIn("activity_cohorts", data)


if __name__ == '__main__':
    unittest.main()
