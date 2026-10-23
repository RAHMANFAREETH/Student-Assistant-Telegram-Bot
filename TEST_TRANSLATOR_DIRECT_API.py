"""Offline tests of direct MyMemory fallback and history resilience."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import TEST_TRANSLATOR_FIX as base

tr = base.translator

class Tests(unittest.TestCase):
    def setUp(self):
        tr.translation_cache.clear()

    def _response(self, status=200, text="எப்படி"):
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"responseStatus": status, "responseData": {"translatedText": text}},
        )

    def test_en_to_tamil_direct_api(self):
        with patch.object(tr.requests, 'get', return_value=self._response()) as mock:
            value = tr.translate_mymemory_api('en', 'ta', 'How')
        self.assertEqual(value, 'எப்படி')
        self.assertEqual(mock.call_args.kwargs['params']['langpair'], 'en|ta')
        self.assertIn('timeout', mock.call_args.kwargs)

    def test_tamil_to_english_direct_api(self):
        with patch.object(tr.requests, 'get', return_value=self._response(text='What')) as mock:
            value = tr.translate_mymemory_api('ta', 'en', 'என்ன')
        self.assertEqual(value, 'What')
        self.assertEqual(mock.call_args.kwargs['params']['langpair'], 'ta|en')

    def test_rejects_quota_exhaustion(self):
        response = self._response(text='MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS')
        with patch.object(tr.requests, 'get', return_value=response):
            with self.assertRaisesRegex(RuntimeError, 'allowance exhausted'):
                tr.translate_mymemory_api('en','ta','How')

    def test_api_rejects_long_utf8_and_auto(self):
        with self.assertRaisesRegex(ValueError, 'Text too long'):
            tr.translate_mymemory_api('ta','en','அ'*151)
        with self.assertRaisesRegex(ValueError, 'explicit source'):
            tr.translate_mymemory_api('auto','en','hello')

    def test_direct_provider_fallback_after_google_failure(self):
        with patch.object(tr, 'translate_mymemory', side_effect=RuntimeError('unavailable')), \
             patch.object(tr.GoogleTranslator,'translate',side_effect=RuntimeError('429')), \
             patch.object(tr.requests,'get',return_value=self._response()):
            value,provider=tr.translate_chunk('en','ta','How')
        self.assertEqual((value,provider),('எப்படி','MyMemory Direct API'))

    def test_history_failure_does_not_hide_translation(self):
        bot = base.FakeBot()
        message = SimpleNamespace(chat=SimpleNamespace(id=5),from_user=SimpleNamespace(id=7))
        with patch.object(tr,'save_translation',side_effect=RuntimeError('database unavailable')):
            tr.send_translation_result(bot,message,'en','ta','How','எப்படி','MyMemory')
        self.assertIn('எப்படி',bot.sent[0][1])

    def test_api_rejects_non_200_status(self):
        with patch.object(tr.requests, 'get', return_value=self._response(status=429)):
            with self.assertRaisesRegex(RuntimeError, 'status 429'):
                tr.translate_mymemory_api('en','ta','How')

if __name__=='__main__':
    unittest.main()
