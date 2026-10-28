"""Offline regression tests for V7.15 standalone Photo/Image Crop."""
import io
from pathlib import Path
import sys
import types
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from photo_crop_v715 import (
    PHOTO_CROP_BUTTON, PHOTO_CROP_MODE, SAVE_CROP_BUTTON, CHANGE_PHOTO_BUTTON,
    PREVIEW_CROP_BUTTON, CUSTOM_CROP_BUTTON, CANCEL_CROP_BUTTON,
    AUTO_PAGE_BUTTON, ORIGINAL_BUTTON, PRESETS, MAX_SOURCE_BYTES,
    PhotoCropError, create_cropped_image, crop_image, parse_custom_edges, read_image,
)


def sample(width=400, height=300, fmt="JPEG", alpha=False):
    color = (255, 0, 0, 160) if alpha else (255, 0, 0)
    image = Image.new("RGBA" if alpha else "RGB", (width, height), color)
    out = io.BytesIO()
    image.save(out, format=fmt)
    image.close()
    return out.getvalue()


class CropMathTests(unittest.TestCase):
    def test_all_aspect_ratios(self):
        with Image.new("RGB", (1600, 1100), "white") as original:
            for name, (a, b) in PRESETS.items():
                with self.subTest(name=name), crop_image(original, name) as cropped:
                    self.assertAlmostEqual(cropped.width / cropped.height, a / b, delta=0.006)
            self.assertEqual(original.size, (1600, 1100))

    def test_original_keeps_dimensions(self):
        with Image.open(io.BytesIO(create_cropped_image(sample(), ORIGINAL_BUTTON).getvalue())) as im:
            self.assertEqual(im.size, (400, 300))

    def test_custom_percentages(self):
        coords = parse_custom_edges("10 5 90 95")
        with Image.open(io.BytesIO(create_cropped_image(sample(), CUSTOM_CROP_BUTTON, coords).getvalue())) as im:
            self.assertEqual(im.size, (320, 270))

    def test_custom_commas_supported(self):
        self.assertEqual(parse_custom_edges("10, 20, 80, 90"), (10., 20., 80., 90.))

    def test_invalid_custom_edges_rejected(self):
        for bad in ("", "10 20 40", "-1 0 60 80", "10 10 5 60", "1 1 2 2", "nan 0 100 100", "1e309 0 10 20", "a b c d"):
            with self.subTest(bad=bad), self.assertRaises(PhotoCropError):
                parse_custom_edges(bad)

    def test_too_narrow_custom_crop_rejected(self):
        with self.assertRaises(PhotoCropError):
            create_cropped_image(sample(100, 100), CUSTOM_CROP_BUTTON, (0, 0, 3, 3))

    def test_square_vertical_photo(self):
        with Image.open(io.BytesIO(create_cropped_image(sample(200, 800), "⬜ Square 1:1").getvalue())) as im:
            self.assertEqual(im.size, (200, 200))

    def test_auto_crop_safe_fallback(self):
        raw = sample(300, 300)
        with Image.open(io.BytesIO(create_cropped_image(raw, AUTO_PAGE_BUTTON).getvalue())) as im:
            self.assertEqual(im.size, (300, 300))

    def test_transparent_png_stays_png(self):
        raw = sample(200, 160, "PNG", alpha=True)
        with Image.open(io.BytesIO(create_cropped_image(raw, "⬜ Square 1:1").getvalue())) as im:
            self.assertEqual(im.format, "PNG")
            self.assertEqual(im.mode, "RGBA")
            self.assertEqual(im.getpixel((0,0))[3], 160)

    def test_preview_is_small_jpeg(self):
        output = create_cropped_image(sample(1800, 1200), "⬜ Square 1:1", preview=True)
        self.assertEqual(output.name, "cropped_preview.jpg")
        with Image.open(output) as im:
            self.assertLessEqual(max(im.size), 960)
        output.close()

    def test_original_image_bytes_not_mutated(self):
        raw = sample()
        before = bytes(raw)
        result = create_cropped_image(raw, "⬜ Square 1:1")
        result.close()
        self.assertEqual(raw, before)

    def test_exif_orientation_applied_and_removed(self):
        im = Image.new("RGB", (120, 80), "white")
        exif = Image.Exif()
        exif[274] = 6
        out = io.BytesIO()
        im.save(out, "JPEG", exif=exif)
        im.close()
        with Image.open(io.BytesIO(create_cropped_image(out.getvalue(), ORIGINAL_BUTTON).getvalue())) as output:
            self.assertEqual(output.size, (80, 120))
            self.assertEqual(len(output.getexif()), 0)

    def test_invalid_bytes_and_formats_rejected(self):
        for data in (b"", b"not-an-image", b"z" * (MAX_SOURCE_BYTES + 1)):
            with self.subTest(data=data[:5]), self.assertRaises(PhotoCropError):
                read_image(data)

    def test_pixel_limit_rejected(self):
        im = Image.new("RGB", (5000, 5000), "white")
        out = io.BytesIO()
        im.save(out, "PNG")
        im.close()
        with self.assertRaises(PhotoCropError):
            read_image(out.getvalue())

    def test_no_external_network_or_data_storage(self):
        import inspect, photo_crop_v715
        source = inspect.getsource(photo_crop_v715)
        for needle in ("requests.", "urllib.request", "supabase.", "bot.send_message"):
            self.assertNotIn(needle, source)


