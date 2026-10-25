"""Offline tests for the V5.8 Achievements add-on (no live API credentials)."""
import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

try:
    from telebot import types as telegram_types
except ImportError:
    fake = types.ModuleType("telebot")
    fake_types = types.ModuleType("telebot.types")

    class KeyboardButton:
        def __init__(self, text):
            self.text = text

    class ReplyKeyboardMarkup:
        def __init__(self, resize_keyboard=False, row_width=2):
            self.keyboard = []

        def row(self, *buttons):
            self.keyboard.append(list(buttons))

    fake_types.KeyboardButton = KeyboardButton
    fake_types.ReplyKeyboardMarkup = ReplyKeyboardMarkup
    fake.types = fake_types
    sys.modules.setdefault("telebot", fake)
    sys.modules.setdefault("telebot.types", fake_types)

import achievements_v58 as a
import INSTALL_V5_8 as installer


class Query:
    def __init__(self, rows, error=None):
        self.rows = list(rows)
        self.conditions = []
        self.offset = None
        self.slice_size = None
        self.limit_count = None
        self.error = error
        self.columns = ""
        self.exact = False

    def select(self, columns, count=None):
        self.columns = columns
        self.exact = count == "exact"
        return self

    def eq(self, key, value):
        self.conditions.append(("eq", key, value))
        return self

    def gte(self, key, value):
        self.conditions.append(("gte", key, value))
        return self

    def limit(self, n):
        self.limit_count = n
        return self

    def order(self, *args, **kwargs):
        return self

    def range(self, start, end):
        self.offset = start
        self.slice_size = end - start + 1
        return self

    def execute(self):
        if self.error:
            raise self.error
        data = self.rows
        for op, k, v in self.conditions:
            if op == "eq":
                data = [r for r in data if r.get(k) == v]
            elif op == "gte":
                data = [r for r in data if r.get(k) is not None and r.get(k) >= v]
        count = len(data)
        if self.offset is not None:
            data = data[self.offset:self.offset + self.slice_size]
        elif self.limit_count is not None:
            data = data[:self.limit_count]
        return types.SimpleNamespace(data=data, count=count if self.exact else None)


class DB:
    def __init__(self, data):
        self.data = data
        self.called = []

    def table(self, name):
        self.called.append(name)
        return Query(self.data.get(name, []))


class FakeBot:
    def __init__(self):
        self.registered = []
        self.sent = []

    def message_handler(self, **kwargs):
        def decorator(callback):
            self.registered.append((kwargs, callback))
            return callback
        return decorator

    def send_message(self, chat, message, **kwargs):
        self.sent.append((chat, message, kwargs))

    def deliver(self, text, user_id=100, chat_id=100, chat_type="private"):
        message = types.SimpleNamespace(
            text=text,
            chat=types.SimpleNamespace(type=chat_type, id=chat_id),
            from_user=types.SimpleNamespace(id=user_id, first_name="Student"),
        )
        for spec, handler in self.registered:
            if text.startswith("/") and text[1:].split("@")[0] in spec.get("commands", []):
                return handler(message)
            if "func" in spec and spec["func"](message):
                return handler(message)
        raise AssertionError("No matching handler")


