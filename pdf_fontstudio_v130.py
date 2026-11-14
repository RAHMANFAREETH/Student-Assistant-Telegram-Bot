"""V13: Telegram PDF Tools -> Four-language Font & Writing Studio launcher.

Only opens the existing browser-based Studio in a Telegram Web App; nothing is
uploaded by this handler. The existing text-to-PDF and DOCX/PPTX conversion
routes remain independent. Identity/pilot checks are delegated to V12 launcher.
"""
from __future__ import annotations
import os

FONT_STUDIO_BUTTON = '🌍 Font & Writing Studio'
_TRUE = frozenset(('1', 'yes', 'true', 'on'))


def studio_url(user_id):
    """Return a verified https Studio URL, or (None, reason) when unavailable."""
    from super_miniapp_v120_launch import can_launch, mini_app_url
    if os.getenv('SUPER_FONT_STUDIO_V122_ENABLED', '').strip().lower() not in _TRUE:
        return None, 'The Font & Writing Studio is not enabled on this server yet.'
    if not can_launch(user_id):
        return None, ('The Super Mini App is not available for this account yet. '
                      'Ask the administrator to check the Mini App launch settings.')
    home = mini_app_url()
    if not home:
        return None, 'The Super Mini App HTTPS address has not been configured.'
    # mini_app_url() already validates HTTPS, host, lack of query/fragment,
    # and the exact /app path. Only append to this validated path.
    return home + '/fonts', None


def register_pdf_fontstudio_handlers(bot):
    """Register a private-chat launcher without intercepting other PDF modes."""
    from telebot import types

    @bot.message_handler(commands=['fontstudio', 'fonts'])
    @bot.message_handler(func=lambda m: getattr(m, 'text', None) == FONT_STUDIO_BUTTON,
                         content_types=['text'])
    def launch_fontstudio(message):
        chat = getattr(message, 'chat', None)
        chat_id = getattr(chat, 'id', None)
        if chat_id is None:
            return
        if getattr(chat, 'type', None) != 'private':
            bot.send_message(chat_id, '🔒 Open the Student Assistant Bot in a private chat to use Font & Writing Studio.')
            return
        user_id = getattr(getattr(message, 'from_user', None), 'id', None)
        url, explanation = studio_url(user_id)
        if explanation:
            bot.send_message(chat_id, '⚠️ ' + explanation + '\n\n'
                             'You can still use PDF Tools → 📝 Text → PDF for ordinary Unicode text.')
            return
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(
            '✍️ Open Four-Language Font Studio',
            web_app=types.WebAppInfo(url=url)))
        bot.send_message(chat_id,
            '🌍 Font & Writing Studio\n\n'
            'தமிழ் · English · العربية · සිංහල\n\n'
            '• Unicode font previews and writing helpers\n'
            '• Unicode ↔ Bamini ↔ SunTommy for Tamil\n'
            '• Copy and save text locally on your device\n\n'
            'To generate a PDF, return to PDF Tools and use 📝 Text → PDF '
            'or DOCX → PDF. Font previews do not guarantee the font is installed '
            'on the PDF conversion server.',
            reply_markup=keyboard)
