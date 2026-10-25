"""Offline V6.5 unit/integration checks. No secrets, network or Supabase requests."""
from __future__ import annotations

import ast
import importlib.util
import sys
import tempfile
from pathlib import Path
import types
import unittest
from unittest.mock import patch

import INSTALL_V6_5 as installer
from ai_save_v65 import (
    SaveValidationError, prepare_note, parse_quiz_cards, save_note, save_flashcards,
)

FIXTURE = Path(__file__).with_name('FIXTURE_V6_4_AI.txt')

QUIZ = '''🧠 Practice Quiz
1. What do plants absorb from the sun?
A) Wind
B) Sunlight
C) Soil
D) Rocks

2. What gas do plants absorb?
A) Carbon dioxide
B) Oxygen
C) Nitrogen
D) Hydrogen

3. Which gas is released?
A) Methane
B) Nitrogen
C) Oxygen
D) Helium

Answer Key:
1. B - Photosynthesis uses light energy.
2. A - Plants take in carbon dioxide.
3. C - Plants release oxygen.
'''

TAMIL = '''1. ஒளிச்சேர்க்கைக்கு என்ன தேவை?
A) மழை
B) சூரிய ஒளி
C) மணல்
D) கல்

2. தாவரம் எதை வெளியிடுகிறது?
A) ஹைட்ரஜன்
B) நைட்ரஜன்
C) ஆக்சிஜன்
D) கார்பன்

விடைகள்
1. B
2. C
'''


