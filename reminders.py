from datetime import (
    datetime,
    timedelta
)

from zoneinfo import ZoneInfo
from telebot import types

from db import supabase


TIMEZONE = ZoneInfo(
    "Asia/Colombo"
)

reminder_state = {}
temp_reminder = {}


# ==================================================
# DATE
# ==================================================

def parse_date(text):

    text = (
        text.strip()
        .lower()
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
        .replace(" - ", "-")
        .replace(" / ", "/")
        .replace(" . ", ".")
    )

    today = datetime.now(
        TIMEZONE
    ).date()

    if text in [
        "today",
        "இன்று"
    ]:

        return today

    if text in [
        "tomorrow",
        "நாளை"
    ]:

        return today + timedelta(
            days=1
        )

    formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%d-%m-%y",
        "%d/%m/%y",
        "%Y-%m-%d",
        "%d %b %Y",
        "%d %B %Y"
    ]

    for fmt in formats:

        try:

            return datetime.strptime(
                text,
                fmt
            ).date()

        except ValueError:
            pass

    raise ValueError(
        "Invalid date"
    )


# ==================================================
# TIME
# ==================================================

def parse_time(text):

    text = text.strip().upper()

    formats = [
        "%I:%M %p",
        "%I.%M %p",
        "%H:%M"
    ]

    for fmt in formats:

        try:

            return datetime.strptime(
                text,
                fmt
            ).time()

        except ValueError:
            pass

    raise ValueError(
        "Invalid time"
    )


# ==================================================
# FORMAT SUPABASE TIME
# ==================================================

def format_database_time(value):

    value = value.replace(
        "Z",
        "+00:00"
    )

    dt = datetime.fromisoformat(
        value
    )

    dt = dt.astimezone(
        TIMEZONE
    )

    return dt.strftime(
        "%d-%m-%Y %I:%M %p"
    )


# ==================================================
# REGISTER
# ==================================================

