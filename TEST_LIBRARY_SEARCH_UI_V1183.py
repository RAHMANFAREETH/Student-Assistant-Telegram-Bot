"""Offline V11.8.3 search filters, ownership, expiry and installer tests."""
from __future__ import annotations

import os
import sys
import time
import types
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import library_search_ui_v1183 as ui
import library_media_v117_bot as api
from PATCH_LIBRARY_SEARCH_UI_V1183 import transform_media, transform_group

UID1=str(uuid.uuid4())
UID2=str(uuid.uuid4())
UID3=str(uuid.uuid4())

class Button:
    def __init__(self,text,callback_data=None,url=None,**kw):
        self.text=text; self.callback_data=callback_data; self.url=url

class Markup:
    def __init__(self,*args,**kw): self.inline_keyboard=[]
    def add(self,*args): self.inline_keyboard.append(list(args))

class Bot:
    def __init__(self):
        self.sent=[]; self.edited=[]; self.answered=[]; self.copied=[]; self.callbacks=[]
    def send_message(self,chat_id,text,**kw):
        self.sent.append((chat_id,text,kw))
        return types.SimpleNamespace(message_id=123)
    def edit_message_text(self,text,chat_id,message_id,**kw):
        self.edited.append((text,chat_id,message_id,kw))
        return True
    def answer_callback_query(self,callback_id,text,**kw):
        self.answered.append((text,kw))
    def get_me(self): return types.SimpleNamespace(username='TestStudentBot')
    def callback_query_handler(self,**kw):
        def deco(fn):self.callbacks.append((kw,fn));return fn
        return deco


def data():
    return [
      {'id':UID1,'source':'book','media_kind':'pdf','title':'The Psychology of Money',
       'language':'English','author':'Morgan Housel','category':'Finance','file_size':2800000},
      {'id':UID2,'source':'book','media_kind':'pdf','title':'The Psychology of Money',
       'language':'Tamil','author':'Morgan Housel','category':'Finance','file_size':39700000},
      {'id':UID3,'source':'media','media_kind':'image','title':'Psychology chart',
       'language':'Tamil','author':'Tutor','category':'Education','file_size':9000},
    ]


def buttons(markup):
    return [b for row in markup.inline_keyboard for b in row]


def call(token,action,uid=42,cid=-1002,chat_type='supergroup'):
    return types.SimpleNamespace(id='cb',data=f'ls83:{token}:{action}',
      from_user=types.SimpleNamespace(id=uid),
      message=types.SimpleNamespace(chat=types.SimpleNamespace(id=cid,type=chat_type),message_id=123))

