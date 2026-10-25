"""V7.7 isolated tests: private exports, confirmation, ownership, installer."""
import ast
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import INSTALL_V7_7 as installer
import material_download_v77 as v77
import material_library_v75 as v75


class Button:
    def __init__(self, text, callback_data=None):
        self.text = text
        self.callback_data = callback_data

class Markup:
    def __init__(self, **kw):
        self.buttons = []
    def row(self, *buttons):
        self.buttons.extend(buttons)
    def add(self, *buttons):
        self.buttons.extend(buttons)

TYPES = types.SimpleNamespace(InlineKeyboardMarkup=Markup, InlineKeyboardButton=Button)

class FakeBot:
    def __init__(self):
        self.handlers, self.callbacks = [], []
        self.messages, self.documents = [], []
        self.raise_send = False
    def message_handler(self, **kw):
        def decorate(fn):
            self.handlers.append((kw, fn))
            return fn
        return decorate
    def callback_query_handler(self, **kw):
        def decorate(fn):
            self.callbacks.append((kw, fn))
            return fn
        return decorate
    def send_message(self, chat_id, text, reply_markup=None):
        self.messages.append((chat_id, text, reply_markup))
    def send_document(self, chat_id, document, caption=''):
        if self.raise_send:
            raise RuntimeError('socket error secret')
        self.documents.append((chat_id, document.name, document.getvalue(), caption))
    def answer_callback_query(self, callback_id):
        return None
    def cmd(self, name, argument='', uid=42, chat_type='private'):
        chat = types.SimpleNamespace(id=uid, type=chat_type)
        obj = types.SimpleNamespace(chat=chat, from_user=types.SimpleNamespace(id=uid),
                    text='/' + name + ((' ' + str(argument)) if argument != '' else ''))
        for kw, fn in self.handlers:
            if name in kw.get('commands', []):
                return fn(obj)
        raise AssertionError('Missing handler '+name)
    def click(self, data, uid=42, chat_type='private'):
        obj = types.SimpleNamespace(id='click', data=data, from_user=types.SimpleNamespace(id=uid),
            message=types.SimpleNamespace(chat=types.SimpleNamespace(id=uid, type=chat_type)))
        for kw, fn in self.callbacks:
            if kw.get('func', lambda c: False)(obj):
                return fn(obj)
        raise AssertionError('Missing callback '+data)
    def buttons(self):
        markup = self.messages[-1][2]
        return getattr(markup, 'buttons', [])
    def click_named(self, label, uid=42):
        for b in self.buttons():
            if b.text == label:
                return self.click(b.callback_data, uid=uid)
        raise AssertionError('Button missing '+label)
    @property
    def text(self):
        return self.messages[-1][1]

class Store:
    def __init__(self):
        self.data = {7: {'id': 7, 'user_id': 42, 'title': 'தமிழ் உயிரியல்',
                         'file_name': 'Biology عربي.pdf', 'file_type': 'pdf',
                         'extracted_text': 'ஒளிச்சேர்க்கை என்பது...\nمرحبا\nසිංහල\n'},
                     8: {'id': 8, 'user_id': 99, 'title': 'Hidden',
                         'extracted_text': 'secret'}}
        self.fail = False
        self.queries = []
    def get(self, uid, mid):
        self.queries.append((uid, mid))
        if self.fail:
            raise RuntimeError('database secret')
        return self.data.get(mid)

