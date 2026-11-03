"""Installer tests without touching a real student bot workspace."""
from __future__ import annotations
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import INSTALL_V120_TASK_SYNC as inst

class InstallerTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  (self.root/'main.py').write_text('register_super_miniapp(app)',encoding='utf-8')
  (self.root/'TEST_SUPER_PLANNER_V120.py').write_text('# prior patch')
  (self.root/'TEST_SUPER_LOCALE_PLANNER_V120.mjs').write_text('// prior patch')
  known={}
  for name in inst.BASE_HASHES:
   value=('safe-baseline-'+name).encode()
   (self.root/name).write_bytes(value)
   known[name]=hashlib.sha256(value).hexdigest()
  self.patcher=patch.dict(inst.BASE_HASHES,known,clear=True);self.patcher.start()
 def tearDown(self):self.patcher.stop();self.temp.cleanup()
 def test_check_does_not_change_files(self):
  actions=inst.planned(self.root,inst.PAYLOAD)
  self.assertEqual(len(actions),len(inst.FILES))
  self.assertFalse(list(self.root.glob('V120_TASK_SYNC_BACKUP_*')))
 def test_apply_creates_backup_and_idempotence(self):
  actions,backup=inst.apply(self.root,inst.PAYLOAD)
  self.assertTrue(backup.is_dir())
  for name in inst.BASE_HASHES:self.assertTrue((backup/name).exists())
  for name in inst.FILES:self.assertEqual((self.root/name).read_bytes(),(inst.PAYLOAD/name).read_bytes())
  _,another=inst.apply(self.root,inst.PAYLOAD);self.assertIsNone(another)
 def test_refuses_manual_edits(self):
  (self.root/'super_miniapp_v120.js').write_text('manual edit')
  with self.assertRaisesRegex(ValueError,'Unexpected local changes'):inst.planned(self.root,inst.PAYLOAD)
 def test_refuses_missing_parent_patch(self):
  (self.root/'TEST_SUPER_PLANNER_V120.py').unlink()
  with self.assertRaisesRegex(ValueError,'earlier V12'):inst.planned(self.root,inst.PAYLOAD)
 def test_refuses_symlinks(self):
  # Windows often denies os.symlink without Developer Mode or special privileges.
  # Mock the filesystem predicate instead: this still verifies that the
  # production installer rejects a destination flagged as a symbolic link.
  path=self.root/'TEST_SUPER_MINIAPP_V120.py'
  original_is_symlink=Path.is_symlink
  def report_target_as_symlink(candidate):
   if candidate==path:return True
   return original_is_symlink(candidate)
  with patch.object(Path,'is_symlink',report_target_as_symlink):
   with self.assertRaisesRegex(ValueError,'symbolic'):
    inst.planned(self.root,inst.PAYLOAD)

if __name__=='__main__':unittest.main()
