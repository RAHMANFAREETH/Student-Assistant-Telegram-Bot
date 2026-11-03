"""Focused V12 public utility access security and installer regression tests."""
import importlib
import importlib.util
import logging
import os
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
import INSTALL_V120_PUBLIC_ACCESS as patcher

# Offline test harness without Flask installed (use real Flask on Windows).
try:
    import flask
except ImportError:
    flask=types.ModuleType('flask')
    flask.abort=lambda status: (_ for _ in ()).throw(RuntimeError(status))
    flask.jsonify=lambda data: data
    flask.request=types.SimpleNamespace(headers={}, method='GET',path='/app/api/session')
    flask.send_file=lambda path,mimetype=None: (path,mimetype)
    flask.make_response=lambda body:body
    sys.modules['flask']=flask

import super_miniapp_v120 as backend
import super_miniapp_v120_launch as launcher

class FakeApp:
    def __init__(self):self.view_functions={};self.logger=logging.getLogger('test-v120-public');self.after=[]
    def after_request(self,fn):self.after.append(fn);return fn
    def get(self,path,endpoint=None):return self.route(path,endpoint=endpoint)
    def route(self,path,methods=None,endpoint=None):
        def deco(fn):self.view_functions[endpoint or fn.__name__]=fn;return fn
        return deco

class Tests(unittest.TestCase):
    def test_public_unconfigured_fails_closed(self):
        with patch.dict(os.environ,{'SUPER_MINIAPP_V120_PUBLIC_TOOLS':'false','SUPER_MINIAPP_V120_REQUIRE_ADULT':'true'}):
            self.assertFalse(backend.public_tools_enabled())
            self.assertTrue(backend.adult_verification_required())
    def test_no_login_public_tools_guest(self):
        app=FakeApp();backend.register_super_miniapp(app)
        with patch.dict(os.environ,{'SUPER_MINIAPP_V120_ENABLED':'true','SUPER_MINIAPP_V120_PUBLIC_TOOLS':'true'}),patch.object(backend,'request',types.SimpleNamespace(headers={})),patch.object(backend,'jsonify',side_effect=lambda obj:obj):
            result=app.view_functions['v120_super_session']()
        self.assertTrue(result['guest']);self.assertIsNone(result['user_id']);self.assertFalse(result['private_features'])
    def test_unsigned_private_tasks_rejected_even_with_public_tools(self):
        app=FakeApp();backend.register_super_miniapp(app)
        v8=types.ModuleType('v8_miniapp');v8.MiniAppAuthError=ValueError
        v8.validate_init_data=lambda raw,token: (_ for _ in ()).throw(ValueError('Invalid signature'))
        with patch.dict(sys.modules,{'v8_miniapp':v8}),patch.dict(os.environ,{'SUPER_MINIAPP_V120_ENABLED':'true','SUPER_MINIAPP_V120_PUBLIC_TOOLS':'true'}),patch.object(backend,'request',types.SimpleNamespace(headers={},method='GET')),patch.object(backend,'jsonify',side_effect=lambda obj:obj):
            response=app.view_functions['v120_super_tasks']()
        self.assertEqual(response[1],401)
    def test_bad_signature_only_guest_in_public_session(self):
        app=FakeApp();backend.register_super_miniapp(app)
        v8=types.ModuleType('v8_miniapp');v8.MiniAppAuthError=ValueError
        v8.validate_init_data=lambda raw,token: (_ for _ in ()).throw(ValueError('Invalid signature'))
        with patch.dict(sys.modules,{'v8_miniapp':v8}),patch.dict(os.environ,{'SUPER_MINIAPP_V120_ENABLED':'true','SUPER_MINIAPP_V120_PUBLIC_TOOLS':'true','BOT_TOKEN':'abc'}),patch.object(backend,'request',types.SimpleNamespace(headers={'X-Telegram-Init-Data':'bad'})),patch.object(backend,'jsonify',side_effect=lambda obj:obj):
            result=app.view_functions['v120_super_session']()
        self.assertIsNone(result['user_id']);self.assertFalse(result['private_features'])
    def test_verified_signature_no_manual_adult_gate_if_explicit(self):
        v8=types.ModuleType('v8_miniapp');v8.MiniAppAuthError=ValueError
        v8.validate_init_data=lambda raw,token: 123 if (raw,token)==('signed','abc') else None
        ages=types.ModuleType('study_access_v9')
        ages.is_verified_adult=lambda uid: (_ for _ in ()).throw(AssertionError('Must not call adult verification when disabled'))
        with patch.dict(sys.modules,{'v8_miniapp':v8,'study_access_v9':ages}),patch.dict(os.environ,{'SUPER_MINIAPP_V120_REQUIRE_ADULT':'false','BOT_TOKEN':'abc','SUPER_MINIAPP_V120_LAUNCH_PUBLIC':'true'}):
            self.assertEqual(backend.verify_super_session('signed'),123)
    def test_adult_gate_retained_by_default(self):
        v8=types.ModuleType('v8_miniapp');v8.MiniAppAuthError=ValueError;v8.validate_init_data=lambda raw,token: 123
        ages=types.ModuleType('study_access_v9');ages.is_verified_adult=lambda uid:False
        with patch.dict(sys.modules,{'v8_miniapp':v8,'study_access_v9':ages}),patch.dict(os.environ,{'SUPER_MINIAPP_V120_REQUIRE_ADULT':'true','BOT_TOKEN':'abc','SUPER_MINIAPP_V120_LAUNCH_PUBLIC':'true'}):
            with self.assertRaises(PermissionError):backend.verify_super_session('signed')
    def test_public_launcher_accepts_unverified_user_with_flags(self):
        with patch.dict(os.environ,{'SUPER_MINIAPP_V120_ENABLED':'true','SUPER_MINIAPP_V120_LAUNCH_ENABLED':'true','SUPER_MINIAPP_V120_LAUNCH_PUBLIC':'true','SUPER_MINIAPP_V120_PUBLIC_TOOLS':'true','SUPER_MINIAPP_V120_PILOT_IDS':''}):
            self.assertTrue(launcher.can_launch(9876543))
    def test_launcher_cannot_open_if_disabled(self):
        with patch.dict(os.environ,{'SUPER_MINIAPP_V120_ENABLED':'false','SUPER_MINIAPP_V120_LAUNCH_ENABLED':'true','SUPER_MINIAPP_V120_LAUNCH_PUBLIC':'true','SUPER_MINIAPP_V120_PUBLIC_TOOLS':'true'}):
            self.assertFalse(launcher.can_launch(9876543))
    def test_frontend_does_not_use_unsigned_identity(self):
        js=(HERE/'super_miniapp_v120.js').read_text(encoding='utf-8')
        self.assertIn('guest===true',js)
        self.assertIn('sessionStorage',js)
        self.assertIn('data.private_features!==true',js)
        self.assertNotIn('initDataUnsafe',js)
    def test_installer_repeated_apply_no_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for file in patcher.PATCHES:shutil.copy2(HERE/file,root/file)
            originals={n:(root/n).read_bytes() for n in patcher.PATCHES}
            patcher.process(root,apply=True)
            self.assertEqual(originals,{n:(root/n).read_bytes() for n in patcher.PATCHES})
    def test_bad_anchor_refuses_modify(self):
        with self.assertRaises(ValueError):patcher.frontend('invalid source')

if __name__=='__main__':unittest.main()
