"""Offline display tests; never connect to Telegram or Supabase."""
import unittest
from unittest.mock import patch
import library_media_v117_bot as api


class TestResultLabels(unittest.TestCase):
    def test_tamil_english_distinguishable(self):
        base={'title':'The Psychology of Money','media_kind':'pdf'}
        eng=api._result_label({**base,'language':'English','file_size':2936013})
        tam=api._result_label({**base,'language':'Tamil','file_size':39741030})
        self.assertIn('English',eng)
        self.assertIn('Tamil',tam)
        self.assertIn('2.8 MB',eng)
        self.assertIn('37.9 MB',tam)
        self.assertNotEqual(eng,tam)
        self.assertLessEqual(len(eng),63)
        self.assertLessEqual(len(tam),63)

    def test_long_title_preserves_language_and_size(self):
        txt=api._result_label({'title':'An extremely lengthy title that would obscure the language information if not truncated', 'media_kind':'pdf','language':'Tamil','file_size':39741030})
        self.assertIn('Tamil',txt)
        self.assertIn('PDF',txt)
        self.assertIn('37.9 MB',txt)
        self.assertLessEqual(len(txt),63)

    def test_markup_distinct_links(self):
        class DummyKeyboard:
            def __init__(self):self.buttons=[]
            def add(self,item):self.buttons.append(item)
        rows=[{'id':'1','title':'The Psychology of Money','media_kind':'pdf','language':language,'file_size':size} for language,size in [('English',2936013),('Tamil',39741030)]]
        with patch.object(api,'_keyboard',return_value=DummyKeyboard()), patch.object(api,'_button',side_effect=lambda text,**kwargs:(text,kwargs)), patch.object(api,'_link',side_effect=['https://t.me/example?start=book_a','https://t.me/example?start=book_b']):
            markup=api._markup(None,rows)
        self.assertEqual(len(markup.buttons),2)
        self.assertIn('English',markup.buttons[0][0]);self.assertIn('Tamil',markup.buttons[1][0])
        self.assertNotEqual(markup.buttons[0][1]['url'],markup.buttons[1][1]['url'])

    def test_language_filter_parsed(self):
        q,f=api.parse_search_query('The Psychology of Money lang:Tamil')
        self.assertEqual(q,'The Psychology of Money')
        self.assertEqual(f['language'],'Tamil')


if __name__=='__main__':
    unittest.main()
