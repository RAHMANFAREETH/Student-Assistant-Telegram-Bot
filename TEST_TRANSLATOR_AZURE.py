"""Unit tests for Azure API requests, fallback, caching and rate-limit protection."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from TEST_TRANSLATOR_FIX import translator as tr

class AzureTests(unittest.TestCase):
    def setUp(self):
        tr.translation_cache.clear()
        tr.provider_blocked_until.clear()

    def fake_response(self, text="வணக்கம்", status=200):
        return SimpleNamespace(status_code=status, json=lambda: [{"translations": [{"text": text}]}])

    def test_official_english_to_tamil(self):
        with patch.object(tr, "AZURE_TRANSLATOR_KEY", "test-not-real"), patch.object(tr, "AZURE_TRANSLATOR_REGION", "global"), patch.object(tr.requests,"post",return_value=self.fake_response()) as post:
            translated, provider = tr.translate_chunk("en", "ta", "hello")
        self.assertEqual((translated,provider),("வணக்கம்","Azure Translator"))
        self.assertEqual(post.call_args.kwargs["params"]["from"],"en")
        self.assertEqual(post.call_args.kwargs["params"]["to"],"ta")
        self.assertEqual(post.call_args.kwargs["headers"]["Ocp-Apim-Subscription-Region"],"global")
        self.assertEqual(post.call_args.kwargs["json"],[{"Text":"hello"}])
        self.assertIn("timeout",post.call_args.kwargs)

    def test_auto_language_omits_from(self):
        with patch.object(tr,"AZURE_TRANSLATOR_KEY","test-not-real"), patch.object(tr.requests,"post",return_value=self.fake_response(text="what")) as post:
            result = tr.translate_azure("auto","en","என்ன")
        self.assertEqual(result,"what")
        self.assertNotIn("from",post.call_args.kwargs["params"])

    def test_invalid_key_does_not_use_public_services(self):
        with patch.object(tr,"AZURE_TRANSLATOR_KEY","bad-key"), patch.object(tr.requests,"post",return_value=self.fake_response(status=401)), patch.object(tr,"translate_mymemory") as public:
            with self.assertRaisesRegex(RuntimeError,"Azure Translator failed"):
                tr.translate_chunk("en","ta","hello")
            public.assert_not_called()

    def test_cache_prevents_duplicate_billing(self):
        with patch.object(tr,"AZURE_TRANSLATOR_KEY","test-not-real"), patch.object(tr.requests,"post",return_value=self.fake_response()) as post:
            first=tr.translate_chunk("en","ta","hello")
            second=tr.translate_chunk("en","ta","hello")
        self.assertEqual(first[1],"Azure Translator")
        self.assertEqual(second[1],"Cache")
        self.assertEqual(post.call_count,1)

    def test_public_rate_limited_service_is_skipped_subsequently(self):
        # Prevent network access: all endpoints fail. MyMemory reports HTTP 429.
        with patch.object(tr,"AZURE_TRANSLATOR_KEY",""), patch.object(tr,"translate_mymemory",side_effect=RuntimeError("HTTP 429")) as mm, patch.object(tr.GoogleTranslator,"translate",side_effect=RuntimeError("offline")), patch.object(tr,"translate_mymemory_api",side_effect=RuntimeError("offline")), patch.object(tr,"translate_google_endpoint",side_effect=RuntimeError("offline")):
            for word in ("hello","goodbye"):
                with self.assertRaises(RuntimeError):
                    tr.translate_chunk("en","ta",word)
        self.assertEqual(mm.call_count,1)
        self.assertIn("MyMemory",tr.provider_blocked_until)

    def test_invalid_data_fails_cleanly(self):
        fake = SimpleNamespace(status_code=200, json=lambda: {})
        with patch.object(tr,"AZURE_TRANSLATOR_KEY","test-not-real"), patch.object(tr.requests,"post",return_value=fake):
            with self.assertRaisesRegex(ValueError,"invalid response"):
                tr.translate_azure("en","ta","hello")

if __name__=='__main__': unittest.main()
