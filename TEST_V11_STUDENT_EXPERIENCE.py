"""Offline V11 functional and installer regression tests. No Telegram/API/DB traffic."""
from __future__ import annotations
import io
import os
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import v11_center as c
import v11_metrics as p
from INSTALL_V11_STUDENT_EXPERIENCE import transform, integrate, BUTTON


class FakeButton:
    def __init__(self, text, callback_data):
        self.text = text
        self.callback_data = callback_data


class FakeMarkup:
    def __init__(self, **kwargs):
        self.buttons = []
    def add(self, *buttons):
        self.buttons.extend(buttons)


class Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeBot:
    def __init__(self):
        self.commands = {}
        self.callbacks = []
        self.others = []
        self.sent = []
        self.acks = []
    def message_handler(self, commands=None, **kwargs):
        def register(fn):
            if commands:
                for command in commands:
                    self.commands[command] = fn
            else:
                self.others.append((kwargs, fn))
            return fn
        return register
    def callback_query_handler(self, func=None):
        def register(fn):
            self.callbacks.append((func, fn))
            return fn
        return register
    def send_message(self, chat, text, **kwargs):
        self.sent.append((chat, text, kwargs))
    def answer_callback_query(self, callback_id, text=''):
        self.acks.append((callback_id, text))
    def message(self, text='/study', uid=44, chat_type='private'):
        chat = 987 if chat_type != 'private' else uid
        return Obj(chat=Obj(id=chat, type=chat_type), from_user=Obj(id=uid), text=text)
    def cmd(self, line='/study', uid=44, chat_type='private'):
        msg = self.message(line, uid, chat_type)
        self.commands[line[1:].split(' ', 1)[0]](msg)
        return self.sent[-1][1]
    def callback(self, code='docs', uid=44, data=None, chat_type='private'):
        if data is None:
            kb = self.sent[-1][2]['reply_markup']
            button = next(b for b in kb.buttons if b.callback_data.endswith(':' + code))
            data = button.callback_data
        # callback.message.from_user is normally the BOT, not the person pressing a button
        msg = Obj(chat=Obj(id=uid, type=chat_type), from_user=Obj(id=123456), text=None)
        call = Obj(id='callback-1', data=data, from_user=Obj(id=uid), message=msg)
        for predicate, handler in self.callbacks:
            if predicate(call):
                handler(call)
                break
        return (self.sent[-1][1] if self.sent else None, self.acks[-1][1] if self.acks else None)


