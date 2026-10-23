from datetime import datetime
from zoneinfo import ZoneInfo

from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase
from subjects import (
    get_subjects,
    get_subject_by_id,
    subject_display,
)


attendance_state = {}
SRI_LANKA_TZ = ZoneInfo("Asia/Colombo")


GLOBAL_BUTTONS = {
    "📄 PDF Tools",
    "📝 Notes",
    "🌐 Translate",
    "⏰ Study Reminder",
    "📚 Subjects",
    "📅 Assignments",
    "📚 Study Materials",
    "🗓 Timetable",
    "⏱ Study Planner",
    "🎙 Voice Notes",
    "🌍 Language Tools",
    "🧠 Flashcards",
    "❓ Quiz",
    "📝 Exams",
    "✅ Attendance",
    "🎯 Study Goals",
    "📊 Dashboard",
    "📈 Progress",
    "ℹ️ Help",
}


STATUS_MAP = {
    "✅ Present": "present",
    "❌ Absent": "absent",
    "🟡 Late": "late",
    "📝 Excused": "excused",
}


def get_records(
    user_id,
    subject_id=None,
    limit=100,
):
    query = (
        supabase
        .table("attendance_records")
        .select(
            "id,user_id,subject_id,class_date,status,note,created_at"
        )
        .eq("user_id", int(user_id))
    )

    if subject_id is not None:
        query = query.eq(
            "subject_id",
            int(subject_id),
        )

    result = (
        query
        .order(
            "class_date",
            desc=True,
        )
        .limit(limit)
        .execute()
    )

    return result.data or []


def attendance_summary(
    records
):
    counts = {
        "present": 0,
        "absent": 0,
        "late": 0,
        "excused": 0,
    }

    for record in records:
        status = record.get(
            "status"
        )

        if status in counts:
            counts[
                status
            ] += 1

    total = sum(
        counts.values()
    )

    attended = (
        counts[
            "present"
        ]
        + counts[
            "late"
        ]
    )

    percentage = (
        round(
            attended
            / total
            * 100,
            1,
        )
        if total
        else 0
    )

    return (
        counts,
        total,
        percentage,
    )


def save_attendance(
    user_id,
    subject_id,
    class_date,
    status,
    note=None,
):
    payload = {
        "user_id": int(user_id),
        "subject_id": int(subject_id),
        "class_date": class_date.isoformat(),
        "status": status,
        "note": (
            note.strip()
            if note
            else None
        ),
    }

    return (
        supabase
        .table("attendance_records")
        .upsert(
            payload,
            on_conflict=(
                "user_id,"
                "subject_id,"
                "class_date"
            ),
        )
        .execute()
    )


def delete_record(
    user_id,
    record_id,
):
    result = (
        supabase
        .table("attendance_records")
        .select("id")
        .eq("user_id", int(user_id))
        .eq("id", int(record_id))
        .limit(1)
        .execute()
    )

    if not result.data:
        return False

    (
        supabase
        .table("attendance_records")
        .delete()
        .eq("user_id", int(user_id))
        .eq("id", int(record_id))
        .execute()
    )

    return True


def parse_subject_button(text):
    if not text.startswith(
        "📚 #"
    ):
        return None

    try:
        return int(
            text.split(
                " ",
                2,
            )[1].replace(
                "#",
                ""
            )
        )

    except Exception:
        return None


