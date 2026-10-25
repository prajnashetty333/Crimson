"""
Verification tests for database safety and test isolation in OvaCare.
Confirms that:
1. Production database backend/ovacare.db is never touched by tests.
2. Automated tests run against an isolated test database.
3. Protected database path cannot be configured as the test database.
4. Writes to the test database do not leak into or modify the production database.
"""
import os
import sys
import sqlite3
import unittest
from unittest.mock import patch

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import db
from db import (
    PROTECTED_PROD_DB_PATH,
    DEFAULT_TEST_DB_PATH,
    is_test_mode,
    resolve_database_url,
    init_test_database,
    execute_query,
    execute_write,
    get_active_db_path,
    is_active_db_protected,
)


class TestDatabaseIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Record baseline state of the production database
        cls.prod_path = PROTECTED_PROD_DB_PATH
        cls.assertTrue(os.path.exists(cls.prod_path), "Production database must exist")
        cls.baseline_size = os.path.getsize(cls.prod_path)

        conn = sqlite3.connect(f"file:{cls.prod_path}?mode=ro", uri=True)
        cur = conn.cursor()
        cls.baseline_users = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        cls.baseline_cycles = cur.execute("SELECT COUNT(*) FROM cycles").fetchone()[0]
        cls.baseline_logs = cur.execute("SELECT COUNT(*) FROM wellness_logs").fetchone()[0]
        conn.close()

    def test_production_path_is_accurate(self):
        """Verifies that the protected database path points to backend/ovacare.db."""
        expected = os.path.abspath(os.path.join(BACKEND_DIR, "ovacare.db"))
        self.assertEqual(PROTECTED_PROD_DB_PATH, expected)

    def test_default_dev_resolution_is_production_db(self):
        """When not in test mode, resolve_database_url falls back to the protected production database."""
        with patch.dict(os.environ, {"OVACARE_TEST_MODE": "", "TEST_DATABASE_PATH": "", "OVACARE_TEST_DB": ""}, clear=False):
            url = resolve_database_url()
            self.assertEqual(url, f"sqlite:///{PROTECTED_PROD_DB_PATH}")

    def test_test_mode_resolves_to_test_database(self):
        """When in test mode, resolve_database_url resolves to DEFAULT_TEST_DB_PATH."""
        with patch.dict(os.environ, {"OVACARE_TEST_MODE": "true"}, clear=False):
            url = resolve_database_url()
            self.assertEqual(url, f"sqlite:///{DEFAULT_TEST_DB_PATH}")
            self.assertNotEqual(url, f"sqlite:///{PROTECTED_PROD_DB_PATH}")

    def test_init_test_database_rejects_protected_prod_db(self):
        """Attempting to initialize the test database with the protected production path must raise RuntimeError."""
        with self.assertRaises(RuntimeError) as ctx:
            init_test_database(PROTECTED_PROD_DB_PATH)
        self.assertIn("CRITICAL DATABASE SAFETY VIOLATION", str(ctx.exception))

    def test_write_guard_blocks_writes_on_protected_db_during_test_mode(self):
        """execute_write must abort immediately if test mode is active while connected to production db."""
        # Save current state
        original_url = db.DATABASE_URL
        original_engine = db.engine
        try:
            db.DATABASE_URL = f"sqlite:///{PROTECTED_PROD_DB_PATH}"
            db.engine = original_engine
            with patch.dict(os.environ, {"OVACARE_TEST_MODE": "true"}):
                self.assertTrue(is_test_mode())
                self.assertTrue(is_active_db_protected())
                with self.assertRaises(RuntimeError) as ctx:
                    execute_write("DELETE FROM users WHERE user_id = 'impossible_dummy'")
                self.assertIn("CRITICAL DATABASE SAFETY VIOLATION", str(ctx.exception))
        finally:
            db.DATABASE_URL = original_url
            db.engine = original_engine

    def test_test_database_isolation_does_not_mutate_production_db(self):
        """Operations in the test database must not affect production database records."""
        # Initialize isolated test database
        active_test_path = init_test_database()
        self.assertNotEqual(active_test_path, PROTECTED_PROD_DB_PATH)
        self.assertEqual(get_active_db_path(), active_test_path)

        dummy_uid = "usr_isolation_probe_999"
        execute_write("DELETE FROM users WHERE user_id = :uid", {"uid": dummy_uid})
        execute_write(
            """
            INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos)
            VALUES (:uid, 'Isolation Probe', 'probe@test.local', 'hash', 25, 'Active', 0)
            """,
            {"uid": dummy_uid}
        )

        # Record exists in test database
        test_records = execute_query("SELECT user_id FROM users WHERE user_id = :uid", {"uid": dummy_uid})
        self.assertEqual(len(test_records), 1)

        # Record MUST NOT exist in production database
        conn = sqlite3.connect(f"file:{PROTECTED_PROD_DB_PATH}?mode=ro", uri=True)
        cur = conn.cursor()
        prod_probe = cur.execute("SELECT user_id FROM users WHERE user_id = ?", (dummy_uid,)).fetchall()
        prod_users = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        prod_cycles = cur.execute("SELECT COUNT(*) FROM cycles").fetchone()[0]
        prod_logs = cur.execute("SELECT COUNT(*) FROM wellness_logs").fetchone()[0]
        conn.close()

        self.assertEqual(len(prod_probe), 0, "Probe user leaked into production database!")
        self.assertEqual(prod_users, self.baseline_users, "Production user count mutated!")
        self.assertEqual(prod_cycles, self.baseline_cycles, "Production cycle count mutated!")
        self.assertEqual(prod_logs, self.baseline_logs, "Production log count mutated!")

        # Production file size must be unchanged
        current_prod_size = os.path.getsize(PROTECTED_PROD_DB_PATH)
        self.assertEqual(current_prod_size, self.baseline_size, "Production database file size changed!")

        # Clean up probe from test database
        execute_write("DELETE FROM users WHERE user_id = :uid", {"uid": dummy_uid})


if __name__ == '__main__':
    unittest.main()
