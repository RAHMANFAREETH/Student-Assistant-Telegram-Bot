"""Offline V10 tests. No live Telegram, Supabase or AI calls."""
import io,os,sys,unittest, tempfile, importlib,types
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone,timedelta

from v10_engine import (StudyError,words,split_pages,rank_chunks,revise_plan,
                        viva_prompt,viva_feedback,next_schedule,due)
import v10_store as store
from INSTALL_V10_ADVANCED_STUDY import transform,integrate

NOW=datetime(2026,10,31,12,tzinfo=timezone.utc)


class EngineTests(unittest.TestCase):
    def test_unicode_tokenization(self):self.assertIn('தமிழ்',words('தமிழ் பாடம்'))
    def test_short_upload_rejected(self):
        with self.assertRaises(StudyError):split_pages([(1,'a')])
    def test_page_preserved(self):self.assertEqual(split_pages([(4,'x'*50)])[0]['page_number'],4)
    def test_split_is_bounded(self):
        x=split_pages([(1,'abcdef ' * 10000)])
        self.assertLessEqual(len(x),40)
        self.assertTrue(all(len(z['body'])<=1300 for z in x))
        self.assertLessEqual(sum(len(z['body']) for z in x),45000)
    def test_invalid_page(self):
        with self.assertRaises(StudyError):split_pages([(0,'x'*50)])
    def test_ctrl_chars_removed(self):self.assertNotIn('\0',split_pages([(1,'abc\x00 '*20)])[0]['body'])
    def test_ranked_source_evidence(self):
        chunks=[{'body':'gravity mass orbit forces and the solar system','page_number':4,'title':'Physics'},
                {'body':'photosynthesis plants green and sunlight','page_number':1,'title':'Biology'}]
        x=rank_chunks(chunks,'Explain gravity orbit')
        self.assertEqual(x[0]['title'],'Physics')
        self.assertEqual(x[0]['page_number'],4)
    def test_search_cannot_hallucinate(self):self.assertEqual(rank_chunks([{'body':'hydrogen oxygen water'}],'elephant'),[])
    def test_search_question_length(self):
        with self.assertRaises(StudyError):rank_chunks([], 'x')
    def test_search_limit(self):
        self.assertEqual(len(rank_chunks([{'body':'gravity'}]*100,'gravity',limit=99)),6)
    def test_coach_prioritizes_errors(self):
        plan=revise_plan([{'topic':'Algebra','mastered':False}],[{'title':'History','completed':False}], [{'question':'Fractions','wrong_count':3,'correct_count':0}])
        self.assertIn('Algebra',plan[0]);self.assertIn('Fractions',plan[1])
    def test_coach_skips_mastered(self):self.assertEqual(revise_plan([{'topic':'done','mastered':True}],[{'title':'done','completed':True}],[]),[])
    def test_viva_from_mistakes(self):
        p=viva_prompt('Algebra',[{'topic':'algebra','question':'Solve x','answer':'x equals two','mastered':False}],[])
        self.assertEqual(p['source'],'Your Mistake Notebook')
    def test_viva_fallback_to_document(self):
        p=viva_prompt('Gravity',[],[{'body':'gravity pulls mass','title':'Phys','page_number':3}])
        self.assertIn('page 3',p['source'])
    def test_viva_no_source(self):
        with self.assertRaises(StudyError):viva_prompt('Gravity',[],[])
    def test_viva_feedback_caution(self):self.assertIn('keyword-based',viva_feedback('gravity pulls objects','gravity pulls objects')['disclaimer'])
    def test_viva_answer_too_short(self):
        with self.assertRaises(StudyError):viva_feedback('yes','reference')
    def test_schedule_first_rating(self):self.assertEqual(next_schedule(None,'good',NOW)['interval_days'],1)
    def test_schedule_easy(self):self.assertEqual(next_schedule(None,'easy',NOW)['interval_days'],3)
    def test_schedule_again(self):self.assertEqual(next_schedule({'interval_days':20,'repetitions':4},'again',NOW)['repetitions'],0)
    def test_schedule_cap(self):self.assertEqual(next_schedule({'interval_days':180,'repetitions':4},'easy',NOW)['interval_days'],180)
    def test_schedule_invalid(self):
        with self.assertRaises(StudyError):next_schedule({},'excellent',NOW)
    def test_due_unscheduled(self):self.assertTrue(due(NOW,None))
    def test_due_future(self):self.assertFalse(due(NOW,{'due_at':(NOW+timedelta(days=2)).isoformat()}))
    def test_due_past(self):self.assertTrue(due(NOW,{'due_at':(NOW-timedelta(seconds=1)).isoformat()}))
    def test_due_malformed_fails_closed(self):self.assertFalse(due(NOW,{'due_at':'not time'}))


