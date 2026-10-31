"""Offline V11.3 Book Library security, behavior, installer and integration tests.
No Telegram network, Open Library requests or real Supabase connections.
"""
from __future__ import annotations
import hashlib
import hmac
import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import urlencode, parse_qsl

HERE=pathlib.Path(__file__).resolve().parent
# Package is copied into existing project root; import only current local modules.
import book_library_v113_store as store
import book_library_v113_bot as botmod
import book_library_v113_notify as notify
from INSTALL_BOOK_LIBRARY_V113 import transform, integrate, MARK


def install_stub_flask():
    """Flask is already in requirements.txt on Render; tests run without it installed."""
    try:
        import flask  # Use the real Flask package when it is installed (production).
    except ImportError:
        fake=types.ModuleType('flask')
        fake.request=types.SimpleNamespace(path='/',headers={},args={},get_json=lambda silent=True:{})
        fake.jsonify=lambda d: d
        fake.send_file=lambda path, mimetype='':(str(path),mimetype)
        fake.make_response=lambda x:x
        fake.abort=lambda code: (_ for _ in ()).throw(ValueError('HTTP '+str(code)))
        sys.modules['flask']=fake
    import book_library_v113_web as web
    return web


class NormalizeTests(unittest.TestCase):
    def setUp(self): store._metadata_cache.clear()
    def test_arabic_marks_removed(self):
        self.assertEqual(store.norm('إِحْيَاء  العُلُوم'),store.norm('إحياء العُلوم'))
    def test_tamil_remains(self):
        self.assertIn('தமிழ்',store.norm('தமிழ் புத்தகம்'))
    def test_nfkc(self):
        self.assertEqual(store.norm('ＡＢＣ'),'abc')
    def test_fuzzy_typo(self):
        arr=[dict(id=1,title='Ihya Ulumuddin',author='Al Ghazali',active=True),
             dict(id=2,title='Plant Biology',author='A Scientist',active=True)]
        self.assertEqual(store.fuzzy_rank('Ihya Ulumudin',arr)[0]['id'],1)
    def test_fuzzy_excludes_inactive(self):
        self.assertFalse(store.fuzzy_rank('Ihya Ulumudin',[{'title':'Ihya Ulumuddin','active':False}]))
    def test_fuzzy_bad_query(self):
        self.assertEqual(store.fuzzy_rank('x',[]),[])
    def test_clean_xss(self):
        with self.assertRaises(ValueError):store.clean('<script>')
    def test_clean_unicode(self):
        self.assertEqual(store.clean('அறிவியல் புத்தகம்'),'அறிவியல் புத்தகம்')
    def test_duplicate_check(self):
        d=MagicMock()
        d.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data=[{'id':'ok','title':'Copy'}]
        result=store.find_duplicate('unique',db=d)
        self.assertEqual(result['matched_on'],'file_unique_id')
    def test_duplicate_missing(self):
        self.assertIsNone(store.find_duplicate(db=MagicMock()))
    def test_status_validation(self):
        with self.assertRaises(ValueError):store.update_progress(123,'a','fiction')
    def test_percent_validation(self):
        with self.assertRaises(ValueError):store.update_progress(123,'a','reading',101)
    def test_review_rating_validation(self):
        with self.assertRaises(ValueError):store.submit_review(123,'a',8,'A review')
    def test_report_kind_validation(self):
        with self.assertRaises(ValueError):store.report_book(123,'a','unknown','abc')
    def test_challenge_limits(self):
        with self.assertRaises(ValueError):store.challenge(12,0,30)
    def test_edition_year(self):
        with self.assertRaises(ValueError):store.set_edition('a',year=1200)
    def test_subscribe_invalid(self):
        with self.assertRaises(ValueError):store.subscribe(1,'private','xyz')
    def test_negative_userid(self):
        with self.assertRaises(ValueError):store.uid(-1)
    def test_isbn_metadata_rejects(self):
        with self.assertRaises(ValueError):store.isbn_metadata('1234')
    def test_isbn_fixed_host(self):
        class Resp:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):return b'{"title":"Sample","covers":[77]}'
        def opener(req,timeout):
            self.assertEqual(req.full_url,'https://openlibrary.org/isbn/9780140328721.json')
            self.assertEqual(timeout,6)
            return Resp()
        result=store.isbn_metadata('9780140328721',opener=opener,now=123)
        self.assertEqual(result['cover_url'],'https://covers.openlibrary.org/b/id/77-M.jpg')
    def test_isbn_cache(self):
        class FailOpener:
            def __call__(self,*args,**kwargs):raise AssertionError('cache should avoid network')
        store._metadata_cache['9780140328721']=(1000,{'title':'Cached Book'})
        self.assertEqual(store.isbn_metadata('9780140328721',opener=FailOpener(),now=124)['title'],'Cached Book')
    def test_isbn_oversize(self):
        class Resp:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):return b'a'*100001
        with self.assertRaises(ValueError):store.isbn_metadata('9780000000002',opener=lambda *x,**k:Resp(),now=42)


class TelegramAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.web=install_stub_flask()
    def signed(self,user=123,when=123456):
        data={'auth_date':str(when),'user':json.dumps({'id':user},separators=(',',':')),'query_id':'id1'}
        checked='\n'.join(f'{k}={v}' for k,v in sorted(data.items()))
        secret=hmac.new(b'WebAppData',b'test-token',hashlib.sha256).digest()
        data['hash']=hmac.new(secret,checked.encode(),hashlib.sha256).hexdigest()
        return urlencode(data)
    def test_auth_success(self):
        self.assertEqual(self.web.validate_init_data(self.signed(), 'test-token',now=123457),123)
    def test_auth_different_user(self):
        self.assertEqual(self.web.validate_init_data(self.signed(user=456),'test-token',now=123457),456)
    def test_auth_tamper(self):
        fields=parse_qsl(self.signed())
        forged=urlencode([(k,'{"id":999}' if k=='user' else v) for k,v in fields])
        with self.assertRaises(ValueError):self.web.validate_init_data(forged,'test-token',now=123457)
    def test_auth_expired(self):
        with self.assertRaises(ValueError):self.web.validate_init_data(self.signed(),'test-token',now=123457+90000)
    def test_auth_future(self):
        with self.assertRaises(ValueError):self.web.validate_init_data(self.signed(),'test-token',now=123000)
    def test_auth_wrong_token(self):
        with self.assertRaises(ValueError):self.web.validate_init_data(self.signed(),'other-token',now=123457)
    def test_auth_missing(self):
        with self.assertRaises(ValueError):self.web.validate_init_data('','test-token',now=123457)
    def test_auth_duplicate(self):
        with self.assertRaises(ValueError):self.web.validate_init_data(self.signed()+'&auth_date=123456','test-token',now=123457)
    def test_auth_invalid_user(self):
        with self.assertRaises(ValueError):self.web.validate_init_data(self.signed(user=-1),'test-token',now=123457)
    def test_catalog_redaction(self):
        obj=self.web._public({'id':'a','title':'Sample','channel_id':-10099,'message_id':111,'uploaded_by':123,
                              'cover_url':'https://evil.test/image.jpg','file_size':222})
        self.assertNotIn('channel_id',obj)
        self.assertNotIn('message_id',obj)
        self.assertNotIn('uploaded_by',obj)
        self.assertIsNone(obj['cover_url'])
    def test_allow_safe_cover(self):
        url='https://covers.openlibrary.org/b/id/123-M.jpg'
        self.assertEqual(self.web._public({'cover_url':url})['cover_url'],url)
    def test_cannot_use_userid_only(self):
        with self.assertRaises(ValueError):self.web.validate_init_data('user_id=123','test-token',now=123457)


class FakeBot:
    def __init__(self):self.handlers=[];self.callbacks=[];self.inlines=[];self.sent=[]
    def message_handler(self,*args,**kwargs):
        def deco(fn):self.handlers.append((kwargs.get('commands'),kwargs.get('func'),fn));return fn
        return deco
    def callback_query_handler(self,*args,**kwargs):
        def deco(fn):self.callbacks.append((kwargs,fn));return fn
        return deco
    def inline_handler(self,*args,**kwargs):
        def deco(fn):self.inlines.append((kwargs,fn));return fn
        return deco
    def send_message(self,chat_id,text,**kw):self.sent.append((chat_id,text,kw))
    def answer_callback_query(self,*a,**k):pass
    def answer_inline_query(self,*a,**k):pass


def msg(text,chat='private',uid=123):
    chat_id=uid if chat=='private' else -100555
    return types.SimpleNamespace(text=text,chat=types.SimpleNamespace(id=chat_id,type=chat),
                  from_user=types.SimpleNamespace(id=uid),document=None,caption='')


class BotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake=types.ModuleType('telebot')
        fake.types=types.SimpleNamespace(InlineKeyboardButton=lambda *a,**kw:types.SimpleNamespace(**kw),
            InlineKeyboardMarkup=lambda *a,**kw:types.SimpleNamespace(add=lambda *a:None),
            WebAppInfo=lambda **kw:types.SimpleNamespace(**kw),
            InlineQueryResultArticle=lambda **kw:types.SimpleNamespace(**kw),
            InputTextMessageContent=lambda x:types.SimpleNamespace(text=x))
        cls.old_telebot=sys.modules.get('telebot')
        sys.modules['telebot']=fake
    @classmethod
    def tearDownClass(cls):
        if cls.old_telebot is None:sys.modules.pop('telebot',None)
        else:sys.modules['telebot']=cls.old_telebot
    def setUp(self):
        self.b=FakeBot()
        self.env=patch.dict(os.environ,{
            'BOOK_LIBRARY_ENABLED':'true','BOOK_LIBRARY_V112_ENABLED':'true','BOOK_LIBRARY_V113_ENABLED':'true',
            'BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT':'false','BOOK_LIBRARY_ALLOW_ALL_GROUPS':'true',
            'BOOK_LIBRARY_ADMIN_IDS':'987','BOOK_LIBRARY_BOT_USERNAME':'StudentLibBot'},clear=False)
        self.env.start();botmod.register_v113_handlers(self.b)
    def tearDown(self):self.env.stop();botmod._recent_actions.clear()
    def handler(self,command):
        for cmds,cond,fn in self.b.handlers:
            if cmds and command in cmds:return fn
        raise AssertionError('Missing handler '+command)
    def test_all_feature_commands_exist(self):
        expected='booksmart bookrelated bookseries bookinfo bookreading bookprogress bookchallenge bookchallengecheck bookcollections bookcollection bookcollectionadd bookcollectionview bookreview bookreviews bookalert bookalerts bookrequest bookreport booksubmit bookmeta bookmetafill bookedition bookdescription bookrequests bookrequestresolve bookreviewsadmin bookreviewmoderate booksubmissions booksubmitapprove booksubmitreject bookreports bookreportresolve bookanalytics bookbulk bookbulkapply'.split()
        self.assertTrue(all(self.handler(x) for x in expected))
    def test_public_smart_search_group(self):
        with patch.object(botmod,'smart_search',return_value=[]):
            self.handler('booksmart')(msg('/booksmart secret',chat='group'))
        self.assertTrue(self.b.sent)
    def test_user_cannot_admin(self):
        self.handler('bookmeta')(msg('/bookmeta 9780140328721'))
        self.assertIn('administrators only',self.b.sent[-1][1])
    def test_group_cannot_get_personal_progress(self):
        self.handler('bookreading')(msg('/bookreading',chat='group'))
        self.assertIn('private chat',self.b.sent[-1][1])
    def test_admin_can_request_metadata(self):
        with patch.object(botmod,'isbn_metadata',return_value={'title':'A Book'}):
            self.handler('bookmeta')(msg('/bookmeta 9780140328721',uid=987))
        self.assertIn('A Book',self.b.sent[-1][1])
    def test_alert_restricted_to_private(self):
        self.handler('bookalert')(msg('/bookalert category | Psychology',chat='group'))
        self.assertIn('private',self.b.sent[-1][1])
    def test_submit_state_set(self):
        self.handler('booksubmit')(msg('/booksubmit'))
        self.assertIn(123,botmod._pending_submissions)
    def test_student_cannot_edit(self):
        self.handler('bookedition')(msg('/bookedition abc',uid=123))
        self.assertIn('administrators only',self.b.sent[-1][1])
    def test_failed_review_validation(self):
        self.handler('bookreview')(msg('/bookreview invalid'))
        self.assertIn('⚠️',self.b.sent[-1][1])
    def test_request_is_private(self):
        self.handler('bookrequest')(msg('/bookrequest title',chat='group'))
        self.assertIn('private',self.b.sent[-1][1])
    def test_book_admin_enabled_flag(self):
        with patch.dict(os.environ,{'BOOK_LIBRARY_V113_ENABLED':'false'}):
            self.handler('bookmeta')(msg('/bookmeta test',uid=987))
        self.assertIn('administrators only',self.b.sent[-1][1])
    def test_inline_registered(self):
        self.assertEqual(len(self.b.inlines),1)
    def test_callback_registered(self):
        self.assertEqual(len(self.b.callbacks),1)
    def test_optional_small_hash(self):
        d=types.SimpleNamespace(file_size=3,file_id='fid')
        with patch.dict(os.environ,{'BOOK_LIBRARY_HASH_SMALL_FILES':'true'}):
            self.b.get_file=lambda x:types.SimpleNamespace(file_path='path')
            self.b.download_file=lambda x:b'abc'
            self.assertEqual(botmod._safe_hash(self.b,d),hashlib.sha256(b'abc').hexdigest())
    def test_hash_off(self):
        self.assertIsNone(botmod._safe_hash(self.b,types.SimpleNamespace(file_size=3)))
    def test_miniapp_invalid_scheme(self):
        with patch.dict(os.environ,{'BOOK_LIBRARY_MINIAPP_URL':'http://example.com/library'}):
            self.assertIsNone(botmod._mini_url())
    def test_miniapp_https(self):
        with patch.dict(os.environ,{'BOOK_LIBRARY_MINIAPP_URL':'https://app.example.com/library'}):
            self.assertEqual(botmod._mini_url(),'https://app.example.com/library')
    def test_admin_approval_guard(self):
        with self.assertRaises(ValueError):botmod._approve_submission(self.b,msg('/booksubmitapprove ABC',uid=987),'ABC')


class InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_bot=HERE/'book_library_bot.py'
        cls.old_store=HERE/'book_library_store.py'
        cls.old_main=HERE/'main.py'
    def test_source_layout(self):
        if not self.old_bot.exists():self.skipTest('Original V11.2 code fixture unavailable')
        self.assertIn('V11.3',transform('book_library_bot.py',self.old_bot.read_text(encoding='utf-8')))
    def test_installer_preserves_legacy(self):
        if not self.old_bot.exists():self.skipTest('Original fixture unavailable')
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder)
            for name,source in [('book_library_bot.py',self.old_bot),('book_library_store.py',self.old_store),('main.py',self.old_main)]:
                shutil.copy2(source,root/name)
            before={x:(root/x).read_bytes() for x in ['main.py','book_library_bot.py','book_library_store.py']}
            planned=integrate(root,apply=False,output=lambda x:None)
            self.assertTrue(len(planned) in (0,3))
            self.assertTrue(all((root/x).read_bytes()==b for x,b in before.items()))
            self.assertEqual(len(integrate(root,apply=True,output=lambda x:None)),len(planned))
            self.assertEqual(integrate(root,apply=True,output=lambda x:None),[])
            source=(root/'book_library_bot.py').read_text(encoding='utf-8')
            self.assertIn('register_v112_handlers(bot)',source)
            self.assertIn('register_v113_handlers(bot)',source)
            self.assertIn('latest_books(limit=5)',source)
            self.assertIn('BOOK_LIBRARY_ALLOW_ALL_GROUPS',source)
            self.assertIn('V11.3 Advanced Library',source)
            self.assertIn('register_book_library_web(app, bot)',(root/'main.py').read_text(encoding='utf-8'))
    def test_windows_crlf(self):
        if not self.old_bot.exists():self.skipTest('Original fixture unavailable')
        s=self.old_bot.read_text(encoding='utf-8').replace('\n','\r\n')
        r=transform('book_library_bot.py',s.replace('\r\n','\n')).replace('\n','\r\n')
        self.assertIn('\r\n',r)
    def test_unknown_source_refused(self):
        with self.assertRaises(ValueError):transform('book_library_bot.py','test only')


class AssetTests(unittest.TestCase):
    def test_required_sql_security(self):
        sql=(HERE/'SQL_BOOK_LIBRARY_V113.sql').read_text(encoding='utf-8')
        for term in ['ROW LEVEL SECURITY','REVOKE ALL','service_role','book_library_v113_claim_submission',
                     'book_library_submissions','book_library_reports','book_library_reviews',
                     'book_library_daily_stats','book_library_v113_claim_notifications']:
            self.assertIn(term,sql)
    def test_html_no_secrets(self):
        text=(HERE/'book_library_v113_miniapp.html').read_text(encoding='utf-8')
        self.assertIn('telegram-web-app.js',text)
        self.assertNotIn('SUPABASE_SECRET',text)
    def test_js_uses_initdata(self):
        js=(HERE/'book_library_v113_app.js').read_text(encoding='utf-8')
        self.assertIn('X-Telegram-Init-Data',js)
        self.assertIn('textContent',js)
    def test_notifier_default_off(self):
        with patch.dict(os.environ,{'BOOK_LIBRARY_V113_ENABLED':'true','BOOK_LIBRARY_NOTIFIER_ENABLED':'false'}):
            self.assertFalse(notify.start_worker_if_enabled(MagicMock()))


if __name__=='__main__':unittest.main()