class SearchUiTests(unittest.TestCase):
    def setUp(self):
        self.environment=patch.dict(os.environ,{'BOOK_LIBRARY_ENABLED':'true',
            'LIBRARY_MEDIA_V117_ENABLED':'true','BOOK_LIBRARY_BOT_USERNAME':'TestStudentBot',
            'BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT':'false',
            'BOOK_LIBRARY_ALLOW_ALL_GROUPS':'true'})
        self.environment.start()
        self.fake_modules=patch.dict(sys.modules,{
           'telebot':types.SimpleNamespace(types=types.SimpleNamespace(InlineKeyboardMarkup=Markup,
                                                InlineKeyboardButton=Button))})
        self.fake_modules.start()
        self.bot=Bot()
        with ui._LOCK: ui._SESSIONS.clear()
    def tearDown(self):
        with ui._LOCK: ui._SESSIONS.clear()
        self.fake_modules.stop()
        self.environment.stop()
    def _search(self,group=True,uid=42):
        chat=-1002 if group else 42
        with patch('group_ui_v115._remember') as remember:
            ui.send_search_results(self.bot,chat,'📚 Library results: Psychology\n📩 Private preview',
                    data(),group=group,requester_id=uid)
            if group:remember.assert_called_once_with(self.bot,chat,123,kind='book_links')
            else:remember.assert_not_called()
        token=next(iter(ui._SESSIONS))
        return token
    def test_distinguishes_tamil_and_english_file_links(self):
        self._search()
        kb=self.bot.sent[0][2]['reply_markup']
        labels=[b.text for b in buttons(kb) if b.url]
        self.assertTrue(any('English' in text and '2.7 MB' in text for text in labels))
        self.assertTrue(any('Tamil' in text and '37.9 MB' in text for text in labels))
        self.assertTrue(all('start=book_' in b.url or 'start=media_' in b.url
                            for b in buttons(kb) if b.url))
        self.assertTrue(all(len(b.callback_data)<=64 for b in buttons(kb) if b.callback_data))
    def test_language_filter_choice(self):
        token=self._search()
        with patch('book_library_bot._allowed_group',return_value=True):
            ui.handle_callback(self.bot,call(token,'l'),group=True)
            self.assertIn('choose an option',self.bot.edited[-1][0])
            kb=self.bot.edited[-1][3]['reply_markup']
            choices={b.text:b.callback_data for b in buttons(kb)}
            self.assertIn('Tamil (2)',choices)
            data_value=choices['Tamil (2)'].split(':')[-1]
            ui.handle_callback(self.bot,call(token,'v:'+data_value),group=True)
            labels=[b.text for b in buttons(self.bot.edited[-1][3]['reply_markup']) if b.url]
            self.assertEqual(len(labels),2)
            self.assertTrue(all('Tamil' in text for text in labels))
    def test_type_and_category_filter(self):
        token=self._search()
        with patch('book_library_bot._allowed_group',return_value=True):
            ui.handle_callback(self.bot,call(token,'f'),group=True)
            options={b.text:b.callback_data for b in buttons(self.bot.edited[-1][3]['reply_markup'])}
            code=next(v for k,v in options.items() if k.startswith('image'))
            ui.handle_callback(self.bot,call(token,'v:'+code.split(':')[-1]),group=True)
            urls=[b for b in buttons(self.bot.edited[-1][3]['reply_markup']) if b.url]
            self.assertEqual(len(urls),1)
            self.assertIn('start=media_',urls[0].url)
            ui.handle_callback(self.bot,call(token,'z'),group=True)
            self.assertEqual(len([b for b in buttons(self.bot.edited[-1][3]['reply_markup']) if b.url]),3)
    def test_group_ownership_protection(self):
        token=self._search()
        with patch('book_library_bot._allowed_group',return_value=True):
            ui.handle_callback(self.bot,call(token,'l',uid=99),group=True)
        self.assertEqual(self.bot.edited,[])
        self.assertTrue(self.bot.answered[-1][1]['show_alert'])
    def test_group_policy_protection(self):
        token=self._search()
        with patch('book_library_bot._allowed_group',return_value=False):
            ui.handle_callback(self.bot,call(token,'l'),group=True)
        self.assertEqual(self.bot.edited,[])
    def test_search_expiration(self):
        token=self._search()
        ui._SESSIONS[token]['expires']=time.monotonic()-1
        with patch('book_library_bot._allowed_group',return_value=True):
            ui.handle_callback(self.bot,call(token,'l'),group=True)
        self.assertEqual(self.bot.edited,[])
        self.assertIn('expired',self.bot.answered[-1][0])
    def test_private_filters(self):
        token=self._search(group=False)
        ui.handle_callback(self.bot,call(token,'l',cid=42,chat_type='private'),group=False)
        self.assertEqual(len(self.bot.edited),1)
        self.assertEqual(self.bot.copied,[])
    def test_private_other_user_blocked(self):
        token=self._search(group=False)
        ui.handle_callback(self.bot,call(token,'l',uid=99,cid=42,chat_type='private'),group=False)
        self.assertEqual(self.bot.edited,[])
    def test_pagination_and_bounded_page(self):
        many = [{**data()[0], 'id':str(uuid.uuid4()),'title':f'Book {i}'} for i in range(12)]
        with patch('group_ui_v115._remember'):
            ui.send_search_results(self.bot,-1002,'📚 Library results',many,group=True,requester_id=42)
        token=next(iter(ui._SESSIONS))
        with patch('book_library_bot._allowed_group',return_value=True):
            ui.handle_callback(self.bot,call(token,'p:1'),group=True)
        self.assertIn('2 / 3',[b.text for b in buttons(self.bot.edited[-1][3]['reply_markup'])])
        self.assertEqual(len([b for b in buttons(self.bot.edited[-1][3]['reply_markup']) if b.url]),5)
    def test_no_bulk_delivery_or_channel_leak(self):
        token=self._search()
        with patch('book_library_bot._allowed_group',return_value=True):
            ui.handle_callback(self.bot,call(token,'z'),group=True)
        self.assertFalse(self.bot.copied)
        self.assertNotIn('storage_channel',str(self.bot.sent))
        self.assertNotIn('channel_id',str(self.bot.edited))
    def test_ui_registration_is_idempotent(self):
        ui.register_private_handlers(self.bot)
        ui.register_private_handlers(self.bot)
        self.assertEqual(len(self.bot.callbacks),1)

class InstallerTests(unittest.TestCase):
    def test_idempotence_and_anchor_guards(self):
        root=Path(__file__).parent
        original=(root/'library_media_v117_bot.py').read_text(encoding='utf-8')
        next_source=transform_media(original)
        self.assertEqual(transform_media(next_source),next_source)
        with self.assertRaises(ValueError):transform_media('bad code')
        group=(root/'group_books_only_v116.py').read_text(encoding='utf-8')
        next_group=transform_group(group)
        self.assertEqual(transform_group(next_group),next_group)
        with self.assertRaises(ValueError):transform_group('bad code')

if __name__=='__main__': unittest.main()
