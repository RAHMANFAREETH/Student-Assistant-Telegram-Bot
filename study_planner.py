from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase
from subjects import (
    get_subjects,
    get_subject_by_id,
    subject_display,
)
from study_analytics import build_study_analytics


planner_state = {}
SRI_LANKA_TZ = ZoneInfo("Asia/Colombo")

GLOBAL_BUTTONS = {
    "📄 PDF Tools",
    "📝 Notes",
    "🌐 Translate",
    "⏰ Study Reminder",
    "📚 Subjects",
    "📅 Assignments",
    "📚 Study Materials",
    "🧠 Flashcards",
    "❓ Quiz",
    "📊 Dashboard",
    "📈 Progress",
    "🗓 Timetable",
    "⏱ Study Planner",
    "ℹ️ Help",
}


def active_session(
    user_id,
):
    result = (
        supabase
        .table("study_sessions")
        .select(
            "id,user_id,chat_id,subject_id,planned_minutes,"
            "started_at,planned_end_at,ended_at,actual_minutes,status"
        )
        .eq("user_id", int(user_id))
        .eq("status", "active")
        .order(
            "started_at",
            desc=True,
        )
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def start_session(
    user_id,
    chat_id,
    subject_id,
    minutes,
):
    now_utc = datetime.now(
        timezone.utc
    )

    planned_end = (
        now_utc
        + timedelta(
            minutes=int(minutes)
        )
    )

    result = (
        supabase
        .table("study_sessions")
        .insert(
            {
                "user_id": int(user_id),
                "chat_id": int(chat_id),
                "subject_id": subject_id,
                "planned_minutes": int(minutes),
                "started_at": now_utc.isoformat(),
                "planned_end_at": planned_end.isoformat(),
                "status": "active",
                "alert_sent": False,
            }
        )
        .execute()
    )

    return (
        result.data[0]
        if result.data
        else None
    )


def end_session_early(
    user_id,
):
    session = active_session(
        user_id
    )

    if not session:
        return None

    now_utc = datetime.now(
        timezone.utc
    )

    try:
        started = datetime.fromisoformat(
            session[
                "started_at"
            ].replace(
                "Z",
                "+00:00",
            )
        )

        actual_minutes = max(
            1,
            round(
                (
                    now_utc
                    - started
                ).total_seconds()
                / 60
            ),
        )

    except Exception:
        actual_minutes = 1

    (
        supabase
        .table("study_sessions")
        .update(
            {
                "status": "completed",
                "ended_at": now_utc.isoformat(),
                "actual_minutes": actual_minutes,
                "alert_sent": True,
            }
        )
        .eq("user_id", int(user_id))
        .eq("id", int(session["id"]))
        .execute()
    )

    session[
        "actual_minutes"
    ] = actual_minutes

    return session


def subject_name(
    user_id,
    subject_id,
):
    if not subject_id:
        return "No Subject"

    subject = get_subject_by_id(
        user_id,
        subject_id,
    )

    if not subject:
        return "No Subject"

    return subject_display(
        subject
    )


def local_datetime_text(
    value,
):
    if not value:
        return "Unknown"

    try:
        dt = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        ).astimezone(
            SRI_LANKA_TZ
        )

        return dt.strftime(
            "%d-%m-%Y %I:%M %p"
        )

    except Exception:
        return str(value)


def parse_subject_button(
    text
):
    if text == "⏭ No Subject":
        return None

    if not text.startswith(
        "📚 #"
    ):
        return "invalid"

    try:
        token = text.split(
            " ",
            2,
        )[1]

        return int(
            token.replace(
                "#",
                ""
            )
        )

    except Exception:
        return "invalid"


