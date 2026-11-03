"""V11.8.6 offline tests: query progress, found, not-found, errors and fallback.
No live Telegram, DB, network or credentials.
"""
from __future__ import annotations
import sys
import types
import unittest
import uuid
from unittest.mock import patch

import library_media_v117_bot as media
import library_search_ui_v1183 as search
from PATCH_LIBRARY_SEARCH_COMBINED_V1186 import transform_media,transform_ui,transform_book,transform_prior_installer,transform_group


class Button:
    def __init__(self,text,callback_data=None,url=None,**kw):
        self.text=text;self.callback_data=callback_data;self.url=url
class Keyboard:
    def __init__(self,*args,**kwargs):self.inline_keyboard=[]
    def add(self,*items):self.inline_keyboard.append(list(items))
    def row(self,*items):self.inline_keyboard.append(list(items))
class Bot:
    def __init__(self):
        self.sent=[];self.edited=[];self.deleted=[];self.count=0;self.edit_fails=False
    def send_message(self,cid,body,**kw):
        self.count+=1
        self.sent.append((cid,body,kw))
        return types.SimpleNamespace(message_id=self.count+100)
    def edit_message_text(self,body,**kwargs):
        if self.edit_fails:raise RuntimeError('Telegram edit denied')
        self.edited.append((body,kwargs))
        return True
    def delete_message(self,cid,mid):
        self.deleted.append((cid,mid));return True
    def get_me(self):return types.SimpleNamespace(username='StudentTestBot')

class SearchFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.bot=Bot()
        self.telebot=patch.dict(sys.modules,{'telebot':types.SimpleNamespace(types=types.SimpleNamespace(
            InlineKeyboardMarkup=Keyboard,InlineKeyboardButton=Button))})
        self.telebot.start()
        self.active=patch.object(media,'enabled',return_value=True)
        self.active.start()
        self.remember=patch('group_ui_v115._remember')
        self.cleanup=self.remember.start()
        with search._LOCK:search._SESSIONS.clear()
    def tearDown(self):
        with search._LOCK:search._SESSIONS.clear()
        self.remember.stop();self.active.stop();self.telebot.stop()
    def test_found_edits_progress_into_file_buttons(self):
        book={'id':str(uuid.uuid4()),'source':'book','title':'The Psychology of Money',
              'language':'Tamil','media_kind':'pdf','file_size':39700000}
        def answer(*args,**kwargs):
            self.assertTrue(self.bot.sent)
            self.assertIn('SEARCHING',self.bot.sent[0][1])
            return [book]
        with patch.object(media,'union_search',side_effect=answer):
            result=media.unified_search(self.bot,-1002,'The Psychology of Money',group=True,
                                        requester_id=42)
        self.assertEqual(result.message_id,101)
        self.assertEqual(len(self.bot.sent),1)
        self.assertEqual(len(self.bot.edited),1)
        text,kwargs=self.bot.edited[-1]
        self.assertIn('Library results',text)
        buttons=[b for row in kwargs['reply_markup'].inline_keyboard for b in row]
        self.assertTrue(any(b.url and 'start=book_' in b.url and 'Tamil' in b.text for b in buttons))
        self.cleanup.assert_called_with(self.bot,-1002,101,kind='book_links')
    def test_no_result_edits_with_spelling_help(self):
        with patch.object(media,'union_search',return_value=[]):
            result=media.unified_search(self.bot,-1002,'HBDBFBBFJ',group=True,
                                        requester_id=42)
        self.assertIsNot(result,False)
        self.assertEqual(len(self.bot.sent),1)
        self.assertEqual(len(self.bot.edited),1)
        text,kwargs=self.bot.edited[-1]
        self.assertIn('NO FILES FOUND',text)
        self.assertIn('HBDBFBBFJ',text)
        self.assertIn('spelling',text.lower())
        self.assertIn('auto-deletes',text)
        self.assertIn('google.com/search?q=',kwargs['reply_markup'].inline_keyboard[0][0].url)
    def test_no_results_in_private(self):
        with patch.object(media,'union_search',return_value=[]):
            media.unified_search(self.bot,42,'asdfasdf',group=False,requester_id=42)
        self.assertEqual(len(self.bot.sent),1)
        self.assertIn('NO FILES FOUND',self.bot.edited[0][0])
        self.cleanup.assert_not_called()
    def test_failed_database_is_not_called_empty_catalog(self):
        with patch.object(media,'union_search',side_effect=RuntimeError('db offline')):
            media.unified_search(self.bot,42,'The Psychology of Money',requester_id=42)
        self.assertIn('temporarily unavailable',self.bot.edited[0][0])
        self.assertNotIn('NO FILES FOUND',self.bot.edited[0][0])
    def test_telegram_edit_denied_sends_fallback_and_removes_spinner(self):
        self.bot.edit_fails=True
        with patch.object(media,'union_search',return_value=[]):
            media.unified_search(self.bot,-1002,'No such title',group=True,requester_id=42)
        self.assertEqual(len(self.bot.sent),2)
        self.assertIn('NO FILES FOUND',self.bot.sent[-1][1])
        self.assertEqual(self.bot.deleted,[(-1002,101)])
        self.assertEqual(self.cleanup.call_count,2)
    def test_bad_query_does_not_create_search_spinner(self):
        with patch.object(media,'union_search') as lookup:
            media.unified_search(self.bot,42,'x',requester_id=42)
        lookup.assert_not_called()
        self.assertNotIn('SEARCHING',self.bot.sent[0][1])
    def test_plain_group_text_is_opt_in_and_still_requires_existing_guard(self):
        import os
        import group_books_only_v116 as groups
        msg=types.SimpleNamespace(text='Unknown book name',
            chat=types.SimpleNamespace(id=-10022,type='supergroup'),
            from_user=types.SimpleNamespace(id=42),message_id=4)
        env={'BOOK_LIBRARY_AUTO_GROUP_SEARCH':'true',
             'GROUP_BOOK_ONLY_V116_ENABLED':'true',
             'LIBRARY_SEARCH_V1186_ALL_TEXT_ENABLED':'true'}
        with patch.dict(os.environ,env), \
             patch('book_library_bot._enabled',return_value=True), \
             patch('book_library_bot._allowed_group',return_value=True), \
             patch('book_library_bot._verified',return_value=True), \
             patch.object(groups,'_is_book_match',return_value=False), \
             patch.object(groups,'_book_search') as submit:
            groups.route_group_text(self.bot,msg)
            submit.assert_called_once_with(self.bot,msg,'Unknown book name')
        env['LIBRARY_SEARCH_V1186_ALL_TEXT_ENABLED']='false'
        with patch.dict(os.environ,env), \
             patch('book_library_bot._enabled',return_value=True), \
             patch('book_library_bot._allowed_group',return_value=True), \
             patch('book_library_bot._verified',return_value=True), \
             patch.object(groups,'_is_book_match',return_value=False), \
             patch.object(groups,'_book_search') as submit:
            groups.route_group_text(self.bot,msg)
            submit.assert_not_called()

    def test_transformers_idempotent(self):
        from pathlib import Path
        root=Path(__file__).resolve().parent
        for name,transform in [('library_media_v117_bot.py',transform_media),
                               ('library_search_ui_v1183.py',transform_ui),
                               ('book_library_v112_bot.py',transform_book),
                               ('PATCH_LIBRARY_SEARCH_UI_V1183.py',transform_prior_installer),
                               ('group_books_only_v116.py',transform_group)]:
            source=(root/name).read_text(encoding='utf-8')
            self.assertEqual(source,transform(source))

if __name__=='__main__':unittest.main()
