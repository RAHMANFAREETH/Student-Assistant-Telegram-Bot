"""Offline tests for V6.0; no HTTP requests, Telegram credentials or Supabase."""
from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import ai_ops_v60 as ops
import INSTALL_V6_0 as installer
import AI_V6_0_QUALITY_CHECK as quality


MAIN_SAMPLE = '''from achievements_v58 import register_achievements_v58_handlers
from ai_study_assistant import register_ai_study_assistant_handlers
bot = object()
def show_main_menu(chat_id):
    return chat_id
register_achievements_v58_handlers(bot, show_main_menu)
register_ai_study_assistant_handlers(bot, show_main_menu)
health = {"version": "5.8"}
'''
AI_SAMPLE = '''CF_MODEL = "@cf/qwen/qwen3-30b-a3b-fp8"
GUARD_MODEL = "@cf/meta/llama-guard-3-8b"
def _provider_call(model, messages, max_tokens):
    return "An answer"
def _check_safety(text):
    return True
def register_ai_study_assistant_handlers(bot, show_main_menu):
    return None
'''


class MockBot:
    def __init__(self):
        self.messages = []
        self.registered = []

    def message_handler(self, **args):
        self.registered.append(args)
        return lambda f: f

    def send_message(self, chat_id, message):
        self.messages.append((chat_id, message))


