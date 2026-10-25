import os
import sys
import unittest

# Ensure backend directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app


class TestHealthAndAppSmoke(unittest.TestCase):
    """
    Stage 1 Baseline Smoke Tests:
    Verifies that the Flask application initializes properly,
    the health check endpoint responds correctly, and unknown endpoints return 404.
    """

    @classmethod
    def setUpClass(cls):
        from db import init_test_database
        init_test_database()

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_app_instance_exists(self):
        """Verifies that the Flask app instance is created and configured."""
        self.assertIsNotNone(app)
        self.assertTrue(app.config['TESTING'])

    def test_health_check_endpoint(self):
        """Verifies that GET /api/health returns 200 with expected JSON payload."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("message"), "OvaCare backend is running")

    def test_unknown_endpoint_returns_404(self):
        """Verifies that unmapped endpoints return 404 Not Found."""
        response = self.client.get('/api/unknown_nonexistent_route')
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
