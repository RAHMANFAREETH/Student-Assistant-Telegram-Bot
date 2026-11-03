"""V7.13+ Office PDF integration checks for the current bot layout.

The old INSTALL_V7_13.py file uses an abandoned installer API and is retained
only as a historical artifact. The actual deployed integration uses
`office_to_pdf_v713.register_office_to_pdf_handlers`.
"""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.src = (ROOT / 'pdf_tools.py').read_text(encoding='utf-8')
        self.tree = ast.parse(self.src)

    def test_office_handlers_registered_before_pdf_upload_handler(self):
        fn = next(n for n in self.tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == 'register_pdf_handlers')
        start = ast.get_source_segment(self.src, fn)
        self.assertIn('register_office_to_pdf_handlers(', start)
        self.assertLess(start.index('register_office_to_pdf_handlers('),
                        start.index('def receive_pdf_document('))
        self.assertIn('from office_to_pdf_v713 import register_office_to_pdf_handlers', self.src)

    def test_office_buttons_visible_in_pdf_tools_menu(self):
        fn = next(n for n in self.tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == '_pdf_tools_menu')
        segment = ast.get_source_segment(self.src, fn)
        for label in ('📄 DOCX → PDF', '📊 PPTX → PDF', '🏠 Main Menu'):
            self.assertIn(label, segment)
        self.assertLess(segment.index('📄 DOCX → PDF'), segment.index('🏠 Main Menu'))

    def test_office_file_upload_keeps_private_chat_requirement(self):
        src = (ROOT / 'office_to_pdf_v713.py').read_text(encoding='utf-8')
        tree = ast.parse(src)
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == 'register_office_to_pdf_handlers')
        segment = ast.get_source_segment(src, fn)
        self.assertIn('def _private(', segment)
        self.assertIn('if not _private(m):', segment)
        self.assertIn('commands=["docxpdf", "pptxpdf"]', segment)


if __name__ == '__main__':
    unittest.main()
