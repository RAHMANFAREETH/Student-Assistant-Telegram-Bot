"""V6.9 offline privacy, export, compatibility, and Windows installer tests."""
import ast
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import INSTALL_V6_9 as installer
import TEST_V6_6_REVISION_HUB as v66

HERE = Path(__file__).resolve().parent
FIXTURE = (HERE / 'FIXTURE_V6_8_REVISION_HUB.txt').read_text(encoding='utf-8')


def modules(db):
    tel = types.ModuleType('telebot')
    tel.types = types.SimpleNamespace(
        KeyboardButton=v66.FakeButton, InlineKeyboardButton=v66.FakeButton,
        ReplyKeyboardMarkup=v66.FakeReply, InlineKeyboardMarkup=v66.FakeInline)
    db_module = types.ModuleType('db')
    db_module.supabase = db
    safe = types.ModuleType('safe_utils')
    safe.split_telegram_text = lambda s, limit: [s[i:i+limit] for i in range(0,len(s), limit)]
    with patch.dict(sys.modules, {'telebot':tel, 'db':db_module, 'safe_utils':safe}):
        helper = types.ModuleType('study_export_v69')
        exec(compile((HERE / 'study_export_v69.py').read_text(encoding='utf-8'),
                     'study_export_v69.py', 'exec'), helper.__dict__)
        with patch.dict(sys.modules, {'study_export_v69':helper}):
            code, _ = installer.patch_module(FIXTURE)
            hub = types.ModuleType('revision_hub_v66')
            exec(compile(code, 'revision_hub_v66.py', 'exec'), hub.__dict__)
    return helper, hub


class DocBot(v66.FakeBot):
    def __init__(self):
        super().__init__()
        self.files=[]
    def send_document(self, chatid, document, **kw):
        self.files.append((chatid, document.name, document.read(), kw))


