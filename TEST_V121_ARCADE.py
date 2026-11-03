"""V12.1 guarded standalone Arcade: route, opt-in and privacy regression."""
import importlib
import os
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent

class FakeApp:
    def __init__(self):self.view_functions={};self.routes={}
    def get(self,path,endpoint=None):
        def dec(fn):self.view_functions[endpoint]=fn;self.routes[path]=fn;return fn
        return dec
    def add_url_rule(self,path,endpoint,view_func,methods):
        assert methods==['GET'];self.view_functions[endpoint]=view_func;self.routes[path]=view_func

class TestArcade(unittest.TestCase):
    def setUp(self):
        self.arcade=importlib.import_module('super_miniapp_v121')
        self.v120=importlib.import_module('super_miniapp_v120')

    def test_default_disabled(self):
        with patch.object(self.v120,'enabled',return_value=True),patch.dict(os.environ,{},clear=True):
            self.assertFalse(self.arcade.enabled_v121())

    def test_master_flag_cannot_be_bypassed(self):
        with patch.object(self.v120,'enabled',return_value=False),patch.dict(os.environ,{'SUPER_ARCADE_V121_ENABLED':'true'}):
            self.assertFalse(self.arcade.enabled_v121())

    def test_public_flag_only_enables_arcade(self):
        with patch.object(self.v120,'enabled',return_value=True),patch.dict(os.environ,{'SUPER_ARCADE_V121_ENABLED':'true'}):
            self.assertTrue(self.arcade.enabled_v121())

    def test_routes_and_idempotence(self):
        app=FakeApp()
        with patch.dict(os.environ,{'SUPER_ARCADE_V121_ENABLED':'true'}):
            self.arcade.register_v121_arcade(app)
            first=len(app.routes)
            self.arcade.register_v121_arcade(app)
        self.assertEqual(len(app.routes),first)
        self.assertEqual(first,11)
        self.assertIn('/app/arcade',app.routes)
        self.assertIn('/app/arcade/meta',app.routes)
        self.assertIn('/app/assets/arcade-entry.mjs',app.routes)
        self.assertNotIn('/library',app.routes)

    def test_no_extra_routes_when_feature_off(self):
        app=FakeApp()
        with patch.dict(os.environ,{'SUPER_ARCADE_V121_ENABLED':'false'}):
            self.arcade.register_v121_arcade(app)
        self.assertEqual(len(app.routes),0)

    def test_no_identity_or_database_access(self):
        src=(ROOT/'super_miniapp_v121.py').read_text(encoding='utf8')
        for forbidden in ('BOT_TOKEN','get_assignments','read_planner_overview','verify_super_session(', 'supabase', 'telegram_user_id'):
            self.assertNotIn(forbidden,src)
        self.assertNotIn('POST',src)

    def test_asset_paths_are_constant(self):
        for filename, _mime in self.arcade._STATIC.values():
            self.assertTrue((ROOT/filename).is_file(),filename)
            self.assertFalse(Path(filename).is_absolute())

    def test_new_page_has_only_self_hosted_scripts(self):
        html=(ROOT/'super_miniapp_v121.html').read_text(encoding='utf8')
        self.assertIn('/app/arcade/assets/app.mjs',html)
        self.assertNotIn('https://',html)

    def test_all_32_activities_not_linked_to_private_api(self):
        js=(ROOT/'super_miniapp_v121_app.mjs').read_text(encoding='utf8')
        self.assertNotIn('/app/api/tasks',js)
        self.assertNotIn('/app/api/planner',js)
        self.assertNotIn('user_id',js)

    def test_legacy_asset_entry_is_static_only(self):
        js=(ROOT/'super_miniapp_v121_entry.mjs').read_text(encoding='utf8')
        self.assertIn('/app/arcade/meta',js)
        self.assertIn('/app/arcade',js)
        self.assertNotIn('innerHTML',js)

if __name__=='__main__':unittest.main()
