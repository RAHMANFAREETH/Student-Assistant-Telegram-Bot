import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import group_books_only_v116 as gate
import group_ui_v115 as previous


def msg(text='small', kind='supergroup', cid=-10088, uid=42, mid=101):
    return SimpleNamespace(chat=SimpleNamespace(id=cid, type=kind),
                           from_user=SimpleNamespace(id=uid), text=text, message_id=mid)


class FakeContinueHandling: pass

class FakeButton:
    def __init__(self,text,url=None): self.text=text;self.url=url

class FakeMarkup:
    def __init__(self): self.inline_keyboard=[]
    def add(self,b): self.inline_keyboard.append([b])

class FakeTypes:
    InlineKeyboardMarkup=FakeMarkup
    InlineKeyboardButton=FakeButton

class FakeBot:
    def __init__(self):
        self.sent=[]; self.deleted=[]; self.answered=[]; self.handlers=[]; self.callbacks=[]
        self.mid=500
    def send_message(self, cid, text, *args, **kw):
        self.mid+=1
        self.sent.append((int(cid),text,kw))
        return SimpleNamespace(message_id=self.mid, chat=SimpleNamespace(id=cid))
    def delete_message(self, chat,mid):
        self.deleted.append((int(chat),int(mid)))
        return True
    def answer_callback_query(self, cid, text=None, show_alert=None):
        self.answered.append((cid,text,show_alert))
    def message_handler(self,*args,**kwargs):
        def reg(fn):
            self.handlers.append((fn,kwargs))
            return fn
        return reg
    def callback_query_handler(self,*args,**kwargs):
        def reg(fn):
            self.callbacks.append((fn,kwargs))
            return fn
        return reg
    def h(self,name):
        return next(fn for fn,_ in self.handlers if fn.__name__==name)
    def cb(self,name):
        return next(fn for fn,_ in self.callbacks if fn.__name__==name)


