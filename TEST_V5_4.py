"""Tests of scheduling math without calling Telegram or Supabase."""
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

# The module imports telebot/db only; replace these if SDKs aren't installed
# in the local test environment. Existing runtime imports still use real SDKs.
try:
    import telebot
except ImportError:
    fake = types.ModuleType("telebot")
    fake.types = MagicMock()
    sys.modules["telebot"] = fake
try:
    import db
except ImportError:
    fake = types.ModuleType("db")
    fake.supabase = MagicMock()
    sys.modules["db"] = fake

from spaced_repetition import next_schedule, choose_due

NOW = datetime(2026, 10, 23, tzinfo=timezone.utc)


class SrsTests(unittest.TestCase):
    def test_new_card_intervals(self):
        for rating, days in [("hard", 1), ("good", 3), ("easy", 7)]:
            result = next_schedule(None, rating, NOW)
            self.assertEqual(result["interval_days"], days)
            self.assertEqual(result["review_count"], 1)

    def test_again_ten_minutes(self):
        result = next_schedule({"interval_days": 12, "repetitions": 4,
                                "ease_factor": 2.5, "review_count": 6}, "again", NOW)
        self.assertEqual(result["repetitions"], 0)
        self.assertEqual(datetime.fromisoformat(result["due_at"]), NOW + timedelta(minutes=10))
        self.assertEqual(result["review_count"], 7)

    def test_due(self):
        cards = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        reviews = {"2": {"due_at": (NOW + timedelta(days=1)).isoformat()},
                   "3": {"due_at": (NOW - timedelta(days=1)).isoformat()}}
        self.assertEqual([c["id"] for c in choose_due(cards, reviews, NOW)], ["1", "3"])

    def test_invalid_rating(self):
        with self.assertRaises(ValueError):
            next_schedule(None, "wrong", NOW)


if __name__ == "__main__":
    unittest.main()
