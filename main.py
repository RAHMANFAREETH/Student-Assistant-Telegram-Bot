import os

import telebot
from flask import Flask, request
from telebot import types

from config import (
    BOT_TOKEN,
    WEBHOOK_SECRET,
)


# ==================================================
# CORE MODULES
# ==================================================

from pdf_tools import register_pdf_handlers
from notes import register_note_handlers
from translate import register_translation_handlers
from reminders import register_reminder_handlers


# ==================================================
# ACADEMIC MODULES
# ==================================================

from subjects import register_subject_handlers
from assignments import register_assignment_handlers
from study_materials import register_study_material_handlers
from timetable import register_timetable_handlers
from study_planner import register_study_planner_handlers


# ==================================================
# VOICE + MULTILINGUAL TOOLS
# ==================================================

from voice_notes import register_voice_note_handlers
from language_tools import register_language_tool_handlers


# ==================================================
# LEARNING MODULES
# ==================================================

from flashcards import register_flashcard_handlers
from quiz import register_quiz_handlers
from progress import register_progress_handlers


# ==================================================
# V4.6 MODULES
# ==================================================

from exam_planner import register_exam_handlers
from attendance import register_attendance_handlers
from study_goals import register_study_goal_handlers


# ==================================================
# DASHBOARD
# ==================================================

from dashboard import register_dashboard_handlers


