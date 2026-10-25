"""V7.4 offline tests for privacy, export completeness, installer and compatibility."""
from __future__ import annotations

import ast
import io
import tempfile
import types
import unittest
from pathlib import Path

import INSTALL_V7_4 as installer
import study_collections_v73 as col
import study_collection_tools_v74 as tools
import TEST_V7_3_COLLECTIONS as previous
import TEST_V6_6_REVISION_HUB as older

ROOT=Path(__file__).resolve().parent
BASE=(ROOT/'FIXTURE_V7_3_COLLECTIONS.txt').read_text(encoding='utf-8')


class MockQuery(previous.Query):
    def in_(self,key,values):
        self.in_filter = (key, set(values))
        return self
    def execute(self):
        if self.op!='select' or not hasattr(self,'in_filter'):
            return super().execute()
        if self.db.fail: raise RuntimeError('Disconnected')
        self.db.calls.append((self.op,self.table,list(self.filters)))
        entries=self.db.tables[self.table]
        key,values=self.in_filter
        data=[dict(row) for row in entries
              if row.get(key) in values and all(str(row.get(k))==str(v) for k,v in self.filters)]
        if self.sort_key:data.sort(key=lambda row:row[self.sort_key],reverse=self.reverse)
        if self.max is not None:data=data[:self.max]
        return previous.Result(data)


class MockDB(previous.DB):
    def table(self,table):return MockQuery(self,table)


class MockBot(older.FakeBot):
    def __init__(self):
        super().__init__()
        self.documents=[]
    def send_document(self,chatid,doc,**kw):
        self.documents.append((chatid,doc.name,doc.getvalue(),kw))


BUTTON_TYPES=types.SimpleNamespace(InlineKeyboardButton=older.FakeButton,
                                    InlineKeyboardMarkup=older.FakeInline)


