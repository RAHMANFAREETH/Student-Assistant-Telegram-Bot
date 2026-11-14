"""Static integration assertions; no Flask import or production env required."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parent
class TestStudioRouteIntegration(unittest.TestCase):
 def test_v133_assets_route_once_and_gated(self):
  source=(ROOT/'super_miniapp_v122_fonts.py').read_text(encoding='utf-8')
  for path in ['/app/assets/verified-profiles-v133.mjs','/app/assets/verified-profiles-ui-v133.mjs','/app/assets/verified-profiles-v133.css']:
   self.assertEqual(source.count(" '"+path+"':"),1)
  self.assertIn('if not enabled_v122():abort(404)',source)
  self.assertIn('methods=[\'GET\']',source)
 def test_studio_tab_and_page_scripts(self):
  source=(ROOT/'super_miniapp_v122_fonts.html').read_text(encoding='utf-8')
  for marker in ['data-panel="legacy133"','id="legacy133"','/app/assets/verified-profiles-ui-v133.mjs','/app/assets/verified-profiles-v133.css']:
   self.assertEqual(source.count(marker),1)
  self.assertIn('id="legacy4"',source)
 def test_runtime_and_converter_assets_exist(self):
  for name in ['verified_profiles_v133.mjs','verified_profiles_v133_ui.mjs','verified_profiles_v133.css','AUDIT_CONVERT_LEGACY_DOCX_V133.py']:
   self.assertTrue((ROOT/name).is_file(),name)
if __name__=='__main__':unittest.main()
