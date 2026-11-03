"""V11.7 offline tests — no real Telegram, Supabase, keys or API calls."""
from __future__ import annotations
import io
import os
import sys
import tempfile
import types
import unittest
import uuid
import zipfile
from pathlib import Path
from unittest.mock import patch,Mock

import library_media_v117_store as st
import library_media_v117_bot as api
import library_media_v117_processing as prep
from INSTALL_LIBRARY_MEDIA_V117 import transform,TARGETS,integrate

ROOT=Path(__file__).parent
UID=str(uuid.uuid4())

class Btn:
    def __init__(self,text,callback_data=None,url=None,**kwargs):
        self.text=text;self.callback_data=callback_data;self.url=url
class Markup:
    def __init__(self,*args,**kwargs):self.inline_keyboard=[]
    def add(self,*items):self.inline_keyboard.append(list(items))
class End:pass
class Bot:
    def __init__(self):
        self.sent=[];self.photos=[];self.copied=[];self.deleted=[];self.answered=[]
        self.handlers=[];self.callbacks=[];self.next_id=100
    def send_message(self,chat_id,text,**kw):
        self.sent.append((chat_id,text,kw));self.next_id+=1
        return types.SimpleNamespace(message_id=self.next_id)
    def send_photo(self,chat_id,photo,**kw):
        self.photos.append((chat_id,photo,kw));self.next_id+=1
        return types.SimpleNamespace(message_id=self.next_id,
                                     photo=[types.SimpleNamespace(file_id='PREVIEW123')])
    def copy_message(self,*args,**kwargs):
        if args:
            kwargs=dict(chat_id=args[0],from_chat_id=args[1],message_id=args[2])
        self.copied.append(kwargs);return types.SimpleNamespace(message_id=900)
    def delete_message(self,*args):self.deleted.append(args);return True
    def get_me(self):return types.SimpleNamespace(username='TestStudentBot')
    def answer_callback_query(self,*args,**kwargs):self.answered.append((args,kwargs))
    def message_handler(self,**kwargs):
        def register(fn):self.handlers.append((kwargs,fn));return fn
        return register
    def callback_query_handler(self,**kwargs):
        def register(fn):self.callbacks.append((kwargs,fn));return fn
        return register


def message(text='',kind='private',uid=42,cid=None,caption=None,document=None,photo=None):
    return types.SimpleNamespace(chat=types.SimpleNamespace(id=cid or uid,type=kind),
         from_user=types.SimpleNamespace(id=uid),text=text,caption=caption,
         document=document,photo=photo,message_id=25)


def document(name='notes.pdf',size=3400):
    return types.SimpleNamespace(file_id='FILE_ID',file_unique_id='UNIQUE_ID',
                                 file_name=name,file_size=size)

