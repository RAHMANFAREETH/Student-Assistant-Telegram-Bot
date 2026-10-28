"""Offline V7.13 regressions; no Telegram API, Supabase or network calls.

Run: python -m unittest TEST_V7_13_IMAGE_FILTERS.py -v
"""
from __future__ import annotations

from io import BytesIO
import sys
import types as pytypes
import unittest

from PIL import Image

import image_filters_v713 as filters


def image_bytes(mode="RGB", fmt="PNG", color=(160, 80, 60), size=(140, 90)):
    img = Image.new(mode, size, color if mode == "RGB" else 100)
    stream = BytesIO()
    img.save(stream, fmt)
    img.close()
    return stream.getvalue()


class FilterEngineTests(unittest.TestCase):
    def test_all_filter_codes_have_labels(self):
        self.assertEqual(len(filters.FILTER_LABELS), 8)
        self.assertEqual(len(set(filters.FILTER_LABELS.values())), 8)

    def test_default_original(self):
        self.assertEqual(filters.selected_filter({}), "original")
        self.assertEqual(filters.selected_filter({"image_filter": "unknown"}), "original")

    def test_supported_filters_keep_valid_rgb(self):
        with Image.open(BytesIO(image_bytes())) as img:
            for name, code in filters.FILTER_LABELS.items():
                with self.subTest(name=name):
                    result = filters.filter_image(img, code)
                    try:
                        self.assertEqual(result.mode, "RGB")
                        self.assertEqual(result.size, img.size)
                    finally:
                        result.close()

    def test_gray_b_and_w_make_monochrome_pixels(self):
        with Image.open(BytesIO(image_bytes())) as img:
            for code in ("gray", "bw", "scan"):
                result = filters.filter_image(img, code)
                self.assertEqual(len(set(result.getpixel((20, 20)))), 1)
                result.close()

    def test_shadow_does_not_become_black_block(self):
        """Uneven lighting on a notebook must not swallow a page."""
        from PIL import ImageDraw
        original = Image.new("RGB", (360, 420), (208, 207, 202))
        draw = ImageDraw.Draw(original)
        draw.rectangle((45, 65, 310, 380), fill=(72, 69, 66))
        draw.line((100, 130, 260, 130), fill=(18, 17, 18), width=4)
        bw = filters.filter_image(original, "bw")
        try:
            core = bw.crop((125, 180, 225, 300)).convert("L")
            try:
                hist = core.histogram()
                dark_fraction = sum(hist[:100]) / (core.width * core.height)
                self.assertLess(dark_fraction, .12)
            finally:
                core.close()
        finally:
            original.close()
            bw.close()

    def test_scan_is_not_binary_or_all_white(self):
        original = Image.new("RGB", (250, 250), (210, 210, 210))
        from PIL import ImageDraw
        ImageDraw.Draw(original).line((20, 50, 230, 50), fill=(35, 35, 35), width=3)
        scan = filters.filter_image(original, "scan")
        try:
            self.assertLess(scan.getpixel((125, 50))[0], 200)
            self.assertGreater(scan.getpixel((120, 120))[0], 150)
        finally:
            original.close()
            scan.close()

    def test_filter_does_not_modify_original(self):
        with Image.open(BytesIO(image_bytes())) as img:
            before = img.getpixel((10, 10))
            filtered = filters.filter_image(img, "bw")
            self.assertEqual(img.getpixel((10, 10)), before)
            filtered.close()

    def test_alpha_is_flattened_on_white(self):
        rgba = Image.new("RGBA", (20, 10), (0, 0, 0, 0))
        out = BytesIO()
        rgba.save(out, "PNG")
        rgba.close()
        image = filters._read_image(out.getvalue())
        try:
            self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))
        finally:
            image.close()

    def test_queue_validates_before_adding(self):
        state = {"images": []}
        self.assertEqual(filters.enqueue_image(state, image_bytes()), 1)
        with self.assertRaises(filters.ImageFilterError):
            filters.enqueue_image(state, b"not an image")
        self.assertEqual(len(state["images"]), 1)

    def test_queue_enforces_15_images(self):
        state = {"images": []}
        data = image_bytes()
        for i in range(filters.MAX_IMAGES):
            self.assertEqual(filters.enqueue_image(state, data), i + 1)
        with self.assertRaises(filters.ImageFilterError):
            filters.enqueue_image(state, data)

    def test_queue_rejects_oversized_files(self):
        with self.assertRaisesRegex(filters.ImageFilterError, "size"):
            filters.enqueue_image({}, b"a" * (filters.MAX_IMAGE_BYTES + 1))

    def test_queue_rejects_oversized_resolutions(self):
        with self.assertRaisesRegex(filters.ImageFilterError, "resolution"):
            filters.enqueue_image({}, image_bytes(size=(5000, 5000)))

    def test_preview_is_jpeg(self):
        result = filters.make_preview(image_bytes(), "contrast")
        try:
            with Image.open(result) as img:
                self.assertEqual(img.format, "JPEG")
                self.assertLessEqual(max(img.size), 900)
        finally:
            result.close()

    def test_pdf_has_one_page_per_image(self):
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader
        contents = [image_bytes(color=(c, 100, 70)) for c in (40, 80, 120)]
        for code in ("original", "scan", "bw", "auto"):
            with self.subTest(code=code):
                out = filters.images_to_pdf(contents, code)
                try:
                    self.assertEqual(len(PdfReader(out).pages), 3)
                    self.assertGreater(len(out.getvalue()), 500)
                finally:
                    out.close()

    def test_missing_images_rejected(self):
        with self.assertRaises(filters.ImageFilterError):
            filters.images_to_pdf([])

    def test_unknown_filter_rejected(self):
        with self.assertRaises(filters.ImageFilterError):
            filters.images_to_pdf([image_bytes()], "not-a-filter")

    def test_generated_pdf_does_not_call_api(self):
        self.assertGreater(len(filters.images_to_pdf([image_bytes()], "scan").getvalue()), 100)


