"""V8 offline tests. Run on the real project with python -m unittest TEST_V8_STUDY_LAB -v."""
import hashlib
import hmac
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from urllib.parse import urlencode

from v8_engine import (StudyInputError, extract_document, answer_from_document,
    analyze_past_paper, flashcards_from_text, practice_quiz, make_exam_plan,
    summarize_lecture, citation, MAX_FILE_BYTES)
from INSTALL_V8_STUDY_LAB import patch_text


class ExtractTests(unittest.TestCase):
    def test_utf8(self):
        pages=extract_document('class.txt','Photosynthesis: plants make food with light.'.encode());self.assertEqual(pages[0][0],1)
    def test_pdf_page_numbers(self):
        from pypdf import PdfWriter
        from reportlab.pdfgen import canvas
        def page(text):
            out=BytesIO();c=canvas.Canvas(out);c.drawString(50,700,text);c.save();return out.getvalue()
        from pypdf import PdfReader
        writer=PdfWriter()
        for text in ('Plants make energy from sunlight.','Cells contain a nucleus and membrane.'):
            writer.add_page(PdfReader(BytesIO(page(text))).pages[0])
        b=BytesIO();writer.write(b)
        results=extract_document('test.pdf',b.getvalue())
        self.assertEqual(len(results),2)
        self.assertIn('Cells',answer_from_document(results,'What contains a nucleus?'))
        self.assertIn('[Page 2]',answer_from_document(results,'What contains a nucleus?'))
    def test_docx(self):
        from docx import Document
        d=Document();d.add_paragraph('Cell: The basic unit of a living organism.');b=BytesIO();d.save(b)
        self.assertIn('Cell',extract_document('file.docx',b.getvalue())[0][1])
    def test_untrusted_extension(self):
        with self.assertRaises(StudyInputError):extract_document('file.exe',b'ignored contents')
    def test_oversize(self):
        with self.assertRaises(StudyInputError):extract_document('file.txt',b'A'*(MAX_FILE_BYTES+1))
    def test_binary_txt(self):
        with self.assertRaises(StudyInputError):extract_document('file.txt',b'\xff\xfe\xff')
    def test_scan_empty(self):
        with self.assertRaises(StudyInputError):extract_document('file.txt',b'1')

class StudyTests(unittest.TestCase):
    def setUp(self):
        self.pages=[(1,'Cell: The smallest unit of life.\nAtom: The basic building block of matter.\nMolecule: Two or more atoms.\nOrgan: A body structure of tissues.\nTissue: A group of similar cells.')]
    def test_answer_rank(self):self.assertIn('[Page 1]',answer_from_document(self.pages,'What is a cell?'))
    def test_answer_no_match(self):self.assertIn("couldn't find",answer_from_document(self.pages,'quantum astrophysics'))
    def test_answer_short(self):
        with self.assertRaises(StudyInputError):answer_from_document(self.pages,'a')
    def test_card_generation(self):self.assertGreaterEqual(len(flashcards_from_text(self.pages)),4)
    def test_quiz(self):
        quiz=practice_quiz(flashcards_from_text(self.pages))
        self.assertGreaterEqual(len(quiz),4)
        for _,opts,key in quiz:self.assertEqual(len(opts),4);self.assertIn(key,'ABCD')
    def test_quiz_not_enough(self):
        with self.assertRaises(StudyInputError):practice_quiz([('a','b')])
    def test_paper_questions(self):
        data=analyze_past_paper([(1,'1. Explain photosynthesis and sunlight.\n2. Define cellular respiration and oxygen?')])
        self.assertEqual(data['total_detected'],2)
        self.assertTrue(data['topics'])
    def test_paper_dedup(self):
        data=analyze_past_paper([(1,'1. Explain how plants grow?\n1. Explain how plants grow?')])
        self.assertEqual(len(data['questions']),1)
    def test_plan(self):
        result=make_exam_plan([{'exam_at':'2026-11-03T09:00:00+00:00','title':'Physics'}],60,today=__import__('datetime').date(2026,11,1))
        self.assertTrue(any('Physics' in row for row in result))
    def test_plan_empty(self):self.assertIn('No upcoming',make_exam_plan([])[0])
    def test_plan_invalid(self):
        with self.assertRaises(StudyInputError):make_exam_plan([],0)
    def test_summary(self):self.assertIn('Keywords',summarize_lecture('Photosynthesis uses sunlight to convert carbon dioxide into glucose. Plants produce oxygen during this reaction.'))
    def test_summary_empty(self):
        with self.assertRaises(StudyInputError):summarize_lecture('hello')
    def test_apa(self):self.assertIn('(2020)',citation('Ali','2020','My Paper','Journal'))
    def test_harvard(self):self.assertIn("'My Paper'",citation('Ali','2020','My Paper','Journal','HARVARD'))
    def test_mla(self):self.assertIn('"My Paper."',citation('Ali','2020','My Paper','Journal','MLA'))
    def test_cite_invalid_year(self):
        with self.assertRaises(StudyInputError):citation('Ali','20','Title','Journal')
    def test_cite_invalid_style(self):
        with self.assertRaises(StudyInputError):citation('Ali','2020','Title','Journal','Unknown')