def register_reminder_handlers(
    bot,
    show_main_menu
):


    # ==============================================
    # MENU
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        m.text == "⏰ Study Reminder"
    )
    def reminder_menu(message):

        chat_id = message.chat.id

        reminder_state.pop(
            chat_id,
            None
        )

        temp_reminder.pop(
            chat_id,
            None
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2
        )

        markup.add(
            types.KeyboardButton(
                "➕ Add Reminder"
            ),

            types.KeyboardButton(
                "📋 View Reminders"
            ),

            types.KeyboardButton(
                "🗑 Delete Reminder"
            ),

            types.KeyboardButton(
                "⬅️ Main Menu"
            )
        )

        bot.send_message(
            chat_id,
            """
⏰ Study Reminders

Choose an option:

➕ Add Reminder
📋 View Reminders
🗑 Delete Reminder
""",
            reply_markup=markup
        )


    # ==============================================
    # CANCEL
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        m.text == "❌ Cancel Reminder"
        and m.chat.id in reminder_state
    )
    def cancel_reminder(message):

        chat_id = message.chat.id

        reminder_state.pop(
            chat_id,
            None
        )

        temp_reminder.pop(
            chat_id,
            None
        )

        bot.send_message(
            chat_id,
            "❌ Reminder operation cancelled."
        )

        reminder_menu(
            message
        )


    # ==============================================
    # ADD
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        m.text == "➕ Add Reminder"
    )
    def add_reminder(message):

        chat_id = message.chat.id

        reminder_state[
            chat_id
        ] = "title"

        temp_reminder[
            chat_id
        ] = {}

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True
        )

        markup.add(
            types.KeyboardButton(
                "❌ Cancel Reminder"
            )
        )

        bot.send_message(
            chat_id,
            """
➕ New Study Reminder

First, send the reminder title.

Example:

Arabic Assignment
""",
            reply_markup=markup
        )


    # ==============================================
    # VIEW
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        m.text == "📋 View Reminders"
    )
    def view_reminders(message):

        user_id = message.from_user.id
        chat_id = message.chat.id

        try:

            response = (
                supabase
                .table("reminders")
                .select(
                    "id,title,remind_at"
                )
                .eq(
                    "user_id",
                    user_id
                )
                .eq(
                    "status",
                    "pending"
                )
                .order(
                    "remind_at"
                )
                .execute()
            )

            reminders = (
                response.data
                or []
            )

            if not reminders:

                bot.send_message(
                    chat_id,
                    """
📭 You don't have any upcoming reminders.
"""
                )

                return

            text = (
                "📋 Upcoming Reminders\n\n"
            )

            for reminder in reminders:

                when = format_database_time(
                    reminder[
                        "remind_at"
                    ]
                )

                text += (
                    f'⏰ #{reminder["id"]}\n'
                    f'📚 {reminder["title"]}\n'
                    f'🕒 {when}\n\n'
                )

            bot.send_message(
                chat_id,
                text
            )

        except Exception as e:

            print(
                "View reminder error:",
                e
            )

            bot.send_message(
                chat_id,
                "❌ Failed to load reminders."
            )


    # ==============================================
    # DELETE MENU
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        m.text == "🗑 Delete Reminder"
    )
    def delete_reminder_menu(message):

        user_id = message.from_user.id
        chat_id = message.chat.id

        try:

            response = (
                supabase
                .table("reminders")
                .select(
                    "id,title"
                )
                .eq(
                    "user_id",
                    user_id
                )
                .eq(
                    "status",
                    "pending"
                )
                .order(
                    "id"
                )
                .execute()
            )

            reminders = (
                response.data
                or []
            )

            if not reminders:

                bot.send_message(
                    chat_id,
                    "📭 No reminders to delete."
                )

                return

            text = (
                "🗑 Send the Reminder ID "
                "you want to delete:\n\n"
            )

            for reminder in reminders:

                text += (
                    f'#{reminder["id"]} - '
                    f'{reminder["title"]}\n'
                )

            reminder_state[
                chat_id
            ] = "delete"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True
            )

            markup.add(
                types.KeyboardButton(
                    "❌ Cancel Reminder"
                )
            )

            bot.send_message(
                chat_id,
                text,
                reply_markup=markup
            )

        except Exception as e:

            print(
                "Delete reminder menu error:",
                e
            )

            bot.send_message(
                chat_id,
                "❌ Failed to load reminders."
            )


    # ==============================================
    # INPUT
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        m.chat.id in reminder_state
    )
    def reminder_input(message):

        if not message.text:
            return

        chat_id = message.chat.id
        user_id = message.from_user.id

        text = message.text.strip()

        state = reminder_state.get(
            chat_id
        )


        # ======================================
        # TITLE
        # ======================================

        if state == "title":

            if not text:

                bot.send_message(
                    chat_id,
                    "❌ Enter a title."
                )

                return

            temp_reminder[
                chat_id
            ]["title"] = text

            reminder_state[
                chat_id
            ] = "date"

            bot.send_message(
                chat_id,
                """
📅 Enter the reminder date.

Examples:

today
tomorrow
25-10-2026
"""
            )

            return


        # ======================================
        # DATE
        # ======================================

        if state == "date":

            try:

                selected_date = parse_date(
                    text
                )

            except ValueError:

                bot.send_message(
                    chat_id,
                    """
❌ Invalid date.

Examples:

today
tomorrow
25-10-2026
"""
                )

                return

            temp_reminder[
                chat_id
            ]["date"] = selected_date

            reminder_state[
                chat_id
            ] = "time"

            bot.send_message(
                chat_id,
                """
🕒 Enter the reminder time.

Examples:

7:30 PM
10:00 AM
21:30
"""
            )

            return


        # ======================================
        # TIME
        # ======================================

        if state == "time":

            try:

                selected_time = parse_time(
                    text
                )

            except ValueError:

                bot.send_message(
                    chat_id,
                    """
❌ Invalid time.

Examples:

7:30 PM
10:00 AM
21:30
"""
                )

                return

            reminder_datetime = (
                datetime.combine(
                    temp_reminder[
                        chat_id
                    ]["date"],
                    selected_time
                )
                .replace(
                    tzinfo=TIMEZONE
                )
            )

            now = datetime.now(
                TIMEZONE
            )

            if reminder_datetime <= now:

                bot.send_message(
                    chat_id,
                    """
❌ That time has already passed.

Please enter a future time.
"""
                )

                return

            title = temp_reminder[
                chat_id
            ]["title"]

            try:

                response = (
                    supabase
                    .table("reminders")
                    .insert(
                        {
                            "user_id":
                                user_id,

                            "chat_id":
                                chat_id,

                            "title":
                                title,

                            "remind_at":
                                reminder_datetime.isoformat(),

                            "status":
                                "pending"
                        }
                    )
                    .select("id")
                    .execute()
                )

                reminder_id = (
                    response.data[0]["id"]
                    if response.data
                    else "Saved"
                )

                formatted = (
                    reminder_datetime
                    .strftime(
                        "%d-%m-%Y %I:%M %p"
                    )
                )

                reminder_state.pop(
                    chat_id,
                    None
                )

                temp_reminder.pop(
                    chat_id,
                    None
                )

                bot.send_message(
                    chat_id,
                    f"""
✅ Reminder created!

⏰ Reminder #{reminder_id}

📚 {title}

📅 {formatted}

🇱🇰 Sri Lanka Time
"""
                )

                reminder_menu(
                    message
                )

            except Exception as e:

                print(
                    "Create reminder error:",
                    e
                )

                bot.send_message(
                    chat_id,
                    "❌ Failed to create reminder."
                )

            return


        # ======================================
        # DELETE
        # ======================================

        if state == "delete":

            try:

                reminder_id = int(
                    text
                )

            except ValueError:

                bot.send_message(
                    chat_id,
                    """
❌ Send only the Reminder ID.

Example:

2
"""
                )

                return

            try:

                response = (
                    supabase
                    .table("reminders")
                    .select(
                        "id,title"
                    )
                    .eq(
                        "id",
                        reminder_id
                    )
                    .eq(
                        "user_id",
                        user_id
                    )
                    .eq(
                        "status",
                        "pending"
                    )
                    .execute()
                )

                if not response.data:

                    bot.send_message(
                        chat_id,
                        "❌ Reminder not found."
                    )

                    return

                title = response.data[
                    0
                ]["title"]

                (
                    supabase
                    .table("reminders")
                    .delete()
                    .eq(
                        "id",
                        reminder_id
                    )
                    .eq(
                        "user_id",
                        user_id
                    )
                    .execute()
                )

                reminder_state.pop(
                    chat_id,
                    None
                )

                bot.send_message(
                    chat_id,
                    f"""
🗑 Reminder deleted.

📚 {title}
"""
                )

                reminder_menu(
                    message
                )

            except Exception as e:

                print(
                    "Delete reminder error:",
                    e
                )

                bot.send_message(
                    chat_id,
                    "❌ Failed to delete reminder."
                )