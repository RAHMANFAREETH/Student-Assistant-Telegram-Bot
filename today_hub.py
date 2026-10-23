from datetime import datetime, timedelta, time as dt_time, timezone
from zoneinfo import ZoneInfo

from telebot import types

from db import supabase
from subjects import get_subject_by_id, subject_display


SRI_LANKA_TZ = ZoneInfo("Asia/Colombo")


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


def _subject_name(
    user_id,
    subject_id,
):
    if not subject_id:
        return "No Subject"

    try:
        subject = get_subject_by_id(
            user_id,
            subject_id,
        )

        if subject:
            return subject_display(
                subject
            )

    except Exception:
        pass

    return "No Subject"


def _format_time(value):
    if not value:
        return "--:--"

    text = str(value)

    for fmt in (
        "%H:%M:%S",
        "%H:%M",
    ):
        try:
            return datetime.strptime(
                text,
                fmt,
            ).strftime(
                "%I:%M %p"
            )

        except ValueError:
            pass

    return text


def _format_datetime(value):
    if not value:
        return "Unknown"

    try:
        dt = datetime.fromisoformat(
            str(value).replace(
                "Z",
                "+00:00",
            )
        )

        return (
            dt
            .astimezone(SRI_LANKA_TZ)
            .strftime(
                "%d-%m-%Y %I:%M %p"
            )
        )

    except Exception:
        return str(value)


def build_today_hub(
    user_id,
):
    now = datetime.now(
        SRI_LANKA_TZ
    )

    today_start = datetime.combine(
        now.date(),
        dt_time.min,
        tzinfo=SRI_LANKA_TZ,
    )

    tomorrow_start = (
        today_start
        + timedelta(days=1)
    )

    week_end = (
        now
        + timedelta(days=7)
    )

    sections = [
        "☀️ TODAY HUB",
        "━━━━━━━━━━━━━━━━━━",
        "",
        now.strftime(
            "📅 %A, %d %B %Y"
        ),
    ]

    # ==================================================
    # TODAY'S TIMETABLE
    # ==================================================

    try:
        timetable_result = (
            supabase
            .table(
                "timetable_entries"
            )
            .select(
                "id,subject_id,title,"
                "start_time,end_time,location"
            )
            .eq(
                "user_id",
                int(user_id),
            )
            .eq(
                "day_of_week",
                now.weekday(),
            )
            .order(
                "start_time"
            )
            .execute()
        )

        entries = (
            timetable_result.data
            or []
        )

        sections.append(
            "\n🗓 TODAY'S CLASSES"
        )

        if entries:
            for item in entries:
                location = (
                    item.get(
                        "location"
                    )
                    or ""
                ).strip()

                location_text = (
                    f" | 📍 {location}"
                    if location
                    else ""
                )

                sections.append(
                    (
                        f"• {_format_time(item.get('start_time'))}"
                        f"–{_format_time(item.get('end_time'))} "
                        f"{item['title']}\n"
                        f"  📚 "
                        f"{_subject_name(user_id, item.get('subject_id'))}"
                        f"{location_text}"
                    )
                )

        else:
            sections.append(
                "• No classes scheduled."
            )

    except Exception as error:
        print(
            "Today hub timetable error:",
            repr(error),
        )

        sections.append(
            "\n🗓 TODAY'S CLASSES\n"
            "• Could not load."
        )

    # ==================================================
    # ASSIGNMENTS DUE TODAY
    # ==================================================

    try:
        assignment_result = (
            supabase
            .table(
                "assignments"
            )
            .select(
                "id,subject_id,title,due_at,priority"
            )
            .eq(
                "user_id",
                int(user_id),
            )
            .eq(
                "status",
                "pending",
            )
            .gte(
                "due_at",
                _utc_iso(
                    today_start
                ),
            )
            .lt(
                "due_at",
                _utc_iso(
                    tomorrow_start
                ),
            )
            .order(
                "due_at"
            )
            .execute()
        )

        assignments = (
            assignment_result.data
            or []
        )

        sections.append(
            "\n📅 ASSIGNMENTS DUE TODAY"
        )

        if assignments:
            for item in assignments:
                sections.append(
                    (
                        f"• #{item['id']} {item['title']}\n"
                        f"  🕒 {_format_datetime(item.get('due_at'))}\n"
                        f"  📚 "
                        f"{_subject_name(user_id, item.get('subject_id'))}"
                        f" | ⚡ {str(item.get('priority') or 'medium').title()}"
                    )
                )

        else:
            sections.append(
                "• Nothing due today. ✅"
            )

    except Exception as error:
        print(
            "Today hub assignments error:",
            repr(error),
        )

        sections.append(
            "\n📅 ASSIGNMENTS DUE TODAY\n"
            "• Could not load."
        )

    # ==================================================
    # EXAMS IN NEXT 7 DAYS
    # ==================================================

    try:
        exam_result = (
            supabase
            .table(
                "exams"
            )
            .select(
                "id,subject_id,title,exam_at,location"
            )
            .eq(
                "user_id",
                int(user_id),
            )
            .gte(
                "exam_at",
                datetime.now(
                    timezone.utc
                ).isoformat(),
            )
            .lte(
                "exam_at",
                _utc_iso(
                    week_end
                ),
            )
            .order(
                "exam_at"
            )
            .execute()
        )

        exams = (
            exam_result.data
            or []
        )

        sections.append(
            "\n📝 EXAMS — NEXT 7 DAYS"
        )

        if exams:
            for item in exams:
                sections.append(
                    (
                        f"• #{item['id']} {item['title']}\n"
                        f"  🕒 {_format_datetime(item.get('exam_at'))}\n"
                        f"  📚 "
                        f"{_subject_name(user_id, item.get('subject_id'))}"
                    )
                )

        else:
            sections.append(
                "• No exams in the next 7 days."
            )

    except Exception as error:
        print(
            "Today hub exams error:",
            repr(error),
        )

        sections.append(
            "\n📝 EXAMS — NEXT 7 DAYS\n"
            "• Could not load."
        )

    # ==================================================
    # ACTIVE / OVERDUE GOALS
    # ==================================================

    try:
        goals_result = (
            supabase
            .table(
                "study_goals"
            )
            .select(
                "id,subject_id,title,target_date"
            )
            .eq(
                "user_id",
                int(user_id),
            )
            .eq(
                "status",
                "pending",
            )
            .order(
                "target_date"
            )
            .limit(8)
            .execute()
        )

        goals = (
            goals_result.data
            or []
        )

        sections.append(
            "\n🎯 ACTIVE GOALS"
        )

        if goals:
            for item in goals:
                target = (
                    item.get(
                        "target_date"
                    )
                    or "No deadline"
                )

                warning = ""

                if (
                    item.get(
                        "target_date"
                    )
                    and str(
                        item[
                            "target_date"
                        ]
                    ) < now.date().isoformat()
                ):
                    warning = (
                        " ⚠️ OVERDUE"
                    )

                sections.append(
                    (
                        f"• #{item['id']} "
                        f"{item['title']}\n"
                        f"  🎯 {target}{warning}"
                    )
                )

        else:
            sections.append(
                "• No active study goals."
            )

    except Exception as error:
        print(
            "Today hub goals error:",
            repr(error),
        )

        sections.append(
            "\n🎯 ACTIVE GOALS\n"
            "• Could not load."
        )

    # ==================================================
    # STUDY MINUTES TODAY
    # ==================================================

    try:
        sessions_result = (
            supabase
            .table(
                "study_sessions"
            )
            .select(
                "actual_minutes,planned_minutes"
            )
            .eq(
                "user_id",
                int(user_id),
            )
            .eq(
                "status",
                "completed",
            )
            .gte(
                "started_at",
                _utc_iso(
                    today_start
                ),
            )
            .lt(
                "started_at",
                _utc_iso(
                    tomorrow_start
                ),
            )
            .execute()
        )

        minutes = 0

        for item in (
            sessions_result.data
            or []
        ):
            minutes += int(
                item.get(
                    "actual_minutes"
                )
                or item.get(
                    "planned_minutes"
                )
                or 0
            )

        sections.append(
            (
                "\n⏱ STUDY TODAY\n"
                f"• {minutes} minutes completed"
            )
        )

    except Exception as error:
        print(
            "Today hub study session error:",
            repr(error),
        )

    return "\n".join(
        sections
    )


