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

from ui_v57 import greeting, register_ui_v57_handlers

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
    help_text = (
            "🎓 STUDENT ASSISTANT BOT V5.4\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🧩 CORE STABILITY\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Central navigation system\n"
            "• Shared global menu buttons\n"
            "• Universal Main Menu / Cancel\n"
            "• Safer state handling\n"
            "• System health checker\n\n"

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
            "• Add reminders\n"
            "• View reminders\n"
            "• Delete reminders\n"
            "• Automatic Telegram alerts\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📚 SUBJECTS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Add subjects\n"
            "• Subject codes\n"
            "• View subjects\n"
            "• Delete subjects\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📅 ASSIGNMENTS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Add assignments\n"
            "• Description\n"
            "• Deadline\n"
            "• Priority\n"
            "• Subject linking\n"
            "• Due today\n"
            "• Due this week\n"
            "• Mark completed\n"
            "• Delete assignments\n"
            "• Deadline alerts\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📚 STUDY MATERIALS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• PDF / DOCX / TXT\n"
            "• OCR scanned PDFs\n"
            "• Subject linking\n"
            "• Read extracted text\n"
            "• Search materials\n"
            "• Summaries\n"
            "• Key points\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🗓 TIMETABLE\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Weekly classes\n"
            "• Start/end times\n"
            "• Subject linking\n"
            "• Locations\n"
            "• Today's timetable\n"
            "• Weekly timetable\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "⏱ STUDY PLANNER\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• 25-minute focus\n"
            "• 50-minute focus\n"
            "• Custom sessions\n"
            "• Subject linking\n"
            "• Automatic completion alerts\n"
            "• Weekly analytics\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🎙 VOICE NOTES\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Save voice notes\n"
            "• Organize by subject\n"
            "• Replay notes\n"
            "• Optional speech-to-text\n"
            "• View transcripts\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🌍 LANGUAGE TOOLS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🇱🇰 Tamil\n"
            "🇬🇧 English\n"
            "🇱🇰 Sinhala\n"
            "🇸🇦 Arabic\n\n"
            "• Vocabulary\n"
            "• Meanings\n"
            "• Examples\n"
            "• Practice\n"
            "• Pronunciation\n"
            "• Mastery tracking\n"
            "• Text tools\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🧠 FLASHCARDS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Add flashcards\n"
            "• Subject-based cards\n"
            "• Study mode\n"
            "• Mastery tracking\n"
            "• V5.4: Due reviews & adaptive scheduling\n"
            "• Again / Hard / Good / Easy\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "❓ QUIZ\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• MCQ quizzes\n"
            "• Quiz by subject\n"
            "• Immediate feedback\n"
            "• Quiz scores\n"
            "• Quiz history\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📝 EXAM PLANNER\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Add exams\n"
            "• Exam date/time\n"
            "• Location\n"
            "• Notes\n"
            "• Upcoming exams\n"
            "• Automatic exam alerts\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "✅ ATTENDANCE\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Present\n"
            "• Absent\n"
            "• Late\n"
            "• Excused\n"
            "• Attendance history\n"
            "• Attendance percentage\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🎯 STUDY GOALS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Create goals\n"
            "• Link to subject\n"
            "• Target date\n"
            "• Active goals\n"
            "• Completed goals\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🎓 SEMESTERS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Create semesters\n"
            "• GPA scale\n"
            "• Start/end dates\n"
            "• Active semester\n"
            "• Semester history\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📊 GRADES & GPA\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Course credits\n"
            "• Grade labels\n"
            "• Grade points\n"
            "• Percentage scores\n"
            "• Weighted GPA\n"
            "• Semester GPA\n"
            "• Cumulative GPA\n"
            "• Target GPA calculator\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "☀️ TODAY HUB\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Today's classes\n"
            "• Assignments due today\n"
            "• Exams in next 7 days\n"
            "• Active goals\n"
            "• Overdue goals\n"
            "• Study minutes today\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🔎 GLOBAL SEARCH\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Search across:\n"
            "• Notes\n"
            "• Materials\n"
            "• Assignments\n"
            "• Exams\n"
            "• Goals\n"
            "• Voice transcripts\n"
            "• Vocabulary\n"
            "• Flashcards\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📚 REVISION PLANNER\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Create revision plan from exam\n"
            "• Enter topics one per line\n"
            "• Auto-distribute topics by day\n"
            "• Today's revision tasks\n"
            "• Complete revision tasks\n"
            "• Revision progress\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🔥 STUDY STREAK\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Daily study target\n"
            "• Today's study minutes\n"
            "• Current streak\n"
            "• Best streak\n"
            "• Last 7 days activity\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🧠 SMART INSIGHTS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Smart Study Insights\n"
            "• Subject Health scores\n"
            "• Study priority ranking\n"
            "• Weekly study review\n"
            "• Rule-based recommendations\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🔔 SMART NOTIFICATIONS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Daily morning study brief\n"
            "• Weekly study review\n"
            "• Custom notification time\n"
            "• Custom weekly day\n"
            "• Timezone support\n"
            "• Supabase Cron delivery\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📢 STUDENT RESOURCES\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Tamil-medium courses group\n"
            "• Tamil-medium A/L & O/L past papers\n"
            "• Contact Admin on Telegram\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📦 DATA EXPORT\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Personal academic backup\n"
            "• Compressed JSON\n"
            "• Excludes bot/API secrets\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📊 DASHBOARD\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Subjects\n"
            "• Materials\n"
            "• Notes\n"
            "• Reminders\n"
            "• Flashcards\n"
            "• Assignments\n"
            "• Due today\n"
            "• Completion percentage\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "📈 PROGRESS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Flashcard mastery\n"
            "• Quiz statistics\n"
            "• Assignment progress\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "🛠 SYSTEM HEALTH\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• Required environment variables\n"
            "• Optional integration keys\n"
            "• Expected Supabase tables\n"
            "• Does not display secret values\n\n"

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
            "/reviews\n"
            "/reviewstats\n"
            "/quiz\n"
            "/exams\n"
            "/attendance\n"
            "/goals\n"
            "/semesters\n"
            "/gpa\n"
            "/todayhub\n"
            "/search\n"
            "/revision\n"
            "/streak\n"
            "/insights\n"
            "/notifications\n"
            "/resources\n"
            "/export\n"
            "/dashboard\n"
            "/progress\n"
            "/translate\n"
            "/ai\n"
            "/aiclear\n"
            "/aistats\n"
            "/healthcheck\n"
            "/systemhealth"
    )

    for part in split_telegram_text(
        help_text
    ):
        bot.send_message(
            message.chat.id,
            part,
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
register_ui_v57_handlers(bot, show_main_menu)

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
        "version": "5.7",
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
        bot.remove_webhook()

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
            "🎓 Student Assistant Bot V5.5 enabled."
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