class InstallTests(unittest.TestCase):
    def setUp(self):
        self.source = Path(__file__).with_name('FIXTURE_V7_6_MATERIAL_LIBRARY.txt').read_text(encoding='utf-8')
    def test_patch_only_v76_and_idempotent(self):
        patched, changed = installer.patch_code(self.source)
        self.assertTrue(changed)
        self.assertIn('register_material_filter_handlers(', patched)
        self.assertIn('register_material_download_handlers(', patched)
        self.assertIn('v77:req:txt:', patched)
        self.assertEqual(installer.patch_code(patched), (patched, False))
    def test_refuse_unfamiliar_code(self):
        with self.assertRaises(installer.InstallationError):
            installer.patch_code('def unrelated(): pass')
    def test_refuse_half_installed_code(self):
        with self.assertRaises(installer.InstallationError):
            installer.patch_code(self.source.replace(installer.BUTTON_ANCHOR,
                  installer.BUTTON_INSERT+installer.BUTTON_ANCHOR))
    def test_install_preserves_backup_and_repeat_no_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            src_bytes=self.source.replace('\n','\r\n').encode('utf-8')
            (root/installer.TARGET).write_bytes(src_bytes)
            (root/installer.HELPER).write_text('def stub(): pass\n', encoding='utf-8')
            self.assertTrue(installer.install(root))
            result=(root/installer.TARGET).read_bytes()
            self.assertIn(b'\r\n', result)
            self.assertEqual((root/installer.BACKUP).read_bytes(), src_bytes)
            self.assertFalse(installer.install(root))
            self.assertEqual((root/installer.TARGET).read_bytes(), result)
    def test_no_helper_keeps_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/installer.TARGET).write_text(self.source, encoding='utf-8')
            with self.assertRaises(installer.InstallationError):
                installer.install(root)
            self.assertFalse((root/installer.BACKUP).exists())
    def test_existing_backup_no_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/installer.TARGET).write_text(self.source, encoding='utf-8')
            (root/installer.HELPER).write_text('def ok():pass\n', encoding='utf-8')
            (root/installer.BACKUP).write_bytes(b'old backup')
            with self.assertRaises(installer.InstallationError):
                installer.install(root)
            self.assertEqual((root/installer.BACKUP).read_bytes(), b'old backup')
            self.assertEqual((root/installer.TARGET).read_text(encoding='utf-8'), self.source)