class InstallerTests(unittest.TestCase):
    ROOT=Path(__file__).resolve().parent
    SOURCE=Path(__file__).resolve().parent
    def test_real_main_anchor(self):
        # In an installed project, verify the real anchors if source files are present.
        source=Path(__file__).resolve().parent/'main.py'
        if not source.exists(): self.skipTest('Run from StudentAssistantBot folder to check integration')
        text=source.read_text('utf-8'); updated=patch_text('main.py',text)
        self.assertEqual(patch_text('main.py',updated),updated)
    def test_ui_fixture(self):
        fixture='ALL_UI_BUTTONS = (\nTEXT = {\"en\": {\"welcome\": \"Hello V7.9\"}}\nCATEGORY_TEXT = {\n'
        updated=patch_text('ui_v57.py',fixture)
        self.assertIn('V8_ENABLED',updated)
        self.assertEqual(updated,patch_text('ui_v57.py',updated))
    def test_navigation_fixture(self):
        fixture='GLOBAL_BUTTONS.add("📝 Text → PDF")\n'
        updated=patch_text('navigation.py',fixture)
        self.assertIn('V8 Study Lab',updated)
        self.assertEqual(updated,patch_text('navigation.py',updated))
    def test_missing_anchor_fails_closed(self):
        with self.assertRaises(ValueError):patch_text('main.py','no matches')

class TelegramWorkflowTests(unittest.TestCase):
    def setUp(self):
        try: import telebot
        except ImportError:
            mod=types.ModuleType('telebot')
            class Keyboard:
                def __init__(self,*args,**kwargs):self.rows=[]
                def row(self,*args):self.rows.append(args)
                def add(self,*args):self.rows.append(args)
            mod.types=types.SimpleNamespace(ReplyKeyboardMarkup=Keyboard,KeyboardButton=lambda x:x,
                InlineKeyboardMarkup=Keyboard,InlineKeyboardButton=lambda *args,**kwargs:(args,kwargs),
                WebAppInfo=lambda **kw:kw)
            back=types.ModuleType('telebot.handler_backends');back.ContinueHandling=object
            sys.modules['telebot']=mod;sys.modules['telebot.handler_backends']=back
        try: import navigation
        except ImportError:
            nav=types.ModuleType('navigation')
            nav.should_yield_to_navigation=lambda text:text.startswith('/') or text in ('🏠 Main Menu','❌ Cancel')
            sys.modules['navigation']=nav
        import v8_bot
        self.mod=v8_bot
        self.old=(os.getenv('V8_ENABLED'),os.getenv('V8_ALLOWED_USER_IDS'))
        os.environ['V8_ENABLED']='true';os.environ['V8_ALLOWED_USER_IDS']='2468'
        class Bot:
            def __init__(self):self.handlers={};self.sent=[]
            def message_handler(self,**kwargs):
                def deco(fn):self.handlers[fn.__name__]=fn;return fn
                return deco
            def send_message(self,chat_id,text,reply_markup=None):self.sent.append((chat_id,text))
            def get_file(self,file_id):return types.SimpleNamespace(file_size=100,file_path='example.txt')
            def download_file(self,path):return b'Cell: The smallest unit of life.\nAtom: The building block of matter.\nMolecule: Two or more atoms.\nOrgan: Tissue-based body structure.\nTissue: Collection of similar cells.'
            def get_chat_member(self,group,uid):return types.SimpleNamespace(status='administrator')
        self.bot=Bot();self.mod.register_v8_handlers(self.bot,lambda *a:None)
    def tearDown(self):
        self.mod._clear(2468)
        for key,val in zip(('V8_ENABLED','V8_ALLOWED_USER_IDS'),self.old):
            if val is None:os.environ.pop(key,None)
            else:os.environ[key]=val
    def msg(self,text=None,chat_id=2468,chat_type='private',document=None):
        return types.SimpleNamespace(text=text,chat=types.SimpleNamespace(id=chat_id,type=chat_type),from_user=types.SimpleNamespace(id=2468),document=document)
    def test_private_document_search(self):
        self.bot.handlers['feature_command'](self.msg('/v8doc'))
        self.bot.handlers['on_document'](self.msg(document=types.SimpleNamespace(file_size=100,file_name='lecture.txt',file_id='any')))
        self.bot.handlers['on_text'](self.msg('What is a cell?'))
        self.assertTrue(any('Matching passages' in text for _,text in self.bot.sent))
    def test_flashcards_preview(self):
        self.bot.handlers['feature_command'](self.msg('/v8cards'))
        self.bot.handlers['on_document'](self.msg(document=types.SimpleNamespace(file_size=100,file_name='lecture.txt',file_id='any')))
        self.assertTrue(any('Draft cards' in text for _,text in self.bot.sent))
    def test_group_creation_not_public(self):
        self.bot.handlers['battle_new'](self.msg('/v8battle_new -100123456789 | Question? | A | B | C | D | A',chat_id=-100123456789,chat_type='supergroup'))
        self.assertIn('privately',self.bot.sent[-1][1])
    def test_unlisted_user_no_access(self):
        self.bot.handlers['feature_command'](types.SimpleNamespace(text='/v8doc',chat=types.SimpleNamespace(id=7,type='private'),from_user=types.SimpleNamespace(id=7)))
        self.assertIn('not enabled',self.bot.sent[-1][1])
    def test_cancel_clears_state(self):
        self.bot.handlers['feature_command'](self.msg('/v8doc'))
        self.bot.handlers['cancel'](self.msg('/v8cancel'))
        self.assertIsNone(self.mod._get(2468))

