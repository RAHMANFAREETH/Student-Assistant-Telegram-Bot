import os
import sys
import types
import unittest
from unittest.mock import patch

from super_miniapp_v120_launch import mini_app_url, pilot_user_ids, pilot_access_allowed, can_launch, register_super_app_launcher


class TestLaunch(unittest.TestCase):
    def test_empty_url_fails(self):
        with patch.dict(os.environ, {'RENDER_EXTERNAL_URL':'', 'BOOK_LIBRARY_PUBLIC_URL':'',
                                     'SUPER_MINIAPP_V120_PUBLIC_URL':''}):
            self.assertIsNone(mini_app_url())

    def test_https_url_and_fallback(self):
        with patch.dict(os.environ, {'RENDER_EXTERNAL_URL':'https://bot.onrender.com/',
                                     'SUPER_MINIAPP_V120_PUBLIC_URL':''}):
            self.assertEqual(mini_app_url(),'https://bot.onrender.com/app')

    def test_invalid_urls_rejected(self):
        for url in ('http://bot.example/app', 'https://bot.example/library',
                    'https://bot.example/app?user_id=1', 'https://user:pass@bot.example/app',
                    'https://localhost/app', 'https://bot.example:555/app',
                    'https://bot.example/app#x', 'https://bot.example/app\\bad'):
            with self.subTest(url=url), patch.dict(os.environ, {'SUPER_MINIAPP_V120_PUBLIC_URL': url}):
                self.assertIsNone(mini_app_url())

    def test_allowlist_parsing(self):
        with patch.dict(os.environ, {'SUPER_MINIAPP_V120_PILOT_IDS':'7, foo, -1, 33, 7'}):
            self.assertEqual(pilot_user_ids(), {7, 33})

    def test_backend_pilot_gate_when_configured(self):
        with patch.dict(os.environ, {'SUPER_MINIAPP_V120_PILOT_IDS':'7', 'SUPER_MINIAPP_V120_LAUNCH_PUBLIC':'false'}):
            self.assertTrue(pilot_access_allowed(7))
            self.assertFalse(pilot_access_allowed(9))
        with patch.dict(os.environ, {'SUPER_MINIAPP_V120_PILOT_IDS':'', 'SUPER_MINIAPP_V120_LAUNCH_PUBLIC':'false'}):
            self.assertTrue(pilot_access_allowed(9))  # backward-compatible adult auth

    def test_fails_closed_without_flags(self):
        with patch.dict(os.environ, {'SUPER_MINIAPP_V120_ENABLED':'false',
                                     'SUPER_MINIAPP_V120_LAUNCH_ENABLED':'false',
                                     'SUPER_MINIAPP_V120_PILOT_IDS':'7'}):
            self.assertFalse(can_launch(7))

    def test_requires_adult(self):
        study = types.ModuleType('study_access_v9')
        study.is_verified_adult = lambda uid: uid == 7
        env = {'SUPER_MINIAPP_V120_ENABLED':'true', 'SUPER_MINIAPP_V120_LAUNCH_ENABLED':'true',
               'SUPER_MINIAPP_V120_PILOT_IDS':'7', 'SUPER_MINIAPP_V120_LAUNCH_PUBLIC':'false'}
        with patch.dict(os.environ,env), patch.dict(sys.modules,{'study_access_v9':study}):
            self.assertTrue(can_launch(7))
            self.assertFalse(can_launch(8))

    def test_command_only_private_and_signed_user(self):
        class Bot:
            def __init__(self): self.func = None; self.sent = []
            def message_handler(self,**kwargs):
                def inner(func): self.func = func; return func
                return inner
            def send_message(self,*args,**kwargs): self.sent.append((args,kwargs))
        bot=Bot()
        register_super_app_launcher(bot)
        message = types.SimpleNamespace(chat=types.SimpleNamespace(id=123, type='group'),
                                        from_user=types.SimpleNamespace(id=7))
        bot.func(message)
        self.assertFalse(bot.sent)
        message.chat.type='private'
        with patch('super_miniapp_v120_launch.can_launch',return_value=False): bot.func(message)
        self.assertIn('not available',bot.sent[-1][0][1])

    def test_command_webapp_button(self):
        class Keyboard:
            def __init__(self): self.buttons = []
            def add(self,x): self.buttons.append(x)
        fake_types=types.SimpleNamespace(InlineKeyboardMarkup=Keyboard,
                                         InlineKeyboardButton=lambda text,web_app: (text,web_app),
                                         WebAppInfo=lambda url: types.SimpleNamespace(url=url))
        telebot=types.ModuleType('telebot');telebot.types=fake_types
        class Bot:
            def message_handler(self,**kwargs):
                def inner(f): self.f = f; return f
                return inner
            def send_message(self,*args,**kwargs): self.sent=(args,kwargs)
        bot=Bot();register_super_app_launcher(bot)
        message=types.SimpleNamespace(chat=types.SimpleNamespace(id=7,type='private'),
                                      from_user=types.SimpleNamespace(id=7))
        with patch.dict(sys.modules,{'telebot':telebot}),\
             patch('super_miniapp_v120_launch.can_launch',return_value=True),\
             patch('super_miniapp_v120_launch.mini_app_url',return_value='https://example.com/app'):
            bot.f(message)
        markup=bot.sent[1]['reply_markup']
        self.assertEqual(markup.buttons[0][1].url,'https://example.com/app')


if __name__ == '__main__': unittest.main()
