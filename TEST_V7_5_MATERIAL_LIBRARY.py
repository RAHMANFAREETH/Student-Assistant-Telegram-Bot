"""V7.5 offline tests (no Telegram token, Supabase access, or network required)."""
import ast
import tempfile
import types
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import INSTALL_V7_5 as installer
import material_library_v75 as lib

FIXTURE = Path(__file__).with_name('FIXTURE_STUDY_MATERIALS_PRE_V75.txt').read_text(encoding='utf-8')

class FakeButton:
    def __init__(self, label, callback_data=None):
        self.text = label
        self.callback_data = callback_data

class FakeMarkup:
    def __init__(self, row_width=2, **kwargs):
        self.buttons = []
    def add(self, *bs):
        self.buttons.extend(bs)
    def row(self, *bs):
        self.buttons.extend(bs)

TYPES = types.SimpleNamespace(InlineKeyboardButton=FakeButton, InlineKeyboardMarkup=FakeMarkup, KeyboardButton=FakeButton, ReplyKeyboardMarkup=FakeMarkup)

class FakeBot:
    def __init__(self):
        self.messages = []
        self.handlers = []
        self.callbacks = []
        self.acks = []
    def message_handler(self, **spec):
        def dec(fn):
            self.handlers.append((spec,fn))
            return fn
        return dec
    def callback_query_handler(self, **spec):
        def dec(fn):
            self.callbacks.append((spec,fn))
            return fn
        return dec
    def send_message(self, chatid, text, reply_markup=None):
        self.messages.append((chatid, text, reply_markup))
        return types.SimpleNamespace(message_id=len(self.messages))
    def answer_callback_query(self, id):
        self.acks.append(id)
    def cmd(self, command, sender=42, chat_type='private', args=''):
        m = types.SimpleNamespace(chat=types.SimpleNamespace(id=sender,type=chat_type),
                                  from_user=types.SimpleNamespace(id=sender),
                                  text='/' + command + ((' ' + args) if args else ''))
        for spec,fn in self.handlers:
            if command in spec.get('commands', []):
                return fn(m)
        raise AssertionError('command not found: '+command)
    def callback(self, data, sender=42, chat_type='private'):
        msg = types.SimpleNamespace(chat=types.SimpleNamespace(id=sender,type=chat_type))
        c = types.SimpleNamespace(id='ack',from_user=types.SimpleNamespace(id=sender),
                                  message=msg, data=data)
        for spec,fn in self.callbacks:
            if spec['func'](c):
                return fn(c)
        raise AssertionError('callback not found')
    @property
    def last(self):
        return self.messages[-1][1]
    @property
    def buttons(self):
        markup = self.messages[-1][2]
        return list(markup.buttons) if markup else []

class Store:
    def __init__(self):
        self.rows=[{'id':i,'user_id':42,'title':f'Biology {i}' if i%2 else f'கணிதம் {i}',
                    'file_name':f'material{i}.txt','file_type':'txt',
                    'extracted_text':'Photosynthesis ' + str(i) + ' ' + 'A'*1600}
                   for i in range(1,15)]
        self.rows.append({'id':999,'user_id':99,'title':'Secret', 'file_name':'secret.pdf',
                          'file_type':'pdf','extracted_text':'Private person information'})
        self.calls=[]
    def list(self,uid,limit=100):
        self.calls.append(('list',uid))
        return [r for r in self.rows if r['user_id']==uid][:limit]
    def get(self,uid,n):
        self.calls.append(('get',uid,n))
        return next((dict(r) for r in self.rows if r['user_id']==uid and r['id']==n),None)
    def delete(self,uid,n):
        if getattr(self,'fail_delete',False):
            raise RuntimeError('secret details')
        self.calls.append(('delete',uid,n))
        r=self.get(uid,n)
        if not r:return False
        self.rows=[x for x in self.rows if not (x['user_id']==uid and x['id']==n)]
        return True

