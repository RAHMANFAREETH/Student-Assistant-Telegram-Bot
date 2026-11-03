"""Standalone verification of the guarded V12.0.1 test compatibility patch."""
import tempfile
import unittest
from pathlib import Path
import INSTALL_V120_TEST_COMPAT_FIX as fix

SUPER = '''    def test_requires_signed_login_and_adult(self):
        with patch.dict(sys.modules, {'v8_miniapp':fake_v8,'study_access_v9':fake_age}):
            with patch.dict(os.environ, {'BOT_TOKEN':'secret'}):
                self.assertEqual(module.verify_super_session('valid'),44)
                with self.assertRaises(AuthError):module.verify_super_session('invalid')
                fake_age.is_verified_adult=lambda uid:False
                with self.assertRaises(PermissionError):module.verify_super_session('valid')
    def test_safe_security_headers(self):
        pass
'''
AUDIT = '''    def test_ui_categories_unchanged(self):
        from navigation import MAIN_MENU_ROWS, GLOBAL_BUTTONS
        self.assertEqual(sum(len(row) for row in MAIN_MENU_ROWS), 11)
    def test_finder_covers_legacy_and_new_tools(self):
        pass
'''

class TestCompat(unittest.TestCase):
    def test_super_test_is_safe_and_idempotent(self):
        new=fix.update_super_test(SUPER)
        self.assertIn("'SUPER_MINIAPP_V120_REQUIRE_ADULT':'true'",new)
        self.assertIn("'SUPER_MINIAPP_V120_REQUIRE_ADULT':'false'",new)
        self.assertIn('assertRaises(AuthError)',new)
        self.assertEqual(fix.update_super_test(new),new)
        compile('class C:\n'+new, 'test_super.py', 'exec')
    def test_audit_does_not_hide_duplicate_buttons(self):
        new=fix.update_audit_test(AUDIT)
        self.assertIn('self.assertIn(occurrences, (0, 1))',new)
        self.assertIn('11 + occurrences',new)
        self.assertIn('📚 Book Library',new)
        self.assertEqual(fix.update_audit_test(new),new)
        compile('class C:\n'+new, 'test_audit.py', 'exec')
    def test_missing_anchors_abort_before_write(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'TEST_SUPER_MINIAPP_V120.py').write_text('class C:\n'+SUPER,encoding='utf-8')
            (p/'TEST_V7_9_AUDIT.py').write_text('UNRELATED',encoding='utf-8')
            with self.assertRaises(ValueError): fix.process(p,True)
            self.assertEqual((p/'TEST_SUPER_MINIAPP_V120.py').read_text(), 'class C:\n'+SUPER)
    def test_apply_twice_and_preserve_other_files(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'TEST_SUPER_MINIAPP_V120.py').write_text('class C:\n'+SUPER,encoding='utf-8')
            (p/'TEST_V7_9_AUDIT.py').write_text('class C:\n'+AUDIT,encoding='utf-8')
            (p/'main.py').write_text('preserve',encoding='utf-8')
            modes=fix.process(p,False)
            self.assertEqual(list(modes.values()),['UPDATE','UPDATE'])
            fix.process(p,True)
            modes=fix.process(p,True)
            self.assertEqual(list(modes.values()),['UNCHANGED','UNCHANGED'])
            self.assertEqual((p/'main.py').read_text(),'preserve')

if __name__=='__main__':unittest.main()