class TextTests(unittest.TestCase):
    def test_page_coverage(self):
        self.assertEqual(set(c.PAGES), {'docs', 'ai', 'practice', 'more', 'access', 'errors'})
    def test_relevant_real_commands(self):
        self.assertIn('/v10save', c.PAGES['docs'])
        self.assertIn('/v101confirm', c.PAGES['ai'])
        self.assertIn('/v101mock', c.PAGES['practice'])
        self.assertIn('/v8', c.PAGES['more'])
        self.assertIn('/verify_adult', c.PAGES['access'])
    def test_menu_privacy_copy(self):
        self.assertIn('do not contact Gemini or Supabase', c.HOME_TEXT)
    def test_pilot_mode_warns(self):
        with patch.dict(os.environ, {'STUDY_ACCESS_MODE': 'pilot'}, clear=True):
            text = c.status_text(44, verifier=lambda x: self.fail('must not call verified check'))
        self.assertIn('not the active study access mode', text)
    def test_verified_status_true(self):
        with patch.dict(os.environ, {'STUDY_ACCESS_MODE': 'verified_adults'}, clear=True):
            self.assertIn('verification: active', c.status_text(5, verifier=lambda uid: uid == 5))
    def test_verified_status_unknown(self):
        with patch.dict(os.environ, {'STUDY_ACCESS_MODE': 'verified_adults'}, clear=True):
            self.assertIn('not confirmed', c.status_text(5, verifier=lambda uid: False))
    def test_verification_exception_sanitized(self):
        with patch.dict(os.environ, {'STUDY_ACCESS_MODE': 'verified_adults'}, clear=True):
            def boom(uid):raise RuntimeError('TOP-SECRET')
            with patch.object(c.LOG, 'warning'):
                value = c.status_text(5, verifier=boom)
        self.assertIn('temporarily unavailable', value)
        self.assertNotIn('TOP-SECRET', value)
    def test_admin_list(self):
        with patch.dict(os.environ, {'V91_ADMIN_USER_IDS': ' 44, 55, NaN '}, clear=True):
            self.assertTrue(c.admin(55))
            self.assertFalse(c.admin(5))
            self.assertFalse(c.admin('NaN'))
    def test_no_admin_if_empty(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(c.admin(44))
    def test_enabled_default_false(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(c.enabled())
    def test_enabled_true(self):
        with patch.dict(os.environ, {'V11_ENABLED': 'YES'}, clear=True):
            self.assertTrue(c.enabled())
    def test_private_check(self):
        b=FakeBot()
        self.assertTrue(c.private(b.message()))
        self.assertFalse(c.private(b.message(chat_type='group')))
    def test_diag_does_not_show_secrets(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY':'extremely-secret','SUPABASE_SERVICE_ROLE_KEY':'db-secret'}, clear=True):
            d = c.diagnostic_text()
        self.assertNotIn('extremely-secret', d)
        self.assertNotIn('db-secret', d)
        self.assertIn('not a live API/SQL health check', d)
    def test_token_single_use(self):
        token=c._new_token(44,44)
        self.assertTrue(c._redeem_token(token,44,44))
        self.assertFalse(c._redeem_token(token,44,44))
    def test_token_foreign_user_not_consumed(self):
        token=c._new_token(44,44)
        self.assertFalse(c._redeem_token(token,45,44))
        self.assertTrue(c._redeem_token(token,44,44))
    def test_token_expired(self):
        token=c._new_token(44,44)
        with c._LOCK:
            uid, chat, stamp=c._TOKENS[token]
            c._TOKENS[token]=(uid, chat, stamp-c.TOKEN_TTL-1)
        self.assertFalse(c._redeem_token(token,44,44))
    def test_tokens_bounded(self):
        for _ in range(c.TOKEN_LIMIT+30):c._new_token(44,44)
        self.assertLessEqual(len(c._TOKENS), c.TOKEN_LIMIT)
    def test_metrics_no_pii(self):
        p.record('home', 4.2)
        d=p.report()
        self.assertIn('median',d)
        self.assertNotIn('user_id',d)
    def test_metrics_invalid_clamped(self):
        p.record('not-a-whitelisted-name', 900000)
        self.assertIn('other:',p.report())
    def test_markups_short(self):
        sysmod=types.ModuleType('telebot');sysmod.types=Obj(InlineKeyboardButton=FakeButton, InlineKeyboardMarkup=FakeMarkup)
        with patch.dict(sys.modules, {'telebot':sysmod}):
            k=c._keyboard(44,44,c.HOME_BUTTONS)
        self.assertEqual(len(k.buttons), 8)
        self.assertTrue(all(len(x.callback_data)<=64 for x in k.buttons))


class BotTests(unittest.TestCase):
    def setUp(self):
        self.bot=FakeBot()
        self.types=types.ModuleType('telebot')
        self.types.types=Obj(InlineKeyboardButton=FakeButton,InlineKeyboardMarkup=FakeMarkup)
        self.module=patch.dict(sys.modules, {'telebot':self.types});self.module.start();self.addCleanup(self.module.stop)
        self.flags=patch.dict(os.environ, {'V11_ENABLED':'true','STUDY_ACCESS_MODE':'pilot','V91_ADMIN_USER_IDS':'44'}, clear=True)
        self.flags.start();self.addCleanup(self.flags.stop)
        c.register_v11_handlers(self.bot)
    def test_registers_all_commands(self):
        self.assertEqual(set(self.bot.commands), {'study','v11','studyhelp','studystatus','studycancel','studydiag','studyperf'})
    def test_home_without_any_db_access(self):
        with patch.dict(sys.modules, {'study_access_v9':None}):
            text=self.bot.cmd('/study')
        self.assertIn('Study Center',text)
    def test_menu_alias(self):
        self.assertIn('Study Center', self.bot.cmd('/v11'))
    def test_text_menu(self):
        msg=self.bot.message(c.BUTTON)
        self.bot.others[0][1](msg)
        self.assertIn('Study Center',self.bot.sent[-1][1])
    def test_disabled_returns_message(self):
        os.environ['V11_ENABLED']='false'
        self.assertIn('not enabled',self.bot.cmd('/study'))
    def test_group_denied(self):
        self.assertIn('private Telegram chat',self.bot.cmd('/study', chat_type='group'))
    def test_topic_help(self):
        self.assertIn('/v101mock',self.bot.cmd('/studyhelp practice'))
    def test_help_default(self):
        self.assertIn('Topics:',self.bot.cmd('/studyhelp'))
    def test_button_page_and_back(self):
        self.bot.cmd('/study')
        text, ack=self.bot.callback('docs')
        self.assertIn('/v10save',text)
        self.assertEqual(ack,'Done')
        text, ack=self.bot.callback('home')
        self.assertIn('Study Center',text)
    def test_buttons_are_single_use(self):
        self.bot.cmd('/study')
        data=self.bot.sent[-1][2]['reply_markup'].buttons[0].callback_data
        self.bot.callback(data=data)
        text,ack=self.bot.callback(data=data)
        self.assertIn('already-used',ack)
    def test_stale_button_ack(self):
        self.bot.cmd('/study')
        _,ack=self.bot.callback(data='v11:invalid:docs')
        self.assertIn('Expired',ack)
    def test_invalid_button_ack(self):
        self.bot.cmd('/study')
        _,ack=self.bot.callback(data='v11:token:killall')
        self.assertIn('Invalid',ack)
    def test_group_callback_denied(self):
        self.bot.cmd('/study')
        _,ack=self.bot.callback('docs',chat_type='group')
        self.assertIn('Private chat',ack)
    def test_disabled_callback_ack(self):
        self.bot.cmd('/study')
        os.environ['V11_ENABLED']='false'
        _,ack=self.bot.callback('docs')
        self.assertIn('disabled',ack)
    def test_callback_wrong_user_cannot_redeem(self):
        self.bot.cmd('/study')
        data=self.bot.sent[-1][2]['reply_markup'].buttons[0].callback_data
        # attacker cannot redeem a token made for another chat.
        msg=Obj(chat=Obj(id=44,type='private'),from_user=Obj(id=999))
        call=Obj(id='x',data=data,from_user=Obj(id=100),message=msg)
        self.bot.callbacks[0][1](call)
        self.assertIn('Private chat',self.bot.acks[-1][1])
        self.assertIn('/v10save',self.bot.callback(data=data)[0])
    def test_status_shows_switches(self):
        with patch.dict(os.environ, {'V10_ENABLED':'true'}):
            self.assertIn('V10: ON',self.bot.cmd('/studystatus'))
    def test_no_admin_access_to_diagnostics(self):
        self.assertIn('Administrator access required',self.bot.cmd('/studydiag',uid=50))
    def test_admin_diagnostics(self):
        self.assertIn('deployment diagnostics',self.bot.cmd('/studydiag'))
    def test_no_admin_metrics(self):
        self.assertIn('Administrator access required',self.bot.cmd('/studyperf',uid=50))
    def test_admin_perf(self):
        self.assertIn('local performance',self.bot.cmd('/studyperf'))
    def test_cancel_only_user_states(self):
        v10=types.ModuleType('v10_bot');v10._clear=Mock()
        v101=types.ModuleType('v101_bot');v101.cancel=Mock()
        with patch.dict(sys.modules, {'v10_bot':v10,'v101_bot':v101}):
            result=self.bot.cmd('/studycancel',uid=44)
            self.assertIn('V8/V9 sessions are unchanged',result)
            v10._clear.assert_called_once_with(44)
            v101.cancel.assert_called_once_with(44)
    def test_cancel_button(self):
        v10=types.ModuleType('v10_bot');v10._clear=Mock()
        v101=types.ModuleType('v101_bot');v101.cancel=Mock()
        with patch.dict(sys.modules, {'v10_bot':v10,'v101_bot':v101}):
            self.bot.cmd('/study')
            text, ack=self.bot.callback('cancel')
            self.assertIn('temporary V10/V10.1',text)
            self.assertEqual(ack,'Done')
            v10._clear.assert_called_once_with(44)
            v101.cancel.assert_called_once_with(44)
    def test_cancel_does_not_touch_db(self):
        v10=types.ModuleType('v10_bot');v10._clear=lambda uid:None
        v101=types.ModuleType('v101_bot');v101.cancel=lambda uid:None
        with patch.dict(sys.modules, {'v10_bot':v10,'v101_bot':v101,'v101_store':None}):
            self.assertIn('Stored documents',self.bot.cmd('/studycancel'))
    def test_metrics_after_command(self):
        self.bot.cmd('/study')
        self.assertIn('home:',p.report())


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'main.py').write_text('register_v101_handlers(bot)\nfrom v10_bot import register_v10_handlers\n',encoding='utf-8')
        (self.root/'ui_v57.py').write_text('CAT_MORE="more"\nALL_UI_BUTTONS = set()\n',encoding='utf-8')
        (self.root/'navigation.py').write_text('GLOBAL_BUTTONS=set()\nGLOBAL_BUTTONS.add("📝 Text → PDF")\n',encoding='utf-8')
    def test_preview_no_change(self):
        originals={x:p.read_bytes() for x in ('main.py','ui_v57.py','navigation.py') for p in [self.root/x]}
        out=[]
        self.assertEqual(len(integrate(self.root, output=out.append)),3)
        self.assertIn('CHECK OK',out[-1])
        self.assertEqual(originals,{x:(self.root/x).read_bytes() for x in originals})
    def test_apply_and_idempotence(self):
        out=[]
        self.assertEqual(len(integrate(self.root,apply=True,output=out.append)),3)
        self.assertEqual(integrate(self.root,apply=True,output=out.append),[])
        self.assertTrue(list(self.root.glob('V11_BACKUP_*')))
    def test_registration_order(self):
        integrate(self.root,apply=True,output=lambda x:None)
        text=(self.root/'main.py').read_text(encoding='utf-8')
        self.assertLess(text.index('register_v11_handlers(bot)'),text.index('register_v101_handlers(bot)'))
    def test_preserves_crlf_and_bom(self):
        b= b'\xef\xbb\xbf' + 'register_v101_handlers(bot)\r\n'.encode('utf-8')
        (self.root/'main.py').write_bytes(b)
        integrate(self.root,apply=True,output=lambda x:None)
        payload=(self.root/'main.py').read_bytes()
        self.assertTrue(payload.startswith(b'\xef\xbb\xbf'))
        self.assertNotIn(b'\n',payload.replace(b'\r\n',b''))
    def test_missing_anchor_fails_all_before_writes(self):
        before=(self.root/'main.py').read_bytes()
        (self.root/'navigation.py').write_text('GLOBAL_BUTTONS=set()',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'navigation'):
            integrate(self.root,apply=True,output=lambda x:None)
        self.assertEqual((self.root/'main.py').read_bytes(),before)
        self.assertFalse(list(self.root.glob('V11_BACKUP_*')))
    def test_v101_must_exist_first(self):
        with self.assertRaisesRegex(ValueError, 'V10.1'):
            transform('main.py','register_v10_handlers(bot)')
    def test_ui_and_nav_new_buttons(self):
        integrate(self.root,apply=True,output=lambda x:None)
        self.assertIn(BUTTON,(self.root/'ui_v57.py').read_text(encoding='utf-8'))
        self.assertIn(BUTTON,(self.root/'navigation.py').read_text(encoding='utf-8'))
    def test_no_extra_files_modification(self):
        (self.root/'v10_bot.py').write_bytes(b'NOT TOUCH THIS')
        integrate(self.root,apply=True,output=lambda x:None)
        self.assertEqual((self.root/'v10_bot.py').read_bytes(),b'NOT TOUCH THIS')


if __name__ == '__main__':
    unittest.main()