def register_study_planner_handlers(
    bot,
    show_main_menu,
):

    def show_planner_menu(
        chat_id
    ):
        planner_state.pop(
            chat_id,
            None,
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "🍅 25 Min Focus"
            ),
            types.KeyboardButton(
                "📘 50 Min Focus"
            ),
            types.KeyboardButton(
                "⏱ Custom Session"
            ),
            types.KeyboardButton(
                "▶️ Active Session"
            ),
            types.KeyboardButton(
                "⏹ End Session"
            ),
            types.KeyboardButton(
                "📊 Weekly Study Analytics"
            ),
            types.KeyboardButton(
                "🗓 Timetable"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "⏱ Study Planner\n\n"
                "Start a focused study session. "
                "Supabase tracks it and sends a Telegram "
                "message when the timer finishes."
            ),
            reply_markup=markup,
        )

    def choose_subject(
        message,
        minutes,
    ):
        if active_session(
            message.from_user.id
        ):
            bot.send_message(
                message.chat.id,
                (
                    "⚠️ You already have an active "
                    "study session.\n\n"
                    "Use ▶️ Active Session or ⏹ End Session."
                ),
            )
            return

        subjects = get_subjects(
            message.from_user.id
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=1,
        )

        markup.add(
            types.KeyboardButton(
                "⏭ No Subject"
            )
        )

        for subject in subjects:
            markup.add(
                types.KeyboardButton(
                    (
                        f"📚 #{subject['id']} "
                        f"{subject_display(subject)}"
                    )
                )
            )

        markup.add(
            types.KeyboardButton(
                "🔙 Planner Menu"
            )
        )

        planner_state[
            message.chat.id
        ] = {
            "step": "subject",
            "minutes": int(minutes),
        }

        bot.send_message(
            message.chat.id,
            (
                f"⏱ Session length: {minutes} minutes\n\n"
                "📚 Choose what you are studying:"
            ),
            reply_markup=markup,
        )

    @bot.message_handler(
        commands=["planner"]
    )
    def planner_command(
        message
    ):
        show_planner_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "⏱ Study Planner"
    )
    def planner_button(
        message
    ):
        show_planner_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🍅 25 Min Focus"
    )
    def focus_25(
        message
    ):
        choose_subject(
            message,
            25,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📘 50 Min Focus"
    )
    def focus_50(
        message
    ):
        choose_subject(
            message,
            50,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "⏱ Custom Session"
    )
    def custom_session(
        message
    ):
        if active_session(
            message.from_user.id
        ):
            bot.send_message(
                message.chat.id,
                "⚠️ End your active session first.",
            )
            return

        planner_state[
            message.chat.id
        ] = {
            "step": "custom_minutes"
        }

        bot.send_message(
            message.chat.id,
            (
                "⏱ Send session length in minutes.\n\n"
                "Allowed: 1–360\n"
                "Example: 90"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "▶️ Active Session"
    )
    def show_active(
        message
    ):
        session = active_session(
            message.from_user.id
        )

        if not session:
            bot.send_message(
                message.chat.id,
                "✅ No active study session.",
            )
            return

        bot.send_message(
            message.chat.id,
            (
                "▶️ ACTIVE STUDY SESSION\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"📚 "
                f"{subject_name(message.from_user.id, session.get('subject_id'))}\n"
                f"⏱ Planned: {session['planned_minutes']} min\n"
                f"🕒 Started: {local_datetime_text(session.get('started_at'))}\n"
                f"🏁 Ends: {local_datetime_text(session.get('planned_end_at'))}"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "⏹ End Session"
    )
    def end_session(
        message
    ):
        try:
            session = end_session_early(
                message.from_user.id
            )

            if not session:
                bot.send_message(
                    message.chat.id,
                    "✅ No active session to end.",
                )
                return

            bot.send_message(
                message.chat.id,
                (
                    "⏹ Study session ended.\n\n"
                    f"⏱ Studied: "
                    f"{session.get('actual_minutes', 0)} minutes"
                ),
            )

        except Exception as error:
            print(
                "End study session error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not end the study session.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "📊 Weekly Study Analytics"
    )
    def weekly_analytics(
        message
    ):
        try:
            text = build_study_analytics(
                message.from_user.id
            )

            bot.send_message(
                message.chat.id,
                text,
            )

        except Exception as error:
            print(
                "Study analytics error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not load study analytics.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔙 Planner Menu"
    )
    def back_planner(
        message
    ):
        show_planner_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.chat.id in planner_state,
        content_types=["text"],
    )
    def planner_state_handler(
        message
    ):
        chat_id = message.chat.id
        text = (
            message.text
            or ""
        ).strip()

        if text == "🏠 Main Menu":
            planner_state.pop(
                chat_id,
                None,
            )

            show_main_menu(
                chat_id,
                message.from_user.first_name
                or "Friend",
            )
            return

        if text == "🔙 Planner Menu":
            show_planner_menu(
                chat_id
            )
            return

        if (
            text.startswith("/")
            or text in GLOBAL_BUTTONS
        ):
            planner_state.pop(
                chat_id,
                None,
            )
            return ContinueHandling()

        state = planner_state.get(
            chat_id,
            {}
        )

        step = state.get(
            "step"
        )

        if step == "custom_minutes":
            try:
                minutes = int(
                    text
                )
            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Send minutes as a number.",
                )
                return

            if not 1 <= minutes <= 360:
                bot.send_message(
                    chat_id,
                    "❌ Choose between 1 and 360 minutes.",
                )
                return

            planner_state.pop(
                chat_id,
                None,
            )

            choose_subject(
                message,
                minutes,
            )
            return

        if step == "subject":
            subject_id = parse_subject_button(
                text
            )

            if subject_id == "invalid":
                bot.send_message(
                    chat_id,
                    "❌ Choose a subject using the buttons.",
                )
                return

            if (
                subject_id is not None
                and not get_subject_by_id(
                    message.from_user.id,
                    subject_id,
                )
            ):
                bot.send_message(
                    chat_id,
                    "❌ Subject not found.",
                )
                return

            try:
                session = start_session(
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    subject_id=subject_id,
                    minutes=state[
                        "minutes"
                    ],
                )

                planner_state.pop(
                    chat_id,
                    None,
                )

                if not session:
                    raise RuntimeError(
                        "Session was not created."
                    )

                bot.send_message(
                    chat_id,
                    (
                        "▶️ Study session started!\n\n"
                        f"📚 "
                        f"{subject_name(message.from_user.id, subject_id)}\n"
                        f"⏱ {state['minutes']} minutes\n"
                        f"🏁 Ends: "
                        f"{local_datetime_text(session.get('planned_end_at'))}\n\n"
                        "Focus on one task. "
                        "You will receive a Telegram message "
                        "when the session is complete. 📖"
                    ),
                )

                show_planner_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Start study session error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not start the study session.",
                )

            return
