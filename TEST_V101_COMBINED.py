"""Offline regression tests for all 12 V10.1 modules; no live API or DB calls."""
from __future__ import annotations
import io,json,os,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import v101_engine as e
import v101_gemini as g
ai=g
import v101_store as s
import v101_bot as b
from INSTALL_V101_COMBINED import integrate,transform,BUTTON
from v10_engine import StudyError

SOURCES=[{'title':'Biology','document_id':'1','page_number':2,'body':'Cells are the building blocks of organisms and contain genetic material.'},
         {'title':'Science','document_id':'2','page_number':3,'body':'Living organisms contain cells and may reproduce using genetic material.'}]
QUIZ={'questions':[{'question':'Which statement about cells is accurate?',
                    'options':['They are the building blocks','They are moons','They are cities','They are metals'],
                    'answer':'A','explanation':'Cells build organisms. [S1]'}]*3}
CARDS={'cards':[{'question':'What are living things made of?','answer':'Cells [S1]'},
                {'question':'What do cells contain inside them?','answer':'Genetic material [S2]'}]}

class EngineTests(unittest.TestCase):
    def test_languages(self):
        for code,name in [('en','English'),('ta','Tamil'),('si','Sinhala'),('ar','Arabic')]:
            self.assertEqual(e.language(code),name)
    def test_language_rejects_unknown(self):
        with self.assertRaises(StudyError):e.language('unknown')
    def test_topic_bounds(self):
        with self.assertRaises(StudyError):e.topic('x')
        self.assertEqual(e.topic(' Biology '),'Biology')
    def test_source_refs(self):
        self.assertIn('[S1] Biology, page 2:',e.sources(SOURCES)[0])
    def test_source_limit(self):self.assertEqual(len(e.sources(SOURCES*10)),4)
    def test_extract_json_fence(self):self.assertEqual(e.extract_json('```json\n{"x":1}\n```'),{'x':1})
    def test_extract_bad_json(self):
        with self.assertRaises(StudyError):e.extract_json('not JSON')
    def test_mock_parser(self):self.assertEqual(len(e.validate_mock(json.dumps(QUIZ))),3)
    def test_mock_invalid_answers(self):
        payload=json.loads(json.dumps(QUIZ));payload['questions'][0]['answer']='Q'
        with self.assertRaises(StudyError):e.validate_mock(json.dumps(payload))
    def test_mock_wrong_count(self):
        with self.assertRaises(StudyError):e.validate_mock('{"questions":[]}')
    def test_mock_grade(self):
        score,lines,mistakes=e.grade_mock(e.validate_mock(json.dumps(QUIZ)),'A B C')
        self.assertEqual(score,1);self.assertEqual(len(mistakes),2)
    def test_mock_grade_requires_three(self):
        with self.assertRaises(StudyError):e.grade_mock(e.validate_mock(json.dumps(QUIZ)),'A B')
    def test_cards(self):self.assertEqual(len(e.validate_cards(json.dumps(CARDS))),2)
    def test_cards_duplicates(self):
        with self.assertRaises(StudyError):e.validate_cards(json.dumps({'cards':[CARDS['cards'][0]]*2}))
    def test_roadmap(self):self.assertEqual(len(e.roadmap(7,'Physics',60,['Review laws'])),7)
    def test_roadmap_invalid(self):
        with self.assertRaises(StudyError):e.roadmap(31,'Physics',60)
    def test_summary(self):self.assertIn('Cells',e.summary_from_evidence(SOURCES))
    def test_compare_two_sources(self):self.assertIn('Shared terms',e.compare_passages(SOURCES))
    def test_compare_requires_two(self):
        with self.assertRaises(StudyError):e.compare_passages(SOURCES[:1])
    def test_check_does_not_claim_truth(self):self.assertIn('NOT proof',e.claim_support('Cells contain genetic material',SOURCES))
    def test_empty_evidence(self):self.assertIn('NOT verified',e.claim_support('Cells contain genetic material',[]))

