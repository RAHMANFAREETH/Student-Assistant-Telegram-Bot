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

HELP = "ℹ️ Help"


# ==================================================
# UNIVERSAL NAVIGATION BUTTONS
# ==================================================

MAIN_MENU = "🏠 Main Menu"
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
    (HELP,),
]


GLOBAL_BUTTONS = {
    button
    for row in MAIN_MENU_ROWS
    for button in row
}
# Review statistics is available in the Flashcards submenu. Treat it as
# a global action so other modules do not consume its text as form data.
GLOBAL_BUTTONS.add(REVIEW_STATS)


NAVIGATION_BUTTONS = {
    MAIN_MENU,
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
