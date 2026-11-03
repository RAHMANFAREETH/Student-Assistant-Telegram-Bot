"""Offline regression tests: python TEST_OFFICE_MENU_FIX.py (no Telegram token required)."""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch
from advanced_pdf_v717 import ADVANCED_BUTTONS

ROOT = Path(__file__).resolve().parent

class Button:
    def __init__(self, text):
        self.text = text

class Keyboard:
    def __init__(self, **kwargs):
        self.rows = []
        self.width = kwargs.get('row_width', 2)

    def add(self, *buttons):
        for i in range(0, len(buttons), self.width):
            self.rows.append(list(buttons[i:i+self.width]))

    def row(self, *buttons):
        self.rows.append(list(buttons))

class FakeBot:
    def __init__(self):
        self.sent = []
        self.handlers = []

    def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text, kwargs))

    def message_handler(self, commands=None, func=None, content_types=None, **kwargs):
        def decorated(fn):
            self.handlers.append((commands, func, content_types or ['text'], fn))
            return fn
        return decorated

    def dispatch(self, text, *, chat_type='private', chat_id=111):
        message = SimpleNamespace(text=text, chat=SimpleNamespace(id=chat_id, type=chat_type),
                                  from_user=SimpleNamespace(id=chat_id, first_name='Student'))
        for commands, func, content_types, handler in self.handlers:
            if 'text' not in content_types:
                continue
            if commands is not None:
                candidate = (text or '').split(' ', 1)[0].split('@', 1)[0].lstrip('/')
                if not (text or '').startswith('/') or candidate not in commands:
                    continue
            if func is not None and not func(message):
                continue
            return handler(message)
        return None

class OfficeMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = (ROOT / 'pdf_tools.py').read_text(encoding='utf-8')
        parsed = ast.parse(src)
        fn = next(n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name == '_pdf_tools_menu')
        ns = dict(types=SimpleNamespace(ReplyKeyboardMarkup=Keyboard, KeyboardButton=Button),
                  pdf_state={}, PHOTO_CROP_BUTTON='✂️ Photo/Image Crop',
                  SCAN_BUTTON='📸 Scan Document', PDF_TEXT_BUTTON='📝 Text → PDF',
                  ADVANCED_BUTTONS=ADVANCED_BUTTONS)
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(ROOT/'pdf_tools.py'), 'exec'), ns)
        cls.menu = staticmethod(ns['_pdf_tools_menu'])
        spec = importlib.util.spec_from_file_location('office_to_pdf_v713', ROOT/'office_to_pdf_v713.py')
        cls.office = importlib.util.module_from_spec(spec)
        sys.modules['office_to_pdf_v713'] = cls.office
        spec.loader.exec_module(cls.office)

    def test_keyboard_has_both_buttons_before_main_menu(self):
        bot = FakeBot()
        self.menu(bot, 111)
        self.assertEqual(len(bot.sent), 1)
        chat, caption, kw = bot.sent[0]
        rows = [[button.text for button in row] for row in kw['reply_markup'].rows]
        self.assertIn(['📄 DOCX → PDF', '📊 PPTX → PDF'], rows[:-1])
        self.assertEqual(rows[-1], ['🏠 Main Menu'])
        flat = [button for row in rows for button in row]
        for advanced in ADVANCED_BUTTONS:
            self.assertIn(advanced, flat)
        self.assertIn('📄 DOCX → PDF', caption)
        self.assertIn('📊 PPTX → PDF', caption)
        self.assertIn('🖼 Images → PDF', ' '.join(sum(rows, [])))
        self.assertIn('📸 Scan Document', ' '.join(sum(rows, [])))

    def _handlers(self):
        bot = FakeBot()
        fake_telebot = SimpleNamespace(types=SimpleNamespace(ReplyKeyboardMarkup=Keyboard, KeyboardButton=Button))
        fake_backends = SimpleNamespace(ContinueHandling=type('ContinueHandling', (), {}))
        with patch.dict(sys.modules, {'telebot': fake_telebot, 'telebot.handler_backends': fake_backends}):
            states = self.office.register_office_to_pdf_handlers(bot, lambda chat:None,
                  lambda chat: None, lambda chat, name:None)
        return bot, states

    def test_docx_button_routes_to_upload(self):
        bot, states = self._handlers()
        bot.dispatch('📄 DOCX → PDF')
        self.assertEqual(states[111]['kind'], 'docx')
        self.assertIn('Upload one .docx file', bot.sent[-1][1])

    def test_pptx_button_routes_to_upload(self):
        bot, states = self._handlers()
        bot.dispatch('📊 PPTX → PDF')
        self.assertEqual(states[111]['kind'], 'pptx')
        self.assertIn('Upload one .pptx file', bot.sent[-1][1])

    def test_slash_commands_work(self):
        for command, suffix in [('/docxpdf', 'docx'), ('/pptxpdf', 'pptx')]:
            with self.subTest(command=command):
                bot, states = self._handlers()
                bot.dispatch(command)
                self.assertEqual(states[111]['kind'], suffix)

    def test_group_chat_rejected(self):
        bot, states = self._handlers()
        bot.dispatch('📊 PPTX → PDF', chat_type='group')
        self.assertEqual(states, {})
        self.assertIn('private chat', bot.sent[-1][1])

    def test_pdf_handlers_register_office_converter(self):
        src=(ROOT/'pdf_tools.py').read_text(encoding='utf-8')
        self.assertIn('from office_to_pdf_v713 import register_office_to_pdf_handlers', src)
        self.assertIn('register_office_to_pdf_handlers(\n        bot,', src)

if __name__ == '__main__':
    unittest.main(verbosity=2)
