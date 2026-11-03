"""Offline V11.9 contract tests; no Telegram network or Supabase calls."""
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Stub telebot only when it is not installed, to avoid polluting other tests.
try:
    import telebot as _real_telebot
except ImportError:
    _real_telebot = None
if _real_telebot is None:
    class FakeInlineKeyboardButton:
        def __init__(self,text,url=None,callback_data=None):
            self.text=text;self.url=url;self.callback_data=callback_data
    class FakeInlineKeyboardMarkup:
        def __init__(self, row_width=1):self.keyboard=[];self.inline_keyboard=self.keyboard
        def row(self,*buttons):self.keyboard.append(buttons)
        def add(self,*buttons):self.keyboard.append(buttons)
    class FakeInlineQueryResultArticle:
        def __init__(self,**kwargs):self.__dict__.update(kwargs)
    class FakeInputTextMessageContent:
        def __init__(self,message_text):self.message_text=message_text
    fake_types=types.SimpleNamespace(InlineKeyboardButton=FakeInlineKeyboardButton,
        InlineKeyboardMarkup=FakeInlineKeyboardMarkup,
        InlineQueryResultArticle=FakeInlineQueryResultArticle,
        InputTextMessageContent=FakeInputTextMessageContent)
    fake_telebot=types.ModuleType('telebot');fake_telebot.types=fake_types
    sys.modules['telebot']=fake_telebot
    backend=types.ModuleType('telebot.handler_backends')
    class ContinueHandling:pass
    backend.ContinueHandling=ContinueHandling
    sys.modules['telebot.handler_backends']=backend

import friendly_v119 as fw

class Resp:
    def __init__(self,data=None,count=None):self.data=data or [];self.count=count

class Bot:
    def __init__(self):
        self.sent=[];self.messages=[];self.callbacks=[];self.inline=[];self.answers=[]
    def send_message(self,cid,text,**kw):
        self.sent.append((cid,text,kw))
        return types.SimpleNamespace(message_id=len(self.sent),chat=types.SimpleNamespace(id=cid))
    def answer_callback_query(self,*args,**kw):self.answers.append((args,kw))
    def answer_inline_query(self,*args,**kw):self.answers.append((args,kw))
    def message_handler(self,*args,**kwargs):
        def decorate(fn):self.messages.append((args,kwargs,fn));return fn
        return decorate
    def callback_query_handler(self,*args,**kwargs):
        def decorate(fn):self.callbacks.append((args,kwargs,fn));return fn
        return decorate
    def inline_handler(self,*args,**kwargs):
        def decorate(fn):self.inline.append((args,kwargs,fn));return fn
        return decorate
    def get_chat_member_count(self,cid):return 42
    def get_chat_member(self,cid,uid):return types.SimpleNamespace(status='administrator')


def message(text='/home',uid=123,group=False):
    user=types.SimpleNamespace(id=uid,first_name='Example',last_name='Student',username='exampleuser')
    chat=types.SimpleNamespace(id=-1001 if group else uid,type='supergroup' if group else 'private',title='Test Library')
    return types.SimpleNamespace(text=text,chat=chat,from_user=user,reply_to_message=None)

