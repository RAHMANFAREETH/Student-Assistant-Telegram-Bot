"""Offline user-isolation tests; no Telegram, Supabase, or network calls."""
from __future__ import annotations
import os
import sys
import tempfile
import types
import unittest
import uuid
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import book_library_privacy_v114 as privacy
from INSTALL_BOOK_LIBRARY_PRIVACY_V114 import integrate, NAMES, MARKER

BOOK={'id':str(uuid.uuid4()),'title':'Test Book','author':'Test Author',
      'language':'English','file_size':20000,'active':True}


class FakeBot:
    def __init__(self):
        self.handlers=[]; self.callbacks=[]; self.sent=[]; self.deleted=[]
        self.answered=[]; self.actions=[]; self.edited=[]
        self.deny_private=False; self.deny_delete=False
    def message_handler(self,**options):
        def dec(fn):self.handlers.append((options,fn));return fn
        return dec
    def callback_query_handler(self,**options):
        def dec(fn):self.callbacks.append((options,fn));return fn
        return dec
    def inline_handler(self,**options):
        return lambda fn:fn
    def get_me(self):return types.SimpleNamespace(username='TestStudyBot')
    def send_chat_action(self,chat_id,action):
        self.actions.append((chat_id,action))
        if self.deny_private:raise RuntimeError('user has not started bot')
        return True
    def send_message(self,chat_id,text,**kwargs):
        if self.deny_private and int(chat_id)>0:raise RuntimeError('private chat forbidden')
        self.sent.append((int(chat_id),str(text),kwargs))
        return types.SimpleNamespace(message_id=321)
    def delete_message(self,chat_id,message_id):
        if self.deny_delete:raise RuntimeError('no permission')
        self.deleted.append((chat_id,message_id))
    def edit_message_reply_markup(self,**kwargs):
        self.edited.append(kwargs)
    def answer_callback_query(self,cb_id,text='',**kwargs):
        self.answered.append((cb_id,text,kwargs))
    def copy_message(self,**kwargs):return types.SimpleNamespace(message_id=999)


class FakeMarkup:
    def __init__(self,**kwargs):self.buttons=[]
    def add(self,*buttons):self.buttons.extend(buttons)
    def row(self,*buttons):self.buttons.extend(buttons)
class FakeButton:
    def __init__(self,text,**kwargs):self.text=text;self.options=kwargs
class ContinueHandling:pass


def msg(uid=42,chat=None,kind='private',text='/book Test',mid=101):
    return types.SimpleNamespace(chat=types.SimpleNamespace(id=uid if chat is None else chat, type=kind),
       from_user=types.SimpleNamespace(id=uid),text=text,message_id=mid)


def cb(uid=42,chat=None,kind='private',data='lib:latest',mid=321):
    return types.SimpleNamespace(from_user=types.SimpleNamespace(id=uid),
                                 id='cb123',data=data,message=msg(uid=uid,chat=chat,kind=kind,mid=mid))


