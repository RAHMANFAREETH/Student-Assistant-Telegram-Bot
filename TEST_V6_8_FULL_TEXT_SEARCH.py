"""V6.8 offline tests; no network, secrets, or running Telegram service."""
from pathlib import Path
import ast
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import INSTALL_V6_8 as installer
import TEST_V6_6_REVISION_HUB as v66

HERE = Path(__file__).resolve().parent
SOURCE = (HERE / 'FIXTURE_V6_7_REVISION_HUB.txt').read_text(encoding='utf-8')


def v68_module(db, src=SOURCE):
    upgraded, _ = installer.patch_module(src)
    tel = types.ModuleType('telebot')
    tel.types = types.SimpleNamespace(
        KeyboardButton=v66.FakeButton, InlineKeyboardButton=v66.FakeButton,
        ReplyKeyboardMarkup=v66.FakeReply, InlineKeyboardMarkup=v66.FakeInline)
    db_mod = types.ModuleType('db')
    db_mod.supabase = db
    util_mod = types.ModuleType('safe_utils')
    util_mod.split_telegram_text = lambda s, limit: [s[i:i+limit] for i in range(0, len(s), limit)]
    with patch.dict(sys.modules, {'telebot': tel, 'db': db_mod, 'safe_utils': util_mod}):
        mod = types.ModuleType('revision_hub_v66')
        exec(compile(upgraded, 'revision_hub_v66.py', 'exec'), mod.__dict__)
    return mod


