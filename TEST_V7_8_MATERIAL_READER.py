"""V7.8 tests. Runs offline: no Telegram, API key or Supabase connection."""
import ast
import tempfile
import unittest
from pathlib import Path

import INSTALL_V7_8 as installer
import material_reader_v78 as reader
from TEST_V7_7_MATERIAL_EXPORT import FakeBot, TYPES, Store


class ReaderFunctions(unittest.TestCase):
    def test_lossless_paging_with_multilingual_text(self):
        content = ('தமிழ் العربية සිංහල English 🔬\n' * 270).strip()
        reconstructed = []
        total = None
        for page in range(20):
            number, pages, chunk = reader.read_page(content, page)
            total = pages
            if page >= total:
                break
            self.assertEqual(number, page)
            self.assertLessEqual(len(chunk), reader.PAGE_CHARS)
            reconstructed.append(chunk)
        self.assertEqual(''.join(reconstructed), content)
        self.assertGreater(total, 1)

    def test_paging_clamps_and_handles_empty(self):
        self.assertEqual(reader.read_page(' abc ', -123), (0, 1, 'abc'))
        self.assertEqual(reader.read_page(' abc ', 555), (0, 1, 'abc'))
        with self.assertRaises(ValueError):
            reader.read_page(' \n ')

    def test_ascii_only_positive_id(self):
        self.assertEqual(reader.parse_positive_id('17'), 17)
        for value in ['0', '-1', '1x', '١', '', str(2**63), '9' * 300]:
            self.assertIsNone(reader.parse_positive_id(value))

    def test_unicode_search_and_matching_positions(self):
        res = reader.search_extracted_text('தாவரங்கள் ஒளிச்சேர்க்கை செய்கின்றன. ஒளிச்சேர்க்கை!', 'ஒளிச்சேர்க்கை')
        self.assertEqual(res['count'], 2)
        self.assertEqual(len(res['results']), 2)
        res = reader.search_extracted_text('INTRO ABOUT PHOTOSYNTHESIS.', 'photosynthesis')
        self.assertEqual(res['count'], 1)
        res = reader.search_extracted_text('Straße', 'STRASSE')
        self.assertIsInstance(res['count'], int)

    def test_search_is_limited_and_explicitly_partial(self):
        content = 'x' * reader.SEARCH_SCAN_CHARS + ' photosynthesis'
        res = reader.search_extracted_text(content, 'photosynthesis')
        self.assertEqual(res['count'], 0)
        self.assertTrue(res['partial'])
        self.assertEqual(res['scanned'], reader.SEARCH_SCAN_CHARS)
        res2 = reader.search_extracted_text('Aa ' * 40, 'aa')
        self.assertEqual(res2['count'], 40)
        self.assertEqual(len(res2['results']), 5)

    def test_search_query_validation(self):
        for bad in ['', 'x', 'a'*81, 'bad\nquery', 'bad\tquery']:
            with self.assertRaises(ValueError):
                reader.search_extracted_text('abc abc', bad)
        with self.assertRaises(ValueError):
            reader.search_extracted_text(' ', 'abc')


