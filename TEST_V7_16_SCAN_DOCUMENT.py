"""Offline tests for automatic document scanner + Telegram PDF Tools integration."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import sys
import types
import unittest

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scan_document_v716 import (
    SCAN_BUTTON, SCAN_MODE, SCAN_ADJUST, SCAN_RESCAN, SCAN_SAVE_IMAGE, SCAN_SAVE_PDF,
    SCAN_PREVIEW, SCAN_CANCEL, SCAN_CHANGE, SCAN_ORIGINAL, MAX_SOURCE_BYTES,
    ScanError, read_photo, detect_corners, parse_corners, rectify, create_scan, create_scan_pdf,
)


def paper_sample():
    with Image.new('RGB', (1000, 800), (54, 53, 53)) as image:
        d = ImageDraw.Draw(image)
        d.polygon([(210, 70), (810, 102), (870, 740), (140, 690)], fill='white')
        for y in range(180, 620, 55):
            d.line((260, y, 770, y + 9), fill='#353535', width=5)
        raw = BytesIO()
        image.save(raw, 'JPEG', quality=96)
        return raw.getvalue()


def ordinary_photo():
    with Image.new('RGB', (320, 220), '#aaaaaa') as image:
        buf = BytesIO()
        image.save(buf, 'JPEG')
        return buf.getvalue()


class ScannerEngineTests(unittest.TestCase):
    def test_detect_perspective(self):
        with read_photo(paper_sample()) as source:
            corners = detect_corners(source)
            self.assertIsNotNone(corners)
            self.assertEqual(corners.shape, (4, 2))
            with rectify(source, corners) as page:
                self.assertGreater(page.width, 450)
                self.assertGreater(page.height, 400)
                self.assertNotEqual(page.size, source.size)
                self.assertGreater(sum(page.getpixel((20, 20))), 500)

    def test_unclear_edges_fall_back_to_original(self):
        raw = ordinary_photo()
        with read_photo(raw) as source:
            self.assertIsNone(detect_corners(source))
            with rectify(source, None) as page:
                self.assertEqual(page.size, source.size)

    def test_four_corner_adjustment(self):
        with read_photo(paper_sample()) as source:
            quad = parse_corners('15 8 83 12 89 91 12 85', source.size)
            with rectify(source, quad) as fixed:
                self.assertGreater(fixed.width, 450)
        self.assertEqual(quad.shape, (4, 2))

    def test_comma_separated_corners(self):
        self.assertEqual(parse_corners('5,5,95,5,95,95,5,95', (100, 100)).shape, (4, 2))

    def test_invalid_corner_values(self):
        for value in ('', '5 10 90 95', '-1 5 95 5 95 95 5 95',
                      'nan 5 95 5 95 95 5 95', '5 5 5 5 95 95 5 95',
                      '90 90 10 90 10 10 90 10', '1 1 2 1 2 2 1 2',
                      'x 1 9 1 9 9 1 9'):
            with self.subTest(value=value), self.assertRaises(ScanError):
                parse_corners(value, (1000, 800))

    def test_input_limits(self):
        for blob in (b'', b'not a photo', b'Z' * (MAX_SOURCE_BYTES + 1)):
            with self.subTest(blob=blob[:6]), self.assertRaises(ScanError):
                read_photo(blob)

    def test_preview_is_small(self):
        with read_photo(paper_sample()) as photo:
            edges = detect_corners(photo)
        with create_scan(paper_sample(), edges, preview=True) as preview:
            with Image.open(preview) as img:
                self.assertEqual(img.format, 'JPEG')
                self.assertLessEqual(max(img.size), 1050)

    def test_high_quality_jpeg_no_gps(self):
        data = paper_sample()
        with read_photo(data) as photo:
            quad = detect_corners(photo)
        with create_scan(data, quad) as output:
            self.assertEqual(output.name, 'scanned_document.jpg')
            with Image.open(output) as img:
                self.assertEqual(img.format, 'JPEG')
                self.assertFalse(img.getexif())

    def test_a4_pdf_output(self):
        raw = paper_sample()
        with read_photo(raw) as photo:
            quad = detect_corners(photo)
        with create_scan_pdf(raw, quad) as output:
            self.assertEqual(output.name, 'scanned_document.pdf')
            self.assertTrue(output.getvalue().startswith(b'%PDF'))
            # Pillow PDF has a standard uncompressed MediaBox, no extra PDF test dependency.
            import re
            pdf = output.getvalue()
            self.assertIn(b'/Count 1', pdf)
            match = re.search(rb'/MediaBox\s*\[\s*0\s+0\s+([0-9.]+)\s+([0-9.]+)\s*\]', pdf)
            self.assertIsNotNone(match)
            dimensions = sorted((float(match.group(1)), float(match.group(2))))
            self.assertAlmostEqual(dimensions[0], 595.3, delta=2)
            self.assertAlmostEqual(dimensions[1], 841.9, delta=2)

    def test_original_no_mutation(self):
        raw = paper_sample()
        before = bytes(raw)
        create_scan(raw, None).close()
        self.assertEqual(before, raw)

    def test_no_external_ai_or_data_storage(self):
        import inspect, scan_document_v716
        src = inspect.getsource(scan_document_v716)
        for forbidden in ('requests.post(', 'urllib.request', 'supabase.table(', 'openai.'):
            self.assertNotIn(forbidden, src)


class ContinueHandling:
    pass


class FakeMarkup:
    def __init__(self, *a, **kw): self.buttons = []
    def row(self, *rows): self.buttons.extend(rows)
    def add(self, *rows): self.buttons.extend(rows)


class FakeKeyboard:
    def __init__(self, label): self.text = label


class FakeMessage:
    def __init__(self, text='', user=100, kind='text', chat_type='private', filename='sample.jpg', size=200):
        self.chat = types.SimpleNamespace(id=user, type=chat_type)
        self.from_user = types.SimpleNamespace(id=user, first_name='Learner')
        self.text = text if kind == 'text' else None
        self.content_type = kind
        self.photo = [types.SimpleNamespace(file_id=text, file_size=size)] if kind == 'photo' else None
        self.document = types.SimpleNamespace(file_id=text, file_size=size, file_name=filename) if kind == 'document' else None


class FakeBot:
    def __init__(self, files):
        self.handlers = []
        self.files = files
        self.messages, self.photos, self.documents = [], [], []
    def message_handler(self, **kw):
        def decorate(fn):
            self.handlers.append((kw, fn)); return fn
        return decorate
    def send_message(self, cid, txt, **kw):
        self.messages.append((cid, txt, kw))
        return types.SimpleNamespace(message_id=len(self.messages))
    def send_photo(self, cid, file, **kw):
        self.photos.append((cid, bytes(file.getvalue()), kw))
    def send_document(self, cid, file, **kw):
        self.documents.append((cid, file.name, bytes(file.getvalue()), kw))
    def get_file(self, file_id): return types.SimpleNamespace(file_path=file_id)
    def download_file(self, path): return self.files[path]
    def dispatch(self, m):
        for kw, fn in self.handlers:
            if m.content_type not in kw.get('content_types', ['text']): continue
            commands = kw.get('commands')
            if commands is not None:
                cmd = (m.text or '').split(' ', 1)[0].split('@',1)[0].lstrip('/')
                if cmd not in commands: continue
            if 'func' in kw and not kw['func'](m): continue
            result = fn(m)
            if not isinstance(result, ContinueHandling): return


class ScannerBotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Allow tests to run even without the Telegram and PDF packages installed.
        if 'telebot' not in sys.modules:
            try: import telebot
            except ImportError:
                tb = types.ModuleType('telebot')
                t = types.ModuleType('telebot.types')
                h = types.ModuleType('telebot.handler_backends')
                t.ReplyKeyboardMarkup = FakeMarkup
                t.KeyboardButton = FakeKeyboard
                h.ContinueHandling = ContinueHandling
                tb.types = t
                sys.modules.update({'telebot':tb,'telebot.types':t,'telebot.handler_backends':h})
        if 'PyPDF2' not in sys.modules:
            try: import PyPDF2
            except ImportError:
                p = types.ModuleType('PyPDF2')
                p.PdfReader = object
                p.PdfWriter = object
                sys.modules['PyPDF2'] = p
        if 'navigation' not in sys.modules:
            n = types.ModuleType('navigation')
            n.should_yield_to_navigation = lambda t: bool(t and (t.startswith('/') or t in ('📄 PDF Tools', '🏠 Main Menu', '🔗 Merge PDFs')))
            sys.modules['navigation'] = n
        if 'text_pdf_v711' not in sys.modules:
            t = types.ModuleType('text_pdf_v711')
            t.create_text_pdf = lambda txt: BytesIO(b'%PDF-1.4')
            t.TextPdfError = ValueError
            t.MAX_TEXT_CHARS = 10000
            t.MAX_TEXT_MESSAGES = 30
            t.PDF_TEXT_MODE = 'text_pdf_v711'
            t.PDF_TEXT_BUTTON = '📝 Text → PDF'
            t.PDF_TEXT_CREATE = '✅ Create Text PDF'
            t.PDF_TEXT_CLEAR = '🧹 Clear Text'
            sys.modules['text_pdf_v711'] = t
        import pdf_tools
        cls.pdf = pdf_tools

    def setUp(self):
        self.pdf.pdf_state.clear()
        self.bot = FakeBot({'paper':paper_sample(), 'blank':ordinary_photo(), 'invalid':b'bad'})
        self.pdf.register_pdf_handlers(self.bot, lambda cid, name: self.bot.send_message(cid, 'MAIN MENU'))

    def test_scan_button_and_command(self):
        self.bot.dispatch(FakeMessage(text='/scan'))
        self.assertEqual(self.pdf.pdf_state[100]['mode'], SCAN_MODE)
        self.bot.dispatch(FakeMessage(text=SCAN_BUTTON, user=101))
        self.assertEqual(self.pdf.pdf_state[101]['mode'], SCAN_MODE)
        menu = self.pdf._pdf_tools_menu
        menu(self.bot, 102)
        kb = self.bot.messages[-1][2]['reply_markup']
        items = getattr(kb, "buttons", None)
        if items is None:
            items = [button for row in kb.keyboard for button in row]
        
        self.assertIn(
    SCAN_BUTTON,
    [
        button.get("text") if isinstance(button, dict) else button.text
        for button in items
    ],
)


    def test_photo_preview_then_save_jpg(self):
        self.bot.dispatch(FakeMessage('/scan'))
        self.bot.dispatch(FakeMessage('paper', kind='photo'))
        self.assertEqual(len(self.bot.photos), 1)
        self.assertIsNotNone(self.pdf.pdf_state[100]['corners'])
        self.bot.dispatch(FakeMessage(SCAN_SAVE_IMAGE))
        self.assertEqual(len(self.bot.documents), 1)
        self.assertEqual(self.bot.documents[0][1], 'scanned_document.jpg')
        self.assertEqual(self.pdf.pdf_state[100]['mode'], 'menu')

    def test_photo_preview_then_save_pdf(self):
        self.bot.dispatch(FakeMessage('/scan'))
        self.bot.dispatch(FakeMessage('paper', kind='document', filename='sheet.jpg'))
        self.assertEqual(len(self.bot.photos), 1)
        self.bot.dispatch(FakeMessage(SCAN_SAVE_PDF))
        self.assertEqual(self.bot.documents[-1][1], 'scanned_document.pdf')
        self.assertTrue(self.bot.documents[-1][2].startswith(b'%PDF'))

    def test_retake_adjust_and_rescan(self):
        self.bot.dispatch(FakeMessage('/scan'))
        self.bot.dispatch(FakeMessage('paper', kind='photo'))
        self.bot.dispatch(FakeMessage(SCAN_ADJUST))
        self.assertTrue(self.pdf.pdf_state[100]['await_corners'])
        self.bot.dispatch(FakeMessage('15 8 83 12 89 91 12 85'))
        self.assertFalse(self.pdf.pdf_state[100]['await_corners'])
        self.bot.dispatch(FakeMessage(SCAN_RESCAN))
        self.assertEqual(len(self.bot.photos), 3)
        self.bot.dispatch(FakeMessage(SCAN_CHANGE))
        self.assertIsNone(self.pdf.pdf_state[100]['original'])

    def test_uncertain_edges_require_manual_adjustment(self):
        self.bot.dispatch(FakeMessage('/scan'))
        self.bot.dispatch(FakeMessage('blank', kind='photo'))
        self.assertIsNone(self.pdf.pdf_state[100]['corners'])
        self.assertIn('edges were not detected', self.bot.photos[-1][2]['caption'])

    def test_group_rejected(self):
        self.bot.dispatch(FakeMessage('/scan', chat_type='supergroup'))
        self.assertNotIn(100, self.pdf.pdf_state)

    def test_invalid_file_keeps_scan_mode(self):
        self.bot.dispatch(FakeMessage('/scan'))
        self.bot.dispatch(FakeMessage('invalid', kind='document', filename='notepad.pdf'))
        self.assertIsNone(self.pdf.pdf_state[100]['original'])
        self.assertIn('not a PDF', self.bot.messages[-1][1])

    def test_cancel_returns_pdf_tools(self):
        self.bot.dispatch(FakeMessage('/scan'))
        self.bot.dispatch(FakeMessage(SCAN_CANCEL))
        self.assertEqual(self.pdf.pdf_state[100]['mode'], 'menu')

    def test_other_pdf_tools_not_intercepted(self):
        self.bot.dispatch(FakeMessage('🔗 Merge PDFs'))
        self.assertEqual(self.pdf.pdf_state[100]['mode'], 'merge')
        self.bot.dispatch(FakeMessage('/scan'))
        self.bot.dispatch(FakeMessage('🏠 Main Menu'))
        self.assertNotIn(100, self.pdf.pdf_state)
        self.assertEqual(self.bot.messages[-1][1], 'MAIN MENU')

    def test_separate_users_state(self):
        self.bot.dispatch(FakeMessage('/scan', user=100))
        self.bot.dispatch(FakeMessage('/scan', user=222))
        self.bot.dispatch(FakeMessage('paper', kind='photo', user=100))
        self.assertIsNotNone(self.pdf.pdf_state[100]['original'])
        self.assertIsNone(self.pdf.pdf_state[222]['original'])


if __name__ == '__main__':
    unittest.main()
