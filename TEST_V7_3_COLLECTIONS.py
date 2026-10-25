"""V7.3 offline tests: installer safety, DB owner scope, Telegram callbacks, and SQL."""
from __future__ import annotations

import ast
import tempfile
import types
import unittest
from pathlib import Path

import INSTALL_V7_3 as installer
import study_collections_v73 as col
import TEST_V6_6_REVISION_HUB as old

HERE=Path(__file__).resolve().parent
BASELINE=(HERE/'FIXTURE_V7_2_REVISION_HUB.txt').read_text(encoding='utf-8')

class Result:
    def __init__(self,data):self.data=data

class Query:
    def __init__(self,db,table):
        self.db=db;self.table=table;self.filters=[];self.op='select';self.payload=None
        self.reverse=False;self.sort_key=None;self.max=None;self.start=None;self.end=None
    def select(self,_):return self
    def eq(self,key,value):self.filters.append((key,value));return self
    def order(self,key,desc=False):self.sort_key=key;self.reverse=desc;return self
    def limit(self,n):self.max=n;return self
    def range(self,start,end):self.start=start;self.end=end;return self
    def insert(self,obj):self.op='insert';self.payload=dict(obj);return self
    def update(self,obj):self.op='update';self.payload=dict(obj);return self
    def delete(self):self.op='delete';return self
    def execute(self):
        if self.db.fail:raise RuntimeError('Disconnected')
        self.db.calls.append((self.op,self.table,list(self.filters)))
        entries=self.db.tables[self.table]
        matches=[(i,r) for i,r in enumerate(entries) if all(str(r.get(k))==str(v) for k,v in self.filters)]
        if self.op=='insert':
            item=dict(self.payload)
            if self.table==col.COLLECTIONS:
                item['id']=self.db.nextid;self.db.nextid+=1
                if any(r['user_id']==item['user_id'] and r['name'].lower()==item['name'].lower() for r in entries):
                    raise RuntimeError('duplicate collection name')
            if self.table==col.ITEMS and any(all(r.get(k)==item[k] for k in ('user_id','collection_id','note_id')) for r in entries):
                raise RuntimeError('duplicate membership')
            entries.append(item)
            self.db.writes.append((self.op,self.table,item))
            return Result([item])
        if self.op=='update':
            affected=[]
            for _,row in matches:
                row.update(self.payload);affected.append(dict(row))
            self.db.writes.append((self.op,self.table,self.payload))
            return Result(affected)
        if self.op=='delete':
            affected=[r for _,r in matches]
            self.db.tables[self.table]=[r for i,r in enumerate(entries) if i not in {i for i,_ in matches}]
            if self.table==col.COLLECTIONS:
                for r in affected:
                    self.db.tables[col.ITEMS]=[x for x in self.db.tables[col.ITEMS]
                                             if not (x['collection_id']==r['id'] and x['user_id']==r['user_id'])]
            self.db.writes.append((self.op,self.table,affected))
            return Result(affected)
        matched=[r for _,r in matches]
        if self.sort_key:
            matched.sort(key=lambda r:r.get(self.sort_key),reverse=self.reverse)
        if self.start is not None:matched=matched[self.start:self.end+1]
        if self.max is not None:matched=matched[:self.max]
        return Result([dict(x) for x in matched])

class DB:
    def __init__(self):
        self.fail=False;self.calls=[];self.writes=[];self.nextid=12
        self.tables={
            col.COLLECTIONS:[],col.ITEMS:[],
            'notes':[{'id':1,'user_id':42,'title':'AI Study: ஒளிச்சேர்க்கை','content':'கற்றல்'},
                     {'id':2,'user_id':42,'title':'AI Study: Algebra','content':'Maths'},
                     {'id':3,'user_id':99,'title':'AI Study: Private','content':'Secret'},
                     {'id':4,'user_id':42,'title':'Personal Note','content':'Secret'}]
        }
    def table(self,table):return Query(self,table)

def load_note(db,uid,nid):
    data=db.table('notes').select('id,title,content').eq('user_id',uid).eq('id',nid).limit(1).execute().data
    return data[0] if data and data[0]['title'].startswith('AI Study:') else None

