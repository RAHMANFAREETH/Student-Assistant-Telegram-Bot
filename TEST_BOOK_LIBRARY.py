"""No network, Telegram key, Supabase key, or real documents needed."""
from __future__ import annotations
import os
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from book_library_store import (parse_caption, validate_metadata, format_size,
                                search_books, get_book, deactivate_book)
from INSTALL_BOOK_LIBRARY import integrate, transform
import book_library_bot as lib


class FakeMarkup:
    def __init__(self, **kwargs): self.buttons = []
    def add(self, *buttons): self.buttons.extend(buttons)


class FakeButton:
    def __init__(self, text, **kwargs): self.text, self.options = text, kwargs


class ContinueHandling:
    pass


class FakeBot:
    def __init__(self):
        self.message_handlers, self.callback_handlers, self.sent, self.copied, self.deleted = [], [], [], [], []
        self.fail_copy = False
    def message_handler(self, **params):
        def decorator(fn): self.message_handlers.append((params, fn)); return fn
        return decorator
    def callback_query_handler(self, **params):
        def decorator(fn): self.callback_handlers.append((params, fn)); return fn
        return decorator
    def get_message(self, command=None, content_type='text', message=None):
        for options, fn in self.message_handlers:
            if options.get('commands') and command not in options['commands']:
                continue
            if options.get('commands') is None and options.get('content_types') and content_type not in options['content_types']:
                continue
            if options.get('commands') is None and 'func' in options and not options['func'](message):
                continue
            return fn
        return None
    def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text, kwargs))
    def answer_callback_query(self, *args, **kwargs): pass
    def get_me(self): return types.SimpleNamespace(username='TestStudyBot')
    def copy_message(self, **kwargs):
        if self.fail_copy: raise RuntimeError('injected bot error')
        self.copied.append(kwargs)
        return types.SimpleNamespace(message_id=781)
    def delete_message(self, *args): self.deleted.append(args)


def fake_message(user=7, chat=None, kind='private', text=None, caption=None,
                 file_name='book.pdf', file_size=1234):
    return types.SimpleNamespace(from_user=types.SimpleNamespace(id=user),
            chat=types.SimpleNamespace(id=chat if chat is not None else user, type=kind),
            text=text, caption=caption, message_id=81,
            document=types.SimpleNamespace(file_name=file_name, file_size=file_size))


class SupabaseRequest:
    def __init__(self, data): self.data=data; self.calls=[]
    def select(self,*args): self.calls.append(('select',args));return self
    def eq(self,*args): self.calls.append(('eq',args));return self
    def limit(self,*args):self.calls.append(('limit',args));return self
    def order(self,*args,**kwargs):self.calls.append(('order',args));return self
    def update(self,*args):self.calls.append(('update',args));return self
    def execute(self):return types.SimpleNamespace(data=self.data)

class FakeDb:
    def __init__(self, data): self.query=SupabaseRequest(data);self.rpc_calls=[]
    def rpc(self,name,params):self.rpc_calls.append((name,params));return self.query
    def table(self,name):self.table_name=name;return self.query


