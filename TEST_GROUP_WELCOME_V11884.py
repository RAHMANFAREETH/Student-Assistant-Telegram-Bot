from __future__ import annotations
import os
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch
import group_welcome_v11884 as w

def member(uid=21, username=None, first_name='Amina', is_bot=False):
    return NS(id=uid, username=username, first_name=first_name, is_bot=is_bot)

def event(*members, kind='supergroup', cid=-100123):
    return NS(chat=NS(type=kind,id=cid),new_chat_members=list(members))

class Bot:
    def __init__(self):self.sent=[];self.handlers=[]
    def send_message(self,cid,text,**kwargs):
        self.sent.append((cid,text,kwargs))
        return NS(message_id=100+len(self.sent))
    def message_handler(self,**kw):
        def register(fn):self.handlers.append((fn,kw));return fn
        return register

class WelcomeTests(unittest.TestCase):
    def setUp(self):
        w._SEEN.clear()
        self.env=patch.dict(os.environ, {'GROUP_WELCOME_V11884_ENABLED':'true','GROUP_BOOK_ONLY_V116_ENABLED':'true','GROUP_WELCOME_AUTO_DELETE_V11884':'false'})
        self.env.start();self.addCleanup(self.env.stop)
        self.permission=patch.object(w,'_allowed',return_value=True)
        self.permission.start();self.addCleanup(self.permission.stop)
        self.bot=Bot()
    def test_display_name(self):
        self.assertEqual(w.handle_join(self.bot,event(member())),1)
        self.assertIn('Amina',self.bot.sent[0][1])
    def test_username(self):
        w.handle_join(self.bot,event(member(username='reader_11')))
        self.assertIn('@reader_11',self.bot.sent[0][1])
    def test_search_instructions(self):
        w.handle_join(self.bot,event(member()))
        s=self.bot.sent[0][1]
        for term in ('/book Quran','/book The Psychology of Money','/booklatest','https://t.me/Student_Sl_Assistant_bot','18+'):
            self.assertIn(term,s)
    def test_no_command_changes(self):
        w.handle_join(self.bot,event(member()))
        self.assertNotIn('/mediaupload',self.bot.sent[0][1])
    def test_idempotence(self):
        msg=event(member())
        self.assertEqual(w.handle_join(self.bot,msg),1)
        self.assertEqual(w.handle_join(self.bot,msg),0)
    def test_unauthorized(self):
        with patch.object(w,'_allowed',return_value=False):
            self.assertEqual(w.handle_join(self.bot,event(member())),0)
    def test_flag_off(self):
        with patch.dict(os.environ,{'GROUP_WELCOME_V11884_ENABLED':'false'}):
            self.assertEqual(w.handle_join(self.bot,event(member())),0)
    def test_private_ignored(self):
        self.assertEqual(w.handle_join(self.bot,event(member(),kind='private')),0)
    def test_bot_ignored(self):
        self.assertEqual(w.handle_join(self.bot,event(member(is_bot=True))),0)
    def test_multiple(self):
        self.assertEqual(w.handle_join(self.bot,event(member(uid=1),member(uid=2))),2)
    def test_safe_display_name(self):
        w.handle_join(self.bot,event(member(first_name='Hello\n\u202eAdmin',username='bad handle!')))
        self.assertIn('Hello Admin',self.bot.sent[0][1])
    def test_handler_installer(self):
        w.install_group_welcome(self.bot)
        w.install_group_welcome(self.bot)
        self.assertEqual(len(self.bot.handlers),1)
        self.assertEqual(self.bot.handlers[0][1]['content_types'],['new_chat_members'])

if __name__=='__main__':unittest.main()