class GeminiTests(unittest.TestCase):
    def test_chat_with_memory(self):
        p=g.build_prompt('chat',{'question':'What are cells?','evidence':SOURCES,
                                  'history':[{'question':'What is biology?','answer':'Life science'}]})
        self.assertIn('Previous question: What is biology?',p)
    def test_explain_tamil(self):
        self.assertIn('in Tamil',g.build_prompt('explain',{'question':'Describe cells','evidence':SOURCES,'language':'ta'}))
    def test_viva_one(self):self.assertIn('exactly ONE',g.build_prompt('viva',{'question':'Cells','evidence':SOURCES}))
    def test_mock_json(self):self.assertIn('valid JSON',g.build_prompt('mock',{'question':'Cells','evidence':SOURCES}))
    def test_cards_json(self):self.assertIn('ONLY JSON',g.build_prompt('cards',{'question':'Cells','evidence':SOURCES}))
    def test_compare(self):self.assertIn('Compare source',g.build_prompt('compare',{'question':'Cells','evidence':SOURCES}))
    def test_rubric_no_notes(self):
        p=g.build_prompt('rubric',{'question':'Define cell','answer':'A cell is alive.','criteria':'5 marks'})
        self.assertIn('NOT an official score',p)
    def test_missing_sources(self):
        with self.assertRaises(g.AIError):g.build_prompt('chat',{'question':'Hello','evidence':[]})
    def test_source_clamp(self):
        p=g.build_prompt('chat',{'question':'What are cells?','evidence':[{**SOURCES[0],'body':'X'*40000}]})
        self.assertLessEqual(p.count('X'),451)
    def test_no_mystery_action(self):
        with self.assertRaises(g.AIError):g.build_prompt('admin',{})
    def test_provider_reuses_v10_quota(self):
        fake=types.ModuleType('gemini_ai_studio_v59')
        fake.read_api_key=lambda:'test-dummy'
        class Client:
            def __init__(self,*a,**k):pass
            def generate(self,*a,**k):return 'Test answer [S1]'
        fake.GeminiClient=Client
        with patch.dict(sys.modules,{'gemini_ai_studio_v59':fake}),\
             patch.object(g,'validate') as v,patch.object(g,'claim_quota') as q:
            self.assertIn('[S1]',g.generate(123,'chat',{'question':'Cells','evidence':SOURCES}))
            v.assert_called_once_with(123);q.assert_called_once_with(123)
    def test_no_external_call_without_validation(self):
        with patch.object(g,'validate',side_effect=StudyError('Not verified')),patch.object(g,'claim_quota') as quota:
            with self.assertRaises(StudyError):g.generate(8,'chat',{'question':'Cells','evidence':SOURCES})
            quota.assert_not_called()
    def test_provider_failure_safe(self):
        fake=types.ModuleType('gemini_ai_studio_v59');fake.read_api_key=lambda:'secret'
        class Client:
            def __init__(self,*a,**k):pass
            def generate(self,*a,**k):raise RuntimeError('Internal provider secret 123')
        fake.GeminiClient=Client
        with patch.dict(sys.modules,{'gemini_ai_studio_v59':fake}),patch.object(g,'validate'),patch.object(g,'claim_quota'):
            with self.assertRaisesRegex(StudyError,'could not complete') as ctx:
                g.generate(123,'chat',{'question':'Cells','evidence':SOURCES})
            self.assertNotIn('secret',str(ctx.exception))

class FakeResponse:
    def __init__(self,data=None,count=None):self.data=data or [];self.count=count
    def execute(self):return self
class Chain:
    def __init__(self,database,table):self.db=database;self.table=table;self.data=[]
    def __getattr__(self,name):
        def call(*a,**kw):
            self.db.calls.append((self.table,name,a,kw))
            if name=='insert':self.data=a[0] if isinstance(a[0],list) else [a[0]]
            if name=='select':self.data=self.db.responses.get(self.table,[])
            if name=='rpc':self.data=self.db.responses.get('rpc',[])
            return self
        return call
    def execute(self):return FakeResponse(self.data,len(self.data))
class FakeDB:
    def __init__(self,responses=None):self.calls=[];self.responses=responses or {}
    def table(self,name):return Chain(self,name)
    def rpc(self,name,payload):
        self.calls.append(('rpc',name,payload))
        r=Chain(self,'rpc');r.data=self.responses.get('rpc','joined');return r

