import ast
import unittest
from FIX_DOCUMENT_ROUTING import patch_source


SAMPLE = '''def register_translation_handlers(bot):
    translation_state = {}
    @bot.message_handler(
        content_types=["document"]
    )
    def translation_document_handler(
        message
    ):
        state = translation_state.get(message.chat.id)
        if not state:
            return
'''

class DocumentRoutingTests(unittest.TestCase):
    def test_fixes_unrestricted_handler(self):
        new = patch_source(SAMPLE.encode('utf-8')).decode('utf-8')
        self.assertIn('in {"waiting_document", "waiting_ocr_image"}', new)
        self.assertIn('content_types=["document"]', new)
        self.assertIn('def translation_document_handler(', new)
        ast.parse(new)

    def test_works_with_windows_newlines(self):
        source = SAMPLE.replace('\n', '\r\n').encode('utf-8')
        result = patch_source(source)
        self.assertIn(b'\r\n', result)
        self.assertNotIn(b'\n', result.replace(b'\r\n', b''))

    def test_idempotent(self):
        fixed = patch_source(SAMPLE.encode())
        self.assertEqual(patch_source(fixed), fixed)

    def test_unexpected_source_is_not_modified(self):
        original = b'x=1\n'
        with self.assertRaises(ValueError):
            patch_source(original)
        self.assertEqual(original, b'x=1\n')

    def test_other_code_is_unchanged(self):
        updated = patch_source(SAMPLE.encode()).decode()
        self.assertIn('if not state:\n            return', updated)

if __name__ == '__main__':
    unittest.main()
