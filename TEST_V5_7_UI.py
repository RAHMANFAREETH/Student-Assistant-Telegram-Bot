"""Offline tests: python -m unittest TEST_V5_7_UI.py -v"""
import ast
import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

# Make tests run on standard Python as well as inside the bot's virtualenv.
try:
    from telebot import types as bot_types
except ImportError:
    fake_module = types.ModuleType("telebot")
    fake_types = types.ModuleType("telebot.types")

    class KeyboardButton:
        def __init__(self, text):
            self.text = text

    class ReplyKeyboardMarkup:
        def __init__(self, resize_keyboard=False, row_width=2):
            self.keyboard = []
        def row(self, *args):
            self.keyboard.append([{"text": v.text} for v in args])
        def to_dict(self):
            return {"keyboard": self.keyboard}

    fake_types.KeyboardButton = KeyboardButton
    fake_types.ReplyKeyboardMarkup = ReplyKeyboardMarkup
    fake_module.types = fake_types
    sys.modules["telebot"] = fake_module
    sys.modules["telebot.types"] = fake_types

import ui_v57 as ui
from INSTALL_V5_7 import patch_main, patch_navigation


class FakeBot:
    def __init__(self):
        self.registrations = []
        self.sent = []

    def message_handler(self, **kw):
        def wrap(fn):
            self.registrations.append((kw, fn))
            return fn
        return wrap

    def send_message(self, chat_id, body, **kw):
        self.sent.append((chat_id, body, kw))

    def deliver(self, text, user_id=27, chat_type="private", first_name="Test"):
        chat = types.SimpleNamespace(id=user_id, type=chat_type)
        from_user = types.SimpleNamespace(id=user_id, first_name=first_name)
        message = types.SimpleNamespace(chat=chat, from_user=from_user, text=text)
        for predicates, handler in self.registrations:
            if text.startswith("/") and text[1:].split()[0] in predicates.get("commands", []):
                handler(message)
                return handler.__name__
            if "func" in predicates and predicates["func"](message):
                handler(message)
                return handler.__name__
        return None


class UITests(unittest.TestCase):
    def setUp(self):
        ui._PREFS.clear()
        # Keep tests offline: do not fetch UI language from Supabase.
        ui._cache_set(27, "en")
        self.bot = FakeBot()
        self.menus = []

        def show_menu(chat_id, first_name="Friend"):
            self.menus.append((chat_id, first_name))
        ui.register_ui_v57_handlers(self.bot, show_menu)

    def test_eight_categories_all_legacy_features(self):
        self.assertEqual(len(ui.CATEGORY_FEATURES), 8)
        labels = [x for buttons in ui.CATEGORY_FEATURES.values() for x in buttons]
        for label in ["🤖 Ask AI", "📝 Ask My Notes", "📄 Ask My PDF", "🎙 Voice Notes",
                      "📄 PDF Tools", "🧠 Flashcards", "📢 Student Resources", "📊 Review Stats"]:
            self.assertIn(label, labels)
        self.assertEqual(len(labels), len(set(labels)))

    def test_category_contains_original_buttons_and_back(self):
        # Inspect the requested button labels rather than version-specific
        # ReplyKeyboardMarkup internals (.rows/.to_dict/.keyboard).
        # This remains compatible with different pyTelegramBotAPI releases.
        with patch.object(ui, "_keyboard", wraps=ui._keyboard) as make_keyboard:
            self.bot.deliver(ui.CAT_AI)
        make_keyboard.assert_called_once()
        button_labels = make_keyboard.call_args.args[0]
        self.assertIn("🤖 Ask AI", button_labels)
        self.assertIn("📝 Ask My Notes", button_labels)
        self.assertIn("📄 Ask My PDF", button_labels)
        self.assertIn(ui.BACK_CATEGORIES, button_labels)

    def test_original_feature_buttons_not_intercepted(self):
        self.assertIsNone(self.bot.deliver("🧠 Flashcards"))
        self.assertIsNone(self.bot.deliver("📄 Ask My PDF"))
        self.assertIsNone(self.bot.deliver("🤖 Ask AI"))

    def test_help_and_commands(self):
        self.assertEqual(self.bot.deliver("/guide"), "command_help")
        self.assertIn("Help", self.bot.sent[-1][1])
        self.assertEqual(self.bot.deliver("📄 Ask My PDF Guide"), "ui_button")
        self.assertIn("📚 Study Materials", self.bot.sent[-1][1])
        self.assertEqual(self.bot.deliver("↩️ All Categories"), "ui_button")
        self.assertEqual(len(self.menus), 1)

    def test_multilingual_guidance(self):
        for lng in ["en", "ta", "si", "ar"]:
            ui._cache_set(27, lng)
            self.bot.deliver(ui.CAT_STUDY)
            self.assertIn(ui.CATEGORY_TEXT[lng][ui.CAT_STUDY], self.bot.sent[-1][1])
        self.assertIn("மாணவர்", ui.TEXT["ta"]["welcome"])
        self.assertIn("مساعد", ui.TEXT["ar"]["welcome"])

    def test_language_change_works_when_db_missing(self):
        with patch.object(ui, "set_language", side_effect=lambda uid, lang: (ui._cache_set(uid, lang) or False)):
            self.bot.deliver("🇱🇰 தமிழ்")
            self.assertEqual(ui.get_language(27), "ta")
            self.assertIn("தமிழ்", self.bot.sent[-1][1])
            self.assertEqual(len(self.menus), 1)

    def test_language_change_denied_for_group(self):
        self.bot.deliver("🇱🇰 தமிழ்", chat_type="supergroup")
        self.assertIn("private", self.bot.sent[-1][1].lower())

    def test_guide_content_covers_core_student_flows(self):
        for topic in ui.GUIDES:
            self.assertEqual(set(ui.GUIDES[topic]), {"en", "ta", "si", "ar"})
            for body in ui.GUIDES[topic].values():
                self.assertTrue(len(body) > 30)

    def test_menu_greeting_sanitizes_very_long_first_name(self):
        ui._cache_set(27, "en")
        greeting = ui.greeting("A" * 200, 27)
        self.assertLess(len(greeting), 300)

    def test_ui_button_set_complete(self):
        self.assertIn(ui.HELP_CENTER, ui.ALL_UI_BUTTONS)
        self.assertIn(ui.LANGUAGE_MENU, ui.ALL_UI_BUTTONS)
        self.assertTrue(set(ui.GUIDE_BUTTONS).issubset(ui.ALL_UI_BUTTONS))


class InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        here = Path(__file__).parent
        # Use full V5.6 integrated main/navigation when tests are run in a
        # prepared project. The synthetic source below ensures patch logic
        # also works outside a full project.
        cls.main = '''from navigation import (\n    build_main_menu_markup,\n)\n\nfrom telebot import types\n\nbot = object()\n\ndef show_main_menu(chat_id, first_name="Friend"):\n    bot.send_message(chat_id, "Welcome", reply_markup=build_main_menu_markup())\n\nfrom study_context_ai import register_study_context_handlers\nfrom ai_study_assistant import register_ai_study_assistant_handlers\n\nregister_study_context_handlers(bot, show_main_menu)\nregister_ai_study_assistant_handlers(bot, show_main_menu)\n\n"""Other code"""\n'''
        cls.nav = '''from telebot import types\nASK_PDF = "📄 Ask My PDF"\nREVIEW_STATS = "📊 Review Stats"\nMAIN_MENU_ROWS = [\n    ("🤖 Ask AI",),\n    ("📄 Ask My PDF",),\n    ("🧠 Flashcards",),\n]\nGLOBAL_BUTTONS = {button for row in MAIN_MENU_ROWS for button in row}\nGLOBAL_BUTTONS.add(REVIEW_STATS)\nNAVIGATION_BUTTONS = {"🏠 Main Menu"}\nALL_NAVIGATION_BUTTONS = GLOBAL_BUTTONS | NAVIGATION_BUTTONS\n\ndef build_main_menu_markup():\n    keyboard = types.ReplyKeyboardMarkup()\n    for row in MAIN_MENU_ROWS:\n        keyboard.row(*[types.KeyboardButton(s) for s in row])\n    return keyboard\n'''

    def test_patch_main_and_idempotence(self):
        updated, changed = patch_main(self.main)
        self.assertTrue(changed)
        ast.parse(updated)
        self.assertIn("greeting(first_name, chat_id)", updated)
        self.assertLess(updated.index("register_ui_v57_handlers(bot, show_main_menu)"),
                        updated.index("register_study_context_handlers(bot, show_main_menu)"))
        again, changed = patch_main(updated)
        self.assertFalse(changed)
        self.assertEqual(updated, again)

    def test_patch_navigation_and_idempotence(self):
        new, changed = patch_navigation(self.nav)
        self.assertTrue(changed)
        self.assertIn("LEGACY_MENU_ROWS = MAIN_MENU_ROWS", new)
        self.assertIn("GLOBAL_BUTTONS.update(button for row in LEGACY_MENU_ROWS", new)
        self.assertIn('UI_LANGUAGE = "🌐 Menu Language"', new)
        ast.parse(new)
        again, changed = patch_navigation(new)
        self.assertFalse(changed)
        self.assertEqual(new, again)

    def test_pre_v56_project_rejected(self):
        with self.assertRaisesRegex(ValueError, "V5.6"):
            patch_main(self.main.replace("register_study_context_handlers", "not_a_context_handler"))


if __name__ == "__main__":
    unittest.main()
