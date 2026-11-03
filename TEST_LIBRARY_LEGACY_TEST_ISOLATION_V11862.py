"""Unit checks for V11.8.6.2 test-only patch mechanics."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from PATCH_LIBRARY_LEGACY_TESTS_V11862 import RULES, MARK, transform, plan

class InstallerTests(unittest.TestCase):
    def test_targets_only_legacy_test_modules(self):
        self.assertEqual(set(RULES),{
            'TEST_BOOK_LIBRARY.py','TEST_BOOK_LIBRARY_V112.py',
            'TEST_BOOK_LIBRARY_PRIVACY_V114.py','TEST_BOOK_PUBLIC_LATEST5.py'})
    def test_is_idempotent(self):
        root=Path(__file__).parent
        for name in RULES:
            with self.subTest(name=name):
                source=(root/name).read_text(encoding='utf-8')
                self.assertIn(MARK, source)
                self.assertEqual(transform(name, source), source)
    def test_rejects_unknown_source(self):
        for name in RULES:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):transform(name,'# unrelated code')
    def test_check_has_no_changes_after_apply(self):
        root=Path(__file__).parent
        with TemporaryDirectory() as temp:
            dst=Path(temp)
            for name in RULES:
                (dst/name).write_bytes((root/name).read_bytes())
            self.assertEqual(plan(dst),{})

if __name__=='__main__': unittest.main()
