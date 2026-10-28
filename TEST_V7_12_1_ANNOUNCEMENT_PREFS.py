"""Offline tests for command removal and announcements on/off.
No external Telegram or Supabase connection.
"""
from __future__ import annotations
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import broadcast_v710 as feature

class Response:
    def __init__(self,data): self.data=data
class Query:
    def __init__(self,table): self.table=table;self.filters={};self.payload=None
    def select(self,*args): return self
    def eq(self,k,v):self.filters[k]=v;return self
    def limit(self,*args):return self
    def upsert(self,payload,**kwargs):self.payload=payload;return self
    def execute(self):
        if self.payload is not None:
            self.table[int(self.payload['user_id'])]=dict(self.payload)
            return Response([self.payload])
        return Response([dict(row) for row in self.table.values()
                         if all(row.get(k)==v for k,v in self.filters.items())])
class DB:
    def __init__(self):self.rows={}
    def table(self,name):
        if name!=feature.TABLE:raise ValueError('No table: '+name)
        return Query(self.rows)
class Bot:
    def __init__(self):self.sent=[];self.registered=[]
    def send_message(self,uid,text,**kwargs): self.sent.append(text)
    def message_handler(self,**kwargs):
        def add(fn):self.registered.append((kwargs,fn));return fn
        return add
class PreferenceTests(unittest.TestCase):
    def setUp(self):
        self.bot=Bot();self.db=DB();self.service=feature.AnnouncementService(self.bot,self.db)
        self.msg=lambda text:SimpleNamespace(text=text,from_user=SimpleNamespace(id=200),chat=SimpleNamespace(id=200,type='private'))
    def test_no_legacy_command_registration(self):
        feature.register_broadcast_handlers(self.bot,self.db)
        names={n for x,_ in self.bot.registered for n in x.get('commands',[])}
        self.assertNotIn('unsubscribe',names)
        self.assertIn('announcements',names)
        self.assertIn('broadcast',names)
    def test_turn_off_without_legacy_command(self):
        self.service.announcements(self.msg('/announcements off'))
        self.assertFalse(self.db.rows[200]['subscribed'])
        self.assertIn('disabled',self.bot.sent[-1].lower())
    def test_turn_on_again(self):
        self.service.announcements(self.msg('/announcements off'))
        self.service.announcements(self.msg('/announcements on'))
        self.assertTrue(self.db.rows[200]['subscribed'])
    def test_status_after_optout(self):
        self.service.announcements(self.msg('/announcements off'))
        self.service.announcements(self.msg('/announcements'))
        self.assertIn('OFF',self.bot.sent[-1])
    def test_unknown_parameter_not_saved(self):
        self.service.announcements(self.msg('/announcements unknown'))
        self.assertFalse(self.db.rows)
    def test_legacy_false_preference_preserved(self):
        self.db.rows[200]={'user_id':200,'chat_id':200,'subscribed':False}
        self.service.announcements(self.msg('/announcements'))
        self.assertFalse(self.db.rows[200]['subscribed'])
    def test_user_guidance_no_unsubscribe(self):
        self.service.subscription(self.msg('/subscribe'),True)
        self.assertNotIn('/unsubscribe',self.bot.sent[-1])
    def test_known_broadcast_footer_if_supported(self):
        if not hasattr(self.service,'_make_all_preview'):
            self.skipTest('V7.12 known-users not installed')
        import inspect
        source=inspect.getsource(feature.AnnouncementService._make_all_preview)
        self.assertIn('/announcements off',source)
        self.assertNotIn('"/unsubscribe"',source)

if __name__=='__main__':unittest.main()