class FakeResult:
    def __init__(self,data=None):self.data=data or []

class FakeQuery:
    def __init__(self,table,db):self.table=table;self.db=db;self.filters=[];self.mode='select';self.payload=None
    def select(self,*a,**kw):return self
    def eq(self,k,v):self.filters.append((k,v));return self
    def limit(self,n):self.limit_n=n;return self
    def order(self,*a,**kw):return self
    def insert(self,data):self.mode='insert';self.payload=data;return self
    def delete(self):self.mode='delete';return self
    def upsert(self,data,**kw):self.mode='upsert';self.payload=data;return self
    def execute(self):
        self.db.operations.append((self.table,self.mode,list(self.filters)))
        if self.db.fail_insert and self.mode=='insert' and self.table=='v10_document_chunks':
            raise RuntimeError('simulated database outage')
        if self.mode in ('insert','upsert'):
            data=self.payload if isinstance(self.payload,list) else [self.payload]
            self.db.tables[self.table].extend(data)
            return FakeResult(data)
        data=self.db.tables[self.table]
        for k,v in self.filters:data=[r for r in data if r.get(k)==v]
        if self.mode=='delete':
            for r in data:self.db.tables[self.table].remove(r)
            if self.table=='v10_documents':
                ids={r['id'] for r in data}
                self.db.tables['v10_document_chunks']=[x for x in self.db.tables['v10_document_chunks'] if x['document_id'] not in ids]
            return FakeResult(data)
        if hasattr(self,'limit_n'):data=data[:self.limit_n]
        return FakeResult(data)

class FakeDB:
    def __init__(self):
        self.tables={k:[] for k in ('v10_documents','v10_document_chunks','v10_card_schedule','flashcards','v9_mistakes','v9_syllabus_topics')}
        self.operations=[];self.fail_insert=False
    def table(self,t):return FakeQuery(t,self)