class GateTests(unittest.TestCase):
    def setUp(self):
        previous._GROUPS.clear();previous._LOCAL.clear()
        self.p=patch.dict(os.environ,{
            'GROUP_BOOK_ONLY_V116_ENABLED':'true',
            'GROUP_UI_PROTECTION_ENABLED':'true',
            'GROUP_UI_TIMER_ENABLED':'false',
            'BOOK_LIBRARY_ENABLED':'true',
            'BOOK_LIBRARY_V113_ENABLED':'true',
            'BOOK_LIBRARY_AUTO_GROUP_SEARCH':'true',
            'BOOK_LIBRARY_ALLOW_ALL_GROUPS':'true',
            'BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT':'false',
            'BOOK_LIBRARY_BOT_USERNAME':'StudentExampleBot',
            'GROUP_UI_DELETE_NAV_INPUT':'true',
            'BOOK_LIBRARY_PRIVATE_GROUP_RESULTS':'false',
        })
        self.p.start()
        self.modules=patch.dict(sys.modules, {
            'telebot':SimpleNamespace(types=FakeTypes),
            'telebot.handler_backends':SimpleNamespace(ContinueHandling=FakeContinueHandling)
        })
        self.modules.start()
        self.worker=patch.object(previous,'_start_worker',return_value=None)
        self.worker.start()
        self.bot=FakeBot()
        previous.install_group_ui_guard(self.bot)
        gate.install_book_only_group_gate(self.bot)
        import book_library_bot as lib
        self.lib=lib
        self.p_lib=patch.multiple(lib,_enabled=lambda:True,_allowed_group=lambda cid:True,
                                  _verified=lambda uid:True,_cooldown=lambda *a,**k:False)
        self.p_lib.start()

    def tearDown(self):
        self.p_lib.stop();self.worker.stop();self.modules.stop();self.p.stop()
        previous._GROUPS.clear();previous._LOCAL.clear()

    def dispatch(self,m):
        from telebot.handler_backends import ContinueHandling
        for fn,kw in self.bot.handlers:
            if ('text' in kw.get('content_types',['text'])) and getattr(m,'text',None) is None:
                continue
            filt=kw.get('func',lambda m:True)
            if not filt(m): continue
            ans=fn(m)
            if not isinstance(ans,ContinueHandling): return ans

    def test_install_order_and_repeat(self):
        self.assertTrue(self.bot._group_ui_v115_installed)
        self.assertTrue(self.bot._group_books_only_v116_installed)
        n=len(self.bot.handlers)
        gate.install_book_only_group_gate(self.bot)
        self.assertEqual(n,len(self.bot.handlers))

    def test_requires_previous_guard(self):
        with self.assertRaises(RuntimeError):gate.install_book_only_group_gate(FakeBot())

    def test_library_book_search_in_group(self):
        def reply(bot,cid,q,**kwargs):bot.send_message(cid,'🔎 Books matching: '+q,reply_markup=None);return True
        with patch.object(self.lib,'_search',side_effect=reply) as p:
            self.dispatch(msg('/book small'))
            p.assert_called_once()
        self.assertEqual(self.bot.sent[0][0],-10088)

    def test_latest_in_group(self):
        with patch.object(self.lib,'_latest',side_effect=lambda b,c:b.send_message(c,'📚 Latest Books (1):')):
            self.dispatch(msg('/booklatest'))
        self.assertIn('Latest Books',self.bot.sent[-1][1])

    def test_books_without_query_show_latest(self):
        with patch.object(self.lib,'_latest') as p:
            self.dispatch(msg('/books'))
            p.assert_called_once()

    def test_plain_match_search_in_group(self):
        with patch.object(gate,'_is_book_match',return_value=True), patch.object(self.lib,'_search',return_value=True) as p:
            self.dispatch(msg('Small Habits'))
            p.assert_called_once()

    def test_plain_nonmatch_silent(self):
        with patch.object(gate,'_is_book_match',return_value=False):
            self.dispatch(msg('Hello my classmates'))
        self.assertEqual(self.bot.sent,[])

    def test_plain_text_not_routed_to_older_handlers(self):
        other=[]
        @self.bot.message_handler(content_types=['text'],func=lambda m:True)
        def old_wildcard(m):other.append(1)
        with patch.object(gate,'_is_book_match',return_value=False):
            self.dispatch(msg('Hello everyone'))
        self.assertEqual(other,[])

    def test_other_command_private_only(self):
        self.dispatch(msg('/pdfmerge'))
        self.assertEqual(len(self.bot.sent),1)
        self.assertIn('only book library',self.bot.sent[0][1].lower())

    def test_private_library_commands_redirect(self):
        self.dispatch(msg('/bookfavs'))
        self.assertIn('https://t.me/StudentExampleBot',self.bot.sent[-1][1])

    def test_plain_text_ignored_if_auto_search_disabled(self):
        os.environ['BOOK_LIBRARY_AUTO_GROUP_SEARCH']='false'
        with patch.object(gate,'_is_book_match',side_effect=AssertionError('must not search')):
            self.dispatch(msg('small'))
        self.assertFalse(self.bot.sent)

    def test_media_group_blocked(self):
        self.assertIsNone(self.bot.h('group_books_only_media')(msg(None)))

    def test_group_callback_blocked(self):
        cb=SimpleNamespace(id='query',message=msg(kind='group'),from_user=SimpleNamespace(id=99))
        self.bot.cb('group_books_only_callback')(cb)
        self.assertEqual(len(self.bot.answered),1)
        self.assertTrue(self.bot.answered[0][2])

    def test_private_callback_unaffected(self):
        m=msg(kind='private',cid=42)
        fn,kwargs=next((fn,kw) for fn,kw in self.bot.callbacks if fn.__name__=='group_books_only_callback')
        self.assertFalse(kwargs['func'](SimpleNamespace(message=m)))

    def test_other_bot_mention_ignored(self):
        self.dispatch(msg('/book@DifferentBot small'))
        self.assertFalse(self.bot.sent)

    def test_unauthorized_group_denied(self):
        with patch.object(self.lib,'_allowed_group',return_value=False):
            self.dispatch(msg('/book small'))
        self.assertIn('unavailable',self.bot.sent[-1][1])

    def test_no_match_explicit_book_gets_notice(self):
        with patch.object(self.lib,'_search',return_value=False):
            self.dispatch(msg('/book Unfindable'))
        self.assertIn('No matching',self.bot.sent[-1][1])

    def test_public_book_url_footer_with_timer(self):
        from telebot import types
        os.environ['GROUP_UI_TIMER_ENABLED']='true'
        with patch.object(previous,'_remember') as remember:
            previous._GROUPS.add(-10088)
            kb=types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton('📖 Book',url='https://t.me/StudentExampleBot?start=book_'+'a'*32))
            self.bot.send_message(-10088,'🔎 Books matching: small',reply_markup=kb)
            self.assertIn('auto-deletes after 5 minutes',self.bot.sent[-1][1])
            remember.assert_called_once()

    def test_no_footer_private(self):
        os.environ['GROUP_UI_TIMER_ENABLED']='true'
        self.bot.send_message(42,'Hello')
        self.assertNotIn('auto-delete',self.bot.sent[-1][1])

    def test_disabled_gate_delegates(self):
        from telebot.handler_backends import ContinueHandling
        os.environ['GROUP_BOOK_ONLY_V116_ENABLED']='false'
        result=self.bot.h('group_books_only_text')(msg('hello'))
        self.assertIsInstance(result,ContinueHandling)


class InstallerTests(unittest.TestCase):
    def test_check_apply_repeat(self):
        import INSTALL_GROUP_BOOK_ONLY_V116 as inst
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'main.py'
            path.write_text('from flask import Flask\ninstall_group_ui_guard(bot)\napp = Flask(__name__)\n',encoding='utf-8')
            self.assertTrue(inst.integrate(temp,apply=False))
            self.assertTrue(inst.integrate(temp,apply=True))
            self.assertFalse(inst.integrate(temp,apply=True))
            self.assertEqual(path.read_text(encoding='utf-8').count(inst.MARK),1)

    def test_invalid_anchor_does_not_modify(self):
        import INSTALL_GROUP_BOOK_ONLY_V116 as inst
        with self.assertRaises(ValueError):inst.transform('app = Flask(__name__)')

    def test_windows_crlf(self):
        import INSTALL_GROUP_BOOK_ONLY_V116 as inst
        src='install_group_ui_guard(bot)\r\napp = Flask(__name__)\r\n'
        self.assertIn(inst.MARK,inst.transform(src))

if __name__ == '__main__':unittest.main()
