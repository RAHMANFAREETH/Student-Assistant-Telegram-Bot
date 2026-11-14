"""Tests for V13 four-language Font Studio launcher inside PDF Tools.

Standalone: python -X utf8 -m unittest TEST_V130_PDF_FONT_STUDIO -q
"""
from __future__ import annotations
import ast
from contextlib import contextmanager
from pathlib import Path
import importlib.util
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent

def load(path,label):
    spec=importlib.util.spec_from_file_location(label,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class FakeButton:
    def __init__(self,text,web_app=None):self.text=text;self.web_app=web_app
class FakeMarkup:
    def __init__(self,**kw):self.rows=[]
    def add(self,*x):self.rows.append(x)
    def row(self,*x):self.rows.append(x)
class FakeWebAppInfo:
    def __init__(self,url):self.url=url
class FakeBot:
    def __init__(self):self.handlers=[];self.sent=[]
    def message_handler(self,**options):
        def decorator(fn):self.handlers.append((options,fn));return fn
        return decorator
    def send_message(self,chat_id,text,**options):self.sent.append((chat_id,text,options))
    def dispatch(self,text,chat_type='private',user_id=1234):
        msg=types.SimpleNamespace(text=text,
            chat=types.SimpleNamespace(id=1234,type=chat_type),
            from_user=types.SimpleNamespace(id=user_id))
        if text.startswith('/'):
            name=text.split()[0].split('@')[0].lstrip('/')
        else:name=None
        for options,fn in self.handlers:
            if options.get('commands') and name in options['commands']:
                return fn(msg)
            predicate=options.get('func')
            if predicate and predicate(msg):return fn(msg)
        raise AssertionError('Handler not registered: '+text)

@contextmanager
def telegram_stubs():
    telebot=types.ModuleType('telebot')
    telebot.types=types.SimpleNamespace(InlineKeyboardMarkup=FakeMarkup,
        InlineKeyboardButton=FakeButton,WebAppInfo=FakeWebAppInfo)
    with patch.dict(sys.modules,{'telebot':telebot}):yield

@contextmanager
def settings(**overrides):
    defaults={
        'SUPER_FONT_STUDIO_V122_ENABLED':'true',
        'SUPER_MINIAPP_V120_ENABLED':'true',
        'SUPER_MINIAPP_V120_LAUNCH_ENABLED':'true',
        'SUPER_MINIAPP_V120_LAUNCH_PUBLIC':'true',
        'SUPER_MINIAPP_V120_PUBLIC_TOOLS':'true',
        'SUPER_MINIAPP_V120_REQUIRE_ADULT':'false',
        'SUPER_MINIAPP_V120_PUBLIC_URL':'https://student-assistant.example/app',
        'SUPER_MINIAPP_V120_PILOT_IDS':'',
    }
    defaults.update(overrides)
    with patch.dict(os.environ,defaults):yield

class LauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module=load(ROOT/'pdf_fontstudio_v130.py','pdf_fontstudio_under_test')
    def bot(self):
        fake=FakeBot()
        with telegram_stubs():self.module.register_pdf_fontstudio_handlers(fake)
        return fake
    def test_pdf_menu_button_launches_signed_webapp(self):
        bot=self.bot()
        with settings(),telegram_stubs():bot.dispatch('🌍 Font & Writing Studio')
        self.assertEqual(len(bot.sent),1)
        self.assertIn('தமிழ்',bot.sent[0][1])
        buttons=bot.sent[0][2]['reply_markup'].rows[0]
        self.assertEqual(buttons[0].web_app.url,'https://student-assistant.example/app/fonts')
    def test_command_works_without_pdf_state(self):
        bot=self.bot()
        with settings(),telegram_stubs():bot.dispatch('/fontstudio')
        self.assertIn('web_app', repr(bot.sent[0][2]['reply_markup'].rows[0][0].__dict__))
    def test_fonts_alias(self):
        bot=self.bot()
        with settings(),telegram_stubs():bot.dispatch('/fonts')
        self.assertIn('/fonts',bot.sent[0][2]['reply_markup'].rows[0][0].web_app.url)
    def test_group_restricted(self):
        bot=self.bot()
        with settings(),telegram_stubs():bot.dispatch('/fontstudio',chat_type='supergroup')
        self.assertIn('private chat',bot.sent[0][1]);self.assertNotIn('reply_markup',bot.sent[0][2])
    def test_studio_flag_off(self):
        bot=self.bot()
        with settings(SUPER_FONT_STUDIO_V122_ENABLED='false'),telegram_stubs():bot.dispatch('/fontstudio')
        self.assertIn('not enabled',bot.sent[0][1])
    def test_super_app_flag_off(self):
        bot=self.bot()
        with settings(SUPER_MINIAPP_V120_ENABLED='false'),telegram_stubs():bot.dispatch('/fontstudio')
        self.assertIn('not available',bot.sent[0][1])
    def test_invalid_url_rejected(self):
        bot=self.bot()
        with settings(SUPER_MINIAPP_V120_PUBLIC_URL='http://unsafe.example/app'),telegram_stubs():bot.dispatch('/fontstudio')
        self.assertIn('HTTPS address',bot.sent[0][1])
    def test_no_user_rejected(self):
        bot=self.bot()
        with settings(),telegram_stubs():bot.dispatch('/fontstudio',user_id=None)
        self.assertIn('not available',bot.sent[0][1])
    def test_no_data_upload_in_launcher(self):
        text=(ROOT/'pdf_fontstudio_v130.py').read_text(encoding='utf-8')
        for token in ('send_document(', 'requests.post(', 'httpx.post(', '.insert(', 'copy_file('):
            self.assertNotIn(token,text)

class SourceInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.installer=load(ROOT/'INSTALL_V130_FOUR_LANG_PDF_TOOLS.py','pdf_font_studio_installer_test')
    def fixture(self):
        tmp=tempfile.TemporaryDirectory()
        root=Path(tmp.name)
        baseline=ROOT/'V130_MULTIFONT_PAYLOAD'/'baseline'
        for name in ('Dockerfile','office_to_pdf_v713.py',
            'super_miniapp_v122_fonts.html','super_miniapp_v122_fonts.css','super_miniapp_v122_fonts.js'):
            shutil.copy2(baseline/name,root/name)
        # Source from baseline controlled fixture when available; otherwise actual project.
        source=ROOT/'V130_PDF_STUDIO_PAYLOAD'/'pdf_tools_v13_reference.py'
        shutil.copy2(source,root/'pdf_tools.py')
        return tmp,root
    def test_installer_changes_pdf_menu_and_four_language(self):
        tmp,root=self.fixture()
        try:
            proposed=self.installer.plan(root)
            self.assertIn('pdf_tools.py',proposed)
            self.assertIn('register_pdf_fontstudio_handlers(bot)',proposed['pdf_tools.py'])
            self.assertIn('types.KeyboardButton("🌍 Font & Writing Studio")',proposed['pdf_tools.py'])
            self.assertIn('value="ar"',proposed['super_miniapp_v122_fonts.html'])
        finally:tmp.cleanup()
    def test_installer_idempotent(self):
        tmp,root=self.fixture()
        try:
            self.installer.execute(root,apply=True)
            self.assertEqual(self.installer.plan(root),{})
        finally:tmp.cleanup()
    def test_preserves_other_pdf_handlers(self):
        tmp,root=self.fixture()
        try:
            new=self.installer.plan(root)['pdf_tools.py']
            original=(root/'pdf_tools.py').read_text(encoding='utf-8')
            for string in ('register_advanced_pdf_handlers(', 'register_office_to_pdf_handlers(',
                'def start_text_to_pdf(', 'def start_document_scan('):
                self.assertEqual(new.count(string),original.count(string),string)
            self.assertLess(new.index('    register_advanced_pdf_handlers('),
                            new.index('    register_office_to_pdf_handlers('))
        finally:tmp.cleanup()
    def test_unexpected_pdf_layout_refused(self):
        tmp,root=self.fixture()
        try:
            file=root/'pdf_tools.py'
            file.write_text('new custom PDF Tools application',encoding='utf-8')
            with self.assertRaises(self.installer.SafeStop):self.installer.plan(root)
        finally:tmp.cleanup()
    def test_pdf_menu_renders_button(self):
        tmp,root=self.fixture()
        try:
            proposed=self.installer.plan(root)['pdf_tools.py']
        finally:tmp.cleanup()
        tree=ast.parse(proposed)
        menu=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='_pdf_tools_menu')
        # Run the actual function AST without activating the bot or its integrations.
        fake=types.SimpleNamespace(ReplyKeyboardMarkup=FakeMarkup,KeyboardButton=FakeButton)
        env={'types':fake,'pdf_state':{},'ADVANCED_BUTTONS':('Compress PDF','PDF to Word'),
             'PHOTO_CROP_BUTTON':'Photo Crop','SCAN_BUTTON':'Scan Document',
             'PDF_TEXT_BUTTON':'Text to PDF'}
        conv=types.ModuleType('conversation_v130');conv.text=lambda *_:'PDF Tools'
        with patch.dict(sys.modules,{'conversation_v130':conv}):
            exec(compile(ast.Module(body=[menu],type_ignores=[]),'pdf_tools.py','exec'),env)
            bot=FakeBot();env['_pdf_tools_menu'](bot,11)
        names=[button.text for row in bot.sent[0][2]['reply_markup'].rows for button in row]
        self.assertIn('🌍 Font & Writing Studio',names)
        self.assertEqual(names[-1],'🏠 Main Menu')

if __name__=='__main__':unittest.main()