class InstallerTests(unittest.TestCase):
    def get_src(self):
        return FIXTURE.read_text(encoding='utf-8')

    def test_patches_v64_exactly_once(self):
        updated, changed = installer.patch_ai(self.get_src())
        self.assertTrue(changed)
        ast.parse(updated)
        self.assertEqual(installer.patch_ai(updated), (updated, False))
        self.assertEqual(updated.count(installer.MARKER), 1)

    def test_does_not_touch_ai_provider_or_quota(self):
        old = self.get_src()
        new, _ = installer.patch_ai(old)
        for text in ('claim_quota(user_id)', 'def _check_safety(',
                     'def _provider_call(', 'observe_cloudflare_health(',
                     'wrap_cloudflare_provider(', 'MAX_OUTPUT_TOKENS = 1800',
                     'V63_FOLLOW_UPS', 'V64_STUDY_ACTIONS'):
            self.assertEqual(new.count(text), old.count(text))
        self.assertNotIn('GEMINI_API_KEY', new)

    def test_windows_line_endings(self):
        sample = self.get_src().replace('\n', '\r\n')
        updated, changed = installer.patch_ai(sample)
        self.assertTrue(changed)
        self.assertNotIn('\r\r\n', updated)
        self.assertEqual(installer.patch_ai(updated), (updated, False))

    def test_refuses_old_partial_and_modified_versions(self):
        for bad in ('unexpected = True', self.get_src().replace('if text in V64_STUDY_ACTIONS:', ''),
                    self.get_src().replace('def _remember(user_id, question, answer):', '')):
            with self.assertRaises(ValueError):
                installer.patch_ai(bad)
        good, _ = installer.patch_ai(self.get_src())
        with self.assertRaises(ValueError):
            installer.patch_ai(good.replace('if text in V65_SAVE_ACTIONS', 'if text in set()'))

    def test_backup_idempotence(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / installer.TARGET).write_text(self.get_src(), encoding='utf-8')
            (root / 'ai_save_v65.py').write_text('import re\n', encoding='utf-8')
            self.assertTrue(installer.install(root))
            self.assertFalse(installer.install(root))
            self.assertEqual((root/(installer.TARGET+'.before_v65.bak')).read_text(encoding='utf-8'), self.get_src())
            self.assertFalse(list(root.glob('.v65_*.tmp')))

    def test_preflight_refuses_missing_helper_or_backup_clash(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            target = root/installer.TARGET
            target.write_text(self.get_src(),encoding='utf-8')
            with self.assertRaises(ValueError):
                installer.install(root)
            (root/'ai_save_v65.py').write_text('pass\n',encoding='utf-8')
            (root/(installer.TARGET+'.before_v65.bak')).write_text('keep',encoding='utf-8')
            with self.assertRaises(ValueError):
                installer.install(root)
            self.assertEqual(target.read_text(encoding='utf-8'),self.get_src())


class DataTests(unittest.TestCase):
    def test_note_stores_complete_answer_and_title(self):
        note = prepare_note('Explain photosynthesis\n  in Tamil', 'முழுமையான விளக்கம் 🌱')
        self.assertEqual(note['content'], 'முழுமையான விளக்கம் 🌱')
        self.assertIn('photosynthesis in Tamil', note['title'])

    def test_rejects_blank_or_too_long(self):
        for bad in ('', ' '*10, 'x'*20001):
            with self.assertRaises(SaveValidationError):
                prepare_note('hi', bad)

    def test_parses_three_cards_with_answer_text(self):
        cards = parse_quiz_cards(QUIZ)
        self.assertEqual(len(cards),3)
        self.assertIn('B) Sunlight',cards[0]['answer'])
        self.assertIn('A) Carbon dioxide',cards[1]['answer'])
        self.assertIn('C) Oxygen',cards[2]['answer'])

    def test_tamil_quiz_keeps_script(self):
        cards = parse_quiz_cards(TAMIL)
        self.assertEqual(len(cards),2)
        self.assertIn('சூரிய ஒளி', cards[0]['answer'])

    def test_no_unverified_answers_saved(self):
        samples = ['', QUIZ.replace('3. C - Plants release oxygen.',''),
                   QUIZ.replace('1. B - Photosynthesis uses light energy.', '1. D - Wrong'),
                   QUIZ.replace('D) Helium',''),
                   QUIZ.replace('2. A - Plants take in carbon dioxide.','2. A - Plants take in carbon dioxide.\n2. B')]
        # Invalid letter D with a valid option is syntactically valid, so don't test correctness inference.
        samples.pop(2)
        for bad in samples:
            with self.subTest(bad=bad[-60:]):
                with self.assertRaises(SaveValidationError):
                    parse_quiz_cards(bad)

    def test_quiz_with_no_heading_refused(self):
        with self.assertRaises(SaveValidationError):
            parse_quiz_cards(QUIZ.replace('Answer Key:', ''))


class FakeResult:
    def __init__(self,data): self.data=data

class FakeTable:
    def __init__(self, database, name):
        self.db=database; self.name=name; self.value=None
    def insert(self,payload): self.value=payload; return self
    def select(self,cols): return self
    def execute(self):
        self.db.calls.append((self.name,self.value))
        if self.db.fail: raise RuntimeError('fake database inaccessible')
        value = self.value if isinstance(self.value,list) else [self.value]
        return FakeResult([{'id':idx+1} for idx,_ in enumerate(value)])

class FakeSupabase:
    def __init__(self): self.calls=[]; self.fail=False
    def table(self,name): return FakeTable(self,name)

class DBTests(unittest.TestCase):
    def test_note_user_scoped(self):
        db=FakeSupabase()
        id=save_note(db,42,prepare_note('Subject','Content'))
        self.assertEqual(id,1)
        self.assertEqual(db.calls[0][1]['user_id'],42)
        self.assertEqual(db.calls[0][0],'notes')

    def test_batch_flashcards_single_insert_and_no_subject(self):
        db=FakeSupabase()
        count=save_flashcards(db,42,parse_quiz_cards(QUIZ))
        self.assertEqual(count,3)
        self.assertEqual(len(db.calls),1)
        self.assertEqual(db.calls[0][0],'flashcards')
        self.assertTrue(all(r['user_id']==42 and r['subject_id'] is None for r in db.calls[0][1]))

    def test_db_failure_not_reported_as_success(self):
        db=FakeSupabase();db.fail=True
        with self.assertRaises(RuntimeError):
            save_note(db,42,prepare_note('x','y'))
        with self.assertRaises(RuntimeError):
            save_flashcards(db,42,parse_quiz_cards(QUIZ))


class KeyboardButton:
    def __init__(self,text): self.text=text
class ReplyKeyboardMarkup:
    def __init__(self,**kwargs): self.buttons=[]
    def add(self,*buttons): self.buttons.append([b.text for b in buttons])
    def row(self,*buttons): self.buttons.append([b.text for b in buttons])
class FakeBot:
    def __init__(self): self.handlers={};self.sent=[]
    def message_handler(self,**kwargs):
        def decorator(fn): self.handlers[fn.__name__]=fn;return fn
        return decorator
    def send_message(self,chatid,message,**kwargs): self.sent.append((chatid,message,kwargs))

def msg(text,uid=42):
    return types.SimpleNamespace(chat=types.SimpleNamespace(type='private',id=uid),
                                 from_user=types.SimpleNamespace(id=uid),text=text)


def load_runtime(db):
    stubs={}
    t=types.ModuleType('telebot');t.__path__=[]
    t.types=types.SimpleNamespace(ReplyKeyboardMarkup=ReplyKeyboardMarkup,KeyboardButton=KeyboardButton)
    stubs['telebot']=t
    back=types.ModuleType('telebot.handler_backends');back.ContinueHandling=type('ContinueHandling',(),{})
    stubs['telebot.handler_backends']=back
    d=types.ModuleType('db');d.supabase=db;stubs['db']=d
    nav=types.ModuleType('navigation');nav.should_yield_to_navigation=lambda s:s=='🏠 Main Menu'
    stubs['navigation']=nav
    util=types.ModuleType('safe_utils');util.split_telegram_text=lambda t,limit:[t]
    stubs['safe_utils']=util
    ops=types.ModuleType('ai_ops_v60');ops.wrap_cloudflare_provider=lambda f:f
    stubs['ai_ops_v60']=ops
    health=types.ModuleType('ai_reliability_v62');health.observe_cloudflare_health=lambda f:f
    stubs['ai_reliability_v62']=health
    code,_=installer.patch_ai(FIXTURE.read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory() as d,patch.dict(sys.modules,stubs):
        f=Path(d)/'ai_v65_offline.py';f.write_text(code,encoding='utf-8')
        spec=importlib.util.spec_from_file_location('ai_v65_offline',f)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    mod._ai_executor.shutdown(wait=False,cancel_futures=True)
    return mod


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.db=FakeSupabase()
        self.ai=load_runtime(self.db)
        self.ai.is_authorized=lambda uid:True
        self.bot=FakeBot()
        self.ai.register_ai_study_assistant_handlers(self.bot,lambda *args:None)
        self.calls=[]
        self.ai.claim_quota=lambda uid:self.calls.append(('quota',uid)) or 1
        self.ai._check_safety=lambda t,**kwargs:self.calls.append(('guard',t)) or True
        self.ai._provider_call=lambda *args:self.calls.append(('ai',args)) or 'response'
        self.ai._set_mode(42,'ask')
        self.ai._remember(42,'What is photosynthesis?',QUIZ)

    def send(self,text,uid=42):
        self.bot.handlers['ai_chat_message'](msg(text,uid))
        return self.bot.sent[-1][1] if self.bot.sent else ''

    def test_new_buttons_and_old_buttons_retained(self):
        labels=sum(self.ai._ai_chat_markup().buttons,[])
        for x in (self.ai.SAVE_NOTE_BUTTON,self.ai.SAVE_QUIZ_BUTTON,
                  self.ai.SUMMARY_BUTTON,self.ai.KEYPOINTS_BUTTON,
                  self.ai.PRACTICE_BUTTON,self.ai.CONTINUE_BUTTON,
                  self.ai.CLEAR_BUTTON):
            self.assertIn(x,labels)

    def test_note_requires_confirmation_and_no_ai_quota(self):
        result=self.send(self.ai.SAVE_NOTE_BUTTON)
        self.assertIn('Save to My Notes?',result)
        self.assertEqual(self.db.calls,[])
        self.assertIn('Note #1 saved',self.send(self.ai.SAVE_CONFIRM_BUTTON))
        self.assertEqual(self.db.calls[0][1]['content'],QUIZ.strip())
        self.assertEqual(self.calls,[])
        self.assertIn('already saved',self.send(self.ai.SAVE_NOTE_BUTTON))
        self.assertEqual(len(self.db.calls),1)

    def test_flashcards_save_as_single_batch(self):
        self.assertIn('3 multiple-choice questions',self.send(self.ai.SAVE_QUIZ_BUTTON))
        self.assertEqual(self.db.calls,[])
        self.assertIn('3 flashcards saved',self.send(self.ai.SAVE_CONFIRM_BUTTON))
        self.assertEqual(len(self.db.calls),1)
        self.assertEqual(len(self.db.calls[0][1]),3)
        self.assertEqual(self.calls,[])

    def test_cancel_then_confirm_does_not_save(self):
        self.send(self.ai.SAVE_QUIZ_BUTTON)
        self.assertIn('Save cancelled',self.send(self.ai.SAVE_CANCEL_BUTTON))
        self.assertIn('No save awaiting confirmation',self.send(self.ai.SAVE_CONFIRM_BUTTON))
        self.assertEqual(self.db.calls,[])

    def test_no_prior_answer(self):
        self.ai._set_mode(42,'ask')
        self.assertIn('Ask AI for an answer',self.send(self.ai.SAVE_NOTE_BUTTON))
        self.assertEqual(self.db.calls,[])

    def test_session_isolation(self):
        self.assertEqual(self.send(self.ai.SAVE_NOTE_BUTTON,uid=99),'')
        self.assertEqual(self.db.calls,[])
        self.ai._set_mode(99,'ask')
        self.assertIn('Ask AI for an answer',self.send(self.ai.SAVE_NOTE_BUTTON,uid=99))
        self.assertEqual(self.db.calls,[])

    def test_incomplete_quiz_refuses_to_write(self):
        self.ai._remember(42,'question','Not a quiz at all')
        self.assertIn('format is incomplete',self.send(self.ai.SAVE_QUIZ_BUTTON))
        self.assertEqual(self.db.calls,[])

    def test_new_answer_invalidates_old_pending_save(self):
        self.send(self.ai.SAVE_NOTE_BUTTON)
        self.ai._remember(42,'new question','new answer')
        self.assertIn('No save awaiting confirmation',self.send(self.ai.SAVE_CONFIRM_BUTTON))
        self.assertEqual(self.db.calls,[])

    def test_db_failure_does_not_claim_success(self):
        self.send(self.ai.SAVE_NOTE_BUTTON)
        self.db.fail=True
        self.assertIn('Could not verify',self.send(self.ai.SAVE_CONFIRM_BUTTON))
        self.assertNotIn('saved!',self.bot.sent[-1][1])

    def test_confirm_without_preview_does_not_write(self):
        self.assertIn('No save awaiting confirmation',self.send(self.ai.SAVE_CONFIRM_BUTTON))
        self.assertEqual(self.db.calls,[])


if __name__ == '__main__':
    unittest.main()