class InstallerTests(unittest.TestCase):
    def test_patch_and_idempotence(self):
        result, changed = installer.patch_module(FIXTURE)
        self.assertTrue(changed)
        ast.parse(result)
        self.assertIn('register_study_export_v69_handlers(bot, supabase)', result)
        self.assertIn('Export: /studyexport', result)
        self.assertEqual(installer.patch_module(result), (result, False))

    def test_reject_unknown_or_partial(self):
        for source in ('pass\n', FIXTURE.replace('# V6.8 Full-Text Saved AI Note Search', '')):
            with self.assertRaises(installer.InstallationError):
                installer.patch_module(source)
        patched, _ = installer.patch_module(FIXTURE)
        with self.assertRaises(installer.InstallationError):
            installer.patch_module(patched.replace('register_study_export_v69_handlers(bot, supabase)', 'pass'))

    def test_atomic_backup_and_only_one_file_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/installer.TARGET).write_text(FIXTURE, encoding='utf-8')
            (root/'study_export_v69.py').write_bytes((HERE/'study_export_v69.py').read_bytes())
            (root/'ai_study_assistant.py').write_text('unchanged')
            self.assertTrue(installer.install(root))
            self.assertFalse(installer.install(root))
            self.assertEqual((root/'ai_study_assistant.py').read_text(), 'unchanged')
            self.assertEqual((root/installer.BACKUP).read_text(encoding='utf-8'), FIXTURE)
            self.assertEqual(list(root.glob('.v69_*.tmp')), [])

    def test_windows_line_endings(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/installer.TARGET).write_bytes(FIXTURE.replace('\n','\r\n').encode('utf-8'))
            (root/'study_export_v69.py').write_bytes((HERE/'study_export_v69.py').read_bytes())
            self.assertTrue(installer.install(root))
            data=(root/installer.TARGET).read_bytes()
            self.assertIn(b'\r\n', data)
            self.assertNotIn(b'\r\r\n', data)
            ast.parse(data.decode('utf-8'))

    def test_backup_conflict_prevents_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/installer.TARGET).write_text(FIXTURE, encoding='utf-8')
            (root/'study_export_v69.py').write_bytes((HERE/'study_export_v69.py').read_bytes())
            (root/installer.BACKUP).write_text('unrelated',encoding='utf-8')
            with self.assertRaises(installer.InstallationError): installer.install(root)
            self.assertEqual((root/installer.TARGET).read_text(encoding='utf-8'), FIXTURE)

    def test_missing_helper_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/installer.TARGET).write_text(FIXTURE,encoding='utf-8')
            with self.assertRaises(installer.InstallationError): installer.install(root)
            self.assertFalse((root/installer.BACKUP).exists())


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.db = v66.FakeDB()
        self.helper, self.hub = modules(self.db)
        self.bot = DocBot()
        self.hub.register_revision_hub_v66_handlers(self.bot, lambda *a:None)

    def test_owner_only_ai_notes_and_utf8(self):
        notes = self.helper.load_export_notes(self.db,42)
        self.assertEqual(len(notes),1)
        data=self.helper.build_export_bytes(notes,now=datetime(2026,10,25,tzinfo=timezone.utc))
        self.assertTrue(data.startswith(b'\xef\xbb\xbf'))
        text=data.decode('utf-8-sig')
        self.assertIn('தமிழ் ஒளிச்சேர்க்கை',text)
        self.assertNotIn('Personal Note',text)
        self.assertNotIn('other user',text)
        self.assertNotIn('very private',text)
        self.assertIn(('eq','user_id',42),self.db.calls[-1][1])
        self.assertIn(('ilike','title','AI Study:%'),self.db.calls[-1][1])

    def test_commands_wait_for_confirmation(self):
        self.bot.handlers['v69_export_request'](v66.message(42,text='/studyexport'))
        self.assertEqual(self.bot.files,[])
        self.assertEqual(self.db.calls,[])
        kb=self.bot.sent[-1][2]['reply_markup']
        self.assertEqual([b.callback_data for row in kb.rows for b in row],
                         [self.helper.CONFIRM,self.helper.CANCEL])

    def test_confirm_sends_private_file_without_ai_calls(self):
        self.bot.callbacks['v69_export_callback'](v66.callback(self.helper.CONFIRM))
        self.assertEqual(len(self.bot.files),1)
        self.assertEqual(self.bot.files[0][0],42)
        self.assertEqual(self.bot.files[0][1],'Student_Assistant_AI_Study_Notes.txt')
        self.assertIn('தமிழ்',self.bot.files[0][2].decode('utf-8-sig'))
        self.assertFalse([name for name, *_ in self.db.calls if name != 'notes'])

    def test_cancel_requires_no_query_or_file(self):
        self.bot.callbacks['v69_export_callback'](v66.callback(self.helper.CANCEL))
        self.assertEqual(self.db.calls,[])
        self.assertEqual(self.bot.files,[])
        self.assertIn('cancelled',self.bot.sent[-1][1])

    def test_nonprivate_command_refused_without_db(self):
        self.bot.handlers['v69_export_request'](v66.message(42,kind='group',chatid=-1,text='/studyexport'))
        self.assertEqual(self.db.calls,[])
        self.assertIn('private',self.bot.sent[-1][1])

    def test_forwarded_or_group_callback_refused_before_db(self):
        for msg in [v66.callback(self.helper.CONFIRM,uid=42,chatid=77),
                    v66.callback(self.helper.CONFIRM,uid=42,kind='group')]:
            self.bot.callbacks['v69_export_callback'](msg)
        self.assertEqual(self.db.calls,[])
        self.assertEqual(self.bot.files,[])
        self.assertTrue(all(item[2].get('show_alert') for item in self.bot.answered))

    def test_empty_db_user_no_send(self):
        self.db.tables['notes'] = []
        self.bot.callbacks['v69_export_callback'](v66.callback(self.helper.CONFIRM))
        self.assertEqual(self.bot.files,[])
        self.assertIn('No saved AI',self.bot.sent[-1][1])

    def test_db_failure_sanitized(self):
        self.db.fail = True
        self.bot.callbacks['v69_export_callback'](v66.callback(self.helper.CONFIRM))
        self.assertEqual(self.bot.files,[])
        self.assertIn('Could not export',self.bot.sent[-1][1])
        self.assertNotIn('key not reported',self.bot.sent[-1][1])

    def test_note_limit_no_partial_send(self):
        self.db.tables['notes'] += [dict(id=i+100,user_id=42,title='AI Study: lesson',content='x',created_at='today')
                                    for i in range(self.helper.MAX_NOTES)]
        with self.assertRaises(self.helper.ExportLimitError):
            self.helper.load_export_notes(self.db,42)
        self.bot.callbacks['v69_export_callback'](v66.callback(self.helper.CONFIRM))
        self.assertEqual(self.bot.files,[])
        self.assertIn('No partial',self.bot.sent[-1][1])

    def test_size_limit_no_partial_send(self):
        notes=[{'title':'AI Study: Large','content':'அ'*self.helper.MAX_EXPORT_BYTES}]
        with self.assertRaises(self.helper.ExportLimitError):
            self.helper.build_export_bytes(notes)

    def test_pagination_exports_all_behind_first_page(self):
        self.db.tables['notes'] += [dict(id=i+100,user_id=42,title='AI Study: More',content='some note',created_at='today')
                                    for i in range(203)]
        notes=self.helper.load_export_notes(self.db,42)
        self.assertEqual(len(notes),204)
        self.assertGreaterEqual(len(self.db.calls),3)
        self.assertEqual(notes[0]['id'],302)

    def test_multilingual_content_saved_verbatim(self):
        self.db.tables['notes'].append({'id':55,'user_id':42,'title':'AI Study: العربية',
                                        'content':'العربية தமிழ் සිංහල English', 'created_at':'today'})
        data = self.helper.build_export_bytes(self.helper.load_export_notes(self.db,42)).decode('utf-8-sig')
        for word in ('العربية','தமிழ்','සිංහල','English'):
            self.assertIn(word,data)

    def test_existing_revision_handlers_remain_registered(self):
        for name in ('revision_find','revision_content_search','revision_cards','revision_callback','revision_library_page'):
            self.assertIn(name,self.bot.handlers if 'callback' not in name and 'page' not in name else self.bot.callbacks)
        self.assertIn('v69_export_request',self.bot.handlers)
        self.assertIn('v69_export_callback',self.bot.callbacks)

    def test_invalid_export_rows_refused(self):
        with self.assertRaises(ValueError): self.helper.build_export_bytes([{'title':'Some other note'}])
        with self.assertRaises(ValueError): self.helper.load_export_notes(self.db,-123)


if __name__=='__main__':
    unittest.main()