class FunctionalTests(unittest.TestCase):
    def setUp(self):
        v77._PENDING.clear()
        self.bot=FakeBot()
        self.store=Store()
        self.state={42:{'phase':'whatever'}}
        self.time=[100.0]
        v77.register_material_download_handlers(self.bot, TYPES, self.store.get, self.state,
                                                 clock=lambda:self.time[0])
    def test_txt_unicode_and_explicit_disclaimer(self):
        name, data = v77.export_bytes(self.store.data[7], 7, 'txt')
        self.assertEqual(name, 'study_material_7_extracted.txt')
        for expected in ('ஒளிச்சேர்க்கை', 'مرحبا', 'සිංහල', 'NOT the original'):
            self.assertIn(expected, data.decode('utf-8'))
    def test_markdown_untrusted_title_escaped(self):
        row=dict(self.store.data[7], title='[test](https://example.test)')
        name, data=v77.export_bytes(row,7,'md')
        self.assertEqual(name, 'study_material_7_extracted.md')
        self.assertIn('\\[test\\]', data.decode('utf-8'))
    def test_no_text_explicit_failure(self):
        row=dict(self.store.data[7], extracted_text='  ')
        with self.assertRaisesRegex(ValueError, 'No extracted text'):
            v77.export_bytes(row,7,'txt')
    def test_reject_unknown_format_and_large_unicode(self):
        with self.assertRaises(ValueError):
            v77.export_bytes(self.store.data[7],7,'html')
        row=dict(self.store.data[7], extracted_text='தமிழ்' * 200000)
        with self.assertRaisesRegex(ValueError, '2 MB'):
            v77.export_bytes(row,7,'md')
    def test_invalid_ids(self):
        for invalid in ('0', '-1', 'abc', '١٢', '', '999999999999999999999999'):
            self.assertIsNone(v77.parse_material_id(invalid))
        self.assertEqual(v77.parse_material_id('7'),7)
    def test_requires_private_chat(self):
        self.bot.cmd('materialdownload','7',chat_type='group')
        self.assertIn('private', self.bot.text)
        self.assertEqual(self.store.queries, [])
    def test_missing_id_and_old_save_mode_released(self):
        self.bot.cmd('materialdownload')
        self.assertIn('Usage:', self.bot.text)
        self.bot.cmd('materialdownload', '7')
        self.assertNotIn(42, self.state)
        self.assertEqual(len(self.bot.documents),0)
    def test_foreign_material_denied(self):
        self.bot.cmd('materialdownload', '8')
        self.assertIn('not accessible',self.bot.text)
        self.assertEqual(self.bot.documents, [])
    def test_database_error_not_empty(self):
        self.store.fail=True
        self.bot.cmd('materialdownload','7')
        self.assertIn('Could not read', self.bot.text)
    def test_cancel_no_document(self):
        self.bot.cmd('materialdownload','7')
        self.bot.click_named('❌ Cancel')
        self.assertIn('cancelled',self.bot.text)
        self.assertEqual(self.bot.documents, [])
    def test_confirmation_txt_fresh_ownership_lookup(self):
        self.bot.cmd('materialdownload','7')
        self.assertEqual(len(self.store.queries),1)
        self.assertEqual(len(self.bot.documents),0)
        self.bot.click_named('✅ Download Extracted Text')
        self.assertEqual(len(self.store.queries),2)
        self.assertEqual(len(self.bot.documents),1)
        self.assertTrue(self.bot.documents[0][1].endswith('.txt'))
    def test_confirmation_markdown(self):
        self.bot.cmd('materialdownloadmd','7')
        self.bot.click_named('✅ Download Extracted Text')
        self.assertEqual(len(self.bot.documents),1)
        self.assertTrue(self.bot.documents[0][1].endswith('.md'))
    def test_expiry_prevents_send(self):
        self.bot.cmd('materialdownload','7')
        data = next(b.callback_data for b in self.bot.buttons() if b.text.startswith('✅'))
        self.time[0]+=301
        self.bot.click(data)
        self.assertEqual(self.bot.documents, [])
        self.assertIn('expired',self.bot.text)
    def test_one_time_token_prevents_replay(self):
        self.bot.cmd('materialdownload','7')
        data = next(b.callback_data for b in self.bot.buttons() if b.text.startswith('✅'))
        self.bot.click(data)
        self.bot.click(data)
        self.assertEqual(len(self.bot.documents),1)
        self.assertIn('no longer valid',self.bot.text)
    def test_borrowed_confirmation_rejected(self):
        self.bot.cmd('materialdownload','7')
        data=next(b.callback_data for b in self.bot.buttons() if b.text.startswith('✅'))
        self.bot.click(data,uid=99)
        self.assertEqual(self.bot.documents,[])
        self.bot.click(data,uid=42)
        self.assertEqual(len(self.bot.documents),1)
    def test_owner_revoked_between_request_and_send(self):
        self.bot.cmd('materialdownload','7')
        data=next(b.callback_data for b in self.bot.buttons() if b.text.startswith('✅'))
        self.store.data[7]['user_id']=99
        self.bot.click(data)
        self.assertEqual(self.bot.documents, [])
    def test_changed_text_must_revalidate_size(self):
        self.bot.cmd('materialdownload','7')
        data=next(b.callback_data for b in self.bot.buttons() if b.text.startswith('✅'))
        self.store.data[7]['extracted_text']='a' * (v77.MAX_BYTES+1)
        self.bot.click(data)
        self.assertEqual(self.bot.documents, [])
        self.assertIn('too large',self.bot.text)
    def test_network_send_error_fails_closed(self):
        self.bot.cmd('materialdownload','7')
        self.bot.raise_send=True
        self.bot.click_named('✅ Download Extracted Text')
        self.assertIn('Could not send', self.bot.text)
    def test_no_database_writes_no_ai_calls(self):
        self.bot.cmd('materialdownload','7')
        self.bot.click_named('✅ Download Extracted Text')
        self.assertEqual(self.store.queries,[(42,7),(42,7)])
    def test_callback_request_from_preview(self):
        self.bot.click('v77:req:txt:7')
        self.assertIn('extracted text',self.bot.text)
    def test_full_v76_integration_preview_has_buttons(self):
        source=Path(__file__).with_name('FIXTURE_V7_6_MATERIAL_LIBRARY.txt').read_text(encoding='utf-8')
        patched,_=installer.patch_code(source)
        scope={'__name__':'local_v77_fixture'}
        exec(compile(patched,'material_library_v75.py','exec'),scope)
        app=FakeBot()
        rows=[self.store.data[7]]
        scope['register_material_library_handlers'](app, lambda cid:None, {},
             types_module=TYPES, list_fn=lambda uid,limit=100: rows,
             get_fn=self.store.get, delete_fn=lambda uid, mid:True)
        app.cmd('materialpreview','7')
        self.assertIn('v77:req:txt:7',[b.callback_data for b in app.buttons()])
        app.click('v77:req:txt:7')
        self.assertIn('Export extracted text',app.text)

if __name__=='__main__':
    unittest.main()
