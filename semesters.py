from datetime import datetime

from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase


semester_state = {}


from navigation import GLOBAL_BUTTONS


def get_semesters(
    user_id,
    limit=30,
):
    result = (
        supabase
        .table("semesters")
        .select(
            "id,user_id,name,start_date,end_date,"
            "gpa_scale,status,created_at"
        )
        .eq("user_id", int(user_id))
        .order(
            "created_at",
            desc=True,
        )
        .limit(limit)
        .execute()
    )

    return result.data or []


def get_semester(
    user_id,
    semester_id,
):
    result = (
        supabase
        .table("semesters")
        .select(
            "id,user_id,name,start_date,end_date,"
            "gpa_scale,status,created_at"
        )
        .eq("user_id", int(user_id))
        .eq("id", int(semester_id))
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def get_active_semester(
    user_id,
):
    result = (
        supabase
        .table("semesters")
        .select(
            "id,user_id,name,start_date,end_date,"
            "gpa_scale,status,created_at"
        )
        .eq("user_id", int(user_id))
        .eq("status", "active")
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def set_active_semester(
    user_id,
    semester_id,
):
    semester = get_semester(
        user_id,
        semester_id,
    )

    if not semester:
        return False

    (
        supabase
        .table("semesters")
        .update(
            {
                "status": "completed",
            }
        )
        .eq("user_id", int(user_id))
        .eq("status", "active")
        .execute()
    )

    (
        supabase
        .table("semesters")
        .update(
            {
                "status": "active",
            }
        )
        .eq("user_id", int(user_id))
        .eq("id", int(semester_id))
        .execute()
    )

    return True


def create_semester(
    user_id,
    name,
    start_date,
    end_date,
    gpa_scale,
):
    # New semester becomes active.
    (
        supabase
        .table("semesters")
        .update(
            {
                "status": "completed",
            }
        )
        .eq("user_id", int(user_id))
        .eq("status", "active")
        .execute()
    )

    result = (
        supabase
        .table("semesters")
        .insert(
            {
                "user_id": int(user_id),
                "name": name.strip(),
                "start_date": (
                    start_date.isoformat()
                    if start_date
                    else None
                ),
                "end_date": (
                    end_date.isoformat()
                    if end_date
                    else None
                ),
                "gpa_scale": float(
                    gpa_scale
                ),
                "status": "active",
            }
        )
        .execute()
    )

    return (
        result.data[0]
        if result.data
        else None
    )


def delete_semester(
    user_id,
    semester_id,
):
    semester = get_semester(
        user_id,
        semester_id,
    )

    if not semester:
        return False

    (
        supabase
        .table("semesters")
        .delete()
        .eq("user_id", int(user_id))
        .eq("id", int(semester_id))
        .execute()
    )

    return True


def register_semester_handlers(
    bot,
    show_main_menu,
):

    def show_semester_menu(
        chat_id
    ):
        semester_state.pop(
            chat_id,
            None,
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "➕ Add Semester"
            ),
            types.KeyboardButton(
                "🎓 My Semesters"
            ),
            types.KeyboardButton(
                "⭐ Set Active Semester"
            ),
            types.KeyboardButton(
                "🗑 Delete Semester"
            ),
            types.KeyboardButton(
                "📊 Grades & GPA"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        active = None

        try:
            active = get_active_semester(
                chat_id
            )
        except Exception:
            # chat_id usually equals user_id in private chats,
            # but do not rely on this result for functionality.
            active = None

        bot.send_message(
            chat_id,
            (
                "🎓 Semester Manager\n\n"
                "Create semesters, set your GPA scale, "
                "and choose which semester is currently active.\n\n"
                "When you add a new semester, it becomes active."
            ),
            reply_markup=markup,
        )

    @bot.message_handler(
        commands=["semesters"]
    )
    def semesters_command(
        message
    ):
        show_semester_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🎓 Semesters"
    )
    def semester_button(
        message
    ):
        show_semester_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🎓 My Semesters"
    )
    def my_semesters(
        message
    ):
        try:
            semesters = get_semesters(
                message.from_user.id
            )

            if not semesters:
                bot.send_message(
                    message.chat.id,
                    (
                        "🎓 No semesters yet.\n\n"
                        "Choose ➕ Add Semester."
                    ),
                )
                return

            parts = [
                "🎓 MY SEMESTERS\n"
            ]

            for semester in semesters:
                status = (
                    "⭐ ACTIVE"
                    if semester[
                        "status"
                    ] == "active"
                    else "✅ Completed"
                )

                dates = ""

                if semester.get(
                    "start_date"
                ):
                    dates += (
                        f"\n📅 Start: "
                        f"{semester['start_date']}"
                    )

                if semester.get(
                    "end_date"
                ):
                    dates += (
                        f"\n🏁 End: "
                        f"{semester['end_date']}"
                    )

                parts.append(
                    (
                        f"\n#{semester['id']} "
                        f"{semester['name']}\n"
                        f"{status}\n"
                        f"📊 GPA Scale: "
                        f"{float(semester['gpa_scale']):g}"
                        f"{dates}\n"
                    )
                )

            bot.send_message(
                message.chat.id,
                "\n".join(parts),
            )

        except Exception as error:
            print(
                "List semesters error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not load semesters.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "➕ Add Semester"
    )
    def add_semester(
        message
    ):
        semester_state[
            message.chat.id
        ] = {
            "step": "name"
        }

        bot.send_message(
            message.chat.id,
            (
                "🎓 Send the semester name.\n\n"
                "Example:\n"
                "Semester 1 - 2026/2027"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "⭐ Set Active Semester"
    )
    def choose_active(
        message
    ):
        semester_state[
            message.chat.id
        ] = {
            "step": "set_active"
        }

        bot.send_message(
            message.chat.id,
            (
                "⭐ Send the semester number you want active.\n"
                "Example: 2"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🗑 Delete Semester"
    )
    def delete_semester_button(
        message
    ):
        semester_state[
            message.chat.id
        ] = {
            "step": "delete"
        }

        bot.send_message(
            message.chat.id,
            (
                "🗑 Send the semester number.\n\n"
                "⚠️ Deleting a semester also deletes "
                "its saved course results."
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔙 Semester Menu"
    )
    def back_semester_menu(
        message
    ):
        show_semester_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.chat.id in semester_state,
        content_types=["text"],
    )
    def semester_state_handler(
        message
    ):
        chat_id = message.chat.id
        text = (
            message.text
            or ""
        ).strip()

        if text == "🏠 Main Menu":
            semester_state.pop(
                chat_id,
                None,
            )

            show_main_menu(
                chat_id,
                message.from_user.first_name
                or "Friend",
            )
            return

        if text == "🔙 Semester Menu":
            show_semester_menu(
                chat_id
            )
            return

        if (
            text.startswith("/")
            or text in GLOBAL_BUTTONS
        ):
            semester_state.pop(
                chat_id,
                None,
            )
            return ContinueHandling()

        state = semester_state.get(
            chat_id,
            {}
        )

        step = state.get(
            "step"
        )

        if step == "name":
            if len(text) < 2:
                bot.send_message(
                    chat_id,
                    "❌ Enter a valid semester name.",
                )
                return

            state[
                "name"
            ] = text

            state[
                "step"
            ] = "start_date"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
            )

            markup.add(
                types.KeyboardButton(
                    "⏭ Skip Start Date"
                ),
                types.KeyboardButton(
                    "🔙 Semester Menu"
                ),
            )

            bot.send_message(
                chat_id,
                (
                    "📅 Send the semester start date.\n\n"
                    "Example: 01-10-2026\n\n"
                    "Or choose ⏭ Skip Start Date."
                ),
                reply_markup=markup,
            )
            return

        if step == "start_date":
            if text == "⏭ Skip Start Date":
                start_date = None
            else:
                try:
                    start_date = datetime.strptime(
                        text,
                        "%d-%m-%Y",
                    ).date()

                except ValueError:
                    bot.send_message(
                        chat_id,
                        (
                            "❌ Invalid date.\n"
                            "Use: 01-10-2026"
                        ),
                    )
                    return

            state[
                "start_date"
            ] = start_date

            state[
                "step"
            ] = "end_date"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
            )

            markup.add(
                types.KeyboardButton(
                    "⏭ Skip End Date"
                ),
                types.KeyboardButton(
                    "🔙 Semester Menu"
                ),
            )

            bot.send_message(
                chat_id,
                (
                    "🏁 Send the semester end date.\n\n"
                    "Example: 28-02-2027\n\n"
                    "Or choose ⏭ Skip End Date."
                ),
                reply_markup=markup,
            )
            return

        if step == "end_date":
            if text == "⏭ Skip End Date":
                end_date = None
            else:
                try:
                    end_date = datetime.strptime(
                        text,
                        "%d-%m-%Y",
                    ).date()

                except ValueError:
                    bot.send_message(
                        chat_id,
                        (
                            "❌ Invalid date.\n"
                            "Use: 28-02-2027"
                        ),
                    )
                    return

            if (
                end_date
                and state.get(
                    "start_date"
                )
                and end_date
                < state[
                    "start_date"
                ]
            ):
                bot.send_message(
                    chat_id,
                    (
                        "❌ End date cannot be before "
                        "the start date."
                    ),
                )
                return

            state[
                "end_date"
            ] = end_date

            state[
                "step"
            ] = "gpa_scale"

            bot.send_message(
                chat_id,
                (
                    "📊 Send your university's maximum GPA scale.\n\n"
                    "Common example: 4.0\n\n"
                    "Enter the scale your university uses."
                ),
            )
            return

        if step == "gpa_scale":
            try:
                gpa_scale = float(
                    text
                )

            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Enter a number such as 4.0.",
                )
                return

            if not 0 < gpa_scale <= 100:
                bot.send_message(
                    chat_id,
                    "❌ GPA scale must be greater than 0.",
                )
                return

            try:
                semester = create_semester(
                    user_id=message.from_user.id,
                    name=state[
                        "name"
                    ],
                    start_date=state.get(
                        "start_date"
                    ),
                    end_date=state.get(
                        "end_date"
                    ),
                    gpa_scale=gpa_scale,
                )

                semester_state.pop(
                    chat_id,
                    None,
                )

                if not semester:
                    raise RuntimeError(
                        "Semester was not saved."
                    )

                bot.send_message(
                    chat_id,
                    (
                        "✅ Semester created and set active!\n\n"
                        f"🎓 {state['name']}\n"
                        f"📊 GPA Scale: {gpa_scale:g}"
                    ),
                )

                show_semester_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Create semester error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not create semester.",
                )

            return

        if step in {
            "set_active",
            "delete",
        }:
            try:
                semester_id = int(
                    text.replace(
                        "#",
                        ""
                    )
                )

            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Send only the semester number.",
                )
                return

            try:
                if step == "set_active":
                    success = set_active_semester(
                        message.from_user.id,
                        semester_id,
                    )

                    success_text = (
                        "⭐ Active semester updated."
                    )

                else:
                    success = delete_semester(
                        message.from_user.id,
                        semester_id,
                    )

                    success_text = (
                        "✅ Semester deleted."
                    )

                if not success:
                    bot.send_message(
                        chat_id,
                        "❌ Semester not found.",
                    )
                    return

                semester_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    success_text,
                )

                show_semester_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Semester action error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not update semester.",
                )

            return
