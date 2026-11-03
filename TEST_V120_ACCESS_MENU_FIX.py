"""Focused, no-network regression checks for V12 Telegram Mini App menu patch."""
from __future__ import annotations
import importlib.util
import pathlib
import shutil
import tempfile
import unittest

HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('installer_v120_menu',HERE/'INSTALL_V120_ACCESS_MENU_FIX.py')
installer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

class PatchChecks(unittest.TestCase):
    def _patched(self, key, text):
        fn=installer.PATCHES[key]
        new=fn(text)
        compile(new,key,'exec')
        self.assertEqual(fn(new),new)
        return new

    def test_navigation_reply_button_is_flagged(self):
        source='MAIN_MENU_ROWS = [("one",),("help",)]\n# V5.7 CATEGORY MENU END\nGLOBAL_BUTTONS = {x for row in MAIN_MENU_ROWS for x in row}\n'
        updated=self._patched('navigation.py',source)
        self.assertIn('V120_SUPER_MINI_APP_BUTTON',updated)
        self.assertIn('SUPER_MINIAPP_V120_LAUNCH_ENABLED',updated)
        self.assertIn('MAIN_MENU_ROWS.insert(-1',updated)

    def test_home_inline_button_uses_web_app(self):
        source="def home(bot,cid):\n    return _msg(bot,cid,'🏠 Student Assistant — Friendly Home Menu',reply_markup=_keyboard(rows))\n"
        updated=self._patched('friendly_v119.py',source)
        self.assertIn('types.WebAppInfo(url=url)',updated)
        self.assertIn('can_launch(int(cid))',updated)

    def test_launcher_reply_button_reuses_verified_command(self):
        source="def register_super_app_launcher(bot):\n    def v120_super_app_command(message):\n        bot.send_message(chat_id, 'Open your secure Student Assistant Super Mini App:',\n                         reply_markup=keyboard)\n"
        updated=self._patched('super_miniapp_v120_launch.py',source)
        self.assertIn('v120_super_app_command(message)',updated)
        self.assertNotIn('ReplyKeyboardButton(web_app=',updated)

    def test_auth_diagnostics_do_not_bypass_checks(self):
        source='''def register_super_miniapp(app):
    def session():
        try:
            return True
        except (ValueError, TypeError):
            return jsonify({"error": "Open the app from Telegram and sign in again."}), 401
'''
        updated=self._patched('super_miniapp_v120.py',source)
        self.assertIn('V12 login denied:',updated)
        self.assertIn('no sensitive data logged',updated)
        self.assertNotIn('initDataUnsafe',updated)

    def test_missing_home_anchor_aborts(self):
        with self.assertRaisesRegex(ValueError,'expected 1 matching anchor'):
            installer.friendly('def home(): pass')

    def test_missing_files_aborts_before_write(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=pathlib.Path(dirname)
            (root/'navigation.py').write_text('test',encoding='utf-8')
            with self.assertRaises(ValueError):
                installer.process(root,apply=True)
            self.assertEqual((root/'navigation.py').read_text(encoding='utf-8'),'test')

if __name__=='__main__': unittest.main()
