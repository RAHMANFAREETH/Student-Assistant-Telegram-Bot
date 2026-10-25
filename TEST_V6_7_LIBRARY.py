"""V6.7 focused offline tests. Requires the V6.6 tests shipped with V6.6.
Run before or after install. Never accesses real Supabase or Telegram.
"""
from pathlib import Path
import ast
import importlib.util
import tempfile
import types
import unittest
from unittest.mock import patch

import INSTALL_V6_7 as installer
import TEST_V6_6_REVISION_HUB as v66tests

HERE = Path(__file__).resolve().parent
SOURCE = (HERE / 'FIXTURE_V6_6_REVISION_HUB.txt').read_text(encoding='utf-8')


def patched_module(db):
    """Execute V6.7-patched V6.6 in the same mocked environment as V6.6 tests."""
    import sys
    modified, _ = installer.patch_module(SOURCE)
    tel = types.ModuleType('telebot')
    tel.types = types.SimpleNamespace(
        KeyboardButton=v66tests.FakeButton,
        InlineKeyboardButton=v66tests.FakeButton,
        ReplyKeyboardMarkup=v66tests.FakeReply,
        InlineKeyboardMarkup=v66tests.FakeInline)
    mod_db = types.ModuleType('db')
    mod_db.supabase = db
    safe = types.ModuleType('safe_utils')
    safe.split_telegram_text = lambda s, limit: [s[i:i + limit] for i in range(0, len(s), limit)]
    with patch.dict(sys.modules, {'telebot': tel, 'db': mod_db, 'safe_utils': safe}):
        m = types.ModuleType('revision_hub_v66')
        exec(compile(modified, 'revision_hub_v66.py', 'exec'), m.__dict__)
    return m


def notes_for(db, uid=42, amount=20):
    for i in range(amount):
        db.tables['notes'].append({
            'id': 100 + i, 'user_id': uid,
            'title': 'AI Study: lesson ' + str(i), 'content': 'Content ' + str(i),
            'created_at': '2026-10-25'})


