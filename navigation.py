from telebot import types


# ==================================================
# MAIN MENU BUTTONS
# One source of truth for the whole bot.
# ==================================================

PDF_TOOLS = "📄 PDF Tools"
NOTES = "📝 Notes"
TRANSLATE = "🌐 Translate"
REMINDERS = "⏰ Study Reminder"

SUBJECTS = "📚 Subjects"
ASSIGNMENTS = "📅 Assignments"
MATERIALS = "📚 Study Materials"
TIMETABLE = "🗓 Timetable"

STUDY_PLANNER = "⏱ Study Planner"
VOICE_NOTES = "🎙 Voice Notes"
LANGUAGE_TOOLS = "🌍 Language Tools"
FLASHCARDS = "🧠 Flashcards"
DUE_REVIEWS = "🧠 Due Reviews"
REVIEW_STATS = "📊 Review Stats"

QUIZ = "❓ Quiz"
EXAMS = "📝 Exams"
ATTENDANCE = "✅ Attendance"
STUDY_GOALS = "🎯 Study Goals"

SEMESTERS = "🎓 Semesters"
GRADES_GPA = "📊 Grades & GPA"

TODAY_HUB = "☀️ Today Hub"
GLOBAL_SEARCH = "🔎 Global Search"

REVISION_PLANNER = "📚 Revision Planner"
STUDY_STREAK = "🔥 Study Streak"

SMART_INSIGHTS = "🧠 Smart Insights"
SMART_NOTIFICATIONS = "🔔 Smart Notifications"

STUDENT_RESOURCES = "📢 Student Resources"
DATA_EXPORT = "📦 Export My Data"

DASHBOARD = "📊 Dashboard"
PROGRESS = "📈 Progress"

ASK_AI = "🤖 Ask AI"
ASK_NOTES = "📝 Ask My Notes"
ASK_PDF = "📄 Ask My PDF"


HELP = "ℹ️ Help"


# ==================================================
# UNIVERSAL NAVIGATION BUTTONS
# ==================================================

MAIN_MENU = "🏠 Main Menu"
LEGACY_MAIN_MENU = "⬅️ Main Menu"
CANCEL = "❌ Cancel"
BACK = "⬅️ Back"
BACK_ALT = "🔙 Back"
REVISION_BACK = "🔙 Revision Menu"


MAIN_MENU_ROWS = [
    (PDF_TOOLS, NOTES),
    (TRANSLATE, REMINDERS),
    (SUBJECTS, ASSIGNMENTS),
    (MATERIALS, TIMETABLE),
    (STUDY_PLANNER, VOICE_NOTES),
    (LANGUAGE_TOOLS, FLASHCARDS),
    (DUE_REVIEWS,),
    (QUIZ, EXAMS),
    (ATTENDANCE, STUDY_GOALS),
    (SEMESTERS, GRADES_GPA),
    (TODAY_HUB, GLOBAL_SEARCH),
    (REVISION_PLANNER, STUDY_STREAK),
    (SMART_INSIGHTS, SMART_NOTIFICATIONS),
    (STUDENT_RESOURCES, DATA_EXPORT),
    (DASHBOARD, PROGRESS),
    (ASK_AI,),
    (ASK_NOTES, ASK_PDF),
    (HELP,),
]

# V5.7 CATEGORY MENU START
# Retain the exact legacy button labels for all older feature handlers.
LEGACY_MENU_ROWS = MAIN_MENU_ROWS

UI_AI = "🤖 AI & Questions"
UI_STUDY = "📚 Study Tools"
UI_PLAN = "📅 Plans & Reminders"
UI_PRACTICE = "🧠 Practice & Quiz"
UI_LANGUAGES = "🌍 Languages"
UI_PROGRESS = "📊 My Progress"
UI_FILES = "🎙 Voice & PDF"
UI_MORE = "📦 More Tools"
UI_HELP = "❓ Help & Tutorial"
UI_LANGUAGE = "🌐 Menu Language"
UI_CATEGORIES = "↩️ All Categories"

MAIN_MENU_ROWS = [
    (UI_AI, UI_STUDY),
    (UI_PLAN, UI_PRACTICE),
    (UI_LANGUAGES, UI_PROGRESS),
    (UI_FILES, UI_MORE),
    (UI_HELP, UI_LANGUAGE),
]

# V5.7 CATEGORY MENU END


GLOBAL_BUTTONS = {
    button
    for row in MAIN_MENU_ROWS
    for button in row
}
# Review statistics is available in the Flashcards submenu. Treat it as
# a global action so other modules do not consume its text as form data.
GLOBAL_BUTTONS.add(REVIEW_STATS)
GLOBAL_BUTTONS.update(button for row in LEGACY_MENU_ROWS for button in row)
GLOBAL_BUTTONS.update({
    UI_CATEGORIES,
    "🇬🇧 English", "🇱🇰 தமிழ்", "🇱🇰 සිංහල", "🇸🇦 العربية",
    "🚀 Getting Started", "🤖 Ask AI Guide", "📄 Ask My PDF Guide",
    "🧠 Flashcards Guide", "📅 Study Planning Guide",
    "🎙 Voice Notes Guide", "🔒 Privacy Tips",
})



# V5.8 achievements navigation
# Add BEFORE ALL_NAVIGATION_BUTTONS is constructed; preserve older buttons.
GLOBAL_BUTTONS.update({"🏆 Achievements", "⭐ My Level"})

NAVIGATION_BUTTONS = {
    MAIN_MENU,
    LEGACY_MAIN_MENU,
    CANCEL,
    BACK,
    BACK_ALT,
    REVISION_BACK,
}


ALL_NAVIGATION_BUTTONS = (
    GLOBAL_BUTTONS
    | NAVIGATION_BUTTONS
)


def is_main_menu_button(
    text,
):
    return bool(
        text
        and text in GLOBAL_BUTTONS
    )


def is_navigation_button(
    text,
):
    return bool(
        text
        and text in NAVIGATION_BUTTONS
    )


def should_yield_to_navigation(
    text,
):
    """
    Use inside state handlers.

    Example:

        if should_yield_to_navigation(text):
            state.pop(chat_id, None)
            return ContinueHandling()

    Commands also yield automatically.
    """

    if not text:
        return False

    return (
        text.startswith("/")
        or text in ALL_NAVIGATION_BUTTONS
    )


def build_main_menu_markup():
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2,
    )

    for row in MAIN_MENU_ROWS:
        markup.row(
            *[
                types.KeyboardButton(
                    button
                )
                for button in row
            ]
        )

    return markup


def build_cancel_markup():
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2,
    )

    markup.row(
        types.KeyboardButton(
            CANCEL
        ),
        types.KeyboardButton(
            MAIN_MENU
        ),
    )

    return markup


def build_back_markup(
    back_label=BACK,
):
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2,
    )

    markup.row(
        types.KeyboardButton(
            back_label
        ),
        types.KeyboardButton(
            MAIN_MENU
        ),
    )

    return markup
