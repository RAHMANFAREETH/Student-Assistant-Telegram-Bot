"""Offline V5.6 regression tests; no Telegram, Supabase, or Cloudflare calls."""
import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import types as pytypes
from threading import RLock

# No network or third-party packages needed for these tests.
class ContinueHandling: pass
class FakeKeyboardButton:
    def __init__(self, text): self.text = text
class FakeReplyKeyboardMarkup:
    def __init__(self, **kw): self.buttons=[]
    def add(self, *btns): self.buttons.extend(btns)
    def row(self, *btns): self.buttons.extend(btns)

tb = pytypes.ModuleType("telebot")
tbt = pytypes.ModuleType("telebot.types")
tbt.ReplyKeyboardMarkup = FakeReplyKeyboardMarkup
tbt.KeyboardButton = FakeKeyboardButton
tb.types = tbt
tbb = pytypes.ModuleType("telebot.handler_backends")
tbb.ContinueHandling = ContinueHandling
sys.modules["telebot"] = tb
sys.modules["telebot.types"] = tbt
sys.modules["telebot.handler_backends"] = tbb
fake_db = pytypes.ModuleType("db")
fake_db.supabase = None
sys.modules["db"] = fake_db
fake_nav = pytypes.ModuleType("navigation")
fake_nav.should_yield_to_navigation = lambda s: s.startswith("/") or s in {"🏠 Main Menu", "🤖 Ask AI", "📝 Ask My Notes", "📄 Ask My PDF"}
sys.modules["navigation"] = fake_nav
safe = pytypes.ModuleType("safe_utils")
safe.split_telegram_text = lambda s, limit=3400: [s[i:i+limit] for i in range(0,len(s),limit)]
sys.modules["safe_utils"] = safe

class FakeAIUnavailable(Exception):
    def __init__(self, msg, code="error"):
        self.code=code
        super().__init__(msg)
class FakeExecutor:
    def submit(self, fn, *args):
        return fn(*args)

ai = pytypes.ModuleType("ai_study_assistant")
ai.is_authorized=lambda uid: True
ai._clear=lambda uid: None
ai._jobs_lock=RLock()
ai._active_user_ids=set()
ai.MAX_ACTIVE_JOBS=3
ai.claim_quota=lambda uid: 1
ai.daily_limit=lambda: 8
ai._check_safety=lambda *a,**kw: True
ai._provider_call=lambda *a: "Mocked reply"
ai._ai_executor=FakeExecutor()
ai.CF_MODEL="mock-model"
ai.MAX_OUTPUT_TOKENS=650
ai._system_prompt=lambda mode: "Be a student tutor."
ai.AIUnavailable=FakeAIUnavailable
ai.MODE_BUTTONS={"💬 Ask Question": "ask"}
ai.AI_MENU="🤖 Ask AI"
ai.CLEAR_BUTTON="🧹 Clear AI Chat"
ai.BACK_BUTTON="⬅️ AI Menu"
sys.modules["ai_study_assistant"] = ai

class FakeBot:
    def __init__(self): self.handlers=[];self.messages=[]
    def message_handler(self, **kwargs):
        def decorator(fn): self.handlers.append((fn,kwargs)); return fn
        return decorator
    def send_message(self, cid, text, **kwargs): self.messages.append((cid,text,kwargs))
    def call(self,name,msg):
        for fn,kwargs in self.handlers:
            if fn.__name__==name: return fn(msg)
        raise AssertionError("missing handler "+name)
class FakeMsg:
    def __init__(self,text,user=111,private=True):
        self.text=text
        self.from_user=SimpleNamespace(id=user)
        self.chat=SimpleNamespace(id=user if private else -1,type="private" if private else "group")

P = Path(__file__).parent
spec = importlib.util.spec_from_file_location("study_context_test", P / "study_context_ai.py")
ctx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctx)

class FakeQuery:
    def __init__(self, dataset):
        self.dataset = list(dataset)
        self.filters = []
        self._limit = None
        self.fields = None
    def select(self, fields): self.fields = fields; return self
    def eq(self, field, value): self.filters.append((field, value)); return self
    def order(self, *args, **kwargs): return self
    def limit(self, n): self._limit=n; return self
    def execute(self):
        rows = [r for r in self.dataset if all(r.get(f)==v for f,v in self.filters)]
        if self._limit is not None: rows = rows[:self._limit]
        return SimpleNamespace(data=rows)
class FakeSupabase:
    def __init__(self):
        self.collections = {
            "notes": [
                {"id": 1, "user_id": 111, "title": "My Chemistry", "content": "Photosynthesis occurs in chloroplasts."},
                {"id": 2, "user_id": 222, "title": "Private User", "content": "Secret text of second student"},
            ],
            "study_materials": [
                {"id": 11, "user_id": 111, "title": "Biology PDF", "file_name": "biology.pdf", "file_type": "pdf", "extracted_text": "Chlorophyll absorbs light."},
                {"id": 12, "user_id": 111, "title": "Not PDF", "file_name": "lesson.txt", "file_type": "txt", "extracted_text": "Plain text."},
                {"id": 13, "user_id": 222, "title": "Another Student", "file_name": "private.pdf", "file_type": "pdf", "extracted_text": "Do not expose"},
            ],
        }
    def table(self, name): return FakeQuery(self.collections[name])

