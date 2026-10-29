"""Focused offline tests for V7.13 image filters + V7.14 optional auto crop."""
from __future__ import annotations
from io import BytesIO
import inspect
import unittest
from PIL import Image, ImageDraw
import image_filters_v713 as filt


def sample():
    img = Image.new('RGB', (440, 600), (70, 71, 76))
    draw = ImageDraw.Draw(img)
    draw.rectangle((30, 35, 410, 560), fill=(247, 248, 242))
    draw.line((90, 155, 340, 155), fill=(30, 32, 34), width=3)
    out=BytesIO()
    img.save(out, 'PNG')
    img.close()
    return out.getvalue()

class ImageCropCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.image=sample()
    def test_preview_accepts_crop_setting(self):
        self.assertIn('auto_crop', inspect.signature(filt.make_preview).parameters)
    def test_pdf_accepts_crop_setting(self):
        self.assertIn('auto_crop', inspect.signature(filt.images_to_pdf).parameters)
    def test_legacy_preview_still_works(self):
        out=filt.make_preview(self.image,'original')
        self.assertTrue(out.getvalue().startswith(b'\xff\xd8'))
        out.close()
    def test_legacy_pdf_still_works(self):
        out=filt.images_to_pdf([self.image],'original')
        self.assertTrue(out.getvalue().startswith(b'%PDF'))
        out.close()
    def test_auto_crop_preview_works(self):
        out=filt.make_preview(self.image,'original',auto_crop=True)
        self.assertTrue(out.getvalue().startswith(b'\xff\xd8'))
        out.close()
    def test_auto_crop_pdf_works(self):
        out=filt.images_to_pdf([self.image,self.image],'scan',auto_crop=True)
        self.assertTrue(out.getvalue().startswith(b'%PDF'))
        out.close()

if __name__=='__main__':unittest.main(verbosity=2)
