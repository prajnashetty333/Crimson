import os
import sys
import unittest
from unittest.mock import patch, MagicMock

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app

class TestCompanionModule(unittest.TestCase):
    """Test suite for OvaCare 3D AI Companion backend integration."""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.env_patcher = patch.dict(os.environ, {
            "CLOUDFLARE_ACCOUNT_ID": "test_mock_account",
            "CLOUDFLARE_API_TOKEN": "test_mock_token"
        })
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    def test_companion_status_endpoint(self):
        """Companion status endpoint returns readiness without exposing secrets."""
        res = self.client.get('/api/companion/status')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("status", data)
        self.assertIn("model", data)
        self.assertIn("features", data)
        # Ensure credentials are not exposed
        self.assertNotIn("CLOUDFLARE_API_TOKEN", data)
        self.assertNotIn("token", str(data).lower())
        self.assertNotIn("account_id", data)

    def test_companion_chat_rejects_empty_message(self):
        """Chat rejects empty or non-string message with 400."""
        res = self.client.post('/api/companion/chat', json={"message": "   "})
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.get_json())

        res2 = self.client.post('/api/companion/chat', json={})
        self.assertEqual(res2.status_code, 400)

        res3 = self.client.post('/api/companion/chat', json={"message": 12345})
        self.assertEqual(res3.status_code, 400)

    def test_companion_chat_rejects_excessive_length(self):
        """Chat rejects message exceeding 1,000 characters."""
        long_msg = "hello " * 250
        res = self.client.post('/api/companion/chat', json={"message": long_msg})
        self.assertEqual(res.status_code, 400)
        self.assertIn("1,000", res.get_json()["error"])

    @patch('companion.requests.post')
    def test_companion_chat_success(self, mock_post):
        """Chat successfully returns companion reply from Cloudflare Workers AI."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "response": "Hello, I am here for you. How are you feeling today?"
            },
            "success": True
        }
        mock_post.return_value = mock_response

        res = self.client.post(
            '/api/companion/chat',
            json={
                "message": "I feel tired and have irregular cycles.",
                "history": [
                    {"role": "user", "content": "Hi"},
                    {"role": "assistant", "content": "Hello! Welcome to OvaCare."}
                ]
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("Hello, I am here for you", data["response"])
        self.assertIn("model", data)

    @patch('companion.requests.post')
    def test_companion_chat_cloudflare_auth_error(self, mock_post):
        """Handles Cloudflare 401 authentication failure with 502."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        res = self.client.post('/api/companion/chat', json={"message": "Can you help?"})
        self.assertEqual(res.status_code, 502)
        self.assertIn("authentication", res.get_json()["error"].lower())

    @patch('companion.requests.post')
    def test_companion_chat_cloudflare_rate_limit(self, mock_post):
        """Handles Cloudflare 429 rate limit with 429."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 429
        mock_post.return_value = mock_response

        res = self.client.post('/api/companion/chat', json={"message": "What is PCOS?"})
        self.assertEqual(res.status_code, 429)
        self.assertIn("rate limit", res.get_json()["error"].lower())

    @patch('companion.requests.post')
    def test_companion_chat_cloudflare_timeout(self, mock_post):
        """Defaults safely to Deterministic Clinical RAG Engine when Cloudflare times out."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Read timeout")

        res = self.client.post('/api/companion/chat', json={"message": "Help with cramps"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("response", data)
        self.assertEqual(data["model"], "OvaCare-Clinical-RAG-v1")
        self.assertTrue(data.get("fallback"))

    @patch('companion.requests.post')
    def test_companion_chat_structured_json_response(self, mock_post):
        """Chat successfully returns structured metadata and verified sources."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "response": '{"answer": "Lifestyle changes are foundational for PCOS.", "confidence": "high", "medical_topic": "lifestyle", "needs_professional_care": false, "urgency": "routine", "emotion": "warm"}'
            },
            "success": True
        }
        mock_post.return_value = mock_response

        res = self.client.post('/api/companion/chat', json={"message": "What lifestyle changes help with PCOS?"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("structured", data)
        self.assertEqual(data["structured"]["confidence"], "high")
        self.assertIsInstance(data["structured"]["sources"], list)
        self.assertGreater(len(data["structured"]["sources"]), 0)
        self.assertIn("url", data["structured"]["sources"][0])

    @patch('companion.requests.post')
    def test_companion_chat_emergency_safety_override(self, mock_post):
        """Emergency red-flag queries trigger server-side emergency urgency override."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "response": "Please get emergency help immediately."
            },
            "success": True
        }
        mock_post.return_value = mock_response

        res = self.client.post('/api/companion/chat', json={"message": "I have sudden severe sharp pelvic pain and feel like fainting"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["structured"]["urgency"], "emergency")
        self.assertTrue(data["structured"]["needs_professional_care"])
        self.assertEqual(data["structured"]["emotion"], "urgent")

    @patch('companion.requests.post')
    def test_companion_chat_casual_conversation_no_fake_sources(self, mock_post):
        """Casual non-medical conversation does not force medical sources."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "response": '{"answer": "Good morning! It is wonderful to hear from you today.", "confidence": "high", "medical_topic": "general_chat", "needs_professional_care": false, "urgency": "routine", "emotion": "warm"}'
            },
            "success": True
        }
        mock_post.return_value = mock_response

        res = self.client.post('/api/companion/chat', json={"message": "Good morning, how are you today?"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data["structured"]["sources"]), 0)

if __name__ == '__main__':
    unittest.main()