class TelegramAuthTests(unittest.TestCase):
    def setUp(self):
        # Avoid optional Flask dependency for the HMAC-only function; fake imports only if absent.
        if 'flask' not in sys.modules:
            try: import flask
            except ImportError:
                f=types.ModuleType('flask');f.request=object();f.jsonify=lambda x:x;f.Response=object
                sys.modules['flask']=f
        from v8_miniapp import validate_init_data,MiniAppAuthError
        self.validate=validate_init_data; self.Error=MiniAppAuthError
        self.token='123456:TEST_ONLY_TOKEN';self.now=1730000000
    def make(self,uid=2468,stamp=None):
        data={'auth_date':str(self.now if stamp is None else stamp),'user':json.dumps({'id':uid,'first_name':'Test'},separators=(',',':'))}
        body='\n'.join(f'{k}={data[k]}' for k in sorted(data))
        key=hmac.new(b'WebAppData',self.token.encode(),hashlib.sha256).digest()
        sig=hmac.new(key,body.encode(),hashlib.sha256).hexdigest()
        return urlencode({**data,'hash':sig})
    def test_valid(self):self.assertEqual(self.validate(self.make(),self.token,self.now),2468)
    def test_tampered(self):
        with self.assertRaises(self.Error):self.validate(self.make().replace('2468','2469'),self.token,self.now)
    def test_wrong_token(self):
        with self.assertRaises(self.Error):self.validate(self.make(),'987654:DIFFERENT',self.now)
    def test_expired(self):
        with self.assertRaises(self.Error):self.validate(self.make(stamp=self.now-3700),self.token,self.now)
    def test_future(self):
        with self.assertRaises(self.Error):self.validate(self.make(stamp=self.now+65),self.token,self.now)
    def test_duplicate_fields(self):
        with self.assertRaises(self.Error):self.validate(self.make()+'&user=%7B%7D',self.token,self.now)
    def test_missing_auth(self):
        with self.assertRaises(self.Error):self.validate('',self.token,self.now)

class GateTests(unittest.TestCase):
    def setUp(self):
        # telebot installed in live bot; fake module in lightweight local test environment.
        try: import telebot
        except ImportError:
            mod=types.ModuleType('telebot');mod.types=types.SimpleNamespace()
            back=types.ModuleType('telebot.handler_backends');back.ContinueHandling=object
            sys.modules['telebot']=mod;sys.modules['telebot.handler_backends']=back
        import v8_bot
        self.v8=v8_bot
        self.old=(os.getenv('V8_ENABLED'),os.getenv('V8_ALLOWED_USER_IDS'))
    def tearDown(self):
        for name,val in zip(('V8_ENABLED','V8_ALLOWED_USER_IDS'),self.old):
            if val is None:os.environ.pop(name,None)
            else:os.environ[name]=val
    def test_closed_default(self):
        os.environ.pop('V8_ENABLED',None);os.environ['V8_ALLOWED_USER_IDS']='2468'
        self.assertFalse(self.v8.allowed(2468))
    def test_allowlist(self):
        os.environ['V8_ENABLED']='true';os.environ['V8_ALLOWED_USER_IDS']='1234, 2468'
        self.assertTrue(self.v8.allowed(2468));self.assertFalse(self.v8.allowed(2))
    def test_expired_state(self):
        self.v8._put(99999,{'kind':'doc'});self.v8.STATES[99999]['last']-=1000
        self.assertIsNone(self.v8._get(99999))
    def test_progress_user_filter(self):
        class Query:
            def __init__(self):self.conditions=[]
            def select(self,*a,**kw):return self
            def eq(self,key,value):self.conditions.append((key,value));return self
            def limit(self,n):return self
            def execute(self):return types.SimpleNamespace(count=3)
        class DB:
            def table(self,name):self.q=Query();return self.q
        db=DB();old=self.v8._db;self.v8._db=lambda:db
        try:self.assertEqual(self.v8._count_rows(22,'notes'),3);self.assertIn(('user_id',22),db.q.conditions)
        finally:self.v8._db=old

if __name__=='__main__':unittest.main()
