"""Unit/integration tests that run offline without Telegram or web credentials."""
import io
import sys
import threading
import time
import types
import unittest
import zipfile

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen.canvas import Canvas
from docx import Document

from advanced_pdf_v717 import (
    AdvancedPdfError, COMPRESS_BUTTON, PDF_WORD_BUTTON, PDF_IMAGES_BUTTON,
    ORGANIZE_BUTTON, WATERMARK_BUTTON, compress_pdf, pdf_to_word,
    pdf_to_images, organize_pdf, watermark_pdf, pdf_info, parse_pages,
    register_advanced_pdf_handlers, safe_stem,
)


def fixture_pdf(pages=3):
    output=io.BytesIO(); c=Canvas(output,pagesize=(595,842),pageCompression=1)
    for n in range(pages):
        c.setFont("Helvetica",16)
        c.drawString(70,767,f"University studies page {n+1}")
        c.showPage()
    c.save(); return output.getvalue()


def image_pdf():
    from PIL import Image
    import random
    rng = random.Random(9)
    img = Image.frombytes("RGB", (500,500), rng.randbytes(500*500*3))
    png=io.BytesIO(); img.save(png,format="PNG")
    from reportlab.lib.utils import ImageReader
    result=io.BytesIO(); c=Canvas(result,pagesize=(400,400),pageCompression=0)
    c.drawImage(ImageReader(io.BytesIO(png.getvalue())),0,0,width=400,height=400)
    c.showPage(); c.save()
    return result.getvalue()


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pdf = fixture_pdf()

    def test_pdf_info(self):
        self.assertEqual(pdf_info(self.pdf), 3)

    def test_reject_invalid_pdf(self):
        with self.assertRaises(AdvancedPdfError): pdf_info(b"not a PDF")

    def test_reject_oversized_pdf(self):
        with self.assertRaises(AdvancedPdfError): pdf_info(b"0" * (10 * 1024 * 1024 + 1))

    def test_reject_password_protected(self):
        writer=PdfWriter(); writer.append(PdfReader(io.BytesIO(self.pdf)))
        writer.encrypt("secret", "owner")
        output=io.BytesIO(); writer.write(output); protected=output.getvalue()
        with self.assertRaisesRegex(AdvancedPdfError, "Password-protected"):
            pdf_info(protected)

    def test_parse_reorder_duplicate(self):
        self.assertEqual(parse_pages("3,1,2-3,3", 3, preserve_duplicates=True), [2,0,1,2,2])

    def test_parse_deduplicate(self):
        self.assertEqual(parse_pages("3,1,3", 3), [2,0])

    def test_parse_invalid(self):
        for text in ("0", "7", "no", "1,,2", "1--2", ""):
            with self.subTest(text=text), self.assertRaises(AdvancedPdfError): parse_pages(text, 3)

    def test_parse_all_max(self):
        with self.assertRaises(AdvancedPdfError): parse_pages("All", 23, max_pages=20)

    def test_safe_filename(self):
        self.assertEqual(safe_stem(r"..\..\weird/name.pdf"), "name")

    def test_compress_all_levels(self):
        for level in ("🟢 Light", "🟡 Balanced", "🔴 Strong"):
            with self.subTest(level=level):
                out, note = compress_pdf(self.pdf, "notes.pdf", level)
                self.assertTrue(out.getvalue().startswith(b"%PDF"))
                self.assertEqual(pdf_info(out.getvalue()), 3)
                self.assertIn("KB", note)

    def test_compress_real_image_heavy(self):
        data = image_pdf()
        out, note = compress_pdf(data, "large.pdf", "🔴 Strong")
        self.assertLess(len(out.getvalue()), len(data))
        self.assertEqual(pdf_info(out.getvalue()), 1)

    def test_word_editable_content(self):
        out = pdf_to_word(self.pdf, "notes.pdf")
        self.assertEqual(out.name, "notes.docx")
        docx = Document(out)
        text = " ".join(p.text for p in docx.paragraphs)
        self.assertIn("University studies page 1", text)
        self.assertIn("University studies page 3", text)

    def test_word_reject_scanned(self):
        writer=PdfWriter(); writer.add_blank_page(width=595,height=842); output=io.BytesIO(); writer.write(output); blob=output.getvalue()
        with self.assertRaisesRegex(AdvancedPdfError, "OCR"):
            pdf_to_word(blob, "blank.pdf")

    def test_images_png_jpg(self):
        for fmt in ("png", "jpg"):
            with self.subTest(fmt=fmt):
                out = pdf_to_images(self.pdf, "a.pdf", fmt, [0,2])
                with zipfile.ZipFile(out) as zf:
                    self.assertEqual(zf.namelist(), [f"page_001.{fmt}", f"page_003.{fmt}"])
                    self.assertGreater(len(zf.read(zf.namelist()[0])), 100)

    def test_images_invalid_index(self):
        with self.assertRaises(AdvancedPdfError): pdf_to_images(self.pdf, "a.pdf", "jpg", [9])

    def test_organize_and_delete(self):
        out = organize_pdf(self.pdf, "a.pdf", [2,0,0])
        result=PdfReader(out)
        self.assertEqual(len(result.pages), 3)
        self.assertIn("page 3", result.pages[0].extract_text())
        self.assertIn("page 1", result.pages[1].extract_text())
        self.assertIn("page 1", result.pages[2].extract_text())

    def test_watermark_positions(self):
        for position in ("top", "center", "bottom"):
            with self.subTest(position=position):
                out = watermark_pdf(self.pdf, "a.pdf", "DRAFT", position)
                pdf=PdfReader(out)
                self.assertEqual(len(pdf.pages),3)
                self.assertIn("DRAFT",pdf.pages[0].extract_text())

    def test_watermark_escapes_html(self):
        out = watermark_pdf(self.pdf, "a.pdf", "<DRAFT & SAFE>", "center")
        pdf=PdfReader(out)
        self.assertIn("DRAFT",pdf.pages[0].extract_text())

    def test_watermark_rejects_long(self):
        with self.assertRaises(AdvancedPdfError): watermark_pdf(self.pdf, "x.pdf", "x" * 61, "center")


