"""Offline installation regression tests for complete multilingual AI answers."""
from __future__ import annotations

import ast
from pathlib import Path
import tempfile
import unittest

import INSTALL_V6_2_2 as install


class CompleteAnswerTests(unittest.TestCase):
    @staticmethod
    def source():
        return '''MAX_OUTPUT_TOKENS = 650
CF_MODEL = "qwen3"
GUARD_MODEL = "llamaguard"
def _system_prompt(mode):
    base = (
        "You are a student assistant. "
        "Respond in the student's language (Tamil, Sinhala, English, or Arabic), unless they request another. "
        "Do not leak secrets. "
    )
    return base

def _provider_call(model, messages, max_tokens):
    return 'test'

def _check_safety(text):
    return True

def _process_question(answer):
    return split_telegram_text(answer, limit=3500)

# V6.0 aggregate Cloudflare monitoring (no prompt data)
_provider_call = wrap_cloudflare_provider(_provider_call)
# V6.2 passive Cloudflare health observation (never changes outputs)
_provider_call = observe_cloudflare_health(_provider_call)
'''

    def test_increases_generation_limit_only(self):
        patched, did = install.patch_ai(self.source())
        self.assertTrue(did)
        self.assertIn('MAX_OUTPUT_TOKENS = 1800', patched)
        self.assertNotIn('MAX_OUTPUT_TOKENS = 650', patched)
        self.assertEqual(patched.count('MAX_OUTPUT_TOKENS = 1800'), 1)
        self.assertIn('GUARD_MODEL = "llamaguard"', patched)
        self.assertIn('observe_cloudflare_health(_provider_call)', patched)
        self.assertIn('wrap_cloudflare_provider(_provider_call)', patched)
        self.assertIn('split_telegram_text(answer, limit=3500)', patched)
        ast.parse(patched)

    def test_system_prompt_wants_finished_examples_and_plain_text(self):
        patched, _ = install.patch_ai(self.source())
        self.assertIn('finish every requested item', patched)
        self.assertIn('without Markdown symbols', patched)
        self.assertEqual(install.patch_ai(patched), (patched, False))

    def test_preserves_windows_line_endings(self):
        old = self.source().replace('\n', '\r\n')
        patched, _ = install.patch_ai(old)
        self.assertIn('MAX_OUTPUT_TOKENS = 1800\r\n', patched)
        self.assertNotIn('\r\r\n', patched)
        self.assertEqual(install.patch_ai(patched), (patched, False))
        ast.parse(patched)

    def test_does_not_patch_unknown_code(self):
        original = 'print("nothing")\n'
        with self.assertRaises(ValueError):
            install.patch_ai(original)

    def test_safe_backup_and_repeat(self):
        with tempfile.TemporaryDirectory() as path:
            root = Path(path)
            file = root / install.NAME
            file.write_text(self.source(), encoding='utf-8')
            self.assertTrue(install.run(root))
            backup = root / (install.NAME + '.before_v622.bak')
            self.assertEqual(backup.read_text(encoding='utf-8'), self.source())
            self.assertFalse(install.run(root))

    def test_no_backup_on_failed_preflight(self):
        with tempfile.TemporaryDirectory() as path:
            root = Path(path)
            file = root / install.NAME
            file.write_text('print("old")', encoding='utf-8')
            with self.assertRaises(ValueError):
                install.run(root)
            self.assertFalse(list(root.glob('*.bak')))
            self.assertEqual(file.read_text(encoding='utf-8'), 'print("old")')

if __name__ == '__main__':
    unittest.main()
