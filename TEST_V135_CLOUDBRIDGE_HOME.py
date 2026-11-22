"""Offline regression tests for the additive /start CloudBridge Web App button.

Run: python -m unittest TEST_V135_CLOUDBRIDGE_HOME -q
No Telegram bot token, network, Supabase or OAuth access is required.
"""
from __future__ import annotations

import os
import sys
import types
import unittest
from unittest.mock import patch

import friendly_v119 as friendly


class FakeButton:
    def __init__(self, text, callback_data=None, url=None, web_app=None):
        self.text = text
        self.callback_data = callback_data
        self.url = url
        self.web_app = web_app


class FakeWebAppInfo:
    def __init__(self, url):
        self.url = url


class FakeMarkup:
    def __init__(self, row_width=2):
        self.rows = []

    def row(self, *items):
        self.rows.append(items)


class FakeBot:
    def __init__(self):
        self.sent = []

    def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text, kwargs))


class CloudBridgeHomeTests(unittest.TestCase):
    def setUp(self):
        self.bot = FakeBot()
        fake_types = types.SimpleNamespace(InlineKeyboardButton=FakeButton,
                                           WebAppInfo=FakeWebAppInfo,
                                           InlineKeyboardMarkup=FakeMarkup)
        self.fake_telebot = types.SimpleNamespace(types=fake_types)
        self.module_patch = patch.dict(sys.modules, {"telebot": self.fake_telebot})
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)
        self.lang_patch = patch.object(friendly, "_lang", return_value="en")
        self.lang_patch.start()
        self.addCleanup(self.lang_patch.stop)

    def _render(self, private_chat=True, flags="true", base="https://bot.onrender.com"):
        with patch.dict(os.environ, {
            "CLOUDBRIDGE_V134_ENABLED": flags,
            "CLOUDBRIDGE_PUBLIC_URL": base,
            "SUPER_MINIAPP_V120_ENABLED": "false",
            "SUPER_MINIAPP_V120_LAUNCH_ENABLED": "false",
        }):
            friendly.home(self.bot, 123, "Student", send_welcome=False,
                          private_chat=private_chat)
        return [button for row in self.bot.sent[-1][2]["reply_markup"].rows
                for button in row]

    def test_private_start_shows_cloudbridge_with_original_menu_intact(self):
        buttons = self._render()
        labels = [button.text for button in buttons]
        self.assertEqual(len(labels), len(friendly.HOME_LABELS["en"]) + 1)
        self.assertEqual(labels[:len(friendly.HOME_LABELS["en"])],
                         list(friendly.HOME_LABELS["en"]))
        cloud = buttons[-1]
        self.assertEqual(cloud.text, "☁️ CloudBridge · Google Drive")
        self.assertEqual(cloud.web_app.url, "https://bot.onrender.com/cloud")
        self.assertIsNone(cloud.callback_data)

    def test_button_hidden_in_group_context(self):
        self.assertNotIn("☁️ CloudBridge · Google Drive",
                         [button.text for button in self._render(private_chat=False)])

    def test_button_hidden_when_feature_disabled(self):
        self.assertNotIn("☁️ CloudBridge · Google Drive",
                         [button.text for button in self._render(flags="false")])

    def test_button_hidden_when_https_url_invalid(self):
        self.assertNotIn("☁️ CloudBridge · Google Drive",
                         [button.text for button in self._render(base="http://insecure.example")])

    def test_no_adult_gate_for_public_cloud_utility(self):
        with patch.object(friendly, "_adult", side_effect=AssertionError("Not an adult feature")):
            self.assertEqual(self._render()[-1].text, "☁️ CloudBridge · Google Drive")

    def test_super_mini_app_button_is_preserved_when_enabled(self):
        with patch("super_miniapp_v120_launch.can_launch", return_value=True), \
             patch("super_miniapp_v120_launch.mini_app_url", return_value="https://bot.onrender.com/app"):
            labels = [button.text for button in self._render()]
        self.assertIn("🎓 Super Mini App", labels)
        self.assertIn("☁️ CloudBridge · Google Drive", labels)


if __name__ == "__main__":
    unittest.main()