class ReaderHandlers(unittest.TestCase):
    def setUp(self):
        self.bot = FakeBot()
        self.store = Store()
        self.material_state = {42: {'phase': 'await_document'}}
        self.visited = []
        self.handlers = reader.register_material_reader_handlers(
            self.bot, TYPES, self.store.get, self.material_state,
            lambda cid, uid: self.visited.append(('library', cid, uid)),
            lambda cid, uid, mid: self.visited.append(('preview', cid, uid, mid)),
        )

    def test_read_command_and_callbacks(self):
        self.bot.cmd('materialread', '7')
        self.assertIn('Page 1/1', self.bot.text)
        self.assertIn('Extracted text only', self.bot.text)
        self.assertNotIn(42, self.material_state)
        self.bot.click_named('📖 Preview')
        self.assertEqual(self.visited[-1], ('preview', 42, 42, 7))
        self.bot.cmd('materialread', '7')
        self.bot.click_named('📚 Material Library')
        self.assertEqual(self.visited[-1], ('library', 42, 42))

    def test_long_document_page_navigation(self):
        self.store.data[7]['extracted_text'] = ('🔬 Science தமிழ். ' * 400)
        self.bot.cmd('materialread', '7')
        self.assertIn('Page 1/', self.bot.text)
        self.assertIn('Next ➡️', [button.text for button in self.bot.buttons()])
        self.bot.click_named('Next ➡️')
        self.assertIn('Page 2/', self.bot.text)
        self.bot.click_named('⬅️ Previous')
        self.assertIn('Page 1/', self.bot.text)
        self.assertGreaterEqual(len(self.store.queries), 3)  # re-auth each page

    def test_search_command_and_hint(self):
        self.bot.cmd('materialinside', '7 ஒளிச்சேர்க்கை')
        self.assertIn('Matches in scanned text: 1', self.bot.text)
        self.bot.click_named('📖 Read Material')
        self.bot.click_named('🔎 Search Inside')
        self.assertIn('/materialinside 7 photosynthesis', self.bot.text)

    def test_missing_args_and_unsafe_input(self):
        self.bot.cmd('materialread')
        self.assertIn('Usage:', self.bot.text)
        self.bot.cmd('materialinside', '7')
        self.assertIn('Usage:', self.bot.text)
        self.bot.cmd('materialinside', '7 x')
        self.assertIn('2–80', self.bot.text)
        self.bot.cmd('materialread', '١')
        self.assertIn('Usage:', self.bot.text)
        self.bot.click('v78:read:7:-3')
        self.bot.click('v78:read:7:99999999999')
        self.bot.click('v78:read:7:abc')
        self.assertNotIn('secret', self.bot.text)

    def test_foreign_and_deleted_material_denied(self):
        self.bot.cmd('materialread', '8')
        self.assertIn('not accessible', self.bot.text)
        self.bot.cmd('materialinside', '8 secret')
        self.assertIn('not accessible', self.bot.text)
        self.bot.click('v78:hint:8')
        self.assertIn('not accessible', self.bot.text)
        self.bot.cmd('materialread', '700')
        self.assertIn('not accessible', self.bot.text)

    def test_private_chat_only_and_not_leaked(self):
        self.bot.cmd('materialread', '7', uid=99, chat_type='group')
        self.assertIn('private chat', self.bot.text)
        self.bot.click('v78:read:7:0', uid=99, chat_type='group')
        self.assertIn('private chat', self.bot.text)
        self.assertNotIn('தமிழ் உயிரியல்', self.bot.text)

    def test_fresh_ownership_on_each_page(self):
        self.store.data[7]['extracted_text'] = 'a'*5000
        self.bot.cmd('materialread', '7')
        self.store.data[7]['user_id'] = 99
        self.bot.click_named('Next ➡️')
        self.assertIn('not accessible', self.bot.text)

    def test_empty_text_and_database_failure(self):
        self.store.data[7]['extracted_text'] = ''
        self.bot.cmd('materialread', '7')
        self.assertIn('No extracted text', self.bot.text)
        self.store.fail = True
        self.bot.cmd('materialread', '7')
        self.assertIn('Could not load', self.bot.text)
        self.assertNotIn('database secret', self.bot.text)

    def test_callback_cannot_bypass_user_chat_id(self):
        # Private callback with a different chat than the clicking user.
        import types
        cb = types.SimpleNamespace(id='z', data='v78:read:7:0',
          from_user=types.SimpleNamespace(id=42),
          message=types.SimpleNamespace(chat=types.SimpleNamespace(id=99, type='private')))
        self.bot.callbacks[0][1](cb)
        self.assertIn('private chat', self.bot.text)

    def test_partial_search_report_not_silent(self):
        self.store.data[7]['extracted_text'] = 'b'*reader.SEARCH_SCAN_CHARS+' target'
        self.bot.cmd('materialinside', '7 target')
        self.assertIn('Only the first', self.bot.text)
        self.assertIn('No matches in the scanned text.', self.bot.text)


