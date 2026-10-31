"""Offline checks for the V11.1 public library / five most recent books patch.

Run AFTER applying the patch:
python -m unittest TEST_BOOK_LIBRARY TEST_BOOK_PUBLIC_LATEST5 -q
"""
import os
import sys
import types
import uuid
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import book_library_bot as lib
from book_library_store import latest_books
from PATCH_BOOK_LIBRARY_PUBLIC_LATEST5 import transform, integrate
from TEST_BOOK_LIBRARY import FakeBot, FakeDb, FakeButton, FakeMarkup, ContinueHandling, fake_message


class PatchInstallerTests(unittest.TestCase):
    def test_idempotent(self):
        for name in ('book_library_bot.py', 'book_library_store.py'):
            original = (HERE/name).read_text(encoding='utf-8')
            self.assertEqual(transform(name, original), original)

    def test_check_changes_nothing_when_applied(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            for name in ('book_library_bot.py', 'book_library_store.py'):
                (root/name).write_bytes((HERE/name).read_bytes())
            self.assertEqual(integrate(root, apply=False, output=lambda _: None), [])
            self.assertEqual(integrate(root, apply=True, output=lambda _: None), [])
            self.assertEqual(list(root.glob('BOOK_PUBLIC_LATEST5_BACKUP_*')), [])


class CatalogTests(unittest.TestCase):
    def test_latest_defaults_to_five(self):
        db = FakeDb([{'id': str(uuid.uuid4()), 'title': 'A'}])
        latest_books(db=db)
        self.assertIn(('limit', (5,)), db.query.calls)
        self.assertIn(('eq', ('active', True)), db.query.calls)
        self.assertIn(('order', ('added_at',)), db.query.calls)

    def test_only_active_catalog_books(self):
        db = FakeDb([])
        latest_books(db=db)
        self.assertIn(('eq', ('active', True)), db.query.calls)


class PublicTelegramTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            'BOOK_LIBRARY_ENABLED': 'true',
            'BOOK_LIBRARY_ADMIN_IDS': '7',
            'BOOK_LIBRARY_CHANNEL_ID': '-1003000',
            'BOOK_LIBRARY_ALLOW_ALL_GROUPS': 'true',
            'BOOK_LIBRARY_GROUP_IDS': '',
            'BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT': 'false',
            'BOOK_LIBRARY_BOT_USERNAME': 'TestStudyBot',
            'BOOK_LIBRARY_AUTO_GROUP_SEARCH': 'false',
        })
        self.env.start()
        telebot = types.ModuleType('telebot')
        telebot.types = types.SimpleNamespace(
            InlineKeyboardMarkup=FakeMarkup, InlineKeyboardButton=FakeButton)
        backend = types.ModuleType('telebot.handler_backends')
        backend.ContinueHandling = ContinueHandling
        self.mods = patch.dict(sys.modules, {'telebot': telebot, 'telebot.handler_backends': backend})
        self.mods.start()
        self.bot = FakeBot()
        lib._pending.clear()
        lib._throttle.clear()
        lib._username = None
        lib.register_book_library_handlers(self.bot)
        self.handlers = {}
        for opts, fn in self.bot.message_handlers:
            for cmd in opts.get('commands', []):
                self.handlers[cmd] = fn

    def tearDown(self):
        self.mods.stop()
        self.env.stop()

    def test_public_private_menu(self):
        self.assertTrue(lib._verified(912342342))
        lib._menu(self.bot, fake_message(user=12))
        self.assertIn('Book Library', self.bot.sent[-1][1])

    def test_group_allowed_without_id_list(self):
        self.assertTrue(lib._allowed_group(-100123456))
        # The actual catalog may have no match and group searches intentionally
        # stay silent in that case. Mock a result so this test remains offline.
        book = {'id': str(uuid.uuid4()), 'title': 'Ihya Ulumuddin',
                'author': 'Al-Ghazali', 'language': 'Arabic', 'file_size': 12345}
        with patch.object(lib, 'search_books', return_value=[book]):
            self.handlers['book'](fake_message(user=23, chat=-100123456,
                                                kind='supergroup', text='/book Ihya'))
        self.assertTrue(self.bot.sent)
        self.assertIn('Book results for:', self.bot.sent[-1][1])
        self.assertNotIn('not enabled in this group', self.bot.sent[-1][1])

    def test_group_opt_in_false_keeps_allowlist(self):
        with patch.dict(os.environ, {'BOOK_LIBRARY_ALLOW_ALL_GROUPS': 'false', 'BOOK_LIBRARY_GROUP_IDS': '-1009009'}):
            self.assertFalse(lib._allowed_group(-100123456))
            self.assertTrue(lib._allowed_group(-1009009))

    def test_group_latest_uses_five(self):
        books = [dict(id=str(uuid.uuid4()), title=f'Title {i}', author='Author', language='English', file_size=i*1024) for i in range(5)]
        with patch.object(lib, 'latest_books', return_value=books) as read:
            self.handlers['booklatest'](fake_message(user=23, chat=-100123456, kind='supergroup', text='/booklatest'))
        read.assert_called_once_with(limit=5)
        self.assertIn('Latest Books (5', self.bot.sent[-1][1])
        self.assertEqual(len(self.bot.sent[-1][2]['reply_markup'].buttons), 5)

    def test_private_latest_callback_uses_five(self):
        with patch.object(lib, 'latest_books', return_value=[]) as read:
            lib._latest(self.bot, 23)
        read.assert_called_once_with(limit=5)

    def test_group_books_no_args_shows_latest(self):
        with patch.object(lib, 'latest_books', return_value=[]) as read:
            self.handlers['books'](fake_message(user=23, chat=-100123456, kind='group', text='/books'))
        read.assert_called_once_with(limit=5)
        self.assertIn('No books have been added yet', self.bot.sent[-1][1])

    def test_group_search_does_not_process_free_text_by_default(self):
        group_handler = next(opts['func'] for opts, fn in self.bot.message_handlers if fn.__name__ == 'group_search')
        self.assertFalse(group_handler(fake_message(user=23, chat=-100123456, kind='group', text='Ihya')))

    def test_deliver_file_without_adult_gate(self):
        item = dict(title='Book', author='Author', language='English', channel_id=-1003000, message_id=123)
        with patch.object(lib, 'get_book', return_value=item):
            self.assertTrue(lib.handle_library_start(self.bot, fake_message(user=23, text='/start book_'+uuid.uuid4().hex)))
        self.assertEqual(self.bot.copied[-1]['chat_id'], 23)

    def test_admin_upload_stays_admin_only(self):
        upload_filter = next(opts['func'] for opts, fn in self.bot.message_handlers if fn.__name__ == 'admin_book_upload')
        self.assertFalse(upload_filter(fake_message(user=23, caption='Book | Author | English')))

    def test_explicit_adult_toggle_still_restricts(self):
        with patch.dict(os.environ, {'BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT': 'true'}):
            with patch.dict(sys.modules, {'study_access_v9': types.SimpleNamespace(is_verified_adult=lambda uid: False)}):
                self.assertFalse(lib._verified(23))


if __name__ == '__main__':
    unittest.main()