class KeyboardButton:
    def __init__(self, text):
        self.text = text


class ReplyKeyboardMarkup:
    def __init__(self, **kw):
        self.rows = []
    def add(self, *buttons):
        self.rows.append(buttons)
    def row(self, *buttons):
        self.rows.append(buttons)


class FakeBot:
    def __init__(self):
        self.handlers = []
        self.sent = []
        self.documents = []
        self.photos = []
        self.store = {}

    def message_handler(self, **options):
        def decorator(fn):
            self.handlers.append((options, fn))
            return fn
        return decorator

    def dispatch(self, message):
        for options, fn in self.handlers:
            if options.get("content_types") and message.content_type not in options["content_types"]:
                continue
            if not options.get("content_types") and message.content_type != "text":
                continue
            if "commands" in options:
                if not message.text or message.text.split()[0].lstrip("/") not in options["commands"]:
                    continue
            elif "func" in options and not options["func"](message):
                continue
            fn(message)
            return fn.__name__
        return None

    def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text, kwargs))
        return pytypes.SimpleNamespace(message_id=len(self.sent))

    def send_photo(self, chat_id, contents, **kwargs):
        self.photos.append((chat_id, contents.getvalue(), kwargs))

    def send_document(self, chat_id, contents, **kwargs):
        self.documents.append((chat_id, contents.getvalue(), kwargs))

    def send_chat_action(self, *args, **kwargs):
        pass

    def get_file(self, file_id):
        return pytypes.SimpleNamespace(file_path=file_id)

    def download_file(self, file_path):
        return self.store[file_path]

    def delete_message(self, *args):
        pass


def message(text=None, *, chat_id=100, content_type="text", photo=None, document=None):
    return pytypes.SimpleNamespace(
        text=text, chat=pytypes.SimpleNamespace(id=chat_id, type="private"),
        from_user=pytypes.SimpleNamespace(first_name="Student", id=chat_id),
        content_type=content_type,
        photo=photo or [], document=document,
    )


class TelegramFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Stub only external integrations; the actual pdf_tools handlers execute.
        telebot = pytypes.ModuleType("telebot")
        telebot.types = pytypes.SimpleNamespace(
            ReplyKeyboardMarkup=ReplyKeyboardMarkup, KeyboardButton=KeyboardButton,
        )
        backend = pytypes.ModuleType("telebot.handler_backends")
        backend.ContinueHandling = lambda: "continue"
        nav = pytypes.ModuleType("navigation")
        nav.should_yield_to_navigation = lambda val: False
        text_pdf = pytypes.ModuleType("text_pdf_v711")
        for name, val in {
            "create_text_pdf": lambda x: BytesIO(), "TextPdfError": ValueError,
            "MAX_TEXT_CHARS": 50000, "MAX_TEXT_MESSAGES": 50,
            "PDF_TEXT_MODE": "text", "PDF_TEXT_BUTTON": "📝 Text → PDF",
            "PDF_TEXT_CREATE": "✅ Create Text PDF", "PDF_TEXT_CLEAR": "🧹 Clear Text",
        }.items():
            setattr(text_pdf, name, val)
        try:
            import PyPDF2 as legacy_pdf
        except ImportError:
            import pypdf as legacy_pdf
        cls._old = {n: sys.modules.get(n) for n in
                    ("telebot", "telebot.handler_backends", "navigation", "text_pdf_v711", "pdf_tools", "PyPDF2")}
        sys.modules.update({
            "telebot": telebot, "telebot.handler_backends": backend,
            "navigation": nav, "text_pdf_v711": text_pdf, "PyPDF2": legacy_pdf,
        })
        import pdf_tools
        cls.pdf_tools = pdf_tools

    @classmethod
    def tearDownClass(cls):
        for name, mod in cls._old.items():
            if mod is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod

    def setUp(self):
        self.bot = FakeBot()
        self.pdf_tools.pdf_state.clear()
        self.pdf_tools.register_pdf_handlers(self.bot, lambda *args: None)
        self.bot.store["p1"] = image_bytes()
        self.bot.store["p2"] = image_bytes(color=(20, 120, 220))

    def open_mode(self):
        self.bot.dispatch(message("🖼 Images → PDF"))

    def add_photo(self, name="p1"):
        photo = pytypes.SimpleNamespace(file_id=name, file_size=len(self.bot.store[name]))
        return self.bot.dispatch(message(chat_id=100, content_type="photo", photo=[photo]))

    def test_menu_offers_filters_and_preview(self):
        self.open_mode()
        self.assertEqual(self.pdf_tools.pdf_state[100]["image_filter"], "original")
        rows = self.bot.sent[-1][2]["reply_markup"].rows
        labels = [b.text for row in rows for b in row]
        self.assertIn(filters.FILTER_BUTTON, labels)
        self.assertIn(filters.PREVIEW_BUTTON, labels)

    def test_select_filter_and_make_document(self):
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader
        self.open_mode()
        self.add_photo()
        self.add_photo("p2")
        self.bot.dispatch(message(filters.FILTER_BUTTON))
        self.bot.dispatch(message("📄 Clean Scan"))
        self.assertEqual(self.pdf_tools.pdf_state[100]["image_filter"], "scan")
        self.bot.dispatch(message("✅ Create PDF"))
        self.assertEqual(len(self.bot.documents), 1)
        self.assertEqual(len(PdfReader(BytesIO(self.bot.documents[0][1])).pages), 2)
        self.assertIn("Clean Scan", self.bot.documents[0][2]["caption"])

    def test_preview_does_not_remove_or_change_images(self):
        self.open_mode()
        self.add_photo()
        before = self.pdf_tools.pdf_state[100]["images"][0]
        self.bot.dispatch(message(filters.FILTER_BUTTON))
        self.bot.dispatch(message("⚫ Black & White"))
        self.bot.dispatch(message(filters.PREVIEW_BUTTON))
        self.assertEqual(len(self.bot.photos), 1)
        self.assertEqual(self.pdf_tools.pdf_state[100]["images"][0], before)

    def test_remove_last_and_empty_creation(self):
        self.open_mode()
        self.add_photo()
        self.bot.dispatch(message(filters.REMOVE_BUTTON))
        self.assertEqual(self.pdf_tools.pdf_state[100]["images"], [])
        self.bot.dispatch(message("✅ Create PDF"))
        self.assertEqual(len(self.bot.documents), 0)

    def test_two_users_have_separate_filters(self):
        self.open_mode()
        self.bot.dispatch(message("🖼 Images → PDF", chat_id=200))
        self.bot.dispatch(message(filters.FILTER_BUTTON))
        self.bot.dispatch(message("⚪ Grayscale"))
        self.assertEqual(self.pdf_tools.pdf_state[100]["image_filter"], "gray")
        self.assertEqual(self.pdf_tools.pdf_state[200]["image_filter"], "original")

    def test_photo_mode_does_not_intercept_unrelated_photos(self):
        self.assertIsNone(self.add_photo())
        self.assertEqual(self.pdf_tools.pdf_state, {})

    def test_pdf_menu_has_legacy_modes(self):
        self.bot.dispatch(message("📄 PDF Tools"))
        label = self.bot.sent[-1][1]
        for mode in ("Merge PDFs", "Extract Pages", "Images → PDF",
                     "Text → PDF", "Rotate PDF", "Protect PDF"):
            self.assertIn(mode, label)

    def test_invalid_uploaded_photo_does_not_create_pdf(self):
        self.open_mode()
        self.bot.store["bad"] = b"not a photo"
        self.add_photo("bad")
        self.assertEqual(self.pdf_tools.pdf_state[100]["images"], [])

    def test_doc_image_mode_with_filter(self):
        self.open_mode()
        doc = pytypes.SimpleNamespace(file_name="lesson.png", file_id="p1",
                                      file_size=len(self.bot.store["p1"]))
        self.bot.dispatch(message(content_type="document", document=doc))
        self.assertEqual(len(self.pdf_tools.pdf_state[100]["images"]), 1)


if __name__ == "__main__":
    unittest.main()
