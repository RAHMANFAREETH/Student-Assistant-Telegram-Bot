import os
import sys
import unittest
from types import SimpleNamespace, ModuleType
from unittest.mock import patch

# Can run these focused tests in an isolated offline environment too.
try:
    from telebot.handler_backends import ContinueHandling
except ImportError:
    fake_telebot=ModuleType('telebot')
    fake_backend=ModuleType('telebot.handler_backends')
    class ContinueHandling:pass
    fake_backend.ContinueHandling=ContinueHandling
    fake_telebot.handler_backends=fake_backend
    sys.modules['telebot']=fake_telebot
    sys.modules['telebot.handler_backends']=fake_backend

import group_admin_helper_v1191 as g

class FakeBot:
    def __init__(self):
        self.handlers=[];self.sent=[];self.deleted=[];self.member='member'
    def message_handler(self,**kw):
        def dec(f):self.handlers.append((kw,f));return f
        return dec
    def send_message(self,cid,text,**kwargs):
        self.sent.append((cid,text))
        return SimpleNamespace(message_id=len(self.sent))
    def delete_message(self,cid,mid):self.deleted.append((cid,mid))
    def get_chat_member(self,cid,uid):return SimpleNamespace(status=self.member)
    def handler(self,cmd):
        for kw,f in self.handlers:
            if cmd in kw.get('commands',[]):return f
        raise AssertionError(cmd)

def msg(text='/adminhub',private=True,uid=123,cid=123):
    return SimpleNamespace(text=text,caption=None,chat=SimpleNamespace(id=cid,type='private' if private else 'supergroup'),
         from_user=SimpleNamespace(id=uid,is_bot=False),message_id=23)