class FullIntegrationTests(unittest.TestCase):
    def test_installed_library_routes_read_and_search(self):
        from material_library_v75 import register_material_library_handlers
        bot = FakeBot()
        store = Store()
        state = {}
        register_material_library_handlers(
            bot, lambda cid: None, state, types_module=TYPES,
            list_fn=lambda uid, limit=100: [store.data[7]],
            get_fn=store.get, delete_fn=lambda uid, mid: False,
        )
        bot.cmd('materialpreview', '7')
        labels = [b.text for b in bot.buttons()]
        self.assertIn('📖 Read Full Text', labels)
        self.assertIn('🔎 Search Inside', labels)
        self.assertIn('📥 TXT Extract', labels)
        bot.click_named('📖 Read Full Text')
        self.assertIn('Page 1/1', bot.text)
        bot.click_named('🔎 Search Inside')
        self.assertIn('/materialinside 7 photosynthesis', bot.text)
        bot.cmd('materialinside', '7 ஒளிச்சேர்க்கை')
        self.assertIn('Matches in scanned text: 1', bot.text)


class InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = Path(__file__).with_name('FIXTURE_V7_7_MATERIAL_LIBRARY.txt').read_text(encoding='utf-8')

    def test_patch_installs_and_idempotent(self):
        patched, changed = installer.patch_code(self.fixture)
        self.assertTrue(changed)
        self.assertIn('v77:req:txt:', patched)
        self.assertIn('register_material_filter_handlers(', patched)
        self.assertIn('register_material_download_handlers(', patched)
        self.assertIn('register_material_reader_handlers(', patched)
        self.assertEqual(patched.count('v78:read:{material_id}:0'), 1)
        ast.parse(patched)
        self.assertFalse(installer.patch_code(patched)[1])

    def test_partial_patch_rejected(self):
        with self.assertRaises(installer.InstallationError):
            installer.patch_code(self.fixture.replace(installer.BUTTON_ANCHOR,
                                      installer.BUTTON_INSERT + installer.BUTTON_ANCHOR, 1))

    def test_mismatch_rejected(self):
        with self.assertRaises(installer.InstallationError):
            installer.patch_code('def unrelated(): pass')

    def test_backup_and_windows_crlf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = self.fixture.replace('\n', '\r\n').encode('utf-8')
            (root / installer.TARGET).write_bytes(original)
            (root / installer.HELPER).write_text('"""helper"""\n', encoding='utf-8')
            self.assertTrue(installer.install(root))
            self.assertEqual((root / installer.BACKUP).read_bytes(), original)
            updated = (root / installer.TARGET).read_bytes()
            self.assertIn(b'\r\n', updated)
            self.assertFalse(installer.install(root))
            self.assertEqual((root / installer.TARGET).read_bytes(), updated)

    def test_preexisting_backup_blocks_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / installer.TARGET).write_text(self.fixture, encoding='utf-8')
            (root / installer.HELPER).write_text('x=1\n', encoding='utf-8')
            (root / installer.BACKUP).write_text('previous backup', encoding='utf-8')
            with self.assertRaises(installer.InstallationError):
                installer.install(root)
            self.assertEqual((root / installer.TARGET).read_text(encoding='utf-8'), self.fixture)

    def test_helper_missing_never_modifies_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / installer.TARGET).write_text(self.fixture, encoding='utf-8')
            with self.assertRaises(installer.InstallationError):
                installer.install(root)
            self.assertEqual((root / installer.TARGET).read_text(encoding='utf-8'), self.fixture)


if __name__ == '__main__':
    unittest.main()
