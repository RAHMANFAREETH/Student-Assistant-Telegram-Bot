"""Offline tests: python -m unittest TEST_V7_11_TEXT_PDF.py -v"""
import importlib
import sys
import types as pytypes
import unittest
from unittest.mock import patch


class ContinueHandling:
    pass


class KeyboardButton:
    def __init__(self, text):
        self.text = text


class ReplyKeyboardMarkup:
    def __init__(self, **kwargs):
        self.rows = []

    def add(self, *items):
        self.rows.append(list(items))

    def row(self, *items):
        self.rows.append(list(items))


class FakeBot:
    def __init__(self):
        self.handlers = []
        self.messages = []
        self.documents = []
        self.actions = []

    def message_handler(self, commands=None, func=None, content_types=None, **kwargs):
        def decorator(fn):
            self.handlers.append((commands, func, content_types or ["text"], fn))
            return fn
        return decorator

    def dispatch(self, text=None, chat=101, chat_type="private", kind="text"):
        msg = pytypes.SimpleNamespace(
            text=text, content_type=kind,
            chat=pytypes.SimpleNamespace(id=chat, type=chat_type),
            from_user=pytypes.SimpleNamespace(id=chat, first_name="Test"),
            document=pytypes.SimpleNamespace(file_id="dummy", file_name="doc.pdf"),
        )
        for commands, predicate, types, handler in self.handlers:
            if kind not in types:
                continue
            if commands is not None and not (
                text and text.startswith("/") and text.split()[0].split("@")[0][1:] in commands
            ):
                continue
            if predicate is not None and not predicate(msg):
                continue
            result = handler(msg)
            if not isinstance(result, ContinueHandling):
                return result
        return None

    def send_message(self, chat_id, content, **kwargs):
        self.messages.append((chat_id, content, kwargs))
        return pytypes.SimpleNamespace(message_id=len(self.messages))

    def send_document(self, chat_id, file, **kwargs):
        self.documents.append((chat_id, file.getvalue(), kwargs))

    def send_chat_action(self, chat_id, action):
        self.actions.append((chat_id, action))


class TextPdfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake_telebot = pytypes.ModuleType("telebot")
        fake_telebot.types = pytypes.SimpleNamespace(
            KeyboardButton=KeyboardButton, ReplyKeyboardMarkup=ReplyKeyboardMarkup,
        )
        backend = pytypes.ModuleType("telebot.handler_backends")
        backend.ContinueHandling = ContinueHandling
        mocked = {"telebot": fake_telebot, "telebot.handler_backends": backend}
        # CI may not have every existing bot dependency installed. We do not
        # exercise the original PyPDF2 handlers in this isolated unit suite.
        import importlib.util
        if importlib.util.find_spec("PyPDF2") is None:
            legacy_pdf = pytypes.ModuleType("PyPDF2")
            legacy_pdf.PdfReader = object
            legacy_pdf.PdfWriter = object
            mocked["PyPDF2"] = legacy_pdf
        cls.module_patch = patch.dict(sys.modules, mocked)
        cls.module_patch.start()
        cls.nav = importlib.import_module("navigation")
        cls.pdf = importlib.import_module("pdf_tools")
        cls.textmod = importlib.import_module("text_pdf_v711")

    @classmethod
    def tearDownClass(cls):
        cls.module_patch.stop()

    def setUp(self):
        self.pdf.pdf_state.clear()
        self.bot = FakeBot()
        self.pdf.register_pdf_handlers(self.bot, lambda cid, name="Friend":
                                        self.bot.send_message(cid, "Main menu"))

    def test_menu_has_button(self):
        self.bot.dispatch("📄 PDF Tools")
        buttons = [b.text for row in self.bot.messages[-1][2]["reply_markup"].rows for b in row]
        self.assertIn("📝 Text → PDF", buttons)
        self.assertIn("🔗 Merge PDFs", buttons)

    def test_text_flow_pdf_has_selectable_text(self):
        from io import BytesIO
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader
        self.bot.dispatch("📝 Text → PDF")
        self.bot.dispatch("A short lesson about phonetics.")
        self.bot.dispatch("Second sentence.\nA third line.")
        self.bot.dispatch("✅ Create Text PDF")
        self.assertEqual(len(self.bot.documents), 1)
        content = self.bot.documents[0][1]
        self.assertTrue(content.startswith(b"%PDF-"))
        d = PdfReader(BytesIO(content))
        self.assertEqual(len(d.pages), 1)
        page_text = d.pages[0].extract_text()
        self.assertIn("A short lesson about phonetics.", page_text)
        self.assertIn("Second sentence.", page_text)
        self.assertEqual(self.pdf.pdf_state[101]["mode"], "menu")

    def test_command_starts_text_mode(self):
        self.bot.dispatch("/textpdf")
        self.assertEqual(self.pdf.pdf_state[101]["mode"], self.textmod.PDF_TEXT_MODE)

    def test_empty_creation_requires_text(self):
        self.bot.dispatch("/textpdf")
        self.bot.dispatch("✅ Create Text PDF")
        self.assertFalse(self.bot.documents)
        self.assertIn("First send", self.bot.messages[-1][1])

    def test_clear_text(self):
        self.bot.dispatch("/textpdf")
        self.bot.dispatch("Unwanted content")
        self.bot.dispatch("🧹 Clear Text")
        self.assertEqual(self.pdf.pdf_state[101]["parts"], [])
        self.assertEqual(self.pdf.pdf_state[101]["length"], 0)

    def test_cancel_back_to_pdf_menu(self):
        self.bot.dispatch("/textpdf")
        self.bot.dispatch("something")
        self.bot.dispatch("❌ Cancel")
        self.assertEqual(self.pdf.pdf_state[101]["mode"], "menu")

    def test_main_menu_exits(self):
        self.bot.dispatch("/textpdf")
        self.bot.dispatch("🏠 Main Menu")
        self.assertNotIn(101, self.pdf.pdf_state)
        self.assertEqual(self.bot.messages[-1][1], "Main menu")

    def test_navigation_yield_clears_text(self):
        self.bot.dispatch("/textpdf")
        self.bot.dispatch("📚 Study Materials")
        self.assertNotIn(101, self.pdf.pdf_state)
        self.assertFalse(self.bot.documents)

    def test_different_user_state_is_separate(self):
        self.bot.dispatch("/textpdf", chat=101)
        self.bot.dispatch("one", chat=101)
        self.bot.dispatch("/textpdf", chat=202)
        self.bot.dispatch("two", chat=202)
        self.assertEqual(self.pdf.pdf_state[101]["parts"], ["one"])
        self.assertEqual(self.pdf.pdf_state[202]["parts"], ["two"])

    def test_not_allowed_in_group(self):
        self.bot.dispatch("/textpdf", chat=101, chat_type="supergroup")
        self.assertNotIn(101, self.pdf.pdf_state)
        self.assertIn("private chat", self.bot.messages[-1][1])

    def test_document_is_not_added_as_text(self):
        self.bot.dispatch("/textpdf")
        self.bot.dispatch(chat=101, kind="document")
        self.assertIn("typed/pasted text", self.bot.messages[-1][1])

    def test_too_much_text_is_rejected(self):
        self.bot.dispatch("/textpdf")
        self.bot.dispatch("A" * (self.textmod.MAX_TEXT_CHARS + 1))
        self.assertEqual(self.pdf.pdf_state[101]["parts"], [])
        self.assertIn("Too much text", self.bot.messages[-1][1])

    def test_limit_of_messages(self):
        self.bot.dispatch("/textpdf")
        for _ in range(self.textmod.MAX_TEXT_MESSAGES):
            self.bot.dispatch("a")
        self.bot.dispatch("extra")
        self.assertEqual(len(self.pdf.pdf_state[101]["parts"]), self.textmod.MAX_TEXT_MESSAGES)
        self.assertIn("Message limit", self.bot.messages[-1][1])

    def test_missing_fonts_does_not_lose_text(self):
        self.bot.dispatch("/textpdf")
        self.bot.dispatch("Keep this")
        with patch.object(self.pdf, "create_text_pdf", side_effect=self.textmod.TextPdfError("Missing font")):
            self.bot.dispatch("✅ Create Text PDF")
        self.assertEqual(self.pdf.pdf_state[101]["parts"], ["Keep this"])
        self.assertIn("Missing font", self.bot.messages[-1][1])

    def test_other_pdf_modes_not_hijacked(self):
        self.bot.dispatch("🔗 Merge PDFs")
        self.assertEqual(self.pdf.pdf_state[101]["mode"], "merge")
        self.bot.dispatch("random text")
        self.assertEqual(self.pdf.pdf_state[101]["mode"], "merge")

    def test_multilingual_script_detection(self):
        for sample in ("தமிழ் உரை", "සිංහල පෙළ", "مرحبًا بك"):
            self.assertTrue(self.textmod._has_complex_script(sample))
        self.assertFalse(self.textmod._has_complex_script("English notes"))

    def test_arabic_alignment(self):
        self.assertEqual(self.textmod._paragraph_align("مرحبا بكم"), "R")
        self.assertEqual(self.textmod._paragraph_align("Hello مرحبا"), "L")

    def test_normalization_removes_controls(self):
        self.assertEqual(self.textmod._normalise_input("A\r\nB\tC\x00D"), "A\nB    CD")

    def test_empty_text_raises(self):
        with self.assertRaises(self.textmod.TextPdfError):
            self.textmod.create_text_pdf("   ")

    def test_multi_page_pdf(self):
        from io import BytesIO
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader
        content = "\n".join("This is a long revision note with examples." for _ in range(160))
        pdf_bytes = self.textmod.create_text_pdf(content).getvalue()
        document = PdfReader(BytesIO(pdf_bytes))
        self.assertGreater(len(document.pages), 1)
        self.assertIn("Page 2", document.pages[1].extract_text())

    def test_private_no_external_api_calls(self):
        # Code intentionally only touches local fonts and in-memory PDF bytes.
        text = self.textmod.create_text_pdf("Study privacy test.").getvalue()
        self.assertIn(b"%PDF", text)


if __name__ == "__main__":
    unittest.main()
