"""Offline V11.5 security/compatibility tests (no Telegram or DB network)."""
from __future__ import annotations
import os
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import group_ui_v115 as mod
from INSTALL_GROUP_UI_V115 import integrate, transform


class Markup:
    def __init__(self): self.inline_keyboard = []
    def add(self, button): self.inline_keyboard.append([button])
class InlineKeyboardMarkup(Markup): pass
class ReplyKeyboardMarkup:
    def __init__(self, labels=None):
        self.keyboard=[[types.SimpleNamespace(text=x)] for x in (labels or [])]
class ReplyKeyboardRemove:
    def __init__(self, selective=False): self.selective=selective
class InlineKeyboardButton:
    def __init__(self, text, *, url=None, callback_data=None):
        self.text=text; self.url=url; self.callback_data=callback_data
class ContinueHandling: pass

class FakeBot:
    def __init__(self):
        self.handlers=[];self.callbacks=[];self.sent=[];self.deleted=[];self.answered=[]
        self.mid=100
    def message_handler(self,**kwargs):
        def decorator(fn): self.handlers.append((kwargs,fn));return fn
        return decorator
    def callback_query_handler(self,**kwargs):
        def decorator(fn): self.callbacks.append((kwargs,fn));return fn
        return decorator
    def send_message(self,chat_id,text,**kwargs):
        self.mid+=1
        self.sent.append((int(chat_id),str(text),kwargs))
        return types.SimpleNamespace(message_id=self.mid)
    def delete_message(self,chat_id,message_id):
        self.deleted.append((int(chat_id),int(message_id)))
        return True
    def answer_callback_query(self,id,text,**kwargs):self.answered.append((id,text,kwargs))

def msg(chat=-10099, txt='📦 More Tools', uid=17, mid=19, kind='supergroup'):
    return types.SimpleNamespace(chat=types.SimpleNamespace(id=chat,type=kind),
        from_user=types.SimpleNamespace(id=uid),text=txt,message_id=mid)

class UnitTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ, {
            'GROUP_UI_PROTECTION_ENABLED':'true','GROUP_UI_TIMER_ENABLED':'false',
            'GROUP_UI_PRIVATE_NAVIGATION':'true','GROUP_UI_DELETE_NAV_INPUT':'true',
            'BOOK_LIBRARY_BOT_USERNAME':'StudentTestBot',
        });self.env.start()
        self.modules=patch.dict(sys.modules, {
            'telebot':types.SimpleNamespace(types=types.SimpleNamespace(
                InlineKeyboardMarkup=InlineKeyboardMarkup,
                InlineKeyboardButton=InlineKeyboardButton,
                ReplyKeyboardMarkup=ReplyKeyboardMarkup,
                ReplyKeyboardRemove=ReplyKeyboardRemove)),
            'telebot.handler_backends':types.SimpleNamespace(ContinueHandling=ContinueHandling)
        });self.modules.start()
        with mod._LOCK: mod._GROUPS.clear();mod._LOCAL.clear()
        self.bot=FakeBot();mod.install_group_ui_guard(self.bot)
        self.handler=self.bot.handlers[0][1]
        self.callback=self.bot.callbacks[0][1]
    def tearDown(self):self.modules.stop();self.env.stop()

    def test_group_navigation_redirect_and_delete_command(self):
        self.handler(msg())
        self.assertEqual(self.bot.deleted,[(-10099,19)])
        self.assertEqual(self.bot.sent[0][0],-10099)
        self.assertIn('Open your own bot',self.bot.sent[0][1])
        kb=self.bot.sent[0][2]['reply_markup']
        self.assertIsInstance(kb,ReplyKeyboardRemove)
        self.assertTrue(kb.selective)
        self.assertIn('t.me/StudentTestBot?',self.bot.sent[0][1])

    def test_group_command_with_username(self):
        self.handler(msg(txt='/start@StudentTestBot'))
        self.assertIn('Open your own bot',self.bot.sent[0][1])

    def test_group_books_still_run(self):
        returned=self.handler(msg(txt='/book Quran'))
        self.assertIsInstance(returned,ContinueHandling)
        self.assertEqual(self.bot.sent,[])

    def test_book_commands_can_expire_after_five_minutes(self):
        with patch.dict(os.environ,{'GROUP_UI_TIMER_ENABLED':'true'}):
            with patch.object(mod,'_remember') as remember:
                returned=self.handler(msg(txt='/book Quran',mid=91))
        self.assertIsInstance(returned,ContinueHandling)
        remember.assert_called_once_with(self.bot,-10099,91,kind='menu')

    def test_group_quiz_command_unchanged(self):
        returned=self.handler(msg(txt='/groupquiz join'))
        self.assertIsInstance(returned,ContinueHandling)

    def test_regular_group_talk_unchanged(self):
        returned=self.handler(msg(txt='I am studying for exams'))
        self.assertIsInstance(returned,ContinueHandling)
        self.assertEqual(self.bot.deleted,[])

    def test_private_send_unchanged(self):
        m=self.bot.send_message(42,'Personal menu',reply_markup=ReplyKeyboardMarkup())
        self.assertEqual(self.bot.sent[-1][1],'Personal menu')
        self.assertEqual(m.message_id,101)

    def test_old_group_reply_keyboard_becomes_private_link(self):
        self.handler(msg(txt='Good morning'))
        self.bot.send_message(-10099,'Choose a category',reply_markup=ReplyKeyboardMarkup(['📦 More Tools']))
        self.assertIn('private',self.bot.sent[-1][1])
        self.assertIsInstance(self.bot.sent[-1][2]['reply_markup'],InlineKeyboardMarkup)

    def test_group_quiz_reply_keyboard_not_replaced(self):
        self.handler(msg(txt='/groupquiz join'))
        kb=ReplyKeyboardMarkup(['A', 'B', 'C'])
        self.bot.send_message(-10099,'Group quiz: choose an answer',reply_markup=kb)
        self.assertEqual(self.bot.sent[-1][1],'Group quiz: choose an answer')
        self.assertIs(self.bot.sent[-1][2]['reply_markup'],kb)

    def test_group_quiz_inline_keyboard_not_timed(self):
        self.handler(msg(txt='/groupquiz join'))
        kb=InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton('Answer A',callback_data='groupquiz:A'))
        with patch.dict(os.environ,{'GROUP_UI_TIMER_ENABLED':'true'}):
            with patch.object(mod,'_remember') as remember:
                self.bot.send_message(-10099,'Group quiz: choose an answer',reply_markup=kb)
                remember.assert_not_called()

    def test_public_book_url_left_untouched(self):
        self.handler(msg(txt='/book Quran'))
        kb=InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton('Quran',url='https://t.me/StudentTestBot?start=book_'+'a'*32))
        self.bot.send_message(-10099,'📚 Book results for Quran',reply_markup=kb)
        self.assertEqual(self.bot.sent[-1][1],'📚 Book results for Quran')

    def test_not_privacy_callback_redirect_on_group_quiz(self):
        predicate=self.bot.callbacks[0][0]['func']
        c=types.SimpleNamespace(message=msg(),data='groupquiz:123')
        self.assertFalse(predicate(c))

    def test_old_book_callback_denied_group(self):
        c=types.SimpleNamespace(id='x',message=msg(mid=77),data='lib2:page:123')
        self.callback(c)
        self.assertEqual(self.bot.deleted[-1],(-10099,77))
        self.assertTrue(self.bot.answered[-1][2]['show_alert'])

    def test_private_book_callback_unaffected(self):
        predicate=self.bot.callbacks[0][0]['func']
        c=types.SimpleNamespace(id='x',message=msg(chat=42,kind='private'),data='lib2:page:123')
        self.assertFalse(predicate(c))

    def test_private_mode_off_no_redirect(self):
        with patch.dict(os.environ,{'GROUP_UI_PROTECTION_ENABLED':'false'}):
            ret=self.handler(msg())
            self.assertIsInstance(ret,ContinueHandling)
        self.assertEqual(self.bot.sent,[])

    def test_does_not_delete_book_group_command(self):
        self.handler(msg(txt='/book Quran'))
        self.assertEqual(self.bot.deleted,[])

    def test_timer_limits(self):
        self.assertEqual(mod.seconds(),300)
        with patch.dict(os.environ,{'GROUP_UI_DELETE_AFTER_SECONDS':'10'}):self.assertEqual(mod.seconds(),60)
        with patch.dict(os.environ,{'GROUP_UI_DELETE_AFTER_SECONDS':'2000'}):self.assertEqual(mod.seconds(),1800)

    def test_fallback_queue_deleted_at_due_time(self):
        now=datetime(2026,10,31,tzinfo=timezone.utc)
        with patch.dict(os.environ,{'GROUP_UI_TIMER_ENABLED':'true'}):
            with patch.object(mod,'_db',side_effect=RuntimeError('offline')):
                mod._remember(self.bot,-10099,901,now=now)
                self.assertEqual(mod.cleanup_once(self.bot,now=now+timedelta(seconds=299)),0)
                self.assertNotIn((-10099,901),self.bot.deleted)
                self.assertEqual(mod.cleanup_once(self.bot,now=now+timedelta(seconds=310)),1)
        self.assertIn((-10099,901),self.bot.deleted)

    def test_queue_makes_no_user_pii(self):
        now=datetime(2026,10,31,tzinfo=timezone.utc)
        db=MagicMock()
        with patch.dict(os.environ,{'GROUP_UI_TIMER_ENABLED':'true'}):
            mod._remember(self.bot,-10099,102,now=now,db=db)
        values=db.table.return_value.upsert.call_args.args[0]
        self.assertEqual(set(values),{'chat_id','message_id','message_type','delete_at','attempts'})

    def test_installer_adds_code_after_telebot_before_flask(self):
        src="import telebot\nfrom flask import Flask\nbot = telebot.TeleBot('abc')\napp = Flask(__name__)\n"
        out=transform(src)
        self.assertLess(out.index('bot = telebot.TeleBot'),out.index('install_group_ui_guard(bot)'))
        self.assertLess(out.index('install_group_ui_guard(bot)'),out.index('app = Flask'))
        self.assertEqual(transform(out),out)

    def test_installer_no_change_on_bad_main(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'main.py';p.write_text('print(1)\n',encoding='utf-8')
            with self.assertRaises(ValueError):integrate(td,apply=True)
            self.assertEqual(p.read_text(encoding='utf-8'),'print(1)\n')

    def test_installer_copy_on_test_snapshot(self):
        src=Path('/mnt/data/Book_Library_V114_Compatibility_Fix/verification_workspace/main.py')
        if not src.is_file():self.skipTest('Optional reference snapshot not mounted')
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'main.py';p.write_bytes(src.read_bytes())
            self.assertTrue(integrate(td,apply=False))
            self.assertTrue(integrate(td,apply=True))
            self.assertFalse(integrate(td,apply=True))
            compile(p.read_text(encoding='utf-8'),'main.py','exec')

if __name__ == '__main__':unittest.main()
