"""Offline tests for the V5.9 Gemini developer client, no secrets or network."""
import contextlib
import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import gemini_ai_studio_v59 as gm
import GEMINI_V5_9_DEV_TEST as cli


class FakeResponse:
    def __init__(self, doc):
        self.doc = json.dumps(doc).encode()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, limit=-1):
        return self.doc[:limit]


class PayloadTests(unittest.TestCase):
    def test_expected_stable_model(self):
        self.assertEqual(gm.MODEL, "gemini-3.1-flash-lite")
        self.assertEqual(gm.API_URL, "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent")
    def test_all_study_tasks(self):
        self.assertEqual(set(gm.TASKS), {"ask", "explain", "maths", "quiz", "language"})
    def test_four_languages(self):
        self.assertEqual(set(gm.LANGUAGES), {"english", "tamil", "sinhala", "arabic"})
    def test_unicode_question(self):
        p = gm.build_payload("தமிழ் விளக்கம்", language="tamil")
        self.assertEqual(p["contents"][0]["parts"][0]["text"], "தமிழ் விளக்கம்")
        self.assertIn("Tamil", p["systemInstruction"]["parts"][0]["text"])
    def test_empty_question_refused(self):
        with self.assertRaises(ValueError): gm.build_payload("  ")
    def test_non_text_refused(self):
        with self.assertRaises(ValueError): gm.build_payload(123)
    def test_long_question_refused(self):
        with self.assertRaises(ValueError): gm.build_payload("x" * (gm.MAX_INPUT + 1))
    def test_unknown_task_refused(self):
        with self.assertRaises(ValueError): gm.build_payload("hello", task="unsafe")
    def test_unknown_language_refused(self):
        with self.assertRaises(ValueError): gm.build_payload("hello", language="unknown")
    def test_no_hardcoded_key(self):
        self.assertNotIn("AIza", gm.API_URL)
        self.assertNotIn("?key=", gm.API_URL)
    def test_no_chat_registration(self):
        self.assertFalse(hasattr(gm, "register_gemini_handlers"))
        self.assertFalse(hasattr(gm, "bot"))
    def test_no_default_secret(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(gm.read_api_key(), "")
    def test_env_key_supported(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "  abc-test "}, clear=True):
            self.assertEqual(gm.read_api_key(), "abc-test")
    def test_empty_key_rejected(self):
        with self.assertRaises(ValueError): gm.GeminiClient("  ")
    def test_header_injection_rejected(self):
        with self.assertRaises(ValueError): gm.GeminiClient("abc\r\nInjected: yes")
    def test_invalid_timeout_rejected(self):
        with self.assertRaises(ValueError): gm.GeminiClient("xyz", timeout=0)


class NetworkTests(unittest.TestCase):
    def test_success_and_header_and_no_key_in_url(self):
        def fake_open(request, timeout):
            self.assertEqual(timeout, gm.DEFAULT_TIMEOUT)
            self.assertEqual(request.full_url, gm.API_URL)
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(request.headers.get("X-goog-api-key"), "unit-test-key")
            self.assertIn("contents", json.loads(request.data.decode("utf8")))
            return FakeResponse({"candidates": [{"content": {"parts": [{"text": "Hello"}, {"text": "வணக்கம்"}]}}]})
        with patch.object(gm.urllib.request, "urlopen", side_effect=fake_open):
            answer = gm.GeminiClient("unit-test-key").generate("Hello")
        self.assertEqual(answer, "Hello\nவணக்கம்")
    def test_http_429_is_sanitized(self):
        err = HTTPError(gm.API_URL, 429, "raw error includes secret-placeholder", {}, None)
        with patch.object(gm.urllib.request, "urlopen", side_effect=err):
            with self.assertRaises(gm.GeminiClientError) as info:
                gm.GeminiClient("private-key").generate("hello")
        self.assertIn("quota", str(info.exception).lower())
        self.assertNotIn("private-key", str(info.exception))
    def test_http_403_is_sanitized(self):
        err = HTTPError(gm.API_URL, 403, "sensitive", {}, None)
        with patch.object(gm.urllib.request, "urlopen", side_effect=err):
            with self.assertRaises(gm.GeminiClientError) as info:
                gm.GeminiClient("private-key").generate("hello")
        self.assertIn("Authentication", str(info.exception))
        self.assertNotIn("sensitive", str(info.exception))
    def test_connection_error_sanitized(self):
        with patch.object(gm.urllib.request, "urlopen", side_effect=URLError("example.key")):
            with self.assertRaises(gm.GeminiClientError) as info:
                gm.GeminiClient("secret").generate("hello")
        self.assertNotIn("example.key", str(info.exception))
    def test_no_candidate_filtered(self):
        with self.assertRaises(gm.GeminiClientError): gm.extract_text({"candidates": []})
    def test_no_text(self):
        with self.assertRaises(gm.GeminiClientError): gm.extract_text({"candidates": [{"content": {"parts": [{"functionCall": {}}]}}]})
    def test_malformed_text(self):
        with self.assertRaises(gm.GeminiClientError): gm.extract_text("unexpected")
    def test_response_truncated(self):
        self.assertEqual(len(gm.extract_text({"candidates": [{"content": {"parts": [{"text": "x" * (gm.MAX_OUTPUT + 100)}]}}]})), gm.MAX_OUTPUT)
    def test_invalid_json_response(self):
        class InvalidResponse(FakeResponse):
            def read(self, limit=-1): return b"not json"
        with patch.object(gm.urllib.request, "urlopen", return_value=InvalidResponse({})):
            with self.assertRaises(gm.GeminiClientError): gm.GeminiClient("secret").generate("hello")


class CLITests(unittest.TestCase):
    def test_dry_run_no_api_and_no_key(self):
        with patch.object(gm.urllib.request, "urlopen", side_effect=AssertionError("network used")):
            with patch.dict(os.environ, {}, clear=True):
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    code = cli.main(["--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("no API request sent", out.getvalue())
    def test_sanitized_errors_no_key_print(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "private-unit-key"}, clear=True):
            with patch.object(gm.urllib.request, "urlopen", side_effect=HTTPError(gm.API_URL, 403, "private-unit-key", {}, None)):
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    code = cli.main(["--smoke"])
        self.assertEqual(code, 1)
        self.assertNotIn("private-unit-key", out.getvalue())


if __name__ == "__main__":
    unittest.main()
