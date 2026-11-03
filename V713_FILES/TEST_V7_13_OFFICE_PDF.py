"""Offline tests: python -m unittest TEST_V7_13_OFFICE_PDF.py -v"""
import importlib
from io import BytesIO
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader


class _KeyboardButton:
    def __init__(self, text):
        self.text = text


class _ReplyKeyboardMarkup:
    def __init__(self, **kwargs):
        self.rows = []

    def add(self, *buttons):
        self.rows.append(list(buttons))

    def row(self, *buttons):
        self.rows.append(list(buttons))


class _Bot:
    def __init__(self):
        self.handlers = []
        self.messages = []
        self.documents = []
        self.files = {}
        self.actions = []

    def message_handler(self, commands=None, func=None, content_types=None, **kwargs):
        def decorate(fn):
            self.handlers.append((commands, func, content_types or ["text"], fn))
            return fn
        return decorate

    def dispatch(self, text=None, *, user=101, kind="text", chat_type="private",
                 filename="document.docx", blob=None, size=None):
        if blob is not None:
            self.files["test-file"] = blob
        msg = types.SimpleNamespace(
            text=text,
            content_type=kind,
            chat=types.SimpleNamespace(id=user, type=chat_type),
            from_user=types.SimpleNamespace(id=user, first_name="User"),
            document=types.SimpleNamespace(file_name=filename, file_id="test-file",
                                           file_size=size if size is not None else len(blob or b"")),
        )
        for commands, func, content_types, fn in self.handlers:
            if kind not in content_types:
                continue
            if commands is not None:
                if not text or not text.startswith("/"):
                    continue
                cmd = text.split()[0].split("@")[0].lstrip("/")
                if cmd not in commands:
                    continue
            if func is not None and not func(msg):
                continue
            return fn(msg)
        return None

    def send_message(self, chat, message, **kw):
        self.messages.append((chat, message, kw))
        return types.SimpleNamespace(message_id=len(self.messages))

    def send_document(self, chat, doc, **kw):
        self.documents.append((chat, doc.getvalue(), kw))

    def send_chat_action(self, chat, action):
        self.actions.append((chat, action))

    def get_file(self, file_id):
        return types.SimpleNamespace(file_path=file_id)

    def download_file(self, path):
        return self.files[path]


class OfficePdfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake = types.ModuleType("telebot")
        fake.types = types.SimpleNamespace(ReplyKeyboardMarkup=_ReplyKeyboardMarkup,
                                           KeyboardButton=_KeyboardButton)
        cls.fake_modules = patch.dict(sys.modules, {"telebot": fake})
        cls.fake_modules.start()
        import text_pdf_v711
        cls.mod = importlib.import_module("office_pdf_v713")
        import docx
        import pptx
        cls.docx = docx
        cls.pptx = pptx
        # System fonts are used only for offline tests, never distributed to users.
        fonts = {
            "Base": "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "Tamil": "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf",
            "Sinhala": "/usr/share/fonts/truetype/noto/NotoSansSinhala-Regular.ttf",
            "Arabic": "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        }
        if not all(Path(path).is_file() for path in fonts.values()):
            # On Windows, the real installed Noto fonts may be used instead.
            fonts = text_pdf_v711.find_fonts()
        cls.font_patch = patch.object(cls.mod, "find_fonts", return_value=fonts)
        cls.font_patch.start()
        cls.doc_blob = cls.make_docx()
        cls.ppt_blob = cls.make_pptx()

    @classmethod
    def tearDownClass(cls):
        cls.font_patch.stop()
        cls.fake_modules.stop()

    @classmethod
    def make_docx(cls):
        doc = cls.docx.Document()
        doc.add_heading("Phonetics Notes", 1)
        doc.add_paragraph("University phonetics study notes.")
        table = doc.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Topic"
        table.cell(0, 1).text = "Definition"
        table.cell(1, 0).text = "Phoneme"
        table.cell(1, 1).text = "Sound unit"
        stream = BytesIO()
        doc.save(stream)
        return stream.getvalue()

    @classmethod
    def make_pptx(cls):
        presentation = cls.pptx.Presentation()
        layout = presentation.slide_layouts[6]
        for name in ("First slide", "Second slide"):
            slide = presentation.slides.add_slide(layout)
            box = slide.shapes.add_textbox(457200, 457200, 5486400, 1000000)
            box.text_frame.text = name
        stream = BytesIO()
        presentation.save(stream)
        return stream.getvalue()

    def setUp(self):
        self.state = {}
        self.bot = _Bot()
        self.mod.register_office_pdf_v713(
            self.bot, self.state,
            lambda bot, chat: (self.state.__setitem__(chat, {"mode": "menu"}),
                               bot.send_message(chat, "PDF Tools")),
            lambda *buttons: _ReplyKeyboardMarkup(),
        )

    def test_docx_basic_pdf_has_readable_text(self):
        with patch.object(self.mod, "_libreoffice_executable", return_value=None):
            answer = self.mod.convert_document(self.doc_blob, "docx", "demo.docx")
        self.assertEqual(answer.backend, "basic")
        data = answer.pdf.getvalue()
        self.assertTrue(data.startswith(b"%PDF-"))
        doc = PdfReader(BytesIO(data))
        joined = "\n".join(page.extract_text() for page in doc.pages)
        self.assertIn("Phonetics Notes", joined)
        self.assertIn("Sound unit", joined)
        self.assertEqual(answer.pdf.name, "demo_converted.pdf")

    def test_pptx_basic_one_page_per_slide(self):
        with patch.object(self.mod, "_libreoffice_executable", return_value=None):
            answer = self.mod.convert_document(self.ppt_blob, "pptx", "lesson.pptx")
        doc = PdfReader(BytesIO(answer.pdf.getvalue()))
        self.assertEqual(len(doc.pages), 2)
        self.assertIn("First slide", doc.pages[0].extract_text())
        self.assertIn("Second slide", doc.pages[1].extract_text())
        self.assertEqual(answer.backend, "basic")
        self.assertIn("formatting", answer.warning)

    def test_real_libreoffice_docx_when_available(self):
        executable = self.mod._libreoffice_executable()
        if not executable:
            self.skipTest("LibreOffice not installed; basic conversion tested instead")
        answer = self.mod.convert_document(self.doc_blob, "docx", "lesson.docx")
        self.assertEqual(answer.backend, "libreoffice")
        self.assertTrue(answer.pdf.getvalue().startswith(b"%PDF-"))

    def test_real_libreoffice_pptx_when_available(self):
        executable = self.mod._libreoffice_executable()
        if not executable:
            self.skipTest("LibreOffice not installed; basic conversion tested instead")
        answer = self.mod.convert_document(self.ppt_blob, "pptx", "lesson.pptx")
        self.assertEqual(len(PdfReader(answer.pdf).pages), 2)

    def test_wrong_extension_rejected(self):
        self.bot.dispatch(self.mod.DOCX_BUTTON)
        self.bot.dispatch(kind="document", filename="file.pdf", blob=self.doc_blob)
        self.assertFalse(self.bot.documents)
        self.assertIn(".DOCX", self.bot.messages[-1][1])
        self.assertEqual(self.state[101]["mode"], "office_pdf_docx")

    def test_too_big_rejected_before_download(self):
        self.bot.dispatch("/pptxpdf")
        self.bot.dispatch(kind="document", filename="file.pptx", size=13 * 1024 * 1024)
        self.assertIn("maximum 12 MB", self.bot.messages[-1][1])
        self.assertFalse(self.bot.documents)

    def test_private_only(self):
        self.bot.dispatch("/docxpdf", chat_type="group")
        self.assertNotIn(101, self.state)
        self.assertIn("private chat", self.bot.messages[-1][1])

    def test_no_access_to_other_user_state(self):
        self.bot.dispatch("/docxpdf", user=101)
        self.bot.dispatch("/pptxpdf", user=202)
        self.assertEqual(self.state[101]["mode"], "office_pdf_docx")
        self.assertEqual(self.state[202]["mode"], "office_pdf_pptx")

    def test_bot_docx_workflow_uses_single_file(self):
        self.bot.dispatch("/docxpdf")
        with patch.object(self.mod, "_libreoffice_executable", return_value=None):
            self.bot.dispatch(kind="document", filename="Class Notes.docx", blob=self.doc_blob)
        self.assertEqual(len(self.bot.documents), 1)
        self.assertEqual(self.state[101]["mode"], "menu")
        self.assertIn("Basic PDF", self.bot.documents[0][2]["caption"])

    def test_bot_pptx_workflow(self):
        self.bot.dispatch(self.mod.PPTX_BUTTON)
        with patch.object(self.mod, "_libreoffice_executable", return_value=None):
            self.bot.dispatch(kind="document", filename="Slides.pptx", blob=self.ppt_blob)
        self.assertEqual(len(self.bot.documents), 1)

    def test_cancel(self):
        self.bot.dispatch("/docxpdf")
        self.bot.dispatch("❌ Cancel")
        self.assertEqual(self.state[101]["mode"], "menu")

    def test_wrong_file_doesnt_affect_another_pdf_mode(self):
        self.state[101] = {"mode": "merge"}
        self.bot.dispatch(kind="document", filename="file.docx", blob=self.doc_blob)
        self.assertEqual(self.state[101]["mode"], "merge")
        self.assertFalse(self.bot.documents)

    def test_damaged_zip_rejected(self):
        with self.assertRaises(self.mod.OfficePdfError):
            self.mod.convert_document(b"noofficefile", "docx")

    def test_mislabelled_docx_pptx_rejected(self):
        with self.assertRaises(self.mod.OfficePdfError):
            self.mod.convert_document(self.doc_blob, "pptx")

    def test_large_zip_expansion_rejected(self):
        blob = BytesIO()
        with ZipFile(blob, "w", ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", "some xml")
            z.writestr("word/document.xml", "A" * (self.mod.MAX_UNCOMPRESSED_BYTES + 1))
        with self.assertRaisesRegex(self.mod.OfficePdfError, "uncompressed"):
            self.mod.convert_document(blob.getvalue(), "docx")

    def test_macro_file_rejected(self):
        blob = BytesIO()
        with ZipFile(blob, "w") as z:
            z.writestr("[Content_Types].xml", "<types/>")
            z.writestr("word/document.xml", "<document/>")
            z.writestr("word/vbaProject.bin", "macro")
        with self.assertRaisesRegex(self.mod.OfficePdfError, "Macro"):
            self.mod.convert_document(blob.getvalue(), "docx")

    def test_invalid_filename_sanitized(self):
        self.assertEqual(self.mod._safe_filename("../private/My Lesson.docx", "docx"),
                         "My_Lesson_converted.pdf")

    def test_conversion_error_not_leaking_private_details(self):
        self.bot.dispatch("/docxpdf")
        self.bot.dispatch(kind="document", filename="bad.docx", blob=b"bad")
        self.assertIn("valid", self.bot.messages[-1][1])

    def test_limit_12mb(self):
        with self.assertRaisesRegex(self.mod.OfficePdfError, "12 MB"):
            self.mod._validate_office_document(b"a" * (self.mod.MAX_INPUT_BYTES + 1), "docx")

    def test_command_and_button_registration(self):
        command_sets = [handlers[0] for handlers in self.bot.handlers if handlers[0]]
        self.assertIn(["docxpdf", "pptxpdf"], command_sets)
        self.assertIn("document", [c for _, _, cs, _ in self.bot.handlers for c in cs])


if __name__ == "__main__":
    unittest.main()