class StoreTests(unittest.TestCase):
    def setUp(self):self.db=FakeDB()
    def test_save_and_find_with_citations(self):
        a=store.save_document(100,'notes.txt',[(1,'Gravity and mass are related phenomena in physics.'*2)],self.db)
        matches=store.find_evidence(100,'gravity mass',self.db)
        self.assertEqual(matches[0]['title'],'notes');self.assertEqual(matches[0]['page_number'],1)
        self.assertEqual(a['chunks'],1)
    def test_multiuser_isolation(self):
        store.save_document(200,'private.txt',[(1,'Private chemistry information and bonding.'*2)],self.db)
        self.assertEqual(store.find_evidence(100,'chemistry bonding',self.db),[])
        self.assertFalse(store.remove_document(100,self.db.tables['v10_documents'][0]['id'],self.db))
    def test_limit_documents(self):
        for i in range(6):store.save_document(100,f'n{i}.txt',[(1,'a long paragraph with enough readable text')],self.db)
        with self.assertRaises(StudyError):store.save_document(100,'n6.txt',[(1,'a long paragraph with enough readable text')],self.db)
    def test_bad_extension(self):
        with self.assertRaises(StudyError):store.save_document(100,'x.exe',[(1,'a long paragraph with enough readable text')],self.db)
    def test_partial_insert_rolled_back(self):
        self.db.fail_insert=True
        with self.assertRaises(RuntimeError):store.save_document(100,'bad.txt',[(1,'a long paragraph with enough readable text')],self.db)
        self.assertEqual(self.db.tables['v10_documents'],[])
    def test_delete_cascade(self):
        saved=store.save_document(100,'hi.txt',[(1,'gravity and planetary orbit science.'*2)],self.db)
        self.assertTrue(store.remove_document(100,saved['id'],self.db))
        self.assertFalse(self.db.tables['v10_document_chunks'])
    def test_coach_user_scope(self):
        self.db.tables['v9_mistakes']=[{'user_id':200,'topic':'Forbidden','mastered':False},{'user_id':100,'topic':'Allowed','mastered':False}]
        self.assertIn('Allowed',store.coach(100,self.db)[0]);self.assertNotIn('Forbidden',store.coach(100,self.db)[0])
    def test_due_user_scope(self):
        self.db.tables['flashcards']=[{'id':1,'user_id':100,'question':'Q1','answer':'A1'},{'id':2,'user_id':200,'question':'Q2','answer':'A2'}]
        self.assertEqual(len(store.due_cards(100,self.db,now=NOW)),1)
    def test_get_card_owner_check(self):
        self.db.tables['flashcards']=[{'id':2,'user_id':200,'question':'Secret','answer':'Hidden'}]
        self.assertIsNone(store.get_card(100,2,self.db))
    def test_rate_card_owner_check(self):
        self.db.tables['flashcards']=[{'id':2,'user_id':200,'question':'Secret','answer':'Hidden'}]
        with self.assertRaises(StudyError):store.rate_card(100,2,'good',self.db,now=NOW)
    def test_rate_card_schedule(self):
        self.db.tables['flashcards']=[{'id':2,'user_id':100,'question':'Q','answer':'A'}]
        payload=store.rate_card(100,2,'hard',self.db,now=NOW)
        self.assertEqual(payload['interval_days'],1);self.assertEqual(payload['user_id'],100)