class StoreTests(unittest.TestCase):
    def test_chat_owner_scoped(self):
        db=FakeDB({'v101_chat_turns':[{'question':'Q','answer':'A'}]})
        s.chat_history(15,db)
        self.assertIn(('v101_chat_turns','eq',('user_id',15),{}),db.calls)
    def test_append_chat(self):
        db=FakeDB();s.append_chat(15,'Q','A',db)
        self.assertIn(('v101_chat_turns','insert',({'id':unittest.mock.ANY,'user_id':15,'question':'Q','answer':'A'},),{}),db.calls)
    def test_forget_owner_scoped(self):
        db=FakeDB();s.forget_chat(15,db)
        self.assertIn(('v101_chat_turns','eq',('user_id',15),{}),db.calls)
    def test_plan_saved(self):
        db=FakeDB();s.create_plan(15,'Chemistry',7,40,['Day 1'],db)
        self.assertTrue(any(x[1]=='upsert' for x in db.calls))
    def test_cards_reuse_existing_table(self):
        db=FakeDB();self.assertEqual(s.save_cards(15,CARDS['cards'],db),2)
        self.assertTrue(any(x[0]=='flashcards' and x[1]=='insert' for x in db.calls))
    def test_store_mistakes(self):
        db=FakeDB();s.save_mistakes(15,[{'question':'What?','correct_answer':'A'}],db)
        self.assertTrue(any(x[0]=='v101_mock_mistakes' for x in db.calls))
    def test_join_room_rpc(self):
        db=FakeDB({'rpc':'joined'})
        self.assertEqual(s.join_room(15,'Abc123456789',db),'joined')
    def test_join_room_invalid_result(self):
        db=FakeDB({'rpc':'admin'})
        with self.assertRaises(StudyError):s.join_room(15,'Abc123456789',db)
    def test_room_scope(self):
        db=FakeDB()
        self.assertIsNone(s.room_for_user(15,db))
    def test_no_room_leave(self):
        with self.assertRaises(StudyError):s.leave_room(15,FakeDB())

class M:pass
class FakeBot:
    def __init__(self):self.command_handlers={};self.other_handlers=[];self.sent=[]
    def message_handler(self,commands=None,**kwargs):
        def dec(fn):
            if commands:
                for c in commands:self.command_handlers[c]=fn
            else:self.other_handlers.append((kwargs,fn))
            return fn
        return dec
    def send_message(self,chat,msg,**kwargs):self.sent.append((chat,msg))
    def send_audio(self,chat,audio,**kwargs):self.sent.append((chat,'audio'))
    def call(self,cmd,uid=15):
        m=M();m.chat=M();m.chat.type='private';m.chat.id=uid;m.from_user=M();m.from_user.id=uid;m.text=cmd
        self.command_handlers[cmd.split(' ',1)[0][1:]](m);return self.sent[-1][1]

