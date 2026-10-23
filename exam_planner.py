from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase
from subjects import (
    get_subjects,
    get_subject_by_id,
    subject_display,
)


exam_state = {}
SRI_LANKA_TZ = ZoneInfo("Asia/Colombo")


from navigation import GLOBAL_BUTTONS


def local_to_utc_iso(local_dt):
    if local_dt.tzinfo is None:
        local_dt = local_dt.replace(
            tzinfo=SRI_LANKA_TZ
        )

    return (
        local_dt
        .astimezone(timezone.utc)
        .isoformat()
    )


def utc_to_local(value):
    if not value:
        return None

    dt = datetime.fromisoformat(
        value.replace(
            "Z",
            "+00:00",
        )
    )

    return dt.astimezone(
        SRI_LANKA_TZ
    )


def parse_exam_datetime(text):
    value = text.strip()

    for fmt in (
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y %I:%M %p",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %I:%M %p",
    ):
        try:
            return datetime.strptime(
                value,
                fmt,
            ).replace(
                tzinfo=SRI_LANKA_TZ
            )

        except ValueError:
            pass

    return None


def get_exams(
    user_id,
    upcoming_only=True,
    limit=30,
):
    query = (
        supabase
        .table("exams")
        .select(
            "id,user_id,chat_id,subject_id,title,"
            "exam_at,location,notes,created_at"
        )
        .eq("user_id", int(user_id))
    )

    if upcoming_only:
        query = query.gte(
            "exam_at",
            datetime.now(
                timezone.utc
            ).isoformat(),
        )

    result = (
        query
        .order("exam_at")
        .limit(limit)
        .execute()
    )

    return result.data or []


