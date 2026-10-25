"""V6.4 offline tests: no network calls, no API keys and no Supabase access."""
from __future__ import annotations
import ast
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import INSTALL_V6_4 as installer

FIXTURE = Path(__file__).with_name("FIXTURE_V6_3_AI.txt")


def source():
    return FIXTURE.read_text(encoding="utf-8")


class InstallerTests(unittest.TestCase):
    def test_patch_and_idempotent(self):
        modified, changed = installer.patch_ai(source())
        self.assertTrue(changed)
        ast.parse(modified)
        self.assertEqual(installer.patch_ai(modified), (modified, False))
        self.assertEqual(modified.count(installer.MARKER), 1)

    def test_no_existing_features_removed(self):
        old = source()
        changed, _ = installer.patch_ai(old)
        for fragment in [
            'if text in V63_FOLLOW_UPS:',
            'MAX_OUTPUT_TOKENS = 1800',
            '"content": answer[-1800:]',
            'def claim_quota(',
            'def _check_safety(',
            '_provider_call = wrap_cloudflare_provider(_provider_call)',
            '_provider_call = observe_cloudflare_health(_provider_call)',
            'split_telegram_text(answer, limit=3500)',
        ]:
            self.assertIn(fragment, changed)
        self.assertNotIn('GEMINI_API_KEY', changed)
        self.assertNotIn('gemini_ai_studio', changed)
        self.assertEqual(changed.count('claim_quota(user_id)'), old.count('claim_quota(user_id)'))

    def test_crlf_windows_compatible(self):
        windows = source().replace('\n', '\r\n')
        changed, did_change = installer.patch_ai(windows)
        self.assertTrue(did_change)
        self.assertNotIn('\r\r\n', changed)
        self.assertEqual(installer.patch_ai(changed), (changed, False))

    def test_fail_closed_on_old_and_partial_versions(self):
        invalid = [
            'print("unexpected")\n',
            source().replace('# V6.3: student-controlled AI follow-up shortcuts', ''),
            source().replace('"content": answer[-1800:]', '"content": answer[:1800]'),
        ]
        for data in invalid:
            with self.subTest(sample=data[:35]):
                with self.assertRaises(ValueError):
                    installer.patch_ai(data)
        valid, _ = installer.patch_ai(source())
        with self.assertRaises(ValueError):
            installer.patch_ai(valid.replace('if text in V64_STUDY_ACTIONS:', 'if text in {}:'))

    def test_installer_backup_and_idempotency(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / installer.TARGET
            path.write_text(source(), encoding='utf-8')
            self.assertTrue(installer.install(root))
            self.assertFalse(installer.install(root))
            backup = root / (installer.TARGET + '.before_v64.bak')
            self.assertEqual(backup.read_text(encoding='utf-8'), source())
            self.assertTrue(path.read_text(encoding='utf-8').count(installer.MARKER) == 1)
            self.assertFalse(list(root.glob('*.tmp')))

    def test_installer_does_not_mutate_unfamiliar_code(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / installer.TARGET
            path.write_text('x = 10\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                installer.install(root)
            self.assertEqual(path.read_text(encoding='utf-8'), 'x = 10\n')
            self.assertFalse(list(root.glob('*.bak')))

    def test_refuse_overwriting_backup(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / installer.TARGET
            path.write_text(source(), encoding='utf-8')
            (root / (installer.TARGET + '.before_v64.bak')).write_text('old copy',encoding='utf-8')
            with self.assertRaises(ValueError):
                installer.install(root)
            self.assertEqual(path.read_text(encoding='utf-8'), source())


class KeyboardButton:
    def __init__(self, text):
        self.text = text


class ReplyKeyboardMarkup:
    def __init__(self, **kwargs):
        self.buttons = []
    def row(self, *buttons):
        self.buttons.append([b.text for b in buttons])
    def add(self, *buttons):
        self.buttons.append([b.text for b in buttons])


class FakeBot:
    def __init__(self):
        self.handlers = {}
        self.sent = []
    def message_handler(self, **kwargs):
        def deco(fn):
            self.handlers[fn.__name__] = fn
            return fn
        return deco
    def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text, kwargs))


def telegram_message(text, uid=42):
    return types.SimpleNamespace(chat=types.SimpleNamespace(type='private', id=uid),
                                 from_user=types.SimpleNamespace(id=uid), text=text)


def load_code():
    stubs = {}
    t = types.ModuleType('telebot'); t.__path__ = []
    t.types = types.SimpleNamespace(ReplyKeyboardMarkup=ReplyKeyboardMarkup, KeyboardButton=KeyboardButton)
    stubs['telebot'] = t
    back = types.ModuleType('telebot.handler_backends'); back.ContinueHandling = type('ContinueHandling', (), {})
    stubs['telebot.handler_backends'] = back
    db = types.ModuleType('db'); db.supabase = object(); stubs['db'] = db
    nav = types.ModuleType('navigation'); nav.should_yield_to_navigation = lambda txt: txt == '🏠 Main Menu'; stubs['navigation'] = nav
    util = types.ModuleType('safe_utils'); util.split_telegram_text = lambda answer, limit: [answer]; stubs['safe_utils'] = util
    ops = types.ModuleType('ai_ops_v60'); ops.wrap_cloudflare_provider = lambda f: f; stubs['ai_ops_v60'] = ops
    health = types.ModuleType('ai_reliability_v62'); health.observe_cloudflare_health = lambda f: f; stubs['ai_reliability_v62'] = health
    patched, _ = installer.patch_ai(source())
    with tempfile.TemporaryDirectory() as td, patch.dict(sys.modules, stubs):
        f = Path(td)/'offline_ai_v64.py'; f.write_text(patched, encoding='utf-8')
        spec = importlib.util.spec_from_file_location('offline_ai_v64', f)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    module._ai_executor.shutdown(wait=False, cancel_futures=True)
    return module


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.ai = load_code()
        self.bot = FakeBot()
        self.ai.register_ai_study_assistant_handlers(self.bot, lambda *a: None)
        self.ai.is_authorized = lambda *a: True
        self.quota = []
        self.ai.claim_quota = lambda uid: self.quota.append(uid) or 1
        self.safety = []
        self.ai._check_safety = lambda txt, **kw: self.safety.append((txt,kw)) or True
        self.calls = []
        self.ai._provider_call = lambda model, messages, max_tokens: self.calls.append((model,messages,max_tokens)) or 'கற்றல் பதில்.'
        class InlineExecutor:
            def submit(inner, fn, *args):
                fn(*args)
        self.ai._ai_executor = InlineExecutor()

    def prime(self, uid=42):
        self.ai._set_mode(uid, 'ask')
        self.ai._remember(uid,'Explain photosynthesis in Tamil','ஒளிச்சேர்க்கை: செடிகள் சூரிய ஒளியைப் பயன்படுத்துகின்றன.')

    def test_keyboard_keeps_existing_buttons(self):
        labels = sum(self.ai._ai_chat_markup().buttons, [])
        for button in [self.ai.SUMMARY_BUTTON, self.ai.KEYPOINTS_BUTTON, self.ai.PRACTICE_BUTTON,
                       self.ai.CONTINUE_BUTTON, self.ai.SIMPLIFY_BUTTON, self.ai.EXAMPLES_BUTTON,
                       self.ai.BACK_BUTTON, self.ai.CLEAR_BUTTON, '🏠 Main Menu']:
            self.assertIn(button, labels)
            self.assertEqual(labels.count(button),1)

    def test_all_study_tools_use_last_answer_in_context(self):
        for btn in (self.ai.SUMMARY_BUTTON, self.ai.KEYPOINTS_BUTTON, self.ai.PRACTICE_BUTTON):
            with self.subTest(btn=btn):
                self.prime()
                self.bot.handlers['ai_chat_message'](telegram_message(btn))
                _, message_list, tokens = self.calls[-1]
                self.assertEqual(tokens, 1800)
                self.assertEqual(message_list[-1]['content'], self.ai.V64_STUDY_ACTIONS[btn])
                self.assertTrue(any('ஒளிச்சேர்க்கை' in m['content'] for m in message_list))
                self.assertEqual(self.quota[-1],42)
                self.assertTrue(self.safety)

    def test_before_answer_zero_calls_and_zero_quota(self):
        self.ai._set_mode(42, 'ask')
        for btn in (self.ai.SUMMARY_BUTTON, self.ai.KEYPOINTS_BUTTON, self.ai.PRACTICE_BUTTON):
            self.bot.handlers['ai_chat_message'](telegram_message(btn))
        self.assertFalse(self.calls)
        self.assertFalse(self.quota)
        self.assertIn('First ask a study question', self.bot.sent[-1][1])

    def test_daily_limit_enforced(self):
        self.prime()
        self.ai.claim_quota = lambda uid: 0
        self.bot.handlers['ai_chat_message'](telegram_message(self.ai.PRACTICE_BUTTON))
        self.assertEqual(self.calls, [])
        self.assertIn('Daily AI limit reached',str(self.bot.sent))

    def test_other_users_history_not_mixed(self):
        self.prime(42)
        self.ai._set_mode(99,'ask')
        self.ai._remember(99,'What is a noun?','A noun names a person or thing.')
        self.bot.handlers['ai_chat_message'](telegram_message(self.ai.SUMMARY_BUTTON,uid=99))
        msgs=self.calls[-1][1]
        text=' '.join(m['content'] for m in msgs)
        self.assertIn('A noun names', text)
        self.assertNotIn('ஒளிச்சேர்க்கை', text)

    def test_plain_questions_and_v63_shortcuts_unchanged(self):
        self.ai._set_mode(42,'ask')
        self.bot.handlers['ai_chat_message'](telegram_message('What is gravity?'))
        self.assertEqual(self.calls[-1][1][-1]['content'],'What is gravity?')
        self.prime()
        self.bot.handlers['ai_chat_message'](telegram_message(self.ai.CONTINUE_BUTTON))
        self.assertEqual(self.calls[-1][1][-1]['content'],self.ai.V63_FOLLOW_UPS[self.ai.CONTINUE_BUTTON])

    def test_navigation_yields_without_api_calls(self):
        self.prime()
        result=self.bot.handlers['ai_chat_message'](telegram_message('🏠 Main Menu'))
        self.assertEqual(type(result).__name__, 'ContinueHandling')
        self.assertFalse(self.quota)
        self.assertFalse(self.calls)

    def test_prompts_under_input_limit_and_source_restricted(self):
        for btn, prompt in self.ai.V64_STUDY_ACTIONS.items():
            self.assertLess(len(prompt),self.ai.MAX_INPUT_CHARS)
            self.assertIn('recent',prompt)
        self.assertIn('answer key',self.ai.V64_STUDY_ACTIONS[self.ai.PRACTICE_BUTTON])
        self.assertIn('same language',self.ai.V64_STUDY_ACTIONS[self.ai.SUMMARY_BUTTON])

    def test_session_last_answer_retained_v63(self):
        self.ai._set_mode(42,'ask')
        self.ai._remember(42,'example','START!'+'x'*2600+'END!')
        self.assertEqual(len(self.ai._get_session(42)['history'][-1]['content']),1800)
        self.assertTrue(self.ai._get_session(42)['history'][-1]['content'].endswith('END!'))

    def test_no_automatic_second_request(self):
        self.prime()
        self.bot.handlers['ai_chat_message'](telegram_message(self.ai.PRACTICE_BUTTON))
        self.assertEqual(len(self.calls),1)
        self.assertEqual(len(self.quota),1)


if __name__ == '__main__':
    unittest.main()
