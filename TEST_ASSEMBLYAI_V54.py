import os
import unittest
from unittest.mock import patch

import speech_to_text as stt


class FakeResponse:
    def __init__(self, body=None, status=200):
        self.body = body or {}
        self.status_code = status

    def json(self):
        return self.body


class AssemblyTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_unconfigured(self):
        self.assertFalse(stt.stt_is_configured())
        with self.assertRaisesRegex(RuntimeError, "not configured"):
            stt._headers()

    @patch.dict(os.environ, {"ASSEMBLYAI_API_KEY": "TEST_KEY"})
    def test_authorization(self):
        self.assertEqual(stt._headers(), {"authorization": "TEST_KEY"})

    def test_empty_audio(self):
        with self.assertRaisesRegex(ValueError, "No audio data"):
            stt.upload_audio(b"")

    def test_oversize(self):
        with self.assertRaisesRegex(ValueError, "too large"):
            stt.upload_audio(b"x" * (stt.MAX_AUDIO_BYTES + 1))

    @patch.dict(os.environ, {"ASSEMBLYAI_API_KEY": "TEST_KEY"})
    @patch("speech_to_text.requests.post")
    def test_upload(self, post):
        post.return_value = FakeResponse({"upload_url": "https://cdn.example/audio"})
        self.assertEqual(stt.upload_audio(b"voice"), "https://cdn.example/audio")
        self.assertEqual(post.call_args.kwargs["data"], b"voice")

    @patch.dict(os.environ, {"ASSEMBLYAI_API_KEY": "TEST_KEY"})
    @patch("speech_to_text.requests.post")
    @patch("speech_to_text.requests.get")
    def test_multilingual_completed(self, get, post):
        post.side_effect = [
            FakeResponse({"upload_url": "https://cdn.example/voice"}),
            FakeResponse({"id": "example_job"}),
        ]
        get.side_effect = [
            FakeResponse({"status": "processing"}),
            FakeResponse({"status": "completed", "text": "வணக்கம்", "language_code": "ta"}),
        ]
        with patch("speech_to_text.time.sleep"):
            result = stt.transcribe_audio(b"audio")
        self.assertEqual(result["text"], "வணக்கம்")
        self.assertEqual(result["language_code"], "ta")
        self.assertEqual(post.call_args.kwargs["json"]["speech_models"], ["universal-2"])
        self.assertTrue(post.call_args.kwargs["json"]["language_detection"])

    @patch.dict(os.environ, {"ASSEMBLYAI_API_KEY": "TEST_KEY"})
    @patch("speech_to_text.requests.post")
    @patch("speech_to_text.requests.get")
    def test_failed_transcript(self, get, post):
        post.side_effect = [
            FakeResponse({"upload_url": "https://cdn.example/voice"}),
            FakeResponse({"id": "example_job"}),
        ]
        get.return_value = FakeResponse({"status": "error", "error": "private internal data"})
        with self.assertRaisesRegex(RuntimeError, "could not transcribe") as ctx:
            stt.transcribe_audio(b"audio")
        self.assertNotIn("private", str(ctx.exception))

    @patch.dict(os.environ, {"ASSEMBLYAI_API_KEY": "TEST_KEY"})
    @patch("speech_to_text.requests.post")
    def test_api_429(self, post):
        post.return_value = FakeResponse({}, status=429)
        with self.assertRaisesRegex(RuntimeError, "rate limit"):
            stt.upload_audio(b"audio")

    def test_api_401(self):
        with self.assertRaisesRegex(RuntimeError, "authentication failed"):
            stt._checked_json(FakeResponse({}, status=401))

    def test_api_402(self):
        with self.assertRaisesRegex(RuntimeError, "credits may be exhausted"):
            stt._checked_json(FakeResponse({}, status=402))

    def test_api_500(self):
        with self.assertRaisesRegex(RuntimeError, "temporarily unavailable"):
            stt._checked_json(FakeResponse({}, status=500))

    def test_invalid_response(self):
        with self.assertRaisesRegex(RuntimeError, "unexpected response"):
            stt._checked_json(FakeResponse(["bad"]))


if __name__ == "__main__":
    unittest.main()
