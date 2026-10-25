"""Focused V6.6 tests; no network, real credentials or Telegram calls."""
import ast
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
import INSTALL_V6_6 as installer


# Real V5.8 category layout from bundled project upgrade.
def ui_fixture():
    import zipfile
    archive = HERE / 'FIXTURE_V5_8_UI.txt'
    return archive.read_text(encoding='utf-8')


def main_fixture():
    return '''from ui_v57 import greeting, register_ui_v57_handlers
bot = None
show_main_menu = None
register_ui_v57_handlers(bot, show_main_menu)
register_achievements_v58_handlers(bot, show_main_menu)
register_ai_study_assistant_handlers(bot, show_main_menu)
'''


def nav_fixture():
    return '''GLOBAL_BUTTONS = set()
# V5.8 achievements navigation
LEGACY_MAIN_MENU = "⬅️ Main Menu"
NAVIGATION_BUTTONS = {"🏠 Main Menu"}
ALL_NAVIGATION_BUTTONS = GLOBAL_BUTTONS | NAVIGATION_BUTTONS
'''


class InstallerTests(unittest.TestCase):
    def test_patches_expected_versions_idempotently(self):
        for name, original in [('main.py', main_fixture()),
                               ('ui_v57.py', ui_fixture()),
                               ('navigation.py', nav_fixture())]:
            updated, changed = installer.PATCHERS[name](original)
            self.assertTrue(changed)
            ast.parse(updated)
            self.assertEqual(installer.PATCHERS[name](updated), (updated, False))

    def test_menu_preserves_legacy_features(self):
        result, _ = installer.patch_ui(ui_fixture())
        for button in ('"📝 Notes"', '"🧠 Due Reviews"', '"📚 Revision Planner"',
                       '"📚 My AI Study Library"', '"🧠 Practice Saved Cards"'):
            self.assertIn(button, result)
        self.assertIn('"🏆 Achievements"', result)

    def test_registers_before_legacy_handlers(self):
        result, _ = installer.patch_main(main_fixture())
        self.assertLess(result.index('register_revision_hub_v66_handlers(bot, show_main_menu)'),
                        result.index('register_ai_study_assistant_handlers(bot, show_main_menu)'))

    def test_navigation_buttons_yield_and_old_back_still_present(self):
        new, _ = installer.patch_navigation(nav_fixture())
        namespace = {}
        exec(new, namespace)
        self.assertIn('🏠 Main Menu', namespace['NAVIGATION_BUTTONS'])
        self.assertEqual(namespace['LEGACY_MAIN_MENU'], '⬅️ Main Menu')
        self.assertIn('📚 My AI Study Library', namespace['GLOBAL_BUTTONS'])

    def test_rejects_partial_or_unfamiliar_files(self):
        with self.assertRaises(ValueError):
            installer.patch_main(main_fixture().replace('register_achievements_v58_handlers', 'something_else'))
        patched, _ = installer.patch_main(main_fixture())
        with self.assertRaises(ValueError):
            installer.patch_main(patched.replace('register_revision_hub_v66_handlers(bot, show_main_menu)', 'x()'))
        with self.assertRaises(ValueError):
            installer.patch_navigation(nav_fixture().replace('# V5.8 achievements navigation', ''))

    def test_installer_backup_idempotence_utf8(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'revision_hub_v66.py').write_text('pass\n', encoding='utf-8')
            originals = {'main.py': main_fixture(), 'navigation.py': nav_fixture(),
                         'ui_v57.py': ui_fixture()}
            for key, value in originals.items():
                (root/key).write_text(value, encoding='utf-8')
            changed = installer.install(root)
            self.assertEqual(set(changed), set(originals))
            self.assertEqual(installer.install(root), [])
            for key, value in originals.items():
                self.assertEqual((root/(key+'.before_v66.bak')).read_text(encoding='utf-8'),value)
            self.assertFalse(list(root.glob('.v66_*.tmp')))

    def test_preflight_does_not_modify_files(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'revision_hub_v66.py').write_text('pass', encoding='utf-8')
            originals={'main.py':main_fixture(), 'navigation.py':nav_fixture(),
                       'ui_v57.py':ui_fixture().replace('CAT_PRACTICE','UNKNOWN')}
            for key, value in originals.items(): (root/key).write_text(value, encoding='utf-8')
            with self.assertRaises(ValueError): installer.install(root)
            for key,value in originals.items():
                self.assertEqual((root/key).read_text(encoding='utf-8'),value)
                self.assertFalse((root/(key+'.before_v66.bak')).exists())

    def test_windows_line_endings(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'revision_hub_v66.py').write_text('pass',encoding='utf-8')
            for name, src in [('main.py',main_fixture()),('ui_v57.py',ui_fixture()),('navigation.py',nav_fixture())]:
                (root/name).write_bytes(src.replace('\n','\r\n').encode('utf-8'))
            self.assertEqual(set(installer.install(root)),set(installer.TARGETS))
            for name in installer.TARGETS:
                raw=(root/name).read_bytes()
                self.assertIn(b'\r\n',raw)
                self.assertNotIn(b'\r\r\n',raw)
                ast.parse(raw.decode('utf-8'))


