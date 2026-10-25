"""Offline V6.5.1 navigation compatibility tests. No Telegram/network calls."""
from __future__ import annotations

from contextlib import contextmanager
import ast
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import INSTALL_V6_5_1 as upgrade

ROOT = Path(__file__).resolve().parent


def get_existing(name):
    """Use project source or the versioned pre-install backup (never modify either)."""
    backup = ROOT / (name + ".before_v651.bak")
    path = backup if backup.exists() else ROOT / name
    if not path.is_file():
        raise AssertionError(f"Missing project source file: {path.name}")
    with path.open("r", encoding="utf-8", newline="") as f:
        return f.read()


def stage(root: Path):
    for name in upgrade.TARGETS:
        (root / name).write_text(get_existing(name), encoding="utf-8", newline="")


@contextmanager
def loaded_sample(root):
    """Import patched modules with fake Telegram, database; zero network."""
    fake_telebot = types.ModuleType("telebot")
    fake_types = types.ModuleType("telebot.types")

    class KeyboardButton:
        def __init__(self, text):
            self.text = text

    class ReplyKeyboardMarkup:
        def __init__(self, **kwargs):
            self.buttons = []
        def row(self, *buttons):
            self.buttons.append([button.text for button in buttons])
        def add(self, *buttons):
            self.row(*buttons)

    fake_types.KeyboardButton = KeyboardButton
    fake_types.ReplyKeyboardMarkup = ReplyKeyboardMarkup
    fake_telebot.types = fake_types
    fake_db = types.ModuleType("db")
    fake_db.supabase = object()  # Any accidental write would fail the test.

    saved = {name: sys.modules.get(name) for name in
             ("telebot", "telebot.types", "db", "navigation", "navigation_handlers", "notes", "reminders")}
    sys.modules.update({"telebot": fake_telebot, "telebot.types": fake_types, "db": fake_db})

    def load(name):
        spec = importlib.util.spec_from_file_location(name, root / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    try:
        nav = load("navigation")
        nav_handlers = load("navigation_handlers")
        notes = load("notes")
        reminders = load("reminders")
        yield nav, nav_handlers, notes, reminders
    finally:
        for name, old in saved.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


class TestFix(unittest.TestCase):
    def test_parses_and_keeps_other_modules_unchanged(self):
        for name in upgrade.TARGETS:
            patched, _ = upgrade.patch_text(name, get_existing(name))
            ast.parse(patched)
            self.assertEqual(upgrade.patch_text(name, patched), (patched, False))

    def test_both_buttons_registered_for_navigation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            stage(root)
            upgrade.install(root)
            with loaded_sample(root) as (nav, _, _, _):
                for text in ("⬅️ Main Menu", "🏠 Main Menu"):
                    self.assertTrue(nav.is_navigation_button(text))
                    self.assertTrue(nav.should_yield_to_navigation(text))

    def test_legacy_label_is_not_rendered_any_more(self):
        for name in ("notes.py", "reminders.py"):
            patched, _ = upgrade.patch_text(name, get_existing(name))
            self.assertNotIn('types.KeyboardButton("⬅️ Main Menu")', patched)
            self.assertIn('"🏠 Main Menu"', patched)

    def test_global_handler_and_notes_active_state(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            stage(root)
            upgrade.install(root)
            with loaded_sample(root) as (nav, nav_handlers, notes, reminders):
                self._exercise_handlers(nav_handlers, notes, reminders)

    def _exercise_handlers(self, nav_handlers, notes, reminders):
        class Bot:
            def __init__(self):
                self.handlers = []
                self.messages = []
            def message_handler(self, func=None, **kwargs):
                def decorator(fn):
                    self.handlers.append((func, fn))
                    return fn
                return decorator
            def send_message(self, chat_id, text, **kwargs):
                self.messages.append((chat_id, text, kwargs))

        bot = Bot()
        menus = []
        def show_main_menu(chat_id, first_name):
            menus.append((chat_id, first_name))
        notes.register_note_handlers(bot, show_main_menu)
        reminders.register_reminder_handlers(bot, show_main_menu)
        nav_handlers.register_navigation_handlers(bot, show_main_menu)

        def route(label):
            msg = types.SimpleNamespace(
                text=label,
                chat=types.SimpleNamespace(id=989, type="private"),
                from_user=types.SimpleNamespace(id=989, first_name="Student"))
            for predicate, callback in bot.handlers:
                if predicate and predicate(msg):
                    callback(msg)
                    return
            self.fail(f"No handler for {label}")

        route("📝 Notes")
        note_markup = bot.messages[-1][2]["reply_markup"]
        self.assertIn("🏠 Main Menu", [b for r in note_markup.buttons for b in r])
        route("⬅️ Main Menu")  # Stale old keyboard is accepted when idle.
        self.assertEqual(menus[-1], (989, "Student"))
        route("➕ Add Note")
        self.assertIn(989, notes.note_mode)
        route("⬅️ Main Menu")  # No accidental note title save.
        self.assertNotIn(989, notes.note_mode)
        self.assertNotIn(989, notes.temp_note)
        self.assertEqual(menus[-1], (989, "Student"))
        route("➕ Add Note")
        route("🏠 Main Menu")
        self.assertNotIn(989, notes.note_mode)

        route("⏰ Study Reminder")
        reminder_markup = bot.messages[-1][2]["reply_markup"]
        self.assertIn("🏠 Main Menu", [b for r in reminder_markup.buttons for b in r])
        route("⬅️ Main Menu")
        self.assertEqual(menus[-1], (989, "Student"))
        route("➕ Add Reminder")
        self.assertIn(989, reminders.reminder_state)
        route("⬅️ Main Menu")
        self.assertNotIn(989, reminders.reminder_state)
        self.assertNotIn(989, reminders.temp_reminder)
        route("➕ Add Reminder")
        route("🏠 Main Menu")
        self.assertNotIn(989, reminders.reminder_state)

    def test_windows_crlf(self):
        for name in upgrade.TARGETS:
            source = get_existing(name).replace("\r\n", "\n").replace("\n", "\r\n")
            patched, changed = upgrade.patch_text(name, source)
            self.assertTrue(changed or 'LEGACY_MAIN_MENU' in patched or '# V6.5.1' in patched)
            self.assertNotIn("\r\r\n", patched)
            ast.parse(patched)

    def test_install_idempotent_and_backup(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            stage(root)
            originals = {n: (root/n).read_bytes() for n in upgrade.TARGETS}
            updated = upgrade.install(root)
            self.assertEqual(set(updated), set(upgrade.TARGETS))
            self.assertEqual(upgrade.install(root), [])
            for name in upgrade.TARGETS:
                self.assertEqual((root/(name+'.before_v651.bak')).read_bytes(), originals[name])
            self.assertEqual(list(root.glob('.v651_*.tmp')), [])

    def test_preflight_blocks_missing_file_without_edit(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            stage(root)
            (root/"reminders.py").unlink()
            originals = {n: (root/n).read_bytes() for n in upgrade.TARGETS[:-1]}
            with self.assertRaises(ValueError):
                upgrade.install(root)
            for name, data in originals.items():
                self.assertEqual((root/name).read_bytes(), data)

    def test_refuse_unrecognized_source(self):
        name = "navigation_handlers.py"
        with self.assertRaises(ValueError):
            upgrade.patch_text(name, get_existing(name).replace('m.text in {', 'm.text == {'))


if __name__ == '__main__':
    unittest.main()
