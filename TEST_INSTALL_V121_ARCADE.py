"""Guarded installer regression. Uses temp copies; no production mutation."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from INSTALL_V121_ARCADE import (plan, install, PAYLOAD, FILES, HTML, PYTHON,
                                 PY_NEEDLE, HTML_NEEDLE)

class TestInstallArcade(unittest.TestCase):
    def setUp(self):
        self.ctx=TemporaryDirectory();self.addCleanup(self.ctx.cleanup)
        self.root=Path(self.ctx.name)
        (self.root/PYTHON).write_text('def register_super_miniapp(app):\n'+PY_NEEDLE+'    pass\n',encoding='utf-8')
        (self.root/HTML).write_text('<div id="app-shell"></div>'+HTML_NEEDLE,encoding='utf-8')

    def test_check_does_not_write(self):
        changes=plan(self.root,PAYLOAD)
        self.assertEqual(len(changes),len(FILES)+2)
        self.assertFalse((self.root/'super_miniapp_v121.html').exists())

    def test_apply_adds_only_named_files(self):
        changes=plan(self.root,PAYLOAD);backup=install(self.root,changes)
        self.assertTrue(backup.is_dir())
        self.assertIn('register_v121_arcade(app)',(self.root/PYTHON).read_text())
        self.assertIn('arcade-entry.mjs',(self.root/HTML).read_text())
        self.assertFalse((self.root/'main.py').exists())

    def test_second_application_no_changes(self):
        install(self.root,plan(self.root,PAYLOAD))
        self.assertEqual(set(plan(self.root,PAYLOAD).values()),{None})

    def test_preserve_windows_crlf(self):
        path=self.root/PYTHON
        path.write_bytes(('def register_super_miniapp(app):\r\n'+PY_NEEDLE.replace('\n','\r\n')+'    pass\r\n').encode('utf-8'))
        install(self.root,plan(self.root,PAYLOAD))
        after=path.read_bytes()
        self.assertIn(b'register_v121_arcade(app)\r\n',after)
        self.assertNotIn(b'\n    register_v121_arcade(app)\n',after)

    def test_reject_modified_install_file(self):
        (self.root/'super_miniapp_v121.html').write_text('modified')
        with self.assertRaises(RuntimeError):plan(self.root,PAYLOAD)

    def test_reject_unknown_python_layout(self):
        (self.root/PYTHON).write_text('def other(): pass')
        with self.assertRaises(RuntimeError):plan(self.root,PAYLOAD)

    def test_reject_unknown_html_layout(self):
        (self.root/HTML).write_text('<p>other</p>')
        with self.assertRaises(RuntimeError):plan(self.root,PAYLOAD)

if __name__=='__main__':unittest.main()
