"""Offline installer, privacy, per-note export and backwards-compatibility tests."""
import ast
import contextlib
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import INSTALL_V7_1 as installer
import TEST_V6_6_REVISION_HUB as v66
from TEST_V6_9_EXPORT import DocBot

HERE = Path(__file__).resolve().parent
BASELINE = (HERE / 'FIXTURE_V7_0_REVISION_HUB.txt').read_text(encoding='utf-8')


def _fake_env(db):
    tel = types.ModuleType('telebot')
    tel.types = types.SimpleNamespace(
        KeyboardButton=v66.FakeButton, InlineKeyboardButton=v66.FakeButton,
        ReplyKeyboardMarkup=v66.FakeReply, InlineKeyboardMarkup=v66.FakeInline)
    fake_db = types.ModuleType('db')
    fake_db.supabase = db
    safe = types.ModuleType('safe_utils')
    safe.split_telegram_text = lambda s, limit: [s[i:i+limit] for i in range(0, len(s), limit)]
    return {'telebot':tel, 'db':fake_db, 'safe_utils':safe}


def _load(source, name):
    module=types.ModuleType(name)
    exec(compile(source,name+'.py','exec'),module.__dict__)
    return module


class InstallerTests(unittest.TestCase):
    def test_patch_and_idempotence(self):
        changed, yes = installer.patch_module(BASELINE)
        self.assertTrue(yes)
        ast.parse(changed)
        self.assertIn('📎 Quick actions', changed)
        self.assertIn('register_study_note_actions_v71_handlers(bot, supabase', changed)
        self.assertEqual(installer.patch_module(changed), (changed, False))

    def test_refuse_old_and_partial_patch(self):
        for source in ('pass\n', BASELINE.replace('def _send_note(bot, chat_id, row):','def unknown():')):
            with self.assertRaises(installer.InstallationError):
                installer.patch_module(source)
        patched,_=installer.patch_module(BASELINE)
        for corrupt in (patched.replace('    actions = note_actions_keyboard(types, row.get("id"))\n','',1),
                        patched.replace('    register_study_note_actions_v71_handlers(bot, supabase, load_note, send_study_library)\n','',1)):
            with self.assertRaises(installer.InstallationError):
                installer.patch_module(corrupt)

    def _stage(self, root, windows=False):
        text=BASELINE.replace('\n','\r\n') if windows else BASELINE
        (root/installer.TARGET).write_bytes(text.encode('utf-8'))
        (root/installer.HELPER).write_bytes((HERE/installer.HELPER).read_bytes())
        (root/'study_markdown_v70.py').write_bytes((HERE/'study_markdown_v70.py').read_bytes())
        (root/'study_export_v69.py').write_bytes((HERE/'study_export_v69.py').read_bytes())

    def test_install_only_changes_hub_and_keeps_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self._stage(root)
            (root/'ai_study_assistant.py').write_text('keep',encoding='utf-8')
            self.assertTrue(installer.install(root))
            self.assertFalse(installer.install(root))
            self.assertEqual((root/installer.BACKUP).read_text(encoding='utf-8'),BASELINE)
            self.assertEqual((root/'ai_study_assistant.py').read_text(encoding='utf-8'),'keep')
            self.assertEqual(list(root.glob('.v71_*.tmp')),[])

    def test_windows_encoding_and_crlf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self._stage(root,windows=True)
            self.assertTrue(installer.install(root))
            raw=(root/installer.TARGET).read_bytes()
            self.assertIn(b'\r\n',raw)
            self.assertNotIn(b'\r\r\n',raw)
            self.assertIn('தமிழ்',raw.decode('utf-8')) if 'தமிழ்' in BASELINE else None
            ast.parse(raw.decode('utf-8'))

    def test_backup_conflict_prevents_modification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self._stage(root)
            original=(root/installer.TARGET).read_bytes()
            (root/installer.BACKUP).write_text('do-not-overwrite',encoding='utf-8')
            with self.assertRaises(installer.InstallationError): installer.install(root)
            self.assertEqual((root/installer.TARGET).read_bytes(),original)

    def test_missing_v70_or_helper_prevents_mutation(self):
        for missing in ('study_markdown_v70.py','study_note_actions_v71.py'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                self._stage(root)
                (root/missing).unlink()
                original=(root/installer.TARGET).read_bytes()
                with self.assertRaises(installer.InstallationError): installer.install(root)
                self.assertEqual((root/installer.TARGET).read_bytes(),original)
                self.assertFalse((root/installer.BACKUP).exists())

    def test_source_files_no_write_or_ai_provider_access(self):
        code=(HERE/'study_note_actions_v71.py').read_text(encoding='utf-8')
        for forbidden in ('.insert(', '.update(', '.delete(', '.upsert(', 'CLOUDFLARE_', 'GEMINI_API_KEY'):
            self.assertNotIn(forbidden,code)


class BehaviorTests(unittest.TestCase):
    def setUp(self):
        self.db=v66.FakeDB()
        self.stack=contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(sys.modules,_fake_env(self.db)))
        export=_load((HERE/'study_export_v69.py').read_text(encoding='utf-8'),'study_export_v69')
        md=_load((HERE/'study_markdown_v70.py').read_text(encoding='utf-8'),'study_markdown_v70')
        self.stack.enter_context(patch.dict(sys.modules,{'study_export_v69':export,'study_markdown_v70':md}))
        self.actions=_load((HERE/'study_note_actions_v71.py').read_text(encoding='utf-8'),'study_note_actions_v71')
        self.stack.enter_context(patch.dict(sys.modules,{'study_note_actions_v71':self.actions}))
        patched,change=installer.patch_module(BASELINE)
        self.assertTrue(change)
        self.hub=_load(patched,'revision_hub_v66')
        self.bot=DocBot()
        self.hub.register_revision_hub_v66_handlers(self.bot, lambda *args:None)

    def test_handlers_and_retain_v70_export(self):
        self.assertIn('v71_note_action_callback',self.bot.callbacks)
        self.assertIn('v71_study_help',self.bot.handlers)
        self.assertIn('v70_markdown_callback',self.bot.callbacks)
        self.assertIn('v69_export_callback',self.bot.callbacks)

    def test_open_note_shows_one_note_download_actions(self):
        self.bot.callbacks['revision_callback'](v66.callback('v66:n:1'))
        kb=self.bot.sent[-1][2]['reply_markup']
        self.assertEqual([b.callback_data for row in kb.rows for b in row],
                         ['v71:txt:1','v71:md:1','v71:lib:0'])
        self.assertIn('சூரிய', ''.join(x[1] for x in self.bot.sent))
        self.assertFalse(self.bot.files)

    def test_txt_download_multilingual_one_note_only(self):
        self.db.tables['notes'][0]['content']='தமிழ் \n Sinhala සිංහල \nالعربية 🌱'
        self.bot.callbacks['v71_note_action_callback'](v66.callback('v71:txt:1'))
        self.assertEqual(len(self.bot.files),1)
        owner,filename,raw,kw=self.bot.files[0]
        self.assertEqual(owner,42)
        self.assertEqual(filename,'AI_Study_Note_1.txt')
        text=raw.decode('utf-8-sig')
        self.assertIn('සිංහල',text)
        self.assertIn('🌱',text)
        self.assertNotIn('very private',text)
        self.assertNotIn('Personal Note',text)
        self.assertIn(('eq','user_id',42),self.db.calls[-1][1])

    def test_md_download_only_one_and_stable_filename(self):
        self.bot.callbacks['v71_note_action_callback'](v66.callback('v71:md:1'))
        self.assertEqual(len(self.bot.files),1)
        self.assertEqual(self.bot.files[0][1],'AI_Study_Note_1.md')
        self.assertIn('தமிழ்',self.bot.files[0][2].decode('utf-8-sig'))
        self.assertNotIn('very private',self.bot.files[0][2].decode('utf-8-sig'))

    def test_callback_other_user_note_denied(self):
        self.bot.callbacks['v71_note_action_callback'](v66.callback('v71:md:3'))
        self.assertEqual(self.bot.files,[])
        self.assertTrue(self.bot.answered[-1][2].get('show_alert'))
        self.assertNotIn('very private',str(self.bot.sent))

    def test_foreign_group_or_mismatched_sender_denied_before_db(self):
        for c in (v66.callback('v71:md:1',uid=42,chatid=-123,kind='group'),
                  v66.callback('v71:txt:1',uid=99,chatid=42),
                  v66.callback('v71:lib:0',uid=42,chatid=-123,kind='group')):
            self.bot.callbacks['v71_note_action_callback'](c)
        self.assertEqual(self.db.calls,[])
        self.assertEqual(self.bot.files,[])
        self.assertEqual(len(self.bot.answered),3)

    def test_back_to_library_owner_scoped(self):
        self.bot.callbacks['v71_note_action_callback'](v66.callback('v71:lib:0'))
        self.assertIn('Saved AI Notes',self.bot.sent[-1][1])
        self.assertEqual(self.bot.files,[])
        self.assertIn(('eq','user_id',42),self.db.calls[-1][1])

    def test_studytips_explains_exports_and_private(self):
        self.bot.handlers['v71_study_help'](v66.message(42,text='/studytips'))
        self.assertIn('/studyexportmd',self.bot.sent[-1][1])
        self.assertEqual(self.db.calls,[])
        self.bot.handlers['v71_study_help'](v66.message(42,chatid=-123,kind='group',text='/studytips'))
        self.assertIn('private',self.bot.sent[-1][1])
        self.assertEqual(self.db.calls,[])

    def test_invalid_note_id_no_download_button(self):
        self.assertIsNone(self.actions.note_actions_keyboard(self.hub.types, 'oops'))
        self.assertIsNone(self.actions.note_actions_keyboard(self.hub.types, 0))
        self.assertIsNone(self.actions.note_actions_keyboard(self.hub.types, 10**18))

    def test_large_note_does_not_send_partial_file(self):
        self.db.tables['notes'][0]['content']='தமிழ்' * 800000
        self.bot.callbacks['v71_note_action_callback'](v66.callback('v71:txt:1'))
        self.assertEqual(self.bot.files,[])
        self.assertIn('too large',self.bot.sent[-1][1])

    def test_db_errors_do_not_expose_secrets(self):
        self.db.fail=True
        self.bot.callbacks['v71_note_action_callback'](v66.callback('v71:md:1'))
        self.assertEqual(self.bot.files,[])
        self.assertIn('Cannot export',self.bot.sent[-1][1])
        self.assertNotIn('private db',self.bot.sent[-1][1])

    def test_other_note_type_denied(self):
        self.bot.callbacks['v71_note_action_callback'](v66.callback('v71:txt:2'))
        self.assertFalse(self.bot.files)
        self.assertTrue(self.bot.answered[-1][2].get('show_alert'))


if __name__=='__main__':
    unittest.main()
