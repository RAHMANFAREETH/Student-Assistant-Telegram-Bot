import os

import telebot
from flask import Flask, request

from config import (
    BOT_TOKEN,
    WEBHOOK_SECRET,
)


# ==================================================
# CENTRAL NAVIGATION
# ==================================================

from ui_v57 import greeting, get_language, register_ui_v57_handlers
from user_help_v79 import build_quick_help_text, register_user_help_v79_handlers
# V6.6 Revision Hub integration
from revision_hub_v66 import register_revision_hub_v66_handlers
from achievements_v58 import register_achievements_v58_handlers
from ai_ops_v60 import register_ai_ops_v60_handlers
from broadcast_v710 import register_broadcast_handlers, register_known_broadcast_handlers, track_known_private_user

from navigation import (
    build_main_menu_markup,
)

from study_context_ai import register_study_context_handlers
from ai_study_assistant import register_ai_study_assistant_handlers

from navigation_handlers import (
    register_navigation_handlers,
)


# ==================================================
# SYSTEM HEALTH
# ==================================================

from system_health import (
    register_system_health_handlers,
)

from safe_utils import (
    split_telegram_text,
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
# VOICE + LANGUAGE MODULES
# ==================================================

from voice_notes import register_voice_note_handlers
from language_tools import register_language_tool_handlers


# ==================================================
# LEARNING MODULES
# ==================================================

from flashcards import register_flashcard_handlers
from spaced_repetition import register_spaced_repetition_handlers
from quiz import register_quiz_handlers
from progress import register_progress_handlers


# ==================================================
# EXAMS + ATTENDANCE + GOALS
# ==================================================

from exam_planner import register_exam_handlers
from attendance import register_attendance_handlers
from study_goals import register_study_goal_handlers


# ==================================================
# SEMESTER + GPA
# ==================================================

from semesters import register_semester_handlers
from grades_gpa import register_grade_handlers


# ==================================================
# TODAY HUB + SEARCH + EXPORT
# ==================================================

from today_hub import register_today_hub_handlers
from global_search import register_global_search_handlers
from data_export import register_data_export_handlers


# ==================================================
# REVISION + STUDY STREAK
# ==================================================

from revision_planner import register_revision_planner_handlers
from study_streak import register_study_streak_handlers


# ==================================================
# SMART STUDY INSIGHTS
# ==================================================

from smart_insights import register_smart_insight_handlers


# ==================================================
# SMART NOTIFICATIONS
# ==================================================

from notification_preferences import (
    register_notification_preference_handlers,
)


# ==================================================
# STUDENT RESOURCES
# ==================================================

from student_resources import (
    register_student_resource_handlers,
)


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

def show_main_menu(chat_id, first_name="Friend"):
    """V5.7 compact menu; existing modules still receive original button text."""
    bot.send_message(
        chat_id,
        greeting(first_name, chat_id),
        reply_markup=build_main_menu_markup(),
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
    """One clear message instead of the obsolete multi-part V5.4 manual."""
    bot.send_message(
        message.chat.id,
        build_quick_help_text(get_language(message.from_user.id)),
        reply_markup=build_main_menu_markup(),
    )


# ==================================================
# HELP BUTTON
# ==================================================

@bot.message_handler(
    func=lambda message:
    message.text == "ℹ️ Help"
)
def help_button(message):
    help_command(
        message
    )


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
# V5.4 REVIEW HANDLERS — register before legacy module handlers
# so the new main-menu button and /reviews are handled first.
# ==================================================

# V5.7 category handlers MUST come before legacy handlers.
broadcast_service = register_broadcast_handlers(bot)
register_known_broadcast_handlers(bot, broadcast_service)
register_ui_v57_handlers(bot, show_main_menu)
# V7.9 finder runs before stateful legacy forms.
register_user_help_v79_handlers(bot)
register_achievements_v58_handlers(bot, show_main_menu)
register_revision_hub_v66_handlers(bot, show_main_menu)
register_ai_ops_v60_handlers(bot)

# V9.0 optional Academic Toolkit. Register before the older V8 state handlers.
# V9.1 administrator-reviewed age eligibility (before V9 and V8 handlers).
from v91_access_bot import register_v91_access_handlers
register_v91_access_handlers(bot)

# V9.2 optional, administrator-only dashboard. Register before V9/V8 handlers.
from v92_admin_bot import register_v92_admin_handlers
register_v92_admin_handlers(bot)

# V9.3 reliability diagnostics, before legacy stateful handlers.
from v93_reliability_bot import register_v93_reliability_handlers
register_v93_reliability_handlers(bot)

# V10.0 opt-in Learning Lab. Register before V9/V8 state handlers.
from v10_bot import register_v10_handlers
register_v10_handlers(bot)

from v9_bot import register_v9_handlers
register_v9_handlers(bot, show_main_menu)

# V8.0 Study Lab — opt-in and registered before stateful legacy workflows.
from v8_bot import register_v8_handlers
register_v8_handlers(bot, show_main_menu)

register_study_context_handlers(bot, show_main_menu)
register_ai_study_assistant_handlers(bot, show_main_menu)

register_spaced_repetition_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER CORE MODULES
# ==================================================

register_pdf_handlers(
    bot,
    show_main_menu,
)

register_note_handlers(
    bot,
    show_main_menu,
)

register_translation_handlers(
    bot,
    show_main_menu,
)

register_reminder_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER ACADEMIC MODULES
# ==================================================

register_subject_handlers(
    bot,
    show_main_menu,
)

register_assignment_handlers(
    bot,
    show_main_menu,
)

register_study_material_handlers(
    bot,
    show_main_menu,
)

register_timetable_handlers(
    bot,
    show_main_menu,
)

register_study_planner_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER VOICE + LANGUAGE MODULES
# ==================================================

register_voice_note_handlers(
    bot,
    show_main_menu,
)

register_language_tool_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER LEARNING MODULES
# ==================================================

register_flashcard_handlers(
    bot,
    show_main_menu,
)

register_quiz_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER EXAMS + ATTENDANCE + GOALS
# ==================================================

register_exam_handlers(
    bot,
    show_main_menu,
)

register_attendance_handlers(
    bot,
    show_main_menu,
)

register_study_goal_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER SEMESTER + GPA
# ==================================================

register_semester_handlers(
    bot,
    show_main_menu,
)

register_grade_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER TODAY HUB + SEARCH + EXPORT
# ==================================================

register_today_hub_handlers(
    bot,
    show_main_menu,
)

register_global_search_handlers(
    bot,
    show_main_menu,
)

register_data_export_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER REVISION + STUDY STREAK
# ==================================================

register_revision_planner_handlers(
    bot,
    show_main_menu,
)

register_study_streak_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER SMART INSIGHTS
# ==================================================

register_smart_insight_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER SMART NOTIFICATIONS
# ==================================================

register_notification_preference_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER STUDENT RESOURCES
# ==================================================

register_student_resource_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER DASHBOARD + PROGRESS
# ==================================================

register_dashboard_handlers(
    bot,
    show_main_menu,
)

register_progress_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# REGISTER SYSTEM HEALTH
# ==================================================

register_system_health_handlers(
    bot
)


# ==================================================
# REGISTER UNIVERSAL NAVIGATION
# Keep this near the end so module-specific handlers
# are registered first.
# ==================================================

register_navigation_handlers(
    bot,
    show_main_menu,
)


# ==================================================
# HEALTH CHECK
# ==================================================

# V8.0 Mini App: read-only and Telegram-signature protected.
from v8_miniapp import register_v8_miniapp
register_v8_miniapp(app)

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
        "version": ("8.0-pilot" if os.getenv("V8_ENABLED", "").lower() in ("true", "1", "yes") else "7.9"),
        "database": "Supabase",
        "deployment": "Render",

        "architecture": {
            "central_navigation": True,
            "universal_main_menu": True,
            "universal_cancel": True,
            "system_health": True,
        },

        "languages": [
            "Tamil",
            "English",
            "Sinhala",
            "Arabic",
        ],

        "features": {
            "pdf_tools": True,
            "notes": True,
            "translator": True,
            "reminders": True,
            "subjects": True,
            "assignments": True,
            "study_materials": True,
            "timetable": True,
            "study_planner": True,
            "voice_notes": True,
            "language_tools": True,
            "flashcards": True,
            "spaced_repetition": True,
            "ai_study_assistant": True,
            "quiz": True,
            "exams": True,
            "attendance": True,
            "study_goals": True,
            "semesters": True,
            "grades_gpa": True,
            "today_hub": True,
            "global_search": True,
            "revision_planner": True,
            "study_streak": True,
            "smart_insights": True,
            "smart_notifications": True,
            "student_resources": True,
            "data_export": True,
            "dashboard": True,
            "progress": True,
        },

        "resources": {
            "courses": (
                "https://t.me/tamil_courses_foryou"
            ),
            "past_papers": (
                "https://t.me/PastpaperTamilmediumALOL"
            ),
            "admin": (
                "https://t.me/Bestfriendlanka"
            ),
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

        track_known_private_user(update)

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
        # Re-register directly: avoid a temporary outage caused by deleting
        # the working webhook on each Render/Gunicorn worker startup.
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
            "🎓 Student Assistant Bot V7.9 enabled."
        )

        print(
            "🧩 Central Navigation enabled."
        )

        print(
            "🛠 System Health enabled."
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
            "🌍 Language Tools enabled."
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
            "🎓 Semester Manager enabled."
        )

        print(
            "📊 Grades & GPA enabled."
        )

        print(
            "☀️ Today Hub enabled."
        )

        print(
            "🔎 Global Search enabled."
        )

        print(
            "📚 Revision Planner enabled."
        )

        print(
            "🔥 Study Streak enabled."
        )

        print(
            "🧠 Smart Study Insights enabled."
        )

        print(
            "🔔 Smart Notifications enabled."
        )

        print(
            "📢 Student Resources enabled."
        )

        print(
            "📦 Data Export enabled."
        )

        print(
            "📊 Dashboard enabled."
        )

        print(
            "📈 Study Progress enabled."
        )

        try:
            # Local development uses Telegram polling.
            # Remove the Render webhook before polling.

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

    else:
        # Render normally starts using:
        #
        # gunicorn main:app --bind 0.0.0.0:$PORT

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
