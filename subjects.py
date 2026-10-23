from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase


subject_state = {}


from navigation import GLOBAL_BUTTONS


def get_subjects(user_id):
    try:
        result = (
            supabase
            .table("subjects")
            .select("id,name,code,created_at")
            .eq("user_id", int(user_id))
            .order("name")
            .execute()
        )
        return result.data or []

    except Exception as error:
        print("Get subjects error:", repr(error))
        return []


def get_subject_by_id(user_id, subject_id):
    try:
        result = (
            supabase
            .table("subjects")
            .select("id,name,code,created_at")
            .eq("user_id", int(user_id))
            .eq("id", int(subject_id))
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0]

    except Exception as error:
        print("Get subject error:", repr(error))

    return None


def create_subject(user_id, name, code=None):
    payload = {
        "user_id": int(user_id),
        "name": name.strip(),
        "code": (
            code.strip()
            if code and code.strip()
            else None
        ),
    }

    return (
        supabase
        .table("subjects")
        .insert(payload)
        .execute()
    )


def delete_subject(user_id, subject_id):
    subject = get_subject_by_id(
        user_id,
        subject_id,
    )

    if not subject:
        return False

    (
        supabase
        .table("subjects")
        .delete()
        .eq("user_id", int(user_id))
        .eq("id", int(subject_id))
        .execute()
    )

    return True


def subject_display(subject):
    code = subject.get("code")

    if code:
        return (
            f"{subject['name']} "
            f"({code})"
        )

    return subject["name"]


def register_subject_handlers(
    bot,
    show_main_menu,
):

    def show_subject_menu(chat_id):
        subject_state.pop(
            chat_id,
            None,
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "➕ Add Subject"
            ),
            types.KeyboardButton(
                "📚 My Subjects"
            ),
            types.KeyboardButton(
                "🗑 Delete Subject"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "📚 Subjects\n\n"
                "Keep your notes, assignments, "
                "flashcards and quizzes organized "
                "by subject."
            ),
            reply_markup=markup,
        )

    def show_subjects(message):
        subjects = get_subjects(
            message.from_user.id
        )

        if not subjects:
            bot.send_message(
                message.chat.id,
                (
                    "📚 You do not have any subjects yet.\n\n"
                    "Choose ➕ Add Subject."
                ),
            )
            return

        lines = [
            "📚 My Subjects\n"
        ]

        for subject in subjects:
            lines.append(
                (
                    f"\n#{subject['id']}  "
                    f"{subject_display(subject)}"
                )
            )

        bot.send_message(
            message.chat.id,
            "".join(lines),
        )

    @bot.message_handler(
        commands=["subjects"]
    )
    def subjects_command(message):
        show_subject_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📚 Subjects"
    )
    def subjects_button(message):
        show_subject_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📚 My Subjects"
    )
    def my_subjects_button(message):
        show_subjects(message)

    @bot.message_handler(
        func=lambda m:
        m.text == "➕ Add Subject"
    )
    def add_subject_button(message):
        subject_state[
            message.chat.id
        ] = {
            "step": "add"
        }

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
        )

        markup.add(
            types.KeyboardButton(
                "🔙 Subjects Menu"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            message.chat.id,
            (
                "➕ Add Subject\n\n"
                "Send the subject name.\n\n"
                "You can optionally add a code using:\n"
                "Subject Name | Code\n\n"
                "Example:\n"
                "Data Analysis | ICT 1203"
            ),
            reply_markup=markup,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🗑 Delete Subject"
    )
    def delete_subject_button(message):
        subjects = get_subjects(
            message.from_user.id
        )

        if not subjects:
            bot.send_message(
                message.chat.id,
                "📚 No subjects to delete.",
            )
            return

        subject_state[
            message.chat.id
        ] = {
            "step": "delete"
        }

        lines = [
            "🗑 Delete Subject\n\n"
            "Send the subject number:\n"
        ]

        for subject in subjects:
            lines.append(
                (
                    f"\n#{subject['id']}  "
                    f"{subject_display(subject)}"
                )
            )

        bot.send_message(
            message.chat.id,
            "".join(lines),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔙 Subjects Menu"
    )
    def back_subjects(message):
        show_subject_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.chat.id in subject_state,
        content_types=["text"],
    )
    def subject_state_handler(message):
        chat_id = message.chat.id
        text = (message.text or "").strip()

        if text == "🏠 Main Menu":
            subject_state.pop(
                chat_id,
                None,
            )

            show_main_menu(
                chat_id,
                message.from_user.first_name
                or "Friend",
            )
            return

        if text == "🔙 Subjects Menu":
            show_subject_menu(
                chat_id
            )
            return

        # Never swallow commands or another module's main buttons.
        if (
            text.startswith("/")
            or text in GLOBAL_BUTTONS
        ):
            subject_state.pop(
                chat_id,
                None,
            )
            return ContinueHandling()

        state = subject_state.get(
            chat_id,
            {}
        )

        if state.get("step") == "add":
            if len(text) < 2:
                bot.send_message(
                    chat_id,
                    "❌ Please enter a valid subject name.",
                )
                return

            if len(text) > 120:
                bot.send_message(
                    chat_id,
                    "❌ Subject name is too long.",
                )
                return

            if "|" in text:
                name, code = (
                    part.strip()
                    for part in text.split(
                        "|",
                        1,
                    )
                )
            else:
                name = text
                code = None

            if not name:
                bot.send_message(
                    chat_id,
                    "❌ Subject name cannot be empty.",
                )
                return

            try:
                create_subject(
                    message.from_user.id,
                    name,
                    code,
                )

                subject_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    (
                        "✅ Subject added!\n\n"
                        f"📚 {name}"
                        + (
                            f"\n🏷 {code}"
                            if code
                            else ""
                        )
                    ),
                )

                show_subject_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Create subject error:",
                    repr(error),
                )

                error_text = str(error).lower()

                if (
                    "duplicate"
                    in error_text
                    or "unique"
                    in error_text
                ):
                    bot.send_message(
                        chat_id,
                        (
                            "❌ You already have a "
                            "subject with that name."
                        ),
                    )
                else:
                    bot.send_message(
                        chat_id,
                        (
                            "❌ Could not add the subject. "
                            "Please try again."
                        ),
                    )

            return

        if state.get("step") == "delete":
            try:
                subject_id = int(
                    text.replace("#", "")
                )
            except ValueError:
                bot.send_message(
                    chat_id,
                    (
                        "❌ Send only the subject number.\n"
                        "Example: 3"
                    ),
                )
                return

            try:
                deleted = delete_subject(
                    message.from_user.id,
                    subject_id,
                )

                if not deleted:
                    bot.send_message(
                        chat_id,
                        "❌ Subject not found.",
                    )
                    return

                subject_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    (
                        "✅ Subject deleted.\n\n"
                        "Existing assignments are kept, "
                        "but they will no longer be linked "
                        "to that subject."
                    ),
                )

                show_subject_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Delete subject error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not delete the subject.",
                )

            return
