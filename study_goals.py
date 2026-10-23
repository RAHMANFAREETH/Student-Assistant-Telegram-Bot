from datetime import datetime, timezone

from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase
from subjects import (
    get_subjects,
    get_subject_by_id,
    subject_display,
)


goal_state = {}


from navigation import GLOBAL_BUTTONS


def get_goals(
    user_id,
    status="pending",
    limit=50,
):
    query = (
        supabase
        .table("study_goals")
        .select(
            "id,user_id,subject_id,title,description,"
            "target_date,status,created_at,completed_at"
        )
        .eq("user_id", int(user_id))
    )

    if status:
        query = query.eq(
            "status",
            status,
        )

    result = (
        query
        .order("target_date")
        .limit(limit)
        .execute()
    )

    return result.data or []


def get_goal(
    user_id,
    goal_id,
):
    result = (
        supabase
        .table("study_goals")
        .select(
            "id,user_id,subject_id,title,description,"
            "target_date,status"
        )
        .eq("user_id", int(user_id))
        .eq("id", int(goal_id))
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def create_goal(
    user_id,
    subject_id,
    title,
    description=None,
    target_date=None,
):
    result = (
        supabase
        .table("study_goals")
        .insert(
            {
                "user_id": int(user_id),
                "subject_id": subject_id,
                "title": title.strip(),
                "description": (
                    description.strip()
                    if description
                    else None
                ),
                "target_date": (
                    target_date.isoformat()
                    if target_date
                    else None
                ),
                "status": "pending",
            }
        )
        .execute()
    )

    return (
        result.data[0]
        if result.data
        else None
    )


def complete_goal(
    user_id,
    goal_id,
):
    goal = get_goal(
        user_id,
        goal_id,
    )

    if not goal:
        return False

    (
        supabase
        .table("study_goals")
        .update(
            {
                "status": "completed",
                "completed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
        )
        .eq("user_id", int(user_id))
        .eq("id", int(goal_id))
        .execute()
    )

    return True


def delete_goal(
    user_id,
    goal_id,
):
    goal = get_goal(
        user_id,
        goal_id,
    )

    if not goal:
        return False

    (
        supabase
        .table("study_goals")
        .delete()
        .eq("user_id", int(user_id))
        .eq("id", int(goal_id))
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


def format_goal(
    user_id,
    goal,
):
    description = (
        goal.get(
            "description"
        )
        or ""
    ).strip()

    target_date = (
        goal.get(
            "target_date"
        )
        or "No deadline"
    )

    extra = (
        f"\n📝 {description}"
        if description
        else ""
    )

    return (
        f"#{goal['id']} {goal['title']}\n"
        f"📚 {subject_name(user_id, goal.get('subject_id'))}\n"
        f"🎯 Target: {target_date}"
        f"{extra}"
    )


def register_study_goal_handlers(
    bot,
    show_main_menu,
):

    def show_goal_menu(
        chat_id
    ):
        goal_state.pop(
            chat_id,
            None,
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "➕ Add Goal"
            ),
            types.KeyboardButton(
                "🎯 Active Goals"
            ),
            types.KeyboardButton(
                "✅ Complete Goal"
            ),
            types.KeyboardButton(
                "🏆 Completed Goals"
            ),
            types.KeyboardButton(
                "🗑 Delete Goal"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "🎯 Study Goals\n\n"
                "Create clear academic goals and "
                "track them until completion."
            ),
            reply_markup=markup,
        )

    def send_goal_list(
        message,
        goals,
        heading,
    ):
        if not goals:
            bot.send_message(
                message.chat.id,
                f"{heading}\n\n✅ Nothing here.",
            )
            return

        parts = [
            heading,
            "",
        ]

        for goal in goals:
            parts.append(
                format_goal(
                    message.from_user.id,
                    goal,
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
        commands=["goals"]
    )
    def goals_command(message):
        show_goal_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🎯 Study Goals"
    )
    def goals_button(message):
        show_goal_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🎯 Active Goals"
    )
    def active_goals(message):
        send_goal_list(
            message,
            get_goals(
                message.from_user.id,
                status="pending",
            ),
            "🎯 ACTIVE GOALS",
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🏆 Completed Goals"
    )
    def completed_goals(message):
        send_goal_list(
            message,
            get_goals(
                message.from_user.id,
                status="completed",
            ),
            "🏆 COMPLETED GOALS",
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "➕ Add Goal"
    )
    def add_goal(message):
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
                "🔙 Goals Menu"
            )
        )

        goal_state[
            message.chat.id
        ] = {
            "step": "subject"
        }

        bot.send_message(
            message.chat.id,
            "📚 Choose a subject for the goal:",
            reply_markup=markup,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "✅ Complete Goal"
    )
    def complete_goal_button(message):
        goal_state[
            message.chat.id
        ] = {
            "step": "complete"
        }

        bot.send_message(
            message.chat.id,
            (
                "✅ Send the goal number.\n"
                "Example: 3"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🗑 Delete Goal"
    )
    def delete_goal_button(message):
        goal_state[
            message.chat.id
        ] = {
            "step": "delete"
        }

        bot.send_message(
            message.chat.id,
            (
                "🗑 Send the goal number.\n"
                "Example: 3"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔙 Goals Menu"
    )
    def back_goals(message):
        show_goal_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.chat.id in goal_state,
        content_types=["text"],
    )
    def goal_state_handler(
        message
    ):
        chat_id = message.chat.id
        text = (
            message.text
            or ""
        ).strip()

        if text == "🏠 Main Menu":
            goal_state.pop(
                chat_id,
                None,
            )

            show_main_menu(
                chat_id,
                message.from_user.first_name
                or "Friend",
            )
            return

        if text == "🔙 Goals Menu":
            show_goal_menu(
                chat_id
            )
            return

        if (
            text.startswith("/")
            or text in GLOBAL_BUTTONS
        ):
            goal_state.pop(
                chat_id,
                None,
            )
            return ContinueHandling()

        state = goal_state.get(
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
                    "🎯 Send the goal title.\n\n"
                    "Example:\n"
                    "Finish Chapter 5 revision"
                ),
            )
            return

        if step == "title":
            if len(text) < 2:
                bot.send_message(
                    chat_id,
                    "❌ Enter a valid goal title.",
                )
                return

            state[
                "title"
            ] = text

            state[
                "step"
            ] = "description"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
            )

            markup.add(
                types.KeyboardButton(
                    "⏭ Skip Description"
                ),
                types.KeyboardButton(
                    "🔙 Goals Menu"
                ),
            )

            bot.send_message(
                chat_id,
                (
                    "📝 Add an optional description.\n\n"
                    "Or choose ⏭ Skip Description."
                ),
                reply_markup=markup,
            )
            return

        if step == "description":
            state[
                "description"
            ] = (
                None
                if text == "⏭ Skip Description"
                else text
            )

            state[
                "step"
            ] = "target_date"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
            )

            markup.add(
                types.KeyboardButton(
                    "⏭ No Deadline"
                ),
                types.KeyboardButton(
                    "🔙 Goals Menu"
                ),
            )

            bot.send_message(
                chat_id,
                (
                    "📅 Send target date.\n\n"
                    "Example: 30-11-2026\n\n"
                    "Or choose ⏭ No Deadline."
                ),
                reply_markup=markup,
            )
            return

        if step == "target_date":
            if text == "⏭ No Deadline":
                target_date = None
            else:
                try:
                    target_date = datetime.strptime(
                        text,
                        "%d-%m-%Y",
                    ).date()

                except ValueError:
                    bot.send_message(
                        chat_id,
                        (
                            "❌ Invalid date.\n"
                            "Use: 30-11-2026"
                        ),
                    )
                    return

            try:
                goal = create_goal(
                    user_id=message.from_user.id,
                    subject_id=state.get(
                        "subject_id"
                    ),
                    title=state[
                        "title"
                    ],
                    description=state.get(
                        "description"
                    ),
                    target_date=target_date,
                )

                goal_state.pop(
                    chat_id,
                    None,
                )

                if not goal:
                    raise RuntimeError(
                        "Goal was not saved."
                    )

                bot.send_message(
                    chat_id,
                    (
                        "✅ Study goal created!\n\n"
                        f"🎯 {state['title']}"
                    ),
                )

                show_goal_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Create study goal error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not create study goal.",
                )

            return

        if step in {
            "complete",
            "delete",
        }:
            try:
                goal_id = int(
                    text.replace(
                        "#",
                        ""
                    )
                )

            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Send only the goal number.",
                )
                return

            try:
                if step == "complete":
                    success = complete_goal(
                        message.from_user.id,
                        goal_id,
                    )

                    success_text = (
                        "🏆 Goal completed!"
                    )

                else:
                    success = delete_goal(
                        message.from_user.id,
                        goal_id,
                    )

                    success_text = (
                        "✅ Goal deleted."
                    )

                if not success:
                    bot.send_message(
                        chat_id,
                        "❌ Goal not found.",
                    )
                    return

                goal_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    success_text,
                )

                show_goal_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Study goal action error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not update study goal.",
                )

            return
