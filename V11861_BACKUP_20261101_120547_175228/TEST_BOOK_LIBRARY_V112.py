"""Offline V11.2 tests. No Telegram token, Supabase connection or network needed."""
from __future__ import annotations
import os
import sys
import tempfile
import types
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import book_library_bot as lib
import book_library_v112_bot as new
import book_library_v112_store as store
from INSTALL_BOOK_LIBRARY_V112 import transform, integrate, MARKER
from TEST_BOOK_LIBRARY import FakeBot, FakeMarkup, FakeButton, ContinueHandling, fake_message

BID = str(uuid.uuid4())
BOOK = dict(id=BID, title='The Little Guide',author='Test Author', language='English',
            category='Mindset', isbn='9780306406157', cover_file_id='AgAC_photo-id',
            download_count=3,file_size=123000,active=True,added_at='2026-10-31T10:00:00Z')

class TestMarkup(FakeMarkup):
    def row(self, *buttons): self.buttons.extend(buttons)

class TestBot(FakeBot):
    def __init__(self):
        super().__init__()
        self.photos=[]; self.edits=[];self.answers=[]
    def send_photo(self, chat_id, photo, **kwargs):
        self.photos.append((chat_id,photo,kwargs))
    def edit_message_text(self, text, **kwargs):
        self.edits.append((text,kwargs))
    def answer_callback_query(self, id, text='', **kwargs):
        self.answers.append((id,text,kwargs))


class Query:
    def __init__(self, output): self.data=output;self.calls=[]
    def select(self,*a,**k): self.calls.append(('select',a,k));return self
    def eq(self,*a): self.calls.append(('eq',a));return self
    def update(self,*a): self.calls.append(('update',a));return self
    def upsert(self,*a,**k):self.calls.append(('upsert',a,k));return self
    def delete(self,*a):self.calls.append(('delete',a));return self
    def limit(self,*a):self.calls.append(('limit',a));return self
    def range(self,*a):self.calls.append(('range',a));return self
    def order(self,*a,**k):self.calls.append(('order',a,k));return self
    def execute(self):return types.SimpleNamespace(data=self.data)

class DB:
    def __init__(self, result):self.request=Query(result);self.calls=[]
    def table(self, name):self.calls.append(('table',name));return self.request
    def rpc(self, name, data):self.calls.append(('rpc',name,data));return self.request

