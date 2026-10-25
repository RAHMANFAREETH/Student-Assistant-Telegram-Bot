"""V6.1 offline tests. No real HTTP, Telegram access, or secrets needed."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import gemini_render_v61 as v61
import INSTALL_V6_1 as installer
import ai_ops_v60 as ops


class FakeResponse:
    def __init__(self, doc):
        self.data = json.dumps(doc).encode("utf-8")
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, n=-1): return self.data[:n]


GOOD = {
    "candidates": [{"content": {"parts": [{"text": "Four."}]}}],
    "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 3, "totalTokenCount": 25},
}


class ConfigTests(unittest.TestCase):
    def test_no_key(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(v61.config_status()["gemini_env"])
            self.assertIn("not configured", v61.admin_line())

    def test_exact_render_env_variable(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "PRIVATE-TEST", "GOOGLE_API_KEY": "other"}, clear=True):
            self.assertTrue(v61.config_status()["gemini_env"])
            self.assertIn("configured", v61.admin_line())
            self.assertNotIn("PRIVATE-TEST", v61.admin_line())

    def test_other_key_is_not_mistaken_for_render_key(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "some-key"}, clear=True):
            self.assertFalse(v61.config_status()["gemini_env"])

    def test_admin_report_has_config_but_no_secret(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "PRIVATE-TEST"}, clear=True):
            report = ops.format_report()
            self.assertIn("Gemini API key on Render: configured", report)
            self.assertNotIn("PRIVATE-TEST", report)
            self.assertIn("DISABLED", report)


class ProbeTests(unittest.TestCase):
    def test_no_key_refused_without_network(self):
        with patch.object(v61.urllib.request, "urlopen", side_effect=AssertionError("network")):
            self.assertEqual(v61.probe_once("" ).status, "not_configured")
            self.assertEqual(v61.probe_once("abc\r\nxyz").status, "not_configured")

    def test_exact_one_post_fixed_question_and_auth_header(self):
        calls = []
        def mock_open(req, timeout):
            calls.append(req)
            self.assertEqual(timeout, v61._TIMEOUT_SECONDS)
            self.assertEqual(req.full_url, v61.API_URL)
            self.assertNotIn("unit-secret", req.full_url)
            self.assertEqual(req.headers.get("X-goog-api-key"), "unit-secret")
            self.assertEqual(req.get_method(), "POST")
            sent = json.loads(req.data)
            self.assertEqual(sent["contents"][0]["parts"][0]["text"], v61._PROBE_TEXT)
            self.assertNotIn("users", json.dumps(sent))
            return FakeResponse(GOOD)
        with patch.object(v61.urllib.request, "urlopen", side_effect=mock_open):
            result = v61.probe_once("unit-secret")
        self.assertEqual(result.status, "ok")
        self.assertEqual((result.prompt_tokens, result.response_tokens, result.total_tokens), (12, 3, 25))
        self.assertEqual(len(calls), 1)

    def test_no_answer_candidate(self):
        with patch.object(v61.urllib.request, "urlopen", return_value=FakeResponse({"candidates": []})):
            self.assertEqual(v61.probe_once("some-key").status, "no_answer")

    def test_no_text(self):
        with patch.object(v61.urllib.request, "urlopen", return_value=FakeResponse({"candidates": [{"content": {}}]})):
            self.assertEqual(v61.probe_once("some-key").status, "no_answer")

    def test_no_usage_metadata_still_success(self):
        with patch.object(v61.urllib.request, "urlopen", return_value=FakeResponse({"candidates": [{"content": {"parts": [{"text": "4"}]}}]})):
            result = v61.probe_once("some-key")
        self.assertEqual(result.status, "ok")
        self.assertIsNone(result.total_tokens)

    def test_invalid_usage_values_ignored(self):
        bad = json.loads(json.dumps(GOOD))
        bad["usageMetadata"] = {"totalTokenCount": True, "promptTokenCount": -1, "candidatesTokenCount": 2.0}
        with patch.object(v61.urllib.request, "urlopen", return_value=FakeResponse(bad)):
            result = v61.probe_once("some-key")
        self.assertIsNone(result.total_tokens)
        self.assertIsNone(result.prompt_tokens)
        self.assertIsNone(result.response_tokens)

    def test_http_errors_sanitized(self):
        for http_code, status in ((400, "bad_request"), (401, "authentication"), (403, "permission"),
                                  (404, "model_unavailable"), (429, "quota"), (503, "service_error")):
            with self.subTest(http_code=http_code):
                err = HTTPError(v61.API_URL, http_code, "secret-error-blob", {}, None)
                with patch.object(v61.urllib.request, "urlopen", side_effect=err):
                    result = v61.probe_once("unit-secret")
                self.assertEqual(result.status, status)
                self.assertNotIn("secret-error-blob", result.detail)
                self.assertNotIn("unit-secret", result.detail)

    def test_retry_after_is_sanitized_numeric_only(self):
        for header, fragment in (("20", "20s"), ("PRIVATE-DATA", "PRIVATE-DATA"), ("100000", "100000")):
            err = HTTPError(v61.API_URL, 429, "secret", {"Retry-After": header}, None)
            with patch.object(v61.urllib.request, "urlopen", side_effect=err):
                result = v61.probe_once("unit-secret")
            self.assertEqual(fragment in result.detail, header == "20")

    def test_connection_error_does_not_echo_exception(self):
        with patch.object(v61.urllib.request, "urlopen", side_effect=URLError("sensitive?key=unit-secret")):
            result = v61.probe_once("unit-secret")
        self.assertEqual(result.status, "network")
        self.assertNotIn("unit-secret", result.detail)

    def test_bad_json(self):
        class Bad(FakeResponse):
            def read(self, n=-1): return b'bad-json'
        with patch.object(v61.urllib.request, "urlopen", return_value=Bad({})):
            self.assertEqual(v61.probe_once("unit-secret").status, "invalid_response")

    def test_oversized_reply(self):
        class Huge(FakeResponse):
            def read(self, n=-1): return b'x' * (n + 1)
        with patch.object(v61.urllib.request, "urlopen", return_value=Huge({})):
            self.assertEqual(v61.probe_once("unit-secret").status, "invalid_response")

    def test_quota_parsing(self):
        self.assertEqual(v61._quota_seconds(" 45 "), 45)
        self.assertIsNone(v61._quota_seconds("Wed, 21 Oct 2015"))
        self.assertIsNone(v61._quota_seconds("999999999"))


class CLITests(unittest.TestCase):
    def test_default_offline_no_secret(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret-test"}, clear=True):
            with patch.object(v61.urllib.request, "urlopen", side_effect=AssertionError("network used")):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    rc = v61.main([])
        self.assertEqual(rc, 0)
        self.assertIn("No API request sent", output.getvalue())
        self.assertNotIn("secret-test", output.getvalue())

    def test_missing_env_is_code_two(self):
        with patch.dict(os.environ, {}, clear=True):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(v61.main(["--live"]), 2)

    def test_live_success_safe_console(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret-test"}, clear=True):
            with patch.object(v61.urllib.request, "urlopen", return_value=FakeResponse(GOOD)):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(v61.main(["--live"]), 0)
        self.assertIn("Live probe status: ok", output.getvalue())
        self.assertNotIn("secret-test", output.getvalue())
        self.assertNotIn("Four.", output.getvalue())


class InstallerTests(unittest.TestCase):
    OPS_SAMPLE = '''from __future__ import annotations

def format_report():
    rows = [
        "Gemini Telegram routing: DISABLED (mixed-age bot)",
    ]
    return "\\n".join(rows)
'''

    def setup_root(self, p):
        for file in (installer.GEMINI, installer.NEW):
            (p / file).write_text("# module\n", encoding="utf-8")
        (p / installer.OPS).write_text(self.OPS_SAMPLE, encoding="utf-8")

    def test_patch_and_idempotence(self):
        changed, yes = installer.patch_ops(self.OPS_SAMPLE)
        self.assertTrue(yes)
        self.assertIn(installer.MARKER, changed)
        self.assertEqual(installer.patch_ops(changed), (changed, False))

    def test_installer_backups_and_idempotence(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.setup_root(p)
            original = (p / installer.OPS).read_bytes()
            self.assertEqual(installer.run_install(p), [installer.OPS])
            self.assertEqual((p / (installer.OPS + '.before_v61.bak')).read_bytes(), original)
            self.assertEqual(installer.run_install(p), [])

    def test_incompatible_refused_and_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.setup_root(p)
            (p / installer.OPS).write_text("# mismatched", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Compatible V6.0"):
                installer.run_install(p)
            self.assertEqual((p / installer.OPS).read_text(encoding='utf-8'), '# mismatched')
            self.assertFalse((p / (installer.OPS + '.before_v61.bak')).exists())

    def test_preexisting_backup_protected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.setup_root(p)
            (p / (installer.OPS + '.before_v61.bak')).write_text('old', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                installer.run_install(p)

    def test_emoji_utf8_crlf_remain(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.setup_root(p)
            content = self.OPS_SAMPLE.replace('    rows', '    # ✨\n    rows').replace('\n', '\r\n')
            (p / installer.OPS).write_bytes(content.encode('utf-8'))
            installer.run_install(p)
            updated = (p / installer.OPS).read_bytes()
            self.assertIn('✨'.encode('utf-8'), updated)
            self.assertIn(b'\r\n', updated)

    def test_no_bot_changes(self):
        source = (Path(__file__).parent / 'gemini_render_v61.py').read_text(encoding='utf-8')
        for forbidden in ('@bot.message_handler', 'register_gemini_handlers', 'send_message(', 'Flask(', 'main.py'):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("GeminiClient(", (Path(__file__).parent / 'ai_ops_v60.py').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
