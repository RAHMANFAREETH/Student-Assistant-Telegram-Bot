"""V7.13 offline tests. Real conversion runs when LibreOffice is installed locally."""
import io
import threading
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
import types
import zipfile

from office_to_pdf_v713 import (
    convert_office_to_pdf, locate_libreoffice, _safe_filename, _validate_document,
    OfficePdfError, MAX_INPUT_BYTES, DOCX_BUTTON, PPTX_BUTTON,
    register_office_to_pdf_handlers,
)


def fixture_docx():
    from docx import Document
    d = Document()
    d.add_heading("Academic Notes", 0)
    d.add_paragraph("This Word document retains its heading and text in PDF.")
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).text = "Subject"
    t.cell(0, 1).text = "Grade"
    t.cell(1, 0).text = "Arabic"
    t.cell(1, 1).text = "A"
    buffer = io.BytesIO()
    d.save(buffer)
    return buffer.getvalue()


def fixture_pptx():
    from pptx import Presentation
    from pptx.util import Inches
    p = Presentation()
    for idx in range(2):
        slide = p.slides.add_slide(p.slide_layouts[6])
        textbox = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(7), Inches(1))
        textbox.text_frame.text = "University Slide " + str(idx + 1)
    buffer = io.BytesIO()
    p.save(buffer)
    return buffer.getvalue()


class ConversionUnitTests(unittest.TestCase):
    def test_filename_no_path_traversal(self):
        self.assertEqual(_safe_filename("../../secret name.docx", ".pdf"), "secret name.pdf")
        self.assertEqual(_safe_filename(r"C:\\temp\\slides.pptx", ".pdf"), "slides.pdf")

    def test_only_docx_and_pptx(self):
        with self.assertRaises(ValueError):
            convert_office_to_pdf(b"x", "test.pdf", "pdf", binary="no")

    def test_reject_wrong_extension(self):
        with self.assertRaisesRegex(OfficePdfError, "DOCX"):
            convert_office_to_pdf(b"not a document", "test.pdf", "docx", binary="no")

    def test_fake_archive_rejected(self):
        with self.assertRaisesRegex(OfficePdfError, "valid Office"):
            convert_office_to_pdf(b"PK\x03\x04bad", "test.docx", "docx", binary="no")

    def test_large_input_rejected_without_running(self):
        with self.assertRaisesRegex(OfficePdfError, "large"):
            convert_office_to_pdf(b"x" * (MAX_INPUT_BYTES + 1), "big.pptx", "pptx", binary="no")

    def test_reject_zip_bomb_header(self):
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", "ok")
            z.writestr("word/document.xml", b"A" * (121 * 1024 * 1024))
        with self.assertRaisesRegex(OfficePdfError, "complex"):
            _validate_document(out.getvalue(), "docx")

    def test_missing_engine_is_error_not_fake_pdf(self):
        with patch("office_to_pdf_v713.locate_libreoffice", return_value=None):
            with self.assertRaisesRegex(OfficePdfError, "not installed"):
                convert_office_to_pdf(fixture_docx(), "test.docx", "docx")

    @unittest.skipUnless(locate_libreoffice(), "LibreOffice not installed; Docker Render will provide it")
    def test_real_docx_conversion_with_heading_and_table(self):
        pdf = convert_office_to_pdf(fixture_docx(), "Arabic lesson.docx", "docx")
        self.assertEqual(pdf.name, "Arabic lesson.pdf")
        self.assertTrue(pdf.read(5).startswith(b"%PDF-"))
        self.assertGreater(pdf.getbuffer().nbytes, 3000)
        pdf.seek(0)
        try:
            from pypdf import PdfReader
            text = " ".join(page.extract_text() or "" for page in PdfReader(pdf).pages)
            self.assertIn("Academic Notes", text)
            self.assertIn("Subject", text)
        except ImportError:
            pass
        pdf.close()

    @unittest.skipUnless(locate_libreoffice(), "LibreOffice not installed; Docker Render will provide it")
    def test_real_pptx_conversion_all_slides(self):
        pdf = convert_office_to_pdf(fixture_pptx(), "Lecture.pptx", "pptx")
        self.assertEqual(pdf.name, "Lecture.pdf")
        self.assertTrue(pdf.read(5).startswith(b"%PDF-"))
        pdf.seek(0)
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf)
            self.assertEqual(len(reader.pages), 2)
            self.assertIn("University Slide 1", reader.pages[0].extract_text())
            self.assertIn("University Slide 2", reader.pages[1].extract_text())
        except ImportError:
            pass
        pdf.close()