class HelperTests(unittest.TestCase):
    def setUp(self):
        self.bot=FakeBot();self.enabled=patch.dict(os.environ,{
           'GROUP_HELPER_V1191_ENABLED':'true','GROUP_HELPER_ADMIN_CHAT_ID':'0',
           'GROUP_HELPER_MODERATION_ENABLED':'false','GROUP_HELPER_DELETE_ENABLED':'false',
           'GROUP_HELPER_LINK_WARNINGS_ENABLED':'false','GROUP_HELPER_FLOOD_THRESHOLD':'4'})
        self.enabled.start();g.install(self.bot)
    def tearDown(self):self.enabled.stop()
    def test_disabled_no_alert(self):
        with patch.dict(os.environ,{'GROUP_HELPER_V1191_ENABLED':'false','GROUP_HELPER_ADMIN_CHAT_ID':'-100123'}):
            self.assertFalse(g.queue_alert('test'))
    def test_feedback_payload(self):
        with patch.object(g,'queue_alert',return_value=True) as call:
            self.assertTrue(g.publish_feedback_event([{'user_id':1,'message':'Excellent book!','kind':'suggestion'}]))
        self.assertIn('Excellent book!',call.call_args[0][0])
    def test_request_payload(self):
        with patch.object(g,'queue_alert',return_value=True) as call:
            self.assertTrue(g.publish_book_request({'title':'Sahih Bukhari','author':'Test Author'}))
        self.assertIn('Sahih Bukhari',call.call_args[0][0])
    def test_admin_private(self):
        with patch.object(g,'_admin',return_value=True):
            self.bot.handler('adminhub')(msg())
        self.assertIn('/feedbackqueue',self.bot.sent[-1][1])
    def test_nonadmin(self):
        with patch.object(g,'_admin',return_value=False):
            self.bot.handler('adminhub')(msg())
        self.assertIn('administrator',self.bot.sent[-1][1].lower())
    def test_admin_group_rejected(self):
        from telebot.handler_backends import ContinueHandling
        with patch.object(g,'_admin',return_value=True):
            result=self.bot.handler('adminhub')(msg(private=False,cid=-10022))
        self.assertIsInstance(result,ContinueHandling)
    def test_admin_requests(self):
        stub=ModuleType('book_library_v113_store')
        stub.pending_requests=lambda: [{'title':'Test Book','author':'Author'}]
        with patch.object(g,'_admin',return_value=True),patch.dict(sys.modules,{'book_library_v113_store':stub}):
            self.bot.handler('adminrequests')(msg(text='/adminrequests'))
        self.assertIn('Test Book',self.bot.sent[-1][1])
    def test_adminhubid_in_private_admin_group(self):
        with patch.object(g,'_admin',return_value=True):
            self.bot.handler('adminhubid')(msg(text='/adminhubid',private=False,cid=-10044))
        self.assertIn('-10044',self.bot.sent[-1][1])
    def test_testalert_without_channel(self):
        with patch.object(g,'_admin',return_value=True):
            self.bot.handler('admintestalert')(msg(text='/admintestalert'))
        self.assertIn('GROUP_HELPER_ADMIN_CHAT_ID',self.bot.sent[-1][1])
    def test_help_only_group(self):
        with patch.object(g,'_group_allowed',return_value=True):
            self.bot.handler('groupguide')(msg(text='/groupguide',private=False,cid=-1009))
        self.assertIn('/book Quran',self.bot.sent[-1][1])
    def test_report_requires_adult(self):
        with patch.object(g,'_adult',return_value=False):
            self.bot.handler('reportproblem')(msg(text='/reportproblem bad book metadata'))
        self.assertIn('Adult',self.bot.sent[-1][1])
    def test_report_goes_to_existing_feedback(self):
        stub=ModuleType('friendly_v119')
        feedback=__import__('unittest').mock.Mock()
        stub.feedback=feedback
        with patch.object(g,'_adult',return_value=True),patch.dict(sys.modules,{'friendly_v119':stub}):
            self.bot.handler('reportproblem')(msg(text='/reportproblem book description wrong'))
        feedback.assert_called_once()
        self.assertIn('Report saved',self.bot.sent[-1][1])
    def test_group_no_moderation_default(self):
        from telebot.handler_backends import ContinueHandling
        fn=next(f for kw,f in self.bot.handlers if kw.get('func') is g._group)
        with patch.object(g,'_group_allowed',return_value=True):
            response=fn(msg(text='Quran',private=False,cid=-1009))
        self.assertIsInstance(response,ContinueHandling)
        self.assertEqual(self.bot.deleted,[])
    def test_flood_one_user_does_not_block_another(self):
        from telebot.handler_backends import ContinueHandling
        fn=next(f for kw,f in self.bot.handlers if kw.get('func') is g._group)
        g._FLOOD.clear()
        with patch.dict(os.environ,{'GROUP_HELPER_MODERATION_ENABLED':'true'}),patch.object(g,'_group_allowed',return_value=True),patch.object(g,'_admin',return_value=False):
            for i in range(4):
                self.assertIsInstance(fn(msg(text='Quran',private=False,uid=99,cid=-1009)),ContinueHandling)
            fn(msg(text='Quran',private=False,uid=99,cid=-1009))
            self.assertIsInstance(fn(msg(text='Quran',private=False,uid=100,cid=-1009)),ContinueHandling)
        self.assertEqual(self.bot.deleted,[])
    def test_group_admin_skip(self):
        from telebot.handler_backends import ContinueHandling
        fn=next(f for kw,f in self.bot.handlers if kw.get('func') is g._group)
        self.bot.member='administrator';g._FLOOD.clear()
        with patch.dict(os.environ,{'GROUP_HELPER_MODERATION_ENABLED':'true','GROUP_HELPER_DELETE_ENABLED':'true'}),patch.object(g,'_group_allowed',return_value=True),patch.object(g,'_admin',return_value=False):
            for i in range(8):response=fn(msg(text='Quran',private=False,uid=222,cid=-1009))
        self.assertIsInstance(response,ContinueHandling)
        self.assertEqual(self.bot.deleted,[])
    def test_metrics(self):
        with g._LOCK:
            g._STATS.update({'active':0,'peak':0,'requests':0,'errors':0,'last_ms':0})
            g._TIMES.clear()
        t1=g.metrics_start();t2=g.metrics_start()
        g.metrics_finish(t1,200);g.metrics_finish(t2,503)
        self.assertIn('Peak concurrent: 2',g.load_summary())
        self.assertIn('HTTP errors: 1',g.load_summary())
    def test_bad_flag(self):
        self.assertTrue(g.enabled())
        with patch.dict(os.environ,{'GROUP_HELPER_V1191_ENABLED':'false'}):self.assertFalse(g.enabled())
    def test_install_idempotent(self):
        size=len(self.bot.handlers)
        g.install(self.bot)
        self.assertEqual(size,len(self.bot.handlers))
    def test_latency_sample_bounded(self):
        for i in range(300):g.metrics_finish(g.metrics_start(),200)
        self.assertLessEqual(len(g._TIMES),256)
    def test_restrict_group_link_warning(self):
        with patch.dict(os.environ,{'GROUP_HELPER_LINK_WARNINGS_ENABLED':'true'}):
            self.assertFalse(g._link_check(msg(text='https://t.me/library_for_all')))
            self.assertTrue(g._link_check(msg(text='https://scam.example/malware')))
    def test_admin_alerts(self):
        with patch.object(g,'_admin',return_value=True):
            self.bot.handler('adminalerts')(msg(text='/adminalerts'))
        self.assertTrue(self.bot.sent)

if __name__=='__main__':unittest.main()
