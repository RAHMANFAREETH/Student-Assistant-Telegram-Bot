"""V12 route, access-gate and guarded-install tests. Uses a stub if Flask is absent.

When Flask is installed (as in the real bot), it also tests real HTTP responses.
"""
from __future__ import annotations
import importlib
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

# Real Flask is used in the bot. Keep lightweight registration tests runnable
# in a standalone environment without Flask (but skip real HTTP tests there).
try:
    from flask import Flask
    HAS_REAL_FLASK = True
except ImportError:
    Flask = None
    HAS_REAL_FLASK = False
    flask_stub = types.ModuleType('flask')
    class Request:
        path = '/app'
        headers = {}
    flask_stub.request = Request()
    flask_stub.abort = lambda code: (_ for _ in ()).throw(ValueError(f'HTTP {code}'))
    flask_stub.jsonify = lambda data: data
    flask_stub.make_response = lambda *a, **k: None
    flask_stub.send_file = lambda file, mimetype=None: (Path(file).read_bytes(), mimetype)
    sys.modules['flask'] = flask_stub

import super_miniapp_v120 as module
from INSTALL_SUPER_MINIAPP_V120 import BLOCK, planned

class FakeApp:
    def __init__(self): self.view_functions = {}; self.after = []
    def get(self, path, endpoint=None):
        def deco(func):
            self.view_functions[endpoint or func.__name__] = func
            return func
        return deco
    def route(self, path, methods=None, endpoint=None):
        return self.get(path, endpoint=endpoint)
    def after_request(self, fn): self.after.append(fn); return fn

