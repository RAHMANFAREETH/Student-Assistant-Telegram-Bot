"""V11.8.8 smart bulk: isolated offline tests; no Telegram or Supabase calls."""
from __future__ import annotations
import os
import types
import unittest
import uuid
from unittest.mock import Mock, patch

import library_smart_bulk_v1188 as smart
import library_media_v117_bot as api


class Bot:
    def __init__(self, *, supports_edit=True):
        self.sent=[];self.edited=[];self.copied=[];self.deleted=[];self.next_id=50
        self.messages=[];self.callbacks=[]
        self.supports_edit=supports_edit
    def send_message(self, chat_id, text, **kwargs):
        self.next_id+=1; self.sent.append((chat_id,text,kwargs))
        return types.SimpleNamespace(message_id=self.next_id)
    def edit_message_text(self, text, **kwargs):
        if not self.supports_edit:raise RuntimeError('edit unavailable')
        self.edited.append((text,kwargs));return True
    def copy_message(self,chat_id,from_chat_id,message_id,**kw):
        self.copied.append((chat_id,from_chat_id,message_id));return types.SimpleNamespace(message_id=900)
    def delete_message(self,chat_id,message_id):
        self.deleted.append((chat_id,message_id));return True
    def answer_callback_query(self,*args,**kwargs):return True
    def message_handler(self,**options):
        def deco(func):self.messages.append((options,func));return func
        return deco
    def callback_query_handler(self,**options):
        def deco(func):self.callbacks.append((options,func));return func
        return deco


def msg(text='',*,user=123,caption=None,filename='Tamil_Book_01.pdf',size=4*1024**3,kind='private'):
    file=types.SimpleNamespace(file_name=filename,file_size=size,file_id='F'+str(uuid.uuid4()),
                               file_unique_id='U'+str(uuid.uuid4()))
    return types.SimpleNamespace(from_user=types.SimpleNamespace(id=user),
                                 chat=types.SimpleNamespace(id=user,type=kind),
                                 text=text,caption=caption,document=file,
                                 message_id=987,photo=None,audio=None,video=None)


class SmartBulkTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'LIBRARY_SMART_BULK_V1188_ENABLED':'true',
                                        'LIBRARY_MEDIA_V117_ENABLED':'true',
                                        'BOOK_LIBRARY_ENABLED':'true'})
        self.env.start();self.addCleanup(self.env.stop)
        smart._SESSIONS.clear(); api._STATES.clear()
        self.bot=Bot()
        self.admin=msg('/mediabulk')
        smart.begin(self.bot,self.admin)
        self.settings=msg('/mediabulkset Tamil | Education | permission | Unknown | Rights confirmed')
    def tearDown(self):
        smart._SESSIONS.clear();api._STATES.clear()
    def configure(self):
        smart.configure(self.bot,self.settings)
        self.assertIsNotNone(smart._session(123).config)
    def test_opt_in_flag(self):
        self.assertTrue(smart.enabled())
        with patch.dict(os.environ,{'LIBRARY_SMART_BULK_V1188_ENABLED':'false'}):
            self.assertFalse(smart.enabled())
    def test_start_instructions(self):
        self.assertIn('multiple files',self.bot.sent[0][1]);self.assertIn('/mediabulkset',self.bot.sent[0][1])
        self.assertEqual(smart._session(123).attempted,0)
    def test_requires_shared_rights(self):
        smart.configure(self.bot,msg('/mediabulkset Tamil | Education | other'))
        self.assertIsNone(smart._session(123).config)
        self.assertIn('Rights must be',self.bot.sent[-1][1])
    def test_malformed_config_does_not_change_session(self):
        smart.configure(self.bot,msg('/mediabulkset Tamil'))
        self.assertIsNone(smart._session(123).config)
    def test_language_and_category_saved(self):
        self.configure()
        self.assertEqual(smart._session(123).config['language'],'Tamil')
        self.assertEqual(smart._session(123).config['rights'],'permission')
    def test_no_config_uses_legacy(self):
        self.assertFalse(smart.accept_file(self.bot,msg(),api=api))
    def test_filename_metadata_and_large_file(self):
        self.configure()
        with patch.object(api,'submit_media',return_value={'id':str(uuid.uuid4())}) as f:
            self.assertTrue(smart.accept_file(self.bot,msg(filename='தமிழ்_இலக்கணம்.pdf',size=4*1024**3),api=api))
        new=f.call_args.args[1]
        self.assertIn('தமிழ் இலக்கணம் | Unknown | Tamil | Education | permission | Rights confirmed',new.caption)
        self.assertEqual(new.document.file_size,4*1024**3)
        self.assertEqual(smart._session(123).approved,1)
    def test_real_catalog_path_copies_4gb_without_downloading(self):
        self.configure()
        large=msg(filename='Large_Tamil_Reference.pdf',size=4*1024**3)
        with patch.dict(os.environ, {'BOOK_LIBRARY_CHANNEL_ID':'-100987',
                                     'LIBRARY_MEDIA_MAX_BYTES':'0','LIBRARY_MEDIA_OCR_ENABLED':'false'}),\
             patch('library_media_v117_store.duplicates',return_value=None),\
             patch('library_media_v117_store.same_filename',return_value=[]),\
             patch('library_media_v117_store.create',return_value={'id':str(uuid.uuid4()),'title':'Large Tamil Reference'}) as create,\
             patch('library_media_v117_store.audit'):
            self.assertTrue(smart.accept_file(self.bot,large,api=api))
        self.assertEqual(self.bot.copied,[(-100987,123,987)])
        payload=create.call_args.args[0]
        self.assertEqual(payload['file_size'],4*1024**3)
        self.assertEqual(payload['language'],'Tamil')
        self.assertEqual(payload['status'],'approved')

    def test_does_not_mutate_incoming_message(self):
        self.configure();m=msg(caption='My own custom title')
        with patch.object(api,'submit_media'):
            smart.accept_file(self.bot,m,api=api)
        self.assertEqual(m.caption,'My own custom title')
    def test_short_caption_title_override(self):
        self.configure()
        with patch.object(api,'submit_media') as f:
            smart.accept_file(self.bot,msg(caption='Arabic History Book'),api=api)
        self.assertTrue(f.call_args.args[1].caption.startswith('Arabic History Book |'))
    def test_explicit_caption_override(self):
        self.configure();cap='Custom | Writer | Sinhala | History | cc_by | Permission verified'
        with patch.object(api,'submit_media') as f:
            smart.accept_file(self.bot,msg(caption=cap),api=api)
        self.assertEqual(f.call_args.args[1].caption,cap)
    def test_bad_explicit_caption_does_not_publish(self):
        self.configure()
        with patch.object(api,'submit_media') as f:
            smart.accept_file(self.bot,msg(caption='Wrong | Format'),api=api)
        f.assert_not_called();self.assertEqual(smart._session(123).failed,1)
    def test_duplicate_is_skipped_and_counted(self):
        self.configure()
        with patch.object(api,'submit_media',side_effect=ValueError('Duplicate file already exists: Tamil Book')):
            smart.accept_file(self.bot,msg(),api=api)
        s=smart._session(123)
        self.assertEqual((s.attempted,s.duplicates,s.failed,s.approved),(1,1,0,0))
    def test_db_failure_is_counted_not_exposed(self):
        self.configure()
        with patch.object(api,'submit_media',side_effect=RuntimeError('private database credential')):
            smart.accept_file(self.bot,msg(),api=api)
        s=smart._session(123)
        self.assertEqual(s.failed,1)
        self.assertNotIn('private database credential',smart._report(s))
    def test_zip_delegated_to_legacy_with_limits(self):
        self.configure()
        with patch.object(api,'submit_media') as f:
            self.assertFalse(smart.accept_file(self.bot,msg(filename='archive.zip'),api=api))
        f.assert_not_called()
    def test_status_summary(self):
        self.configure()
        with patch.object(api,'submit_media'):
            smart.accept_file(self.bot,msg(),api=api)
        smart.status(self.bot,self.admin)
        self.assertIn('Published: 1',self.bot.sent[-1][1])
    def test_finish_cancels_core_state_and_removes_config(self):
        self.configure();api._state_set(123,'bulk',seconds=120,remaining=100)
        smart.finish(self.bot,self.admin,api=api)
        self.assertIsNone(api._state_get(123));self.assertIsNone(smart._session(123))
        self.assertIn('UPLOAD FINISHED',self.bot.sent[-1][1])
    def test_cancel_prevents_metadata_reuse(self):
        self.configure();smart.cancel(123)
        self.assertFalse(smart.accept_file(self.bot,msg(),api=api))
    def test_full_session_closed_at_limit(self):
        self.configure();api._state_set(123,'bulk',seconds=120,remaining=100)
        smart._session(123).attempted=99
        with patch.object(api,'submit_media'):
            smart.accept_file(self.bot,msg(),api=api)
        self.assertIsNone(smart._session(123));self.assertIsNone(api._state_get(123))
        self.assertIn('UPLOAD FINISHED',self.bot.sent[-1][1])
    def test_independent_admin_sessions(self):
        smart.begin(self.bot,msg('/mediabulk',user=456))
        self.configure()
        self.assertIsNone(smart._session(456).config)
    def test_expired_session_not_reused(self):
        self.configure()
        smart._session(123).expires_at=0
        self.assertIsNone(smart._session(123))
    def test_progress_updates_without_spam(self):
        self.configure()
        with patch.object(api,'submit_media'):
            for j in range(12):smart.accept_file(self.bot,msg(filename=f'Unique_{j}.pdf'),api=api)
        self.assertEqual(smart._session(123).approved,12)
        self.assertEqual(len(self.bot.edited),12)
    def test_status_with_no_session(self):
        smart.cancel(123); smart.status(self.bot,self.admin)
        self.assertIn('No active',self.bot.sent[-1][1])