class DataTests(unittest.TestCase):
    def test_types(self):
        self.assertEqual(st.BADGES['image'],'🖼️');self.assertIn('zip',st.ALLOWED_TYPES)
    def test_user_caption(self):
        cap=st.parse_caption('Arabic Notes | Prof | Arabic | Education | I own copyright | For grammar | نحو',user=True)
        self.assertEqual(cap['category'],'Education');self.assertEqual(cap['aliases'],'نحو')
    def test_student_caption_requires_comment(self):
        with self.assertRaises(ValueError):st.parse_caption('Title | Author | Arabic | Education | permission',user=True)
    def test_caption_plain_text_blocks_html(self):
        with self.assertRaises(ValueError):st.parse_caption('<b>Title</b> | Author | Arabic',user=False)
    def test_caption_auto_title(self):
        val=st.parse_caption('',default_name='Notes')
        self.assertEqual(val['title'],'Notes')
    def test_document_image(self):
        m=message(document=document('diagram.PNG'))
        self.assertEqual(st.detect_kind(m)['kind'],'image')
    def test_photo(self):
        m=message(photo=[types.SimpleNamespace(file_id='ABC',file_unique_id='U',file_size=1200)])
        self.assertEqual(st.detect_kind(m)['kind'],'image')
    def test_video(self):
        m=message();m.video=types.SimpleNamespace(file_id='X',file_unique_id='U',file_size=99)
        self.assertEqual(st.detect_kind(m)['kind'],'video')
    def test_unknown_extension_rejected(self):
        with self.assertRaises(ValueError):st.detect_kind(message(document=document('virus.exe')))
    def test_pathological_media_id_rejected(self):
        with self.assertRaises(ValueError):st.canonical('DROP TABLE media')
    def test_tamil_vowels_preserved(self):
        self.assertIn('தமிழ்',st.normalize('தமிழ் மொழி'))
    def test_arabic_diacritics_removed(self):
        self.assertEqual(st.normalize('اَلْعَرَبِيَّة'),'العربية')
    def test_multilingual_aliases(self):
        self.assertIn('ابن كثير',st.expanded_queries('ibn kathir'))
    def test_rank_title_before_ocr(self):
        one=dict(title='Arabic Notes',author='Teacher',aliases='',category='School',description='',ocr_text='')
        two=dict(one,title='General Notes',ocr_text='Arabic Notes')
        self.assertGreater(st.rank(one,'Arabic Notes'),st.rank(two,'Arabic Notes'))
    def test_media_search_hidden_not_scanned(self):
        rows=[dict(id=UID,title='Tamil chart',author='Writer',category='Education',language='Tamil',media_kind='image',
                   file_size=30000,status='approved',ocr_text='தமிழ் எழுத்து',download_count=5)]
        with patch.object(st,'candidate_rows',return_value=rows):
            self.assertEqual(st.search('தமிழ்',kind='image')[0]['id'],UID)
            self.assertEqual(st.search('தமிழ்',kind='video'),[])
            self.assertEqual(st.search('தமிழ்',min_bytes=40000),[])
    def test_search_sort(self):
        a=dict(id='1',title='Arabic chart',author='Writer',category='Education',language='Arabic',media_kind='image',file_size=100,download_count=2)
        b=dict(a,id='2',title='Arabic notes',download_count=50,file_size=400)
        with patch.object(st,'candidate_rows',return_value=[a,b]):
            self.assertEqual(st.search('Arabic',sort='popular')[0]['id'],'2')
            self.assertEqual(st.search('Arabic',sort='smallest')[0]['id'],'1')
    def test_search_input_no_sql_dynamic(self):
        with self.assertRaises(ValueError):st.search('x'*200)
    def test_permission_and_licensing_sql(self):
        sql=(ROOT/'SQL_LIBRARY_MEDIA_V117.sql').read_text(encoding='utf-8')
        self.assertIn('ENABLE ROW LEVEL SECURITY',sql)
        self.assertIn('FROM anon,authenticated',sql)
        self.assertIn('library_v117_claim_media',sql)
        self.assertIn("'found','uploaded'",sql)
    def test_language_hint(self):
        self.assertEqual(prep.language_hint('தமிழ் மொழி பாடம்'), 'Tamil')
        self.assertEqual(prep.language_hint('hello world'),'English')
    def test_category_hint(self):self.assertEqual(prep.category_hint('biology cell notes'),'Biology')
    def test_title_inference(self):
        self.assertEqual(prep.extract('txt',b'grammar',filename='student_notes.txt')['suggested_title'],'student notes')
    def test_hash(self):
        self.assertEqual(len(prep.extract('txt',b'hello')['sha256']),64)
    def test_ocr_skipped_when_off(self):
        with patch.dict(os.environ,{'LIBRARY_MEDIA_OCR_ENABLED':'false'}):
            self.assertIsNone(prep.inspect_upload(Bot(),dict(kind='image',telegram_file_id='x',size=500))['sha256'])
    def test_download_size_cap(self):
        self.assertIsNone(prep.get_bytes(Bot(),'file',25_000_000))

class QueryTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'LIBRARY_MEDIA_V117_ENABLED':'true','BOOK_LIBRARY_ENABLED':'true',
                                        'BOOK_LIBRARY_BOT_USERNAME':'TestStudentBot',
                                        'BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT':'false'})
        self.env.start()
        self.modules=patch.dict(sys.modules,{
            'telebot':types.SimpleNamespace(types=types.SimpleNamespace(
                InlineKeyboardMarkup=Markup,InlineKeyboardButton=Btn)),
            'telebot.handler_backends':types.SimpleNamespace(ContinueHandling=End)})
        self.modules.start()
        self.bot=Bot()
    def tearDown(self):self.modules.stop();self.env.stop()
    def test_filter_parser(self):
        q,f=api.parse_search_query('Grammar type:image lang:Tamil sort:newest min_kb:10')
        self.assertEqual(q,'Grammar');self.assertEqual(f['kind'],'image');self.assertEqual(f['min_bytes'],10240)
    def test_filter_reject(self):
        with self.assertRaises(ValueError):api.parse_search_query('biology type:exe')
    def test_group_media_link_is_queued_by_v115_recognizer(self):
        import group_ui_v115 as g
        kb=Markup();kb.add(Btn('Image',url='https://t.me/TestStudentBot?start=media_'+uuid.uuid4().hex))
        self.assertTrue(g.book_url_keyboard(kb))
    def test_mixed_media_book_links(self):
        import group_ui_v115 as g
        kb=Markup();kb.add(Btn('Book',url='https://t.me/TestStudentBot?start=book_'+uuid.uuid4().hex))
        kb.add(Btn('Media',url='https://t.me/TestStudentBot?start=media_'+uuid.uuid4().hex))
        self.assertTrue(g.book_url_keyboard(kb))
    def test_group_unified_search(self):
        rows=[dict(id=UID,source='media',media_kind='image',title='Tamil map',file_size=320)]
        with patch.object(api,'union_search',return_value=rows):
            api.unified_search(self.bot,-1002,'Tamil map',group=True)
        self.assertIn('Library results',self.bot.sent[-1][1])
        kb=self.bot.sent[-1][2]['reply_markup']
        self.assertIn('?start=media_',kb.inline_keyboard[0][0].url)
    def test_group_thumbnail_scheduled(self):
        rows=[dict(id=UID,source='media',media_kind='image',title='Tamil map',preview_file_id='PHOTO')]
        with patch('group_ui_v115._remember') as remember:
            api._send_results(self.bot,-1002,'📚 Library results',rows,group=True)
            self.assertEqual(len(self.bot.photos),1)
            remember.assert_called_once()
    def test_private_no_group_thumbnail(self):
        rows=[dict(id=UID,source='media',media_kind='image',title='Tamil map',preview_file_id='PHOTO')]
        api._send_results(self.bot,42,'📚 Library results',rows,group=False)
        self.assertEqual(self.bot.photos,[])
    def test_start_group_is_not_processed(self):
        self.assertFalse(api.handle_media_start(self.bot,message('/start media_'+uuid.uuid4().hex,
                                                                 kind='supergroup',cid=-100)))
    def test_start_private_preview(self):
        with patch.object(api,'_preview') as out:
            self.assertTrue(api.handle_media_start(self.bot,message('/start media_'+uuid.uuid4().hex)))
            out.assert_called_once()
    def test_start_invalid_token_not_processed(self):
        self.assertFalse(api.handle_media_start(self.bot,message('/start media_BAD')))
    def test_preview_does_not_deliver_automatically(self):
        sample={'id':UID,'title':'Tamil Chart','author':'Prof','language':'Tamil',
                'category':'Education','media_kind':'image','file_size':3000,'preview_file_id':'PHOTO'}
        with patch.object(st,'get',return_value=sample):
            api._preview(self.bot,message('/start media_'+uuid.uuid4().hex),'m',UID)
        self.assertEqual(len(self.bot.copied),0)
        self.assertEqual(len(self.bot.photos),1)
    def test_private_delivery(self):
        sample={'id':UID,'title':'Tamil Chart','storage_channel_id':-1009,'storage_message_id':991}
        callback=types.SimpleNamespace(from_user=types.SimpleNamespace(id=42),id='x',
                                       message=message())
        with patch.object(st,'get',return_value=sample),patch.object(st,'record_delivery') as metric:
            api._deliver(self.bot,callback,'m',UID)
        self.assertEqual(self.bot.copied[0]['chat_id'],42);metric.assert_called_once()
    def test_repeated_book_session_is_private(self):
        callback=types.SimpleNamespace(from_user=types.SimpleNamespace(id=42),id='x',
                                       message=message())
        sample=dict(id=UID,title='Book',channel_id=-10099,message_id=80)
        with patch('book_library_store.get_book',return_value=sample),             patch('book_library_v112_store.record_delivery'):
            api._deliver(self.bot,callback,'b',UID)
        self.assertEqual(self.bot.copied[0]['from_chat_id'],-10099)
    def test_admin_panel_denies_other_users(self):
        api._admin_panel(self.bot,message(uid=99))
        self.assertIn('Administrator',self.bot.sent[0][1])
    def test_admin_panel_buttons(self):
        with patch('book_library_bot._admin',return_value=True):
            api._admin_panel(self.bot,message())
        self.assertIn('Pending Contributions',str(self.bot.sent[0][2]['reply_markup'].inline_keyboard[0][0].text))
    def test_no_media_upload_without_private(self):
        self.assertFalse(api.private(message(kind='supergroup',cid=-1002)))
    def test_contributor_uses_review_channel(self):
        with patch.dict(os.environ,{'BOOK_LIBRARY_CHANNEL_ID':'-10011','BOOK_LIBRARY_REVIEW_CHANNEL_ID':'-10012'}):
            m=message(caption='Tamil Charts | Tutor | Tamil | Education | Author granted permission | Class study',
                      document=document('charts.pdf'))
            row={'id':UID,'title':'Tamil Charts'}
            with patch.object(st,'duplicates',return_value=None),patch.object(st,'my_submissions',return_value=[]),\
                 patch.object(st,'create',return_value=row) as saver:
                api.submit_media(self.bot,m,contributor=True)
            self.assertEqual(self.bot.copied[0]['chat_id'],-10012)
            self.assertEqual(saver.call_args.args[0]['status'],'pending')
    def test_admin_requires_license(self):
        with patch.dict(os.environ,{'BOOK_LIBRARY_CHANNEL_ID':'-10011'}):
            with self.assertRaises(ValueError):api.submit_media(self.bot,message(document=document(),caption='Notes | Tutor | Tamil'))
            self.assertFalse(self.bot.copied)
    def test_approval_atomic(self):
        item=dict(id=UID,title='Arabic Chart',review_channel_id=-10012,review_message_id=33,
                  rights_statement='Permission',file_unique_id='AA',sha256=None,uploader_id=42)
        with patch.dict(os.environ,{'BOOK_LIBRARY_CHANNEL_ID':'-10011'}),\
             patch.object(st,'claim',return_value=item),patch.object(st,'duplicates',return_value=dict(id=UID)),\
             patch.object(st,'finalize',return_value=True) as finalize,patch.object(st,'audit'):
            api.approve(self.bot,42,UID)
            finalize.assert_called_once()
        self.assertEqual(self.bot.copied[0]['chat_id'],-10011)
    def test_double_approval_denied(self):
        with patch.object(st,'claim',return_value=None):
            with self.assertRaises(ValueError):api.approve(self.bot,42,UID)
    def test_failed_finalize_rolls_back_copy(self):
        item=dict(id=UID,title='Arabic Chart',review_channel_id=-10012,review_message_id=33,
                  rights_statement='Permission',file_unique_id='AA',sha256=None,uploader_id=42)
        with patch.dict(os.environ,{'BOOK_LIBRARY_CHANNEL_ID':'-10011'}),\
             patch.object(st,'claim',return_value=item),patch.object(st,'duplicates',return_value=None),\
             patch.object(st,'finalize',return_value=False),patch.object(st,'reset_processing'),             patch.object(st,'get',return_value={'status':'processing','storage_message_id':None}):
            with self.assertRaises(RuntimeError):api.approve(self.bot,42,UID)
        self.assertTrue(self.bot.deleted)
    def test_request_notifications(self):
        item={'id':UID,'user_id':43,'title':'Arabic Notes','status':'found'}
        with patch.object(st,'resolve_request',return_value=[item]),patch.object(st,'audit'):
            api._request_decision(self.bot,42,'f',UID)
        self.assertIn('FOUND',self.bot.sent[0][1])
    def test_media_editor_is_whitelisted(self):
        with self.assertRaises(ValueError):st.edit(UID,{'uploader_id':99})

