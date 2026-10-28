"""Offline V7.9 safety/UX tests. No API keys, Telegram network, or Supabase calls."""
import ast
import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
# Minimal test-only keyboard stubs if pyTelegramBotAPI is unavailable in the audit environment.
# The real production bot always uses pyTelegramBotAPI from requirements.txt.
try:
    from telebot import types as _bot_types
except ImportError:
    _fake_telebot = types.ModuleType("telebot")
    _fake_types = types.ModuleType("telebot.types")
    class _Button:
        def __init__(self, text):
            self.text = text
    class _Markup:
        def __init__(self, **kw):
            self.rows = []
        def row(self, *args):
            self.rows.append(args)
        def add(self, *args):
            self.rows.append(args)
    _fake_types.KeyboardButton = _Button
    _fake_types.ReplyKeyboardMarkup = _Markup
    _fake_telebot.types = _fake_types
    sys.modules.setdefault("telebot", _fake_telebot)
    sys.modules.setdefault("telebot.types", _fake_types)

from ui_v57 import ALL_UI_BUTTONS, CATEGORY_FEATURES
from user_help_v79 import find_tools, build_quick_help_text, register_user_help_v79_handlers


class FakeBot:
    def __init__(self):
        self.routes = []
        self.messages = []
    def message_handler(self, **options):
        def wrap(fn):
            self.routes.append((options, fn))
            return fn
        return wrap
    def send_message(self, cid, text, **kw):
        self.messages.append((cid, text))
    def deliver(self, message):
        for options, fn in self.routes:
            if message.text.startswith('/') and message.text.split()[0][1:] in options.get('commands', []):
                fn(message)
                return
        raise ValueError('unregistered command')


class FeatureFinderTests(unittest.TestCase):
    def test_short_help_complete_and_telegram_safe(self):
        text = build_quick_help_text()
        self.assertLess(len(text), 2500)
        for item in ['/guide', '/language', '/findtool', '/start', 'Ask My Notes']:
            self.assertIn(item, text)
        self.assertNotIn('V5.4', text)

    def test_help_is_available_in_four_languages(self):
        for language, distinctive in (("en", "Quick Help"), ("ta", "விரைவு உதவி"),
                                      ("si", "ඉක්මන් උදව්"), ("ar", "مساعدة سريعة")):
            text = build_quick_help_text(language)
            self.assertIn(distinctive, text)
            self.assertIn('/start', text)
            self.assertIn('/findtool', text)
            self.assertLess(len(text), 2500)

    def test_ui_categories_unchanged(self):
        self.assertEqual(len(CATEGORY_FEATURES), 8)
        self.assertIn('🔎 Find a Tool', ALL_UI_BUTTONS)
        from navigation import MAIN_MENU_ROWS, GLOBAL_BUTTONS
        self.assertEqual(sum(len(row) for row in MAIN_MENU_ROWS), 10)
        self.assertIn('🔎 Find a Tool', GLOBAL_BUTTONS)
        self.assertIn('⬅️ Main Menu', __import__('navigation').NAVIGATION_BUTTONS)

    def test_finder_covers_legacy_and_new_tools(self):
        for word, label in [('flashcard', '🧠 Flashcards'), ('தமிழ்', '🌐 Translate'),
                            ('collections', '📁 My Collections'), ('materialread', '📖 Material Reader'),
                            ('gpa', '📊 Grades & GPA')]:
            found = find_tools(word)
            self.assertTrue(any(name == label for name, _ in found), (word, found))
        self.assertEqual(find_tools('x'), [])
        self.assertEqual(find_tools('x'*95), [])

    def test_help_command_sends_valid_paths(self):
        bot = FakeBot()
        register_user_help_v79_handlers(bot)
        msg = types.SimpleNamespace(text='/findtool collections', chat=types.SimpleNamespace(id=19))
        bot.deliver(msg)
        self.assertIn('/collections', bot.messages[-1][1])
        bot.deliver(types.SimpleNamespace(text='/findtool unknownzzzz',chat=msg.chat))
        self.assertIn('No matching', bot.messages[-1][1])
        bot.deliver(types.SimpleNamespace(text='/findtool',chat=msg.chat))
        self.assertIn('Try /findtool', bot.messages[-1][1])


