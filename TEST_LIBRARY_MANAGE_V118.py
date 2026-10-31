"""V11.8 offline safety and integration tests (never touch real files or Telegram)."""
import copy
import os
import sys
import tempfile
import types
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import library_manage_v118 as m
from INSTALL_LIBRARY_MANAGE_V118 import transform, integrate

BOOK_ID = '11111111-2222-4333-8444-555555555555'
MEDIA_ID = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'

class Resp:
    def __init__(self, data): self.data = data

class Query:
    def __init__(self, db, name):
        self.db=db; self.name=name; self.filters=[]; self.action=None; self.values=None
        self.limit_number=None; self.order_key=None; self.desc=False
    def select(self, *a):return self
    def eq(self, key, value):self.filters.append(lambda x,k=key,v=value:x.get(k)==v);return self
    def in_(self, key, values):self.filters.append(lambda x,k=key,v=values:x.get(k) in v);return self
    def ilike(self,key,value):
        val=value.strip('%').casefold()
        self.filters.append(lambda x,k=key,v=val:v in str(x.get(k,'')).casefold())
        return self
    def order(self,key,desc=False):self.order_key=key;self.desc=desc;return self
    def limit(self,n):self.limit_number=n;return self
    def update(self,values):self.action='update';self.values=values;return self
    def delete(self):self.action='delete';return self
    def execute(self):
        matched=[r for r in self.db.data[self.name] if all(f(r) for f in self.filters)]
        if self.order_key:matched.sort(key=lambda x:str(x.get(self.order_key) or ''),reverse=self.desc)
        if self.limit_number is not None:matched=matched[:self.limit_number]
        if self.action=='update':
            for r in matched:r.update(self.values)
        if self.action=='delete':
            self.db.data[self.name]=[r for r in self.db.data[self.name] if r not in matched]
        return Resp(copy.deepcopy(matched))

class DB:
    def __init__(self):
        self.data={
            'book_library_items':[dict(id=BOOK_ID,title='Arabic Grammar PDF',author='Teacher',language='Arabic',
                                       channel_id=-1001,message_id=105,file_name='arabic.pdf',active=True,
                                       added_at='2026-01-01')],
            'library_media_v117':[dict(id=MEDIA_ID,title='Tamil Diagram PNG',author='Teacher',language='Tamil',
                                       status='approved',storage_channel_id=-1001,storage_message_id=106,
                                       media_kind='image',file_name='diagram.png',created_at='2026-01-02')]
        }
    def table(self, name):return Query(self,name)

class Bot:
    def __init__(self):
        self.sent=[];self.deleted=[];self.copied=[];self.answered=[]
        self.handlers=[];self.callbacks=[];self.delete_result=True
    def send_message(self,cid,text,**kw):self.sent.append((cid,text,kw));return True
    def delete_message(self,cid,mid):
        self.deleted.append((cid,mid))
        if isinstance(self.delete_result,Exception):raise self.delete_result
        return self.delete_result
    def copy_message(self,*args,**kw):self.copied.append((args,kw));return True
    def answer_callback_query(self,*a,**kw):self.answered.append((a,kw))
    def message_handler(self,**kw):
        def inner(f):self.handlers.append((kw,f));return f
        return inner
    def callback_query_handler(self,**kw):
        def inner(f):self.callbacks.append((kw,f));return f
        return inner

class Markup:
    def __init__(self,**kw):self.inline_keyboard=[]
    def add(self,*items):self.inline_keyboard.append(items)
class Button:
    def __init__(self,text,callback_data):self.text=text;self.callback_data=callback_data
class ContinueHandling:pass

def message(text='',uid=42,chat_type='private',cid=None):
    return types.SimpleNamespace(text=text,chat=types.SimpleNamespace(id=(uid if cid is None else cid),type=chat_type),
                                 from_user=types.SimpleNamespace(id=uid))

def callback(data,uid=42,chat_type='private',cid=None):
    msg=message('',uid,chat_type,cid)
    return types.SimpleNamespace(data=data,from_user=msg.from_user,message=msg,id='CALLBACK')

