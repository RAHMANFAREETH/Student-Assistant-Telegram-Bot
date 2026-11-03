"""Offline tests for Cloudflare HTTP diagnostics (no external API calls)."""
import contextlib
import io
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from TEST_V5_5_AI import ai


class CloudflareDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict('os.environ', {
            'CLOUDFLARE_ACCOUNT_ID': 'a' * 32,
            'CLOUDFLARE_API_TOKEN': 'private-test-token',
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def assert_status_logged(self, status, expected_code):
        resp = SimpleNamespace(status_code=status)
        buf = io.StringIO()
        with patch.object(ai.requests, 'post', return_value=resp), contextlib.redirect_stdout(buf):
            with self.assertRaises(ai.AIUnavailable) as err:
                ai._provider_call(ai.CF_MODEL, [{"role": "user", "content": "test prompt secret"}], 64)
        output = buf.getvalue()
        self.assertEqual(err.exception.code, expected_code)
        self.assertIn(f'HTTP Status: {status}', output)
        self.assertIn(ai.CF_MODEL, output)
        self.assertNotIn('private-test-token', output)
        self.assertNotIn('test prompt secret', output)

    def test_logs_auth_401_before_raising(self):
        self.assert_status_logged(401, 'auth')

    def test_logs_auth_403_before_raising(self):
        self.assert_status_logged(403, 'auth')

    def test_logs_rate_limit_429_before_raising(self):
        self.assert_status_logged(429, 'rate_limit')

    def test_logs_service_error_503_before_raising(self):
        self.assert_status_logged(503, 'http_503')

    def test_logs_success_200_without_secrets(self):
        resp = SimpleNamespace(status_code=200, json=lambda: {
            'success': True, 'result': {'response': 'Hello!'}
        })
        buf = io.StringIO()
        with patch.object(ai.requests, 'post', return_value=resp), contextlib.redirect_stdout(buf):
            out = ai._provider_call(ai.CF_MODEL, [{"role": "user", "content": "secret test prompt"}], 64)
        self.assertEqual(out, 'Hello!')
        self.assertIn('HTTP Status: 200', buf.getvalue())
        self.assertNotIn('private-test-token', buf.getvalue())
        self.assertNotIn('secret test prompt', buf.getvalue())


if __name__ == '__main__':
    unittest.main()