class InstallerTests(unittest.TestCase):
    def test_patch_valid_and_idempotent(self):
        upgraded, changed = installer.patch_module(SOURCE)
        self.assertTrue(changed)
        ast.parse(upgraded)
        self.assertIn('def revision_content_search(message)', upgraded)
        self.assertEqual(installer.patch_module(upgraded), (upgraded, False))

    def test_v67_prerequisite_required(self):
        with self.assertRaises(installer.InstallationError):
            installer.patch_module('def unrelated(): pass\n')
        with self.assertRaises(installer.InstallationError):
            installer.patch_module(SOURCE.replace('def revision_find(message):', 'def gone(message):'))

    def test_partial_upgrade_rejected(self):
        src, _ = installer.patch_module(SOURCE)
        with self.assertRaises(installer.InstallationError):
            installer.patch_module(src.replace('def search_saved_ai_content(db, uid, term):', 'def missing(db, uid, term):'))

    def test_installer_preserves_other_files_and_backup(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / installer.TARGET).write_text(SOURCE, encoding='utf-8')
            (root / 'ai_study_assistant.py').write_text('no change', encoding='utf-8')
            self.assertTrue(installer.install(root))
            self.assertFalse(installer.install(root))
            self.assertEqual((root / 'ai_study_assistant.py').read_text(), 'no change')
            self.assertEqual((root / installer.BACKUP).read_text(encoding='utf-8'), SOURCE)
            self.assertEqual(list(root.glob('.v68_*.tmp')), [])

    def test_windows_crlf_utf8_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = root / installer.TARGET
            p.write_bytes(SOURCE.replace('\n', '\r\n').encode('utf-8'))
            self.assertTrue(installer.install(root))
            self.assertIn(b'\r\n', p.read_bytes())
            self.assertNotIn(b'\r\r\n', p.read_bytes())
            self.assertIn('📚 My AI Study Library', p.read_text(encoding='utf-8'))

    def test_existing_backup_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = root / installer.TARGET
            p.write_text(SOURCE, encoding='utf-8')
            (root / installer.BACKUP).write_text('unrelated', encoding='utf-8')
            with self.assertRaises(installer.InstallationError):
                installer.install(root)
            self.assertEqual(p.read_text(encoding='utf-8'), SOURCE)

    def test_bad_source_does_not_create_backup(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = root / installer.TARGET
            p.write_text('pass\n', encoding='utf-8')
            with self.assertRaises(installer.InstallationError):
                installer.install(root)
            self.assertEqual(p.read_text(encoding='utf-8'), 'pass\n')
            self.assertFalse((root / installer.BACKUP).exists())


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.db = v66.FakeDB()
        self.db.tables['notes'] += [
            {'id':4, 'user_id':42, 'title':'AI Study: Biology',
             'content':'Chlorophyll absorbs sunlight and makes glucose.', 'created_at':'2026-10-25'},
            {'id':5, 'user_id':42, 'title':'AI Study: தமிழ் அறிவியல்',
             'content':'தாவரங்கள் ஒளிச்சேர்க்கையில் சூரிய ஒளியைப் பயன்படுத்துகின்றன.', 'created_at':'2026-10-25'},
            {'id':6, 'user_id':42, 'title':'AI Study: Chlorophyll basics',
             'content':'Not relevant.', 'created_at':'2026-10-25'},
            {'id':7, 'user_id':99, 'title':'AI Study: Chlorophyll secret',
             'content':'Confidential chlorophyll process.', 'created_at':'2026-10-25'},
            {'id':8, 'user_id':42, 'title':'Ordinary note',
             'content':'Chlorophyll should not appear.', 'created_at':'2026-10-25'}]
        self.mod = v68_module(self.db)
        self.bot = v66.FakeBot()
        self.mod.register_revision_hub_v66_handlers(self.bot, lambda *a: None)

    def test_search_matches_note_bodies_and_titles_and_ranks_titles_first(self):
        results, count, capped = self.mod.search_saved_ai_content(self.db, 42, 'chlorophyll')
        self.assertEqual(count, 2)
        self.assertEqual([r['id'] for r in results], [6, 4])
        self.assertEqual([r['kind'] for r in results], ['title', 'content'])
        self.assertFalse(capped)
        self.assertIn('Chlorophyll', results[1]['excerpt'])

    def test_multilingual_case_insensitive(self):
        self.assertEqual(self.mod.search_saved_ai_content(self.db, 42, 'ஒளிச்சேர்க்கை')[1], 2)
        self.assertEqual(self.mod.search_saved_ai_content(self.db, 42, 'biology')[1], 1)
        self.db.tables['notes'].append({'id':9, 'user_id':42, 'title':'AI Study: Arabic',
                                        'content':'العلوم والمعرفة', 'created_at':'2026-10-25'})
        self.assertEqual(self.mod.search_saved_ai_content(self.db, 42, 'العلوم')[1], 1)

    def test_percent_underscore_are_literal_not_query_wildcards(self):
        self.db.tables['notes'].append({'id':9, 'user_id':42, 'title':'AI Study: Code',
                                        'content':'Result: 100% completed_var', 'created_at':'2026-10-25'})
        self.assertEqual(self.mod.search_saved_ai_content(self.db, 42, '100%')[1], 1)
        self.assertEqual(self.mod.search_saved_ai_content(self.db, 42, '_var')[1], 1)

    def test_sender_id_filter_present_on_queries(self):
        self.mod.search_saved_ai_content(self.db, 42, 'chlorophyll')
        self.assertEqual(self.db.calls[-1][0], 'notes')
        self.assertIn(('eq', 'user_id', 42), self.db.calls[-1][1])
        self.assertIn(('ilike', 'title', 'AI Study:%'), self.db.calls[-1][1])
        self.assertEqual(self.mod.search_saved_ai_content(self.db, 99, 'chlorophyll')[1], 1)
        self.assertNotIn('Confidential', str(self.mod.search_saved_ai_content(self.db, 42, 'chlorophyll')))

    def test_search_bounded_200_and_8(self):
        for i in range(300):
            self.db.tables['notes'].append({'id':100+i, 'user_id':42, 'title':'AI Study: Data',
                                            'content':'searchword', 'created_at':'2026-10-25'})
        results, count, capped = self.mod.search_saved_ai_content(self.db, 42, 'searchword')
        self.assertEqual(len(results), 8)
        self.assertEqual(count, 200)
        self.assertTrue(capped)
        self.assertEqual(results[0]['id'], 399)

    def test_search_term_length_controls(self):
        for bad in ('', 'a', 'a'*61, 'x\ny'):
            with self.assertRaises(ValueError):
                self.mod.search_saved_ai_content(self.db, 42, bad)

    def test_private_command_and_usage(self):
        self.bot.handlers['revision_content_search'](v66.message(42, text='/studysearch chlorophyll'))
        self.assertIn('2 matching', self.bot.sent[-1][1])
        buttons = [b for row in self.bot.sent[-1][2]['reply_markup'].rows for b in row]
        self.assertEqual([b.callback_data for b in buttons], ['v66:n:6','v66:n:4'])
        self.bot.handlers['revision_content_search'](v66.message(42, text='/studysearch'))
        self.assertIn('titles AND content', self.bot.sent[-1][1])

    def test_private_only_before_db(self):
        self.bot.handlers['revision_content_search'](v66.message(42, kind='group', text='/studysearch chlorophyll'))
        self.assertEqual(self.db.calls, [])
        self.assertIn('private chat', self.bot.sent[-1][1])

    def test_callback_open_requires_fresh_owner_lookup(self):
        self.bot.handlers['revision_content_search'](v66.message(42, text='/studysearch chlorophyll'))
        self.db.calls.clear()
        self.bot.callbacks['revision_callback'](v66.callback('v66:n:7'))
        self.assertEqual(self.bot.sent[-1][1].startswith('🔎'), True)
        self.assertTrue(self.bot.answered[-1][2].get('show_alert'))
        self.assertIn(('eq', 'user_id', 42), self.db.calls[-1][1])

    def test_db_error_sanitized_not_false_empty(self):
        self.db.fail = True
        self.bot.handlers['revision_content_search'](v66.message(42, text='/studysearch chlorophyll'))
        self.assertIn('unavailable', self.bot.sent[-1][1])
        self.assertNotIn('key not reported', self.bot.sent[-1][1])

    def test_no_match_and_preview_bounded(self):
        self.bot.handlers['revision_content_search'](v66.message(42, text='/studysearch nonexistent'))
        self.assertIn('No matches', self.bot.sent[-1][1])
        excerpt = self.mod._v68_excerpt('a'*250 + 'MATCH' + 'z'*250, 'MATCH')
        self.assertLessEqual(len(excerpt), 128)
        self.assertIn('MATCH', excerpt)

    def test_read_only_and_existing_handlers_intact(self):
        updated, _ = installer.patch_module(SOURCE)
        self.assertNotIn('.insert(', updated)
        self.assertNotIn('.upsert(', updated)
        self.assertNotIn('.delete(', updated)
        self.assertIn('def revision_find(message):', updated)
        self.assertIn('def revision_library_page(call):', updated)
        self.assertIn('def revision_callback(call):', updated)
        self.assertEqual(self.db.calls, [])


if __name__ == '__main__':
    unittest.main()
