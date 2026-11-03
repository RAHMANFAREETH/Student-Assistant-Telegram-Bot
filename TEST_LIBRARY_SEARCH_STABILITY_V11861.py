"""Offline regression tests for clients without edit_message_text; no network."""
from __future__ import annotations
import types
import unittest
from unittest.mock import patch
import library_media_v117_bot as media
import library_search_ui_v1183 as ui
from PATCH_LIBRARY_SEARCH_STABILITY_V11861 import transform_media, transform_ui, transform_test, transform_legacy_test
from pathlib import Path

class NoEditor:
    def __init__(self):
        self.deleted=[]
    def delete_message(self, chat_id, message_id):
        self.deleted.append((chat_id, message_id))
        return True

class StatusFallbackTests(unittest.TestCase):
    def test_no_editor_no_results_fallback(self):
        bot=NoEditor()
        status=types.SimpleNamespace(message_id=17)
        final=types.SimpleNamespace(message_id=18)
        with patch.object(media, '_message', return_value=final) as send:
            result=media._replace_search_status(bot, 22, status, 'Nothing found', group=False)
        self.assertIs(result, final)
        send.assert_called_once()
        self.assertEqual(bot.deleted,[(22,17)])

    def test_no_editor_results_fallback(self):
        bot=NoEditor()
        status=types.SimpleNamespace(message_id=17)
        final=types.SimpleNamespace(message_id=18)
        # This test does not exercise Telegram or Supabase; only the fallback.
        with patch.object(ui, '_create', return_value=('token',{})), \
             patch.object(ui, '_display',return_value=('results',object())), \
             patch.object(media,'_message',return_value=final) as send:
            result=ui.send_search_results(bot,22,'results',[{'title':'Test'}],status_message=status)
        self.assertIs(result,final)
        send.assert_called_once()
        self.assertEqual(bot.deleted,[(22,17)])

    def test_idempotent_transformers(self):
        root=Path(__file__).resolve().parent
        for name,fn in [('library_media_v117_bot.py', transform_media),
                        ('library_search_ui_v1183.py', transform_ui),
                        ('TEST_BOOK_LIBRARY_V112.py', transform_test),
                        ('TEST_BOOK_LIBRARY.py',lambda s: transform_legacy_test(s,'TEST_BOOK_LIBRARY.py')),
                        ('TEST_BOOK_PUBLIC_LATEST5.py',lambda s: transform_legacy_test(s,'TEST_BOOK_PUBLIC_LATEST5.py'))]:
            old=(root/name).read_text(encoding='utf-8')
            self.assertEqual(fn(old),old)

if __name__=='__main__':
    unittest.main()
