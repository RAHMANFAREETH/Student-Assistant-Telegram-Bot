"""Mocked V5.4 Telegram/Supabase integration checks (no network or credentials)."""
import sys
import types
import unittest
from unittest.mock import MagicMock

if "telebot" not in sys.modules:
    try:
        import telebot  # noqa
    except ImportError:
        telebot = types.ModuleType("telebot")
        telebot.types = MagicMock()
        sys.modules["telebot"] = telebot

if "db" not in sys.modules:
    try:
        import db  # noqa
    except (ImportError, ValueError):
        fake_db = types.ModuleType("db")
        fake_db.supabase = MagicMock()
        sys.modules["db"] = fake_db

import spaced_repetition as sr


class Response:
    def __init__(self, data):
        self.data = data


class MockQuery:
    def __init__(self, database, table_name):
        self.database = database
        self.table_name = table_name
        self.filters = []
        self.start = 0
        self.end = 1000
        self.payload = None

    def select(self, *args):
        return self

    def eq(self, field, value):
        self.filters.append((field, str(value)))
        return self

    def range(self, start, end):
        self.start, self.end = start, end
        return self

    def limit(self, count):
        self.start, self.end = 0, count - 1
        return self

    def upsert(self, data, on_conflict=None):
        assert self.table_name == "flashcard_reviews"
        assert on_conflict == "user_id,flashcard_id"
        self.payload = data
        return self

    def execute(self):
        if self.payload is not None:
            self.database.reviews[(str(self.payload["user_id"]), str(self.payload["flashcard_id"]))] = dict(self.payload)
            return Response([self.payload])
        if self.table_name == "flashcards":
            # Must filter to the authenticated Telegram user on the server side.
            assert any(f == "user_id" for f, _ in self.filters), "Unfiltered flashcards read!"
            rows = self.database.cards
        elif self.table_name == "flashcard_reviews":
            assert any(f == "user_id" for f, _ in self.filters), "Unfiltered reviews read!"
            rows = list(self.database.reviews.values())
        else:
            raise AssertionError("Unexpected database table " + self.table_name)
        rows = [r for r in rows if all(str(r.get(f)) == value for f, value in self.filters)]
        return Response(rows[self.start:self.end + 1])


class MockDatabase:
    def __init__(self):
        self.cards = [
            {"id": 11, "user_id": 123, "subject_id": 7, "question": "Hello?", "answer": "World"},
            {"id": 12, "user_id": 123, "subject_id": None, "question": "What?", "answer": "Answer"},
            {"id": 99, "user_id": 999, "subject_id": 8, "question": "Private", "answer": "Secret"},
        ]
        self.reviews = {}

    def table(self, name):
        return MockQuery(self, name)


class MockBot:
    def __init__(self):
        self.messages = {}
        self.callbacks = {}
        self.outgoing = []
        self.callback_answers = []

    def message_handler(self, **kwargs):
        def decorator(fn):
            self.messages[fn.__name__] = fn
            return fn
        return decorator

    def callback_query_handler(self, **kwargs):
        def decorator(fn):
            self.callbacks[fn.__name__] = fn
            return fn
        return decorator

    def send_message(self, chat_id, text, **kwargs):
        self.outgoing.append((chat_id, text, kwargs))

    def answer_callback_query(self, *args, **kwargs):
        self.callback_answers.append((args, kwargs))


def telegram_message(chat_id=123, user_id=123, chat_type="private", text="/reviews"):
    return types.SimpleNamespace(chat=types.SimpleNamespace(id=chat_id, type=chat_type),
                                 from_user=types.SimpleNamespace(id=user_id), text=text)


def telegram_callback(data, chat_id=123, user_id=123):
    return types.SimpleNamespace(id="answer-me", data=data,
                                 message=types.SimpleNamespace(chat=types.SimpleNamespace(id=chat_id)),
                                 from_user=types.SimpleNamespace(id=user_id))


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.original_db = sr.supabase
        self.db = MockDatabase()
        sr.supabase = self.db
        sr._sessions.clear()
        self.bot = MockBot()
        sr.register_spaced_repetition_handlers(self.bot, lambda *args: None)

    def tearDown(self):
        sr.supabase = self.original_db
        sr._sessions.clear()

    def test_only_owned_cards_fetched_and_mapped(self):
        cards, reviews = sr._load_data(123)
        self.assertEqual([c["id"] for c in cards], ["11", "12"])
        self.assertEqual(cards[0]["subject"], "Subject #7")
        self.assertEqual(cards[1]["subject"], "Unassigned")
        self.assertEqual(reviews, {})

    def test_full_reveal_rate_and_stat_flow(self):
        self.bot.messages["due_command"](telegram_message())
        self.assertIn("Hello?", self.bot.outgoing[-1][1])
        session = sr._sessions[(123, 123)]
        self.bot.callbacks["review_callback"](telegram_callback(f"sr:s:{session['token']}"))
        self.assertIn("World", self.bot.outgoing[-1][1])
        self.bot.callbacks["review_callback"](telegram_callback(f"sr:r:{session['token']}:good"))
        review = self.db.reviews[("123", "11")]
        self.assertEqual(review["last_rating"], "good")
        self.assertEqual(review["interval_days"], 3)
        self.bot.messages["review_stats"](telegram_message(text="📊 Review Stats"))
        self.assertIn("Reviewed: 1", self.bot.outgoing[-1][1])
        self.assertIn("Due: 1", self.bot.outgoing[-1][1])

    def test_stale_button_cannot_double_rate(self):
        self.bot.messages["due_command"](telegram_message())
        token = sr._sessions[(123, 123)]["token"]
        self.bot.callbacks["review_callback"](telegram_callback(f"sr:s:{token}"))
        self.bot.callbacks["review_callback"](telegram_callback(f"sr:r:{token}:easy"))
        self.bot.callbacks["review_callback"](telegram_callback(f"sr:r:{token}:easy"))
        self.assertEqual(self.db.reviews[("123", "11")]["review_count"], 1)

    def test_other_user_cannot_operate_session(self):
        self.bot.messages["due_command"](telegram_message())
        token = sr._sessions[(123, 123)]["token"]
        self.bot.callbacks["review_callback"](telegram_callback(f"sr:s:{token}", user_id=999))
        self.assertEqual(sr._sessions[(123, 123)]["phase"], "question")
        self.assertFalse(self.db.reviews)

    def test_group_review_is_blocked(self):
        self.bot.messages["due_command"](telegram_message(chat_type="supergroup"))
        self.assertIn("private chat", self.bot.outgoing[-1][1])
        self.assertEqual(self.db.reviews, {})


if __name__ == "__main__":
    unittest.main()