class StoreTests(unittest.TestCase):
    def test_isbn10(self):self.assertEqual(store.normalize_isbn('0-306-40615-2'),'0306406152')
    def test_isbn13(self):self.assertEqual(store.normalize_isbn('978 0 306 40615 7'),'9780306406157')
    def test_invalid_check_digit(self):
        with self.assertRaises(ValueError):store.normalize_isbn('9780306406158')
    def test_invalid_isbn_length(self):
        with self.assertRaises(ValueError):store.normalize_isbn('1234')
    def test_isbn_unset(self):self.assertIsNone(store.normalize_isbn('-'))
    def test_caption_legacy(self):
        self.assertEqual(store.parse_extended_caption('Small Habits | Author | English'),
                         ('Small Habits','Author','English','General',None))
    def test_caption_category(self):
        self.assertEqual(store.parse_extended_caption('Small Habits | Author | English | Self Help')[3],'Self Help')
    def test_caption_full(self):
        self.assertEqual(store.parse_extended_caption('Book Name | Author | English | Learning | 9780306406157')[4],'9780306406157')
    def test_caption_newline_blocked(self):
        with self.assertRaises(ValueError):store.parse_extended_caption('Title | Author | English | Category\nX')
    def test_caption_trailing_fields_blocked(self):
        with self.assertRaises(ValueError):store.parse_extended_caption('Title | Author | English | A | B | C')
    def test_query_pagination_bounded(self):
        db=DB([dict(BOOK, id=str(uuid.uuid4())) for _ in range(6)])
        books,more=store.browse_books(query='small',page=2,db=db)
        self.assertEqual(len(books),5);self.assertTrue(more)
        self.assertEqual(db.calls[0][2]['p_offset'],10)
        self.assertEqual(db.calls[0][2]['p_limit'],6)
    def test_query_literal_parameters(self):
        db=DB([]);store.browse_books(query="' OR 1=1 --",db=db)
        self.assertEqual(db.calls[0][2]['p_query'],"' OR 1=1 --")
    def test_query_page_cap(self):
        with self.assertRaises(ValueError):store.browse_books(page=101,db=DB([]))
    def test_facets_validation(self):
        with self.assertRaises(ValueError):store.facets('evil',db=DB([]))
    def test_facets_rpc(self):
        db=DB([]);store.facets('language',db=db)
        self.assertEqual(db.calls[0][1], 'book_library_v112_facets')
    def test_get_details_rejects_bad_uuid(self):
        self.assertIsNone(store.get_details('bad-uuid', db=DB([])))
    def test_update_admin_metadata(self):
        db=DB([BOOK]);self.assertTrue(store.update_metadata(BID,title='Book Name',author='Author',language='English',category='Study',isbn='-',db=db))
        updates=[c for c in db.request.calls if c[0]=='update']
        self.assertIsNone(updates[0][1][0]['isbn'])
    def test_cover_store(self):
        db=DB([BOOK]);self.assertTrue(store.set_cover(BID,'Photo_id_123',db=db))
    def test_invalid_cover(self):
        with self.assertRaises(ValueError):store.set_cover(BID,'a\n',db=DB([]))
    def test_favorite_add(self):
        d=DB([])
        with patch.object(store,'get_details',return_value=BOOK),patch.object(store,'is_favorite',return_value=False):
            self.assertTrue(store.toggle_favorite(42,BID,db=d))
        self.assertIn('upsert', [c[0] for c in d.request.calls])
    def test_favorite_remove(self):
        d=DB([])
        with patch.object(store,'get_details',return_value=BOOK),patch.object(store,'is_favorite',return_value=True):
            self.assertFalse(store.toggle_favorite(42,BID,db=d))
        self.assertIn('delete',[c[0] for c in d.request.calls])
    def test_record_delivery_rpc(self):
        db=DB([]);store.record_delivery(BID,db=db)
        self.assertEqual(db.calls[0][1], 'book_library_v112_record_delivery')
        self.assertNotIn('user_id',db.calls[0][2])
    def test_sql_security(self):
        sql=(HERE/'SQL_BOOK_LIBRARY_V112.sql').read_text(encoding='utf8')
        self.assertIn('ENABLE ROW LEVEL SECURITY',sql)
        self.assertIn('REVOKE ALL ON public.book_library_favorites',sql)
        self.assertIn('SECURITY INVOKER',sql)
        self.assertIn('book_library_v112_record_delivery',sql)
        self.assertIn('GRANT EXECUTE',sql)
        self.assertNotIn('SERVICE_ROLE_KEY=',sql)


class BotTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{
            'BOOK_LIBRARY_ENABLED':'true','BOOK_LIBRARY_V112_ENABLED':'true',
            'BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT':'false','BOOK_LIBRARY_ALLOW_ALL_GROUPS':'true',
            'BOOK_LIBRARY_ADMIN_IDS':'7','BOOK_LIBRARY_CHANNEL_ID':'-1003000',
            'BOOK_LIBRARY_BOT_USERNAME':'TestStudyBot','BOOK_LIBRARY_AUTO_GROUP_SEARCH':'true'})
        self.env.start()
        fake_telebot=types.ModuleType('telebot')
        fake_telebot.types=types.SimpleNamespace(InlineKeyboardMarkup=TestMarkup,InlineKeyboardButton=FakeButton)
        fake_backend=types.ModuleType('telebot.handler_backends');fake_backend.ContinueHandling=ContinueHandling
        self.mocks=patch.dict(sys.modules,{'telebot':fake_telebot,'telebot.handler_backends':fake_backend})
        self.mocks.start()
        self.bot=TestBot();lib._username=None;lib._pending.clear();lib._throttle.clear()
        new._sessions.clear();new._covers.clear()
        lib.register_book_library_handlers(self.bot)
        self.handlers={}
        for opts,fn in self.bot.message_handlers:
            for command in opts.get('commands',[]):self.handlers[command]=fn
            self.handlers[fn.__name__]=fn
        self.callbacks={fn.__name__:fn for opts,fn in self.bot.callback_handlers}
    def tearDown(self):self.mocks.stop();self.env.stop()
    def _cb(self, data, *, user=7, chat=None, kind='private'):
        m=fake_message(user=user,chat=chat if chat is not None else user,kind=kind)
        m.message_id=202
        return types.SimpleNamespace(id='cb1',data=data,from_user=types.SimpleNamespace(id=user),message=m)

    def test_existing_menu_new_buttons(self):
        lib._menu(self.bot,fake_message())
        names=[b.text for b in self.bot.sent[-1][2]['reply_markup'].buttons]
        self.assertIn('🗂 Categories',names)
        self.assertIn('❤️ My Favorites',names)
    def test_public_group_search_paginates(self):
        data=[dict(BOOK,id=str(uuid.uuid4())) for i in range(5)]
        with patch.object(new,'browse_books',return_value=(data,True)):
            self.handlers['book'](fake_message(user=22,chat=-100700,kind='supergroup',text='/book Habits'))
        self.assertIn('Page 1',self.bot.sent[-1][1]);markup=self.bot.sent[-1][2]['reply_markup']
        self.assertTrue(any('Next' in b.text for b in markup.buttons))
    def test_group_automatic_search_uses_browse(self):
        with patch.object(new,'show_search',return_value=True) as f:
            result=self.handlers['group_search'](fake_message(user=22,chat=-100700,kind='group',text='Habits'))
        self.assertIsInstance(result,ContinueHandling)
        f.assert_called_once()
    def test_category_command(self):
        with patch.object(new,'browse_books',return_value=([BOOK],False)) as f:
            self.handlers['bookcat'](fake_message(user=22,chat=-100700,kind='supergroup',text='/bookcat Mindset'))
        self.assertEqual(f.call_args.kwargs['category'],'Mindset')
    def test_isbn_command_exact(self):
        with patch.object(new,'browse_books',return_value=([BOOK],False)) as f:
            self.handlers['bookisbn'](fake_message(text='/bookisbn 9780306406157'))
        self.assertEqual(f.call_args.kwargs['isbn'],'9780306406157')
    def test_category_facets(self):
        with patch.object(new,'facets',return_value=[{'value':'Mindset','book_count':2}]):
            self.handlers['bookcats'](fake_message(text='/bookcats'))
        self.assertIn('Choose a category',self.bot.sent[-1][1])
    def test_next_page_callback(self):
        with patch.object(new,'browse_books',return_value=([BOOK],True)):
            new.show_search(self.bot,7,'Mindset')
            token=next(iter(new._sessions))
            self.callbacks['library_v112_callback'](self._cb(f'lib2:pg:{token}:1'))
        self.assertEqual(len(self.bot.edits),1)
        self.assertIn('Page 2',self.bot.edits[0][0])
    def test_group_token_cannot_be_replayed_in_other_chat(self):
        token=new._save_session(-100700,{'kind':'browse'})
        self.callbacks['library_v112_callback'](self._cb(f'lib2:pg:{token}:1',chat=-100800,kind='supergroup'))
        self.assertIn('expired',self.bot.answers[-1][1].lower())
    def test_favorites_only_private(self):
        self.handlers['bookfavs'](fake_message(user=7,chat=-100100,kind='supergroup',text='/bookfavs'))
        self.assertIn('private',self.bot.sent[-1][1].lower())
    def test_fav_callback_spoof_blocked(self):
        self.callbacks['library_v112_callback'](self._cb('lib2:f:'+uuid.UUID(BID).hex,user=8,chat=7))
        self.assertIn('private',self.bot.answers[-1][1].lower())
    def test_favorite_toggle_private(self):
        with patch.object(new,'toggle_favorite',return_value=True) as t:
            self.handlers['bookfav'](fake_message(user=22,text='/bookfav '+BID))
        t.assert_called_once_with(22,BID)
        self.assertIn('Saved',self.bot.sent[-1][1])
    def test_cover_preview_private(self):
        with patch.object(new,'get_details',return_value=BOOK):
            self.assertTrue(new.handle_preview_start(self.bot,fake_message(text='/start preview_'+uuid.UUID(BID).hex)))
        self.assertEqual(self.bot.photos[-1][1],'AgAC_photo-id')
    def test_preview_invalid_link(self):
        self.assertTrue(new.handle_preview_start(self.bot,fake_message(text='/start preview_bad')))
        self.assertIn('Invalid',self.bot.sent[-1][1])
    def test_admin_stats_restricted(self):
        self.handlers['bookstats'](fake_message(user=22,text='/bookstats'))
        self.assertIn('administrators only',self.bot.sent[-1][1].lower())
    def test_admin_stats(self):
        with patch.object(new,'top_downloaded',return_value=[BOOK]):
            self.handlers['bookstats'](fake_message(text='/bookstats'))
        self.assertIn('Top Deliveries',self.bot.sent[-1][1]);self.assertIn('3',self.bot.sent[-1][1])
    def test_manage_shows_book_ids(self):
        with patch.object(new,'recently_uploaded',return_value=[BOOK]):
            self.handlers['bookmanage'](fake_message(text='/bookmanage'))
        self.assertIn(BID, self.bot.sent[-1][1])
    def test_manage_admin_only(self):
        self.handlers['bookmanage'](fake_message(user=22,text='/bookmanage'))
        self.assertIn('administrators only',self.bot.sent[-1][1].lower())
    def test_admin_edit_restricted(self):
        self.handlers['bookedit'](fake_message(user=22,text='/bookedit '+BID+' | T | A | English | Learning | -'))
        self.assertIn('administrators only',self.bot.sent[-1][1].lower())
    def test_admin_edit_allowed(self):
        msg='/bookedit '+BID+' | Book Title | Author Name | English | Learning | -'
        with patch.object(new,'update_metadata',return_value=True) as f:
            self.handlers['bookedit'](fake_message(text=msg))
        self.assertTrue(f.called)
        self.assertIn('updated',self.bot.sent[-1][1])
    def test_cover_requires_admin(self):
        self.handlers['bookcover'](fake_message(user=22,text='/bookcover '+BID))
        self.assertIn('administrators only',self.bot.sent[-1][1].lower())
    def test_cover_upload_flow(self):
        with patch.object(new,'get_details',return_value=BOOK),patch.object(new,'set_cover',return_value=True) as f:
            self.handlers['bookcover'](fake_message(text='/bookcover '+BID))
            m=fake_message();m.photo=[types.SimpleNamespace(file_id='photo_telegram_456')]
            self.handlers['library_v112_cover_photo'](m)
        f.assert_called_once_with(BID,'photo_telegram_456')
        self.assertIn('saved',self.bot.sent[-1][1])
    def test_delivery_counter_best_effort(self):
        item=dict(BOOK,channel_id=-1003000,message_id=10)
        with patch.object(lib,'get_book',return_value=item),patch.object(store,'record_delivery') as counter:
            self.assertTrue(lib.handle_library_start(self.bot,fake_message(text='/start book_'+uuid.UUID(BID).hex)))
        counter.assert_called_once_with(BID)
        self.assertEqual(len(self.bot.copied),1)
    def test_count_failure_does_not_block_delivery(self):
        item=dict(BOOK,channel_id=-1003000,message_id=10)
        with patch.object(lib,'get_book',return_value=item),patch.object(store,'record_delivery',side_effect=RuntimeError('db unavailable')):
            self.assertTrue(lib.handle_library_start(self.bot,fake_message(text='/start book_'+uuid.UUID(BID).hex)))
        self.assertEqual(len(self.bot.copied),1)
        self.assertIn('Sent:',self.bot.sent[-1][1])

class InstallTests(unittest.TestCase):
    def test_repeat_install_idempotent(self):
        path=(HERE/'book_library_bot.py').read_text(encoding='utf8')
        self.assertIn(MARKER,path)
        self.assertEqual(transform('book_library_bot.py',path),path)
    def test_only_two_existing_files(self):
        with tempfile.TemporaryDirectory() as td:
            for f in ('book_library_bot.py','book_library_store.py'):
                (Path(td)/f).write_bytes((HERE/f).read_bytes())
            self.assertEqual(integrate(td,apply=False,output=lambda x:None),[])
            self.assertEqual(integrate(td,apply=True,output=lambda x:None),[])
    def test_module_compiles(self):
        import ast
        for f in ('book_library_bot.py','book_library_store.py','book_library_v112_bot.py','book_library_v112_store.py'):
            ast.parse((HERE/f).read_text(encoding='utf8'))

if __name__=='__main__':unittest.main()
