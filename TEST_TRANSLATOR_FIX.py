"""Offline tests for V5.4 translation fix. No Telegram/Supabase/network calls."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def install_stubs():
    telebot = types.ModuleType('telebot')
    ttypes = types.ModuleType('telebot.types')

    class InlineKeyboardMarkup:
        def __init__(self, **kwargs):
            self.buttons = []
        def add(self, *buttons):
            self.buttons.extend(buttons)

    class InlineKeyboardButton:
        def __init__(self, text, **kwargs):
            self.text, self.kwargs = text, kwargs

    # Deliberately no CopyTextButton: simulates an older Telegram library.
    ttypes.InlineKeyboardMarkup = InlineKeyboardMarkup
    ttypes.InlineKeyboardButton = InlineKeyboardButton
    telebot.types = ttypes
    sys.modules['telebot'] = telebot
    sys.modules['telebot.types'] = ttypes

    dt = types.ModuleType('deep_translator')
    class GoogleTranslator:
        def __init__(self, **kwargs):
            pass
        def translate(self, text):
            raise RuntimeError('Mock Google service unavailable')
    class MyMemoryTranslator:
        def __init__(self, **kwargs):
            pass
        def translate(self, text):
            raise RuntimeError('Mock MyMemory service unavailable')
    dt.GoogleTranslator, dt.MyMemoryTranslator = GoogleTranslator, MyMemoryTranslator
    sys.modules['deep_translator'] = dt

    config = types.ModuleType('config')
    config.LIBRETRANSLATE_URL = ''
    config.LIBRETRANSLATE_API_KEY = ''
    sys.modules['config'] = config
    h = types.ModuleType('translation_history')
    h.save_translation = lambda **kw: None
    h.get_translation_history = lambda *a, **kw: []
    h.get_translation_by_id = lambda *a, **kw: None
    h.clear_translation_history = lambda *a, **kw: True
    sys.modules['translation_history'] = h

    tts = types.ModuleType('translation_tts')
    tts.build_pronunciation_audio = lambda *a: (b'', False)
    sys.modules['translation_tts'] = tts
    docs = types.ModuleType('translation_documents')
    docs.SUPPORTED_DOCUMENT_EXTENSIONS = set()
    docs.extract_text_from_document = lambda *a: ''
    docs.build_translated_text_file = lambda *a: (b'', 'output.txt')
    sys.modules['translation_documents'] = docs
    ocr = types.ModuleType('translation_ocr')
    ocr.extract_text_with_ocr = lambda *a: ''
    ocr.get_ocr_api_key = lambda: ''
    sys.modules['translation_ocr'] = ocr

install_stubs()
spec = importlib.util.spec_from_file_location('translate_v54_fixed', HERE / 'translate.py')
translator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(translator)


class FakeBot:
    def __init__(self, reject_markup=False):
        self.sent = []
        self.reject_markup = reject_markup
    def send_message(self, chat_id, text, reply_markup=None):
        if self.reject_markup and reply_markup is not None:
            raise ValueError('Mock Telegram keyboard rejection')
        self.sent.append((chat_id, text, reply_markup))
        return types.SimpleNamespace(message_id=4)


class TranslationTests(unittest.TestCase):
    def setUp(self):
        translator.translation_cache.clear()

    def test_provider_success(self):
        with patch.object(translator.GoogleTranslator, 'translate', return_value='எப்படி'):
            value, provider = translator.translate_chunk('en', 'ta', 'how')
        self.assertEqual(value, 'எப்படி')
        self.assertEqual(provider, 'Google')

    def test_fallback_endpoint_response(self):
        fake = types.SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: [[['எப்படி', 'how', None, None]]],
        )
        with patch.object(translator.requests, 'get', return_value=fake) as method:
            result, provider = translator.translate_chunk('en', 'ta', 'how')
        self.assertEqual((result, provider), ('எப்படி', 'Google Public Endpoint'))
        self.assertIn('timeout', method.call_args.kwargs)

    def test_cached_translation(self):
        translator.cache_save(('en', 'ta', 'how'), 'எப்படி')
        result, provider = translator.translate_chunk('en', 'ta', 'how')
        self.assertEqual((result, provider), ('எப்படி', 'Cache'))

    def test_older_telebot_without_copy_text(self):
        self.assertIsNone(translator.create_result_markup('எப்படி', None))

    def test_translation_delivered_even_without_history(self):
        bot = FakeBot()
        message = types.SimpleNamespace(
            chat=types.SimpleNamespace(id=123),
            from_user=types.SimpleNamespace(id=456),
        )
        translator.send_translation_result(
            bot, message, 'en', 'ta', 'how', 'எப்படி', 'Google'
        )
        self.assertEqual(len(bot.sent), 1)
        self.assertIn('எப்படி', bot.sent[0][1])

    def test_reject_markup_falls_back_to_plain_text(self):
        bot = FakeBot(reject_markup=True)
        optional_markup = translator.types.InlineKeyboardMarkup()
        translator.send_safe_translation_message(bot, 123, 'எப்படி', optional_markup)
        self.assertEqual(bot.sent[0][1], 'எப்படி')
        self.assertIsNone(bot.sent[0][2])

    def test_all_providers_failed_has_clear_diagnostic(self):
        with patch.object(translator.requests, 'get', side_effect=TimeoutError('Mock timeout')):
            with self.assertRaisesRegex(RuntimeError, 'All available translation services failed'):
                translator.translate_chunk('en', 'ta', 'how')


if __name__ == '__main__':
    unittest.main(verbosity=2)
