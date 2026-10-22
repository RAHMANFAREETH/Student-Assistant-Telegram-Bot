import telebot
from telebot import types

from config import BOT_TOKEN

from pdf_tools import register_pdf_handlers
from notes import register_note_handlers
from translate import register_translation_handlers

from reminders import (
    register_reminder_handlers,
    start_reminder_worker
)


bot = telebot.TeleBot(
    BOT_TOKEN
)


# ==================================================
# MAIN MENU
# ==================================================

def show_main_menu(
    chat_id,
    first_name="Friend"
):

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2
    )

    markup.add(
        types.KeyboardButton(
            "📄 PDF Tools"
        ),

        types.KeyboardButton(
            "📝 Notes"
        ),

        types.KeyboardButton(
            "🌐 Translate"
        ),

        types.KeyboardButton(
            "⏰ Study Reminder"
        ),

        types.KeyboardButton(
            "ℹ️ Help"
        )
    )


    bot.send_message(
        chat_id,
        f"""
👋 Hello {first_name}!

🎓 Welcome to Student Assistant Bot.

Choose what you want to do:

📄 PDF Tools
📝 Notes
🌐 Translation
⏰ Study Reminders
""",
        reply_markup=markup
    )


# ==================================================
# START
# ==================================================

@bot.message_handler(
    commands=["start"]
)
def start(message):

    first_name = (
        message.from_user.first_name
        or "Friend"
    )

    show_main_menu(
        message.chat.id,
        first_name
    )


# ==================================================
# HELP
# ==================================================

@bot.message_handler(
    commands=["help"]
)
def help_command(message):

    bot.send_message(
        message.chat.id,
        """
🎓 Student Assistant Bot

Available Features

📄 PDF Tools
• Merge PDF
• Extract Pages
• Images → PDF
• Rotate PDF
• Protect PDF

📝 Notes
• Add Notes
• View Notes
• Search Notes
• Delete Notes

🌐 Translation
• English
• Tamil
• Arabic
• Sinhala
• Auto Detect

⏰ Study Reminders
• Create Reminder
• View Upcoming Reminders
• Delete Reminder

Commands:

/start
/help
/id
"""
    )


@bot.message_handler(
    func=lambda message:
    message.text == "ℹ️ Help"
)
def help_button(message):

    help_command(
        message
    )


# ==================================================
# USER ID
# ==================================================

@bot.message_handler(
    commands=["id"]
)
def user_id(message):

    bot.send_message(
        message.chat.id,
        f"""
👤 User ID:
{message.from_user.id}

💬 Chat ID:
{message.chat.id}
"""
    )


# ==================================================
# REGISTER FEATURES
# ==================================================

register_pdf_handlers(
    bot,
    show_main_menu
)

register_note_handlers(
    bot,
    show_main_menu
)

register_translation_handlers(
    bot,
    show_main_menu
)

register_reminder_handlers(
    bot,
    show_main_menu
)


# ==================================================
# START REMINDER SYSTEM
# ==================================================

start_reminder_worker(
    bot
)


# ==================================================
# RUN BOT
# ==================================================

print(
    "✅ Student Assistant Bot is running..."
)

print(
    "⏰ Reminder system is running..."
)


bot.infinity_polling(
    skip_pending=True
)