class FakeMarkup:
    def __init__(self, **kwargs): self.rows = []
    def row(self, *args): self.rows.append(args)
    def add(self, *args): self.rows.append(args)

class FakeButton:
    def __init__(self, text): self.text = text

class FakeContinueHandling:
    pass


class FakeBot:
    def __init__(self, blob):
        self.handlers = []; self.sent = []; self.docs = []; self.blob = blob
    def message_handler(self, **options):
        def decor(fn):
            self.handlers.append((options, fn))
            return fn
        return decor
    def send_message(self, chat_id, text, **kwargs): self.sent.append((chat_id, text, kwargs))
    def send_document(self, chat_id, data, **kwargs): self.docs.append((chat_id, data.getvalue(), data.name, kwargs))
    def get_file(self, file_id): return types.SimpleNamespace(file_path="test_upload", file_size=len(self.blob))
    def download_file(self, path): return self.blob
    def dispatch(self, text=None, content_type="text", filename="notes.pdf"):
        msg = types.SimpleNamespace(chat=types.SimpleNamespace(id=11, type="private"),
             from_user=types.SimpleNamespace(first_name="Student"),
             text=text, content_type=content_type,
             document=types.SimpleNamespace(file_name=filename, file_id="fid", file_size=len(self.blob)))
        for opts, fn in self.handlers:
            if content_type not in opts.get("content_types", ["text"]): continue
            if "func" in opts and not opts["func"](msg): continue
            fn(msg); return True
        return False


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.old_telebot = sys.modules.get("telebot")
        self.old_backends = sys.modules.get("telebot.handler_backends")
        module = types.ModuleType("telebot")
        module.types = types.SimpleNamespace(ReplyKeyboardMarkup=FakeMarkup, KeyboardButton=FakeButton)
        backend = types.ModuleType("telebot.handler_backends")
        backend.ContinueHandling = FakeContinueHandling
        sys.modules["telebot"] = module
        sys.modules["telebot.handler_backends"] = backend
        self.bot = FakeBot(fixture_pdf())
        self.opened = []
        self.states = register_advanced_pdf_handlers(self.bot, self.opened.append,
                                                       lambda cid: None, lambda cid, name: None)
    def tearDown(self):
        for key, original in (("telebot", self.old_telebot), ("telebot.handler_backends", self.old_backends)):
            if original is None: sys.modules.pop(key, None)
            else: sys.modules[key] = original
    def _finish(self):
        for _ in range(200):
            if self.bot.docs: return
            time.sleep(0.025)
        self.fail("Conversion worker did not send document")
    def test_buttons_and_document_routing(self):
        self.assertTrue(self.bot.dispatch(COMPRESS_BUTTON))
        self.assertEqual(self.states[11]["tool"], "compress")
        self.bot.dispatch(content_type="document")
        self.assertEqual(self.states[11]["stage"], "level")
        self.bot.dispatch("🟢 Light")
        self._finish()
        self.assertEqual(self.bot.docs[0][2], "notes_compressed.pdf")
    def test_word_file_uploaded_and_converted(self):
        self.bot.dispatch(PDF_WORD_BUTTON)
        self.bot.dispatch(content_type="document")
        self._finish()
        self.assertEqual(self.bot.docs[0][2], "notes.docx")
    def test_images_upload_format_pages(self):
        self.bot.dispatch(PDF_IMAGES_BUTTON)
        self.bot.dispatch(content_type="document")
        self.bot.dispatch("📷 JPG")
        self.bot.dispatch("1,3")
        self._finish()
        self.assertEqual(self.bot.docs[0][2], "notes_images.zip")
    def test_organize_upload_order(self):
        self.bot.dispatch(ORGANIZE_BUTTON)
        self.bot.dispatch(content_type="document")
        self.bot.dispatch("3,1")
        self._finish()
        self.assertTrue(self.bot.docs[0][2].endswith("_organized.pdf"))
    def test_watermark_upload_position(self):
        self.bot.dispatch(WATERMARK_BUTTON)
        self.bot.dispatch(content_type="document")
        self.bot.dispatch("CONFIDENTIAL")
        self.bot.dispatch("🎯 Center")
        self._finish()
        self.assertTrue(self.bot.docs[0][2].endswith("_watermarked.pdf"))
    def test_bad_extension(self):
        self.bot.dispatch(PDF_WORD_BUTTON)
        self.bot.dispatch(content_type="document", filename="malicious.docx")
        self.assertIn(".pdf", self.bot.sent[-1][1])
        self.assertFalse(self.bot.docs)
    def test_cancel(self):
        self.bot.dispatch(COMPRESS_BUTTON)
        self.bot.dispatch("❌ Cancel")
        self.assertNotIn(11, self.states)
        self.assertEqual(self.opened, [11])