class InstallerTests(unittest.TestCase):
    def test_patch_and_idempotence(self):
        updated,changed=installer.patch_code(FIXTURE)
        self.assertTrue(changed)
        ast.parse(updated)
        self.assertFalse(installer.patch_code(updated)[1])
        self.assertIn('register_material_library_handlers(bot, show_material_menu, material_state)',updated)
        self.assertIn('📚 Material Library',updated)
        self.assertIn('"🔎 Search Materials"',updated)
        self.assertIn('def material_document_handler(',updated)
    def test_install_backup_and_no_touch_second_time(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/installer.TARGET).write_bytes(FIXTURE.encode('utf-8'))
            (root/installer.HELPER).write_bytes(Path(lib.__file__).read_bytes())
            self.assertTrue(installer.install(root))
            self.assertFalse(installer.install(root))
            self.assertEqual((root/installer.BACKUP).read_bytes(),FIXTURE.encode('utf-8'))
    def test_crlf_compatible(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);raw=FIXTURE.replace('\n','\r\n').encode('utf-8')
            (root/installer.TARGET).write_bytes(raw)
            (root/installer.HELPER).write_bytes(Path(lib.__file__).read_bytes())
            self.assertTrue(installer.install(root))
            self.assertEqual((root/installer.BACKUP).read_bytes(),raw)
            self.assertIn(b'\r\n', (root/installer.TARGET).read_bytes())
            self.assertNotIn(b'\r\r\n', (root/installer.TARGET).read_bytes())
    def test_unfamiliar_code_refused(self):
        with self.assertRaises(installer.InstallationError):installer.patch_code('print("hi")')
    def test_partial_patch_refused(self):
        updated,_=installer.patch_code(FIXTURE)
        with self.assertRaises(installer.InstallationError):
            installer.patch_code(updated.replace(installer.REG.strip(),'# removed',1))
    def test_patched_study_materials_registration_and_menu(self):
        """Import patched Study Materials with mocked optional services."""
        patched,_=installer.patch_code(FIXTURE)
        telebot = types.ModuleType('telebot'); telebot.types=TYPES
        backend = types.ModuleType('telebot.handler_backends')
        backend.ContinueHandling=type('ContinueHandling',(),{})
        db=types.ModuleType('db');db.supabase=object()
        subj=types.ModuleType('subjects')
        subj.get_subjects=lambda uid:[]
        subj.get_subject_by_id=lambda uid,n:None
        subj.subject_display=lambda item:'Subject'
        docs=types.ModuleType('translation_documents')
        docs.SUPPORTED_DOCUMENT_EXTENSIONS={'.pdf','.docx','.txt'}
        docs.extract_text_from_document=lambda data,name:'hello'
        ocr=types.ModuleType('translation_ocr')
        ocr.extract_text_with_ocr=lambda data,name:'hello'
        ocr.get_ocr_api_key=lambda:None
        nav=types.ModuleType('navigation');nav.GLOBAL_BUTTONS=set()
        module=types.ModuleType('study_materials')
        modules={'telebot':telebot,'telebot.handler_backends':backend,'db':db,'subjects':subj,
                 'translation_documents':docs,'translation_ocr':ocr,'navigation':nav,
                 'study_materials':module}
        with patch.dict(sys.modules,modules):
            exec(compile(patched,'study_materials.py','exec'),module.__dict__)
            bot=FakeBot()
            module.register_study_material_handlers(bot,lambda *a:None)
            self.assertTrue(any('materiallibrary' in spec.get('commands',[]) for spec,fn in bot.handlers))
            bot.cmd('materials')
            self.assertIn('Study Materials',bot.last)
            self.assertIn('📚 Material Library',[b.text for b in bot.buttons])

    def test_missing_helper_and_backup_collision(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/installer.TARGET;p.write_text(FIXTURE,encoding='utf-8')
            with self.assertRaises(installer.InstallationError):installer.install(root)
            self.assertEqual(p.read_text(encoding='utf-8'),FIXTURE)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/installer.TARGET;p.write_text(FIXTURE,encoding='utf-8')
            (root/installer.HELPER).write_bytes(Path(lib.__file__).read_bytes())
            (root/installer.BACKUP).write_text('old backup',encoding='utf-8')
            with self.assertRaises(installer.InstallationError):installer.install(root)
            self.assertEqual(p.read_text(encoding='utf-8'),FIXTURE)

class FeatureTests(unittest.TestCase):
    def setUp(self):
        lib._PENDING.clear()
        lib._SEARCH.clear()
        self.db=Store()
        self.bot=FakeBot()
        self.ts=[1000.0]
        self.nav=[]
        self.state={42:{'step':'waiting_file'}}
        lib.register_material_library_handlers(self.bot,lambda c:self.nav.append(c),self.state,
             types_module=TYPES,list_fn=self.db.list,get_fn=self.db.get,delete_fn=self.db.delete,
             clock=lambda:self.ts[0])
    def test_library_pagination_and_navigation(self):
        self.bot.cmd('materiallibrary')
        self.assertIn('Page 1/3',self.bot.last)
        self.assertNotIn(42,self.state)
        self.assertEqual(len([b for b in self.bot.buttons if b.callback_data.startswith('v75:open:')]),6)
        self.bot.callback('v75:page:1')
        self.assertIn('Page 2/3',self.bot.last)
        self.bot.callback('v75:page:100')
        self.assertIn('Page 3/3',self.bot.last)
        self.bot.callback('v75:menu:0')
        self.assertEqual(self.nav,[42])
    def test_title_search_and_unicode(self):
        self.bot.cmd('materialfind',args='BiOlOgY')
        self.assertIn('Matches: 7',self.bot.last)
        self.assertTrue(any(b.callback_data == 'v75:search:1' for b in self.bot.buttons))
        self.bot.callback('v75:search:1')
        self.assertIn('Matches: 7',self.bot.last)
        self.assertEqual(len([b for b in self.bot.buttons if b.callback_data.startswith('v75:open:')]),1)
        self.bot.cmd('materialfind',args='கணிதம்')
        self.assertIn('Matches: 7',self.bot.last)
        self.bot.cmd('materialfind',args='nonexistent')
        self.assertIn('No matching',self.bot.last)
    def test_search_invalid_no_db_lookup(self):
        before=len(self.db.calls)
        self.bot.cmd('materialfind',args='x')
        self.assertIn('between 2 and 80',self.bot.last)
        self.assertEqual(len(self.db.calls),before)
    def test_metadata_search_does_not_leak_content(self):
        self.assertEqual(lib.search_metadata(self.db.rows,'Private person'),[])
        self.assertEqual(len(lib.search_metadata(self.db.rows,'material1')),6)
    def test_preview_truncated_and_original_file_notice(self):
        self.bot.cmd('materialpreview',args='1')
        self.assertIn('Preview shortened',self.bot.last)
        self.assertIn('not the original file',self.bot.last)
        self.assertLess(len(self.bot.last),1500)
    def test_search_expiry_does_not_use_stale_private_query(self):
        self.bot.cmd('materialfind',args='Biology')
        self.ts[0]+=610
        self.bot.callback('v75:search:1')
        self.assertIn('Search expired',self.bot.last)
    def test_unowned_material_inaccessible(self):
        self.bot.cmd('materialpreview',args='999')
        self.assertIn('not accessible',self.bot.last)
        self.bot.callback('v75:open:999')
        self.assertIn('not accessible',self.bot.last)
        self.bot.callback('v75:del:999')
        self.assertIn('not accessible',self.bot.last)
        self.assertNotIn(('delete',42,999),self.db.calls)
    def test_private_only_for_both_message_and_callback(self):
        count=len(self.db.calls)
        self.bot.cmd('materiallibrary',chat_type='group')
        self.bot.cmd('materialfind',chat_type='group',args='bio')
        self.bot.callback('v75:page:0',chat_type='group')
        self.assertEqual(len(self.db.calls),count)
        self.assertIn('private chat',self.bot.last)
    def test_delete_requires_private_confirmation_and_ownership(self):
        self.bot.callback('v75:del:1')
        buttons=self.bot.buttons
        token=[b.callback_data for b in buttons if b.callback_data.startswith('v75:yes:')][0]
        self.assertEqual(sum(c[0]=='delete' for c in self.db.calls),0)
        self.bot.callback(token,sender=99)
        self.assertEqual(sum(c[0]=='delete' for c in self.db.calls),0)
        self.bot.callback(token)
        self.assertIn('Material deleted',self.bot.last)
        self.assertEqual(sum(c[0]=='delete' for c in self.db.calls),1)
        self.bot.callback(token)
        self.assertIn('expired or invalid',self.bot.last)
    def test_delete_cancel_and_expiry(self):
        self.bot.callback('v75:del:1')
        token=[b.callback_data for b in self.bot.buttons if b.callback_data.startswith('v75:yes:')][0]
        self.bot.callback('v75:no:1')
        self.bot.callback(token)
        self.assertEqual(sum(c[0]=='delete' for c in self.db.calls),0)
        self.bot.callback('v75:del:1')
        token=[b.callback_data for b in self.bot.buttons if b.callback_data.startswith('v75:yes:')][0]
        self.ts[0]+=310
        self.bot.callback(token)
        self.assertEqual(sum(c[0]=='delete' for c in self.db.calls),0)
    def test_confirm_rechecks_ownership(self):
        self.bot.callback('v75:del:1')
        token=[b.callback_data for b in self.bot.buttons if b.callback_data.startswith('v75:yes:')][0]
        self.db.rows=[r for r in self.db.rows if r['id']!=1]
        self.bot.callback(token)
        self.assertIn('not accessible',self.bot.last)
        self.assertEqual(sum(c[0]=='delete' for c in self.db.calls),0)
    def test_delete_database_error_is_safe(self):
        self.bot.callback('v75:del:1')
        token=[b.callback_data for b in self.bot.buttons if b.callback_data.startswith('v75:yes:')][0]
        self.db.fail_delete=True
        self.bot.callback(token)
        self.assertNotIn('secret details',self.bot.last)
        self.assertIn('Could not delete',self.bot.last)
    def test_bad_callbacks_no_deletes(self):
        for val in ['v75:page:-4','v75:open:banana','v75:yes:1:fake','v75:del:-3','v75:extra:1']:
            self.bot.callback(val)
        self.assertEqual(sum(c[0]=='delete' for c in self.db.calls),0)
    def test_telegram_limits_and_formatting(self):
        data={'title':'x'*400,'file_type':'txt','extracted_text':'abc'*2000}
        self.assertLess(len(lib.preview_text(data)),1500)
        self.assertTrue(lib.clean_line('hello\nworld')=='hello world')
        self.assertEqual(lib._pagination(20,100),(3,4))
        self.assertEqual(lib._pagination(0,-2),(0,1))

if __name__=='__main__':
    unittest.main()