class InstallerTests(unittest.TestCase):
    def test_patch_main_idempotent(self):
        src, changed = installer.patch_main(MAIN_SAMPLE)
        self.assertTrue(changed)
        self.assertIn(installer.MAIN_IMPORT, src)
        self.assertIn(installer.MAIN_REGISTRATION, src)
        self.assertIn('"version": "6.0"', src)
        self.assertEqual(installer.patch_main(src), (src, False))

    def test_patch_ai_idempotent_without_changing_old_logic(self):
        src, changed = installer.patch_ai(AI_SAMPLE)
        self.assertTrue(changed)
        self.assertIn(AI_SAMPLE.strip(), src)
        self.assertIn(installer.AI_MARKER, src)
        self.assertEqual(installer.patch_ai(src), (src, False))

    def test_no_files_changed_when_incompatible(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.create_files(p, main=MAIN_SAMPLE.replace("achievements_v58", "unknown_v58"))
            before = {n: (p / n).read_bytes() for n in (installer.MAIN, installer.AI)}
            with self.assertRaisesRegex(ValueError, "Expected V5.8"):
                installer.run_install(p)
            self.assertEqual(before, {n: (p / n).read_bytes() for n in before})
            self.assertFalse(list(p.glob("*.bak")))

    def test_install_creates_backups_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.create_files(p)
            result = installer.run_install(p)
            self.assertEqual(result, [installer.AI, installer.MAIN])
            self.assertEqual((p / (installer.MAIN + ".before_v60.bak")).read_text(encoding="utf-8"), MAIN_SAMPLE)
            self.assertEqual((p / (installer.AI + ".before_v60.bak")).read_text(encoding="utf-8"), AI_SAMPLE)
            self.assertEqual(installer.run_install(p), [])

    def test_handles_utf8_emoji_and_crlf(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.create_files(p)
            # Test actual open path preserves CRLF in existing lines.
            (p / installer.MAIN).write_bytes((MAIN_SAMPLE + '# 🧠 AI\n').replace('\n','\r\n').encode('utf-8'))
            installer.run_install(p)
            content = (p / installer.MAIN).read_bytes()
            self.assertIn('🧠'.encode('utf-8'), content)
            self.assertIn(b'health = {"version": "6.0"}\r\n', content)

    def test_refuses_existing_backups(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.create_files(p)
            (p / (installer.MAIN + '.before_v60.bak')).write_text('old', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Backup already exists'):
                installer.run_install(p)
            self.assertEqual((p / installer.MAIN).read_text(encoding='utf-8'), MAIN_SAMPLE)

    def test_missing_gemini_preflight(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.create_files(p)
            (p / installer.GEMINI).unlink()
            with self.assertRaisesRegex(ValueError, 'Missing gemini'):
                installer.run_install(p)

    @staticmethod
    def create_files(root, main=MAIN_SAMPLE):
        for name, content in ((installer.MAIN, main), (installer.AI, AI_SAMPLE),
                              (installer.OPS, "# ops"), (installer.GEMINI, "# gemini")):
            (root / name).write_text(content, encoding="utf-8")


class WrapperTests(unittest.TestCase):
    def setUp(self):
        with ops._LOCK:
            ops._COUNTERS.clear()
            ops._ERROR_COUNTS.clear()
            ops._TOTAL_LATENCY_MS.clear()
            ops._SHORT_ANSWERS = 0

    def test_passthrough_and_no_student_data_retained(self):
        sentinel = "Student private SECRET phone 1234567890"
        calls = []
        def real(model, messages, max_tokens):
            calls.append((model, messages, max_tokens))
            return "the result is clear enough for the student's lesson"
        wrapped = ops.wrap_cloudflare_provider(real)
        result = wrapped(ops_model(), [{"role":"user", "content":sentinel}], 650)
        self.assertEqual(result, "the result is clear enough for the student's lesson")
        self.assertEqual(calls[0][1][0]["content"], sentinel)
        snapshot = repr(ops.metrics_snapshot())
        self.assertNotIn(sentinel, snapshot)
        self.assertNotIn("1234567890", ops.format_report())
        self.assertEqual(ops.metrics_snapshot()["providers"]["generation"]["success"], 1)
        self.assertIs(ops.wrap_cloudflare_provider(wrapped), wrapped)

    def test_exception_unmodified_but_code_aggregated(self):
        class CloudflareFailure(RuntimeError):
            code = "rate_limit"
        failure = CloudflareFailure("private provider response with SECRET value")
        def faulty(*args):
            raise failure
        with self.assertRaises(CloudflareFailure) as result:
            ops.wrap_cloudflare_provider(faulty)(ops_model(), [{"content": "SECRET"}], 100)
        self.assertIs(result.exception, failure)
        snap = ops.metrics_snapshot()
        self.assertEqual(snap["error_counts"]["generation:rate_limit"], 1)
        self.assertNotIn("SECRET", repr(snap))
        self.assertIn("rate limits", ops.format_report())

    def test_arbitrary_exception_strings_not_recorded(self):
        class Leak(RuntimeError):
            code = "TOP-SECRET-KEY"
        def faulty(*args):
            raise Leak("TOP-SECRET-RESPONSE")
        with self.assertRaises(Leak):
            ops.wrap_cloudflare_provider(faulty)(ops_model(), [], 12)
        snap = repr(ops.metrics_snapshot())
        self.assertNotIn("TOP-SECRET", snap)
        self.assertIn("other_error", snap)

    def test_moderation_classification_and_short_output_only_as_count(self):
        guard = ops.wrap_cloudflare_provider(lambda *args: "safe")
        guard("@cf/meta/llama-guard-3-8b", [{"role": "user", "content": "x"}], 64)
        gen = ops.wrap_cloudflare_provider(lambda *args: "2")
        gen(ops_model(), [{"role": "user", "content": "x"}], 650)
        s = ops.metrics_snapshot()
        self.assertEqual(s["providers"]["safety"]["success"], 1)
        self.assertEqual(s["short_generation_answers"], 1)

    def test_zero_metrics(self):
        s = ops.metrics_snapshot()
        self.assertEqual(s["providers"]["generation"]["average_ms"], 0)


class AdminTests(unittest.TestCase):
    def make_message(self, uid, kind="private", chat_id=111):
        return SimpleNamespace(chat=SimpleNamespace(id=chat_id, type=kind),
                               from_user=SimpleNamespace(id=uid))

    def test_defaults_deny_all_and_no_secret_echo(self):
        bot = MockBot()
        handler = ops.register_ai_ops_v60_handlers(bot)["admin_command"]
        with patch.dict(os.environ, {"AI_OPS_ADMIN_IDS": "", "CLOUDFLARE_API_TOKEN": "VERY-PRIVATE-KEY"}):
            handler(self.make_message(1))
        self.assertIn("not enabled", bot.messages[-1][1])
        self.assertNotIn("VERY-PRIVATE-KEY", str(bot.messages))

    def test_private_admin_only_sender_not_chat(self):
        bot = MockBot()
        handler = ops.register_ai_ops_v60_handlers(bot)["admin_command"]
        with patch.dict(os.environ, {"AI_OPS_ADMIN_IDS": "222, nope,333"}):
            handler(self.make_message(999, chat_id=222))
            self.assertIn("not enabled", bot.messages[-1][1])
            handler(self.make_message(222, chat_id=222))
            self.assertIn("AI Operations V6.0", bot.messages[-1][1])
            handler(self.make_message(222, kind="group"))
            self.assertIn("private chat", bot.messages[-1][1])

    def test_allowed_student_is_not_admin(self):
        bot = MockBot()
        handler = ops.register_ai_ops_v60_handlers(bot)["admin_command"]
        with patch.dict(os.environ, {"AI_OPS_ADMIN_IDS": "", "AI_ALLOWED_USER_IDS": "222"}):
            handler(self.make_message(222))
        self.assertIn("not enabled", bot.messages[-1][1])

    def test_no_auto_gemini_fallback(self):
        source = (Path(__file__).parent / 'ai_ops_v60.py').read_text(encoding='utf-8')
        self.assertNotIn('GeminiClient(', source)
        self.assertNotIn('.generate(', source)

    def test_report_bounds(self):
        self.assertLess(len(ops.format_report()), 3900)
        self.assertIn('reset on restart', ops.format_report())


class QualityTests(unittest.TestCase):
    def test_four_languages(self):
        self.assertEqual({v[1] for v in quality.SAMPLES.values()}, {'english','tamil','sinhala','arabic'})

    def test_offline_default(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = quality.main([])
        self.assertEqual(code, 0)
        self.assertIn('DRY RUN', out.getvalue())

    def test_checklist_includes_accuracy(self):
        self.assertIn('Correct and verifiable', quality.rubric())


def ops_model():
    return '@cf/qwen/qwen3-30b-a3b-fp8'


if __name__ == '__main__':
    unittest.main()