class Tests(unittest.TestCase):
    def setUp(self):
        self.db=DB();self.bot=Bot()
        self.dbpatch=patch.object(m._store(),'_db',return_value=self.db);self.dbpatch.start()
        self.auditpatch=patch.object(m,'_audit');self.audit=self.auditpatch.start()
        self.env=patch.dict(os.environ,{'LIBRARY_MANAGE_V118_ENABLED':'true'});self.env.start()
        self.auth=patch('book_library_bot._admin',side_effect=lambda x:x==42);self.auth.start()
        self.modules=patch.dict(sys.modules,{'telebot':types.SimpleNamespace(types=types.SimpleNamespace(
                    InlineKeyboardMarkup=Markup,InlineKeyboardButton=Button)),
                    'telebot.handler_backends':types.SimpleNamespace(ContinueHandling=ContinueHandling)})
        self.modules.start()
        m._CONFIRM.clear()
    def tearDown(self):
        self.modules.stop();self.auth.stop();self.env.stop();self.auditpatch.stop();self.dbpatch.stop()
    def test_search_both_catalogs(self):
        self.assertEqual(len(m.find()),2)
        self.assertEqual(m.find('Arabic')[0][0],'b')
        self.assertEqual(m.find('Tamil')[0][0],'m')
    def test_uuid_search_beyond_recent(self):
        self.assertEqual(m.find('b:'+BOOK_ID)[0][1]['id'],BOOK_ID)
        self.assertEqual(m.find(MEDIA_ID)[0][0],'m')
    def test_invalid_wildcard_rejected(self):
        with self.assertRaises(ValueError):m.find('some%name')
    def test_book_hide_and_restore(self):
        self.assertIn('Hidden',m.change_visibility('b',BOOK_ID,False,42))
        self.assertFalse(self.db.data['book_library_items'][0]['active'])
        self.assertIn('Restored',m.change_visibility('b',BOOK_ID,True,42))
        self.assertTrue(self.db.data['book_library_items'][0]['active'])
    def test_media_hide_and_restore(self):
        m.change_visibility('m',MEDIA_ID,False,42)
        self.assertEqual(self.db.data['library_media_v117'][0]['status'],'hidden')
        m.change_visibility('m',MEDIA_ID,True,42)
        self.assertEqual(self.db.data['library_media_v117'][0]['status'],'approved')
    def test_hidden_items_remain_admin_visible(self):
        m.change_visibility('b',BOOK_ID,False,42)
        m.change_visibility('m',MEDIA_ID,False,42)
        self.assertEqual(len(m.find()),2)
    def test_rename_both(self):
        m.rename('b',BOOK_ID,'Updated Book Title',42)
        m.rename('m',MEDIA_ID,'Updated Image Title',42)
        self.assertEqual(self.db.data['book_library_items'][0]['title'],'Updated Book Title')
        self.assertEqual(self.db.data['library_media_v117'][0]['title'],'Updated Image Title')
        self.assertEqual(self.db.data['book_library_items'][0]['file_name'],'arabic.pdf')
    def test_invalid_rename_rejected(self):
        with self.assertRaises(ValueError):m.rename('b',BOOK_ID,'<bad>',42)
    def test_preview_private_copies_storage_file(self):
        m.register_manage_handlers(self.bot)
        handle=self.bot.callbacks[0][1]
        handle(callback('v118:v:m:'+uuid.UUID(MEDIA_ID).hex))
        self.assertEqual(self.bot.copied[0][0][1],-1001)
        self.assertEqual(self.bot.copied[0][0][2],106)
    def test_permanent_delete_success_pdf(self):
        result=m.delete(self.bot,'b',BOOK_ID,42)
        self.assertIn('Permanently',result)
        self.assertEqual(self.db.data['book_library_items'],[])
        self.assertEqual(self.bot.deleted,[(-1001,105)])
    def test_permanent_delete_success_image(self):
        m.delete(self.bot,'m',MEDIA_ID,42)
        self.assertEqual(self.db.data['library_media_v117'],[])
        self.assertEqual(self.bot.deleted,[(-1001,106)])
    def test_telegram_failure_keeps_catalog_hidden_pdf(self):
        self.bot.delete_result=RuntimeError('too old')
        with self.assertRaisesRegex(RuntimeError,'HIDDEN'):
            m.delete(self.bot,'b',BOOK_ID,42)
        self.assertFalse(self.db.data['book_library_items'][0]['active'])
    def test_telegram_failure_keeps_catalog_hidden_image(self):
        self.bot.delete_result=False
        with self.assertRaisesRegex(RuntimeError,'HIDDEN'):
            m.delete(self.bot,'m',MEDIA_ID,42)
        self.assertEqual(self.db.data['library_media_v117'][0]['status'],'hidden')
    def test_manual_purge_works_after_attestation(self):
        m.change_visibility('m',MEDIA_ID,False,42)
        m.delete(self.bot,'m',MEDIA_ID,42,manually_removed=True)
        self.assertEqual(self.db.data['library_media_v117'],[])
        self.assertEqual(self.bot.deleted,[])
    def test_duplicate_channel_message_prevents_delete(self):
        self.db.data['library_media_v117'][0].update(storage_message_id=105)
        with self.assertRaisesRegex(ValueError,'another library item'):
            m.delete(self.bot,'b',BOOK_ID,42)
        self.assertEqual(len(self.db.data['book_library_items']),1)
        self.assertEqual(self.bot.deleted,[])
    def test_delete_does_not_run_without_channel(self):
        self.db.data['book_library_items'][0]['channel_id']=None
        with self.assertRaisesRegex(ValueError,'reference missing'):
            m.delete(self.bot,'b',BOOK_ID,42)
    def test_confirmation_token_single_use(self):
        token=m._issue_token(42,'m',MEDIA_ID,'delete')
        self.assertEqual(m._take_token(42,token)[0],'m')
        with self.assertRaises(ValueError):m._take_token(42,token)
    def test_token_wrong_admin_rejected(self):
        token=m._issue_token(42,'b',BOOK_ID,'delete')
        with self.assertRaises(ValueError):m._take_token(44,token)
    def test_admin_search_button_registered(self):
        m.register_manage_handlers(self.bot)
        self.assertEqual(len(self.bot.handlers),1)
        self.assertEqual(len(self.bot.callbacks),1)
        self.bot.handlers[0][1](message('/librarymanage Arabic'))
        self.assertTrue(any('Manage Library' in x[1] for x in self.bot.sent))
    def test_non_admin_rejected_before_data_lookup(self):
        m.register_manage_handlers(self.bot)
        self.bot.handlers[0][1](message('/librarymanage Arabic',uid=55))
        self.assertIn('authorized admins',self.bot.sent[-1][1])
    def test_group_admin_rejected(self):
        m.register_manage_handlers(self.bot)
        self.bot.handlers[0][1](message('/librarymanage',uid=42,chat_type='supergroup',cid=-1009))
        self.assertIn('private chat',self.bot.sent[-1][1])
    def test_other_users_cannot_click_admin_button(self):
        m.register_manage_handlers(self.bot)
        self.bot.callbacks[0][1](callback('v118:i:b:'+uuid.UUID(BOOK_ID).hex,uid=55))
        self.assertEqual(self.bot.sent,[])
        self.assertTrue(self.bot.answered[0][1]['show_alert'])
    def test_group_click_rejected(self):
        m.register_manage_handlers(self.bot)
        self.bot.callbacks[0][1](callback('v118:i:b:'+uuid.UUID(BOOK_ID).hex,chat_type='supergroup',cid=-1009))
        self.assertEqual(self.bot.sent,[])
    def test_full_delete_requires_second_confirm(self):
        m.register_manage_handlers(self.bot)
        handler=self.bot.callbacks[0][1]
        handler(callback('v118:d:b:'+uuid.UUID(BOOK_ID).hex))
        self.assertEqual(self.bot.deleted,[])
        self.assertEqual(len(self.db.data['book_library_items']),1)
        confirm_markup=self.bot.sent[-1][2]['reply_markup']
        confirm_data=confirm_markup.inline_keyboard[0][0].callback_data
        self.assertLessEqual(len(confirm_data),64)
        handler(callback(confirm_data))
        self.assertEqual(len(self.db.data['book_library_items']),0)
    def test_command_rename_requires_admin(self):
        m.register_manage_handlers(self.bot)
        self.bot.handlers[0][1](message('/librarysettitle b:'+BOOK_ID+' | Renamed in bot',uid=55))
        self.assertEqual(self.db.data['book_library_items'][0]['title'],'Arabic Grammar PDF')
    def test_disabled_feature_guard(self):
        with patch.dict(os.environ,{'LIBRARY_MANAGE_V118_ENABLED':'false'}):
            self.assertFalse(m.enabled())

class InstallTests(unittest.TestCase):
    def test_v117_patch_has_three_separate_hooks(self):
        root=Path(__file__).parent
        v117=(root/'library_media_v117_bot.py').read_text(encoding='utf8')
        self.assertIn('Manage Library Files',transform(v117))
        self.assertIn('register_manage_handlers',transform(v117))
        self.assertEqual(transform(transform(v117)),transform(v117))
    def test_installer_never_modifies_main_or_database(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'library_media_v117_bot.py').write_text(
                (Path(__file__).parent/'library_media_v117_bot.py').read_text(encoding='utf8'))
            before=(root/'library_media_v117_bot.py').read_bytes()
            integrate(root,apply=False,output=lambda x:None)
            self.assertEqual(before,(root/'library_media_v117_bot.py').read_bytes())
            self.assertFalse((root/'main.py').exists())

if __name__ == '__main__':unittest.main()