def register_attendance_handlers(
    bot,
    show_main_menu,
):

    def show_attendance_menu(
        chat_id
    ):
        attendance_state.pop(
            chat_id,
            None,
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "➕ Mark Attendance"
            ),
            types.KeyboardButton(
                "📊 Attendance Summary"
            ),
            types.KeyboardButton(
                "📋 Attendance History"
            ),
            types.KeyboardButton(
                "🗑 Delete Attendance"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "✅ Attendance Tracker\n\n"
                "Track attendance by subject and "
                "monitor your attendance percentage."
            ),
            reply_markup=markup,
        )

    def choose_subject(
        message,
        step,
        prompt,
    ):
        subjects = get_subjects(
            message.from_user.id
        )

        if not subjects:
            bot.send_message(
                message.chat.id,
                (
                    "📚 Add at least one subject first."
                ),
            )
            return

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=1,
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
                "🔙 Attendance Menu"
            )
        )

        attendance_state[
            message.chat.id
        ] = {
            "step": step
        }

        bot.send_message(
            message.chat.id,
            prompt,
            reply_markup=markup,
        )

    @bot.message_handler(
        commands=["attendance"]
    )
    def attendance_command(message):
        show_attendance_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "✅ Attendance"
    )
    def attendance_button(message):
        show_attendance_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "➕ Mark Attendance"
    )
    def mark_attendance(message):
        choose_subject(
            message,
            "mark_subject",
            "📚 Choose the subject:",
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📊 Attendance Summary"
    )
    def summary_button(message):
        choose_subject(
            message,
            "summary_subject",
            "📚 Choose a subject:",
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📋 Attendance History"
    )
    def history_button(message):
        choose_subject(
            message,
            "history_subject",
            "📚 Choose a subject:",
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🗑 Delete Attendance"
    )
    def delete_button(message):
        attendance_state[
            message.chat.id
        ] = {
            "step": "delete"
        }

        bot.send_message(
            message.chat.id,
            (
                "🗑 Send the attendance record number.\n"
                "Example: 8"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔙 Attendance Menu"
    )
    def back_attendance(message):
        show_attendance_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.chat.id in attendance_state,
        content_types=["text"],
    )
    def attendance_state_handler(
        message
    ):
        chat_id = message.chat.id
        text = (
            message.text
            or ""
        ).strip()

        if text == "🏠 Main Menu":
            attendance_state.pop(
                chat_id,
                None,
            )

            show_main_menu(
                chat_id,
                message.from_user.first_name
                or "Friend",
            )
            return

        if text == "🔙 Attendance Menu":
            show_attendance_menu(
                chat_id
            )
            return

        if (
            text.startswith("/")
            or text in GLOBAL_BUTTONS
        ):
            attendance_state.pop(
                chat_id,
                None,
            )
            return ContinueHandling()

        state = attendance_state.get(
            chat_id,
            {}
        )

        step = state.get(
            "step"
        )

        if step in {
            "mark_subject",
            "summary_subject",
            "history_subject",
        }:
            subject_id = parse_subject_button(
                text
            )

            if (
                not subject_id
                or not get_subject_by_id(
                    message.from_user.id,
                    subject_id,
                )
            ):
                bot.send_message(
                    chat_id,
                    "❌ Choose a subject using the buttons.",
                )
                return

            if step == "summary_subject":
                records = get_records(
                    message.from_user.id,
                    subject_id=subject_id,
                    limit=500,
                )

                counts, total, percentage = (
                    attendance_summary(
                        records
                    )
                )

                subject = get_subject_by_id(
                    message.from_user.id,
                    subject_id,
                )

                attendance_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    (
                        "📊 ATTENDANCE SUMMARY\n"
                        "━━━━━━━━━━━━━━━━━━\n\n"
                        f"📚 {subject_display(subject)}\n\n"
                        f"✅ Present: {counts['present']}\n"
                        f"🟡 Late: {counts['late']}\n"
                        f"❌ Absent: {counts['absent']}\n"
                        f"📝 Excused: {counts['excused']}\n"
                        f"📋 Total: {total}\n\n"
                        f"📈 Attendance: {percentage}%"
                    ),
                )

                show_attendance_menu(
                    chat_id
                )
                return

            if step == "history_subject":
                records = get_records(
                    message.from_user.id,
                    subject_id=subject_id,
                    limit=50,
                )

                attendance_state.pop(
                    chat_id,
                    None,
                )

                if not records:
                    bot.send_message(
                        chat_id,
                        "📋 No attendance records.",
                    )

                    show_attendance_menu(
                        chat_id
                    )
                    return

                subject = get_subject_by_id(
                    message.from_user.id,
                    subject_id,
                )

                parts = [
                    (
                        f"📋 ATTENDANCE HISTORY\n"
                        f"📚 {subject_display(subject)}\n"
                    )
                ]

                emoji = {
                    "present": "✅",
                    "absent": "❌",
                    "late": "🟡",
                    "excused": "📝",
                }

                for record in records:
                    parts.append(
                        (
                            f"\n#{record['id']} "
                            f"{emoji.get(record['status'], '•')} "
                            f"{record['class_date']} "
                            f"— {record['status'].title()}"
                        )
                    )

                bot.send_message(
                    chat_id,
                    "\n".join(parts),
                )

                show_attendance_menu(
                    chat_id
                )
                return

            state[
                "subject_id"
            ] = subject_id

            state[
                "step"
            ] = "date"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
            )

            markup.add(
                types.KeyboardButton(
                    "📅 Today"
                ),
                types.KeyboardButton(
                    "🔙 Attendance Menu"
                ),
            )

            bot.send_message(
                chat_id,
                (
                    "📅 Send class date.\n\n"
                    "Example: 23-10-2026\n"
                    "or choose 📅 Today."
                ),
                reply_markup=markup,
            )
            return

        if step == "date":
            if text == "📅 Today":
                class_date = datetime.now(
                    SRI_LANKA_TZ
                ).date()
            else:
                try:
                    class_date = datetime.strptime(
                        text,
                        "%d-%m-%Y",
                    ).date()

                except ValueError:
                    bot.send_message(
                        chat_id,
                        (
                            "❌ Invalid date.\n"
                            "Use: 23-10-2026"
                        ),
                    )
                    return

            state[
                "class_date"
            ] = class_date

            state[
                "step"
            ] = "status"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
                row_width=2,
            )

            markup.add(
                *[
                    types.KeyboardButton(
                        label
                    )
                    for label in STATUS_MAP
                ]
            )

            bot.send_message(
                chat_id,
                "✅ Choose attendance status:",
                reply_markup=markup,
            )
            return

        if step == "status":
            if text not in STATUS_MAP:
                bot.send_message(
                    chat_id,
                    "❌ Choose a status using the buttons.",
                )
                return

            try:
                save_attendance(
                    user_id=message.from_user.id,
                    subject_id=state[
                        "subject_id"
                    ],
                    class_date=state[
                        "class_date"
                    ],
                    status=STATUS_MAP[
                        text
                    ],
                )

                attendance_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    (
                        "✅ Attendance saved!\n\n"
                        f"📅 {state['class_date'].strftime('%d-%m-%Y')}\n"
                        f"{text}"
                    ),
                )

                show_attendance_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Save attendance error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not save attendance.",
                )

            return

        if step == "delete":
            try:
                record_id = int(
                    text.replace(
                        "#",
                        ""
                    )
                )

            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Send only the record number.",
                )
                return

            try:
                success = delete_record(
                    message.from_user.id,
                    record_id,
                )

                if not success:
                    bot.send_message(
                        chat_id,
                        "❌ Attendance record not found.",
                    )
                    return

                attendance_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    "✅ Attendance record deleted.",
                )

                show_attendance_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Delete attendance error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not delete attendance.",
                )

            return
