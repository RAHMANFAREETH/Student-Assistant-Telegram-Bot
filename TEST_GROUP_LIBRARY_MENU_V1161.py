"""V11.6.1 group-only library menu tests; no live Telegram/Supabase calls."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import group_library_menu_v1161 as new
import group_ui_v115 as old

class FakeContinueHandling: pass
class FakeButton:
    def __init__(self,text,callback_data=None,url=None,**kwargs):
        self.text=text; self.callback_data=callback_data; self.url=url
class FakeMarkup:
    def __init__(self,*args,**kwargs): self.inline_keyboard=[]
    def row(self,*items):self.inline_keyboard.append(list(items))
    def add(self,*items):self.inline_keyboard.append(list(items))
class FakeTypes:
    InlineKeyboardMarkup=FakeMarkup
    InlineKeyboardButton=FakeButton

class FakeBot:
    def __init__(self):
        self.handlers=[];self.callbacks=[];self.sent=[];self.deleted=[];self.answered=[];self.edited=[]
        self.mid=1000
    def send_message(self,cid,text,*args,**kwargs):
        self.mid+=1
        m=SimpleNamespace(message_id=self.mid,chat=SimpleNamespace(id=int(cid),type='supergroup'))
        self.sent.append((int(cid),str(text),kwargs,m))
        return m
    def message_handler(self,*args,**kwargs):
        def reg(fn):self.handlers.append((fn,kwargs));return fn
        return reg
    def callback_query_handler(self,*args,**kwargs):
        def reg(fn):self.callbacks.append((fn,kwargs));return fn
        return reg
    def answer_callback_query(self,cid,text=None,show_alert=False):self.answered.append((cid,text,show_alert))
    def delete_message(self,cid,mid):self.deleted.append((int(cid),int(mid)));return True
    def edit_message_reply_markup(self,**kw):self.edited.append(kw)
    def dispatch(self,m):
        for fn, kw in self.handlers:
            if kw.get('func',lambda m:True)(m):
                res=fn(m)
                if not isinstance(res,FakeContinueHandling):return res
    def dispatch_callback(self,c):
        for fn,kw in self.callbacks:
            if kw.get('func',lambda c:True)(c):return fn(c)

def msg(t='📚 Book Library',uid=42,cid=-10088,mid=50,kind='supergroup'):
    return SimpleNamespace(text=t,from_user=SimpleNamespace(id=uid),
                           chat=SimpleNamespace(id=cid,type=kind),message_id=mid)

class GroupMenuTests(unittest.TestCase):
    def setUp(self):
        new._SESSIONS.clear();old._GROUPS.clear();old._LOCAL.clear()
        self.env=patch.dict(os.environ,{
            'GROUP_LIBRARY_MENU_V1161_ENABLED':'true',
            'GROUP_BOOK_ONLY_V116_ENABLED':'true',
            'GROUP_UI_PROTECTION_ENABLED':'true',
            'GROUP_UI_TIMER_ENABLED':'true',
            'GROUP_UI_DELETE_AFTER_SECONDS':'300',
            'GROUP_UI_DELETE_NAV_INPUT':'false',
            'BOOK_LIBRARY_ENABLED':'true',
            'BOOK_LIBRARY_ALLOW_ALL_GROUPS':'true',
            'BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT':'false',
            'BOOK_LIBRARY_BOT_USERNAME':'StudentExampleBot',
            'BOOK_LIBRARY_V113_ENABLED':'true',
            'BOOK_LIBRARY_PRIVATE_GROUP_RESULTS':'false',
        });self.env.start()
        self.modules=patch.dict(sys.modules,{
            'telebot':SimpleNamespace(types=FakeTypes),
            'telebot.handler_backends':SimpleNamespace(ContinueHandling=FakeContinueHandling)})
        self.modules.start()
        self.worker=patch.object(old,'_start_worker',return_value=None);self.worker.start()
        self.queue=patch.object(old,'_remember',return_value=None);self.q=self.queue.start()
        self.forget=patch.object(new,'_forget_after_delete',return_value=None);self.forget.start()
        import book_library_bot as library
        self.lib=library
        self.allow=patch.multiple(library,_enabled=lambda:True,_allowed_group=lambda cid:True,
                     _verified=lambda uid:True,_bot_username=lambda bot:'StudentExampleBot')
        self.allow.start()
        self.bot=FakeBot()
        new.install_group_library_menu(self.bot)
        old.install_group_ui_guard(self.bot)
        from group_books_only_v116 import install_book_only_group_gate
        install_book_only_group_gate(self.bot)
    def tearDown(self):
        self.allow.stop();self.forget.stop();self.queue.stop();self.worker.stop()
        self.modules.stop();self.env.stop()
        new._SESSIONS.clear();old._GROUPS.clear();old._LOCAL.clear()

    def open(self,uid=42,text='📚 Book Library'):
        self.bot.dispatch(msg(text,uid))
        return self.bot.sent[-1]
    def click(self,action='l',uid=42):
        cid,txt,kw,m=self.bot.sent[0]
        data=next(b.callback_data for r in kw['reply_markup'].inline_keyboard for b in r
                  if b.callback_data and b.callback_data.startswith('gbm1:'+action+':'))
        cb=SimpleNamespace(id='q12',message=m,from_user=SimpleNamespace(id=uid),data=data)
        self.bot.dispatch_callback(cb)
        return cb

    def test_group_menu_visible_in_group(self):
        cid,txt,kw,m=self.open()
        self.assertEqual(cid,-10088)
        self.assertIn('auto-deletes after 5 minutes',txt)
        labels=[b.text for r in kw['reply_markup'].inline_keyboard for b in r]
        self.assertIn('🔎 Search a Book',labels)
        self.assertIn('🆕 Latest 5 Books',labels)
        self.assertIn('📚 Full Library in Private Bot',labels)
        self.assertNotIn('My Favorites',str(labels))
    def test_group_bookmenu_command(self):
        self.open(text='/bookmenu')
        self.assertEqual(len(self.bot.sent),1)
    def test_group_library_command(self):
        self.open(text='/library')
        self.assertEqual(len(self.bot.sent),1)
    def test_private_chat_not_captured(self):
        self.bot.dispatch(msg(kind='private',cid=42))
        self.assertFalse(self.bot.sent)
    def test_another_bot_mention_ignored(self):
        self.bot.dispatch(msg('/bookmenu@OtherBot'))
        self.assertFalse(self.bot.sent)
    def test_menu_group_is_registered_before_v115(self):
        self.open()
        self.assertIn(-10088,old._GROUPS)
        self.assertTrue(self.q.called)
    def test_menu_uses_five_minute_lifetime(self):
        self.open()
        self.assertLessEqual(abs(new._MENU_TTL-300),0)
        self.assertAlmostEqual(next(iter(new._SESSIONS.values()))[3]-time.monotonic(),300,delta=2)
    def test_latest_click_closes_group_menu(self):
        self.open()
        with patch.object(self.lib,'_latest') as latest:
            self.click('l')
        latest.assert_called_once_with(self.bot,-10088)
        self.assertIn((-10088,1001),self.bot.deleted)
    def test_search_click_closes_menu_and_explains_command(self):
        self.open()
        self.click('s')
        self.assertTrue(any('/book TITLE' in text for _,text,_ in self.bot.answered))
        self.assertEqual(self.bot.deleted,[(-10088,1001)])
    def test_other_user_cannot_operate_owner_menu(self):
        self.open()
        self.click('l',uid=99)
        self.assertFalse(self.bot.deleted)
        self.assertIn('another user',self.bot.answered[-1][1].lower())
    def test_invalid_token_is_denied(self):
        self.open()
        c=SimpleNamespace(id='bad',message=self.bot.sent[0][-1],from_user=SimpleNamespace(id=42),data='gbm1:l:abcdef123456')
        self.bot.dispatch_callback(c)
        self.assertFalse(self.bot.deleted)
        self.assertIn('expired',self.bot.answered[-1][1].lower())
    def test_callback_replay_is_denied(self):
        self.open()
        c=self.click('s')
        self.bot.dispatch_callback(c)
        self.assertIn('expired',self.bot.answered[-1][1].lower())
    def test_no_private_menu_changes(self):
        self.assertEqual(new._is_target(msg(kind='private',cid=42)),False)
    def test_disable_rolls_back_to_old_handlers(self):
        os.environ['GROUP_LIBRARY_MENU_V1161_ENABLED']='false'
        res=self.bot.handlers[0][0](msg())
        self.assertIsInstance(res,FakeContinueHandling)
    def test_not_enabled_in_non_v116_mode(self):
        os.environ['GROUP_BOOK_ONLY_V116_ENABLED']='false'
        res=self.bot.handlers[0][0](msg())
        self.assertIsInstance(res,FakeContinueHandling)
    def test_group_not_allowed_no_menu(self):
        with patch.object(self.lib,'_allowed_group',return_value=False):
            self.bot.dispatch(msg())
        self.assertFalse(self.bot.sent)
    def test_menu_delete_failure_removes_keyboard(self):
        self.open()
        with patch.object(self.bot,'delete_message',side_effect=RuntimeError('deleted')),patch.object(self.bot,'edit_message_reply_markup') as edit:
            self.click('s')
            edit.assert_called_once()
    def test_latest_keeps_public_book_delivery_unchanged(self):
        self.open()
        with patch.object(self.lib,'_latest',side_effect=lambda b,c:b.send_message(c,'📚 Latest Books (1):')):
            self.click('l')
        self.assertTrue(any('Latest Books' in s[1] for s in self.bot.sent))
    def test_quiz_and_other_group_callbacks_still_blocked(self):
        self.open()
        cb=SimpleNamespace(id='legacy',message=self.bot.sent[0][-1],from_user=SimpleNamespace(id=42),data='nav:secret')
        self.bot.dispatch_callback(cb)
        self.assertTrue(any('private' in str(text).lower() for _,text,_ in self.bot.answered))

class InstallerTests(unittest.TestCase):
    BASE='bot = object()\nfrom group_ui_v115 import install_group_ui_guard\ninstall_group_ui_guard(bot)\nfrom group_books_only_v116 import install_book_only_group_gate\ninstall_book_only_group_gate(bot)\n'
    def test_preview_apply_and_repeat(self):
        import INSTALL_GROUP_LIBRARY_MENU_V1161 as installer
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'main.py').write_text(self.BASE,encoding='utf-8')
            self.assertTrue(installer.integrate(root,apply=False))
            self.assertEqual((root/'main.py').read_text(encoding='utf-8'),self.BASE)
            self.assertTrue(installer.integrate(root,apply=True))
            self.assertFalse(installer.integrate(root,apply=True))
            dst=(root/'main.py').read_text(encoding='utf-8')
            self.assertLess(dst.index('install_group_library_menu(bot)'),dst.index('install_group_ui_guard(bot)'))
    def test_missing_v116_fails_closed(self):
        import INSTALL_GROUP_LIBRARY_MENU_V1161 as inst
        with self.assertRaises(ValueError):inst.transform(self.BASE.replace('install_book_only_group_gate(bot)','not_installed()'))
    def test_crlf_is_supported(self):
        import INSTALL_GROUP_LIBRARY_MENU_V1161 as inst
        src=self.BASE.replace('\n','\r\n')
        new_src=inst.transform(src)
        compile(new_src,'main.py','exec')
    def test_no_existing_code_modified(self):
        import INSTALL_GROUP_LIBRARY_MENU_V1161 as inst
        src=inst.transform(self.BASE)
        self.assertIn('install_group_ui_guard(bot)',src)
        self.assertIn('install_book_only_group_gate(bot)',src)
        self.assertEqual(src.count('install_group_library_menu(bot)'),1)

if __name__=='__main__':unittest.main()