class PatcherTests(unittest.TestCase):
    def test_valid_patcher_and_ast(self):
        src, changed = installer.patch_module(SOURCE)
        self.assertTrue(changed)
        ast.parse(src)
        self.assertIn('def revision_find(message)', src)
        self.assertIn('def revision_library_page(call)', src)
        self.assertEqual(installer.patch_module(src), (src, False))

    def test_rejects_old_partial_and_unknown_module(self):
        for src in ('pass\n', SOURCE.replace('def revision_callback(call):', 'def removed(call):')):
            with self.assertRaises(installer.InstallationError):
                installer.patch_module(src)
        src, _ = installer.patch_module(SOURCE)
        with self.assertRaises(installer.InstallationError):
            installer.patch_module(src.replace('def revision_find(message):', 'def forgotten(message):'))

    def test_installer_only_edits_revision_hub_with_utf8_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'revision_hub_v66.py').write_text(SOURCE, encoding='utf-8')
            (root / 'main.py').write_text('unchanged')
            self.assertTrue(installer.install(root))
            self.assertEqual(installer.install(root), False)
            self.assertEqual((root / 'main.py').read_text(), 'unchanged')
            self.assertEqual((root / installer.BACKUP).read_text(encoding='utf-8'), SOURCE)
            self.assertFalse(list(root.glob('.v67_*.tmp')))

    def test_installer_windows_crlf_and_no_modify_on_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dst = root / installer.TARGET
            dst.write_bytes(SOURCE.replace('\n', '\r\n').encode('utf-8'))
            self.assertTrue(installer.install(root))
            data = dst.read_bytes()
            self.assertIn(b'\r\n', data)
            self.assertNotIn(b'\r\r\n', data)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dst = root / installer.TARGET
            dst.write_text('pass\n', encoding='utf-8')
            with self.assertRaises(installer.InstallationError):
                installer.install(root)
            self.assertEqual(dst.read_text(), 'pass\n')
            self.assertFalse((root / installer.BACKUP).exists())

    def test_backup_conflict_stops_before_modify(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dst = root / installer.TARGET
            dst.write_text(SOURCE, encoding='utf-8')
            (root / installer.BACKUP).write_text('another backup', encoding='utf-8')
            with self.assertRaises(installer.InstallationError):
                installer.install(root)
            self.assertEqual(dst.read_text(encoding='utf-8'), SOURCE)


class BrowseTests(unittest.TestCase):
    def setUp(self):
        self.db = v66tests.FakeDB()
        notes_for(self.db)
        self.mod = patched_module(self.db)
        self.bot = v66tests.FakeBot()
        self.mod.register_revision_hub_v66_handlers(self.bot, lambda *a: None)

    def test_pagination_eight_at_a_time(self):
        rows, more = self.mod.load_ai_note_page(self.db, 42, 0)
        self.assertEqual([r['id'] for r in rows], list(range(119, 111, -1)))
        self.assertTrue(more)
        rows, more = self.mod.load_ai_note_page(self.db, 42, 1)
        self.assertEqual(len(rows), 8)
        self.assertTrue(more)
        rows, more = self.mod.load_ai_note_page(self.db, 42, 2)
        self.assertEqual(len(rows), 5)  # includes V6.6 fixture's saved AI note id 1
        self.assertFalse(more)

    def test_owner_isolation_for_paging_and_title_search(self):
        self.assertEqual([r['id'] for r in self.mod.load_ai_note_page(self.db, 99, 0)[0]], [3])
        self.assertEqual(self.mod.find_ai_study_titles(self.db, 99, 'lesson')[1], 0)
        self.assertEqual(self.mod.find_ai_study_titles(self.db, 42, 'lesson')[1], 20)
        for tab, filters in self.db.calls:
            self.assertEqual(tab, 'notes')
            self.assertIn(('eq', 'user_id', 42 if ('eq', 'user_id', 42) in filters else 99), filters)

    def test_title_search_case_insensitive_multilingual_and_literal(self):
        self.db.tables['notes'].append({'id': 200, 'user_id': 42,
                                        'title': 'AI Study: தமிழ் PHOTOSYNTHESIS_100%',
                                        'content': 'private', 'created_at': '2026-10-25'})
        self.assertEqual(self.mod.find_ai_study_titles(self.db, 42, 'photosynthesis')[1], 1)
        self.assertEqual(self.mod.find_ai_study_titles(self.db, 42, 'தமிழ்')[1], 2)
        self.assertEqual(self.mod.find_ai_study_titles(self.db, 42, '100%')[1], 1)
        self.assertEqual(self.mod.find_ai_study_titles(self.db, 42, 'PHOTOSYNTHESIS_100%')[1], 1)

    def test_invalid_pages_and_search_length(self):
        for page in (-1, 1000, '0', None):
            with self.assertRaises(ValueError):
                self.mod.load_ai_note_page(self.db, 42, page)
        for term in ('a', '', 'a' * 61):
            with self.assertRaises(ValueError):
                self.mod.find_ai_study_titles(self.db, 42, term)

    def test_library_contains_previous_next_buttons(self):
        self.bot.handlers['revision_notes'](v66tests.message(42, text='/studylibrary'))
        kb = self.bot.sent[-1][2]['reply_markup']
        texts = [b.text for row in kb.rows for b in row]
        self.assertIn('Older notes ➡️', texts)
        self.assertNotIn('⬅️ Newer notes', texts)
        self.bot.callbacks['revision_library_page'](v66tests.callback('v67:l:1'))
        texts2 = [b.text for row in self.bot.sent[-1][2]['reply_markup'].rows for b in row]
        self.assertIn('⬅️ Newer notes', texts2)
        self.assertIn('Older notes ➡️', texts2)

    def test_search_command_shows_matching_buttons(self):
        self.bot.handlers['revision_find'](v66tests.message(42, text='/studyfind lesson 1'))
        self.assertIn('Found 11 title matches', self.bot.sent[-1][1])
        kb = self.bot.sent[-1][2]['reply_markup']
        self.assertLessEqual(sum(len(r) for r in kb.rows), 8)
        self.bot.handlers['revision_find'](v66tests.message(42, text='/studyfind'))
        self.assertIn('Search saved AI note titles', self.bot.sent[-1][1])

    def test_studyfind_cannot_query_db_in_group(self):
        self.bot.handlers['revision_find'](v66tests.message(42, kind='group', text='/studyfind lesson'))
        self.assertEqual(self.db.calls, [])
        self.assertIn('private chat', self.bot.sent[-1][1])

    def test_reject_page_callback_other_chat_before_db(self):
        self.bot.callbacks['revision_library_page'](v66tests.callback('v67:l:1', uid=42, chatid=99))
        self.assertEqual(self.db.calls, [])
        self.assertEqual(len(self.bot.sent), 0)
        self.assertTrue(self.bot.answered[-1][2]['show_alert'])

    def test_page_query_error_friendly_and_no_raw_exception(self):
        self.db.fail = True
        self.bot.handlers['revision_notes'](v66tests.message(42, text='/studylibrary'))
        self.assertIn('Cannot load', self.bot.sent[-1][1])
        self.bot.callbacks['revision_library_page'](v66tests.callback('v67:l:1'))
        self.assertIn('Could not load', self.bot.sent[-1][1])

    def test_zero_saved_ai_notes(self):
        self.db.tables['notes'] = []
        self.bot.handlers['revision_notes'](v66tests.message(42, text='/studylibrary'))
        self.assertIn('No saved AI study notes', self.bot.sent[-1][1])
        self.bot.callbacks['revision_library_page'](v66tests.callback('v67:l:2'))
        self.assertIn('No more older', self.bot.sent[-1][1])

    def test_still_uses_v66_note_owner_lookup(self):
        self.bot.callbacks['revision_callback'](v66tests.callback('v66:n:3'))
        self.assertIn('unavailable', self.bot.answered[-1][1].lower())
        self.assertEqual(len(self.bot.sent), 0)

    def test_no_write_or_ai_calls(self):
        s, _ = installer.patch_module(SOURCE)
        for token in ('.insert(', '.update(', '.delete(', 'generate_ai(', 'call_gemini('):
            self.assertNotIn(token, s)


if __name__ == '__main__':
    unittest.main()
