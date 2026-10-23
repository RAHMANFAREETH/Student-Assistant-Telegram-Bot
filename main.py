import os
import threading

import telebot

from flask import (
    Flask,
    request
)

from telebot import types

from config import (
    BOT_TOKEN,
    WEBHOOK_SECRET
)

from pdf_tools import (
    register_pdf_handlers
)

from notes import (
    register_note_handlers
)

from translate import (
    register_translation_handlers
)

from reminders import (
    register_reminder_handlers
)


# ==================================================
# TELEGRAM
# ==================================================

bot = telebot.TeleBot(
    BOT_TOKEN
)


# ==================================================
# FLASK
# ==================================================

app = Flask(
    __name__
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

    name = (
        message.from_user.first_name
        or "Friend"
    )

    show_main_menu(
        message.chat.id,
        name
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

📄 PDF Tools
• Merge PDF
• Extract Pages
• Images → PDF
• Rotate PDF
• Protect PDF

📝 Notes
• Add
• View
• Search
• Delete

🌐 Translation
• English
• Tamil
• Arabic
• Sinhala

⏰ Study Reminders
• Add
• View
• Delete

Commands:

/start
/help
/id
"""
    )


@bot.message_handler(
    func=lambda m:
    m.text == "ℹ️ Help"
)
def help_button(message):

    help_command(
        message
    )


# ==================================================
# ID
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
# REGISTER MODULES
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
# HEALTH CHECK
# ==================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return {
        "status": "ok",
        "bot": "Student Assistant Bot"
    }, 200


# ==================================================
# PROCESS TELEGRAM UPDATE
# ==================================================

def process_update(update):

    try:

        bot.process_new_updates(
            [update]
        )

    except Exception as e:

        print(
            "Update processing error:",
            e
        )


# ==================================================
# TELEGRAM WEBHOOK
# ==================================================

@app.route(
    "/telegram-webhook",
    methods=["POST"]
)
def telegram_webhook():

    received_secret = (
        request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token"
        )
    )

    if received_secret != WEBHOOK_SECRET:

        return (
            "Forbidden",
            403
        )

    try:

        update = (
            telebot.types.Update
            .de_json(
                request.get_data(
                    as_text=True
                )
            )
        )

        thread = threading.Thread(
            target=process_update,
            args=(update,),
            daemon=True
        )

        thread.start()

        return (
            "OK",
            200
        )

    except Exception as e:

        print(
            "Webhook error:",
            e
        )

        return (
            "Bad Request",
            400
        )


# ==================================================
# SET RENDER WEBHOOK
# ==================================================

def setup_render_webhook():

    render_url = os.getenv(
        "RENDER_EXTERNAL_URL"
    )

    if not render_url:

        return

    webhook_url = (
        render_url.rstrip("/")
        + "/telegram-webhook"
    )

    try:

        result = bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET
        )

        print(
            "🌐 Webhook URL:",
            webhook_url
        )

        print(
            "✅ Webhook configured:",
            result
        )

    except Exception as e:

        print(
            "❌ Webhook setup failed:",
            e
        )


# Configure only when hosted on Render
if os.getenv("RENDER"):

    setup_render_webhook()


# ==================================================
# LOCAL DEVELOPMENT
# ==================================================

if __name__ == "__main__":

    if os.getenv("RENDER"):

        port = int(
            os.getenv(
                "PORT",
                "10000"
            )
        )

        app.run(
            host="0.0.0.0",
            port=port
        )

    else:

        print(
            "✅ Student Assistant Bot "
            "running locally..."
        )

        print(
            "🌐 Supabase database enabled."
        )

        bot.remove_webhook()

        bot.infinity_polling(
            skip_pending=True
        )