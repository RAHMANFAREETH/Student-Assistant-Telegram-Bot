"""Installer isolation, idempotence, and modified-file refusal."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import INSTALL_V120_FULL_QA as inst

HERE=Path(__file__).resolve().parent

def baseline_files(root):
    for name in inst.FILES:
        src=HERE/'V120_TOOL_QA_PAYLOAD'/name
        if name=='super_miniapp_v120.js':
            text=(HERE/'V120_QA_TEST_FIXTURES'/'baseline_js.txt').read_text(encoding='utf-8')
        elif name=='super_miniapp_v120_tools.mjs':
            text=(HERE/'V120_QA_TEST_FIXTURES'/'baseline_tools.txt').read_text(encoding='utf-8')
        elif name=='TEST_SUPER_TOOLS_V120.mjs':
            text=(HERE/'V120_QA_TEST_FIXTURES'/'baseline_test_tools.txt').read_text(encoding='utf-8')
        elif name=='TEST_SUPER_TOOLS_EXPANSION_V120.mjs':
            text=(HERE/'V120_QA_TEST_FIXTURES'/'baseline_test_expansion.txt').read_text(encoding='utf-8')
        elif name=='TEST_SUPER_LOCALE_PLANNER_V120.mjs':
            text=(HERE/'V120_QA_TEST_FIXTURES'/'baseline_test_locale.txt').read_text(encoding='utf-8')
        else:raise AssertionError(name)
        (root/name).write_text(text,encoding='utf-8')

class InstallerTests(unittest.TestCase):
    def test_check_does_not_modify(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);baseline_files(root)
            before={name:(root/name).read_bytes() for name in inst.FILES}
            modes=inst.process(root,apply=False)
            self.assertEqual(sum(mode=='UPDATE' for _,mode in modes),5)
            self.assertEqual(sum(mode=='ADD' for _,mode in modes),1)
            self.assertEqual(before,{name:(root/name).read_bytes() for name in inst.FILES})
    def test_apply_and_repeat_and_preserve_main(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);baseline_files(root)
            (root/'main.py').write_text('KEEP EXISTING BOT\n',encoding='utf-8')
            inst.process(root,apply=True)
            self.assertEqual((root/'main.py').read_text(),'KEEP EXISTING BOT\n')
            self.assertEqual((root/'super_miniapp_v120.js').read_bytes(),(HERE/'V120_TOOL_QA_PAYLOAD'/'super_miniapp_v120.js').read_bytes())
            self.assertEqual((root/'super_miniapp_v120_tools.mjs').read_bytes(),(HERE/'V120_TOOL_QA_PAYLOAD'/'super_miniapp_v120_tools.mjs').read_bytes())
            modes=inst.process(root,apply=True)
            self.assertTrue(all(m=='UNCHANGED' for _,m in modes))
    def test_rejects_unknown_local_change_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);baseline_files(root)
            modified=root/'super_miniapp_v120.js';modified.write_text('CUSTOM VERSION',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Unexpected local version'):inst.process(root,apply=True)
            self.assertEqual(modified.read_text(),'CUSTOM VERSION')
            self.assertFalse((root/'TEST_V120_REBUILT_TOOLS.mjs').exists())
    def test_refuses_symlink_if_available(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);baseline_files(root)
            file=root/'super_miniapp_v120.js';file.unlink()
            try:file.symlink_to(root/'super_miniapp_v120_tools.mjs')
            except (OSError,NotImplementedError):self.skipTest('Symbolic links require OS privilege')
            with self.assertRaisesRegex(ValueError,'Unsafe nonregular file'):inst.process(root,apply=True)

if __name__=='__main__':unittest.main()