class StoreTests(unittest.TestCase):
    def test_caption(self): self.assertEqual(parse_caption(' Ihya | Al Ghazali | Arabic '),('Ihya','Al Ghazali','Arabic'))
    def test_caption_missing(self):
        with self.assertRaises(ValueError):parse_caption('Ihya - Ghazali')
    def test_caption_extra(self):
        with self.assertRaises(ValueError):parse_caption('A | B | C | D')
    def test_caption_injection(self):
        with self.assertRaises(ValueError):parse_caption('A\nB | Author | English')
    def test_caption_bad_length(self):
        with self.assertRaises(ValueError):validate_metadata('X','Author','English')
    def test_size(self):self.assertEqual(format_size(1048576),'1.0 MB')
    def test_size_unknown(self):self.assertEqual(format_size('no'), 'Unknown size')
    def test_rpc_bind(self):
        db=FakeDb([{'id':'abc','active':True}])
        self.assertEqual(search_books("' OR 1=1 --",db=db), [{'id':'abc','active':True}])
        self.assertEqual(db.rpc_calls[0][1]['p_query'],"' OR 1=1 --")
    def test_rpc_empty(self):
        db=FakeDb([]);self.assertEqual(search_books('a',db=db),[]);self.assertEqual(db.rpc_calls,[])
    def test_uuid_rejected(self):
        db=FakeDb([]);self.assertIsNone(get_book('DROP TABLE',db=db))
    def test_get_book(self):
        db=FakeDb([{'id':str(__import__('uuid').uuid4()),'title':'T'}]);bookid=str(__import__('uuid').uuid4())
        self.assertEqual(get_book(bookid,db=db)['title'],'T')
    def test_deactivate_bad_uuid(self):
        with self.assertRaises(ValueError):deactivate_book('bad',db=FakeDb([]))
    def test_search_cap(self):
        db=FakeDb([]);search_books('Ihya',limit=500,db=db)
        self.assertEqual(db.rpc_calls[0][1]['p_limit'],10)
    def test_sql_permissions(self):
        sql=(HERE/'SQL_BOOK_LIBRARY.sql').read_text(encoding='utf8')
        self.assertIn('ENABLE ROW LEVEL SECURITY',sql)
        self.assertIn('REVOKE ALL ON public.book_library_items FROM PUBLIC, anon, authenticated',sql)
        self.assertIn('GRANT EXECUTE ON FUNCTION public.book_library_search',sql)
    def test_sql_no_provider_key(self):
        self.assertNotIn('SERVICE_ROLE_KEY=', (HERE/'SQL_BOOK_LIBRARY.sql').read_text(encoding='utf8'))


class BotTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{
            'BOOK_LIBRARY_ENABLED':'true','BOOK_LIBRARY_ADMIN_IDS':'7',
            'BOOK_LIBRARY_GROUP_IDS':'-1002020','BOOK_LIBRARY_CHANNEL_ID':'-1003000',
            'BOOK_LIBRARY_BOT_USERNAME':'TestStudyBot',
            'BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT':'false',
            'BOOK_LIBRARY_AUTO_GROUP_SEARCH':'true',
        })
        self.env.start()
        module=types.ModuleType('telebot')
        module.types=types.SimpleNamespace(InlineKeyboardMarkup=FakeMarkup, InlineKeyboardButton=FakeButton)
        backend=types.ModuleType('telebot.handler_backends')
        backend.ContinueHandling=ContinueHandling
        self.modules=patch.dict(sys.modules,{'telebot':module,'telebot.handler_backends':backend})
        self.modules.start()
        self.bot=FakeBot()
        self.handlers={}
        lib._pending.clear();lib._throttle.clear();lib._username=None
        lib.register_book_library_handlers(self.bot)
        for opts, fn in self.bot.message_handlers:
            for cmd in opts.get('commands',[]):self.handlers[cmd]=fn
            if fn.__name__ in ('admin_book_upload','group_search','private_search','library_menu'):
                self.handlers[fn.__name__]=fn
    def tearDown(self):self.modules.stop();self.env.stop()
    def test_book_command(self):
        with patch.object(lib,'search_books',return_value=[{'id':str(__import__('uuid').uuid4()),'title':'Ihya','author':'Ghazali','language':'Arabic','file_size':1048576}]):
            self.handlers['book'](fake_message(text='/book Ihya'))
        self.assertIn('Book results',self.bot.sent[-1][1]);self.assertIn('https://t.me/TestStudyBot?start=book_',self.bot.sent[-1][2]['reply_markup'].buttons[0].options['url'])
    def test_menu(self):
        self.handlers['library_menu'](fake_message(text=lib.BUTTON))
        self.assertIn('Book Library',self.bot.sent[-1][1])
    def test_private_search_callback(self):
        c=types.SimpleNamespace(id='cb',data='lib:search',from_user=types.SimpleNamespace(id=7),message=fake_message())
        self.bot.callback_handlers[0][1](c)
        self.assertTrue(lib._session_active(fake_message()))
    def test_group_search_allowlist(self):
        m=fake_message(user=7,chat=-1002020,kind='supergroup',text='Ihya')
        with patch.object(lib,'search_books',return_value=[]):
            r=self.handlers['group_search'](m)
        self.assertIsInstance(r,ContinueHandling)
    def test_group_search_found(self):
        m=fake_message(user=7,chat=-1002020,kind='supergroup',text='Ihya')
        with patch.object(lib,'search_books',return_value=[{'id':str(__import__('uuid').uuid4()),'title':'Ihya','author':'Ghazali','language':'Arabic','file_size':51200}]):
            self.handlers['group_search'](m)
        self.assertIn('Matching books',self.bot.sent[-1][1])
    def test_group_forbidden(self):
        self.handlers['book'](fake_message(user=7,chat=-10020,kind='supergroup',text='/book Ihya'))
        self.assertIn('not enabled in this group',self.bot.sent[-1][1])
    def test_admin_only(self):
        m=fake_message(user=8, caption='Ihya | Ghazali | Arabic')
        self.assertFalse(self.bot.message_handlers[-3][0].get('commands'))
        # Predicate on document handler excludes non-admin IDs.
        handler=next(opts for opts,fn in self.bot.message_handlers if fn.__name__=='admin_book_upload')
        self.assertFalse(handler['func'](m))
    def test_admin_document(self):
        with patch.object(lib,'add_book',return_value={'id':'a1'}):
            self.handlers['admin_book_upload'](fake_message(caption='Ihya | Ghazali | Arabic'))
        self.assertEqual(self.bot.copied[-1]['chat_id'],-1003000)
        self.assertIn('Added to Book Library',self.bot.sent[-1][1])
    def test_admin_store_fail_cleanup(self):
        with patch.object(lib,'add_book',side_effect=RuntimeError('DB fail')):
            self.handlers['admin_book_upload'](fake_message(caption='Ihya | Ghazali | Arabic'))
        self.assertEqual(self.bot.deleted[-1],(-1003000,781))
    def test_admin_copy_fail(self):
        self.bot.fail_copy=True
        self.handlers['admin_book_upload'](fake_message(caption='Ihya | Ghazali | Arabic'))
        self.assertIn('Could not store',self.bot.sent[-1][1])
    def test_admin_unsupported_type(self):
        self.handlers['admin_book_upload'](fake_message(caption='Ihya | Ghazali | Arabic',file_name='book.exe'))
        self.assertIn('Supported book files',self.bot.sent[-1][1])
    def test_admin_oversize(self):
        self.handlers['admin_book_upload'](fake_message(caption='Ihya | Ghazali | Arabic',file_size=90*1024*1024))
        self.assertIn('exceeds library upload limit',self.bot.sent[-1][1])
    def test_deeplink_delivery(self):
        bookid=__import__('uuid').uuid4()
        with patch.object(lib,'get_book',return_value={'title':'Ihya','author':'Ghazali','language':'Arabic','channel_id':-1003000,'message_id':456}):
            self.assertTrue(lib.handle_library_start(self.bot,fake_message(text='/start book_'+bookid.hex)))
        self.assertEqual(self.bot.copied[-1]['from_chat_id'],-1003000)
        self.assertEqual(self.bot.copied[-1]['chat_id'],7)
    def test_deeplink_invalid(self):
        self.assertTrue(lib.handle_library_start(self.bot,fake_message(text='/start book_NOTVALID')))
        self.assertIn('Invalid book link',self.bot.sent[-1][1])
    def test_normal_start_untouched(self):
        self.assertFalse(lib.handle_library_start(self.bot,fake_message(text='/start')))
    def test_deeplink_verified_gate(self):
        with patch.dict(os.environ,{'BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT':'true'}):
            with patch.object(lib,'_verified',return_value=False):
                self.assertTrue(lib.handle_library_start(self.bot,fake_message(text='/start book_'+'0'*32)))
        self.assertFalse(self.bot.copied)
        self.assertIn('verified adults',self.bot.sent[-1][1])
    def test_deeplink_in_group_ignored(self):
        m=fake_message(chat=-1002020,kind='group',text='/start book_'+'0'*32)
        self.assertFalse(lib.handle_library_start(self.bot,m))
    def test_remove_admin_only(self):
        self.handlers['bookremove'](fake_message(user=8,text='/bookremove a'))
        self.assertIn('administrator only',self.bot.sent[-1][1])
    def test_group_throttle(self):
        self.assertFalse(lib._cooldown(321,7,10));self.assertTrue(lib._cooldown(321,7,10))
    def test_group_message_filter_disabled_by_default(self):
        with patch.dict(os.environ,{'BOOK_LIBRARY_AUTO_GROUP_SEARCH':'false'}):
            m=fake_message(chat=-1002020,kind='group',text='Ihya')
            filt=next(o['func'] for o,fn in self.bot.message_handlers if fn.__name__=='group_search')
            self.assertFalse(filt(m))
    def test_disabled_gating(self):
        with patch.dict(os.environ,{'BOOK_LIBRARY_ENABLED':'false'}):
            self.handlers['book'](fake_message(text='/book Test'))
            self.assertIn('not enabled',self.bot.sent[-1][1])


