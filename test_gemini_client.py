"""Offline contract tests for the existing tested Gemini 3.1 Flash-Lite client."""
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import gemini_ai_studio_v59 as gm


class DummyReply:
    def __init__(self, payload):
        self.data = json.dumps(payload).encode('utf-8')
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, maximum=-1):
        return self.data[:maximum]


class ClientTests(unittest.TestCase):
    def test_3_1_stable_model(self):
        self.assertEqual(gm.MODEL, 'gemini-3.1-flash-lite')
    def test_four_languages(self):
        self.assertEqual(set(gm.LANGUAGES), {'english', 'tamil', 'sinhala', 'arabic'})
    def test_tamil_payload(self):
        p = gm.build_payload('தமிழ் விளக்கம்', language='tamil')
        self.assertEqual(p['contents'][0]['parts'][0]['text'], 'தமிழ் விளக்கம்')
        self.assertIn('Tamil', p['systemInstruction']['parts'][0]['text'])
    def test_bad_question(self):
        with self.assertRaises(ValueError):
            gm.build_payload('')
    def test_http_payload_and_header(self):
        def intercept(req, timeout):
            self.assertEqual(req.full_url, gm.API_URL)
            self.assertEqual(req.headers.get('X-goog-api-key'), 'dummy-private-key')
            self.assertNotIn('dummy-private-key', req.full_url)
            self.assertEqual(json.loads(req.data)['contents'][0]['parts'][0]['text'], 'hello')
            return DummyReply({'candidates':[{'content':{'parts':[{'text':'வணக்கம்'}]}}]})
        with patch.object(gm.urllib.request, 'urlopen', side_effect=intercept):
            value = gm.GeminiClient('dummy-private-key').generate('hello')
        self.assertEqual(value, 'வணக்கம்')
    def test_429_error_does_not_leak_key(self):
        exc = HTTPError(gm.API_URL, 429, 'secret-do-not-log', {}, None)
        with patch.object(gm.urllib.request, 'urlopen', side_effect=exc):
            with self.assertRaises(gm.GeminiClientError) as ctx:
                gm.GeminiClient('my-private-key').generate('hello')
        self.assertNotIn('my-private-key', str(ctx.exception))
        self.assertNotIn('secret-do-not-log', str(ctx.exception))
    def test_urllib_failure_sanitized(self):
        with patch.object(gm.urllib.request, 'urlopen', side_effect=URLError('secret URL')):
            with self.assertRaises(gm.GeminiClientError) as ctx:
                gm.GeminiClient('example').generate('hello')
        self.assertNotIn('secret URL', str(ctx.exception))
    def test_reasoning_text_not_exposed(self):
        payload = {"candidates":[{"content":{"parts":[{"thought": True, "text":"hidden reasoning"}, {"text":"final answer"}]}}]}
        self.assertEqual(gm.extract_text(payload), "final answer")
    def test_empty_candidate_sanitized(self):
        with self.assertRaises(gm.GeminiClientError):
            gm.extract_text({'candidates':[]})


if __name__ == '__main__':
    unittest.main()
