"""V7.6 offline tests; no secrets, Supabase requests or Telegram network."""
import ast
import tempfile
import types
import unittest
from pathlib import Path

import INSTALL_V7_6 as installer
import material_filters_v76 as v76
import material_library_v75 as v75

FIXTURE = Path(__file__).with_name('FIXTURE_V7_5_MATERIAL_LIBRARY.txt').read_text(encoding='utf-8')


class FakeButton:
    def __init__(self, text, callback_data=None):
        self.text = text
        self.callback_data = callback_data


class FakeMarkup:
    def __init__(self, **kwargs):
        self.buttons = []
    def row(self, *buttons):
        self.buttons.extend(buttons)
    def add(self, *buttons):
        self.buttons.extend(buttons)


TYPES = types.SimpleNamespace(InlineKeyboardMarkup=FakeMarkup, InlineKeyboardButton=FakeButton)


class Bot:
    def __init__(self):
        self.handlers = []
        self.callbacks = []
        self.messages = []
    def message_handler(self, **opts):
        def dec(fn):
            self.handlers.append((opts, fn))
            return fn
        return dec
    def callback_query_handler(self, **opts):
        def dec(fn):
            self.callbacks.append((opts, fn))
            return fn
        return dec
    def send_message(self, cid, text, reply_markup=None):
        self.messages.append((cid, text, reply_markup))
    def answer_callback_query(self, cid):
        pass
    def cmd(self, name, args='', user=42, chat_type='private'):
        message = types.SimpleNamespace(chat=types.SimpleNamespace(id=user, type=chat_type),
                    from_user=types.SimpleNamespace(id=user),
                    text='/' + name + ((' ' + args) if args else ''))
        for spec, fn in self.handlers:
            if name in spec.get('commands', []):
                return fn(message)
        raise AssertionError('No handler for ' + name)
    def click(self, data, user=42, chat_type='private'):
        callback = types.SimpleNamespace(id='callback', data=data,
              from_user=types.SimpleNamespace(id=user),
              message=types.SimpleNamespace(chat=types.SimpleNamespace(id=user, type=chat_type)))
        for spec, fn in self.callbacks:
            if spec.get('func', lambda _: False)(callback):
                return fn(callback)
        raise AssertionError('No callback for ' + data)
    @property
    def text(self):
        return self.messages[-1][1]
    @property
    def buttons(self):
        markup = self.messages[-1][2]
        return getattr(markup, 'buttons', []) if markup else []


class Store:
    def __init__(self):
        self.rows = [
            {'id': 1, 'user_id': 42, 'title': 'Photosynthesis', 'file_name': 'plants.pdf',
             'file_type': 'pdf', 'subject_id': 5, 'extracted_chars': 810},
            {'id': 2, 'user_id': 42, 'title': 'கணிதம்', 'file_name': 'algebra.docx',
             'file_type': 'docx', 'subject_id': 8, 'extracted_chars': 700},
            {'id': 3, 'user_id': 42, 'title': 'Python', 'file_name': 'code.txt',
             'file_type': 'txt', 'subject_id': None, 'extracted_chars': 450},
            {'id': 4, 'user_id': 42, 'title': 'Arabic لغة', 'file_name': 'arabic.txt',
             'file_type': 'txt', 'subject_id': 5, 'extracted_chars': 300},
            {'id': 999, 'user_id': 99, 'title': 'Private', 'file_name': 'secret.pdf',
             'file_type': 'pdf', 'subject_id': 1, 'extracted_chars': 9999},
        ]
        self.queries = []
        self.fail = False
        self.return_foreign = False
    def list(self, uid, limit=100):
        self.queries.append((uid, limit))
        if self.fail:
            raise RuntimeError('db secret error')
        if self.return_foreign:
            return list(self.rows)
        return [r for r in self.rows if r['user_id'] == uid][:limit]