# ==================================================
# TELEGRAM BOT
# ==================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    threaded=False,
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
    first_name="Friend",
):

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2,
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
            "📚 Subjects"
        ),

        types.KeyboardButton(
            "📅 Assignments"
        ),

        types.KeyboardButton(
            "📚 Study Materials"
        ),

        types.KeyboardButton(
            "🗓 Timetable"
        ),

        types.KeyboardButton(
            "⏱ Study Planner"
        ),

        types.KeyboardButton(
            "🎙 Voice Notes"
        ),

        types.KeyboardButton(
            "🌍 Language Tools"
        ),

        types.KeyboardButton(
            "🧠 Flashcards"
        ),

        types.KeyboardButton(
            "❓ Quiz"
        ),

        types.KeyboardButton(
            "📝 Exams"
        ),

        types.KeyboardButton(
            "✅ Attendance"
        ),

        types.KeyboardButton(
            "🎯 Study Goals"
        ),

        types.KeyboardButton(
            "📊 Dashboard"
        ),

        types.KeyboardButton(
            "📈 Progress"
        ),

        types.KeyboardButton(
            "ℹ️ Help"
        ),
    )

    bot.send_message(
        chat_id,
        (
            f"👋 Hello {first_name}!\n\n"

            "🎓 Student Assistant Bot V4.6\n\n"

            "Choose what you want to do:\n\n"

            "📄 PDF & Document Tools\n"
            "📝 Notes\n"
            "🌐 Translation\n"
            "⏰ Study Reminders\n\n"

            "📚 Subjects\n"
            "📅 Assignments\n"
            "📚 Study Materials\n"
            "🗓 Timetable\n\n"

            "⏱ Study Planner\n"
            "🎙 Voice Notes\n"
            "🌍 Language Tools\n\n"

            "🧠 Flashcards\n"
            "❓ Quiz\n\n"

            "📝 Exams\n"
            "✅ Attendance\n"
            "🎯 Study Goals\n\n"

            "📊 Dashboard\n"
            "📈 Study Progress\n"
            "ℹ️ Help"
        ),
        reply_markup=markup,
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
        "▶️ /start received from:",
        message.from_user.id,
    )

    show_main_menu(
        message.chat.id,
        first_name,
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
        (
            "🎓 STUDENT ASSISTANT BOT V4.6\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📄 PDF TOOLS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Merge PDFs\n"
            "• Extract pages\n"
            "• Images → PDF\n"
            "• Rotate PDF\n"
            "• Protect PDF\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📝 NOTES\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Add notes\n"
            "• View notes\n"
            "• Search notes\n"
            "• Delete notes\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🌐 TRANSLATOR\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Text translation\n"
            "• Tamil\n"
            "• English\n"
            "• Sinhala\n"
            "• Arabic\n"
            "• Translation history\n"
            "• Pronunciation\n"
            "• Document translation\n"
            "• OCR image translation\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "⏰ STUDY REMINDERS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Add reminder\n"
            "• View reminders\n"
            "• Delete reminder\n"
            "• Automatic Telegram alerts\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📚 SUBJECTS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Add subject\n"
            "• Subject code\n"
            "• View subjects\n"
            "• Delete subjects\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📅 ASSIGNMENTS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Add assignment\n"
            "• Add description\n"
            "• Set deadline\n"
            "• Set priority\n"
            "• Link to subject\n"
            "• Upcoming assignments\n"
            "• Due today\n"
            "• Due this week\n"
            "• Mark completed\n"
            "• Delete assignment\n"
            "• Automatic deadline alerts\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📚 STUDY MATERIALS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Upload PDF\n"
            "• Upload DOCX\n"
            "• Upload TXT\n"
            "• Link material to subject\n"
            "• OCR scanned PDFs\n"
            "• Read material\n"
            "• Search materials\n"
            "• Summarize material\n"
            "• Extract key points\n"
            "• Delete material\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🗓 TIMETABLE\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Add weekly classes\n"
            "• Link class to subject\n"
            "• Class start/end time\n"
            "• Classroom/location\n"
            "• Today's timetable\n"
            "• Weekly timetable\n"
            "• Delete class\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "⏱ STUDY PLANNER\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• 25-minute focus session\n"
            "• 50-minute focus session\n"
            "• Custom study session\n"
            "• Link session to subject\n"
            "• View active session\n"
            "• End session early\n"
            "• Automatic completion alert\n"
            "• Weekly study analytics\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🎙 VOICE NOTES\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Save voice notes\n"
            "• Organize by subject\n"
            "• Replay voice notes\n"
            "• Optional speech-to-text\n"
            "• Store transcripts\n"
            "• View transcripts\n"
            "• Delete voice notes\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🌍 LANGUAGE TOOLS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Supported:\n"
            "🇱🇰 Tamil\n"
            "🇬🇧 English\n"
            "🇱🇰 Sinhala\n"
            "🇸🇦 Arabic\n\n"
            "• Add vocabulary\n"
            "• Meaning in any language\n"
            "• Example sentences\n"
            "• Practice vocabulary\n"
            "• Mastery tracking\n"
            "• Pronunciation\n"
            "• Text analysis\n"
            "• Arabic ḥarakāt removal\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🧠 FLASHCARDS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Add flashcards\n"
            "• Organize by subject\n"
            "• Study flashcards\n"
            "• Show answers\n"
            "• I knew it\n"
            "• Practice again\n"
            "• Mastery tracking\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "❓ QUIZ ENGINE\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• MCQ quizzes\n"
            "• Quiz by subject\n"
            "• Questions from flashcards\n"
            "• Immediate feedback\n"
            "• Quiz scores\n"
            "• Quiz history\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📝 EXAM PLANNER\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Add exams\n"
            "• Link exam to subject\n"
            "• Exam date/time\n"
            "• Exam location\n"
            "• Exam notes/syllabus\n"
            "• Upcoming exams\n"
            "• Delete exams\n"
            "• 7-day alerts\n"
            "• 24-hour alerts\n"
            "• 1-hour alerts\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "✅ ATTENDANCE\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Present\n"
            "• Absent\n"
            "• Late\n"
            "• Excused\n"
            "• Attendance by subject\n"
            "• Attendance history\n"
            "• Attendance percentage\n"
            "• Delete attendance record\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🎯 STUDY GOALS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Add study goals\n"
            "• Link goal to subject\n"
            "• Goal description\n"
            "• Target date\n"
            "• Active goals\n"
            "• Mark goal completed\n"
            "• Completed-goal history\n"
            "• Delete goals\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📊 DASHBOARD\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Subjects\n"
            "• Study materials\n"
            "• Notes\n"
            "• Reminders\n"
            "• Flashcards\n"
            "• Assignments\n"
            "• Due today\n"
            "• Completion percentage\n"
            "• Next assignment\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📈 STUDY PROGRESS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Flashcard mastery\n"
            "• Quiz attempts\n"
            "• Average quiz score\n"
            "• Best quiz score\n"
            "• Assignment progress\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "⌨️ COMMANDS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "/start\n"
            "/help\n"
            "/id\n"
            "/subjects\n"
            "/assignments\n"
            "/today\n"
            "/materials\n"
            "/timetable\n"
            "/planner\n"
            "/voice\n"
            "/languages\n"
            "/flashcards\n"
            "/quiz\n"
            "/exams\n"
            "/attendance\n"
            "/goals\n"
            "/dashboard\n"
            "/progress\n"
            "/translate"
        ),
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
        (
            "👤 User ID:\n"
            f"{message.from_user.id}\n\n"

            "💬 Chat ID:\n"
            f"{message.chat.id}"
        ),
    )


# ==================================================
# REGISTER PDF TOOLS
# ==================================================

register_pdf_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER NOTES
# ==================================================

register_note_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER TRANSLATOR
# ==================================================

register_translation_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER REMINDERS
# ==================================================

register_reminder_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER SUBJECTS
# ==================================================

register_subject_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER ASSIGNMENTS
# ==================================================

register_assignment_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER STUDY MATERIALS
# ==================================================

register_study_material_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER TIMETABLE
# ==================================================

register_timetable_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER STUDY PLANNER
# ==================================================

register_study_planner_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER VOICE NOTES
# ==================================================

register_voice_note_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER LANGUAGE TOOLS
# ==================================================

register_language_tool_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER FLASHCARDS
# ==================================================

register_flashcard_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER QUIZ
# ==================================================

register_quiz_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER EXAM PLANNER
# ==================================================

register_exam_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER ATTENDANCE
# ==================================================

register_attendance_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER STUDY GOALS
# ==================================================

register_study_goal_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER DASHBOARD
# ==================================================