class MenuInstallerTests(unittest.TestCase):
    def test_integration_menu_and_office_buttons(self):
        import ast
        from pathlib import Path
        path = Path(__file__).with_name("pdf_tools.py")
        if not path.is_file():
            self.skipTest("Run after installing in your actual StudentAssistantBot project")
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        body = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_pdf_tools_menu")
        fake = types.SimpleNamespace(ReplyKeyboardMarkup=FakeMarkup, KeyboardButton=FakeButton)
        env = {"types": fake, "pdf_state": {}, "ADVANCED_BUTTONS": (
            COMPRESS_BUTTON, PDF_WORD_BUTTON, PDF_IMAGES_BUTTON, ORGANIZE_BUTTON, WATERMARK_BUTTON),
            "PHOTO_CROP_BUTTON": "Photo/Image Crop", "SCAN_BUTTON": "Scan Document",
            "PDF_TEXT_BUTTON": "Text → PDF"}
        exec(compile(ast.Module(body=[body], type_ignores=[]), str(path), "exec"), env)
        bot = FakeBot(fixture_pdf())
        env["_pdf_tools_menu"](bot, 11)
        self.assertEqual(len(bot.sent), 1)
        markup = bot.sent[0][2]["reply_markup"]
        labels = [x.text for row in markup.rows for x in row]
        for button in (*env["ADVANCED_BUTTONS"], "📄 DOCX → PDF", "📊 PPTX → PDF"):
            self.assertEqual(labels.count(button), 1, button)
        self.assertEqual(labels[-1], "🏠 Main Menu")
        self.assertIn("💧 Add Watermark", bot.sent[0][1])

    def test_installer_registered_before_office(self):
        import ast
        from pathlib import Path
        path = Path(__file__).with_name("pdf_tools.py")
        if not path.is_file():
            self.skipTest("Run after installing in your actual StudentAssistantBot project")
        src = path.read_text(encoding="utf-8")
        self.assertIn("from advanced_pdf_v717 import", src)
        self.assertLess(src.index("    register_advanced_pdf_handlers("),
                        src.index("    register_office_to_pdf_handlers("))



if __name__ == "__main__":
    unittest.main()

# Menu integration tests run when the installer has been applied alongside pdf_tools.py.
# They intentionally avoid import/initialization of the production bot and its APIs.
