from datetime import datetime, timedelta, time as dt_time, timezone
from zoneinfo import ZoneInfo

from telebot import types

from db import supabase


SRI_LANKA_TZ = ZoneInfo("Asia/Colombo")


def _count_rows(table_name, user_id, status=None):
    try:
        query = (
            supabase
            .table(table_name)
            .select("id")
            .eq("user_id", int(user_id))
        )

        if status is not None:
            query = query.eq(
                "status",
                status,
            )

        result = query.execute()
        return len(result.data or [])

    except Exception as error:
        print(
            f"Dashboard count error ({table_name}):",
            repr(error),
        )
        return 0


def _count_flashcards(user_id, mastered=None):
    try:
        query = (
            supabase
            .table("flashcards")
            .select("id")
            .eq("user_id", int(user_id))
        )

        if mastered is not None:
            query = query.eq(
                "mastered",
                mastered,
            )

        result = query.execute()

        return len(
            result.data or []
        )

    except Exception:
        return 0


def _utc_iso(local_dt):
    if local_dt.tzinfo is None:
        local_dt = local_dt.replace(
            tzinfo=SRI_LANKA_TZ
        )

    return (
        local_dt
        .astimezone(timezone.utc)
        .isoformat()
    )


def _due_count(user_id, start_local, end_local):
    try:
        result = (
            supabase
            .table("assignments")
            .select("id")
            .eq("user_id", int(user_id))
            .eq("status", "pending")
            .gte("due_at", _utc_iso(start_local))
            .lt("due_at", _utc_iso(end_local))
            .execute()
        )

        return len(result.data or [])

    except Exception as error:
        print(
            "Dashboard due count error:",
            repr(error),
        )
        return 0


def _next_assignment(user_id):
    try:
        now_iso = datetime.now(
            timezone.utc
        ).isoformat()

        result = (
            supabase
            .table("assignments")
            .select(
                "id,title,due_at,priority,subject_id"
            )
            .eq("user_id", int(user_id))
            .eq("status", "pending")
            .gte("due_at", now_iso)
            .order("due_at")
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0]

    except Exception as error:
        print(
            "Dashboard next assignment error:",
            repr(error),
        )

    return None


def _subject_name(subject_id):
    if not subject_id:
        return None

    try:
        result = (
            supabase
            .table("subjects")
            .select("name")
            .eq("id", int(subject_id))
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0].get("name")

    except Exception as error:
        print(
            "Dashboard subject name error:",
            repr(error),
        )

    return None


def _format_due(due_at):
    if not due_at:
        return "Unknown"

    try:
        value = datetime.fromisoformat(
            due_at.replace(
                "Z",
                "+00:00",
            )
        )

        return (
            value
            .astimezone(SRI_LANKA_TZ)
            .strftime(
                "%d-%m-%Y %I:%M %p"
            )
        )

    except Exception:
        return due_at


def build_dashboard(user_id):
    now_local = datetime.now(
        SRI_LANKA_TZ
    )

    today_start = datetime.combine(
        now_local.date(),
        dt_time.min,
        tzinfo=SRI_LANKA_TZ,
    )

    tomorrow_start = (
        today_start
        + timedelta(days=1)
    )

    week_end = (
        now_local
        + timedelta(days=7)
    )

    subjects = _count_rows(
        "subjects",
        user_id,
    )

    notes = _count_rows(
        "notes",
        user_id,
    )

    materials = _count_rows(
        "study_materials",
        user_id,
    )

    pending_assignments = _count_rows(
        "assignments",
        user_id,
        status="pending",
    )

    completed_assignments = _count_rows(
        "assignments",
        user_id,
        status="completed",
    )

    active_reminders = _count_rows(
        "reminders",
        user_id,
        status="pending",
    )

    flashcards = _count_flashcards(
        user_id
    )

    mastered_flashcards = _count_flashcards(
        user_id,
        mastered=True,
    )

    due_today = _due_count(
        user_id,
        today_start,
        tomorrow_start,
    )

    due_week = _due_count(
        user_id,
        now_local,
        week_end,
    )

    total_assignments = (
        pending_assignments
        + completed_assignments
    )

    if total_assignments:
        completion = round(
            completed_assignments
            / total_assignments
            * 100
        )
    else:
        completion = 0

    next_item = _next_assignment(
        user_id
    )

    if next_item:
        subject = _subject_name(
            next_item.get(
                "subject_id"
            )
        )

        next_lines = (
            "\n\n📌 NEXT ASSIGNMENT\n"
            f"{next_item['title']}\n"
            f"🕒 {_format_due(next_item.get('due_at'))}"
        )

        if subject:
            next_lines += (
                f"\n📚 {subject}"
            )

    else:
        next_lines = (
            "\n\n📌 NEXT ASSIGNMENT\n"
            "No upcoming assignment 🎉"
        )

    return (
        "📊 STUDENT DASHBOARD\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"📚 Subjects: {subjects}\n"
        f"📚 Study Materials: {materials}\n"
        f"📝 Notes: {notes}\n"
        f"⏰ Active Reminders: {active_reminders}\n"
        f"🧠 Flashcards: {flashcards}\n"
        f"⭐ Mastered Cards: {mastered_flashcards}\n\n"

        "📅 ASSIGNMENTS\n"
        f"📌 Pending: {pending_assignments}\n"
        f"📅 Due Today: {due_today}\n"
        f"🗓 Next 7 Days: {due_week}\n"
        f"✅ Completed: {completed_assignments}\n"
        f"📈 Completion: {completion}%"
        f"{next_lines}"
    )


def register_dashboard_handlers(
    bot,
    show_main_menu,
):

    def send_dashboard(message):
        status = bot.send_message(
            message.chat.id,
            "📊 Building your dashboard..."
        )

        try:
            dashboard = build_dashboard(
                message.from_user.id
            )

            try:
                bot.delete_message(
                    message.chat.id,
                    status.message_id,
                )
            except Exception:
                pass

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
                row_width=2,
            )

            markup.add(
                types.KeyboardButton(
                    "📅 Assignments"
                ),
                types.KeyboardButton(
                    "📚 Subjects"
                ),
                types.KeyboardButton(
                    "📚 Study Materials"
                ),
                types.KeyboardButton(
                    "🧠 Flashcards"
                ),
                types.KeyboardButton(
                    "❓ Quiz"
                ),
                types.KeyboardButton(
                    "📈 Progress"
                ),
                types.KeyboardButton(
                    "🔄 Refresh Dashboard"
                ),
                types.KeyboardButton(
                    "🏠 Main Menu"
                ),
            )

            bot.send_message(
                message.chat.id,
                dashboard,
                reply_markup=markup,
            )

        except Exception as error:
            print(
                "Dashboard error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not build your dashboard.",
            )

    @bot.message_handler(
        commands=["dashboard"]
    )
    def dashboard_command(message):
        send_dashboard(message)

    @bot.message_handler(
        func=lambda m:
        m.text in {
            "📊 Dashboard",
            "🔄 Refresh Dashboard",
        }
    )
    def dashboard_button(message):
        send_dashboard(message)

    @bot.message_handler(
        func=lambda m:
        m.text == "🏠 Main Menu"
    )
    def dashboard_main_menu(message):
        show_main_menu(
            message.chat.id,
            message.from_user.first_name
            or "Friend",
        )
