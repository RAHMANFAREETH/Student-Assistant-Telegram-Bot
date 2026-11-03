"""Offline V11.8.7 tests for large media relayed inside Telegram; no network/credentials."""
import os
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import book_library_bot as library
import book_library_v113_bot as v113
import library_media_v117_bot as media
import library_media_v117_store as store
import library_media_v117_processing as process
from TEST_BOOK_LIBRARY import FakeBot, FakeMarkup, FakeButton, ContinueHandling, fake_message
from TEST_LIBRARY_MEDIA_V117 import Bot as MediaBot, message, document

GIGABYTE = 1024**3
PREMIUM_FILE_SIZE = 4 * GIGABYTE


class AdminBookRelayTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            'BOOK_LIBRARY_ENABLED': 'true', 'BOOK_LIBRARY_ADMIN_IDS': '7',
            'BOOK_LIBRARY_CHANNEL_ID': '-1003000',
            'BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT': 'false',
            'LIBRARY_MEDIA_V117_ENABLED': 'false',
            'BOOK_LIBRARY_V112_ENABLED': 'false',
            'BOOK_LIBRARY_V113_ENABLED': 'false',
            'BOOK_LIBRARY_MAX_BYTES': '0',
        })
        self.env.start()
        import sys
        telebot = types.ModuleType('telebot')
        telebot.types = types.SimpleNamespace(
            InlineKeyboardMarkup=FakeMarkup, InlineKeyboardButton=FakeButton)
        backend = types.ModuleType('telebot.handler_backends')
        backend.ContinueHandling = ContinueHandling
        self.stub = patch.dict(sys.modules, {
            'telebot': telebot, 'telebot.handler_backends': backend
        })
        self.stub.start()
        self.bot = FakeBot()
        library.register_book_library_handlers(self.bot)
        self.handler = next(fn for opts, fn in self.bot.message_handlers
                            if fn.__name__ == 'admin_book_upload')

    def tearDown(self):
        self.stub.stop()
        self.env.stop()

    def test_63_mb_document_is_copied(self):
        with patch.object(library, 'add_book', return_value={'id': 'test'}):
            self.handler(fake_message(caption='Atomic Habits | James Clear | Tamil',
                                      file_size=63_900_000))
        self.assertEqual(len(self.bot.copied), 1)
        self.assertEqual(self.bot.copied[0]['chat_id'], -1003000)

    def test_premium_four_gigabyte_document_is_copied_without_download(self):
        with patch.object(library, 'add_book', return_value={'id': 'test'}):
            self.handler(fake_message(caption='A Long PDF | Author | Tamil',
                                      file_size=PREMIUM_FILE_SIZE))
        self.assertEqual(len(self.bot.copied), 1)

    def test_positive_admin_cap_still_enforced(self):
        with patch.dict(os.environ, {'BOOK_LIBRARY_MAX_BYTES': '52428800'}):
            self.handler(fake_message(caption='Atomic Habits | James Clear | Tamil',
                                      file_size=63_900_000))
        self.assertFalse(self.bot.copied)
        self.assertIn('exceeds library upload limit', self.bot.sent[-1][1])

    def test_negative_config_is_rejected(self):
        with patch.dict(os.environ, {'BOOK_LIBRARY_MAX_BYTES': '-1'}):
            self.handler(fake_message(caption='Atomic Habits | James Clear | Tamil',
                                      file_size=63_900_000))
        self.assertFalse(self.bot.copied)
        self.assertIn('misconfigured', self.bot.sent[-1][1])


class UnifiedMediaRelayTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'LIBRARY_MEDIA_MAX_BYTES': '0',
                        'LIBRARY_MEDIA_SUBMISSION_MAX_BYTES': '0',
                        'LIBRARY_MEDIA_OCR_ENABLED': 'false'})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def _message(self, size):
        return message(caption='Atomic Habits | James Clear | Tamil | Self-Help | permission',
                       document=document(name='atomic.pdf', size=size))

    def test_four_gigabyte_metadata_is_valid(self):
        info, meta = media._file_meta(MediaBot(), self._message(PREMIUM_FILE_SIZE))
        self.assertEqual(info['size'], PREMIUM_FILE_SIZE)
        self.assertEqual(meta['language'], 'Tamil')

    def test_admin_media_is_copied_without_download(self):
        bot = MediaBot()
        m = self._message(PREMIUM_FILE_SIZE)
        with patch.dict(os.environ, {'BOOK_LIBRARY_CHANNEL_ID': '-10011'}), \
             patch.object(store, 'duplicates', return_value=None), \
             patch.object(store, 'same_filename', return_value=[]), \
             patch.object(store, 'create', return_value={'id': 'fake'}), \
             patch.object(store, 'audit'):
            media.submit_media(bot, m, contributor=False)
        self.assertEqual(len(bot.copied), 1)
        self.assertEqual(bot.copied[0]['chat_id'], -10011)
        self.assertEqual(len(bot.photos), 0)

    def test_positive_media_cap_still_enforced(self):
        with patch.dict(os.environ, {'LIBRARY_MEDIA_MAX_BYTES': '52428800'}):
            with self.assertRaisesRegex(ValueError, 'too large'):
                media._file_meta(MediaBot(), self._message(63_900_000))

    def test_small_processing_limit_still_applies(self):
        with patch.dict(os.environ, {'LIBRARY_MEDIA_OCR_ENABLED': 'true'}):
            bot = MediaBot()
            with patch.object(process, 'get_bytes', return_value=None) as fetch:
                result = process.inspect_upload(bot, {'kind': 'pdf',
                                    'telegram_file_id': 'FILE', 'size': PREMIUM_FILE_SIZE,
                                    'name': 'atomic.pdf'})
            self.assertIsNone(result['sha256'])
            self.assertTrue(fetch.called)
            self.assertLessEqual(fetch.call_args.kwargs['limit'], process.MAX_DOWNLOAD)

    def test_database_uses_bigint_size(self):
        sql = (Path(__file__).parent / 'SQL_LIBRARY_MEDIA_V117.sql').read_text(encoding='utf8')
        self.assertIn('file_size BIGINT', sql)


class StudentReviewRelayTests(unittest.TestCase):
    def test_four_gigabyte_submission_is_copied_to_review_channel(self):
        import sys
        import time
        from TEST_BOOK_LIBRARY_V113 import FakeBot as V113Bot, msg as v113_message
        telebot = types.ModuleType('telebot')
        telebot.types = types.SimpleNamespace(
            InlineKeyboardButton=lambda *a, **k: types.SimpleNamespace(**k),
            InlineKeyboardMarkup=lambda *a, **k: types.SimpleNamespace(add=lambda *a:None),
            WebAppInfo=lambda **kw: types.SimpleNamespace(**kw),
            InlineQueryResultArticle=lambda **kw: types.SimpleNamespace(**kw),
            InputTextMessageContent=lambda x: types.SimpleNamespace(text=x))
        env = {'BOOK_LIBRARY_ENABLED':'true', 'BOOK_LIBRARY_V113_ENABLED':'true',
               'BOOK_LIBRARY_ADMIN_IDS':'987',
               'BOOK_LIBRARY_CHANNEL_ID':'-10011',
               'BOOK_LIBRARY_REVIEW_CHANNEL_ID':'-10012',
               'BOOK_LIBRARY_SUBMISSION_MAX_BYTES':'0'}
        with patch.dict(os.environ, env), patch.dict(sys.modules, {'telebot':telebot}):
            b = V113Bot()
            calls=[]
            b.copy_message=lambda **kwargs: (calls.append(kwargs) or types.SimpleNamespace(message_id=12345))
            v113.register_v113_handlers(b)
            fn=next(handler for cmds, cond, handler in b.handlers
                    if handler.__name__=='student_submission')
            m=v113_message('', uid=123)
            m.document=types.SimpleNamespace(file_name='huge.pdf', file_size=PREMIUM_FILE_SIZE,
                                              file_unique_id='UNIQ')
            m.caption='Large PDF | Approved Author | Tamil | Permission to share'
            m.message_id=77
            v113._pending_submissions[123]=time.monotonic()+180
            try:
                with patch.object(v113,'add_submission',return_value={'id':'fake'}):
                    fn(m)
                self.assertEqual(calls[0]['chat_id'],-10012)
                self.assertIn('Submitted',b.sent[-1][1])
            finally:
                v113._pending_submissions.pop(123,None)


if __name__ == '__main__':
    unittest.main()
