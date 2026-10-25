"""Offline V6.3 tests; no Cloudflare, Google, Supabase or Telegram network calls."""
from __future__ import annotations
import ast
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import INSTALL_V6_3 as installer


BASE = Path(__file__).with_name('FIXTURE_V6_2_2_AI.txt')


def _fixture_source():
    """Real V6.2.2-shaped AI module, assembled from the prior released project."""
    return BASE.read_text(encoding='utf-8')


class InstallerTests(unittest.TestCase):
    def test_patch_compiles_and_targets_only_expected_changes(self):
        source = _fixture_source()
        result, installed = installer.patch_ai(source)
        self.assertTrue(installed)
        ast.parse(result)
        self.assertEqual(result.count(installer.MARKER), 1)
        for old in ['_provider_call = wrap_cloudflare_provider(_provider_call)',
                    '_provider_call = observe_cloudflare_health(_provider_call)',
                    'GUARD_MODEL = ', 'MAX_OUTPUT_TOKENS = 1800',
                    'split_telegram_text(answer, limit=3500)']:
            self.assertIn(old, result)
        self.assertNotIn('gemini_ai_studio', result)
        self.assertEqual(installer.patch_ai(result), (result, False))

    def test_crlf_utf8_and_idempotence(self):
        source = _fixture_source().replace('\n', '\r\n')
        result, changed = installer.patch_ai(source)
        self.assertTrue(changed)
        self.assertNotIn('\r\r\n', result)
        self.assertIn('➡️ Continue Answer'.encode('utf-8'), result.encode('utf-8'))
        self.assertEqual(installer.patch_ai(result), (result, False))

    def test_invalid_source_refused(self):
        for s in ['print("hello")\n', _fixture_source().replace('MAX_OUTPUT_TOKENS = 1800','MAX_OUTPUT_TOKENS = 650')]:
            with self.assertRaises(ValueError):
                installer.patch_ai(s)

    def test_backup_and_duplicate_safe(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / installer.TARGET
            source = _fixture_source()
            file.write_text(source, encoding='utf-8')
            self.assertTrue(installer.install(root))
            self.assertEqual((root / (installer.TARGET+'.before_v63.bak')).read_text(encoding='utf-8'), source)
            self.assertFalse(installer.install(root))
            file.write_text(source, encoding='utf-8')
            with self.assertRaises(ValueError):
                installer.install(root)

    def test_preflight_does_not_modify_original(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / installer.TARGET
            target.write_text('print("bad version")\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                installer.install(root)
            self.assertFalse(list(root.glob('*.bak')))
            self.assertEqual(target.read_text(encoding='utf-8'), 'print("bad version")\n')


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

class Bot:
    def __init__(self):
        self.handlers = {}
        self.sent = []
    def message_handler(self, **params):
        def decorator(fn):
            self.handlers[fn.__name__] = fn
            return fn
        return decorator
    def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text, kwargs))


def load_module_for_offline_test():
    """Provide tiny stub interfaces so the actual patched module can run without dependencies."""
    stubs = {}
    telebot = types.ModuleType('telebot')
    telebot.__path__ = []
    telebot.types = types.SimpleNamespace(ReplyKeyboardMarkup=ReplyKeyboardMarkup, KeyboardButton=KeyboardButton)
    stubs['telebot'] = telebot
    backends = types.ModuleType('telebot.handler_backends')
    backends.ContinueHandling = type('ContinueHandling', (), {})
    stubs['telebot.handler_backends'] = backends
    db = types.ModuleType('db')
    db.supabase = object()
    stubs['db'] = db
    nav = types.ModuleType('navigation')
    nav.should_yield_to_navigation = lambda text: text == '🏠 Main Menu'
    stubs['navigation'] = nav
    utils = types.ModuleType('safe_utils')
    utils.split_telegram_text = lambda answer, limit: [answer]
    stubs['safe_utils'] = utils
    ops = types.ModuleType('ai_ops_v60')
    ops.wrap_cloudflare_provider = lambda func:func
    stubs['ai_ops_v60'] = ops
    health = types.ModuleType('ai_reliability_v62')
    health.observe_cloudflare_health = lambda func:func
    stubs['ai_reliability_v62'] = health
    src, _ = installer.patch_ai(_fixture_source())
    with tempfile.TemporaryDirectory() as temp, patch.dict(sys.modules, stubs):
        filename = Path(temp)/'ai_v63_test_module.py'
        filename.write_text(src, encoding='utf-8')
        spec = importlib.util.spec_from_file_location('ai_v63_test_module', filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    # Thread pool is created on import; stop it at cleanup to avoid leaks.
    module._ai_executor.shutdown(wait=False, cancel_futures=True)
    return module


def message(text, uid=42):
    return types.SimpleNamespace(chat=types.SimpleNamespace(type='private',id=42),
                                 from_user=types.SimpleNamespace(id=uid),text=text)


class AIChatTests(unittest.TestCase):
    def setUp(self):
        self.ai = load_module_for_offline_test()
        self.bot = Bot()
        self.ai.register_ai_study_assistant_handlers(self.bot, lambda *args:None)
        self.ai.is_authorized = lambda *args: True
        self.ai.claim_quota = lambda *args: 1
        self.calls = []
        self.ai._check_safety = lambda *args, **kwargs: True
        self.ai._provider_call = lambda model, messages, max_tokens: self.calls.append((model,messages,max_tokens)) or 'A clear response.'
        class Executor:
            def submit(inner, fn, *args): return fn(*args)
        self.ai._ai_executor = Executor()

    def test_shortcuts_in_keyboard_and_legacy_controls_kept(self):
        keyboard = self.ai._ai_chat_markup().buttons
        text = sum(keyboard, [])
        for button in (self.ai.CONTINUE_BUTTON,self.ai.SIMPLIFY_BUTTON,self.ai.EXAMPLES_BUTTON,
                       self.ai.BACK_BUTTON,self.ai.CLEAR_BUTTON,'🏠 Main Menu'):
            self.assertIn(button, text)
        self.assertEqual(len([t for t in text if t == self.ai.CONTINUE_BUTTON]),1)

    def test_shortcut_before_first_answer_does_not_claim_quota(self):
        used = []
        self.ai.claim_quota = lambda uid: used.append(uid)
        self.ai._set_mode(42, 'ask')
        self.bot.handlers['ai_chat_message'](message(self.ai.CONTINUE_BUTTON))
        self.assertFalse(used)
        self.assertFalse(self.calls)
        self.assertIn('First ask a study question', self.bot.sent[-1][1])

    def test_each_shortcut_routes_through_existing_safety_and_daily_limit(self):
        for button in (self.ai.CONTINUE_BUTTON, self.ai.SIMPLIFY_BUTTON, self.ai.EXAMPLES_BUTTON):
            self.ai._set_mode(42, 'ask')
            self.ai._remember(42, 'explain photosynthesis in Tamil','தாவரங்கள் சூரிய ஒளியை பயன்படுத்துகின்றன.')
            self.bot.handlers['ai_chat_message'](message(button))
            self.assertTrue(self.calls)
            _, messages, output = self.calls[-1]
            self.assertEqual(output, 1800)
            self.assertEqual(messages[-1]['content'], self.ai.V63_FOLLOW_UPS[button])
            self.assertEqual(messages[1]['content'], 'explain photosynthesis in Tamil')
            self.assertTrue(any('தாவரங்கள்' in m['content'] for m in messages))

    def test_history_keeps_last_part_of_long_answer(self):
        self.ai._set_mode(42, 'ask')
        long_answer = 'INTRO_START'+'x'*2600+'END_OF_EXAMPLE_THREE'
        self.ai._remember(42, 'topic in Tamil',long_answer)
        stored = self.ai._get_session(42)['history'][-1]['content']
        self.assertEqual(len(stored),1800)
        self.assertTrue(stored.endswith('END_OF_EXAMPLE_THREE'))
        self.assertNotIn('INTRO_START',stored)

    def test_normal_user_question_remains_unchanged(self):
        self.ai._set_mode(42, 'ask')
        self.bot.handlers['ai_chat_message'](message('What is a noun?'))
        self.assertEqual(self.calls[-1][1][-1]['content'], 'What is a noun?')

    def test_followups_observe_existing_quota(self):
        self.ai._set_mode(42, 'ask')
        self.ai._remember(42,'a','b')
        self.ai.claim_quota = lambda *args: 0
        self.bot.handlers['ai_chat_message'](message(self.ai.EXAMPLES_BUTTON))
        self.assertFalse(self.calls)
        self.assertIn('Daily AI limit reached', str(self.bot.sent))

    def test_followup_length_under_input_limit(self):
        self.ai._set_mode(42, 'ask')
        self.ai._remember(42,'a','b')
        for prompt in self.ai.V63_FOLLOW_UPS.values():
            self.assertLessEqual(len(prompt),self.ai.MAX_INPUT_CHARS)


if __name__ == '__main__':
    unittest.main()