class FakeButton:
    def __init__(self, text, callback_data=None):
        self.text=text
        self.callback_data=callback_data
class FakeReply:
    def __init__(self,**kw): self.rows=[]
    def row(self,*buttons): self.rows.append(buttons)
class FakeInline(FakeReply):
    def add(self,*buttons): self.rows.append(buttons)
class FakeBot:
    def __init__(self): self.handlers={};self.callbacks={};self.sent=[];self.answered=[]
    def message_handler(self,**kw):
        def decorate(fn): self.handlers[fn.__name__]=fn;return fn
        return decorate
    def callback_query_handler(self,**kw):
        def decorate(fn): self.callbacks[fn.__name__]=fn;return fn
        return decorate
    def send_message(self,chatid,text,**kw): self.sent.append((chatid,text,kw))
    def answer_callback_query(self,ident,text=None,**kw): self.answered.append((ident,text,kw))


class Result:
    def __init__(self,data): self.data=data
class Query:
    def __init__(self,db,table):
        self.db=db;self.table=table;self.filters=[];self.limit_size=None;self.lo=None;self.hi=None;self.reverse=False
    def select(self,s):return self
    def eq(self,k,v):self.filters.append(('eq',k,v));return self
    def ilike(self,k,v):self.filters.append(('ilike',k,v));return self
    def lt(self,k,v):self.filters.append(('lt',k,v));return self
    def order(self,k,desc=False):self.key=k;self.reverse=desc;return self
    def limit(self,n):self.limit_size=n;return self
    def range(self,lo,hi):self.lo=lo;self.hi=hi;return self
    def execute(self):
        if self.db.fail: raise RuntimeError('private db connection failed: key not reported')
        self.db.calls.append((self.table,list(self.filters)))
        data=list(self.db.tables[self.table]);
        for op,k,v in self.filters:
            if op=='eq': data=[r for r in data if str(r.get(k))==str(v)]
            elif op=='ilike': data=[r for r in data if str(r.get(k,'')).lower().startswith(v[:-1].lower())]
            elif op=='lt': data=[r for r in data if int(r.get(k))<int(v)]
        if hasattr(self,'key'): data.sort(key=lambda r:r.get(self.key),reverse=self.reverse)
        if self.lo is not None: data=data[self.lo:self.hi+1]
        if self.limit_size is not None: data=data[:self.limit_size]
        return Result(data)