class InstallerTests(unittest.TestCase):
    def setUp(self):
        # Minimal markers present in the V11 project; keeps test independent of real repo.
        self.main=("import os\n@bot.message_handler(commands=['start'])\n"
                   "def start(message):\n    show_main_menu(message.chat.id)\n"
                   "broadcast_service = register_broadcast_handlers(bot)\n"
                   "register_v11_handlers(bot)\n")
        self.nav=("MAIN_MENU_ROWS = [\n    (UI_FILES, UI_MORE),\n"
                  "    (UI_HELP, UI_LANGUAGE),\n]\n"
                  "GLOBAL_BUTTONS.add(\"📝 Text → PDF\")\n"
                  "ALL_NAVIGATION_BUTTONS = GLOBAL_BUTTONS\n")
    def test_transform_main(self):
        out=transform('main.py',self.main)
        self.assertIn('register_book_library_handlers(bot)',out)
        self.assertIn('if handle_library_start(bot, message):',out)
        self.assertLess(out.index('register_book_library_handlers(bot)'),out.index('register_v11_handlers(bot)'))
    def test_transform_nav(self):
        out=transform('navigation.py',self.nav)
        self.assertIn('("📚 Book Library",)',out)
        self.assertIn('GLOBAL_BUTTONS.add("📚 Book Library")',out)
    def test_idempotent(self):
        for name,original in [('main.py',self.main),('navigation.py',self.nav)]:
            self.assertEqual(transform(name,transform(name,original)),transform(name,original))
    def test_safe_check_and_apply(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'main.py').write_text(self.main,encoding='utf8');(root/'navigation.py').write_text(self.nav,encoding='utf8')
            before=(root/'main.py').read_bytes()
            self.assertEqual(len(integrate(root,apply=False,output=lambda x:None)),2)
            self.assertEqual((root/'main.py').read_bytes(),before)
            self.assertEqual(len(integrate(root,apply=True,output=lambda x:None)),2)
            self.assertEqual(integrate(root,apply=True,output=lambda x:None),[])
            self.assertEqual(len(list(root.glob('BOOK_LIBRARY_BACKUP_*'))),1)
    def test_crlf(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name,src in [('main.py',self.main),('navigation.py',self.nav)]:
                (root/name).write_bytes(src.replace('\n','\r\n').encode('utf8'))
            integrate(root,apply=True,output=lambda x:None)
            self.assertIn(b'\r\n', (root/'main.py').read_bytes())
            self.assertNotIn(b'\n\n', (root/'main.py').read_bytes())
    def test_reject_unknown_project(self):
        with self.assertRaises(ValueError):transform('main.py','print(1)')


if __name__=='__main__':unittest.main()
