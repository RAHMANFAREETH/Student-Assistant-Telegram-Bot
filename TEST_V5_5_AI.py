"""Run: python -m unittest TEST_V5_5_AI.py -v (no keys/network)."""
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import shutil
import sys
import tempfile
import types as pytypes
import unittest
from unittest.mock import patch

BASE = Path(__file__).parent

# Test stubs for pyTelegramBotAPI and Supabase; never open external services.
if "telebot" not in sys.modules:
    telebot = pytypes.ModuleType("telebot")
    telebot_types = pytypes.ModuleType("telebot.types")
    class KeyboardButton:
        def __init__(self, text): self.text = text
    class ReplyKeyboardMarkup:
        def __init__(self, **kwargs): self.buttons = []
        def add(self, *buttons): self.buttons.extend(buttons)
        def row(self, *buttons): self.buttons.extend(buttons)
    telebot_types.KeyboardButton = KeyboardButton
    telebot_types.ReplyKeyboardMarkup = ReplyKeyboardMarkup
    telebot.types = telebot_types
    backends = pytypes.ModuleType("telebot.handler_backends")
    class ContinueHandling: pass
    backends.ContinueHandling = ContinueHandling
    sys.modules["telebot"] = telebot
    sys.modules["telebot.types"] = telebot_types
    sys.modules["telebot.handler_backends"] = backends
else:
    from telebot.handler_backends import ContinueHandling

if "db" not in sys.modules:
    db = pytypes.ModuleType("db")
    db.supabase = SimpleNamespace()
    sys.modules["db"] = db
if "navigation" not in sys.modules:
    nav = pytypes.ModuleType("navigation")
    nav.should_yield_to_navigation = lambda x: x.startswith("/") or x in {"🏠 Main Menu", "📝 Notes", "📄 PDF Tools", "🤖 Ask AI"}
    sys.modules["navigation"] = nav
if "safe_utils" not in sys.modules:
    utils = pytypes.ModuleType("safe_utils")
    utils.split_telegram_text = lambda s, limit=3500: [s[i:i+limit] for i in range(0,len(s),limit)]
    sys.modules["safe_utils"] = utils

spec = importlib.util.spec_from_file_location("ai_v55_testable", BASE / "ai_study_assistant.py")
ai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai)

class FakeBot:
    def __init__(self): self.handlers = []; self.messages = []
    def message_handler(self, **params):
        def deco(fn): self.handlers.append((fn, params)); return fn
        return deco
    def send_message(self, chat_id, text, **kwargs): self.messages.append((chat_id, text, kwargs))
    def call(self, name, msg):
        for fn, _ in self.handlers:
            if fn.__name__ == name: return fn(msg)
        raise AssertionError(f"Missing handler {name}")

class FakeMsg:
    def __init__(self, text, user=111, private=True):
        self.text = text
        self.from_user = SimpleNamespace(id=user, first_name="Student")
        self.chat = SimpleNamespace(id=user if private else -1, type="private" if private else "group")