class ContinueHandling:
    pass


class DummyMarkup:
    def __init__(self, *args, **kwargs):
        self.rows = []
    def add(self, *items):
        self.rows.append(list(items))
    def row(self, *items):
        self.rows.append(list(items))


class DummyKeyboard:
    def __init__(self, value):
        self.text = value


class FakeMessage:
    def __init__(self, user=100, kind="text", value="", chat_type="private", file_name=None, file_size=100):
        self.chat = types.SimpleNamespace(id=user, type=chat_type)
        self.from_user = types.SimpleNamespace(first_name="Student", id=user)
        self.text = value if kind == "text" else None
        self.content_type = kind
        self.photo = [types.SimpleNamespace(file_id=value, file_size=file_size)] if kind == "photo" else None
        self.document = types.SimpleNamespace(file_id=value, file_size=file_size, file_name=file_name) if kind == "document" else None


class FakeBot:
    def __init__(self, files=None):
        self.handlers = []
        self.texts = []
        self.photos = []
        self.documents = []
        self.files = files or {}
    def message_handler(self, **kwargs):
        def deco(fn):
            self.handlers.append((kwargs, fn))
            return fn
        return deco
    def send_message(self, chat_id, text, **kwargs):
        self.texts.append((chat_id, text, kwargs))
        return types.SimpleNamespace(message_id=len(self.texts))
    def send_photo(self, chat_id, payload, **kwargs):
        self.photos.append((chat_id, bytes(payload.getvalue()), kwargs))
    def send_document(self, chat_id, payload, **kwargs):
        self.documents.append((chat_id, payload.name, bytes(payload.getvalue()), kwargs))
    def get_file(self, file_id):
        return types.SimpleNamespace(file_path=file_id)
    def download_file(self, path):
        return self.files[path]
    def dispatch(self, message):
        for cfg, fn in self.handlers:
            kinds = cfg.get("content_types", ["text"])
            if message.content_type not in kinds:
                continue
            if "commands" in cfg:
                if not message.text or message.text.split()[0].split("@",1)[0].lstrip("/") not in cfg["commands"]:
                    continue
            if "func" in cfg and not cfg["func"](message):
                continue
            result = fn(message)
            if not isinstance(result, ContinueHandling):
                return


class BotWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Test a real installed PDF Tools module with lightweight Telegram stubs.
        if 'telebot' not in sys.modules:
            try:
                import telebot  # noqa
            except ImportError:
                telebot_mod = types.ModuleType('telebot')
                telebot_types = types.ModuleType('telebot.types')
                telebot_backends = types.ModuleType('telebot.handler_backends')
                telebot_types.ReplyKeyboardMarkup = DummyMarkup
                telebot_types.KeyboardButton = DummyKeyboard
                telebot_backends.ContinueHandling = ContinueHandling
                telebot_mod.types = telebot_types
                sys.modules['telebot'] = telebot_mod
                sys.modules['telebot.types'] = telebot_types
                sys.modules['telebot.handler_backends'] = telebot_backends
        if 'PyPDF2' not in sys.modules:
            try:
                import PyPDF2  # noqa
            except ImportError:
                pypdf = types.ModuleType('PyPDF2')
                pypdf.PdfReader = object
                pypdf.PdfWriter = object
                sys.modules['PyPDF2'] = pypdf
        if 'navigation' not in sys.modules:
            nav = types.ModuleType('navigation')
            nav.should_yield_to_navigation = lambda t: bool(t and (t.startswith('/') or t in ('🏠 Main Menu','📄 PDF Tools')))
            sys.modules['navigation'] = nav
        if 'text_pdf_v711' not in sys.modules:
            t = types.ModuleType('text_pdf_v711')
            t.create_text_pdf = lambda t: None
            t.TextPdfError = ValueError
            t.MAX_TEXT_CHARS = 100000
            t.MAX_TEXT_MESSAGES = 50
            t.PDF_TEXT_MODE = 'text_pdf_v711'
            t.PDF_TEXT_BUTTON = '📝 Text → PDF'
            t.PDF_TEXT_CREATE = '✅ Create Text PDF'
            t.PDF_TEXT_CLEAR = '🧹 Clear Text'
            sys.modules['text_pdf_v711'] = t
        import pdf_tools
        cls.pdf = pdf_tools

    def setUp(self):
        self.pdf.pdf_state.clear()
        self.bot = FakeBot({"a": sample(800, 600), "b": sample(600, 400), "png": sample(400, 300, "PNG")})
        self.pdf.register_pdf_handlers(self.bot, lambda chat, user: self.bot.send_message(chat, "MAIN MENU"))

    def test_command_starts_private_mode(self):
        self.bot.dispatch(FakeMessage(value='/cropimage'))
        self.assertEqual(self.pdf.pdf_state[100]['mode'], PHOTO_CROP_MODE)
        self.assertIn('Photo/Image Crop', self.bot.texts[-1][1])

    def test_group_blocked(self):
        self.bot.dispatch(FakeMessage(value='/cropimage',chat_type='group'))
        self.assertNotIn(100,self.pdf.pdf_state)

    def test_menu_button_exists(self):
        self.bot.dispatch(FakeMessage(value='📄 PDF Tools'))
        keyboard = self.bot.texts[-1][2]['reply_markup']
        all_buttons = [b.get("text") if isinstance(b, dict) else b.text
                       for row in getattr(keyboard, "keyboard",getattr(keyboard, "rows", []))
                       for b in row]
        self.assertIn(PHOTO_CROP_BUTTON, all_buttons)

    def test_crop_photo_and_send_download(self):
        self.bot.dispatch(FakeMessage(value='/cropimage'))
        self.bot.dispatch(FakeMessage(kind='photo', value='a'))
        self.bot.dispatch(FakeMessage(value='⬜ Square 1:1'))
        self.assertEqual(len(self.bot.photos), 1)
        self.bot.dispatch(FakeMessage(value=SAVE_CROP_BUTTON))
        self.assertEqual(len(self.bot.documents), 1)
        _, name, payload, _ = self.bot.documents[0]
        self.assertEqual(name, 'cropped_photo.jpg')
        with Image.open(io.BytesIO(payload)) as image:
            self.assertEqual(image.size, (600, 600))
        self.assertEqual(self.pdf.pdf_state[100]['mode'], 'menu')

    def test_custom_crop_flow(self):
        self.bot.dispatch(FakeMessage(value='/cropimage'))
        self.bot.dispatch(FakeMessage(kind='document',value='png',file_name='my_photo.png'))
        self.bot.dispatch(FakeMessage(value=CUSTOM_CROP_BUTTON))
        self.bot.dispatch(FakeMessage(value='10 10 90 90'))
        self.assertEqual(self.pdf.pdf_state[100]['selection'], CUSTOM_CROP_BUTTON)
        self.bot.dispatch(FakeMessage(value=SAVE_CROP_BUTTON))
        self.assertEqual(len(self.bot.documents), 1)
        _, name, payload, _ = self.bot.documents[0]
        self.assertEqual(name, 'cropped_photo.png')
        with Image.open(io.BytesIO(payload)) as image:
            self.assertEqual(image.size, (320, 240))

    def test_reject_pdf_document_and_retain_previous(self):
        self.bot.dispatch(FakeMessage(value='/cropimage'))
        self.bot.dispatch(FakeMessage(kind='photo',value='a'))
        self.bot.dispatch(FakeMessage(kind='document',value='b',file_name='bad.pdf'))
        self.assertEqual(self.pdf.pdf_state[100]['image'], self.bot.files['a'])
        self.assertEqual(len(self.bot.documents), 0)

    def test_change_photo_and_cancel(self):
        self.bot.dispatch(FakeMessage(value='/cropimage'))
        self.bot.dispatch(FakeMessage(kind='photo',value='a'))
        self.bot.dispatch(FakeMessage(value=CHANGE_PHOTO_BUTTON))
        self.assertIsNone(self.pdf.pdf_state[100]['image'])
        self.bot.dispatch(FakeMessage(value=CANCEL_CROP_BUTTON))
        self.assertEqual(self.pdf.pdf_state[100]['mode'], 'menu')

    def test_user_state_is_separate(self):
        self.bot.dispatch(FakeMessage(user=100,value='/cropimage'))
        self.bot.dispatch(FakeMessage(user=200,value='/cropimage'))
        self.bot.dispatch(FakeMessage(user=100,kind='photo',value='a'))
        self.assertIsNotNone(self.pdf.pdf_state[100]['image'])
        self.assertIsNone(self.pdf.pdf_state[200]['image'])

    def test_other_pdf_mode_not_hijacked(self):
        self.bot.dispatch(FakeMessage(value='🖼 Images → PDF'))
        self.bot.dispatch(FakeMessage(kind='photo', value='a'))
        self.assertEqual(len(self.pdf.pdf_state[100]['images']), 1)
        self.assertEqual(len(self.bot.documents), 0)

    def test_global_command_yields(self):
        self.bot.dispatch(FakeMessage(value='/cropimage'))
        self.bot.dispatch(FakeMessage(value='/help'))
        self.assertNotIn(100,self.pdf.pdf_state)

    def test_photo_oversize_rejected_without_download(self):
        self.bot.dispatch(FakeMessage(value='/cropimage'))
        self.bot.dispatch(FakeMessage(kind='photo',value='a',file_size=MAX_SOURCE_BYTES + 1))
        self.assertIsNone(self.pdf.pdf_state[100]['image'])

    def test_no_photo_save_rejected(self):
        self.bot.dispatch(FakeMessage(value='/cropimage'))
        self.bot.dispatch(FakeMessage(value=SAVE_CROP_BUTTON))
        self.assertEqual(len(self.bot.documents),0)

    def test_preview_only_does_not_send_final_file(self):
        self.bot.dispatch(FakeMessage(value='/cropimage'))
        self.bot.dispatch(FakeMessage(kind='photo',value='a'))
        self.bot.dispatch(FakeMessage(value=PREVIEW_CROP_BUTTON))
        self.assertEqual(len(self.bot.photos),1)
        self.assertEqual(len(self.bot.documents),0)


if __name__ == '__main__':
    unittest.main()