class WiringTests(unittest.TestCase):
    def setUp(self):
        smart._SESSIONS.clear();api._STATES.clear()
        self.env=patch.dict(os.environ,{'LIBRARY_SMART_BULK_V1188_ENABLED':'true'})
        self.env.start();self.addCleanup(self.env.stop)
        self.bot=Bot()
        import sys
        self.sysmods=patch.dict(sys.modules,{'telebot.handler_backends':types.SimpleNamespace(ContinueHandling=type('End',(),{}))})
        self.sysmods.start();self.addCleanup(self.sysmods.stop)
        self.handlers=patch('library_manage_v118.register_manage_handlers'),patch('library_search_ui_v1183.register_private_handlers')
        for p in self.handlers:p.start();self.addCleanup(p.stop)
        api.register_v117_handlers(self.bot)
    def find(self,command):
        return next(fn for kw,fn in self.bot.messages if command in kw.get('commands',[]))
    def test_start_command_registers_guided_bulk(self):
        m=msg('/mediabulk')
        with patch.object(api,'enabled',return_value=True),patch.object(api,'admin',return_value=True):
            self.find('mediabulk')(m)
        self.assertEqual(api._state_get(123)[0],'bulk')
        self.assertEqual(api._state_get(123)[2],100)
        self.assertIsNotNone(smart._session(123))
    def test_admin_restriction_still_applies(self):
        with patch.object(api,'enabled',return_value=True),patch.object(api,'admin',return_value=False):
            self.find('mediabulk')(msg('/mediabulk'))
        self.assertIsNone(smart._session(123))
    def test_buttons_reuse_admin_callback_auth(self):
        self.assertTrue(any('callback_query_handler' not in kw for kw,_ in self.bot.messages))
    def test_admin_panel_bulk_button_starts_guided_session(self):
        callback=types.SimpleNamespace(
            id='cb', data='v117:adm:bulk',
            from_user=types.SimpleNamespace(id=123),
            message=types.SimpleNamespace(chat=types.SimpleNamespace(id=123,type='private')))
        handler=next(fn for kw,fn in self.bot.callbacks if kw.get('func'))
        with patch.object(api,'enabled',return_value=True),\
             patch('book_library_bot._admin',return_value=True):
            handler(callback)
        self.assertEqual(api._state_get(123)[2],100)
        self.assertIsNotNone(smart._session(123))

    def test_file_handler_with_shared_metadata(self):
        m=msg('/mediabulk')
        with patch.object(api,'enabled',return_value=True),patch.object(api,'admin',return_value=True):
            self.find('mediabulk')(m)
            self.find('mediabulkset')(msg('/mediabulkset Tamil | General | permission'))
            file_fn=next(fn for kw,fn in self.bot.messages if kw.get('content_types')==['document','photo','audio','video'])
            with patch.object(api,'submit_media',return_value={'id':'X'}):
                file_fn(msg(filename='Some_Arabic_Book.pdf'))
        self.assertEqual(smart._session(123).approved,1)
    def test_mediacancel_resets_both_states(self):
        with patch.object(api,'enabled',return_value=True),patch.object(api,'admin',return_value=True):
            self.find('mediabulk')(msg('/mediabulk'))
            self.find('mediacancel')(msg('/mediacancel'))
        self.assertIsNone(smart._session(123));self.assertIsNone(api._state_get(123))

if __name__=='__main__':unittest.main()