class ContextTests(unittest.TestCase):
    def setUp(self):
        ctx._states.clear()
        ai._active_user_ids.clear()
        self.db = patch.object(ctx, "supabase", FakeSupabase())
        self.db.start()
        self.auth = patch.object(ai, "is_authorized", return_value=True)
        self.auth.start()
        self.bot = FakeBot()
        ctx.register_study_context_handlers(self.bot, lambda cid: self.bot.send_message(cid, "Main Menu"))
    def tearDown(self):
        self.auth.stop()
        self.db.stop()
        ctx._states.clear()
        ai._active_user_ids.clear()

    def call(self, name, text, user=111, private=True):
        return self.bot.call(name, FakeMsg(text, user=user, private=private))

    def test_user_isolation_of_notes(self):
        rows = ctx._query_recent(111, "notes")
        self.assertEqual([r["id"] for r in rows], [1])
        self.assertIsNone(ctx._get_source(111, "notes", 2))
    def test_user_isolation_of_pdf(self):
        self.assertEqual([r["id"] for r in ctx._query_recent(111, "pdf")], [11])
        self.assertIsNone(ctx._get_source(111, "pdf", 13))
        self.assertIsNone(ctx._get_source(111, "pdf", 12))
    def test_query_by_id_and_explicit_consent(self):
        self.call("notes_command", "/asknotes")
        state = ctx._get_state(111)
        self.assertEqual(state["phase"], "choose")
        self.call("source_dialog", "1")
        self.assertEqual(state["phase"], "consent")
        self.call("source_dialog", "no")
        self.assertEqual(state["phase"], "consent")
        self.call("source_dialog", "I AGREE")
        self.assertEqual(state["phase"], "question")
    def test_pdf_only_existing_saved_materials(self):
        self.call("pdf_command", "/askpdf")
        txt = "\n".join(m[1] for m in self.bot.messages)
        self.assertIn("Biology PDF", txt)
        self.assertNotIn("Not PDF", txt)
    def test_no_group_access(self):
        self.call("notes_command", "/asknotes", private=False)
        self.assertIsNone(ctx._get_state(111))
    def test_long_documents_retrieval_is_bounded(self):
        text = "BACKGROUND. " * 500 + " mitochondria ATP " * 50 + "OTHER. " * 1000
        excerpts = ctx.choose_excerpts("How does mitochondria make ATP?", text)
        self.assertLessEqual(len(excerpts), ctx.MAX_CHUNKS)
        self.assertTrue(any("mitochondria" in p for _, p in excerpts))
        self.assertLessEqual(sum(len(piece) for _, piece in excerpts), ctx.MAX_CHUNKS*ctx.CHUNK_CHARS)
    def test_navigation_yields_without_intercepting(self):
        self.call("notes_command", "/asknotes")
        self.assertIsInstance(self.call("source_dialog", "🏠 Main Menu"), ContinueHandling)
        self.assertIsNone(ctx._get_state(111))
    def test_worker_claims_quota_and_moderates_twice(self):
        self.call("notes_command", "/asknotes")
        self.call("source_dialog", "1")
        self.call("source_dialog", "I AGREE")
        checks=[]
        def guard(*args, **kwargs): checks.append(kwargs); return True
        with patch.object(ai, "claim_quota", return_value=1) as quota, \
             patch.object(ai, "_check_safety", side_effect=guard), \
             patch.object(ai, "_provider_call", return_value="Chloroplasts capture light."), \
             patch.object(ai._ai_executor, "submit", side_effect=lambda fn,*args: fn(*args)):
            self.call("source_dialog", "What is photosynthesis?")
        self.assertEqual(quota.call_count, 1)
        self.assertEqual(len(checks), 2)
        self.assertTrue(any("Chloroplasts capture light." in m[1] for m in self.bot.messages))
    def test_no_send_without_consent(self):
        self.call("notes_command", "/asknotes")
        self.call("source_dialog", "1")
        with patch.object(ai, "_provider_call") as provider:
            self.call("source_dialog", "What is chemistry?")
        provider.assert_not_called()
    def test_installer_is_idempotent(self):
        sp = importlib.util.spec_from_file_location("install_v56", P / "INSTALL_V5_6.py")
        installer=importlib.util.module_from_spec(sp); sp.loader.exec_module(installer)
        main=("from ai_study_assistant import register_ai_study_assistant_handlers\n"
              "register_ai_study_assistant_handlers(bot, show_main_menu)\n")
        nav=('ASK_AI = "🤖 Ask AI"\nMAIN_MENU_ROWS = [\n    (ASK_AI,),\n]\n')
        m,yes=installer.update_main(main)
        n,yesn=installer.update_navigation(nav)
        self.assertTrue(yes and yesn)
        m2,yes2=installer.update_main(m)
        n2,yesn2=installer.update_navigation(n)
        self.assertFalse(yes2 or yesn2)
        self.assertEqual(m,m2); self.assertEqual(n,n2)
        self.assertIn("register_study_context_handlers(bot, show_main_menu)\nregister_ai_study_assistant_handlers",m)
        self.assertIn("(ASK_NOTES, ASK_PDF)",n)

if __name__=="__main__": unittest.main()
