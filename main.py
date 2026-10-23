import os

import telebot
from flask import Flask, request
from telebot import types

from config import (
    BOT_TOKEN,
    WEBHOOK_SECRET
)

from pdf_tools import register_pdf_handlers
from notes import register_note_handlers
from translate import register_translation_handlers
from reminders import register_reminder_handlers


# ==================================================
# TELEGRAM BOT
# ==================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    threaded=False
)


# ==================================================
# FLASK APP
# ==================================================

app = Flask(__name__)


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
# /START
# ==================================================

@bot.message_handler(
    commands=["start"]
)
def start(message):

    first_name = (
        message.from_user.first_name
        or "Friend"
    )

    print(
        f"▶️ /start received from "
        f"{message.from_user.id}"
    )

    show_main_menu(
        message.chat.id,
        first_name
    )


# ==================================================
# /HELP
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
• Add Note
• View Notes
• Search Notes
• Delete Note

🌐 Translation
• English
• Tamil
• Arabic
• Sinhala
• Auto Detect

⏰ Study Reminders
• Add Reminder
• View Reminders
• Delete Reminder

Commands:

/start
/help
/id
"""
    )


# ==================================================
# HELP BUTTON
# ==================================================

@bot.message_handler(
    func=lambda message:
    message.text == "ℹ️ Help"
)
def help_button(message):

    help_command(message)


# ==================================================
# /ID
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
# REGISTER PDF TOOLS
# ==================================================

register_pdf_handlers(
    bot,
    show_main_menu
)


# ==================================================
# REGISTER NOTES
# ==================================================

register_note_handlers(
    bot,
    show_main_menu
)


# ==================================================
# REGISTER TRANSLATOR
# ==================================================

register_translation_handlers(
    bot,
    show_main_menu
)


# ==================================================
# REGISTER REMINDERS
# ==================================================

register_reminder_handlers(
    bot,
    show_main_menu
)


# ==================================================
# HEALTH CHECK
# ==================================================

@app.route(
    "/",
    methods=["GET", "HEAD"]
)
def home():

    return {
        "status": "ok",
        "bot": "Student Assistant Bot"
    }, 200


# ==================================================
# TELEGRAM WEBHOOK
# ==================================================

@app.route(
    "/telegram-webhook",
    methods=["POST"]
)
def telegram_webhook():

    # ----------------------------------------------
    # Verify Telegram webhook secret
    # ----------------------------------------------

    received_secret = (
        request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token"
        )
    )

    if received_secret != WEBHOOK_SECRET:

        print(
            "❌ Invalid Telegram webhook secret"
        )

        return (
            "Forbidden",
            403
        )


    # ----------------------------------------------
    # Process Telegram update
    # ----------------------------------------------

    try:

        json_string = (
            request
            .get_data()
            .decode("utf-8")
        )

        update = (
            telebot
            .types
            .Update
            .de_json(
                json_string
            )
        )

        print(
            "📩 Telegram update received:",
            update.update_id
        )

        bot.process_new_updates(
            [update]
        )

        print(
            "✅ Telegram update processed:",
            update.update_id
        )

        return (
            "OK",
            200
        )


    except Exception as error:

        print(
            "❌ Webhook processing error:"
        )

        print(
            repr(error)
        )

        return (
            "Bad Request",
            400
        )


# ==================================================
# SET TELEGRAM WEBHOOK ON RENDER
# ==================================================

def setup_render_webhook():

    render_url = os.getenv(
        "RENDER_EXTERNAL_URL"
    )

    if not render_url:

        print(
            "ℹ️ RENDER_EXTERNAL_URL not found."
        )

        return


    webhook_url = (
        render_url.rstrip("/")
        + "/telegram-webhook"
    )


    try:

        # Remove old webhook first
        bot.remove_webhook()

        result = bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET,
            allowed_updates=[
                "message",
                "callback_query"
            ]
        )


        print(
            "🌐 Webhook URL:",
            webhook_url
        )

        print(
            "✅ Webhook configured:",
            result
        )


        # Show Telegram webhook information
        info = bot.get_webhook_info()

        print(
            "📡 Telegram webhook info:"
        )

        print(
            "URL:",
            info.url
        )

        print(
            "Pending updates:",
            info.pending_update_count
        )

        if info.last_error_message:

            print(
                "⚠️ Last webhook error:",
                info.last_error_message
            )


    except Exception as error:

        print(
            "❌ Webhook setup failed:"
        )

        print(
            repr(error)
        )


# ==================================================
# RENDER SETUP
# ==================================================

if os.getenv(
    "RENDER_EXTERNAL_URL"
):

    setup_render_webhook()


# ==================================================
# LOCAL DEVELOPMENT
# ==================================================

if __name__ == "__main__":

    # ----------------------------------------------
    # LOCAL VS CODE MODE
    # ----------------------------------------------

    if not os.getenv(
        "RENDER_EXTERNAL_URL"
    ):

        print(
            "✅ Student Assistant Bot "
            "running locally..."
        )

        print(
            "🌐 Supabase database enabled."
        )

        print(
            "📡 Telegram polling enabled."
        )


        try:

            bot.remove_webhook()

            bot.infinity_polling(
                skip_pending=True,
                timeout=30,
                long_polling_timeout=30
            )

        except KeyboardInterrupt:

            print(
                "🛑 Bot stopped."
            )


        except Exception as error:

            print(
                "❌ Polling error:"
            )

            print(
                repr(error)
            )


    # ----------------------------------------------
    # OPTIONAL DIRECT RENDER RUN
    # Gunicorn normally handles Render instead.
    # ----------------------------------------------

    else:

        port = int(
            os.getenv(
                "PORT",
                "10000"
            )
        )

        print(
            "☁️ Starting Render web server..."
        )

        app.run(
            host="0.0.0.0",
            port=port
        )