class InstallerTests(unittest.TestCase):
    def fixture(self,dir):
        Path(dir,'main.py').write_text('register_v93_reliability_handlers(bot)\n\nfrom v9_bot import register_v9_handlers\n',encoding='utf-8')
        Path(dir,'ui_v57.py').write_text('CATEGORY_FEATURES = {}\nALL_UI_BUTTONS = {}\n',encoding='utf-8')
        Path(dir,'navigation.py').write_text('GLOBAL_BUTTONS = set()\nGLOBAL_BUTTONS.add("📝 Text → PDF")\n',encoding='utf-8')
    def test_dry_run_is_readonly(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.fixture(tmp);before=Path(tmp,'main.py').read_bytes()
            changed=integrate(tmp,False,output=lambda _:None)
            self.assertEqual(len(changed),3)
            self.assertEqual(Path(tmp,'main.py').read_bytes(),before)
    def test_apply_idempotent_and_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.fixture(tmp)
            self.assertEqual(len(integrate(tmp,True,output=lambda _:None)),3)
            self.assertEqual(integrate(tmp,True,output=lambda _:None),[])
            self.assertEqual(len(list(Path(tmp).glob('V10_BACKUP_*'))),1)
    def test_routing_order(self):
        src='register_v93_reliability_handlers(bot)\n\nfrom v9_bot import register_v9_handlers\n'
        changed=transform('main.py',src)
        self.assertLess(changed.index('register_v93_reliability_handlers(bot)'),changed.index('register_v10_handlers(bot)'))
        self.assertLess(changed.index('register_v10_handlers(bot)'),changed.index('register_v9_handlers'))
    def test_old_version_fallback(self):
        src='from v9_bot import register_v9_handlers\n'
        self.assertIn('register_v10_handlers(bot)',transform('main.py',src))
    def test_unknown_anchor_refused(self):
        with self.assertRaises(ValueError):transform('main.py','old_bot()\n')
    def test_line_endings_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.fixture(tmp)
            for f in ('main.py','ui_v57.py','navigation.py'):
                p=Path(tmp,f);p.write_bytes(p.read_bytes().replace(b'\n',b'\r\n'))
            integrate(tmp,True,output=lambda _:None)
            self.assertNotIn(b'\n',Path(tmp,'main.py').read_bytes().replace(b'\r\n',b''))
    def test_source_has_v10_toggle(self):
        self.assertIn('V10_ENABLED',transform('ui_v57.py','ALL_UI_BUTTONS = set()'))


class BotTests(unittest.TestCase):
    def setUp(self):
        self.oldtele=sys.modules.get('telebot')
        self.oldv8=sys.modules.get('v8_bot')
        self.tele=types.ModuleType('telebot')
        t=types.SimpleNamespace()
        class Button:
            def __init__(self,*a,**k):pass
        class Markup:
            def __init__(self,*a,**k):self.buttons=[]
            def add(self,*a):self.buttons.extend(a)
        t.InlineKeyboardButton=Button;t.InlineKeyboardMarkup=Markup
        self.tele.types=t;sys.modules['telebot']=self.tele
        self.v8=types.ModuleType('v8_bot');self.v8.allowed=lambda uid:True
        sys.modules['v8_bot']=self.v8
        import v10_bot
        self.botmod=v10_bot
        self.patcher=patch.dict(os.environ,{'V10_ENABLED':'true','V10_GEMINI_ENABLED':'false'})
        self.patcher.start();self.bot=FakeBot();v10_bot.register_v10_handlers(self.bot)
        self.uid=100
    def tearDown(self):
        self.patcher.stop();self.botmod.STATE.clear()
        if self.oldtele is None:sys.modules.pop('telebot',None)
        else:sys.modules['telebot']=self.oldtele
        if self.oldv8 is None:sys.modules.pop('v8_bot',None)
        else:sys.modules['v8_bot']=self.oldv8
    def m(self,cmd,uid=100,chat='private'):
        return types.SimpleNamespace(text=cmd,from_user=types.SimpleNamespace(id=uid),chat=types.SimpleNamespace(type=chat,id=uid if chat=='private' else -100))
    def test_hub_authorized(self):
        self.bot.run('v10',self.m('/v10'))
        self.assertIn('Learning Lab',self.bot.sent[-1][1])
    def test_disabled_gate(self):
        with patch.dict(os.environ,{'V10_ENABLED':'false'}):
            self.bot.run('v10',self.m('/v10'))
        self.assertIn('disabled',self.bot.sent[-1][1])
    def test_private_gate(self):
        self.bot.run('v10',self.m('/v10',chat='group'))
        self.assertIn('private',self.bot.sent[-1][1])
    def test_unapproved_gate(self):
        self.v8.allowed=lambda uid:False
        self.bot.run('v10',self.m('/v10'))
        self.assertIn('not active',self.bot.sent[-1][1])
    def test_ai_off_by_default(self):
        self.bot.run('v10askai',self.m('/v10askai gravity'))
        self.assertIn('disabled',self.bot.sent[-1][1])
    def test_save_requires_preview(self):
        self.bot.run('v10save',self.m('/v10save'))
        self.assertIn('No prepared upload',self.bot.sent[-1][1])
    def test_deletion_requires_pending_session(self):
        self.bot.run('v10confirmdelete',self.m('/v10confirmdelete'))
        self.assertIn('No document deletion',self.bot.sent[-1][1])
    def test_review_requires_reveal(self):
        self.bot.run('v10rate',self.m('/v10rate easy'))
        self.assertIn('Reveal',self.bot.sent[-1][1])
    def test_cancel_clears_session(self):
        self.botmod._set(100,{'kind':'upload'})
        self.bot.run('v10cancel',self.m('/v10cancel'))
        self.assertIsNone(self.botmod._get(100))
    def test_expired_state(self):
        self.botmod._set(100,{'kind':'upload'})
        self.botmod.STATE[100]['ts']-=900
        self.assertIsNone(self.botmod._get(100))
    def test_ai_requires_single_use_confirmation(self):
        evidence=[{'title':'Physics','page_number':3,'body':'Gravity pulls masses toward Earth.'}]
        with patch.dict(os.environ,{'V10_GEMINI_ENABLED':'true'}), \
             patch.object(self.botmod,'find_evidence',return_value=evidence), \
             patch.object(self.botmod,'gemini_validate') as validate, \
             patch.object(self.botmod,'gemini_generate',return_value='Gravity [S1]') as generate:
            self.bot.run('v10askai',self.m('/v10askai gravity'))
            self.assertIn('consent',self.bot.sent[-1][1].lower())
            generate.assert_not_called()
            self.bot.run('v10confirm_ai',self.m('/v10confirm_ai'))
            self.assertIn('Physics, page 3',self.bot.sent[-1][1])
            generate.assert_called_once()
            self.bot.run('v10confirm_ai',self.m('/v10confirm_ai'))
            self.assertIn('No pending Gemini',self.bot.sent[-1][1])

    def test_ai_viva_one_time_consent(self):
        evidence=[{'title':'Physics','page_number':3,'body':'Gravity pulls masses toward Earth.'}]
        with patch.dict(os.environ,{'V10_GEMINI_ENABLED':'true'}), \
             patch.object(self.botmod,'find_evidence',return_value=evidence), \
             patch.object(self.botmod,'gemini_validate'), \
             patch.object(self.botmod,'gemini_generate',return_value='Explain gravity using an example.') as generate:
            self.bot.run('v10vivaai',self.m('/v10vivaai gravity'))
            generate.assert_not_called()
            self.bot.run('v10confirm_ai',self.m('/v10confirm_ai'))
            self.assertIn('Explain gravity',self.bot.sent[-1][1])
            self.assertEqual(self.botmod._get(100)['kind'],'viva')

    def test_ai_coach_one_time_consent(self):
        with patch.dict(os.environ,{'V10_GEMINI_ENABLED':'true'}), \
             patch.object(self.botmod,'coach',return_value=['Revise algebra mistakes']), \
             patch.object(self.botmod,'gemini_validate'), \
             patch.object(self.botmod,'gemini_generate',return_value='Study algebra every morning.') as generate:
            self.bot.run('v10coachai',self.m('/v10coachai'))
            generate.assert_not_called()
            self.bot.run('v10confirm_ai',self.m('/v10confirm_ai'))
            self.assertIn('Study algebra',self.bot.sent[-1][1])

    def test_review_reveal_then_rating(self):
        with patch.object(self.botmod,'get_card',return_value={'id':2,'question':'Q','answer':'A'}), \
             patch.object(self.botmod,'rate_card',return_value={'interval_days':3}):
            self.bot.run('v10card',self.m('/v10card 2'))
            self.bot.run('v10rate',self.m('/v10rate easy'))
            self.assertIn('Reveal',self.bot.sent[-1][1])
            self.bot.run('v10reveal',self.m('/v10reveal'))
            self.bot.run('v10rate',self.m('/v10rate easy'))
            self.assertIn('3 day',self.bot.sent[-1][1])
            self.assertIsNone(self.botmod._get(100))
    def test_viva_expires_after_answer(self):
        self.botmod._set(100,{'kind':'viva','prompt':{'question':'What is gravity?',
            'reference':'Gravity pulls objects toward Earth','source':'Physics'}})
        self.bot.run('v10answer',self.m('/v10answer Gravity pulls things toward Earth'))
        self.assertIn('keyword-based',self.bot.sent[-1][1])
        self.assertIsNone(self.botmod._get(100))
    def test_one_user_cannot_read_others_state(self):
        self.botmod._set(100,{'kind':'delete','id':'x'})
        self.assertIsNone(self.botmod._get(200))


class FakeBot:
    def __init__(self):self.handlers={};self.callbacks=[];self.sent=[]
    def message_handler(self,commands=None,**kw):
        def wrap(func):
            if commands:
                for cmd in commands:self.handlers[cmd]=func
            return func
        return wrap
    def callback_query_handler(self,**kw):
        def wrap(func):self.callbacks.append(func);return func
        return wrap
    def send_message(self,uid,text,**kw):self.sent.append((uid,text))
    def run(self,cmd,msg):return self.handlers[cmd](msg)


if __name__=='__main__':unittest.main()