class FakeDB:
    def __init__(self):
        self.calls=[];self.fail=False
        self.tables={
          'notes':[
            {'id':1,'user_id':42,'title':'AI Study: தமிழ் ஒளிச்சேர்க்கை','content':'தாவரங்கள் சூரிய ஒளியைப் பயன்படுத்துகின்றன.','created_at':'2026-10-24'},
            {'id':2,'user_id':42,'title':'Personal Note','content':'private','created_at':'2026-10-24'},
            {'id':3,'user_id':99,'title':'AI Study: other user','content':'very private','created_at':'2026-10-24'},
          ],
          'flashcards':[
            {'id':11,'user_id':42,'question':'What is sun?','answer':'A star'},
            {'id':12,'user_id':42,'question':'கேள்வி: தாவரமா?','answer':'ஆம்'},
            {'id':13,'user_id':99,'question':'Someone secret?','answer':'secret'},
          ],
          'flashcard_reviews':[
            {'flashcard_id':11,'user_id':42,'repetitions':3,'review_count':4,'due_at':'2026-10-20T00:00:00+00:00'},
            {'flashcard_id':13,'user_id':99,'repetitions':8,'review_count':8,'due_at':'2026-10-25T00:00:00+00:00'}]
        }
    def table(self,name):return Query(self,name)