class TestSuperMiniApp(unittest.TestCase):
    def setUp(self):
        self.app=FakeApp(); module.register_super_miniapp(self.app)
    def test_routes_registered(self):
        names=('v120_super_home','v120_super_css','v120_super_js','v120_super_tools','v120_super_session','v120_super_planner','v120_super_tasks','v120_super_task_item','v120_super_results')
        for n in names: self.assertIn(n,self.app.view_functions)
    def test_registration_idempotent(self):
        module.register_super_miniapp(self.app)
        self.assertEqual(len(self.app.view_functions),9)
    def test_feature_off_by_default(self):
        # Assert that the view aborts with 404 independently of Flask exception types.
        with patch.dict(os.environ, {'SUPER_MINIAPP_V120_ENABLED':'false'}):
            self.assertFalse(module.enabled())
            with patch.object(module, 'abort', side_effect=RuntimeError('HTTP 404')) as abort_mock:
                with self.assertRaisesRegex(RuntimeError, 'HTTP 404'):
                    self.app.view_functions['v120_super_home']()
                abort_mock.assert_called_once_with(404)
    def test_enabled_html_only_new_app(self):
        # Flask.send_file needs a request; replace only that boundary in this
        # lightweight unit test and verify the actual HTML asset contents.
        def read_asset(path, mimetype=None):
            return Path(path).read_bytes(), mimetype
        with patch.dict(os.environ, {'SUPER_MINIAPP_V120_ENABLED':'true'}):
            with patch.object(module, 'send_file', side_effect=read_asset):
                page=self.app.view_functions['v120_super_home']()
        self.assertIn(b'Super Mini App', page[0])
        self.assertIn(b'/app/assets/app.js', page[0])
    def test_requires_signed_login_and_adult(self):
        fake_v8=types.ModuleType('v8_miniapp')
        class AuthError(ValueError): pass
        fake_v8.MiniAppAuthError=AuthError
        fake_v8.validate_init_data=lambda raw,token: 44 if raw=='valid' and token=='secret' else (_ for _ in ()).throw(AuthError('invalid'))
        fake_age=types.ModuleType('study_access_v9'); fake_age.is_verified_adult=lambda uid:uid==44
        with patch.dict(sys.modules, {'v8_miniapp':fake_v8,'study_access_v9':fake_age}):
            with patch.dict(os.environ, {'BOT_TOKEN':'secret', 'SUPER_MINIAPP_V120_REQUIRE_ADULT':'true', 'SUPER_MINIAPP_V120_LAUNCH_PUBLIC':'true', 'SUPER_MINIAPP_V120_PILOT_IDS':''}):  # V120 TEST MODE COMPAT
                self.assertEqual(module.verify_super_session('valid'),44)
                with self.assertRaises(AuthError):module.verify_super_session('invalid')
                with self.assertRaises(AuthError):module.verify_super_session('')
                fake_age.is_verified_adult=lambda uid:False
                with self.assertRaises(PermissionError):module.verify_super_session('valid')
                # Public utility mode deliberately removes *manual* adult verification,
                # but always requires valid Telegram HMAC for private user data.
                with patch.dict(os.environ, {'SUPER_MINIAPP_V120_REQUIRE_ADULT':'false'}):
                    self.assertEqual(module.verify_super_session('valid'), 44)
                    with self.assertRaises(AuthError):module.verify_super_session('invalid')
    def test_safe_security_headers(self):
        response=types.SimpleNamespace(headers={})
        # Patch module.request, not flask.request (Flask's LocalProxy requires
        # a live request context just to access its attributes).
        with patch.object(module, 'request', types.SimpleNamespace(path='/app/api/session')):
            result=self.app.after[0](response)
        self.assertEqual(result.headers['Cache-Control'],'no-store')
        self.assertIn("default-src 'none'",result.headers['Content-Security-Policy'])
        self.assertNotIn("'unsafe-inline'",result.headers['Content-Security-Policy'])
    def test_headers_do_not_modify_existing_library(self):
        response=types.SimpleNamespace(headers={})
        with patch.object(module, 'request', types.SimpleNamespace(path='/library')):
            result=self.app.after[0](response)
        self.assertEqual(result.headers, {})
    @unittest.skipUnless(HAS_REAL_FLASK, 'Flask not installed in this offline environment')
    def test_real_http_routes_off_by_default(self):
        app=Flask('v120_http_off_test')
        module.register_super_miniapp(app)
        with patch.dict(os.environ, {'SUPER_MINIAPP_V120_ENABLED':'false'}):
            client=app.test_client()
            for path in ('/app','/app/assets/style.css','/app/api/session'):
                with self.subTest(path=path):
                    self.assertEqual(client.get(path).status_code, 404)
    @unittest.skipUnless(HAS_REAL_FLASK, 'Flask not installed in this offline environment')
    def test_real_http_serves_html_and_sets_security_headers(self):
        app=Flask('v120_http_on_test')
        module.register_super_miniapp(app)
        with patch.dict(os.environ, {'SUPER_MINIAPP_V120_ENABLED':'true'}):
            response=app.test_client().get('/app')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Super Mini App',response.data)
        self.assertIn(b'/app/assets/app.js',response.data)
        self.assertEqual(response.headers['Cache-Control'],'no-store')
        self.assertIn("default-src 'none'", response.headers['Content-Security-Policy'])
    def test_installer_keeps_existing_routes(self):
        main="app = Flask(__name__)\nfrom v8_miniapp import register_v8_miniapp\nregister_v8_miniapp(app)\n@app.get('/library')\ndef library(): return 1\n"
        result=planned(main)
        self.assertEqual(result.count('register_v8_miniapp(app)'),1)
        self.assertIn(BLOCK,result)
        self.assertIn("@app.get('/library')",result)
        self.assertEqual(planned(result),result)
    def test_installer_refuses_mismatched_source(self):
        with self.assertRaises(ValueError): planned('app = Flask(__name__)')
        with self.assertRaises(ValueError): planned('app = Flask(__name__)\nregister_v8_miniapp(app)\nregister_v8_miniapp(app)')
    def test_no_secrets_in_html(self):
        page=(module.ASSETS/'super_miniapp_v120.html').read_text(encoding='utf-8')
        self.assertNotIn('SUPABASE_SERVICE_ROLE',page)
        self.assertNotIn('BOT_TOKEN',page)
        self.assertIn('auth-wall',page)

if __name__=='__main__':unittest.main()