class InstallerTests(unittest.TestCase):
    def stage(self,root,newline='\n'):
        (root/installer.TARGET).write_bytes(BASE.replace('\n',newline).encode('utf-8'))
        for name in (installer.HELPER,'study_markdown_v70.py'):
            (root/name).write_bytes((ROOT/name).read_bytes())

    def test_idempotent_patch_on_v73(self):
        updated,changed=installer.patch_module(BASE)
        self.assertTrue(changed)
        ast.parse(updated)
        self.assertFalse(installer.patch_module(updated)[1])
        for text in ('📊 Collection Tools','📤 Export Collection (MD)',
                     'register_study_collection_tools_v74_handlers'):
            self.assertIn(text,updated)
        self.assertEqual(BASE.count('def register_study_collections_v73_handlers'),1)

    def test_rejects_unrecognized_and_partial_patch(self):
        with self.assertRaises(installer.InstallationError):installer.patch_module('pass\n')
        patched,_=installer.patch_module(BASE)
        for block in (installer.MENU_BLOCK,installer.BUTTON_BLOCK,installer.REG_BLOCK):
            with self.assertRaises(installer.InstallationError):
                installer.patch_module(patched.replace(block,'',1))

    def test_preserves_v73_existing_handlers_and_callbacks(self):
        patched,_=installer.patch_module(BASE)
        for action in ('v73_create','v73_rename','v73_delete','v73_callback'):
            self.assertIn('def '+action,patched)
        self.assertEqual(patched.count('def v73_callback'),1)

    def test_installer_backup_and_repeat(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.stage(p)
            (p/'gemini_ai_studio_v59.py').write_text('unchanged',encoding='utf-8')
            self.assertTrue(installer.install(p))
            self.assertFalse(installer.install(p))
            self.assertEqual((p/installer.BACKUP).read_bytes(),BASE.encode('utf-8'))
            self.assertEqual((p/'gemini_ai_studio_v59.py').read_text(encoding='utf-8'),'unchanged')

    def test_windows_utf8_and_crlf_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.stage(p,'\r\n')
            self.assertTrue(installer.install(p))
            raw=(p/installer.TARGET).read_bytes()
            self.assertIn(b'\r\n',raw)
            self.assertNotIn(b'\r\r\n',raw)
            self.assertEqual((p/installer.BACKUP).read_bytes(),BASE.replace('\n','\r\n').encode('utf-8'))

    def test_missing_dependency_or_backup_collision_refused(self):
        for missing in (installer.HELPER,'study_markdown_v70.py'):
            with tempfile.TemporaryDirectory() as d:
                p=Path(d);self.stage(p)
                old=(p/installer.TARGET).read_bytes()
                (p/missing).unlink()
                with self.assertRaises(installer.InstallationError):installer.install(p)
                self.assertEqual((p/installer.TARGET).read_bytes(),old)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.stage(p)
            old=(p/installer.TARGET).read_bytes()
            (p/installer.BACKUP).write_text('existing backup',encoding='utf-8')
            with self.assertRaises(installer.InstallationError):installer.install(p)
            self.assertEqual((p/installer.TARGET).read_bytes(),old)

    def test_installer_preserves_untouched_modules(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.stage(p)
            for file in ('main.py','revision_hub_v66.py','ai_study_assistant.py'):
                (p/file).write_text('unchanged_'+file,encoding='utf-8')
            installer.install(p)
            for file in ('main.py','revision_hub_v66.py','ai_study_assistant.py'):
                self.assertEqual((p/file).read_text(encoding='utf-8'),'unchanged_'+file)


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.db=MockDB();self.bot=MockBot()
        tools.register_study_collection_tools_v74_handlers(self.bot,self.db,BUTTON_TYPES)
    def add_collection(self,name='Biology'):
        return col.create_collection(self.db,42,name)['id']
    def add_note(self,cid,nid):
        col.add_note(self.db,42,cid,nid,previous.load_note)

    def test_search_literal_casefold_tamil_and_ownership(self):
        self.add_collection('Biology Revision')
        self.add_collection('தமிழ் இலக்கணம்')
        col.create_collection(self.db,99,'Biology Private')
        before = len(self.db.calls)
        self.assertEqual([r['name'] for r in tools.search_collections(self.db,42,'bIoLoGy')],['Biology Revision'])
        self.assertEqual(len(tools.search_collections(self.db,42,'தமிழ்')),1)
        self.assertEqual(tools.search_collections(self.db,42,'private'),[])
        self.assertTrue(all(('user_id',42) in call[2] for call in self.db.calls[before:] if call[0]=='select'))

    def test_search_invalid_terms_and_no_db_access(self):
        for value in ('','x','z'*61,'\x00hey',None):
            before=len(self.db.calls)
            with self.assertRaises(ValueError):tools.search_collections(self.db,42,value)
            self.assertEqual(len(self.db.calls),before)

    def test_stats_counts_link_records_not_cross_owner(self):
        a=self.add_collection('Science');b=self.add_collection('Maths')
        self.db.tables[col.ITEMS]=[
            {'user_id':42,'collection_id':a,'note_id':1},
            {'user_id':42,'collection_id':b,'note_id':1},
            {'user_id':42,'collection_id':b,'note_id':2},
            {'user_id':99,'collection_id':a,'note_id':3},
        ]
        result=tools.collection_stats(self.db,42)
        self.assertEqual(result['links'],3)
        self.assertEqual(result['unique_note_ids'],2)
        self.assertEqual(result['counts'],{a:1,b:2})

    def test_stats_500_page_boundaries_and_max(self):
        cid=self.add_collection()
        self.db.tables[col.ITEMS]=[{'user_id':42,'collection_id':cid,'note_id':i+1} for i in range(510)]
        result=tools.collection_stats(self.db,42)
        self.assertEqual(result['links'],510)
        self.db.tables[col.ITEMS]=[{'user_id':42,'collection_id':cid,'note_id':i+1}
                                  for i in range(tools.MAX_MEMBERSHIPS+1)]
        with self.assertRaises(RuntimeError):tools.collection_stats(self.db,42)

    def test_export_only_own_ai_study_notes_and_maintains_order(self):
        cid=self.add_collection()
        self.add_note(cid,1)
        self.add_note(cid,2)
        collection, notes=tools.collection_export_notes(self.db,42,cid)
        self.assertEqual(collection['id'],cid)
        self.assertEqual([n['id'] for n in notes],[2,1])
        self.assertTrue(all(n['user_id']==42 for n in notes))

    def test_export_wrong_owner_denied_without_note_read(self):
        cid=self.add_collection()
        before=len(self.db.calls)
        with self.assertRaises(ValueError):tools.collection_export_notes(self.db,99,cid)
        self.assertFalse(any(x[1]=='notes' for x in self.db.calls[before:]))

    def test_stale_or_non_ai_notes_refuse_partial_export(self):
        cid=self.add_collection()
        self.db.tables[col.ITEMS]=[{'user_id':42,'collection_id':cid,'note_id':1},
                                   {'user_id':42,'collection_id':cid,'note_id':3}]
        with self.assertRaises(tools.CollectionExportError):tools.collection_export_notes(self.db,42,cid)
        self.db.tables[col.ITEMS][-1]['note_id']=4
        with self.assertRaises(tools.CollectionExportError):tools.collection_export_notes(self.db,42,cid)

    def test_export_empty_and_membership_limit(self):
        cid=self.add_collection()
        collection,notes=tools.collection_export_notes(self.db,42,cid)
        self.assertEqual(notes,[])
        self.db.tables[col.ITEMS]=[{'user_id':42,'collection_id':cid,'note_id':i+1} for i in range(101)]
        with self.assertRaises(tools.CollectionExportError):tools.collection_export_notes(self.db,42,cid)

    def test_export_markdown_multilingual_and_in_memory(self):
        cid=self.add_collection('தமிழ் அறிவியல்')
        self.add_note(cid,1)
        collection,notes=tools.collection_export_notes(self.db,42,cid)
        with tools.collection_markdown_document(collection,notes) as file:
            self.assertEqual(file.name,f'Student_Assistant_Collection_{cid}.md')
            value=file.read().decode('utf-8-sig')
            self.assertIn('தமிழ் அறிவியல்',value)
            self.assertIn('ஒளிச்சேர்க்கை',value)
            self.assertIn('Collection Export',value)
            self.assertTrue(value.count('## 1.')==1)

    def test_export_oversize_never_truncated(self):
        cid=self.add_collection()
        self.db.tables['notes'][0]['content']='அ' * 1_300_000
        self.add_note(cid,1)
        collection,notes=tools.collection_export_notes(self.db,42,cid)
        with self.assertRaises(ValueError):tools.collection_markdown_document(collection,notes)

    def test_register_all_new_commands(self):
        for name in ('v74_menu','v74_search','v74_stats','v74_export'):
            self.assertIn(name,self.bot.handlers)
        self.assertIn('v74_callback',self.bot.callbacks)

    def test_group_or_forged_private_never_reads_database(self):
        self.bot.handlers['v74_search'](older.message(42,-100,'group','/collectionsearch Bio'))
        self.bot.handlers['v74_stats'](older.message(42,-100,'group','/collectionstats'))
        self.bot.handlers['v74_export'](older.message(42,-100,'group','/collectionexport 12'))
        self.bot.callbacks['v74_callback'](older.callback('v74:e:12',42,-100,'group'))
        self.bot.callbacks['v74_callback'](older.callback('v74:e:12',99,42,'private'))
        self.assertEqual(self.db.calls,[])
        self.assertEqual(self.bot.documents,[])

    def test_export_confirm_not_sent_until_tap(self):
        cid=self.add_collection();self.add_note(cid,1)
        self.bot.handlers['v74_export'](older.message(42,text=f'/collectionexport {cid}'))
        self.assertFalse(self.bot.documents)
        kb=self.bot.sent[-1][2]['reply_markup']
        self.assertIn(f'v74:e:{cid}',[b.callback_data for row in kb.rows for b in row])
        self.bot.callbacks['v74_callback'](older.callback(f'v74:e:{cid}'))
        self.assertEqual(len(self.bot.documents),1)
        self.assertIn('ஒளிச்சேர்க்கை',self.bot.documents[0][2].decode('utf-8-sig'))
        self.assertEqual(self.db.writes,[('insert',col.COLLECTIONS,self.db.tables[col.COLLECTIONS][0]),
                                         ('insert',col.ITEMS,self.db.tables[col.ITEMS][0])])

    def test_callback_rechecks_current_owner_and_cancel(self):
        cid=self.add_collection();self.add_note(cid,1)
        cb=self.bot.callbacks['v74_callback']
        cb(older.callback(f'v74:n:{cid}'))
        self.assertEqual(self.bot.documents,[])
        cb(older.callback(f'v74:e:{cid}',uid=99))
        self.assertEqual(self.bot.documents,[])
        self.assertTrue(any('No file' in m[1] for m in self.bot.sent))

    def test_deleting_note_after_confirmation_prevents_partial_file(self):
        cid=self.add_collection();self.add_note(cid,1)
        self.bot.handlers['v74_export'](older.message(42,text=f'/collectionexport {cid}'))
        self.db.tables['notes']=[n for n in self.db.tables['notes'] if n['id']!=1]
        self.bot.callbacks['v74_callback'](older.callback(f'v74:e:{cid}'))
        self.assertEqual(self.bot.documents,[])

    def test_callback_menu_and_stats(self):
        self.bot.callbacks['v74_callback'](older.callback('v74:menu:0'))
        self.assertIn('Collection Tools',self.bot.sent[-1][1])
        self.bot.callbacks['v74_callback'](older.callback('v74:stats:0'))
        self.assertIn('Collection Statistics',self.bot.sent[-1][1])

    def test_bad_database_does_not_show_empty_success(self):
        self.add_collection();self.db.fail=True
        self.bot.handlers['v74_stats'](older.message(42,text='/collectionstats'))
        self.assertIn('unavailable',self.bot.sent[-1][1])

    def test_v73_buttons_remain_and_new_buttons_present(self):
        updated,_=installer.patch_module(BASE)
        names={}
        exec(compile(updated,'study_collections_v73.py','exec'),names)
        mod=types.SimpleNamespace(**names)
        db=MockDB();bot=MockBot();cid=col.create_collection(db,42,'Collection')['id']
        col.add_note(db,42,cid,1,previous.load_note)
        mod._show_collection(bot,db,BUTTON_TYPES,42,42,cid,previous.load_note)
        callbacks=[b.callback_data for row in bot.sent[-1][2]['reply_markup'].rows for b in row]
        self.assertIn(f'v74:request:{cid}',callbacks)
        self.assertIn(f'v73:x:{cid}',callbacks)
        mod._list_ui(bot,db,BUTTON_TYPES,42,42)
        callbacks=[b.callback_data for row in bot.sent[-1][2]['reply_markup'].rows for b in row]
        self.assertIn('v74:menu:0',callbacks)

if __name__=='__main__':unittest.main()