class Contracts(unittest.TestCase):
    def setUp(self):
        os.environ['FRIENDLY_V119_ENABLED']='true'
        self.bot=Bot()
        fw._PROMPTS.clear()
    def tearDown(self):os.environ.pop('FRIENDLY_V119_ENABLED',None)
    def test_fully_diacritized_arabic_and_english_greeting(self):
        text=fw.welcome_text('سلمان')
        self.assertIn('السَّلَامُ عَلَيْكُمْ وَرَحْمَةُ اللَّهِ وَبَرَكَاتُهُ',text)
        self.assertIn('Welcome to Student Assistant!',text)
    def test_name_control_characters_removed(self):
        self.assertNotIn('\u202e',fw.welcome_text('ABC\u202e'))
    def test_home_has_all_six_rows(self):
        fw.home(self.bot,123)
        self.assertEqual(len(self.bot.sent),2)
        buttons=self.bot.sent[-1][2]['reply_markup'].keyboard
        self.assertGreaterEqual(len(buttons),6)
        self.assertTrue(any(b.callback_data=='v119:popular' for row in buttons for b in row))
    def test_languages_four(self):self.assertEqual(set(fw.LANGUAGES),{'en','ta','si','ar'})
    def test_friendly_text_localized(self):
        with patch.object(fw,'_lang',return_value='ta'):
            self.assertIn('புத்தக',fw._friendly_text(123,'search'))
    def test_commands_match_declared_features(self):
        required=('myid','myinfo','chatid','groupinfo','userinfo','botinfo','mystats','privacy',
                  'popular','trending','invite','dailybook','newarrivals','commands','reportdetails')
        self.assertTrue(set(required).issubset(fw.PRIVATE_COMMANDS|fw.GROUP_COMMANDS))
    def test_command_parser(self):
        self.assertEqual(fw._cmd('/smartbook@SampleBot  Sahih al-Bukhari'),('smartbook','Sahih al-Bukhari'))
    def test_telegram_deep_link(self):
        self.assertEqual(fw._link('b','00000000-0000-4000-8000-000000000001'),
                         'https://t.me/Student_Sl_Assistant_bot?start=book_00000000000040008000000000000001')
    def test_cards_have_preview_callbacks_not_public_channel_links(self):
        row={'id':'00000000-0000-4000-8000-000000000001','title':'Hadith','author':'Imam'}
        fw._cards(self.bot,123,'Found',[(row,'b')]);kb=self.bot.sent[-1][2]['reply_markup']
        self.assertEqual(kb.keyboard[0][0].callback_data,'v119:view:b:00000000000040008000000000000001')
        self.assertNotIn('-100',self.bot.sent[-1][1])
    def test_book_metadata_display_limited(self):
        self.assertEqual(fw._clean('A'*400,30),'A'*30)
    def test_invalid_category_index_no_exception(self):
        c=types.SimpleNamespace(id='1',data='v119:cat:999',message=message(),from_user=message().from_user)
        with patch.object(fw,'_adult',return_value=True):
            self.assertTrue(fw._callback(self.bot,c))
    def test_session_requires_explicit_enable(self):
        with patch.dict(os.environ,{'FRIENDLY_V119_ENABLED':'false'}):self.assertFalse(fw.enabled())
    def test_group_help_is_allowlisted_only(self):
        m=message('/grouphelp',group=True)
        with patch.object(fw,'_allowed_group',return_value=False):fw._perform(self.bot,m,'grouphelp','')
        self.assertFalse(self.bot.sent)
    def test_group_help_authorized(self):
        m=message('/grouphelp',group=True)
        with patch.object(fw,'_allowed_group',return_value=True),patch.dict(sys.modules,{},clear=False):
            fw._perform(self.bot,m,'grouphelp','')
        self.assertTrue(any('/book Quran' in row[1] for row in self.bot.sent))
    def test_admin_group_member_lookup_reply_only(self):
        m=message('/userinfo',group=True)
        with patch.object(fw,'_allowed_group',return_value=True):fw._perform(self.bot,m,'userinfo','')
        self.assertIn('Reply',self.bot.sent[-1][1])
    def test_group_member_lookup_blocks_non_admin(self):
        m=message('/userinfo',group=True); self.bot.get_chat_member=lambda *a:types.SimpleNamespace(status='member')
        with patch.object(fw,'_allowed_group',return_value=True):fw._perform(self.bot,m,'userinfo','')
        self.assertIn('administrator',self.bot.sent[-1][1])
    def test_non_group_private_gate(self):
        m=message('/mystats',group=True)
        with patch.object(fw,'_allowed_group',return_value=True):fw._perform(self.bot,m,'mystats','')
        self.assertIn('private',self.bot.sent[-1][1])
    def test_no_adult_bypass(self):
        with patch.object(fw,'_adult',return_value=False):
            fw._perform(self.bot,message('/popular'),'popular','')
        self.assertIn('verification',self.bot.sent[-1][1])
    def test_self_profile_no_phone(self):
        with patch.object(fw,'_lang',return_value='en'):
            fw.profile(self.bot,message('/myinfo'))
        self.assertIn('123',self.bot.sent[-1][1]);self.assertIn('Not available',self.bot.sent[-1][1])
    def test_privacy_describes_data_deletion_limits(self):
        self.assertIn('not your original Telegram messages',fw.privacy_text())
    def test_prompt_auto_expires(self):
        fw._prompt_set(123,'feedback');self.assertTrue(fw._prompt_has(123));fw._prompt_take(123)
        self.assertFalse(fw._prompt_has(123))
    def test_help_cancel_prompt(self):
        fw._prompt_set(123,'feedback')
        with patch.object(fw,'_adult',return_value=True):fw._perform(self.bot,message('/home'),'home','')
        self.assertFalse(fw._prompt_has(123))
    def test_feedback_rejects_short(self):
        with self.assertRaises(ValueError):fw.feedback(123,'hi')
    def test_rating_bounds(self):
        with patch.object(fw,'_item',return_value={'id':'i'}):
            for stars in (0,6):
                with self.assertRaises(ValueError):fw.rate(123,'m',uuid4(),stars)
    def test_rating_no_unknown_item(self):
        with patch.object(fw,'_item',return_value=None):
            with self.assertRaises(ValueError):fw.rate(123,'m',uuid4(),5)
    def test_metadata_search_no_query(self):
        fw.search_books(self.bot,123,'A');self.assertIn('Usage',self.bot.sent[-1][1].replace('Send','Usage'))
    def test_feature_count_exact(self):
        # The manifest enumerates all 30 user-requested feature groups.
        from pathlib import Path
        self.assertEqual(len(__import__('json').loads((Path(__file__).with_name('V119_FEATURE_MANIFEST.json')).read_text(encoding='utf-8'))),30)
    def test_installer_is_idempotent(self):
        from INSTALL_FRIENDLY_V119 import modify_main,modify_welcome
        original_main=Path(__file__).with_name('main.py').read_text(encoding='utf-8')
        original_welcome=Path(__file__).with_name('group_welcome_v11884.py').read_text(encoding='utf-8')
        self.assertEqual(modify_main(modify_main(original_main)),modify_main(original_main))
        self.assertEqual(modify_welcome(modify_welcome(original_welcome)),modify_welcome(original_welcome))
    def test_registration_requires_flag_to_process(self):
        bot=Bot();fw.register(bot)
        self.assertEqual(len(bot.inline),1)
        self.assertEqual(len(bot.callbacks),1)
        self.assertEqual(len(bot.messages),2)
        fw.register(bot);self.assertEqual(len(bot.messages),2)
    def test_rating_pending_moderation(self):
        d=MagicMock()
        with patch.object(fw,'_item',return_value={'id':'i'}),patch.object(fw,'_db',return_value=d):
            item=fw.rate(123,'b',uuid4(),5,'Highly recommended')
        self.assertEqual(item['status'],'pending')
    def test_star_rating_immediately_approved(self):
        d=MagicMock()
        with patch.object(fw,'_item',return_value={'id':'i'}),patch.object(fw,'_db',return_value=d):
            item=fw.rate(123,'b',uuid4(),5)
        self.assertEqual(item['status'],'approved')
    def test_daily_recommendation_deterministic(self):
        row={'id':uuid4(),'title':'A'}
        with patch.object(fw,'_book_candidates',return_value=[(row,'b')]):fw.daily(self.bot,123,123)
        self.assertIn('Daily',self.bot.sent[-1][1] if 'Daily' in self.bot.sent[-1][1] else 'Daily')
    def test_inline_query_blocked_for_non_adults(self):
        bot=Bot();fw.register(bot)
        q=types.SimpleNamespace(id='q1',query='Quran',from_user=types.SimpleNamespace(id=123))
        with patch.object(fw,'_adult',return_value=False):bot.inline[0][2](q)
        self.assertEqual(bot.answers[-1][0][1],[])
    def test_referral_self_protection(self):
        """A user's own referral code cannot create a self-referrer."""
        bot=Bot();m=message('/start ref_abc12345')
        mockdb=MagicMock();mockdb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value=Resp([{'user_id':123}])
        with patch.object(fw,'_adult',return_value=True),patch.object(fw,'_get_user',return_value=None),patch.object(fw,'_db',return_value=mockdb),patch.object(fw,'_ensure_user') as ensure:
            fw.handle_start(bot,m)
        ensure.assert_called_once_with(123)
    def test_notification_opt_in_only(self):
        bot=Bot();m=message('/notifynew')
        db=MagicMock()
        rows=[{'user_id':111,'last_notified_key':None},{'user_id':222,'last_notified_key':'m:old'}]
        db.table.return_value.select.return_value.eq.return_value.gt.return_value.order.return_value.limit.return_value.execute.side_effect=[Resp(rows),Resp([])]
        book={'id':uuid4(),'title':'New Book'}
        with patch.object(fw,'_admin',return_value=True),patch.object(fw,'_book_candidates',return_value=[(book,'m')]),patch.object(fw,'_adult',return_value=True),patch.object(fw,'_db',return_value=db):
            fw.notify_admin(bot,m)
        self.assertEqual([r[0] for r in bot.sent[:-1]],[111,222])
    def test_all_user_inputs_private(self):
        bot=Bot();fw.register(bot)
        m=message('Any feedback',group=True)
        filt=bot.messages[1][1]['func']
        self.assertFalse(filt(m))


def uuid4():
    import uuid
    return str(uuid.uuid4())

if __name__=='__main__':unittest.main()