def load_module(db):
    fake_types=types.SimpleNamespace(KeyboardButton=FakeButton,InlineKeyboardButton=FakeButton,
                      ReplyKeyboardMarkup=FakeReply,InlineKeyboardMarkup=FakeInline)
    tel=types.ModuleType('telebot');tel.types=fake_types
    mod_db=types.ModuleType('db');mod_db.supabase=db
    safe=types.ModuleType('safe_utils');safe.split_telegram_text=lambda s,limit:[s[i:i+limit] for i in range(0,len(s),limit)]
    with patch.dict(sys.modules,{'telebot':tel,'db':mod_db,'safe_utils':safe}):
        spec=importlib.util.spec_from_file_location('revision_hub_v66',HERE/'revision_hub_v66.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


def message(uid=42, chatid=None, kind='private',text=''):
    chatid=uid if chatid is None else chatid
    return types.SimpleNamespace(chat=types.SimpleNamespace(id=chatid,type=kind),
                                 from_user=types.SimpleNamespace(id=uid),text=text)

def callback(data,uid=42,chatid=None,kind='private'):
    return types.SimpleNamespace(id='cb1',from_user=types.SimpleNamespace(id=uid),
              message=types.SimpleNamespace(chat=types.SimpleNamespace(type=kind,id=uid if chatid is None else chatid)),data=data)


class RevisionDataTests(unittest.TestCase):
    def setUp(self):self.db=FakeDB();self.mod=load_module(self.db)
    def test_fetch_ai_notes_only_by_owner_and_prefix(self):
        rows=self.mod.load_ai_notes(self.db,42)
        self.assertEqual([r['id'] for r in rows],[1])
        self.assertEqual(self.mod.load_ai_notes(self.db,99)[0]['id'],3)
        self.assertIsNone(self.mod.load_note(self.db,42,3))
        self.assertIsNone(self.mod.load_note(self.db,42,2))
    def test_card_owner_protected_on_read(self):
        self.assertIsNone(self.mod.load_card(self.db,42,13))
        self.assertEqual(self.mod.load_card(self.db,42,12)['answer'],'ஆம்')
    def test_latest_card_no_other_student(self):
        self.assertEqual(self.mod.latest_card(self.db,42)['id'],12)
        self.assertEqual(self.mod.latest_card(self.db,42,before=12)['id'],11)
        self.assertIsNone(self.mod.latest_card(self.db,42,before=11))
    def test_progress_scope_and_due(self):
        summary=self.mod.revision_summary(self.db,42,now=self.mod.datetime(2026,10,25,tzinfo=self.mod.timezone.utc))
        self.assertEqual(summary['cards'],2)
        self.assertEqual(summary['due'],2)
        self.assertEqual(summary['reviewed'],1)
        self.assertEqual(summary['strong'],1)
    def test_progress_missing_review_table_is_not_false_zero(self):
        self.db.fail=True
        with self.assertRaises(RuntimeError):self.mod.revision_summary(self.db,42)
    def test_progress_future_due(self):
        self.db.tables['flashcard_reviews'][0]['due_at']='2099-01-01T00:00:00Z'
        self.assertEqual(self.mod.revision_summary(self.db,42)['due'],1)
    def test_privacy_requires_private_chat(self):
        self.assertFalse(self.mod._private(message(42,-123,'group')))
        self.assertTrue(self.mod._private(message(42)))
    def test_split_large_notes(self):
        bot=FakeBot()
        self.mod._send_note(bot,42,{'title':'AI Study: Tamil','content':'அ'*9000})
        self.assertGreaterEqual(len(bot.sent),4)
        self.assertTrue(all(len(text)<=3800 for _,text,_ in bot.sent))


class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.db=FakeDB();self.mod=load_module(self.db)
        self.bot=FakeBot();self.mod.register_revision_hub_v66_handlers(self.bot,lambda *a:None)
    def send(self,name, uid=42, kind='private'):
        self.bot.handlers[name](message(uid,kind=kind))
        return self.bot.sent[-1][1]
    def test_all_five_features_registered(self):
        for name in ('revision_hub_menu','revision_notes','revision_cards','revision_progress','revision_reminders'):
            self.assertIn(name,self.bot.handlers)
    def test_guide_does_not_make_ai_calls_or_db_writes(self):
        self.send('revision_hub_menu')
        self.send('revision_reminders')
        self.assertEqual(self.db.calls,[])
        self.assertIn('does not create a reminder', self.bot.sent[-1][1])
    def test_private_note_list_buttons(self):
        self.send('revision_notes')
        markup=self.bot.sent[-1][2]['reply_markup']
        buttons=[b for row in markup.rows for b in row]
        self.assertEqual([b.callback_data for b in buttons],['v66:n:1'])
    def test_private_note_callback_content(self):
        self.bot.callbacks['revision_callback'](callback('v66:n:1'))
        self.assertIn('சூரிய', ''.join(m[1] for m in self.bot.sent))
    def test_other_user_note_callback_cannot_leak(self):
        self.bot.callbacks['revision_callback'](callback('v66:n:3'))
        self.assertFalse(any('very private' in m[1] for m in self.bot.sent))
        self.assertTrue(self.bot.answered[-1][2].get('show_alert'))
    def test_group_callback_denied_without_db_lookup(self):
        self.bot.callbacks['revision_callback'](callback('v66:n:1',uid=42,chatid=-123,kind='group'))
        self.assertEqual(self.db.calls,[])
        self.assertFalse(self.bot.sent)
    def test_telegram_user_mismatch_denied(self):
        self.bot.callbacks['revision_callback'](callback('v66:n:1',uid=99,chatid=42))
        self.assertEqual(self.db.calls,[])
    def test_reveal_and_next_card(self):
        self.send('revision_cards')
        self.assertIn('தாவரமா?',self.bot.sent[-1][1])
        self.bot.callbacks['revision_callback'](callback('v66:a:12'))
        self.assertIn('ஆம்',self.bot.sent[-1][1])
        buttons=[b for row in self.bot.sent[-1][2]['reply_markup'].rows for b in row]
        self.assertEqual(buttons[0].callback_data,'v66:p:11')
        self.bot.callbacks['revision_callback'](callback('v66:p:11'))
        self.assertIn('What is sun?',self.bot.sent[-1][1])
    def test_revealing_other_users_card_denied(self):
        self.bot.callbacks['revision_callback'](callback('v66:a:13'))
        self.assertNotIn('secret',''.join(m[1] for m in self.bot.sent))
        self.assertTrue(self.bot.answered[-1][2].get('show_alert'))
    def test_progress_error_no_silent_zero(self):
        self.db.fail=True
        answer=self.send('revision_progress')
        self.assertIn('unavailable',answer)
    def test_group_messages_denied_before_database(self):
        for name in ('revision_hub_menu','revision_notes','revision_cards','revision_progress','revision_reminders'):
            self.send(name,kind='group')
        self.assertEqual(self.db.calls,[])
    def test_no_unauthorized_write_method_in_module(self):
        content=(HERE/'revision_hub_v66.py').read_text(encoding='utf-8')
        self.assertNotIn('.insert(',content)
        self.assertNotIn('.update(',content)
        self.assertNotIn('.delete(',content)
        self.assertNotIn('.upsert(',content)


if __name__ == '__main__':unittest.main()