class BotTests(unittest.TestCase):
    def setUp(self):
        self.bot=FakeBot();b.register_v101_handlers(self.bot)
        self.gate=patch.object(b,'allowed',return_value=True);self.gate.start();self.addCleanup(self.gate.stop)
        self.addCleanup(lambda:b.cancel(15))
    def test_all_12_in_menu(self):
        result=self.bot.call('/v101')
        self.assertIn('12 features',result)
        for n in range(1,13):self.assertIn(str(n)+' ',result)
    def test_cannot_access_without_verified_adult(self):
        with patch.object(b,'allowed',return_value=False):
            self.assertIn('unavailable',self.bot.call('/v101'))
    def test_error_if_no_docs(self):
        with patch.object(b,'find_evidence',return_value=[]):self.assertIn('No matching',self.bot.call('/v101chat What is gravity?'))
    def test_queue_ai_requires_consent(self):
        with patch.object(b,'find_evidence',return_value=SOURCES),patch.object(s,'chat_history',return_value=[]),patch.object(ai,'validate'):
            self.assertIn('consent',self.bot.call('/v101chat What are cells?'))
            self.assertEqual(b.current(15)['kind'],'gemini')
    def test_no_ai_without_consent(self):
        with patch.object(ai,'generate') as generate:
            self.assertIn('No pending',self.bot.call('/v101confirm'))
            generate.assert_not_called()
    def test_ai_one_shot(self):
        b.stage(15,{'kind':'gemini','action':'chat','payload':{'question':'Cells','evidence':SOURCES}})
        with patch.object(ai,'generate',return_value='Cells are living units [S1]'),\
             patch.object(s,'append_chat') as append:
            self.bot.call('/v101confirm');self.bot.call('/v101confirm')
            append.assert_called_once();self.assertIn('No pending',self.bot.sent[-1][1])
    def test_mock_questions(self):
        b.stage(15,{'kind':'gemini','action':'mock','payload':{'question':'Cells','evidence':SOURCES}})
        with patch.object(ai,'generate',return_value=json.dumps(QUIZ)):
            self.assertIn('3-question',self.bot.call('/v101confirm'))
            self.assertEqual(b.current(15)['kind'],'mock')
    def test_mock_grade(self):
        b.stage(15,{'kind':'mock','questions':e.validate_mock(json.dumps(QUIZ))})
        with patch.object(s,'save_mistakes'):
            self.assertIn('1/3',self.bot.call('/v101submit A B C'))
    def test_cards_store_preview(self):
        b.stage(15,{'kind':'gemini','action':'cards','payload':{'question':'Cells','evidence':SOURCES}})
        with patch.object(ai,'generate',return_value=json.dumps(CARDS)):
            self.assertIn('/v101cardsave',self.bot.call('/v101confirm'))
    def test_viva_feedback_stage(self):
        b.stage(15,{'kind':'viva','question':'What is a cell?','evidence':SOURCES})
        with patch.object(ai,'validate'):
            self.assertIn('consent',self.bot.call('/v101answer Cells are living units'))
    def test_ocr_requires_consent(self):
        self.assertIn('No OCR document',self.bot.call('/v101ocrconfirm'))
    def test_audio_requires_consent(self):
        self.assertIn('No audio lesson',self.bot.call('/v101audioconfirm'))
    def test_room_join_short_code_rejected(self):
        self.assertIn('Usage',self.bot.call('/v101roomjoin abc'))
    def test_offline_compare(self):
        with patch.object(s,'compare_rows',return_value=SOURCES):
            self.assertIn('Source comparison',self.bot.call('/v101compare biology'))
    def test_source_checker_caution(self):
        with patch.object(b,'find_evidence',return_value=SOURCES):
            self.assertIn('NOT proof',self.bot.call('/v101check Cells contain genetic material'))
    def test_cancel_discards_state(self):
        b.stage(15,{'kind':'gemini','action':'chat'})
        self.bot.call('/v101cancel');self.assertIsNone(b.current(15))
    def test_gemini_offline_access_denied(self):
        self.gate.stop()
        with patch.dict(os.environ,{'V101_ENABLED':'true'}),patch('v10_bot.authorized',return_value=True),\
             patch('v10_gemini.adult_eligible',return_value=False):
            self.assertFalse(b.allowed(15))

class InstallerTests(unittest.TestCase):
    def fixture(self,root):
        (root/'main.py').write_text('register_v10_handlers(bot)\n\nfrom v9_bot import register_v9_handlers\n',encoding='utf-8')
        (root/'ui_v57.py').write_text('ALL_UI_BUTTONS = set()\n',encoding='utf-8')
        (root/'navigation.py').write_text('GLOBAL_BUTTONS.add("📝 Text → PDF")\n',encoding='utf-8')
    def test_check_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root);prior=(root/'main.py').read_bytes()
            self.assertEqual(len(integrate(root,output=lambda *_:None)),3)
            self.assertEqual(prior,(root/'main.py').read_bytes())
    def test_apply_then_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            self.assertEqual(len(integrate(root,apply=True,output=lambda *_:None)),3)
            self.assertEqual(integrate(root,apply=True,output=lambda *_:None),[])
            self.assertEqual(len(list(root.glob('V101_BACKUP_*'))),1)
    def test_missing_anchor_refused(self):
        with self.assertRaises(ValueError):transform('main.py','no v10')
    def test_existing_registration_unchanged(self):
        old='register_v101_handlers(bot)\n';self.assertEqual(transform('main.py',old),old)
    def test_ui_is_env_guarded(self):
        self.assertIn('V101_ENABLED',transform('ui_v57.py','ALL_UI_BUTTONS ='))

if __name__=='__main__':unittest.main()
