"""Test core webhook security logic without importing Flask/TeleBot packages."""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent


def get_checked_secret():
    """Compile only the standalone validator from app.py to avoid external imports."""
    module = ast.parse((ROOT / 'app.py').read_text(encoding='utf8'))
    fn = next(x for x in module.body if isinstance(x, ast.FunctionDef) and x.name == 'checked_secret')
    safe_module = ast.Module(body=[fn], type_ignores=[])
    namespace = {'re': __import__('re')}
    exec(compile(safe_module, 'validator', 'exec'), namespace)
    return namespace['checked_secret']


class WebhookSecurityTests(unittest.TestCase):
    def test_valid_telegram_secret(self):
        f = get_checked_secret()
        self.assertEqual(f('a' * 32), 'a' * 32)
    def test_empty_or_short_secret_rejected(self):
        f = get_checked_secret()
        for value in ('', '1234567890', 'a' * 257, 'abc def' + 'x' * 20, 'a' * 20 + '\n'):
            with self.subTest(value=value), self.assertRaises(ValueError): f(value)
    def test_separate_token_env_used(self):
        code = (ROOT / 'app.py').read_text(encoding='utf8')
        self.assertIn('ADULT_GEMINI_BOT_TOKEN', code)
        self.assertIn('GEMINI_ADULT_USER_IDS', code)
        self.assertIn('hmac.compare_digest', code)
        self.assertIn('X-Telegram-Bot-Api-Secret-Token', code)
        self.assertNotIn('register_ai_study_assistant_handlers', code)
    def test_no_public_bot_overwrite(self):
        self.assertFalse((ROOT / 'main.py').exists())
        self.assertTrue((ROOT / 'gemini_ai_studio_v59.py').exists())


if __name__ == '__main__':
    unittest.main()
