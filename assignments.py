from datetime import (
    datetime,
    timedelta,
    time as dt_time,
    timezone,
)
from zoneinfo import ZoneInfo

from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase
from subjects import (
    get_subjects,
    get_subject_by_id,
    subject_display,
)


assignment_state = {}

SRI_LANKA_TZ = ZoneInfo(
    "Asia/Colombo"
)

GLOBAL_BUTTONS = {
    "📄 PDF Tools",
    "📝 Notes",
    "🌐 Translate",
    "⏰ Study Reminder",
    "ℹ️ Help",
    "📚 Subjects",
    "📅 Assignments",
    "📊 Dashboard",
}


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


def parse_due_datetime(text):
    value = text.strip()

    formats = [
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y %I:%M %p",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %I:%M %p",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                value,
                fmt,
            ).replace(
                tzinfo=SRI_LANKA_TZ
            )
        except ValueError:
            pass

    for fmt in (
        "%d-%m-%Y",
        "%d/%m/%Y",
    ):
        try:
            date_only = datetime.strptime(
                value,
                fmt,
            ).date()

            return datetime.combine(
                date_only,
                dt_time(
                    23,
                    59,
                ),
                tzinfo=SRI_LANKA_TZ,
            )

        except ValueError:
            pass

    return None


def create_assignment(
    user_id,
    title,
    description,
    due_at,
    priority,
    subject_id=None,
):
    payload = {
        "user_id": int(user_id),
        "subject_id": subject_id,
        "title": title.strip(),
        "description": (
            description.strip()
            if description
            else None
        ),
        "due_at": local_to_utc_iso(
            due_at
        ),
        "priority": priority,
        "status": "pending",
    }

    return (
        supabase
        .table("assignments")
        .insert(payload)
        .execute()
    )


def get_assignments(
    user_id,
    status="pending",
    start_iso=None,
    end_iso=None,
    limit=20,
):
    query = (
        supabase
        .table("assignments")
        .select(
            "id,title,description,due_at,"
            "priority,status,subject_id,"
            "created_at,completed_at"
        )
        .eq(
            "user_id",
            int(user_id),
        )
    )

    if status:
        query = query.eq(
            "status",
            status,
        )

    if start_iso:
        query = query.gte(
            "due_at",
            start_iso,
        )

    if end_iso:
        query = query.lt(
            "due_at",
            end_iso,
        )

    result = (
        query
        .order("due_at")
        .limit(limit)
        .execute()
    )

    return result.data or []


