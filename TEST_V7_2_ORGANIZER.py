"""Offline tests for V7.2 note ownership, organization, installer, and regression."""
from __future__ import annotations

import ast
import contextlib
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import INSTALL_V7_2 as installer
import study_organizer_v72 as organizer
import TEST_V6_6_REVISION_HUB as old
import TEST_V7_1_NOTE_ACTIONS as v71

HERE = Path(__file__).resolve().parent
BASELINE = (HERE/'FIXTURE_V7_1_REVISION_HUB.txt').read_text(encoding='utf-8')


class Result:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, db, table):
        self.db, self.table = db, table
        self.filters = []
        self.limit_value = None
        self.sort_column = None
        self.sort_desc = False
        self.payload = None

    def select(self, _): return self
    def eq(self, column, value): self.filters.append(('eq',column,value)); return self
    def ilike(self, column, value): self.filters.append(('ilike',column,value)); return self
    def in_(self, column, values): self.filters.append(('in',column,tuple(values))); return self
    def order(self, column, desc=False): self.sort_column=column; self.sort_desc=desc; return self
    def limit(self, value): self.limit_value=value; return self
    def upsert(self, payload, on_conflict=None):
        if on_conflict != 'user_id,note_id':
            raise AssertionError('unsafe conflict keys')
        self.payload = dict(payload)
        return self
    def execute(self):
        if self.db.fail:
            raise RuntimeError('offline DB error')
        self.db.requests.append((self.table, list(self.filters)))
        if self.payload is not None:
            self.db.writes.append(self.payload)
            records=self.db.tables[self.table]
            for i,row in enumerate(records):
                if all(str(row[k]) == str(self.payload[k]) for k in ('user_id','note_id')):
                    records[i] = self.payload
                    break
            else:
                records.append(self.payload)
            return Result([self.payload])
        rows = list(self.db.tables[self.table])
        for op, name, val in self.filters:
            if op=='eq': rows=[r for r in rows if str(r.get(name)) == str(val)]
            elif op=='ilike': rows=[r for r in rows if str(r.get(name,'')).lower().startswith(str(val)[:-1].lower())]
            elif op=='in': rows=[r for r in rows if str(r.get(name)) in set(map(str,val))]
        if self.sort_column:
            rows.sort(key=lambda x:x.get(self.sort_column, 0),reverse=self.sort_desc)
        if self.limit_value is not None:
            rows=rows[:self.limit_value]
        return Result(rows)


class FakeDB:
    def __init__(self):
        self.fail=False
        self.requests=[]
        self.writes=[]
        self.tables={
            'notes':[
                {'id': 1,'user_id':42,'title':'AI Study: ஒளிச்சேர்க்கை','content':'Tamil 🌱'},
                {'id': 2,'user_id':42,'title':'AI Study: Algebra','content':'Maths'},
                {'id': 3,'user_id':99,'title':'AI Study: another student','content':'Private'},
                {'id': 4,'user_id':42,'title':'Personal note','content':'Private'},
                {'id': 5,'user_id':42,'title':'AI Study: Physics','content':'Science'},
            ],
            organizer.TABLE:[],
        }

    def table(self,name):
        return FakeQuery(self,name)


def load_note(db,uid, ident):
    rows=(db.table('notes').select('id,title,content').eq('user_id',uid)
          .eq('id',ident).limit(1).execute()).data
    if not rows or not str(rows[0]['title']).startswith('AI Study:'):
        return None
    return rows[0]


def load_page(db, uid, page):
    rows=(db.table('notes').select('id,title').eq('user_id',uid)
          .ilike('title','AI Study:%').order('id',desc=True).execute()).data
    return rows[page*8:(page+1)*8], len(rows)>(page+1)*8


class Bot(old.FakeBot):
    pass


