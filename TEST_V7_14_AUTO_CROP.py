"""V7.14 regressions: Original default, opt-in Auto Crop, previews, PDF, rollback.
Run from project root: python -m unittest TEST_V7_14_AUTO_CROP.py -v
"""
from __future__ import annotations

from io import BytesIO
import unittest

from PIL import Image, ImageDraw

import image_crop_v714 as crop
import image_filters_v713 as filt


def paper_photo(*, desk=(67, 65, 65), size=(720, 900), paper=(80, 120, 640, 810)):
    im = Image.new("RGB", size, desk)
    draw = ImageDraw.Draw(im)
    draw.rectangle(paper, fill=(245, 246, 242))
    for y in (170, 205, 240, 275, 310):
        draw.line((105, y, 615, y), fill=(42, 49, 57), width=4)
    stream = BytesIO()
    im.save(stream, format="PNG")
    im.close()
    return stream.getvalue()


class AutoCropEngineTests(unittest.TestCase):
    def test_default_is_original(self):
        self.assertFalse(crop.selected_crop({}))
        self.assertFalse(crop.selected_crop({"image_autocrop": "true"}))
        self.assertTrue(crop.selected_crop({"image_autocrop": True}))
        self.assertEqual(filt.selected_filter({}), "original")

    def test_dark_background_paper_cropped(self):
        with Image.open(BytesIO(paper_photo())) as original:
            before = original.tobytes()
            out = crop.auto_crop_image(original)
            self.assertTrue(560 <= out.width < original.width)
            self.assertTrue(690 <= out.height < original.height)
            self.assertEqual(original.tobytes(), before)
            self.assertGreaterEqual(out.getpixel((out.width//2, out.height//2))[0], 235)
            out.close()

    def test_colored_background_paper_cropped(self):
        for color in ((175, 128, 80), (60, 112, 166)):
            with self.subTest(color=color), Image.open(BytesIO(paper_photo(desk=color))) as img:
                out = crop.auto_crop_image(img)
                self.assertLess(out.width, img.width)
                out.close()

    def test_already_cropped_white_image_unchanged(self):
        src = Image.new("RGB", (600, 830), (248, 248, 246))
        out = crop.auto_crop_image(src)
        self.assertEqual(out.size, src.size)
        out.close()
        src.close()

    def test_ambiguous_full_frame_kept(self):
        for color in ((80, 80, 80), (255, 255, 255), (220, 220, 220)):
            with self.subTest(color=color):
                src = Image.new("RGB", (500, 700), color)
                out = crop.auto_crop_image(src)
                self.assertEqual(out.size, src.size)
                out.close()
                src.close()

    def test_tiny_images_not_cropped(self):
        img = Image.new("RGB", (50, 60), "white")
        cropped = crop.auto_crop_image(img)
        self.assertEqual(cropped.size, img.size)
        cropped.close()
        img.close()

    def test_preview_auto_crop_changes_aspect_to_paper(self):
        data = paper_photo()
        original = filt.make_preview(data, "original")
        cropped = filt.make_preview(data, "original", auto_crop=True)
        with Image.open(original) as a, Image.open(cropped) as b:
            self.assertLess(b.width, a.width)
            self.assertLess(b.height, a.height)
        original.close()
        cropped.close()

    def test_preview_fallback_keeps_whole_photo(self):
        im = Image.new("RGB", (350, 500), (248, 248, 246))
        raw = BytesIO(); im.save(raw, "PNG"); im.close()
        out = filt.make_preview(raw.getvalue(), "original", auto_crop=True)
        with Image.open(out) as preview:
            self.assertEqual(preview.size, (350, 500))
        out.close()

    def test_pdf_original_and_cropped_distinct_page_shapes(self):
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader
        data = paper_photo()
        raw = filt.images_to_pdf([data], "original")
        cropped = filt.images_to_pdf([data], "original", auto_crop=True)
        try:
            orig_page = PdfReader(raw).pages[0]
            crop_page = PdfReader(cropped).pages[0]
            self.assertLess(float(crop_page.mediabox.width), float(orig_page.mediabox.width))
            self.assertLess(float(crop_page.mediabox.height), float(orig_page.mediabox.height))
        finally:
            raw.close(); cropped.close()

    def test_multiple_pages_and_filter_combination(self):
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader
        data = paper_photo()
        for name in ("original", "scan", "gray", "bw", "sharp"):
            with self.subTest(name=name):
                result = filt.images_to_pdf([data, data], name, auto_crop=True)
                self.assertEqual(len(PdfReader(result).pages), 2)
                result.close()

    def test_default_legacy_call_still_works(self):
        data = paper_photo()
        no_crop = filt.images_to_pdf([data], "original")
        explicit_no_crop = filt.images_to_pdf([data], "original", auto_crop=False)
        self.assertEqual(no_crop.getvalue(), explicit_no_crop.getvalue())
        no_crop.close();explicit_no_crop.close()


# Reuse the V7.13 stubs and real handler registration; requires V7.13 tests.
try:
    from TEST_V7_13_IMAGE_FILTERS import TelegramFlowTests as BaseFlow, message, image_bytes
except ImportError:
    BaseFlow = None

if BaseFlow:
    class CropTelegramFlowTests(BaseFlow):
        def test_original_default_and_crop_button(self):
            self.open_mode()
            state = self.pdf_tools.pdf_state[100]
            self.assertIs(state["image_autocrop"], False)
            rows = self.bot.sent[-1][2]["reply_markup"].rows
            labels = [b.text for row in rows for b in row]
            self.assertIn(crop.CROP_MENU_BUTTON, labels)

        def test_user_selects_auto_crop_and_original_again(self):
            self.open_mode()
            self.bot.dispatch(message(crop.CROP_MENU_BUTTON))
            self.bot.dispatch(message(crop.CROP_AUTO_BUTTON))
            self.assertTrue(crop.selected_crop(self.pdf_tools.pdf_state[100]))
            self.bot.dispatch(message(crop.CROP_MENU_BUTTON))
            self.bot.dispatch(message(crop.CROP_ORIGINAL_BUTTON))
            self.assertFalse(crop.selected_crop(self.pdf_tools.pdf_state[100]))

        def test_crop_selection_is_per_user(self):
            self.open_mode()
            self.bot.dispatch(message("🖼 Images → PDF", chat_id=200))
            self.bot.dispatch(message(crop.CROP_MENU_BUTTON))
            self.bot.dispatch(message(crop.CROP_AUTO_BUTTON))
            self.assertTrue(crop.selected_crop(self.pdf_tools.pdf_state[100]))
            self.assertFalse(crop.selected_crop(self.pdf_tools.pdf_state[200]))

        def test_crop_preview_and_pdf_settings_caption(self):
            self.open_mode()
            self.bot.store["p1"] = paper_photo()
            self.add_photo()
            self.bot.dispatch(message(crop.CROP_MENU_BUTTON))
            self.bot.dispatch(message(crop.CROP_AUTO_BUTTON))
            self.bot.dispatch(message(filt.PREVIEW_BUTTON))
            self.assertIn("Auto Crop", self.bot.photos[-1][2]["caption"])
            self.bot.dispatch(message("✅ Create PDF"))
            self.assertEqual(len(self.bot.documents), 1)
            self.assertIn("Auto Crop", self.bot.documents[0][2]["caption"])

        def test_original_pdf_preserved_default(self):
            self.open_mode()
            self.add_photo()
            self.bot.dispatch(message("✅ Create PDF"))
            self.assertEqual(len(self.bot.documents), 1)
            self.assertIn("Original", self.bot.documents[0][2]["caption"])

        def test_unrelated_pdf_modes_still_work(self):
            self.bot.dispatch(message("📄 PDF Tools"))
            self.assertTrue(any("Merge PDFs" in x[1] for x in self.bot.sent))
else:
    class CropTelegramFlowTests(unittest.TestCase):
        @unittest.skip("Install and run V7.13 tests to check Telegram handler integration")
        def test_requires_v713_suite(self):
            pass

if __name__ == "__main__":
    unittest.main()
