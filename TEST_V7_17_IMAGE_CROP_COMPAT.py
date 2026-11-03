"""V7.17 image engine compatibility tests (offline, no network/API calls).

Run from the project's root after applying the V7.17 patch:
    python -m unittest TEST_V7_17_IMAGE_CROP_COMPAT -v
"""
from io import BytesIO
import inspect
import unittest

from PIL import Image, ImageDraw

from image_filters_v713 import make_preview, images_to_pdf

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader


def sample_photo():
    photo = Image.new('RGB', (720, 900), (70, 69, 68))
    ImageDraw.Draw(photo).rectangle((80, 120, 640, 810), fill=(246, 246, 242))
    data = BytesIO()
    photo.save(data, format='PNG')
    photo.close()
    return data.getvalue()


class V717CropCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.photo = sample_photo()

    def test_existing_function_signatures_accept_optional_crop(self):
        self.assertIn('auto_crop', inspect.signature(make_preview).parameters)
        self.assertIn('auto_crop', inspect.signature(images_to_pdf).parameters)

    def test_legacy_preview_matches_explicit_no_crop(self):
        original = make_preview(self.photo, 'original')
        unchanged = make_preview(self.photo, 'original', auto_crop=False)
        try:
            self.assertEqual(original.getvalue(), unchanged.getvalue())
        finally:
            original.close()
            unchanged.close()

    def test_original_pdf_matches_explicit_no_crop(self):
        original = images_to_pdf([self.photo], 'original')
        unchanged = images_to_pdf([self.photo], 'original', auto_crop=False)
        try:
            self.assertEqual(original.getvalue(), unchanged.getvalue())
        finally:
            original.close()
            unchanged.close()

    def test_opt_in_preview_crops_but_preserves_source(self):
        photo = self.photo
        result = make_preview(photo, 'scan', auto_crop=True)
        try:
            with Image.open(result) as preview:
                self.assertLess(preview.width, 720)
                self.assertLess(preview.height, 900)
            self.assertEqual(photo, self.photo)
        finally:
            result.close()

    def test_opt_in_pdf_crops_all_pages_with_filter(self):
        raw = images_to_pdf([self.photo], 'original')
        cropped = images_to_pdf([self.photo, self.photo], 'scan', auto_crop=True)
        try:
            base_page = PdfReader(raw).pages[0]
            cropped_pages = PdfReader(cropped).pages
            self.assertEqual(len(cropped_pages), 2)
            self.assertLess(float(cropped_pages[0].mediabox.width), float(base_page.mediabox.width))
        finally:
            raw.close()
            cropped.close()

    def test_ambiguous_image_not_cropped(self):
        blank = Image.new('RGB', (300, 440), (255, 255, 255))
        raw = BytesIO()
        blank.save(raw, format='PNG')
        blank.close()
        result = make_preview(raw.getvalue(), 'original', auto_crop=True)
        try:
            with Image.open(result) as preview:
                self.assertEqual(preview.size, (300, 440))
        finally:
            result.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
