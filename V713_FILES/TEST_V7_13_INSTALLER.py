"""Installer safety checks, without touching current project."""
from __future__ import annotations
import unittest
from pathlib import Path
from INSTALL_V7_13 import patch_pdf_tools, MARKER


class InstallerTests(unittest.TestCase):
    def test_not_already_patched_then_patched(self):
        s = (Path(__file__).parent / 'pdf_tools.py').read_text(encoding='utf-8')
        self.assertIn(MARKER, s)
        self.assertEqual(patch_pdf_tools(s), s)

    def test_rejects_unknown_pdf_layout(self):
        with self.assertRaisesRegex(ValueError, 'V7.11'):
            patch_pdf_tools('def unrelated(): pass')

    def test_converter_is_registered_before_generic_document_handler(self):
        s = (Path(__file__).parent / 'pdf_tools.py').read_text(encoding='utf-8')
        self.assertLess(s.index('register_office_to_pdf_handlers('), s.index('def receive_pdf_document('))
        self.assertIn('types.KeyboardButton(DOCX_BUTTON)', s)
        self.assertIn('types.KeyboardButton(PPTX_BUTTON)', s)
        self.assertIn('enqueue_image(state, file_bytes)', s)
        self.assertIn('enqueue_image(state, image_bytes)', s)

if __name__ == '__main__':
    unittest.main()