def register_today_hub_handlers(
    bot,
    show_main_menu,
):

    def send_today_hub(
        message
    ):
        status = bot.send_message(
            message.chat.id,
            "☀️ Building your Today Hub..."
        )

        try:
            text = build_today_hub(
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
                    "🔄 Refresh Today"
                ),
                types.KeyboardButton(
                    "📅 Assignments"
                ),
                types.KeyboardButton(
                    "🗓 Timetable"
                ),
                types.KeyboardButton(
                    "📝 Exams"
                ),
                types.KeyboardButton(
                    "🎯 Study Goals"
                ),
                types.KeyboardButton(
                    "⏱ Study Planner"
                ),
                types.KeyboardButton(
                    "🏠 Main Menu"
                ),
            )

            bot.send_message(
                message.chat.id,
                text,
                reply_markup=markup,
            )

        except Exception as error:
            print(
                "Today hub error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not build Today Hub.",
            )

    @bot.message_handler(
        commands=["todayhub"]
    )
    def today_hub_command(
        message
    ):
        send_today_hub(
            message
        )

    @bot.message_handler(
        func=lambda m:
        m.text in {
            "☀️ Today Hub",
            "🔄 Refresh Today",
        }
    )
    def today_hub_button(
        message
    ):
        send_today_hub(
            message
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🏠 Main Menu"
    )
    def today_hub_main(
        message
    ):
        show_main_menu(
            message.chat.id,
            message.from_user.first_name
            or "Friend",
        )