class PrivacyTests(unittest.TestCase):
    def setUp(self):
        self.settings=patch.dict(os.environ,{
          'BOOK_LIBRARY_ENABLED':'true','BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT':'false',
          'BOOK_LIBRARY_BOT_USERNAME':'TestStudyBot', 'BOOK_LIBRARY_ALLOW_ALL_GROUPS':'true',
          'BOOK_LIBRARY_PRIVATE_GROUP_RESULTS':'true','BOOK_LIBRARY_DELETE_GROUP_COMMANDS':'true',
          'BOOK_LIBRARY_AUTODELETE_MENU':'true','BOOK_LIBRARY_V112_ENABLED':'false',
          'BOOK_LIBRARY_V113_ENABLED':'false', 'BOOK_LIBRARY_AUTO_GROUP_SEARCH':'true',
        })
        self.settings.start()
        self.t=types.ModuleType('telebot')
        self.t.types=types.SimpleNamespace(InlineKeyboardMarkup=FakeMarkup, InlineKeyboardButton=FakeButton)
        self.backend=types.ModuleType('telebot.handler_backends')
        self.backend.ContinueHandling=ContinueHandling
        self.modules=patch.dict(sys.modules,{'telebot':self.t,'telebot.handler_backends':self.backend})
        self.modules.start()
        import book_library_bot as lib
        self.lib=lib
        lib._pending.clear();lib._throttle.clear();lib._username=None
        self.bot=FakeBot();lib.register_book_library_handlers(self.bot)
        self.by_name={fn.__name__:fn for _,fn in self.bot.handlers}
        self.by_callback={fn.__name__:fn for _,fn in self.bot.callbacks}
    def tearDown(self):self.modules.stop();self.settings.stop()

    def test_group_book_search_routes_to_requester_private(self):
        with patch.object(self.lib,'search_books',return_value=[BOOK]):
            self.by_name['library_commands'](msg(chat=-10088,kind='supergroup',text='/book Test'))
        self.assertTrue(self.bot.sent)
        self.assertTrue(all(cid==42 for cid,_,_ in self.bot.sent))
        self.assertIn((-10088,101),self.bot.deleted)

    def test_group_book_latest_routes_to_requester_private(self):
        with patch.object(self.lib,'latest_books',return_value=[BOOK]):
            self.by_name['library_latest_private_group'](msg(chat=-10088,kind='supergroup',text='/booklatest'))
        self.assertTrue(any('Latest Books' in text for _,text,_ in self.bot.sent))
        self.assertTrue(all(chat==42 for chat,_,_ in self.bot.sent))
        self.assertEqual(self.bot.deleted, [(-10088,101)])

    def test_start_bot_first_when_dm_forbidden(self):
        self.bot.deny_private=True
        with patch.object(self.lib,'search_books',return_value=[BOOK]):
            self.by_name['library_commands'](msg(chat=-10088,kind='supergroup',text='/book Test'))
        self.assertTrue(any(chat==-10088 and 'start' in text.lower() for chat,text,_ in self.bot.sent))
        self.assertFalse(self.bot.deleted)

    def test_regular_group_chat_not_auto_deleted(self):
        m=msg(chat=-10088,kind='supergroup',text='Book Test')
        with patch.object(self.lib,'search_books',return_value=[BOOK]):
            self.by_name['group_search'](m)
        self.assertEqual(self.bot.deleted, [])
        self.assertTrue(all(chat==42 for chat,_,_ in self.bot.sent))

    def test_group_auto_miss_stays_silent(self):
        with patch.object(self.lib,'search_books',return_value=[]):
            self.by_name['group_search'](msg(chat=-10088,kind='supergroup',text='Unrelated discussion'))
        self.assertEqual(self.bot.sent,[])

    def test_public_group_behavior_when_disabled(self):
        with patch.dict(os.environ,{'BOOK_LIBRARY_PRIVATE_GROUP_RESULTS':'false'}):
            with patch.object(self.lib,'search_books',return_value=[BOOK]):
                self.by_name['library_commands'](msg(chat=-10088,kind='supergroup',text='/book Test'))
        self.assertTrue(any(chat==-10088 for chat,_,_ in self.bot.sent))
        self.assertEqual(self.bot.deleted, [])

    def test_private_menu_deleted_after_search_click(self):
        self.by_callback['library_callback'](cb(data='lib:search'))
        self.assertEqual(self.bot.deleted,[(42,321)])
        self.assertTrue(self.lib._session_active(msg(text='book query')))

    def test_private_menu_deleted_after_latest_click(self):
        with patch.object(self.lib,'latest_books',return_value=[BOOK]):
            self.by_callback['library_callback'](cb(data='lib:latest'))
        self.assertIn((42,321),self.bot.deleted)
        self.assertTrue(any('Latest Books' in text for _,text,_ in self.bot.sent))

    def test_private_menu_delete_failure_removes_keyboard(self):
        self.bot.deny_delete=True
        self.by_callback['library_callback'](cb(data='lib:search'))
        self.assertEqual(self.bot.edited[-1]['message_id'],321)
        self.assertIsNone(self.bot.edited[-1]['reply_markup'])

    def test_foreign_callback_cannot_delete_or_use_menu(self):
        self.by_callback['library_callback'](cb(uid=84,chat=42,data='lib:latest'))
        self.assertEqual(self.bot.deleted,[])
        self.assertEqual(self.bot.sent,[])
        self.assertTrue(self.bot.answered[-1][2]['show_alert'])

    def test_group_callback_not_deleted_by_wrong_user(self):
        self.by_callback['library_callback'](cb(uid=99,chat=-10088,kind='supergroup'))
        self.assertEqual(self.bot.deleted,[])
        self.assertFalse(self.bot.sent)

    def test_group_command_deletion_cannot_break_private_results(self):
        self.bot.deny_delete=True
        with patch.object(self.lib,'search_books',return_value=[BOOK]):
            self.by_name['library_commands'](msg(chat=-10088,kind='supergroup',text='/book Test'))
        self.assertTrue(any(chat==42 for chat,_,_ in self.bot.sent))
        self.assertFalse(self.bot.deleted)

    def test_do_not_delete_commands_when_setting_off(self):
        with patch.dict(os.environ,{'BOOK_LIBRARY_DELETE_GROUP_COMMANDS':'false'}):
            with patch.object(self.lib,'search_books',return_value=[BOOK]):
                self.by_name['library_commands'](msg(chat=-10088,kind='supergroup',text='/book Test'))
        self.assertEqual(self.bot.deleted,[])

    def test_v112_owner_bound_page_token(self):
        import book_library_v112_bot as mod
        token=mod._save_session(-10088,{'kind':'browse'},owner=42)
        self.assertIsNotNone(mod._session(token,-10088,42))
        self.assertIsNone(mod._session(token,-10088,99))

    def test_v112_legacy_public_group_token_denied(self):
        import book_library_v112_bot as mod
        token=mod._save_session(-10088,{'kind':'browse'},owner=None)
        self.assertIsNone(mod._session(token,-10088,42))

    def test_v112_filters_can_be_private(self):
        import book_library_v112_bot as mod
        with patch.dict(os.environ,{'BOOK_LIBRARY_V112_ENABLED':'true'}):
            with patch.object(mod,'facets',return_value=[{'value':'English','book_count':1}]):
                mod._send_facets(self.bot,42,'language')
        self.assertEqual(self.bot.sent[-1][0],42)

    def test_v113_private_group_discovery_message(self):
        import book_library_v113_bot as mod
        with patch.dict(os.environ,{'BOOK_LIBRARY_V112_ENABLED':'true','BOOK_LIBRARY_V113_ENABLED':'true'}):
            b=FakeBot();mod.register_v113_handlers(b)
            func=next(fn for opts,fn in b.handlers if 'booksmart' in opts.get('commands',[]))
            with patch.object(mod,'smart_search',return_value=[BOOK]):
                func(msg(chat=-10088,kind='supergroup',text='/booksmart Test'))
            self.assertTrue(b.sent)
            self.assertTrue(all(chat==42 for chat,_,_ in b.sent))