register_dashboard_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER PROGRESS
# ==================================================

register_progress_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# HEALTH CHECK
# ==================================================

@app.route(
    "/",
    methods=[
        "GET",
        "HEAD",
    ],
)
def home():

    return {
        "status": "ok",
        "bot": "Student Assistant Bot",
        "version": "4.6",
        "database": "Supabase",
        "deployment": "Render",
        "languages": [
            "Tamil",
            "English",
            "Sinhala",
            "Arabic",
        ],
        "features": {
            "subjects": True,
            "assignments": True,
            "materials": True,
            "timetable": True,
            "study_planner": True,
            "voice_notes": True,
            "language_tools": True,
            "flashcards": True,
            "quiz": True,
            "exams": True,
            "attendance": True,
            "study_goals": True,
            "dashboard": True,
            "progress": True,
        },
    }, 200


# ==================================================
# TELEGRAM WEBHOOK
# ==================================================

@app.route(
    "/telegram-webhook",
    methods=["POST"],
)
def telegram_webhook():

    # ==============================================
    # VERIFY TELEGRAM SECRET
    # ==============================================

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
            403,
        )


    # ==============================================
    # PROCESS TELEGRAM UPDATE
    # ==============================================

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
            update.update_id,
        )

        bot.process_new_updates(
            [update]
        )

        print(
            "✅ Telegram update processed:",
            update.update_id,
        )

        return (
            "OK",
            200,
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
            400,
        )


# ==================================================
# RENDER WEBHOOK SETUP
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


        # Set current webhook
        result = bot.set_webhook(

            url=webhook_url,

            secret_token=WEBHOOK_SECRET,

            allowed_updates=[
                "message",
                "callback_query",
            ],
        )


        print(
            "🌐 Webhook URL:",
            webhook_url,
        )


        print(
            "✅ Webhook configured:",
            result,
        )


        # Get webhook information
        info = bot.get_webhook_info()


        print(
            "📡 Telegram webhook information:"
        )


        print(
            "URL:",
            info.url,
        )


        print(
            "Pending updates:",
            info.pending_update_count,
        )


        if info.last_error_message:

            print(
                "⚠️ Last webhook error:",
                info.last_error_message,
            )


    except Exception as error:

        print(
            "❌ Webhook setup failed:"
        )

        print(
            repr(error)
        )


# ==================================================
# RENDER INITIALIZATION
# ==================================================

if os.getenv(
    "RENDER_EXTERNAL_URL"
):

    setup_render_webhook()


# ==================================================
# LOCAL DEVELOPMENT
# ==================================================

if __name__ == "__main__":

    # ==============================================
    # LOCAL WINDOWS / VS CODE MODE
    # ==============================================

    if not os.getenv(
        "RENDER_EXTERNAL_URL"
    ):

        print(
            "✅ Student Assistant Bot running locally..."
        )

        print(
            "🌐 Supabase database enabled."
        )

        print(
            "📡 Telegram polling enabled."
        )

        print(
            "🎓 Student Assistant Bot V4.6 enabled."
        )

        print(
            "📄 PDF Tools enabled."
        )

        print(
            "📝 Notes enabled."
        )

        print(
            "🌐 Translator enabled."
        )

        print(
            "⏰ Study Reminders enabled."
        )

        print(
            "📚 Subjects enabled."
        )

        print(
            "📅 Assignments enabled."
        )

        print(
            "📚 Study Materials enabled."
        )

        print(
            "🗓 Timetable enabled."
        )

        print(
            "⏱ Study Planner enabled."
        )

        print(
            "🎙 Voice Notes enabled."
        )

        print(
            "🌍 Multilingual Language Tools enabled."
        )

        print(
            "🇱🇰 Tamil enabled."
        )

        print(
            "🇬🇧 English enabled."
        )

        print(
            "🇱🇰 Sinhala enabled."
        )

        print(
            "🇸🇦 Arabic enabled."
        )

        print(
            "🧠 Flashcards enabled."
        )

        print(
            "❓ Quiz Engine enabled."
        )

        print(
            "📝 Exam Planner enabled."
        )

        print(
            "✅ Attendance Tracker enabled."
        )

        print(
            "🎯 Study Goals enabled."
        )

        print(
            "📊 Dashboard enabled."
        )

        print(
            "📈 Study Progress enabled."
        )


        try:

            # ======================================
            # LOCAL MODE USES POLLING.
            # REMOVE RENDER WEBHOOK FIRST.
            # ======================================

            bot.remove_webhook()


            bot.infinity_polling(

                skip_pending=True,

                timeout=30,

                long_polling_timeout=30,
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


    # ==============================================
    # DIRECT RENDER SERVER MODE
    #
    # Render normally starts using:
    #
    # gunicorn main:app --bind 0.0.0.0:$PORT
    # ==============================================

    else:

        port = int(
            os.getenv(
                "PORT",
                "10000",
            )
        )


        print(
            "☁️ Starting Render web server..."
        )


        app.run(

            host="0.0.0.0",

            port=port,
        )