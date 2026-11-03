"""Self-contained guarded-installer tests; no live repo/database required."""
import hashlib
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import INSTALL_V120_PLANNER_LOCALE as installer

class TestPlannerInstaller(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.root=Path(self.tmp.name)
  (self.root/'main.py').write_text('register_super_miniapp(app)',encoding='utf-8')
  self.known={}
  for name in installer.BASE_HASHES:
   b=('known-good-'+name).encode('utf-8')
   (self.root/name).write_bytes(b)
   self.known[name]=hashlib.sha256(b).hexdigest()
  self.baseline=patch.dict(installer.BASE_HASHES,self.known,clear=True)
  self.baseline.start()
 def tearDown(self):
  self.baseline.stop()
  self.tmp.cleanup()
 def test_check_does_not_mutate_files(self):
  actions=installer.planned(self.root,installer.PAYLOAD)
  self.assertEqual(len(actions),len(installer.FILES))
  self.assertEqual(sum(k=='UPDATE' for _,k in actions),len(installer.BASE_HASHES))
  self.assertEqual(sum(k=='ADD' for _,k in actions),len(installer.NEW_FILES))
  self.assertFalse(list(self.root.glob('V120_PLANNER_LOCALE_BACKUP_*')))
 def test_apply_is_idempotent_and_backed_up(self):
  actions,backup=installer.apply(self.root,installer.PAYLOAD)
  self.assertTrue(backup.is_dir())
  for name in installer.FILES:
   self.assertEqual((self.root/name).read_bytes(),(installer.PAYLOAD/name).read_bytes())
  for name in installer.BASE_HASHES:self.assertTrue((backup/name).exists())
  actions,second=installer.apply(self.root,installer.PAYLOAD)
  self.assertIsNone(second)
  self.assertTrue(all(kind=='UNCHANGED' for _,kind in actions))
 def test_rejects_unknown_changes(self):
  (self.root/'super_miniapp_v120.js').write_text('modified by user',encoding='utf-8')
  with self.assertRaisesRegex(ValueError,'Local changes'):installer.planned(self.root,installer.PAYLOAD)
 def test_rejects_missing_baseline(self):
  (self.root/'super_miniapp_v120.css').unlink()
  with self.assertRaisesRegex(ValueError,'Missing installed'):installer.planned(self.root,installer.PAYLOAD)
 def test_requires_main_registration(self):
  (self.root/'main.py').unlink()
  with self.assertRaisesRegex(ValueError,'not registered'):installer.planned(self.root,installer.PAYLOAD)

if __name__=='__main__':unittest.main()