class InstallerTests(unittest.TestCase):
    def test_patch_idempotent_and_no_other_provider_edits(self):
        patched, changed=installer.patch_module(BASELINE)
        self.assertTrue(changed)
        self.assertEqual(installer.patch_module(patched),(patched,False))
        self.assertIn('register_study_organizer_v72_handlers(bot, supabase, load_note, load_ai_note_page, types)',patched)
        self.assertIn('📎 Quick actions', patched)
        self.assertIn('🗂 Organize AI Notes',patched)
        ast.parse(patched)
        self.assertEqual(BASELINE.count('from study_note_actions_v71 import'), 2)
        self.assertEqual(patched.count('from study_note_actions_v71 import'), 2)

    def test_old_and_partial_modules_rejected(self):
        with self.assertRaises(installer.InstallationError): installer.patch_module('pass\n')
        patched,_=installer.patch_module(BASELINE)
        with self.assertRaises(installer.InstallationError):
            installer.patch_module(patched.replace(installer.MENU_BLOCK,'',1))
        with self.assertRaises(installer.InstallationError):
            installer.patch_module(patched.replace('    org_actions = note_organizer_keyboard(types, row.get("id"))\n','',1))

    def _stage(self, root, newline='\n'):
        (root/installer.TARGET).write_bytes(BASELINE.replace('\n',newline).encode('utf-8'))
        for fname in (installer.HELPER, installer.SQL):
            (root/fname).write_bytes((HERE/fname).read_bytes())
        (root/'study_note_actions_v71.py').write_bytes((HERE/'study_note_actions_v71.py').read_bytes())

    def test_installer_atomic_backup_and_idempotence(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            self._stage(root)
            (root/'ai_study_assistant.py').write_text('unchanged',encoding='utf-8')
            self.assertTrue(installer.install(root))
            self.assertFalse(installer.install(root))
            self.assertEqual((root/installer.BACKUP).read_text(encoding='utf-8'),BASELINE)
            self.assertEqual((root/'ai_study_assistant.py').read_text(encoding='utf-8'),'unchanged')
            self.assertFalse(list(root.glob('.v72_*.tmp')))

    def test_windows_utf8_crlf(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name); self._stage(root, '\r\n')
            self.assertTrue(installer.install(root))
            content=(root/installer.TARGET).read_bytes()
            self.assertIn(b'\r\n',content)
            self.assertNotIn(b'\r\r\n',content)
            ast.parse(content.decode('utf-8'))
            self.assertFalse(installer.install(root))

    def test_missing_sql_backup_conflict_no_write(self):
        for missing in (installer.SQL, installer.HELPER, 'study_note_actions_v71.py'):
            with tempfile.TemporaryDirectory() as name:
                root=Path(name); self._stage(root)
                before=(root/installer.TARGET).read_bytes()
                (root/missing).unlink()
                with self.assertRaises(installer.InstallationError): installer.install(root)
                self.assertEqual((root/installer.TARGET).read_bytes(),before)
        with tempfile.TemporaryDirectory() as name:
            root=Path(name); self._stage(root)
            before=(root/installer.TARGET).read_bytes()
            (root/installer.BACKUP).write_text('older backup',encoding='utf-8')
            with self.assertRaises(installer.InstallationError): installer.install(root)
            self.assertEqual((root/installer.TARGET).read_bytes(),before)

    def test_sql_is_metadata_only_and_private(self):
        sql=(HERE/installer.SQL).read_text(encoding='utf-8')
        self.assertIn('ENABLE ROW LEVEL SECURITY',sql)
        self.assertIn('REVOKE ALL',sql)
        self.assertNotIn('DROP TABLE',sql)
        self.assertNotIn('ALTER TABLE public.notes',sql)
        self.assertNotIn('CREATE POLICY',sql)


class OrganizerTests(unittest.TestCase):
    def setUp(self):
        self.db=FakeDB()
        self.bot=Bot()
        self.types=types.SimpleNamespace(InlineKeyboardButton=old.FakeButton,InlineKeyboardMarkup=old.FakeInline)
        organizer.register_study_organizer_v72_handlers(self.bot,self.db,load_note,load_page,self.types)

    def test_registration_and_ui(self):
        self.assertIn('v72_recent',self.bot.handlers)
        self.assertIn('v72_favorites',self.bot.handlers)
        self.assertIn('v72_subjects',self.bot.handlers)
        self.assertIn('v72_organizer_callback',self.bot.callbacks)
        kb=organizer.note_organizer_keyboard(self.types,1)
        self.assertEqual(kb.rows[0][0].callback_data,'v72:o:1')
        self.assertIsNone(organizer.note_organizer_keyboard(self.types,-1))

    def test_private_and_group_no_metadata_or_notes_read(self):
        self.bot.handlers['v72_recent'](old.message(42,-123,'group'))
        self.bot.handlers['v72_favorites'](old.message(42,-123,'group'))
        self.bot.callbacks['v72_organizer_callback'](old.callback('v72:f:1',42,-123,'group'))
        self.assertFalse(self.db.requests)
        self.assertFalse(self.db.writes)

    def test_open_note_checks_owner_before_organizer_table(self):
        self.bot.callbacks['v72_organizer_callback'](old.callback('v72:o:3'))
        self.assertFalse(any(table==organizer.TABLE for table,_ in self.db.requests))
        self.assertFalse(self.db.writes)

    def test_favorites_toggle_and_ownership(self):
        cb=self.bot.callbacks['v72_organizer_callback']
        cb(old.callback('v72:f:1'))
        self.assertEqual(self.db.writes[-1],{'user_id':42,'note_id':1,'favorite':True,'subject':None})
        cb(old.callback('v72:f:1'))
        self.assertIs(self.db.writes[-1]['favorite'],False)
        cb(old.callback('v72:f:3'))  # other student's note
        cb(old.callback('v72:f:4'))  # manual non-AI note
        self.assertEqual(len(self.db.writes),2)

    def test_subject_selection_and_clear_preserves_favorite(self):
        cb=self.bot.callbacks['v72_organizer_callback']
        cb(old.callback('v72:f:1'))
        cb(old.callback('v72:s:1'))
        buttons=[b.callback_data for row in self.bot.sent[-1][2]['reply_markup'].rows for b in row]
        self.assertIn('v72:t:0:1',buttons)
        self.assertIn('v72:t:6:1',buttons)
        cb(old.callback('v72:t:0:1'))
        self.assertEqual(self.db.writes[-1]['subject'],'Science')
        self.assertTrue(self.db.writes[-1]['favorite'])
        cb(old.callback('v72:t:6:1'))
        self.assertIsNone(self.db.writes[-1]['subject'])
        self.assertTrue(self.db.writes[-1]['favorite'])

    def test_organizer_query_filters_and_rechecks_note_owner(self):
        self.db.tables[organizer.TABLE]=[
            {'user_id':42,'note_id':1,'favorite':True,'subject':'Science'},
            {'user_id':42,'note_id':3,'favorite':True,'subject':'Science'}, # forged cross-owner ref
            {'user_id':42,'note_id':4,'favorite':True,'subject':'Science'}, # personal note, not AI
            {'user_id':99,'note_id':2,'favorite':True,'subject':'Science'}, # forged other account
            {'user_id':42,'note_id':2,'favorite':False,'subject':'Science'},
        ]
        found,count,capped=organizer.load_organizer_notes(self.db,42,favorite=True)
        self.assertEqual([x['id'] for x in found],[1])
        self.assertEqual(count,1)
        self.assertFalse(capped)
        found,count,_=organizer.load_organizer_notes(self.db,42,subject='Science')
        self.assertEqual([x['id'] for x in found],[2,1])
        self.assertEqual(count,2)
        self.assertTrue(any(('eq','user_id',42) in args for table,args in self.db.requests if table=='notes'))

    def test_recent_works_without_metadata_sql_and_is_save_order(self):
        del self.db.tables[organizer.TABLE]
        self.bot.handlers['v72_recent'](old.message())
        self.assertIn('Recently SAVED',self.bot.sent[-1][1])
        self.assertIn('🗂 Study Organizer',self.bot.sent[0][1])
        self.assertFalse(self.db.writes)

    def test_favorites_db_error_clearly_reports_setup(self):
        del self.db.tables[organizer.TABLE]
        self.bot.handlers['v72_favorites'](old.message())
        self.assertIn('SQL_V7_2_NOTE_ORGANIZER.sql',self.bot.sent[-1][1])

    def test_note_id_validation_and_bounded_callback(self):
        for invalid in (-4,0,10**20,'abc',True):
            with self.assertRaises(ValueError): organizer._id(invalid)
        for invalid in ('v72:f:-1','v72:f:0','v72:t:99:1','v72:f:1;DROP TABLE'):
            # Some syntactically valid callbacks are rejected at semantic validation.
            if invalid in ('v72:t:99:1', 'v72:f:0'):
                self.assertIsNotNone(organizer.CALLBACK.fullmatch(invalid))
            else:
                self.assertIsNone(organizer.CALLBACK.fullmatch(invalid))
        self.bot.callbacks['v72_organizer_callback'](old.callback('v72:t:99:1'))
        self.assertFalse(self.db.writes)

    def test_no_ai_calls_or_notes_mutations(self):
        self.bot.callbacks['v72_organizer_callback'](old.callback('v72:f:1'))
        self.bot.callbacks['v72_organizer_callback'](old.callback('v72:t:0:1'))
        self.assertTrue(all(set(item)=={'user_id','note_id','favorite','subject'} for item in self.db.writes))
        self.assertEqual(len(self.db.writes), 2)
        source=(HERE/'study_organizer_v72.py').read_text(encoding='utf-8')
        for forbidden in ('GEMINI_API_KEY', 'CLOUDFLARE_API_TOKEN', 'AI_DAILY_LIMIT', '.delete(', '.insert('):
            self.assertNotIn(forbidden,source)

    def test_unauthorized_chat_same_uid_wrong_chat_denied(self):
        cb=old.callback('v72:f:1',uid=42,chatid=900,kind='private')
        self.bot.callbacks['v72_organizer_callback'](cb)
        self.assertFalse(self.db.requests)
        self.assertFalse(self.db.writes)

    def test_public_subject_values_only(self):
        with self.assertRaises(ValueError):
            organizer.save_metadata(self.db,42,1,{'favorite':False},subject='admin;drop',change='subject')
        with self.assertRaises(ValueError):
            organizer.load_organizer_notes(self.db,42,subject='UserDefined')


class IntegrationTests(unittest.TestCase):
    def test_live_hub_note_shows_v72_and_v71_actions(self):
        db=FakeDB()
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.dict(sys.modules,v71._fake_env(db)))
            export=v71._load((HERE/'study_export_v69.py').read_text(encoding='utf-8'),
                             'study_export_v69')
            md=v71._load((HERE/'study_markdown_v70.py').read_text(encoding='utf-8'),
                         'study_markdown_v70')
            actions=v71._load((HERE/'study_note_actions_v71.py').read_text(encoding='utf-8'),
                              'study_note_actions_v71')
            stack.enter_context(patch.dict(sys.modules,
                {'study_export_v69':export, 'study_markdown_v70':md,
                 'study_note_actions_v71':actions,
                 'study_organizer_v72':organizer}))
            patched, did_change=installer.patch_module(BASELINE)
            self.assertTrue(did_change)
            hub=v71._load(patched,'revision_hub_v66')
            bot=v71.DocBot()
            hub.register_revision_hub_v66_handlers(bot, lambda *args:None)
            self.assertIn('v72_organizer_callback', bot.callbacks)
            self.assertIn('v71_note_action_callback', bot.callbacks)
            self.assertIn('v72_recent', bot.handlers)
            bot.callbacks['revision_callback'](old.callback('v66:n:1'))
            all_callbacks=[b.callback_data for _,_,kw in bot.sent
                           for row in getattr(kw.get('reply_markup'), 'rows', [])
                           for b in row if getattr(b,'callback_data',None)]
            self.assertIn('v72:o:1',all_callbacks)
            self.assertIn('v71:txt:1',all_callbacks)
            self.assertIn('v71:md:1',all_callbacks)
            self.assertFalse(db.writes)


if __name__=='__main__':
    unittest.main()
