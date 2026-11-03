"""Offline V11.8.5 validation; no credentials, network, or DB writes."""
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

import library_language_picker_v1185 as picker
import library_search_ui_v1183 as search
import book_library_v112_bot as bookui
from PATCH_LIBRARY_LANGUAGE_PICKER_V1185 import transform_search, transform_facets, install


class Button:
    def __init__(self,text,callback_data=None,url=None,**kwargs):
        self.text=text
        self.callback_data=callback_data
        self.url=url


class Markup:
    def __init__(self,*a,**kw):
        self.inline_keyboard=[]
    def add(self,*buttons):
        self.inline_keyboard.append(list(buttons))
    def row(self,*buttons):
        self.inline_keyboard.append(list(buttons))


class FakeBot:
    def __init__(self): self.sent=[]
    def send_message(self,chat,text,**kw):
        self.sent.append((chat,text,kw))


class ChoiceTests(unittest.TestCase):
    def test_popular_languages_even_if_zero(self):
        options=picker.language_counts([('english',1),('Tamil',2)])
        self.assertEqual(options[0],('Malayalam',0))
        self.assertIn(('Tamil',2),options)
        self.assertIn(('English',1),options)
        self.assertIn(('Sinhala',0),options)
        self.assertIn(('Arabic',0),options)

    def test_unrecognized_metadata_is_not_silently_corrected(self):
        options=picker.language_counts([('Student Assistant Library',3),('Tamil',1)])
        self.assertIn(('Student Assistant Library',3),options)
        self.assertIn(('Tamil',1),options)

    def test_search_grid_and_language_filter(self):
        data=[{'title':'The Psychology of Money','language':'English','file_size':2800000},
              {'title':'The Psychology of Money','language':'Tamil','file_size':39700000}]
        self.assertIn(('Tamil',1),search._options(data,'language'))
        with patch.object(search,'_button',side_effect=lambda label,data=None,url=None: Button(label,data,url)),\
             patch.object(search,'_keyboard',side_effect=Markup):
            token,s=search._create(42,data,'📚 Library results: Psychology',group=False,requester_id=42)
            try:
                s['menu']='language'
                text,keyboard=search._display(FakeBot(),token,s)
                self.assertIn('SELECT LANGUAGE',text)
                self.assertTrue(any(len(row)==2 and 'Tamil' in row[1].text
                                    for row in keyboard.inline_keyboard))
                self.assertTrue(any('Back to Files' in b.text for row in keyboard.inline_keyboard for b in row))
                self.assertTrue(all(len(b.callback_data)<=64 for row in keyboard.inline_keyboard for b in row))
                s['filters']={'language':'Tamil'}
                self.assertEqual(len(search._filtered(s)),1)
                self.assertEqual(search._filtered(s)[0]['language'],'Tamil')
            finally:
                with search._LOCK: search._SESSIONS.pop(token,None)

    def test_private_book_library_language_grid(self):
        bot=FakeBot()
        with patch.object(bookui,'facets',return_value=[
            {'value':'English','book_count':1}, {'value':'Tamil','book_count':2}]),\
             patch.object(bookui,'_keyboard',side_effect=Markup),\
             patch.object(bookui,'_button',side_effect=lambda label,**kw: Button(label,**kw)):
            bookui._send_facets(bot,42,'language')
        self.assertEqual(len(bot.sent),1)
        _, text, opts=bot.sent[0]
        self.assertIn('SELECT LANGUAGE',text)
        rows=opts['reply_markup'].inline_keyboard
        self.assertTrue(any(len(row)==2 and row[1].text=='Tamil (2)' for row in rows))
        self.assertTrue(any('Back to Files' in b.text for row in rows for b in row))
        # Each language filter has a real existing V11.2 session token.
        tamil=next(b for row in rows for b in row if b.text=='Tamil (2)')
        self.assertTrue(tamil.callback_data.startswith('lib2:filter:'))
        token=tamil.callback_data.rsplit(':',1)[-1]
        try:
            self.assertEqual(bookui._session(token,42,42)['params']['language'],'Tamil')
            self.assertIsNone(bookui._session(token,42,999))
        finally:
            with bookui._lock: bookui._sessions.clear()

    def test_tamil_selection_shows_file_buttons_and_back(self):
        import uuid
        books=[{'id':str(uuid.uuid4()),'title':'The Psychology of Money',
                'language':'Tamil','file_size':39700000},
               {'id':str(uuid.uuid4()),'title':'A Second Tamil Book',
                'language':'Tamil','file_size':1200000}]
        bot=FakeBot()
        with patch.object(bookui,'browse_books',return_value=(books,False)) as browse,\
             patch.object(bookui,'_keyboard',side_effect=Markup),\
             patch.object(bookui,'_button',side_effect=lambda label,**kw:Button(label,**kw)),\
             patch('book_library_bot._bot_username',return_value='StudyBot'):
            self.assertTrue(bookui._list_page(bot,42,{'kind':'browse','language':'Tamil'},owner=42))
        browse.assert_called_once()
        self.assertEqual(browse.call_args.kwargs['language'],'Tamil')
        self.assertIn('TAMIL BOOKS',bot.sent[-1][1])
        buttons=[b for row in bot.sent[-1][2]['reply_markup'].inline_keyboard for b in row]
        file_buttons=[b for b in buttons if b.url]
        self.assertEqual(len(file_buttons),2)
        self.assertTrue(all('t.me/StudyBot?start=book_' in b.url for b in file_buttons))
        self.assertTrue(any('Back to Languages' in b.text for b in buttons))
        with bookui._lock:bookui._sessions.clear()

    def test_zero_tamil_books_has_navigable_empty_state(self):
        bot=FakeBot()
        with patch.object(bookui,'browse_books',return_value=([],False)),\
             patch.object(bookui,'_keyboard',side_effect=Markup),\
             patch.object(bookui,'_button',side_effect=lambda label,**kw:Button(label,**kw)):
            self.assertTrue(bookui._list_page(bot,42,{'kind':'browse','language':'Tamil'},owner=42))
        self.assertIn('No indexed Tamil books',bot.sent[-1][1])
        markup=bot.sent[-1][2]['reply_markup']
        self.assertTrue(any(b.callback_data=='lib2:fac:language'
                            for row in markup.inline_keyboard for b in row))

    def test_tamil_file_results_search_view(self):
        data=[{'title':'Psychology','language':'English','file_size':2800000},
              {'title':'Psychology','language':'Tamil','file_size':39700000}]
        with patch.object(search,'_button',side_effect=lambda label,data=None,url=None:Button(label,data,url)),\
             patch.object(search,'_keyboard',side_effect=Markup),\
             patch.object(search,'_file_button',side_effect=lambda bot,item:Button(item['title']+' '+item['language'],url='https://t.me/bot')):
            token,s=search._create(42,data,'📚 Results for Psychology',group=False,requester_id=42)
            try:
                s['filters']['language']='Tamil'
                text,kb=search._display(FakeBot(),token,s)
                self.assertIn('TAMIL FILES',text)
                self.assertIn('1 matching files',text)
                buttons=[b for row in kb.inline_keyboard for b in row]
                self.assertEqual(sum(bool(b.url) for b in buttons),1)
                self.assertTrue(any('Change Language' in b.text for b in buttons))
            finally:
                with search._LOCK:search._SESSIONS.pop(token,None)

    def test_other_facets_untouched(self):
        bot=FakeBot()
        with patch.object(bookui,'facets',return_value=[{'value':'Education','book_count':4}]),\
             patch.object(bookui,'_keyboard',side_effect=Markup),\
             patch.object(bookui,'_button',side_effect=lambda label,**kw: Button(label,**kw)):
            bookui._send_facets(bot,42,'category')
        self.assertIn('Choose a category',bot.sent[0][1])
        with bookui._lock: bookui._sessions.clear()


class PatchTests(unittest.TestCase):
    def test_transform_idempotency(self):
        root=Path(__file__).parent
        for name,func in [('library_search_ui_v1183.py',transform_search),
                          ('book_library_v112_bot.py',transform_facets)]:
            src=(root/name).read_text(encoding='utf-8')
            self.assertEqual(src,func(src))
        with self.assertRaises(ValueError):transform_search('not the module')
        with self.assertRaises(ValueError):transform_facets('not the module')

    def test_installer_dry_run_and_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            project=Path(__file__).parent
            for name in ['library_language_picker_v1185.py','library_search_ui_v1183.py',
                         'book_library_v112_bot.py']:
                shutil.copy2(project/name,root/name)
            before=(root/'book_library_v112_bot.py').read_bytes()
            install(root,apply=False)
            self.assertEqual(before,(root/'book_library_v112_bot.py').read_bytes())
            install(root,apply=True)
            install(root,apply=True)


if __name__=='__main__':unittest.main()