class Tests(unittest.TestCase):
    def setUp(self):
        ai._sessions.clear()
        ai._active_user_ids.clear()
        self.env = patch.dict(os.environ, {
            "AI_ENABLED": "true", "AI_ALLOWED_USER_IDS": "111",
            "CLOUDFLARE_ACCOUNT_ID": "a" * 32,
            "CLOUDFLARE_API_TOKEN": "fake-test-key",
            "AI_ALLOW_PUBLIC": "false", "AI_DAILY_LIMIT": "8"
        })
        self.env.start()
    def tearDown(self): self.env.stop()
    def test_default_off_and_allowlist(self):
        self.assertTrue(ai.is_authorized(111))
        self.assertFalse(ai.is_authorized(222))
        os.environ["AI_ENABLED"] = "false"
        self.assertFalse(ai.is_authorized(111))
    def test_public_mode_switch_and_private_chats(self):
        self.assertFalse(ai.is_authorized(222))
        os.environ["AI_ALLOW_PUBLIC"] = "true"
        self.assertTrue(ai.is_authorized(222))
        os.environ["AI_ENABLED"] = "false"
        self.assertFalse(ai.is_authorized(222))

    def test_quota_limit_clamps(self):
        os.environ["AI_DAILY_LIMIT"] = "100000"
        self.assertEqual(ai.daily_limit(), 30)
        os.environ["AI_DAILY_LIMIT"] = "bad"
        self.assertEqual(ai.daily_limit(), 8)
    def test_modes_private_and_state_isolated(self):
        bot = FakeBot()
        ai.register_ai_study_assistant_handlers(bot, lambda *args: None)
        bot.call("ai_button", FakeMsg(ai.AI_MENU, user=111))
        bot.call("select_ai_mode", FakeMsg("💬 Ask Question", user=111))
        self.assertEqual(ai._get_session(111)["mode"], "ask")
        self.assertIsNone(ai._get_session(222))
        bot.call("select_ai_mode", FakeMsg("💬 Ask Question", user=222))
        self.assertIsNone(ai._get_session(222))
        bot.call("ai_button", FakeMsg(ai.AI_MENU, private=False))
        self.assertTrue(any("private chat" in m[1] for m in bot.messages))
    def test_navigation_yields_and_clears(self):
        bot = FakeBot()
        ai.register_ai_study_assistant_handlers(bot, lambda *args: None)
        ai._set_mode(111, "ask")
        result = bot.call("ai_chat_message", FakeMsg("📝 Notes"))
        self.assertIsInstance(result, ContinueHandling)
        self.assertIsNone(ai._get_session(111))
    def test_clear_and_history(self):
        ai._set_mode(111, "ask")
        ai._remember(111, "Q1", "A1")
        self.assertEqual(len(ai._get_session(111)["history"]), 2)
        ai._clear(111)
        self.assertIsNone(ai._get_session(111))
    def test_build_messages_no_cross_user_or_fake_access(self):
        messages = ai.build_messages("explain", [{"role": "user", "content": "Earlier"}], "Next")
        self.assertEqual([m["role"] for m in messages], ["system", "user", "user"])
        self.assertIn("Do not claim to have read", messages[0]["content"])
    def test_http_429(self):
        fake = SimpleNamespace(status_code=429)
        with patch.object(ai.requests, "post", return_value=fake):
            with self.assertRaises(ai.AIUnavailable) as ctx:
                ai._provider_call(ai.CF_MODEL, [{"role":"user", "content":"Hi"}], 100)
        self.assertEqual(ctx.exception.code, "rate_limit")
    def test_request_payload_uses_token_in_header_only(self):
        fake = SimpleNamespace(status_code=200, json=lambda: {"success": True, "result": {"response": "A short answer"}})
        with patch.object(ai.requests, "post", return_value=fake) as p:
            self.assertEqual(ai._provider_call(ai.CF_MODEL, [{"role":"user", "content":"Hi"}], 100), "A short answer")
            kwargs = p.call_args.kwargs
            self.assertEqual(kwargs["headers"]["Authorization"], "Bearer fake-test-key")
            self.assertNotIn("fake-test-key", str(kwargs["json"]))
            self.assertTrue(p.call_args.args[0].startswith("https://api.cloudflare.com/"))
    def test_moderation_fail_closed(self):
        with patch.object(ai, "_provider_call", return_value="safe\n"):
            self.assertTrue(ai._check_safety("hello"))
        with patch.object(ai, "_provider_call", return_value="unsafe\nS3"):
            self.assertFalse(ai._check_safety("unsafe prompt"))
        with patch.object(ai, "_provider_call", return_value="unknown"):
            with self.assertRaises(ai.AIUnavailable): ai._check_safety("something")
    def test_session_chat_flow_with_mocks(self):
        bot = FakeBot()
        ai.register_ai_study_assistant_handlers(bot, lambda *args: None)
        bot.call("select_ai_mode", FakeMsg("📖 Explain Topic"))
        def inline(fn, *args): fn(*args)
        with patch.object(ai._ai_executor, "submit", side_effect=inline), patch.object(ai, "claim_quota", return_value=1), patch.object(ai, "_check_safety", return_value=True) as safety, patch.object(ai, "_provider_call", return_value="Photosynthesis explained"):
            bot.call("ai_chat_message", FakeMsg("Explain photosynthesis"))
        self.assertIn("Photosynthesis explained", [x[1] for x in bot.messages])
        self.assertEqual(len(ai._get_session(111)["history"]), 2)
        self.assertEqual(safety.call_count, 2)
    def test_invalid_quota_fail_closed(self):
        bot = FakeBot()
        ai.register_ai_study_assistant_handlers(bot, lambda *args: None)
        bot.call("select_ai_mode", FakeMsg("💬 Ask Question"))
        with patch.object(ai._ai_executor, "submit", side_effect=lambda fn,*args: fn(*args)), patch.object(ai, "claim_quota", side_effect=RuntimeError("fake")), patch.object(ai, "_provider_call") as provider:
            bot.call("ai_chat_message", FakeMsg("Hello"))
        provider.assert_not_called()
        self.assertTrue(any("SQL_V5_5_AI.sql" in m[1] for m in bot.messages))
    def test_no_group_or_unapproved_questions(self):
        bot = FakeBot()
        ai.register_ai_study_assistant_handlers(bot, lambda *args: None)
        with patch.object(ai, "_provider_call") as provider:
            bot.call("ai_button", FakeMsg(ai.AI_MENU, private=False))
            bot.call("select_ai_mode", FakeMsg("🧮 Maths Help", user=222))
        provider.assert_not_called()
        self.assertEqual(len(ai._sessions), 0)
    def test_concurrent_student_requests_are_bounded(self):
        bot = FakeBot()
        ai.register_ai_study_assistant_handlers(bot, lambda *args: None)
        bot.call("select_ai_mode", FakeMsg("💬 Ask Question"))
        ai._active_user_ids.add(111)
        with patch.object(ai._ai_executor, "submit") as executor:
            bot.call("ai_chat_message", FakeMsg("Hello again"))
        executor.assert_not_called()
        self.assertTrue(any("still answering" in msg[1] for msg in bot.messages))

    def test_installer_idempotent_keeps_other_modules(self):
        spec = importlib.util.spec_from_file_location("install_v55_testable", BASE / "INSTALL_V5_5.py")
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        # original prior V5.4 files should be present via package for this test
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/"main.py").write_text(
                'from navigation_handlers import (\n    register_navigation_handlers,\n)\n'
                'from translate import register_translation_handlers\n'
                'register_spaced_repetition_handlers(bot, show_main_menu)\n', encoding="utf-8")
            (Path(tmp)/"navigation.py").write_text(
                'HELP = "ℹ️ Help"\nMAIN_MENU_ROWS = [\n    (HELP,),\n]\n', encoding="utf-8")
            shutil.copy(BASE / "ai_study_assistant.py", Path(tmp)/"ai_study_assistant.py")
            oldcwd = os.getcwd()
            try:
                os.chdir(tmp)
                self.assertEqual(installer.main(), 0)
                first = Path("main.py").read_text(encoding="utf-8")
                self.assertIn('from translate import register_translation_handlers', first)
                self.assertIn('register_ai_study_assistant_handlers(bot, show_main_menu)', first)
                self.assertEqual(first.count('register_ai_study_assistant_handlers(bot, show_main_menu)'), 1)
                self.assertEqual(installer.main(), 0)
                self.assertEqual(Path("main.py").read_text(encoding="utf-8"), first)
                self.assertIn('🤖 Ask AI', Path("navigation.py").read_text(encoding="utf-8"))
            finally:
                os.chdir(oldcwd)

if __name__ == "__main__": unittest.main()