def get_assignment(
    user_id,
    assignment_id,
):
    result = (
        supabase
        .table("assignments")
        .select(
            "id,title,description,due_at,"
            "priority,status,subject_id"
        )
        .eq(
            "user_id",
            int(user_id),
        )
        .eq(
            "id",
            int(assignment_id),
        )
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def complete_assignment(
    user_id,
    assignment_id,
):
    assignment = get_assignment(
        user_id,
        assignment_id,
    )

    if not assignment:
        return False

    (
        supabase
        .table("assignments")
        .update(
            {
                "status": "completed",
                "completed_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
        )
        .eq(
            "user_id",
            int(user_id),
        )
        .eq(
            "id",
            int(assignment_id),
        )
        .execute()
    )

    return True


def delete_assignment(
    user_id,
    assignment_id,
):
    assignment = get_assignment(
        user_id,
        assignment_id,
    )

    if not assignment:
        return False

    (
        supabase
        .table("assignments")
        .delete()
        .eq(
            "user_id",
            int(user_id),
        )
        .eq(
            "id",
            int(assignment_id),
        )
        .execute()
    )

    return True


def priority_icon(priority):
    return {
        "high": "🔴",
        "medium": "🟠",
        "low": "🟢",
    }.get(
        priority,
        "⚪",
    )


def format_assignment(
    user_id,
    assignment,
):
    due = utc_to_local(
        assignment.get("due_at")
    )

    due_text = (
        due.strftime(
            "%d-%m-%Y %I:%M %p"
        )
        if due
        else "No date"
    )

    subject_text = "No subject"

    subject_id = assignment.get(
        "subject_id"
    )

    if subject_id:
        subject = get_subject_by_id(
            user_id,
            subject_id,
        )

        if subject:
            subject_text = (
                subject_display(
                    subject
                )
            )

    description = (
        assignment.get(
            "description"
        )
        or ""
    ).strip()

    description_line = (
        f"\n📝 {description}"
        if description
        else ""
    )

    return (
        f"#{assignment['id']} "
        f"{priority_icon(assignment.get('priority'))} "
        f"{assignment['title']}\n"
        f"📚 {subject_text}\n"
        f"🕒 {due_text}"
        f"{description_line}"
    )


def register_assignment_handlers(
    bot,
    show_main_menu,
):

    def show_assignment_menu(
        chat_id
    ):
        assignment_state.pop(
            chat_id,
            None,
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "➕ Add Assignment"
            ),
            types.KeyboardButton(
                "📌 Upcoming"
            ),
            types.KeyboardButton(
                "📅 Due Today"
            ),
            types.KeyboardButton(
                "🗓 Due This Week"
            ),
            types.KeyboardButton(
                "✅ Completed"
            ),
            types.KeyboardButton(
                "☑️ Mark Complete"
            ),
            types.KeyboardButton(
                "🗑 Delete Assignment"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "📅 Assignments\n\n"
                "Track coursework, deadlines "
                "and completed work."
            ),
            reply_markup=markup,
        )

    def send_assignment_list(
        message,
        assignments,
        heading,
    ):
        if not assignments:
            bot.send_message(
                message.chat.id,
                f"{heading}\n\n✅ Nothing here.",
            )
            return

        parts = [
            heading,
            "",
        ]

        for assignment in assignments:
            parts.append(
                format_assignment(
                    message.from_user.id,
                    assignment,
                )
            )
            parts.append(
                "\n──────────────\n"
            )

        bot.send_message(
            message.chat.id,
            "\n".join(parts),
        )

    @bot.message_handler(
        commands=["assignments"]
    )
    def assignments_command(message):
        show_assignment_menu(
            message.chat.id
        )

    @bot.message_handler(
        commands=["today"]
    )
    def today_command(message):
        show_due_today(message)

    @bot.message_handler(
        func=lambda m:
        m.text == "📅 Assignments"
    )
    def assignments_button(message):
        show_assignment_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "➕ Add Assignment"
    )
    def add_assignment_button(message):
        assignment_state[
            message.chat.id
        ] = {
            "step": "title"
        }

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
        )

        markup.add(
            types.KeyboardButton(
                "🔙 Assignments Menu"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            message.chat.id,
            (
                "➕ Add Assignment\n\n"
                "First, send the assignment title.\n\n"
                "Example:\n"
                "Applied Grammar Presentation"
            ),
            reply_markup=markup,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📌 Upcoming"
    )
    def upcoming_button(message):
        try:
            now_iso = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            rows = get_assignments(
                message.from_user.id,
                status="pending",
                start_iso=now_iso,
                limit=20,
            )

            send_assignment_list(
                message,
                rows,
                "📌 Upcoming Assignments",
            )

        except Exception as error:
            print(
                "Upcoming assignments error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not load assignments.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "📅 Due Today"
    )
    def show_due_today(message):
        try:
            now_local = datetime.now(
                SRI_LANKA_TZ
            )

            start_local = datetime.combine(
                now_local.date(),
                dt_time.min,
                tzinfo=SRI_LANKA_TZ,
            )

            end_local = (
                start_local
                + timedelta(days=1)
            )

            rows = get_assignments(
                message.from_user.id,
                status="pending",
                start_iso=local_to_utc_iso(
                    start_local
                ),
                end_iso=local_to_utc_iso(
                    end_local
                ),
                limit=30,
            )

            send_assignment_list(
                message,
                rows,
                "📅 Due Today",
            )

        except Exception as error:
            print(
                "Due today error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not load today's assignments.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "🗓 Due This Week"
    )
    def due_week_button(message):
        try:
            now_local = datetime.now(
                SRI_LANKA_TZ
            )

            start_local = now_local

            end_local = (
                now_local
                + timedelta(days=7)
            )

            rows = get_assignments(
                message.from_user.id,
                status="pending",
                start_iso=local_to_utc_iso(
                    start_local
                ),
                end_iso=local_to_utc_iso(
                    end_local
                ),
                limit=40,
            )

            send_assignment_list(
                message,
                rows,
                "🗓 Due in the Next 7 Days",
            )

        except Exception as error:
            print(
                "Due week error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not load this week's assignments.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "✅ Completed"
    )
    def completed_button(message):
        try:
            rows = get_assignments(
                message.from_user.id,
                status="completed",
                limit=20,
            )

            send_assignment_list(
                message,
                rows,
                "✅ Completed Assignments",
            )

        except Exception as error:
            print(
                "Completed assignments error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not load completed assignments.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "☑️ Mark Complete"
    )
    def mark_complete_button(message):
        assignment_state[
            message.chat.id
        ] = {
            "step": "complete"
        }

        bot.send_message(
            message.chat.id,
            (
                "☑️ Mark Complete\n\n"
                "Send the assignment number.\n"
                "Example: 5"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🗑 Delete Assignment"
    )
    def delete_assignment_button(message):
        assignment_state[
            message.chat.id
        ] = {
            "step": "delete"
        }

        bot.send_message(
            message.chat.id,
            (
                "🗑 Delete Assignment\n\n"
                "Send the assignment number.\n"
                "Example: 5"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔙 Assignments Menu"
    )
    def back_assignments(message):
        show_assignment_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.chat.id in assignment_state,
        content_types=["text"],
    )
    def assignment_state_handler(
        message
    ):
        chat_id = message.chat.id
        text = (message.text or "").strip()

        if text == "🏠 Main Menu":
            assignment_state.pop(
                chat_id,
                None,
            )

            show_main_menu(
                chat_id,
                message.from_user.first_name
                or "Friend",
            )
            return

        if text == "🔙 Assignments Menu":
            show_assignment_menu(
                chat_id
            )
            return

        # Do not trap another module's buttons/commands.
        if (
            text.startswith("/")
            or text in GLOBAL_BUTTONS
        ):
            assignment_state.pop(
                chat_id,
                None,
            )
            return ContinueHandling()

        state = assignment_state.get(
            chat_id,
            {}
        )

        step = state.get("step")

        if step == "title":
            if len(text) < 2:
                bot.send_message(
                    chat_id,
                    "❌ Please enter a valid title.",
                )
                return

            if len(text) > 200:
                bot.send_message(
                    chat_id,
                    "❌ Title is too long.",
                )
                return

            state["title"] = text
            state["step"] = "description"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
            )

            markup.add(
                types.KeyboardButton(
                    "⏭ Skip Description"
                ),
                types.KeyboardButton(
                    "🔙 Assignments Menu"
                ),
            )

            bot.send_message(
                chat_id,
                (
                    "📝 Add a short description.\n\n"
                    "Or choose ⏭ Skip Description."
                ),
                reply_markup=markup,
            )
            return

        if step == "description":
            if text == "⏭ Skip Description":
                state["description"] = None
            else:
                if len(text) > 1000:
                    bot.send_message(
                        chat_id,
                        (
                            "❌ Description is too long. "
                            "Maximum 1,000 characters."
                        ),
                    )
                    return

                state["description"] = text

            state["step"] = "due"

            bot.send_message(
                chat_id,
                (
                    "🕒 Send the deadline.\n\n"
                    "Recommended:\n"
                    "23-10-2026 18:30\n\n"
                    "Also accepted:\n"
                    "23-10-2026 06:30 PM\n"
                    "23-10-2026\n\n"
                    "If you send only a date, "
                    "11:59 PM will be used."
                ),
            )
            return

        if step == "due":
            due = parse_due_datetime(
                text
            )

            if not due:
                bot.send_message(
                    chat_id,
                    (
                        "❌ I could not understand that date.\n\n"
                        "Use:\n"
                        "23-10-2026 18:30"
                    ),
                )
                return

            if due <= datetime.now(
                SRI_LANKA_TZ
            ):
                bot.send_message(
                    chat_id,
                    (
                        "❌ The deadline must be "
                        "in the future."
                    ),
                )
                return

            state["due_at"] = due
            state["step"] = "priority"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
                row_width=3,
            )

            markup.add(
                types.KeyboardButton(
                    "🔴 High"
                ),
                types.KeyboardButton(
                    "🟠 Medium"
                ),
                types.KeyboardButton(
                    "🟢 Low"
                ),
            )

            bot.send_message(
                chat_id,
                "🎯 Choose priority:",
                reply_markup=markup,
            )
            return

        if step == "priority":
            priority_map = {
                "🔴 High": "high",
                "🟠 Medium": "medium",
                "🟢 Low": "low",
            }

            if text not in priority_map:
                bot.send_message(
                    chat_id,
                    "❌ Choose a priority using the buttons.",
                )
                return

            state["priority"] = (
                priority_map[text]
            )

            subjects = get_subjects(
                message.from_user.id
            )

            if not subjects:
                state["subject_id"] = None

                try:
                    create_assignment(
                        user_id=message.from_user.id,
                        title=state["title"],
                        description=state.get(
                            "description"
                        ),
                        due_at=state["due_at"],
                        priority=state["priority"],
                        subject_id=None,
                    )

                    assignment_state.pop(
                        chat_id,
                        None,
                    )

                    bot.send_message(
                        chat_id,
                        "✅ Assignment added successfully!",
                    )

                    show_assignment_menu(
                        chat_id
                    )

                except Exception as error:
                    print(
                        "Create assignment error:",
                        repr(error),
                    )

                    bot.send_message(
                        chat_id,
                        "❌ Could not save the assignment.",
                    )

                return

            state["step"] = "subject"

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

            bot.send_message(
                chat_id,
                (
                    "📚 Choose the subject.\n\n"
                    "Or choose ⏭ No Subject."
                ),
                reply_markup=markup,
            )
            return

        if step == "subject":
            subject_id = None

            if text != "⏭ No Subject":
                if not (
                    text.startswith(
                        "📚 #"
                    )
                ):
                    bot.send_message(
                        chat_id,
                        "❌ Choose a subject using the buttons.",
                    )
                    return

                try:
                    first_part = (
                        text.split(
                            " ",
                            2,
                        )[1]
                    )

                    subject_id = int(
                        first_part.replace(
                            "#",
                            ""
                        )
                    )

                except Exception:
                    bot.send_message(
                        chat_id,
                        "❌ Invalid subject selection.",
                    )
                    return

                if not get_subject_by_id(
                    message.from_user.id,
                    subject_id,
                ):
                    bot.send_message(
                        chat_id,
                        "❌ Subject not found.",
                    )
                    return

            try:
                create_assignment(
                    user_id=message.from_user.id,
                    title=state["title"],
                    description=state.get(
                        "description"
                    ),
                    due_at=state["due_at"],
                    priority=state["priority"],
                    subject_id=subject_id,
                )

                assignment_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    (
                        "✅ Assignment added!\n\n"
                        f"📌 {state['title']}\n"
                        f"🕒 "
                        f"{state['due_at'].strftime('%d-%m-%Y %I:%M %p')}\n"
                        f"{priority_icon(state['priority'])} "
                        f"{state['priority'].title()}"
                    ),
                )

                show_assignment_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Create assignment error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not save the assignment.",
                )

            return

        if step in {
            "complete",
            "delete",
        }:
            try:
                assignment_id = int(
                    text.replace(
                        "#",
                        ""
                    )
                )
            except ValueError:
                bot.send_message(
                    chat_id,
                    (
                        "❌ Send only the assignment number.\n"
                        "Example: 5"
                    ),
                )
                return

            try:
                if step == "complete":
                    success = complete_assignment(
                        message.from_user.id,
                        assignment_id,
                    )

                    success_text = (
                        "✅ Assignment marked complete!"
                    )

                else:
                    success = delete_assignment(
                        message.from_user.id,
                        assignment_id,
                    )

                    success_text = (
                        "✅ Assignment deleted."
                    )

                if not success:
                    bot.send_message(
                        chat_id,
                        "❌ Assignment not found.",
                    )
                    return

                assignment_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    success_text,
                )

                show_assignment_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Assignment action error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not update the assignment.",
                )

            return