class InstallerTests(unittest.TestCase):
    def test_patch_idempotence(self):
        patched,changed=installer.patch_module(BASELINE)
        self.assertTrue(changed);ast.parse(patched)
        self.assertEqual(installer.patch_module(patched),(patched,False))
        for text in ('"📁 My Collections"','register_study_collections_v73_handlers','note_collection_keyboard'):
            self.assertIn(text,patched)
        self.assertIn('register_study_organizer_v72_handlers',patched)

    def test_partial_unfamiliar_rejected(self):
        with self.assertRaises(installer.InstallationError):installer.patch_module('pass\n')
        updated,_=installer.patch_module(BASELINE)
        with self.assertRaises(installer.InstallationError):
            installer.patch_module(updated.replace(installer.NOTE_BLOCK,'',1))
        with self.assertRaises(installer.InstallationError):
            installer.patch_module(updated.replace('    collections_action = note_collection_keyboard(types, row.get("id"))\n','',1))

    def stage(self,root,newline='\n'):
        (root/installer.TARGET).write_bytes(BASELINE.replace('\n',newline).encode('utf-8'))
        for file in (installer.HELPER,installer.SQL,'study_organizer_v72.py'):
            (root/file).write_bytes((HERE/file).read_bytes())

    def test_installer_atomic_backup_and_repeat(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.stage(root)
            (root/'ai_study_assistant.py').write_text('untouched',encoding='utf-8')
            self.assertTrue(installer.install(root))
            self.assertFalse(installer.install(root))
            self.assertEqual((root/installer.BACKUP).read_bytes(),BASELINE.encode('utf-8'))
            self.assertEqual((root/'ai_study_assistant.py').read_text(encoding='utf-8'),'untouched')
            self.assertFalse(list(root.glob('.v73_*.tmp')))

    def test_windows_crlf_utf8(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.stage(root,'\r\n')
            self.assertTrue(installer.install(root))
            raw=(root/installer.TARGET).read_bytes()
            self.assertIn(b'\r\n',raw);self.assertNotIn(b'\r\r\n',raw)
            ast.parse(raw.decode('utf-8'))
            self.assertFalse(installer.install(root))

    def test_missing_dependency_backup_collision_no_modification(self):
        for missing in (installer.HELPER,installer.SQL,'study_organizer_v72.py'):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);self.stage(root)
                before=(root/installer.TARGET).read_bytes()
                (root/missing).unlink()
                with self.assertRaises(installer.InstallationError):installer.install(root)
                self.assertEqual((root/installer.TARGET).read_bytes(),before)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.stage(root)
            original=(root/installer.TARGET).read_bytes()
            (root/installer.BACKUP).write_text('old backup',encoding='utf-8')
            with self.assertRaises(installer.InstallationError):installer.install(root)
            self.assertEqual((root/installer.TARGET).read_bytes(),original)

    def test_sql_private_and_no_note_deletion(self):
        sql=(HERE/installer.SQL).read_text(encoding='utf-8')
        self.assertIn('FOREIGN KEY (collection_id, user_id)',sql)
        self.assertIn('ON DELETE CASCADE',sql)
        self.assertIn('ENABLE ROW LEVEL SECURITY',sql)
        self.assertIn('REVOKE ALL',sql)
        for phrase in ('DROP TABLE','DELETE FROM public.notes','ALTER TABLE public.notes','CREATE POLICY'):
            self.assertNotIn(phrase,sql)

class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.db=DB();self.bot=old.FakeBot()
        self.types=types.SimpleNamespace(InlineKeyboardButton=old.FakeButton,InlineKeyboardMarkup=old.FakeInline)
        col.register_study_collections_v73_handlers(self.bot,self.db,load_note,self.types)

    def created(self,name='Biology'):
        return col.create_collection(self.db,42,name)['id']

    def test_register_commands_and_callback(self):
        for command in ('v73_collections','v73_create','v73_rename','v73_delete'):
            self.assertIn(command,self.bot.handlers)
        self.assertIn('v73_callback',self.bot.callbacks)
        self.assertEqual(col.note_collection_keyboard(self.types,1).rows[0][0].callback_data,'v73:p:1')
        self.assertIsNone(col.note_collection_keyboard(self.types,-1))
        self.assertTrue(col.CB.fullmatch('v73:list:0'))

    def test_create_rename_id_and_duplicate(self):
        ident=self.created('தமிழ் பாடம்')
        self.assertEqual(self.db.tables[col.COLLECTIONS][0]['name'],'தமிழ் பாடம்')
        col.rename_collection(self.db,42,ident,'Science')
        self.assertEqual(col.get_collection(self.db,42,ident)['name'],'Science')
        with self.assertRaises(RuntimeError):self.created('science')
        with self.assertRaises(ValueError):col.rename_collection(self.db,99,ident,'Oops')

    def test_create_name_invalid_and_limits(self):
        for name in ('',' ', 'x'*61, '\x00'):
            with self.assertRaises(ValueError):col.create_collection(self.db,42,name)
        for idx in range(30):col.create_collection(self.db,42,f'Folder {idx}')
        with self.assertRaises(ValueError):col.create_collection(self.db,42,'Overflow')
        self.assertEqual(len(col.list_collections(self.db,42)),30)

    def test_private_only_no_reads_in_group(self):
        self.bot.handlers['v73_collections'](old.message(42,-100,'group','/collections'))
        self.bot.handlers['v73_create'](old.message(42,-100,'group','/collectioncreate HI'))
        self.bot.handlers['v73_delete'](old.message(42,-100,'group','/collectiondelete 1'))
        self.bot.callbacks['v73_callback'](old.callback('v73:list:0',42,-100,'group'))
        self.assertEqual(self.db.calls,[])

    def test_collection_owner(self):
        ident=self.created()
        self.assertIsNone(col.get_collection(self.db,99,ident))
        with self.assertRaises(ValueError):col.delete_collection(self.db,99,ident)
        self.assertEqual(len(self.db.tables[col.COLLECTIONS]),1)

    def test_cross_owner_or_non_ai_notes_cannot_be_added(self):
        cid=self.created()
        for nid in (3,4):
            with self.assertRaises(ValueError):col.add_note(self.db,42,cid,nid,load_note)
        self.assertEqual(self.db.tables[col.ITEMS],[])
        with self.assertRaises(ValueError):col.add_note(self.db,99,cid,3,load_note)

    def test_add_remove_duplicate_and_no_note_changes(self):
        cid=self.created()
        self.assertTrue(col.add_note(self.db,42,cid,1,load_note))
        self.assertFalse(col.add_note(self.db,42,cid,1,load_note))
        self.assertEqual(len(self.db.tables[col.ITEMS]),1)
        col.remove_note(self.db,42,cid,1,load_note)
        self.assertEqual(self.db.tables[col.ITEMS],[])
        self.assertEqual(len(self.db.tables['notes']),4)

    def test_membership_limit(self):
        cid=self.created()
        self.db.tables[col.ITEMS]=[{'user_id':42,'collection_id':cid,'note_id':i} for i in range(10,110)]
        with self.assertRaises(ValueError):col.add_note(self.db,42,cid,1,load_note)

    def test_collection_browse_checks_note_owner_again(self):
        cid=self.created()
        self.db.tables[col.ITEMS]=[{'user_id':42,'collection_id':cid,'note_id':i} for i in (3,4,1)]
        col._show_collection(self.bot,self.db,self.types,42,42,cid,load_note)
        kb=self.bot.sent[-1][2]['reply_markup']
        callbacks=[button.callback_data for row in kb.rows for button in row]
        self.assertIn('v66:n:1',callbacks)
        self.assertNotIn('v66:n:3',callbacks)
        self.assertNotIn('v66:n:4',callbacks)

    def test_list_scopes_telegram_user_id_and_shows_ids(self):
        cid=self.created()
        self.bot.handlers['v73_collections'](old.message(42,42,'private','/collections'))
        text=self.bot.sent[-1][1]
        self.assertIn(f'#{cid} — Biology',text)
        self.assertNotIn('Secret',text)
        self.assertIn(('user_id',42),self.db.calls[-1][2])

    def test_callback_add_pick_remove(self):
        cid=self.created()
        cb=self.bot.callbacks['v73_callback']
        cb(old.callback('v73:p:1'))
        self.assertIn(f'v73:a:{cid}:1',[b.callback_data for row in self.bot.sent[-1][2]['reply_markup'].rows for b in row])
        cb(old.callback(f'v73:a:{cid}:1'))
        self.assertEqual(self.db.tables[col.ITEMS][-1]['note_id'],1)
        cb(old.callback(f'v73:r:{cid}:1'))
        self.assertEqual(self.db.tables[col.ITEMS],[])

    def test_old_callback_for_another_student_cannot_write(self):
        cid=self.created()
        self.bot.callbacks['v73_callback'](old.callback(f'v73:a:{cid}:3'))
        self.assertEqual(self.db.tables[col.ITEMS],[])

    def test_commands_create_rename_delete_confirmation(self):
        self.bot.handlers['v73_create'](old.message(text='/collectioncreate Biology'))
        self.assertEqual(len(self.db.tables[col.COLLECTIONS]),1)
        cid=self.db.tables[col.COLLECTIONS][0]['id']
        self.bot.handlers['v73_rename'](old.message(text=f'/collectionrename {cid} Physics'))
        self.assertEqual(self.db.tables[col.COLLECTIONS][0]['name'],'Physics')
        self.bot.handlers['v73_delete'](old.message(text=f'/collectiondelete {cid}'))
        self.assertEqual(len(self.db.tables[col.COLLECTIONS]),1)
        buttons=[b.callback_data for row in self.bot.sent[-1][2]['reply_markup'].rows for b in row]
        self.assertIn(f'v73:y:{cid}',buttons)
        self.bot.callbacks['v73_callback'](old.callback(f'v73:y:{cid}'))
        self.assertEqual(self.db.tables[col.COLLECTIONS],[])

    def test_delete_leaves_actual_notes(self):
        cid=self.created();col.add_note(self.db,42,cid,1,load_note)
        col.delete_collection(self.db,42,cid)
        self.assertEqual(self.db.tables[col.ITEMS],[])
        self.assertEqual(len(self.db.tables['notes']),4)

    def test_callbacks_invalid_and_unauthorized(self):
        self.assertFalse(col.CB.fullmatch('v73:c:-1'))
        self.assertFalse(col.CB.fullmatch('v73:a:1:2:3'))
        self.assertFalse(col.CB.fullmatch('v73:c:99999999999999999999'))
        self.assertFalse(col.CB.fullmatch('v73:c:99999999999999999999'))
        for value in (True,None,-1,10**18):
            with self.assertRaises(ValueError):col._id(value)

    def test_friendly_database_error_and_no_leak(self):
        self.db.fail=True
        self.bot.handlers['v73_collections'](old.message(text='/collections'))
        self.assertIn('unavailable',self.bot.sent[-1][1].lower())
        self.assertNotIn('Disconnected',self.bot.sent[-1][1])

if __name__=='__main__':unittest.main()