class SecurityAndWiringTests(unittest.TestCase):
    def test_compiles_all_top_level_source(self):
        for path in ROOT.glob('*.py'):
            ast.parse(path.read_text(encoding='utf-8'), filename=path.name)

    def test_all_core_bot_handlers_preserved(self):
        src = (ROOT/'main.py').read_text(encoding='utf-8')
        handlers = [
            'register_note_handlers(', 'register_study_material_handlers(',
            'register_pdf_handlers(', 'register_translation_handlers(',
            'register_ai_study_assistant_handlers(', 'register_study_context_handlers(',
            'register_spaced_repetition_handlers(', 'register_revision_hub_v66_handlers(',
            'register_system_health_handlers(', 'register_navigation_handlers(',
            'register_user_help_v79_handlers(',
        ]
        for item in handlers:
            self.assertIn(item, src, item)

    def test_setup_render_webhook_does_not_remove_live_webhook(self):
        src = (ROOT/'main.py').read_text(encoding='utf-8')
        module = ast.parse(src)
        fun = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'setup_render_webhook')
        code = ast.get_source_segment(src, fun)
        self.assertNotIn('bot.remove_webhook()', code)
        self.assertIn('bot.set_webhook(', code)
        self.assertIn('secret_token=WEBHOOK_SECRET', code)
        self.assertIn('"version": "7.9"', src)

    def test_internal_system_health_is_admin_only(self):
        fake_db = types.ModuleType('db')
        fake_db.supabase = object()
        path = ROOT/'system_health.py'
        module_name = '_v79_health_isolated'
        spec = importlib.util.spec_from_file_location(module_name, path)
        mod = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'db': fake_db}):
            spec.loader.exec_module(mod)
        bot = FakeBot()
        mod.register_system_health_handlers(bot)
        m = types.SimpleNamespace(text='/healthcheck', chat=types.SimpleNamespace(id=20,type='private'),
                                  from_user=types.SimpleNamespace(id=20))
        # Denied: no admin IDs means no DB operations.
        with patch.dict(os.environ, {'AI_OPS_ADMIN_IDS': ''}):
            bot.deliver(m)
        self.assertIn('admins only', bot.messages[-1][1])
        with patch.dict(os.environ, {'AI_OPS_ADMIN_IDS': '21,22'}):
            bot.deliver(m)
        self.assertIn('admins only', bot.messages[-1][1])
        # Admin can access the report; mock builder ensures no live DB.
        mod.build_health_report = lambda: 'TEST HEALTH OK'
        bot.delete_message = lambda *args: None
        # Return message ID needed by delete_message flow.
        orig_send = bot.send_message
        def send(cid, text, **kw):
            orig_send(cid,text,**kw)
            return types.SimpleNamespace(message_id=1)
        bot.send_message = send
        with patch.dict(os.environ, {'AI_OPS_ADMIN_IDS': '20,22'}):
            bot.deliver(m)
        self.assertIn('TEST HEALTH OK', bot.messages[-1][1])

    def test_upload_error_is_not_raw_exception_to_users(self):
        src = (ROOT/'study_materials.py').read_text(encoding='utf-8')
        self.assertIn("Couldn't save this material", src)
        self.assertNotIn('bot.send_message(\n                chat_id,\n                f"❌ {str(error)}"', src)

    def test_env_and_local_data_are_ignored_by_git(self):
        lines = set((ROOT/'.gitignore').read_text(encoding='utf-8').splitlines())
        self.assertTrue({'.env', '*.db', '__pycache__/', '*.zip'}.issubset(lines))
        self.assertIn('!.env.example', lines)


if __name__ == '__main__':
    unittest.main()
