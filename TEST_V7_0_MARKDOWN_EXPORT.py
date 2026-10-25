"""V7.0 offline Markdown export, access control, installer and regression tests."""
import ast
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import INSTALL_V7_0 as installer
import TEST_V6_6_REVISION_HUB as v66
import TEST_V6_9_EXPORT as v69tests
import study_markdown_v70 as md

HERE = Path(__file__).resolve().parent
BASELINE = (HERE/'FIXTURE_V6_9_EXPORT.txt').read_text(encoding='utf-8')


def v70_runtime(db):
    """Emulate V6.9 registration with the V7.0 patch and fake Telegram API."""
    tel = types.ModuleType('telebot')
    tel.types = types.SimpleNamespace(
        KeyboardButton=v66.FakeButton, InlineKeyboardButton=v66.FakeButton,
        ReplyKeyboardMarkup=v66.FakeReply, InlineKeyboardMarkup=v66.FakeInline)
    with patch.dict(sys.modules, {'telebot': tel}):
        source = (HERE / 'study_export_v69.py').read_text(encoding='utf-8')
        source, _ = installer.patch_module(source)
        helper = types.ModuleType('study_export_v69')
        exec(compile(source, 'study_export_v69.py', 'exec'), helper.__dict__)
    bot = v69tests.DocBot()
    helper.register_study_export_v69_handlers(bot, db)
    return bot, helper