class MilestoneTests(unittest.TestCase):
    def metrics(self, **edits):
        base = {"notes": 0, "cards": 0, "reviewed": 0, "quizzes": 0,
                "perfect_quizzes": 0, "assignments": 0, "goals": 0,
                "sessions": 0, "streak": 0}
        base.update(edits)
        return base

    def test_new_student_has_level_one_and_no_badges(self):
        r = a.evaluate(self.metrics())
        self.assertEqual(r["level"], 1)
        self.assertEqual(r["xp"], 0)
        self.assertEqual(len(r["unlocked"]), 0)

    def test_unlocks_real_milestones(self):
        r = a.evaluate(self.metrics(notes=10, cards=25, quizzes=1, streak=3))
        keys = {b.key for b in r["unlocked"]}
        self.assertTrue({"first_note", "notes_10", "first_cards", "cards_25", "first_quiz", "streak_3"}.issubset(keys))
        self.assertNotIn("streak_7", keys)

    def test_xp_does_not_increase_when_achievements_checked(self):
        m = self.metrics(notes=3, cards=8, assignments=2)
        self.assertEqual(a.evaluate(m)["xp"], a.evaluate(m)["xp"])
        self.assertEqual(a.evaluate(m)["xp"], 3*10 + 8*5 + 2*30)

    def test_levels_boundary(self):
        r = a.evaluate(self.metrics(notes=25))
        self.assertEqual((r["level"], r["level_xp"], r["remaining"]), (2, 0, 250))

    def test_four_languages_render(self):
        for lang in ("en", "ta", "si", "ar"):
            self.assertIn("XP", a.format_level(self.metrics(notes=4), lang))
            self.assertIn("4/10", a.format_achievements(self.metrics(notes=4), lang))

    def test_no_more_than_telegram_message_limit(self):
        m = self.metrics(**{k: 9999 for k in self.metrics()})
        self.assertLess(len(a.format_achievements(m)), 4096)

    def test_streak_allows_unfinished_today(self):
        today = datetime(2026, 10, 24).date()
        d = {today - timedelta(days=1): 70, today - timedelta(days=2): 90,
             today - timedelta(days=3): 60}
        self.assertEqual(a.compute_streak(d, 60, today=today), 3)

    def test_streak_breaks_when_yesterday_missed(self):
        today = datetime(2026, 10, 24).date()
        d = {today - timedelta(days=2): 70}
        self.assertEqual(a.compute_streak(d, 60, today=today), 0)

    def test_user_scoped_counts_and_exact_counts_over_1000(self):
        rows = [{"user_id": 100, "id": i} for i in range(1201)] + [{"user_id": 200, "id": 1}]
        client = DB({"notes": rows})
        self.assertEqual(a.count_records(client, "notes", 100), 1201)

    def test_completed_status_only(self):
        db = DB({"assignments": [{"id": 1, "user_id": 100, "status": "completed"},
                                 {"id": 2, "user_id": 100, "status": "pending"},
                                 {"id": 3, "user_id": 200, "status": "completed"}]})
        self.assertEqual(a.count_records(db, "assignments", 100, equals={"status":"completed"}), 1)

    def test_reviewed_card_requires_review_count(self):
        db = DB({"flashcard_reviews": [
            {"user_id": 100, "flashcard_id": "a", "review_count": 2},
            {"user_id": 100, "flashcard_id": "b", "review_count": 0},
        ]})
        self.assertEqual(a.count_records(db, "flashcard_reviews", 100, minimum={"review_count": 1}), 1)

    def test_streak_uses_existing_preference_and_local_day(self):
        now = datetime(2026, 10, 24, 21, 0, tzinfo=a.TZ)
        rows = [
            {"user_id": 100, "status": "completed", "started_at":
             datetime(2026, 10, 23, 8, tzinfo=a.TZ).astimezone(timezone.utc).isoformat(),
             "actual_minutes": 35, "planned_minutes": 45},
            {"user_id": 100, "status": "completed", "started_at":
             datetime(2026, 10, 23, 9, tzinfo=a.TZ).isoformat(),
             "actual_minutes": 30, "planned_minutes": 45},
            {"user_id": 200, "status": "completed", "started_at":
             datetime(2026, 10, 24, 7, tzinfo=a.TZ).isoformat(),
             "actual_minutes": 90, "planned_minutes": 90},
        ]
        db = DB({"study_preferences": [{"user_id": 100, "daily_target_minutes": 60}],
                 "study_sessions": rows})
        self.assertEqual(a.recent_streak(db, 100, now=now), 1)

    def test_missing_count_fails_not_zero(self):
        q = Query([])
        q.execute = lambda: types.SimpleNamespace(data=[], count=None)
        client = types.SimpleNamespace(table=lambda _: q)
        with self.assertRaises(a.ProgressUnavailable):
            a.count_records(client, "notes", 100)

    def test_handler_refuses_group_without_database_lookup(self):
        bot = FakeBot()
        with patch.dict(sys.modules, {"ui_v57": types.SimpleNamespace(get_language=lambda uid:"ta")}):
            a.register_achievements_v58_handlers(bot, lambda *_:None)
            bot.deliver("/achievements", user_id=100, chat_type="supergroup")
        self.assertIn("private", bot.sent[-1][1].lower())

    def test_handler_uses_sender_id_not_chat_id(self):
        bot = FakeBot()
        client = DB({})
        seen = []
        fake_db = types.ModuleType("db")
        fake_db.supabase = client
        fake_ui = types.ModuleType("ui_v57")
        fake_ui.get_language = lambda uid: "en"
        with patch.dict(sys.modules, {"db": fake_db, "ui_v57":fake_ui}):
            with patch.object(a, "collect_metrics", side_effect=lambda c, user_id: (seen.append(user_id) or self.metrics(notes=1))):
                a.register_achievements_v58_handlers(bot, lambda *_:None)
                bot.deliver("🏆 Achievements", user_id=100, chat_id=999)
        self.assertEqual(seen, [100])
        self.assertIn("First Note", bot.sent[-1][1])

    def test_handler_avoids_false_zero_on_db_error(self):
        bot = FakeBot()
        fake_db = types.ModuleType("db")
        fake_db.supabase = DB({})
        fake_ui = types.ModuleType("ui_v57")
        fake_ui.get_language = lambda uid: "en"
        with patch.dict(sys.modules, {"db": fake_db, "ui_v57": fake_ui}):
            with patch.object(a, "collect_metrics", side_effect=RuntimeError("secret details")):
                a.register_achievements_v58_handlers(bot, lambda *_:None)
                bot.deliver("/level")
        self.assertIn("temporarily unavailable", bot.sent[-1][1])
        self.assertNotIn("secret details", bot.sent[-1][1])


class InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).parent
        cls.main = (root / "main.py").read_text(encoding="utf-8") if (root / "main.py").exists() else (
            'from ui_v57 import greeting, register_ui_v57_handlers\n'
            'bot=None\ndef show_main_menu(chat_id): pass\n'
            'register_ui_v57_handlers(bot, show_main_menu)\n')
        cls.nav = (root / "navigation.py").read_text(encoding="utf-8") if (root / "navigation.py").exists() else (
            '# V5.7 CATEGORY MENU START\nGLOBAL_BUTTONS=set()\n'
            'NAVIGATION_BUTTONS = {}\nALL_NAVIGATION_BUTTONS = GLOBAL_BUTTONS | NAVIGATION_BUTTONS\n')
        cls.ui = (root / "ui_v57.py").read_text(encoding="utf-8") if (root / "ui_v57.py").exists() else (
            'from collections import OrderedDict\n'
            'CAT_PROGRESS = "📊 My Progress"\n'
            'CATEGORY_FEATURES = OrderedDict([(CAT_PROGRESS, ["🔥 Study Streak", "🧠 Smart Insights"])])\n')

    def test_patch_main_idempotent(self):
        code, _ = installer.patch_main(self.main)
        self.assertIn(installer.REGISTRATION, code)
        ast.parse(code)
        self.assertFalse(installer.patch_main(code)[1])

    def test_patch_navigation_idempotent(self):
        code, _ = installer.patch_navigation(self.nav)
        self.assertIn('GLOBAL_BUTTONS.update({"🏆 Achievements", "⭐ My Level"})', code)
        ast.parse(code)
        self.assertFalse(installer.patch_navigation(code)[1])

    def test_patch_ui_idempotent(self):
        code, _ = installer.patch_ui(self.ui)
        self.assertIn('"🏆 Achievements", "⭐ My Level"', code)
        ast.parse(code)
        self.assertFalse(installer.patch_ui(code)[1])

    def test_old_main_rejected(self):
        with self.assertRaisesRegex(ValueError, "V5.7"):
            installer.patch_main("def show_main_menu(chat_id): pass\n")

    def test_existing_files_untouched_in_preflight_failure(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for filename, content in {"main.py":self.main, "navigation.py":self.nav,
                                      "ui_v57.py":"broken python!!!", "achievements_v58.py":"# module"}.items():
                (root / filename).write_text(content, encoding="utf-8")
            original = (root / "main.py").read_bytes()
            with self.assertRaises((ValueError, SyntaxError)):
                installer.run_install(root)
            self.assertEqual(original, (root / "main.py").read_bytes())

    def test_installer_patches_existing_v57_project(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for filename, content in {"main.py":self.main, "navigation.py":self.nav,
                                      "ui_v57.py":self.ui, "achievements_v58.py":"# module"}.items():
                (root / filename).write_text(content, encoding="utf-8")
            changed = installer.run_install(root)
            self.assertTrue(changed or installer.MAIN_IMPORT in self.main)
            self.assertEqual(installer.run_install(root), [])
            self.assertIn(installer.REGISTRATION,(root / "main.py").read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