class InstallerTests(unittest.TestCase):
    @staticmethod
    def baseline(tmp):
        with zipfile.ZipFile(ROOT/'V114_TEST_BASELINES.zip') as package:
            for name in NAMES:
                (tmp/name).write_bytes(package.read(name))

    def test_check_apply_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            self.baseline(tmp)
            before=[(tmp/n).read_bytes() for n in NAMES]
            self.assertEqual(len(integrate(tmp,apply=False,output=lambda x:None)),3)
            self.assertEqual(before,[(tmp/n).read_bytes() for n in NAMES])
            self.assertEqual(len(integrate(tmp,apply=True,output=lambda x:None)),3)
            self.assertEqual(integrate(tmp,apply=True,output=lambda x:None),[])
            for n in NAMES:self.assertIn(MARKER,(tmp/n).read_text(encoding='utf-8'))

    def test_installer_preserves_v113_smart_search(self):
        """V11.3 inserts a smart-search branch before the V11.2 branch."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.baseline(tmp)
            path = tmp/'book_library_bot.py'
            source = path.read_text(encoding='utf-8')
            before = ("def _search(bot, chat_id, query, group=False):\n"
                      "    if _on('BOOK_LIBRARY_V112_ENABLED', False):")
            after = ("def _search(bot, chat_id, query, group=False):\n"
                     "    if _on('BOOK_LIBRARY_V113_ENABLED', False):\n"
                     "        from book_library_v113_bot import show_smart_search\n"
                     "        return show_smart_search(bot, chat_id, query, group=group)\n"
                     "    if _on('BOOK_LIBRARY_V112_ENABLED', False):")
            self.assertEqual(source.count(before), 1)
            path.write_text(source.replace(before, after, 1), encoding='utf-8')
            self.assertEqual(len(integrate(tmp, apply=False, output=lambda x: None)), 3)
            self.assertEqual(len(integrate(tmp, apply=True, output=lambda x: None)), 3)
            self.assertEqual(integrate(tmp, apply=False, output=lambda x: None), [])
            result = path.read_text(encoding='utf-8')
            self.assertIn('return show_smart_search(bot, chat_id, query, group=group)', result)
            self.assertIn('def _search(bot, chat_id, query, group=False, requester_id=None):', result)
            self.assertEqual(result.count(MARKER), 1)

    def test_windows_crlf_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            self.baseline(tmp)
            for n in NAMES:
                text=(tmp/n).read_text(encoding='utf-8')
                (tmp/n).write_bytes(text.replace('\n','\r\n').encode('utf-8'))
            integrate(tmp,apply=True,output=lambda x:None)
            for n in NAMES:
                data=(tmp/n).read_bytes()
                self.assertIn(b'\r\n',data)
                self.assertNotIn(b'\n',data.replace(b'\r\n',b''))

    def test_missing_anchor_does_not_modify_any_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            self.baseline(tmp)
            file=tmp/NAMES[-1]
            source=file.read_text(encoding='utf-8')
            file.write_text(source.replace('V11.3: 18 public-library discovery','different layout'),encoding='utf-8')
            before={n:(tmp/n).read_bytes() for n in NAMES}
            with self.assertRaises(ValueError):integrate(tmp,apply=True,output=lambda x:None)
            self.assertEqual(before,{n:(tmp/n).read_bytes() for n in NAMES})

if __name__=='__main__':unittest.main()