class InstallerTests(unittest.TestCase):
    def test_patch_once_and_idempotent(self):
        src = BASELINE
        patched, yes = installer.patch_module(src)
        self.assertTrue(yes)
        ast.parse(patched)
        self.assertIn('register_study_markdown_v70_handlers', patched)
        self.assertEqual(installer.patch_module(patched), (patched, False))

    def test_refuse_wrong_version(self):
        for src in ('pass\n', 'def register_study_export_v69_handlers(bot, db):\n    return True\n'):
            with self.assertRaises(installer.InstallationError):
                installer.patch_module(src)

    def test_partial_patch_refused(self):
        src = BASELINE
        patched,_ = installer.patch_module(src)
        with self.assertRaises(installer.InstallationError):
            installer.patch_module(patched.replace('register_study_markdown_v70_handlers(bot, db, types, load_export_notes,',
                                                  'register_study_markdown_v70_handlers(bot, db, types, WRONG,',1))

    def test_install_backup_idempotence_and_no_unrelated_changes(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            content=BASELINE.encode('utf-8')
            (root/installer.TARGET).write_bytes(content)
            (root/installer.HELPER).write_bytes((HERE/installer.HELPER).read_bytes())
            (root/'ai_study_assistant.py').write_text('unchanged',encoding='utf-8')
            self.assertTrue(installer.install(root))
            self.assertFalse(installer.install(root))
            self.assertEqual((root/installer.BACKUP).read_bytes(),content)
            self.assertEqual((root/'ai_study_assistant.py').read_text(encoding='utf-8'), 'unchanged')
            self.assertFalse(list(root.glob('.v70_*.tmp')))

    def test_windows_crlf_preserved(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            code=BASELINE
            (root/installer.TARGET).write_bytes(code.replace('\n','\r\n').encode('utf-8'))
            (root/installer.HELPER).write_bytes((HERE/installer.HELPER).read_bytes())
            self.assertTrue(installer.install(root))
            data=(root/installer.TARGET).read_bytes()
            self.assertIn(b'\r\n',data)
            self.assertNotIn(b'\r\r\n',data)
            ast.parse(data.decode('utf-8'))

    def test_backup_conflict_prevents_mutation(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            original=BASELINE.encode('utf-8')
            (root/installer.TARGET).write_bytes(original)
            (root/installer.HELPER).write_bytes((HERE/installer.HELPER).read_bytes())
            (root/installer.BACKUP).write_text('preexisting backup', encoding='utf-8')
            with self.assertRaises(installer.InstallationError):installer.install(root)
            self.assertEqual((root/installer.TARGET).read_bytes(),original)

    def test_missing_helper_preflight_does_not_mutate(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            original=BASELINE.encode('utf-8')
            (root/installer.TARGET).write_bytes(original)
            with self.assertRaises(installer.InstallationError):installer.install(root)
            self.assertEqual((root/installer.TARGET).read_bytes(),original)
            self.assertFalse((root/installer.BACKUP).exists())


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.notes=[{'id':1,'title':'AI Study: தமிழ் ஒளிச்சேர்க்கை','content':'தாவரங்கள் 🌱\nالعربية\nසිංහල\nEnglish',
                     'created_at':'2026-10-25'}]

    def test_markdown_multilingual_and_bom(self):
        b=md.build_markdown_bytes(self.notes,now=datetime(2026,10,25,tzinfo=timezone.utc))
        self.assertTrue(b.startswith(b'\xef\xbb\xbf'))
        text=b.decode('utf-8-sig')
        for word in ('தமிழ்','العربية','සිංහල','English','🌱'):
            self.assertIn(word,text)
        self.assertIn('## 1. AI Study:',text)
        self.assertIn('2026-10-25',text)

    def test_embedded_fences_and_html_preserved_inside_longer_fence(self):
        self.notes[0]['content']='````\n<script>alert(1)</script>\n````\n# heading'
        content=md.build_markdown_bytes(self.notes).decode('utf-8-sig')
        self.assertIn('`````text\n````\n<script>alert(1)</script>\n````\n# heading\n`````',content)

    def test_title_newline_and_html_cannot_create_heading_or_tag(self):
        self.notes[0]['title']='AI Study: My lesson\n<h1>Injected</h1>'
        content=md.build_markdown_bytes(self.notes).decode('utf-8-sig')
        self.assertIn('My lesson &lt;h1&gt;Injected&lt;/h1&gt;',content)
        self.assertNotIn('\n<h1>Injected</h1>',content)

    def test_size_limit_refuses_partial(self):
        self.notes[0]['content']='அ'*md.MAX_EXPORT_BYTES
        with self.assertRaises(md.MarkdownExportLimitError):md.build_markdown_bytes(self.notes)

    def test_note_count_limit(self):
        with self.assertRaises(md.MarkdownExportLimitError):md.build_markdown_bytes(self.notes * 2001)

    def test_bad_note_rejected(self):
        with self.assertRaises(ValueError):md.build_markdown_bytes([{'title':'Personal Note','content':'secret'}])

    def test_timestamp_must_have_timezone(self):
        with self.assertRaises(ValueError):md.build_markdown_bytes(self.notes,now=datetime(2026,10,25))

    def test_markdown_document_in_memory(self):
        with md.markdown_document(self.notes) as document:
            self.assertEqual(document.name,md.FILENAME)
            self.assertTrue(document.read().startswith(b'\xef\xbb\xbf'))


class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.db=v66.FakeDB()
        self.bot,self.helper=v70_runtime(self.db)

    def test_original_v69_handlers_untouched(self):
        self.assertIn('v69_export_request',self.bot.handlers)
        self.assertIn('v69_export_callback',self.bot.callbacks)
        self.bot.callbacks['v69_export_callback'](v66.callback(self.helper.CONFIRM))
        self.assertEqual(self.bot.files[0][1],'Student_Assistant_AI_Study_Notes.txt')

    def test_md_request_asks_before_fetching(self):
        self.bot.handlers['v70_markdown_request'](v66.message(42,text='/studyexportmd'))
        self.assertEqual(self.db.calls,[])
        self.assertEqual(self.bot.files,[])
        kb=self.bot.sent[-1][2]['reply_markup']
        buttons=[b.callback_data for row in kb.rows for b in row]
        self.assertEqual(buttons,[md.CONFIRM, md.CANCEL])

    def test_confirm_sends_owned_ai_notes_only(self):
        self.bot.callbacks['v70_markdown_callback'](v66.callback(md.CONFIRM))
        self.assertEqual(len(self.bot.files),1)
        owner,name,payload,kw=self.bot.files[0]
        self.assertEqual(owner,42)
        self.assertEqual(name,md.FILENAME)
        content=payload.decode('utf-8-sig')
        self.assertIn('தமிழ் ஒளிச்சேர்க்கை',content)
        self.assertNotIn('Personal Note',content)
        self.assertNotIn('very private',content)
        self.assertIn(('eq','user_id',42),self.db.calls[-1][1])

    def test_cancel_no_database_lookup(self):
        self.bot.callbacks['v70_markdown_callback'](v66.callback(md.CANCEL))
        self.assertEqual(self.db.calls,[])
        self.assertEqual(self.bot.files,[])
        self.assertIn('cancelled',self.bot.sent[-1][1])

    def test_group_command_denied(self):
        self.bot.handlers['v70_markdown_request'](v66.message(42,chatid=-123,kind='group'))
        self.assertEqual(self.db.calls,[])
        self.assertEqual(self.bot.files,[])

    def test_group_callback_and_sender_mismatch_denied(self):
        for call in (v66.callback(md.CONFIRM,uid=42,chatid=-12,kind='group'),
                     v66.callback(md.CONFIRM,uid=42,chatid=99)):
            self.bot.callbacks['v70_markdown_callback'](call)
        self.assertEqual(self.db.calls,[])
        self.assertEqual(self.bot.files,[])
        self.assertEqual(len(self.bot.answered),2)

    def test_empty_owned_notes_no_export(self):
        self.db.tables['notes']=[]
        self.bot.callbacks['v70_markdown_callback'](v66.callback(md.CONFIRM))
        self.assertEqual(self.bot.files,[])
        self.assertIn('No saved AI',self.bot.sent[-1][1])

    def test_db_error_sanitized(self):
        self.db.fail=True
        self.bot.callbacks['v70_markdown_callback'](v66.callback(md.CONFIRM))
        self.assertEqual(self.bot.files,[])
        self.assertIn('Could not export',self.bot.sent[-1][1])
        self.assertFalse(any('private db' in m[1] for m in self.bot.sent))

    def test_large_notes_no_send(self):
        self.db.tables['notes'][0]['content']='x'*md.MAX_EXPORT_BYTES
        self.bot.callbacks['v70_markdown_callback'](v66.callback(md.CONFIRM))
        self.assertEqual(self.bot.files,[])
        self.assertIn('No partial',self.bot.sent[-1][1])


if __name__ == '__main__':unittest.main()