class FakeButton:
    def __init__(self, text):
        self.text = text

class FakeMarkup:
    def __init__(self, **kwargs):
        self.buttons = []
    def row(self, *values):
        self.buttons.extend(values)
    def add(self, *values):
        self.buttons.extend(values)

class FakeBot:
    def __init__(self):
        self.handlers = []
        self.messages = []
        self.documents = []
        self.upload_bytes = b""
        self.download_count = 0
        self.done = threading.Event()
    def message_handler(self, **opts):
        def decorate(f):
            self.handlers.append((opts, f))
            return f
        return decorate
    def send_message(self, chat_id, text, **kwargs):
        self.messages.append((chat_id, text, kwargs))
    def send_chat_action(self, *args):
        pass
    def get_file(self, file_id):
        return types.SimpleNamespace(file_path="fake_path")
    def download_file(self, path):
        self.download_count += 1
        return self.upload_bytes
    def send_document(self, chat_id, doc, **kwargs):
        self.documents.append((chat_id, doc.read(), kwargs))
        self.done.set()
    def dispatch(self, msg):
        for opts, fn in self.handlers:
            if msg.content_type not in opts.get("content_types", ["text"]):
                continue
            commands = opts.get("commands")
            if commands:
                if not msg.text or msg.text.split()[0].split("@", 1)[0].lstrip("/") not in commands:
                    continue
            if opts.get("func") and not opts["func"](msg):
                continue
            result = fn(msg)
            if result is not None and result.__class__.__name__ == "ContinueHandling":
                continue
            return True
        return False


def m(text="", *, kind="private", content_type="text", filename="", size=10, user=100):
    return types.SimpleNamespace(
        text=text if content_type == "text" else None, content_type=content_type,
        chat=types.SimpleNamespace(id=user, type=kind),
        from_user=types.SimpleNamespace(id=user, first_name="Student"),
        document=types.SimpleNamespace(file_name=filename, file_size=size, file_id="fake") if content_type == "document" else None,
    )


