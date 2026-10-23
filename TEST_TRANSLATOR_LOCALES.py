"""Offline regression tests for proper MyMemory locale codes."""
import unittest
from unittest.mock import patch
import TEST_TRANSLATOR_FIX as base

translator = base.translator

class LocaleTests(unittest.TestCase):
    def setUp(self):
        translator.translation_cache.clear()

    def test_mymemory_en_to_tamil_uses_regional_codes(self):
        class MockMyMemory:
            def __init__(self, source, target):
                self.source = source
                self.target = target
                if (source, target) != ("en-GB", "ta-LK"):
                    raise ValueError("MyMemory expects a regional language pair")
            def translate(self, text):
                return "எப்படி"
        with patch.object(translator, "MyMemoryTranslator", MockMyMemory):
            with patch.object(translator.GoogleTranslator, "translate", side_effect=AssertionError("Google should not run")):
                value, provider = translator.translate_chunk("en", "ta", "How")
        self.assertEqual((value, provider), ("எப்படி", "MyMemory"))

    def test_sinhala_and_arabic_mappings(self):
        self.assertEqual(translator.MYMEMORY_LOCALES["si"], "si-LK")
        self.assertEqual(translator.MYMEMORY_LOCALES["ar"], "ar-SA")

    def test_google_fallback_keeps_original_short_codes(self):
        class BrokenMyMemory:
            def __init__(self, **kwargs):
                raise RuntimeError("MyMemory unavailable")
        args = []
        class WorkingGoogle:
            def __init__(self, source, target):
                args.extend([source,target])
            def translate(self, text):
                return "எப்படி"
        with patch.object(translator, "MyMemoryTranslator", BrokenMyMemory), patch.object(translator, "GoogleTranslator", WorkingGoogle):
            value, provider = translator.translate_chunk("en", "ta", "How")
        self.assertEqual(args, ["en", "ta"])
        self.assertEqual((value, provider), ("எப்படி", "Google"))

    def test_large_text_skips_mymemory(self):
        with self.assertRaisesRegex(ValueError, "Text too long"):
            translator.translate_mymemory("en", "ta", "a" * 451)

    def test_cache_prevents_repeated_provider_calls(self):
        translator.cache_save(("en","ta","How"), "எப்படி")
        with patch.object(translator, "translate_mymemory", side_effect=AssertionError("Should use cache")):
            value, provider = translator.translate_chunk("en", "ta", "How")
        self.assertEqual((value,provider), ("எப்படி", "Cache"))

if __name__ == "__main__":
    unittest.main()