class InstallerTests(unittest.TestCase):
    def test_patch_only_two_anchors_and_idempotent(self):
        patched, changed = installer.patch_code(FIXTURE)
        self.assertTrue(changed)
        ast.parse(patched)
        self.assertIn('🧰 Filters & Stats', patched)
        self.assertIn('register_material_filter_handlers(', patched)
        self.assertIn("f'v75:open:{material_id}'", patched)  # original preview routing preserved
        self.assertEqual(installer.patch_code(patched), (patched, False))
    def test_v75_library_opens_v76_filters_in_live_registration(self):
        patched, _ = installer.patch_code(FIXTURE)
        namespace = {'__name__': 'v75_integration_fixture'}
        exec(compile(patched, 'material_library_v75.py', 'exec'), namespace)
        bot = Bot()
        store = Store()
        state = {}
        namespace['register_material_library_handlers'](
            bot, lambda chat_id: None, state,
            types_module=TYPES, list_fn=store.list,
            get_fn=lambda user_id, mid: next((r for r in store.rows if r['id']==mid and r['user_id']==user_id), None),
            delete_fn=lambda uid, mid: True
        )
        bot.cmd('materiallibrary')
        self.assertIn('v76:menu', [b.callback_data for b in bot.buttons])
        bot.click('v76:menu')
        self.assertIn('Study Materials Filters', bot.text)
        bot.cmd('materialtype', 'txt')
        self.assertIn('2 matching', bot.text)
        bot.click('v75:open:3')
        self.assertIn('Python', bot.text)

    def test_partial_patch_refused(self):
        patched, _ = installer.patch_code(FIXTURE)
        with self.assertRaises(installer.InstallationError):
            installer.patch_code(patched.replace(installer.MENU_INSERT.strip(), '# removed', 1))
    def test_unknown_version_rejected(self):
        with self.assertRaises(installer.InstallationError):
            installer.patch_code('print("hello")')
    def test_backup_and_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            raw = FIXTURE.encode('utf-8')
            (root / installer.TARGET).write_bytes(raw)
            (root / installer.HELPER).write_bytes(Path(v76.__file__).read_bytes())
            self.assertTrue(installer.install(root))
            self.assertEqual((root / installer.BACKUP).read_bytes(), raw)
            before = (root / installer.TARGET).read_bytes()
            self.assertFalse(installer.install(root))
            self.assertEqual((root / installer.TARGET).read_bytes(), before)
    def test_crlf_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            raw = FIXTURE.replace('\n', '\r\n').encode('utf-8')
            (root / installer.TARGET).write_bytes(raw)
            (root / installer.HELPER).write_bytes(Path(v76.__file__).read_bytes())
            self.assertTrue(installer.install(root))
            self.assertEqual((root / installer.BACKUP).read_bytes(), raw)
            self.assertIn(b'\r\n', (root / installer.TARGET).read_bytes())
            self.assertNotIn(b'\r\r\n', (root / installer.TARGET).read_bytes())
    def test_missing_helper_refuses_and_does_not_modify(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / installer.TARGET).write_text(FIXTURE, encoding='utf-8')
            with self.assertRaises(installer.InstallationError):
                installer.install(root)
            self.assertFalse((root / installer.BACKUP).exists())
            self.assertEqual((root / installer.TARGET).read_text(encoding='utf-8'), FIXTURE)
    def test_preexisting_backup_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / installer.TARGET).write_text(FIXTURE, encoding='utf-8')
            (root / installer.HELPER).write_bytes(Path(v76.__file__).read_bytes())
            (root / installer.BACKUP).write_text('existing user backup', encoding='utf-8')
            with self.assertRaises(installer.InstallationError):
                installer.install(root)
            self.assertEqual((root / installer.BACKUP).read_text(), 'existing user backup')
    def test_invalid_helper_syntax_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / installer.TARGET).write_text(FIXTURE, encoding='utf-8')
            (root / installer.HELPER).write_text('def broken(:', encoding='utf-8')
            with self.assertRaises(SyntaxError):
                installer.install(root)
            self.assertFalse((root / installer.BACKUP).exists())


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.store = Store()
        self.bot = Bot()
        self.material_state = {42: {'phase': 'upload'}}
        self.menu_calls = []
        self.library_calls = []
        v76.register_material_filter_handlers(self.bot, TYPES, self.store.list,
                    self.material_state, self.menu_calls.append,
                    lambda cid, uid, *args: self.library_calls.append((cid, uid)))
    def test_menu_commands(self):
        self.bot.cmd('materialfilters')
        self.assertIn('Study Materials Filters', self.bot.text)
        self.assertNotIn(42, self.material_state)
        self.assertIn('v76:t:pdf:0', [b.callback_data for b in self.bot.buttons])
    def test_library_stats_by_type_and_subject(self):
        self.bot.cmd('materialstats')
        self.assertIn('PDF: 1', self.bot.text)
        self.assertIn('TXT: 2', self.bot.text)
        self.assertIn('DOCX: 1', self.bot.text)
        self.assertIn('No Subject: 1', self.bot.text)
        self.assertIn('2,260', self.bot.text)
        self.assertNotIn('Private', self.bot.text)
    def test_type_filter(self):
        self.bot.cmd('materialtype', 'pdf')
        self.assertIn('1 matching', self.bot.text)
        self.assertIn('Photosynthesis', [b.text for b in self.bot.buttons][0])
        self.assertNotIn('Private', repr(self.bot.buttons))
    def test_text_and_unicode_titles(self):
        self.bot.cmd('materialtype', 'docx')
        self.assertTrue(any('கணிதம்' in b.text for b in self.bot.buttons))
        self.bot.cmd('materialtype', 'txt')
        self.assertTrue(any('لغة' in b.text for b in self.bot.buttons))
    def test_type_validation_no_database_call(self):
        self.bot.cmd('materialtype', 'exe')
        self.assertIn('Usage', self.bot.text)
        self.assertEqual(self.store.queries, [])
    def test_all_returns_original_v75_library(self):
        self.bot.cmd('materialtype', 'all')
        self.assertEqual(self.library_calls, [(42, 42)])
    def test_subject_filter(self):
        self.bot.cmd('materialsubject', '5')
        self.assertIn('2 matching', self.bot.text)
        self.assertIn('Subject #5', self.bot.text)
    def test_subject_none(self):
        self.bot.cmd('materialsubject', 'none')
        self.assertIn('1 matching', self.bot.text)
        self.assertIn('No Subject', self.bot.text)
    def test_subject_browse(self):
        self.bot.cmd('materialsubject')
        self.assertIn('Subjects in your most recent', self.bot.text)
        self.assertIn('v76:s:5:0', [b.callback_data for b in self.bot.buttons])
    def test_subject_bad_id_not_queried(self):
        self.bot.cmd('materialsubject', '-8')
        self.assertIn('Usage', self.bot.text)
        self.assertEqual(self.store.queries, [])
    def test_subject_callback_select(self):
        self.bot.click('v76:s:none:0')
        self.assertIn('No Subject', self.bot.text)
    def test_type_callback_select(self):
        self.bot.click('v76:t:pdf:0')
        self.assertIn('PDF', self.bot.text)
    def test_navigation_callbacks(self):
        self.bot.click('v76:menu')
        self.bot.click('v76:subjects')
        self.bot.click('v76:stats')
        self.bot.click('v76:all')
        self.bot.click('v76:home')
        self.assertEqual(self.library_calls, [(42,42)])
        self.assertEqual(self.menu_calls, [42])
    def test_group_denied_before_db_query(self):
        self.bot.cmd('materialstats', chat_type='group')
        self.bot.click('v76:t:pdf:0', chat_type='group')
        self.assertIn('private', self.bot.text)
        self.assertEqual(self.store.queries, [])
    def test_cross_user_rows_not_displayed_even_with_faulty_backend(self):
        self.store.return_foreign = True
        self.bot.cmd('materialtype', 'pdf')
        self.assertIn('1 matching', self.bot.text)
        self.assertFalse(any('Private' in b.text for b in self.bot.buttons))
    def test_error_does_not_falsely_report_zero(self):
        self.store.fail = True
        self.bot.cmd('materialstats')
        self.assertIn('Cannot load', self.bot.text)
        self.assertNotIn('0 saved', self.bot.text)
    def test_invalid_callback_inputs_do_not_query(self):
        self.bot.click('v76:t:jpg:0')
        self.bot.click('v76:s:-1:0')
        self.bot.click('v76:t:pdf:-1')
        self.bot.click('v76:t:pdf:999')
        self.assertEqual(self.store.queries, [])
    def test_filters_work_with_pagination(self):
        for n in range(20):
            self.store.rows.append({'id': 100 + n, 'user_id': 42, 'title': f'Book {n}',
                'file_name':'file.txt','file_type':'txt', 'subject_id':None, 'extracted_chars':10})
        self.bot.cmd('materialtype','txt')
        self.assertIn('Page 1/4', self.bot.text)
        self.assertIn('v76:t:txt:1', [b.callback_data for b in self.bot.buttons])
        self.bot.click('v76:t:txt:1')
        self.assertIn('Page 2/4', self.bot.text)
    def test_read_only_no_ai_usage(self):
        self.bot.cmd('materialstats')
        self.bot.cmd('materialtype','pdf')
        self.bot.cmd('materialsubject','5')
        self.assertTrue(all(uid == 42 and limit == 100 for uid,limit in self.store.queries))


class PureFunctionsTests(unittest.TestCase):
    def test_filter_type_extension_normalization(self):
        self.assertEqual(v76._type_of({'file_type': '.PDF'}), 'pdf')
        self.assertEqual(v76._type_of({'file_type': 'x'}), 'other')
    def test_filter_subject_none(self):
        self.assertEqual(v76._subject_of({'subject_id': '0'}), None)
        self.assertEqual(v76._subject_of({'subject_id': '9'}), 9)
    def test_reject_invalid_filter(self):
        with self.assertRaises(ValueError):
            v76.filter_materials([],kind='unsafe',selector='x')
    def test_bad_char_count_is_zero(self):
        result = v76.library_stats([{'file_type':'pdf', 'subject_id': None, 'extracted_chars':'bad'},
                                   {'file_type':'txt','subject_id': 3, 'extracted_chars':-10}])
        self.assertEqual(result['extracted_chars'],0)


if __name__ == '__main__':
    unittest.main()