class TelegramFlowTests(unittest.TestCase):
    def setUp(self):
        self.bot = FakeBot()
        self.opened = []
        self.exited = []
        fake_telebot = types.ModuleType("telebot")
        fake_telebot.types = types.SimpleNamespace(ReplyKeyboardMarkup=FakeMarkup, KeyboardButton=FakeButton)
        backends = types.ModuleType("telebot.handler_backends")
        backends.ContinueHandling = type("ContinueHandling", (), {})
        with patch.dict(sys.modules, {"telebot": fake_telebot, "telebot.handler_backends": backends}):
            self.state = register_office_to_pdf_handlers(
                self.bot, lambda cid: self.opened.append(cid),
                lambda cid: self.exited.append(cid), lambda cid, _: self.opened.append("main"),
            )

    def test_docx_button_starts_upload_flow(self):
        self.bot.dispatch(m(DOCX_BUTTON))
        self.assertEqual(self.state[100]["kind"], "docx")
        self.assertIn("Upload one .docx", self.bot.messages[-1][1])
        self.assertEqual(self.exited, [100])

    def test_pptx_command_starts(self):
        self.bot.dispatch(m("/pptxpdf"))
        self.assertEqual(self.state[100]["kind"], "pptx")

    def test_not_allowed_in_group(self):
        self.bot.dispatch(m(DOCX_BUTTON, kind="group"))
        self.assertEqual(self.state, {})
        self.assertIn("private", self.bot.messages[-1][1])

    def test_upload_ignored_without_choosing_a_tool(self):
        result = self.bot.dispatch(m(content_type="document", filename="any.docx"))
        self.assertFalse(result)
        self.assertEqual(self.bot.download_count, 0)

    def test_wrong_file_does_not_download(self):
        self.bot.dispatch(m(PPTX_BUTTON))
        self.bot.dispatch(m(content_type="document", filename="notes.docx"))
        self.assertEqual(self.bot.download_count, 0)
        self.assertIn("PPTX", self.bot.messages[-1][1])

    def test_oversized_file_does_not_download(self):
        self.bot.dispatch(m(DOCX_BUTTON))
        self.bot.dispatch(m(content_type="document", filename="notes.docx", size=MAX_INPUT_BYTES + 1))
        self.assertEqual(self.bot.download_count, 0)
        self.assertIn("too large", self.bot.messages[-1][1].lower())

    def test_cancel_returns_to_pdf_tools(self):
        self.bot.dispatch(m(DOCX_BUTTON))
        self.bot.dispatch(m("❌ Cancel"))
        self.assertEqual(self.state, {})
        self.assertEqual(self.opened, [100])

    def test_main_menu_exits(self):
        self.bot.dispatch(m(PPTX_BUTTON))
        self.bot.dispatch(m("🏠 Main Menu"))
        self.assertEqual(self.state, {})
        self.assertEqual(self.opened, ["main"])

    def test_other_pdf_mode_yields(self):
        self.bot.dispatch(m(DOCX_BUTTON))
        self.bot.dispatch(m("📝 Text → PDF"))
        self.assertEqual(self.state, {})

    def test_actual_telegram_flow_sends_pdf(self):
        self.bot.dispatch(m(DOCX_BUTTON))
        self.bot.upload_bytes = fixture_docx()
        with patch("office_to_pdf_v713.convert_office_to_pdf", return_value=io.BytesIO(b"%PDF-fake")) as conv:
            self.bot.dispatch(m(content_type="document", filename="notes.docx", size=len(self.bot.upload_bytes)))
        self.assertTrue(self.bot.done.wait(timeout=5), "Background conversion did not return a PDF")
        self.assertEqual(len(self.bot.documents), 1)
        self.assertEqual(self.bot.documents[0][1], b"%PDF-fake")
        self.assertEqual(self.opened, [100])
        self.assertEqual(self.state, {})
        conv.assert_called_once()

    def test_cancel_while_worker_is_active_does_not_send_pdf(self):
        self.bot.dispatch(m(DOCX_BUTTON))
        self.bot.upload_bytes = fixture_docx()
        started, proceed = threading.Event(), threading.Event()

        def slow_convert(*args, **kwargs):
            started.set()
            proceed.wait(timeout=3)
            return io.BytesIO(b"%PDF-fake")

        with patch("office_to_pdf_v713.convert_office_to_pdf", side_effect=slow_convert):
            self.bot.dispatch(m(content_type="document", filename="notes.docx"))
            self.assertTrue(started.wait(timeout=2))
            self.bot.dispatch(m("❌ Cancel"))
            proceed.set()
            for _ in range(100):
                if not self.state:
                    break
                threading.Event().wait(.01)
            threading.Event().wait(.05)
        self.assertEqual(self.bot.documents, [])
        self.assertNotIn(100, self.state)

    def test_second_document_during_conversion_is_not_downloaded(self):
        self.bot.dispatch(m(PPTX_BUTTON))
        self.bot.upload_bytes = fixture_pptx()
        started, proceed = threading.Event(), threading.Event()

        def slow_convert(*args, **kwargs):
            started.set()
            proceed.wait(timeout=3)
            return io.BytesIO(b"%PDF-fake")

        with patch("office_to_pdf_v713.convert_office_to_pdf", side_effect=slow_convert):
            self.bot.dispatch(m(content_type="document", filename="slides.pptx"))
            self.assertTrue(started.wait(timeout=2))
            self.bot.dispatch(m(content_type="document", filename="slides2.pptx"))
            self.assertEqual(self.bot.download_count, 1)
            self.assertIn("still converting", self.bot.messages[-1][1])
            proceed.set()
            self.assertTrue(self.bot.done.wait(timeout=3))

    def test_failed_document_can_retry(self):
        self.bot.dispatch(m(DOCX_BUTTON))
        self.bot.upload_bytes = b"not a zip"
        self.bot.dispatch(m(content_type="document", filename="notes.docx"))
        self.assertIn(100, self.state)
        for _ in range(50):
            if any("valid Office" in message for _, message, _ in self.bot.messages):
                break
            threading.Event().wait(.02)
        self.assertTrue(any("valid Office" in message for _, message, _ in self.bot.messages))


if __name__ == "__main__":
    unittest.main()
