"""Offline tests: no Telegram token, Google key, or network required."""
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, os.path.dirname(__file__))

from adult_pilot import AdultPilot, PilotDenied, allowed_ids, split_message, register_handlers
from gemini_ai_studio_v59 import GeminiClientError


class FakeGemini:
    def __init__(self, reply="Professional sample answer"):
        self.reply = reply
        self.calls = []

    def generate(self, question, *, task, language):
        self.calls.append((question, task, language))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


class FakeBot:
    def __init__(self):
        self.handlers = []
        self.sent = []

    def message_handler(self, **kwargs):
        def decorator(fn):
            self.handlers.append((kwargs, fn))
            return fn
        return decorator

    def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))

    def command(self, name, message):
        for opts, handler in self.handlers:
            if name in opts.get("commands", ()):
                return handler(message)
        raise KeyError(name)

    def plain(self, message):
        return self.handlers[-1][1](message)


def msg(uid=123, text="What is a neural net?", *, private=True):
    return SimpleNamespace(from_user=SimpleNamespace(id=uid),
                           chat=SimpleNamespace(id=uid, type="private" if private else "group"), text=text)


class AccessTests(unittest.TestCase):
    def test_allowlist_empty_denies_everyone(self):
        self.assertEqual(allowed_ids(""), frozenset())
    def test_allowlist_valid_ids(self):
        self.assertEqual(allowed_ids(" 100 , 200 "), frozenset({100, 200}))
    def test_invalid_allowlist_blocks(self):
        for raw in ("-1", "1,", "x", "1;2", "1, ٢", "0"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                allowed_ids(raw)
    def test_disabled_pilot_never_calls_gemini(self):
        client = FakeGemini()
        p = AdultPilot(client=client, adult_user_ids={123}, enabled=False)
        with self.assertRaises(PilotDenied): p.answer(123, "Test")
        self.assertEqual(client.calls, [])
    def test_unauthorized_never_calls_gemini(self):
        client = FakeGemini()
        p = AdultPilot(client=client, adult_user_ids={123}, enabled=True)
        with self.assertRaises(PilotDenied): p.answer(999, "Test")
        self.assertEqual(client.calls, [])
    def test_groups_denied(self):
        p = AdultPilot(client=FakeGemini(), adult_user_ids={123}, enabled=True)
        with self.assertRaises(PilotDenied): p.answer(123, "Test", private=False)
    def test_valid_allowlisted_query(self):
        c = FakeGemini()
        p = AdultPilot(client=c, adult_user_ids={123}, enabled=True)
        self.assertEqual(p.answer(123, "  hello "), "Professional sample answer")
        self.assertEqual(c.calls, [("hello", "ask", "english")])
    def test_tamil_arabic_modes(self):
        c = FakeGemini()
        p = AdultPilot(client=c, adult_user_ids={123}, enabled=True)
        p.update_setting(123, "language", "tamil")
        p.update_setting(123, "task", "explain")
        p.answer(123, "கணிதம்")
        self.assertEqual(c.calls[-1], ("கணிதம்", "explain", "tamil"))
        p.update_setting(123, "language", "arabic")
        p.answer(123, "الصوتيات")
        self.assertEqual(c.calls[-1][2], "arabic")
    def test_invalid_mode_rejected(self):
        p = AdultPilot(client=FakeGemini(), adult_user_ids={123}, enabled=True)
        with self.assertRaises(PilotDenied): p.update_setting(123, "task", "unsafe")
    def test_user_daily_quota(self):
        c = FakeGemini()
        p = AdultPilot(client=c, adult_user_ids={123}, enabled=True, daily_limit=2)
        p.answer(123, "A")
        p.answer(123, "B")
        with self.assertRaises(PilotDenied): p.answer(123, "C")
        self.assertEqual(len(c.calls), 2)
        self.assertEqual(p.remaining(123), 0)
    def test_shared_daily_quota(self):
        c = FakeGemini()
        p = AdultPilot(client=c, adult_user_ids={123, 456}, enabled=True, shared_daily_limit=1)
        p.answer(123, "A")
        with self.assertRaises(PilotDenied): p.answer(456, "B")
    def test_minute_quota(self):
        c = FakeGemini()
        p = AdultPilot(client=c, adult_user_ids={123}, enabled=True, minute_limit=1)
        p.answer(123, "A")
        with self.assertRaises(PilotDenied): p.answer(123, "B")
    def test_invalid_limit_blocks(self):
        with self.assertRaises(ValueError): AdultPilot(client=FakeGemini(), daily_limit=0)
    def test_blank_and_huge_question_rejected_without_call(self):
        c = FakeGemini()
        p = AdultPilot(client=c, adult_user_ids={123}, enabled=True)
        with self.assertRaises(PilotDenied): p.answer(123, "  ")
        with self.assertRaises(PilotDenied): p.answer(123, "x" * 5001)
        self.assertEqual(c.calls, [])
    def test_provider_error_sanitized(self):
        c = FakeGemini(GeminiClientError("Rate limit or quota reached."))
        p = AdultPilot(client=c, adult_user_ids={123}, enabled=True)
        with self.assertRaisesRegex(PilotDenied, "quota"):
            p.answer(123, "Test")
    def test_unexpected_error_generic(self):
        c = FakeGemini(RuntimeError("private secret example"))
        p = AdultPilot(client=c, adult_user_ids={123}, enabled=True)
        with self.assertRaises(PilotDenied) as error:
            p.answer(123, "Test")
        self.assertNotIn("private secret", str(error.exception))
    def test_long_answer_split_without_loss(self):
        text = "தமிழ் " * 2000
        parts = split_message(text, limit=200)
        self.assertTrue(all(len(x) <= 200 for x in parts))
        self.assertEqual(" ".join(parts).strip(), text.strip())
    def test_zero_length_message(self):
        self.assertEqual(split_message(""), [])
    def test_command_registration(self):
        bot = FakeBot()
        p = AdultPilot(client=FakeGemini(), adult_user_ids={123}, enabled=True)
        register_handlers(bot, p)
        bot.command("myid", msg(999, "/myid"))
        self.assertIn("999", bot.sent[-1][1])
        bot.command("start", msg(123, "/start"))
        self.assertIn("Professional Pilot", bot.sent[-1][1])
        bot.command("language", msg(123, "/language tamil"))
        self.assertIn("tamil", bot.sent[-1][1])
        bot.plain(msg(123, "வணக்கம்"))
        self.assertIn("sample answer", bot.sent[-1][1])
    def test_bot_denies_unapproved_chat(self):
        bot = FakeBot()
        client = FakeGemini()
        p = AdultPilot(client=client, adult_user_ids={123}, enabled=True)
        register_handlers(bot, p)
        bot.plain(msg(999, "Private query"))
        bot.plain(msg(123, "group query", private=False))
        self.assertEqual(client.calls, [])
        self.assertEqual(len(bot.sent), 2)


if __name__ == "__main__":
    unittest.main()