def get_exam(
    user_id,
    exam_id,
):
    result = (
        supabase
        .table("exams")
        .select(
            "id,user_id,chat_id,subject_id,title,"
            "exam_at,location,notes"
        )
        .eq("user_id", int(user_id))
        .eq("id", int(exam_id))
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def create_exam(
    user_id,
    chat_id,
    subject_id,
    title,
    exam_at,
    location=None,
    notes=None,
):
    result = (
        supabase
        .table("exams")
        .insert(
            {
                "user_id": int(user_id),
                "chat_id": int(chat_id),
                "subject_id": subject_id,
                "title": title.strip(),
                "exam_at": local_to_utc_iso(
                    exam_at
                ),
                "location": (
                    location.strip()
                    if location
                    else None
                ),
                "notes": (
                    notes.strip()
                    if notes
                    else None
                ),
            }
        )
        .execute()
    )

    return (
        result.data[0]
        if result.data
        else None
    )


def delete_exam(
    user_id,
    exam_id,
):
    exam = get_exam(
        user_id,
        exam_id,
    )

    if not exam:
        return False

    (
        supabase
        .table("exams")
        .delete()
        .eq("user_id", int(user_id))
        .eq("id", int(exam_id))
        .execute()
    )

    return True


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

    return (
        subject_display(subject)
        if subject
        else "No Subject"
    )


def parse_subject_button(text):
    if text == "⏭ No Subject":
        return None

    if not text.startswith(
        "📚 #"
    ):
        return "invalid"

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
        return "invalid"


def format_exam(
    user_id,
    exam,
):
    exam_local = utc_to_local(
        exam.get(
            "exam_at"
        )
    )

    date_text = (
        exam_local.strftime(
            "%d-%m-%Y %I:%M %p"
        )
        if exam_local
        else "Unknown"
    )

    location = (
        exam.get(
            "location"
        )
        or ""
    ).strip()

    notes = (
        exam.get(
            "notes"
        )
        or ""
    ).strip()

    extra = ""

    if location:
        extra += (
            f"\n📍 {location}"
        )

    if notes:
        extra += (
            f"\n📝 {notes}"
        )

    return (
        f"#{exam['id']} {exam['title']}\n"
        f"📚 {subject_name(user_id, exam.get('subject_id'))}\n"
        f"🕒 {date_text}"
        f"{extra}"
    )


def register_exam_handlers(
    bot,
    show_main_menu,
):

    def show_exam_menu(chat_id):
        exam_state.pop(
            chat_id,
            None,
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "➕ Add Exam"
            ),
            types.KeyboardButton(
                "📅 Upcoming Exams"
            ),
            types.KeyboardButton(
                "🗑 Delete Exam"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "📝 Exam Planner\n\n"
                "Save exams and receive automatic alerts "
                "7 days, 1 day, and 1 hour before."
            ),
            reply_markup=markup,
        )

    @bot.message_handler(
        commands=["exams"]
    )
    def exams_command(message):
        show_exam_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📝 Exams"
    )
    def exams_button(message):
        show_exam_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📅 Upcoming Exams"
    )
    def upcoming_exams(message):
        try:
            exams = get_exams(
                message.from_user.id,
                upcoming_only=True,
                limit=30,
            )

            if not exams:
                bot.send_message(
                    message.chat.id,
                    "✅ No upcoming exams.",
                )
                return

            parts = [
                "📅 UPCOMING EXAMS\n"
            ]

            for exam in exams:
                parts.append(
                    "\n"
                    + format_exam(
                        message.from_user.id,
                        exam,
                    )
                    + "\n"
                )

            bot.send_message(
                message.chat.id,
                "\n".join(parts),
            )

        except Exception as error:
            print(
                "Load exams error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not load exams.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "➕ Add Exam"
    )
    def add_exam(message):
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
                "🔙 Exam Menu"
            )
        )

        exam_state[
            message.chat.id
        ] = {
            "step": "subject"
        }

        bot.send_message(
            message.chat.id,
            "📚 Choose the exam subject:",
            reply_markup=markup,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🗑 Delete Exam"
    )
    def delete_exam_button(message):
        exam_state[
            message.chat.id
        ] = {
            "step": "delete"
        }

        bot.send_message(
            message.chat.id,
            (
                "🗑 Send the exam number.\n"
                "Example: 4"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔙 Exam Menu"
    )
    def back_exam_menu(message):
        show_exam_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.chat.id in exam_state,
        content_types=["text"],
    )
    def exam_state_handler(
        message
    ):
        chat_id = message.chat.id
        text = (
            message.text
            or ""
        ).strip()

        if text == "🏠 Main Menu":
            exam_state.pop(
                chat_id,
                None,
            )

            show_main_menu(
                chat_id,
                message.from_user.first_name
                or "Friend",
            )
            return

        if text == "🔙 Exam Menu":
            show_exam_menu(
                chat_id
            )
            return

        if (
            text.startswith("/")
            or text in GLOBAL_BUTTONS
        ):
            exam_state.pop(
                chat_id,
                None,
            )
            return ContinueHandling()

        state = exam_state.get(
            chat_id,
            {}
        )

        step = state.get(
            "step"
        )

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

            state[
                "subject_id"
            ] = subject_id

            state[
                "step"
            ] = "title"

            bot.send_message(
                chat_id,
                (
                    "📝 Send exam title.\n\n"
                    "Example:\n"
                    "Applied Grammar Mid-Semester Exam"
                ),
            )
            return

        if step == "title":
            if len(text) < 2:
                bot.send_message(
                    chat_id,
                    "❌ Enter a valid title.",
                )
                return

            state[
                "title"
            ] = text

            state[
                "step"
            ] = "date"

            bot.send_message(
                chat_id,
                (
                    "🕒 Send exam date and time.\n\n"
                    "Example:\n"
                    "15-11-2026 09:30\n\n"
                    "Also accepted:\n"
                    "15-11-2026 09:30 AM"
                ),
            )
            return

        if step == "date":
            exam_at = parse_exam_datetime(
                text
            )

            if not exam_at:
                bot.send_message(
                    chat_id,
                    (
                        "❌ Invalid date/time.\n"
                        "Use: 15-11-2026 09:30"
                    ),
                )
                return

            if exam_at <= datetime.now(
                SRI_LANKA_TZ
            ):
                bot.send_message(
                    chat_id,
                    "❌ Exam time must be in the future.",
                )
                return

            state[
                "exam_at"
            ] = exam_at

            state[
                "step"
            ] = "location"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
            )

            markup.add(
                types.KeyboardButton(
                    "⏭ Skip Location"
                ),
                types.KeyboardButton(
                    "🔙 Exam Menu"
                ),
            )

            bot.send_message(
                chat_id,
                (
                    "📍 Send exam location/room.\n\n"
                    "Or choose ⏭ Skip Location."
                ),
                reply_markup=markup,
            )
            return

        if step == "location":
            state[
                "location"
            ] = (
                None
                if text == "⏭ Skip Location"
                else text
            )

            state[
                "step"
            ] = "notes"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
            )

            markup.add(
                types.KeyboardButton(
                    "⏭ Skip Notes"
                ),
                types.KeyboardButton(
                    "🔙 Exam Menu"
                ),
            )

            bot.send_message(
                chat_id,
                (
                    "📝 Add optional notes.\n\n"
                    "Example:\n"
                    "Chapters 1–5\n\n"
                    "Or choose ⏭ Skip Notes."
                ),
                reply_markup=markup,
            )
            return

        if step == "notes":
            notes = (
                None
                if text == "⏭ Skip Notes"
                else text
            )

            try:
                exam = create_exam(
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    subject_id=state.get(
                        "subject_id"
                    ),
                    title=state[
                        "title"
                    ],
                    exam_at=state[
                        "exam_at"
                    ],
                    location=state.get(
                        "location"
                    ),
                    notes=notes,
                )

                exam_state.pop(
                    chat_id,
                    None,
                )

                if not exam:
                    raise RuntimeError(
                        "Exam was not saved."
                    )

                bot.send_message(
                    chat_id,
                    (
                        "✅ Exam saved!\n\n"
                        f"📝 {state['title']}\n"
                        f"🕒 "
                        f"{state['exam_at'].strftime('%d-%m-%Y %I:%M %p')}\n\n"
                        "🔔 Automatic alerts:\n"
                        "• within 7 days\n"
                        "• within 24 hours\n"
                        "• within 1 hour"
                    ),
                )

                show_exam_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Create exam error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not save exam.",
                )

            return

        if step == "delete":
            try:
                exam_id = int(
                    text.replace(
                        "#",
                        ""
                    )
                )
            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Send only the exam number.",
                )
                return

            try:
                success = delete_exam(
                    message.from_user.id,
                    exam_id,
                )

                if not success:
                    bot.send_message(
                        chat_id,
                        "❌ Exam not found.",
                    )
                    return

                exam_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    "✅ Exam deleted.",
                )

                show_exam_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Delete exam error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not delete exam.",
                )

            return
