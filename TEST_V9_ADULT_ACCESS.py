import os
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from UPDATE_V9_ADULT_ACCESS import edited, V8_OLD, V8_NEW, V9_OLD
import study_access_v9 as access

class UpdateTests(unittest.TestCase):
    def test_v8_patch_idempotent(self):
        source = V8_OLD + '\n' + 'def keep(): pass\n'
        result = edited('v8_bot.py', source)
        self.assertIn('STUDY_ACCESS_MODE', result)
        self.assertIn('def keep(): pass', result)
        self.assertEqual(result, edited('v8_bot.py', result))
    def test_v9_message_changes(self):
        result = edited('v9_bot.py', V9_OLD)
        self.assertIn('verified adult eligibility', result)
        self.assertEqual(result, edited('v9_bot.py', result))
    def test_fails_closed_unexpected_code(self):
        with self.assertRaises(ValueError):edited('v8_bot.py', 'def allowed(uid): return True')

class EligibilityTests(unittest.TestCase):
    def setUp(self):
        access._cache.clear()
    def _db(self, rows, exc=None):
        q = MagicMock()
        q.select.return_value = q
        q.eq.return_value = q
        q.limit.return_value = q
        if exc is not None:
            q.execute.side_effect = exc
        else:
            q.execute.return_value = types.SimpleNamespace(data=rows)
        db = MagicMock()
        db.table.return_value = q
        return db, q
    def _call(self, data=None, exc=None):
        db, q = self._db(data or [], exc)
        with patch.dict(sys.modules, {'db': types.SimpleNamespace(supabase=db)}):
            outcome = access.is_verified_adult(123)
        return outcome, db, q
    def test_unverified_denied(self):self.assertFalse(self._call([])[0])
    def test_network_failure_denied(self):self.assertFalse(self._call(exc=RuntimeError('db unavailable'))[0])
    def test_invalid_id_denied(self):
        for bad in (None, 0, -99, 'evil'):
            self.assertFalse(access.is_verified_adult(bad))
    def test_verified_active(self):
        expiry = (datetime.now(timezone.utc)+timedelta(days=10)).isoformat()
        good = {'user_id':123,'status':'verified','verification_method':'trusted_provider','valid_until':expiry}
        result, db, q = self._call([good])
        self.assertTrue(result)
        self.assertEqual(db.table.call_args.args[0], 'study_verified_adults')
    def test_expired_denied(self):
        expiry = (datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
        self.assertFalse(self._call([{'user_id':123,'status':'verified','verification_method':'manual_review','valid_until':expiry}])[0])
    def test_self_attestation_not_enough(self):
        expiry = (datetime.now(timezone.utc)+timedelta(days=3)).isoformat()
        self.assertFalse(self._call([{'user_id':123,'status':'verified','verification_method':'self_attested','valid_until':expiry}])[0])
    def test_revoked_denied(self):
        expiry = (datetime.now(timezone.utc)+timedelta(days=10)).isoformat()
        self.assertFalse(self._call([{'user_id':123,'status':'revoked','verification_method':'trusted_provider','valid_until':expiry}])[0])
    def test_wrong_user_denied(self):
        expiry = (datetime.now(timezone.utc)+timedelta(days=10)).isoformat()
        self.assertFalse(self._call([{'user_id':456,'status':'verified','verification_method':'trusted_provider','valid_until':expiry}])[0])
    def test_timezone_missing_denied(self):
        self.assertFalse(self._call([{'user_id':123,'status':'verified','verification_method':'trusted_provider','valid_until':'2030-01-01T12:00:00'}])[0])


class AuthorizationModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import telebot
        except ImportError:
            import types
            mod = types.ModuleType('telebot')
            class Keyboard:
                def __init__(self,*args,**kwargs): self.buttons = []
                def row(self,*args): self.buttons.append(args)
            mod.types = types.SimpleNamespace(ReplyKeyboardMarkup=Keyboard, KeyboardButton=lambda x:x)
            backend = types.ModuleType('telebot.handler_backends')
            backend.ContinueHandling = type('ContinueHandling', (), {})
            sys.modules['telebot'] = mod
            sys.modules['telebot.handler_backends'] = backend
        from v8_bot import allowed
        cls.access_fn = staticmethod(allowed)

    def test_pilot_defaults_to_allowlist(self):
        with patch.dict(os.environ, {'V8_ENABLED':'true','V8_ALLOWED_USER_IDS':'123','STUDY_ACCESS_MODE':'pilot'}):
            self.assertTrue(self.access_fn(123))
            self.assertFalse(self.access_fn(456))

    def test_verified_adults_mode_requires_registry(self):
        with patch.dict(os.environ, {'V8_ENABLED':'true','STUDY_ACCESS_MODE':'verified_adults'}):
            with patch('study_access_v9.is_verified_adult', return_value=True) as check:
                self.assertTrue(self.access_fn(123))
                check.assert_called_once_with(123)
            with patch('study_access_v9.is_verified_adult', return_value=False):
                self.assertFalse(self.access_fn(999))

    def test_unknown_mode_denied(self):
        with patch.dict(os.environ, {'V8_ENABLED':'true','STUDY_ACCESS_MODE':'public','V8_ALLOWED_USER_IDS':'123'}):
            self.assertFalse(self.access_fn(123))

    def test_disabled_denied_even_if_verified(self):
        with patch.dict(os.environ, {'V8_ENABLED':'false','STUDY_ACCESS_MODE':'verified_adults'}):
            with patch('study_access_v9.is_verified_adult', return_value=True) as check:
                self.assertFalse(self.access_fn(123))
                check.assert_not_called()

if __name__ == '__main__':unittest.main()
