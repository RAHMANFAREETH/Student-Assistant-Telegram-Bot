"""Offline V13.4 all-ages checks; Gemini external-terms gate stays in place."""
import ast
import os
from pathlib import Path
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent


def extracted(name,fn,context=None):
    """Run the function itself without importing unrelated production services."""
    tree=ast.parse((ROOT/name).read_text(encoding="utf-8"))
    node=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name==fn)
    code=compile(ast.Module(body=[node],type_ignores=[]),name,"exec")
    namespace=context or {}
    exec(code,namespace)
    return namespace[fn]


class AccessTests(unittest.TestCase):
    def test_v8_enabled_all_ages_and_invalid_users_denied(self):
        fn=extracted("v8_bot.py","allowed",{"enabled":lambda:True})
        self.assertTrue(fn(12))
        self.assertTrue(fn(9001))
        for value in (0,-1,"123",True,None):self.assertFalse(fn(value))
        fn_off=extracted("v8_bot.py","allowed",{"enabled":lambda:False})
        self.assertFalse(fn_off(12))

    def test_v101_no_adult_dependency(self):
        fn=extracted("v101_bot.py","allowed",{"enabled":lambda:True})
        self.assertTrue(fn(13))
        self.assertFalse(fn("13"))
        self.assertFalse(fn(0))

    def test_v12_private_session_is_signed_but_not_adult_gated(self):
        import super_miniapp_v120 as app
        from TEST_CLOUDBRIDGE_V134 import signed_init_data
        from unittest.mock import Mock
        with patch.dict(os.environ,{"BOT_TOKEN":"test-token"}):
            self.assertEqual(app.verify_super_session(signed_init_data(12)),12)
            with self.assertRaises(ValueError):
                app.verify_super_session(signed_init_data(12)[:-4]+"xxxx")
        self.assertFalse(app.adult_verification_required())

    def test_v12_launcher_for_all_signed_accounts_when_enabled(self):
        import super_miniapp_v120_launch as launch
        with patch.dict(os.environ,{"SUPER_MINIAPP_V120_ENABLED":"true",
                                 "SUPER_MINIAPP_V120_LAUNCH_ENABLED":"true",
                                 "SUPER_MINIAPP_V120_REQUIRE_ADULT":"true",
                                 "SUPER_MINIAPP_V120_PILOT_IDS":"999"}):
            self.assertTrue(launch.can_launch(12))
            self.assertFalse(launch.can_launch(0))
            self.assertTrue(launch.pilot_access_allowed(12))

    def test_book_library_verification_is_no_longer_required(self):
        fn=extracted("book_library_bot.py","_verified",{})
        self.assertTrue(fn(11))
        self.assertFalse(fn(0))
        self.assertFalse(fn("11"))

    def test_gemini_provider_restrictions_still_protected(self):
        import v10_gemini
        with patch.dict(os.environ,{"STUDY_ACCESS_MODE":"public","V10_GEMINI_ENABLED":"true"}):
            self.assertFalse(v10_gemini.adult_eligible(11))
            with self.assertRaises(v10_gemini.GeminiStudyError):
                v10_gemini.validate(11)


if __name__=="__main__":unittest.main()
