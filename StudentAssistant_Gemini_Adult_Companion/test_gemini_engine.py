"""Offline tests: no API key or live network required."""
import os
import unittest
from unittest.mock import patch

import gemini_engine as g


class FakeResponse:
    def __init__(self, code=200, data=None):
        self.status_code = code
        self._data = data or {"candidates": [{"content": {"parts": [{"text": "வணக்கம்"}]}}]}

    def json(self):
        return self._data


class GeminiTests(unittest.TestCase):
    def setUp(self):
        g._daily.clear()
        g._global_daily.clear()
        g._minute.clear()
        g._sessions.clear()
        self.env = patch.dict(os.environ, {
            "GEMINI_API_KEY": "test-only", "GEMINI_ENABLED": "true",
            "GEMINI_ADULT_USER_IDS": "101, 102", "GEMINI_DAILY_LIMIT": "2",
            "GEMINI_SHARED_DAILY_LIMIT": "4", "GEMINI_SHARED_MINUTE_LIMIT": "3",
            "AI_ALLOW_PUBLIC": "true"}, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_allowlisted(self):
        self.assertTrue(g.authorized(101))
        self.assertFalse(g.authorized(103))

    def test_public_flag_does_not_bypass(self):
        self.assertFalse(g.authorized(200))

    def test_disabled(self):
        os.environ["GEMINI_ENABLED"] = "false"
        self.assertFalse(g.authorized(101))

    def test_missing_key(self):
        os.environ.pop("GEMINI_API_KEY")
        self.assertFalse(g.authorized(101))

    def test_model_and_payload(self):
        self.assertEqual(g.MODEL, "gemini-3.1-flash-lite")
        self.assertEqual(g.make_payload("Hello")["contents"][-1]["role"], "user")

    def test_international_script(self):
        self.assertEqual(g.make_payload("தமிழ்")['contents'][-1]['parts'][0]['text'], "தமிழ்")

    def test_success(self):
        seen = {}
        def post(url, headers, json, timeout):
            seen['url'] = url
            seen['json'] = json
            return FakeResponse()
        self.assertEqual(g.generate("What is a word?", 101, http_post=post), "வணக்கம்")
        self.assertIn(g.MODEL, seen['url'])
        self.assertEqual(g._history(101)[-1][1], "வணக்கம்")

    def test_not_approved_never_calls_provider(self):
        def post(*args, **kwargs):
            self.fail("A denied user reached API")
        with self.assertRaises(g.GeminiError) as result:
            g.generate("Hello", 999, http_post=post)
        self.assertEqual(result.exception.code, "unauthorized")

    def test_individual_quota(self):
        g.reserve_quota(101, now=1729800000)
        g.reserve_quota(101, now=1729800001)
        with self.assertRaises(g.GeminiError):
            g.reserve_quota(101, now=1729800002)

    def test_rate_limit(self):
        with self.assertRaises(g.GeminiError) as result:
            g.generate("test", 101, http_post=lambda *a, **k: FakeResponse(429))
        self.assertEqual(result.exception.code, "rate_limit")

    def test_auth_error(self):
        with self.assertRaises(g.GeminiError) as result:
            g.generate("test", 101, http_post=lambda *a, **k: FakeResponse(403))
        self.assertEqual(result.exception.code, "auth")

    def test_safety_block(self):
        payload = {"candidates": [{"finishReason": "SAFETY"}]}
        with self.assertRaises(g.GeminiError) as result:
            g.generate("test", 101, http_post=lambda *a, **k: FakeResponse(200, payload))
        self.assertEqual(result.exception.code, "safety")

    def test_empty_response(self):
        payload = {"candidates": []}
        with self.assertRaises(g.GeminiError):
            g.generate("test", 101, http_post=lambda *a, **k: FakeResponse(200, payload))

    def test_long_input(self):
        with self.assertRaises(g.GeminiError) as result:
            g.generate("a" * 1501, 101, http_post=lambda *a, **k: FakeResponse())
        self.assertEqual(result.exception.code, "input")

    def test_sessions_separate(self):
        g._remember(101, "question1", "reply1")
        self.assertEqual(g._history(102), [])
        g.clear_session(101)
        self.assertEqual(g._history(101), [])

if __name__ == "__main__":
    unittest.main()
