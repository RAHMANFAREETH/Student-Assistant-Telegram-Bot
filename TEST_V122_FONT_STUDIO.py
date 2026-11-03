"""V12.2 regression tests: registration, feature switches and installer guard."""
import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent

class FakeApp:
 def __init__(self):self.view_functions={};self.routes={}
 def get(self,path,endpoint=None):
  def deco(fn):self.view_functions[endpoint]=fn;self.routes[path]=fn;return fn
  return deco
 def add_url_rule(self,path,endpoint,view_func,methods):
  assert methods==['GET'];self.view_functions[endpoint]=view_func;self.routes[path]=view_func

class TestFontStudio(unittest.TestCase):
 def setUp(self):
  self.module=importlib.import_module('super_miniapp_v122_fonts')
  self.v120=importlib.import_module('super_miniapp_v120')
 def test_default_off(self):
  with patch.dict('os.environ',{},clear=True):self.assertFalse(self.module.enabled_v122())
 def test_master_switch_required(self):
  with patch.object(self.v120,'enabled',return_value=False),patch.dict('os.environ',{'SUPER_FONT_STUDIO_V122_ENABLED':'true'}):
   self.assertFalse(self.module.enabled_v122())
 def test_routes_added_once_only_when_enabled(self):
  app=FakeApp()
  with patch.dict('os.environ',{'SUPER_FONT_STUDIO_V122_ENABLED':'false'}):self.module.register_v122_fontstudio(app)
  self.assertEqual(len(app.routes),0)
  with patch.dict('os.environ',{'SUPER_FONT_STUDIO_V122_ENABLED':'true'}):
   self.module.register_v122_fontstudio(app);n=len(app.routes)
   self.module.register_v122_fontstudio(app)
  self.assertEqual(n,7)
  self.assertEqual(len(app.routes),n)
  self.assertIn('/app/fonts',app.routes)
  self.assertNotIn('/library',app.routes)
 def test_all_static_assets_exist(self):
  for filename,_mime in self.module.STATIC.values():self.assertTrue((ROOT/filename).is_file(),filename)
 def test_no_private_data_api(self):
  source=(ROOT/'super_miniapp_v122_fonts.py').read_text(encoding='utf-8')
  for blocked in ['supabase','BOT_TOKEN','/library/api','telegram_user_id','request.form']:
   self.assertNotIn(blocked,source)
 def test_installer_idempotent_and_refuses_unknown_layout(self):
  import INSTALL_V122_FONT_STUDIO as installer
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   (root/'super_miniapp_v120.py').write_text('    register_v121_arcade(app)\n',encoding='utf-8')
   (root/'super_miniapp_v120.html').write_text('<script type="module" src="/app/assets/arcade-entry.mjs"></script>',encoding='utf-8')
   plan=installer.plan(root,ROOT/'V122_FONT_STUDIO_PAYLOAD')
   self.assertEqual(len(plan),2)
   installer.execute(root,ROOT/'V122_FONT_STUDIO_PAYLOAD',apply=True)
   self.assertEqual(installer.plan(root,ROOT/'V122_FONT_STUDIO_PAYLOAD'),{})
   self.assertEqual((root/'super_miniapp_v120.py').read_text().count('register_v122_fontstudio(app)'),1)
   self.assertEqual((root/'super_miniapp_v120.html').read_text().count('fontstudio-entry.mjs'),1)
   (root/'super_miniapp_v120.py').write_text('unsupported source layout',encoding='utf-8')
   with self.assertRaises(installer.LayoutError):installer.plan(root,ROOT/'V122_FONT_STUDIO_PAYLOAD')

if __name__=='__main__':unittest.main()
