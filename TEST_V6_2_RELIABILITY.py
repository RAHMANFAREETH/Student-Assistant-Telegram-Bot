"""Offline, isolated V6.2 tests: no Telegram, Cloudflare, Gemini or DB requests."""
from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import ai_reliability_v62 as health
import ai_ops_v60 as ops
import INSTALL_V6_2 as installer

CF = '@cf/qwen/qwen3-30b-a3b-fp8'
GUARD = '@cf/meta/llama-guard-3-8b'


class HealthTests(unittest.TestCase):
    def setUp(self):
        with health._LOCK:
            health._EVENTS.clear()

    def test_no_recent_calls_is_not_live_health_check(self):
        with patch.dict(os.environ, {'CLOUDFLARE_ACCOUNT_ID': 'x', 'CLOUDFLARE_API_TOKEN':'secret'}, clear=True):
            report = health.format_health_report()
        self.assertIn('NO RECENT CALLS', report)
        self.assertIn('not a live provider probe', report)
        self.assertNotIn('secret', report)

    def test_success_response_and_original_arguments(self):
        received = []
        def provider(model, messages, tokens):
            received.append((model, messages, tokens))
            return 'An accurate and helpful answer about study methods.'
        wrapped = health.observe_cloudflare_health(provider)
        secret = 'PRIVATE STUDENT NOTE 012345'
        reply = wrapped(CF, [{'role':'user', 'content':secret}], 180)
        self.assertEqual(reply, 'An accurate and helpful answer about study methods.')
        self.assertEqual(received[0][1][0]['content'], secret)
        self.assertIs(health.observe_cloudflare_health(wrapped), wrapped)
        snap = health.recent_snapshot()
        self.assertEqual(snap['generation_ok'], 1)
        self.assertNotIn(secret, str(snap))
        self.assertNotIn('012345', health.format_health_report())

    def test_exception_same_instance_and_secret_not_retained(self):
        class Failure(RuntimeError):
            code = 'rate_limit'
        exc = Failure('PRIVATE GOOGLE KEY / study prompt')
        def broken(*args):
            raise exc
        with self.assertRaises(Failure) as caught:
            health.observe_cloudflare_health(broken)(CF, [{'content':'sensitive'}], 10)
        self.assertIs(caught.exception, exc)
        snap = health.recent_snapshot()
        self.assertEqual(snap['errors'], {'rate_limit':1})
        self.assertNotIn('PRIVATE', str(snap))
        self.assertIn('RATE LIMITED', health.format_health_report() if os.getenv('CLOUDFLARE_ACCOUNT_ID') and os.getenv('CLOUDFLARE_API_TOKEN') else health._status(snap, True)[0])

    def test_unknown_exception_code_is_sanitized(self):
        class Failure(ValueError):
            code = 'top-private-string'
        with self.assertRaises(Failure):
            health.observe_cloudflare_health(lambda *args: (_ for _ in ()).throw(Failure('secret')))(CF, [], 3)
        self.assertEqual(health.recent_snapshot()['errors'], {'other_error':1})

    def test_safety_call_and_response_length_proxy(self):
        health.observe_cloudflare_health(lambda *args: 'safe')(GUARD, [], 3)
        health.observe_cloudflare_health(lambda *args: '2')(CF, [], 3)
        snap = health.recent_snapshot()
        self.assertEqual(snap['safety_ok'], 1)
        self.assertEqual(snap['brief_generation_answers'], 1)
        self.assertIn('not a quality score', health.format_health_report())

    def test_recent_window_prunes_old_events(self):
        health.record_event('generation','ok', at=100)
        health.record_event('generation','error','timeout',at=101)
        health.record_event('safety','ok',at=1100)
        snap = health.recent_snapshot(now=1100)
        self.assertEqual(snap['generation_ok'], 0)
        self.assertEqual(snap['generation_failed'], 0)
        self.assertEqual(snap['safety_ok'], 1)
        self.assertFalse(snap['errors'])

    def test_bounded_memory_and_p95(self):
        for i in range(330):
            health.record_event('generation','ok',duration_ms=i,at=100+i/1000)
        snap = health.recent_snapshot(now=101)
        self.assertTrue(snap['sample_truncated'])
        self.assertEqual(snap['generation_ok'], 300)
        self.assertGreater(snap['p95_generation_ms'], 250)
        self.assertEqual(len(health._EVENTS),300)

    def test_http429_and_auth_have_actionable_categories(self):
        health.record_event('generation', 'error', 'http_429')
        s = health.recent_snapshot()
        self.assertEqual(health._status(s, True)[0], 'RATE LIMITED')
        health.record_event('generation', 'error', 'auth')
        self.assertEqual(health._status(health.recent_snapshot(), True)[0], 'ACTION NEEDED')

    def test_failure_threshold_needs_five_samples(self):
        for _ in range(2):
            health.record_event('generation', 'error', 'timeout')
        self.assertEqual(health._status(health.recent_snapshot(), True)[0], 'SOME FAILURES')
        for _ in range(3):
            health.record_event('generation', 'ok')
        self.assertEqual(health._status(health.recent_snapshot(), True)[0], 'ELEVATED FAILURES')

    def test_no_remaining_quota_claim(self):
        with patch.dict(os.environ, {'AI_DAILY_LIMIT':'8', 'CLOUDFLARE_ACCOUNT_ID':'x', 'CLOUDFLARE_API_TOKEN':'secret'}):
            txt = health.format_health_report()
        self.assertIn('8 requests per student', txt)
        self.assertIn('remaining RPM/RPD/tokens: unknown', txt)
        self.assertNotIn('secret', txt)

    def test_cli_does_not_call_network(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(health.main(), 0)
        self.assertIn('does not contact Cloudflare or Gemini', out.getvalue())

    def test_extreme_error_values_sanitized(self):
        health.record_event('private', 'unexpected', 'super-secret', duration_ms=-300)
        snap = health.recent_snapshot()
        self.assertEqual(snap['other_calls'], 1)
        self.assertEqual(snap['errors'], {'other_error':1})
        self.assertNotIn('super-secret', str(snap))


class FakeBot:
    def __init__(self):
        self.sent = []
        self.registered = []
    def message_handler(self, **kwargs):
        self.registered.append(kwargs)
        return lambda fn: fn
    def send_message(self, chat_id, body):
        self.sent.append((chat_id, body))


def message(uid=23, text='/aihealth', kind='private', chat_id=42):
    return SimpleNamespace(from_user=SimpleNamespace(id=uid),
                           chat=SimpleNamespace(type=kind, id=chat_id), text=text)


class AdminCommandTests(unittest.TestCase):
    def setUp(self):
        with health._LOCK:
            health._EVENTS.clear()

    def test_admin_private_aihealth_and_original_aiops(self):
        bot = FakeBot()
        handler = ops.register_ai_ops_v60_handlers(bot)['admin_command']
        with patch.dict(os.environ, {'AI_OPS_ADMIN_IDS':'23', 'CLOUDFLARE_ACCOUNT_ID':'x', 'CLOUDFLARE_API_TOKEN':'secret'}):
            handler(message())
            self.assertIn('AI Reliability V6.2', bot.sent[-1][1])
            handler(message(text='/aihealth@MyBot'))
            self.assertIn('AI Reliability V6.2', bot.sent[-1][1])
            handler(message(text='/aiops'))
            self.assertIn('AI Operations V6.0', bot.sent[-1][1])
        self.assertIn('aihealth', bot.registered[0]['commands'])
        self.assertNotIn('secret', str(bot.sent))

    def test_non_admin_and_group_denied(self):
        bot = FakeBot()
        handler = ops.register_ai_ops_v60_handlers(bot)['admin_command']
        with patch.dict(os.environ, {'AI_OPS_ADMIN_IDS':'23'}):
            handler(message(uid=24))
            self.assertIn('not enabled', bot.sent[-1][1])
            handler(message(kind='group'))
            self.assertIn('private chat', bot.sent[-1][1])
            self.assertNotIn('AI Reliability', str(bot.sent))

    def test_no_user_id_in_snapshot(self):
        with patch.dict(os.environ, {'AI_OPS_ADMIN_IDS':'9283770'}):
            health.record_event('generation','ok')
            self.assertNotIn('9283770', str(health.recent_snapshot()))


class InstallerTests(unittest.TestCase):
    AI_SRC = '''def register_ai_study_assistant_handlers(bot, show_main_menu):\n    pass\n\n# V6.0 aggregate Cloudflare monitoring (no prompt data)\nfrom ai_ops_v60 import wrap_cloudflare_provider\n_provider_call = wrap_cloudflare_provider(_provider_call)\n'''

    def test_patches_existing_sources_and_idempotence(self):
        ai_src, a = installer.patch_ai(self.AI_SRC)
        self.assertTrue(a)
        self.assertIn(installer.AI_MARKER, ai_src)
        self.assertEqual(installer.patch_ai(ai_src), (ai_src, False))
        ops_src = Path(ops.__file__).read_text(encoding='utf-8')
        # Current test environment must already have V6.2 installed.
        self.assertEqual(installer.patch_ops(ops_src), (ops_src, False))
        self.assertIn('commands=["aiops", "aiproviders", "aihealth"]', ops_src)

    def test_preflight_invalid_version_does_not_touch_files(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/installer.MAIN).write_text('pass\n', encoding='utf-8')
            (p/installer.AI).write_text('pass\n',encoding='utf-8')
            (p/installer.OPS).write_text('pass\n',encoding='utf-8')
            (p/installer.MODULE).write_text('pass\n',encoding='utf-8')
            (p/installer.V61).write_text('pass\n',encoding='utf-8')
            with self.assertRaises(ValueError):
                installer.run_install(p)
            self.assertEqual((p/installer.AI).read_text(encoding='utf-8'), 'pass\n')
            self.assertFalse(list(p.glob('*.bak')))

    def test_existing_v61_and_windows_utf8_backups(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            orig_ops = Path(ops.__file__).read_text(encoding='utf-8')
            # derive original V6.1 version by removing V6.2 modifications
            orig_ops = orig_ops.replace(installer.OPS_NEW_COMMANDS, installer.OPS_OLD_COMMANDS)
            orig_ops = orig_ops.replace(installer.OPS_NEW_SEND, installer.OPS_OLD_SEND)
            files = {installer.MAIN: 'pass\n', installer.AI: self.AI_SRC+'# தமிழ்\n',
                     installer.OPS: orig_ops, installer.MODULE: '#module\n', installer.V61: '#v61\n'}
            for name, src in files.items():
                (p/name).write_bytes(src.replace('\n','\r\n').encode('utf-8'))
            changes = installer.run_install(p)
            self.assertEqual(changes, sorted([installer.AI, installer.OPS]))
            self.assertTrue((p/(installer.AI+'.before_v62.bak')).is_file())
            self.assertTrue((p/(installer.OPS+'.before_v62.bak')).is_file())
            self.assertEqual(installer.run_install(p), [])
            self.assertIn('தமிழ்'.encode('utf-8'), (p/installer.AI).read_bytes())

    def test_duplicate_backup_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            for name, src in {installer.MAIN:'pass',installer.AI:self.AI_SRC,
                              installer.OPS:'pass', installer.MODULE:'pass',installer.V61:'pass'}.items():
                (p/name).write_text(src,encoding='utf-8')
            (p/(installer.AI+'.before_v62.bak')).write_text('do not replace',encoding='utf-8')
            # OPS preflight rejects invalid older version before reaching backup stage
            with self.assertRaises(ValueError):
                installer.run_install(p)
            self.assertEqual((p/(installer.AI+'.before_v62.bak')).read_text(encoding='utf-8'), 'do not replace')


if __name__ == '__main__':
    unittest.main()
