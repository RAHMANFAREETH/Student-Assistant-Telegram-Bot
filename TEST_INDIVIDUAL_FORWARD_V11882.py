"""Focused offline tests; no network, Supabase or Telegram credentials needed."""
from __future__ import annotations
import os
import tempfile
import types
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch, Mock

import library_individual_forward_v11882 as fw
import library_media_v117_bot as api

class Bot:
    def __init__(self):self.sent=[];self.copies=[]
    def send_message(self,chat,text,**kwargs):
        self.sent.append((chat,text));return types.SimpleNamespace(message_id=len(self.sent))
    def copy_message(self,cid,src,mid,**kwargs):
        self.copies.append((cid,src,mid));return types.SimpleNamespace(message_id=900)
    def send_photo(self,*a,**kw):raise RuntimeError('no preview')

def msg(text='', *, user=123,filename='صحيح_البخاري.pdf',size=4*1024**3,kind='private'):
    doc=types.SimpleNamespace(file_name=filename,file_size=size,file_unique_id='testUnique123',file_id='telegramFile')
    return types.SimpleNamespace(from_user=types.SimpleNamespace(id=user),chat=types.SimpleNamespace(id=user,type=kind),text=text,caption='CHANNEL CAPTION MISLEADING',document=doc,message_id=700,photo=None,video=None,audio=None)

COMMAND='/mediaforwardset Sahih al-Bukhari | Imam Muhammad al-Bukhari | English | Hadith / Islamic Studies | permission | Rights confirmed'

class Tests(unittest.TestCase):
    def setUp(self):
        fw._SESSIONS.clear();api._STATES.clear();self.bot=Bot()
        self.flags=patch.dict(os.environ,{'LIBRARY_INDIVIDUAL_FORWARD_V11882_ENABLED':'true','LIBRARY_MEDIA_MAX_BYTES':'0','BOOK_LIBRARY_CHANNEL_ID':'-100987','LIBRARY_MEDIA_OCR_ENABLED':'false'})
        self.flags.start();self.addCleanup(self.flags.stop)
    def tearDown(self):fw._SESSIONS.clear();api._STATES.clear()
    def init(self):
        fw.start(self.bot,msg('/mediaforward'),api=api)
        fw.configure(self.bot,msg(COMMAND))
    def test_disabled_by_default(self):
        self.assertTrue(fw.enabled())
        with patch.dict(os.environ,{'LIBRARY_INDIVIDUAL_FORWARD_V11882_ENABLED':'false'}):self.assertFalse(fw.enabled())
    def test_correct_details_saved(self):
        self.init();self.assertEqual(fw._get(123)['meta'][1]['title'],'Sahih al-Bukhari')
    def test_requires_rights(self):
        self.init();fw.configure(self.bot,msg('/mediaforwardset Sahih al-Bukhari | Someone | English | Hadith | unknown | rights explanation'))
        self.assertEqual(fw._get(123)['meta'][1]['title'],'Sahih al-Bukhari')
        self.assertIn('Rights must',self.bot.sent[-1][1])
    def test_no_publish_before_confirmation(self):
        self.init();fw.receive(self.bot,msg(),api=api)
        self.assertIn('No file has been published yet',self.bot.sent[-1][1])
    def test_full_publication_path_large_file(self):
        self.init();fw.receive(self.bot,msg(),api=api)
        with patch('library_media_v117_store.duplicates',return_value=None),\
             patch('library_media_v117_store.same_filename',return_value=[]),\
             patch('library_media_v117_store.create',return_value={'id':str(uuid.uuid4()),'title':'Sahih al-Bukhari'}) as create,\
             patch('library_media_v117_store.audit'):
            fw.publish(self.bot,msg('/mediaforwardpublish'),api=api)
        self.assertEqual(self.bot.copies,[(-100987,123,700)])
        self.assertEqual(create.call_args.args[0]['file_size'],4*1024**3)
        self.assertEqual(create.call_args.args[0]['title'],'Sahih al-Bukhari')
        self.assertEqual(create.call_args.args[0]['author'],'Imam Muhammad al-Bukhari')
        self.assertEqual(create.call_args.args[0]['language'],'English')
        self.assertEqual(create.call_args.args[0]['category'],'Hadith / Islamic Studies')
        self.assertIsNone(fw._get(123))
    def test_no_metadata(self):
        fw.start(self.bot,msg('/mediaforward'),api=api)
        fw.receive(self.bot,msg(),api=api)
        self.assertIn('Set book details first',self.bot.sent[-1][1])
    def test_reject_unsupported_zip(self):
        self.init();fw.receive(self.bot,msg(filename='file.zip'),api=api)
        self.assertIn('Only PDF',self.bot.sent[-1][1])
    def test_one_file_per_session(self):
        self.init();fw.receive(self.bot,msg(),api=api);fw.receive(self.bot,msg(filename='other.pdf'),api=api)
        self.assertIn('awaiting review',self.bot.sent[-1][1])
    def test_publish_without_file(self):
        self.init();fw.publish(self.bot,msg('/mediaforwardpublish'),api=api)
        self.assertIn('No reviewed document',self.bot.sent[-1][1])
    def test_cancellation(self):
        self.init();fw.receive(self.bot,msg(),api=api);fw.cancel(123);self.assertIsNone(fw._get(123))
    def test_session_expiration(self):
        self.init();fw._get(123)['expires']=0;self.assertIsNone(fw._get(123))
    def test_reject_malformed_metadata(self):
        self.init();fw.configure(self.bot,msg('/mediaforwardset Sahih al-Bukhari'))
        self.assertIn('Metadata not saved',self.bot.sent[-1][1])
    def test_non_matching_user(self):
        self.init();fw.receive(self.bot,msg(user=999),api=api)
        self.assertIn('Session expired',self.bot.sent[-1][1])
    def test_retry_if_save_fails(self):
        self.init();fw.receive(self.bot,msg(),api=api)
        with patch.object(api,'submit_media',side_effect=RuntimeError('transient')):
            with self.assertRaises(RuntimeError):fw.publish(self.bot,msg('/mediaforwardpublish'),api=api)
        self.assertIsNotNone(fw._get(123)['file'])
    def test_no_accidental_forward_caption(self):
        self.init();fw.receive(self.bot,msg(),api=api)
        with patch.object(api,'submit_media',return_value={'title':'Sahih al-Bukhari','id':'42'}) as fn:
            fw.publish(self.bot,msg('/mediaforwardpublish'),api=api)
        self.assertNotIn('CHANNEL CAPTION MISLEADING',fn.call_args.args[1].caption)
    def test_installer_idempotence(self):
        import INSTALL_INDIVIDUAL_FORWARD_V11882 as inst
        new,error=inst.plan()
        self.assertIsNone(error)
        self.assertIsNotNone(new)
        self.assertIn('individual_forward_commands_v11882',new)

if __name__=='__main__':unittest.main()
