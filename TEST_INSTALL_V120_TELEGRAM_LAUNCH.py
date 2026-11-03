import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import INSTALL_V120_TELEGRAM_LAUNCH as mod

BASE_MAIN = 'from super_miniapp_v120 import register_super_miniapp\nregister_super_miniapp(app)\n\n' + mod.MAIN_ANCHOR + '\n'
BASE_APP = '''def verify_super_session(raw):
    uid = 1
    return uid


def register_super_miniapp(app):
    pass
'''

class TestInstaller(unittest.TestCase):
    def test_preview_and_idempotence(self):
        new_main,new_app=mod.plan(BASE_MAIN,BASE_APP)
        self.assertIn('register_super_app_launcher(bot)',new_main)
        self.assertIn('pilot_access_allowed(uid)',new_app)
        self.assertEqual(mod.plan(new_main,new_app),(new_main,new_app))

    def test_wrong_main_anchor_fails(self):
        with self.assertRaises(ValueError):mod.plan(BASE_MAIN.replace(mod.MAIN_ANCHOR,'NO HELP'),BASE_APP)

    def test_wrong_app_anchor_fails(self):
        with self.assertRaises(ValueError):mod.plan(BASE_MAIN,BASE_APP.replace('return uid','return None'))

    def test_refuses_missing_source(self):
        with TemporaryDirectory() as td:
            d=Path(td);(d/'main.py').write_text(BASE_MAIN);(d/'super_miniapp_v120.py').write_text(BASE_APP)
            with patch.object(mod,'HERE',d), patch.object(mod,'MAIN',d/'main.py'), patch.object(mod,'APP',d/'super_miniapp_v120.py'):
                with self.assertRaises(ValueError):mod.run(False)

    def test_dry_run_apply_and_repeat(self):
        with TemporaryDirectory() as td:
            d=Path(td);(d/'main.py').write_text(BASE_MAIN);(d/'super_miniapp_v120.py').write_text(BASE_APP)
            (d/'super_miniapp_v120_launch.py').write_text('')
            with patch.object(mod,'HERE',d), patch.object(mod,'MAIN',d/'main.py'), patch.object(mod,'APP',d/'super_miniapp_v120.py'):
                mod.run(False)
                self.assertEqual((d/'main.py').read_text(),BASE_MAIN)
                mod.run(True)
                self.assertIn('register_super_app_launcher(bot)',(d/'main.py').read_text())
                mod.run(False)
                self.assertEqual(len(list(d.glob('V120_TELEGRAM_LAUNCH_BACKUP_*'))),1)

if __name__ == '__main__':unittest.main()