class ZipTests(unittest.TestCase):
    def _archive(self,filename,content):
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:z.writestr(filename,content)
        return buf.getvalue()
    def test_zip_pdf(self):
        names=api._zip_entries(self._archive('arabic.pdf',b'%PDF-1.5\nexample'))
        self.assertEqual(names[0][1],'pdf')
    def test_zip_path_traversal_rejected(self):
        with self.assertRaises(ValueError):api._zip_entries(self._archive('../etc/passwd.pdf',b'%PDF-1.5'))
    def test_zip_bad_pdf_signature(self):
        with self.assertRaises(ValueError):api._zip_entries(self._archive('bad.pdf',b'just a text'))
    def test_zip_unsupported_file_ignored(self):
        self.assertEqual(api._zip_entries(self._archive('note.exe',b'MZ')),[])
    def test_zip_many_entries_rejected(self):
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:
            for i in range(21):z.writestr(str(i)+'.txt',b'hello')
        with self.assertRaises(ValueError):api._zip_entries(buf.getvalue())

class InstallerTests(unittest.TestCase):
    def test_existing_anchors_are_present(self):
        for name in TARGETS:
            self.assertTrue((ROOT/name).exists(),name)
    def test_idempotent(self):
        # Works whether the user runs the test before OR after --apply.
        for name in TARGETS:
            src=(ROOT/name).read_text(encoding='utf-8')
            patched=transform(name,src)
            self.assertEqual(transform(name,patched),patched)
    def test_fail_closed(self):
        with self.assertRaises(ValueError):transform('book_library_bot.py','wrong layout')
    def test_does_not_touch_user_modules(self):
        self.assertNotIn('v10',TARGETS);self.assertNotIn('main.py',TARGETS)

if __name__=='__main__':unittest.main()
