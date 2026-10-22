import sqlite3
import threading
import time

from datetime import datetime
from zoneinfo import ZoneInfo
from telebot import types
from config import DB_NAME




TIMEZONE = ZoneInfo("Asia/Colombo")

reminder_state = {}
temp_reminder = {}


# ==================================================
# DATABASE
# ==================================================

def init_reminder_database():

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            remind_at TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


init_reminder_database()


# ==================================================
# DATE / TIME HELPERS
# ==================================================

def parse_date(text):

    from datetime import timedelta

    text = text.strip().lower()

    # Convert different dash characters to normal hyphen
    text = (
        text
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
    )

    # Remove spaces around separators
    text = text.replace(" - ", "-")
    text = text.replace(" / ", "/")
    text = text.replace(" . ", ".")

    today = datetime.now(
        TIMEZONE
    ).date()

    if text in ["today", "இன்று"]:
        return today

    if text in ["tomorrow", "நாளை"]:
        return today + timedelta(days=1)

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

    raise ValueError("Invalid date format")

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
        "Invalid time format"
    )


# ==================================================
# REMINDER WORKER
# ==================================================

def start_reminder_worker(bot):

    def worker():

        while True:

            try:

                now = datetime.now(
                    TIMEZONE
                )

                now_string = now.strftime(
                    "%Y-%m-%d %H:%M"
                )

                conn = sqlite3.connect(
                    DB_NAME
                )

                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT
                        id,
                        chat_id,
                        title,
                        remind_at
                    FROM reminders
                    WHERE status = 'pending'
                    AND remind_at <= ?
                    ORDER BY remind_at ASC
                    """,
                    (now_string,)
                )

                reminders = cursor.fetchall()

                conn.close()


                for reminder in reminders:

                    reminder_id = reminder[0]
                    chat_id = reminder[1]
                    title = reminder[2]
                    remind_at = reminder[3]

                    try:

                        formatted_time = datetime.strptime(
                            remind_at,
                            "%Y-%m-%d %H:%M"
                        ).strftime(
                            "%d-%m-%Y %I:%M %p"
                        )

                        bot.send_message(
                            chat_id,
                            f"""
⏰ Study Reminder

📚 {title}

🕒 {formatted_time}

It's time for your study task! 📖
"""
                        )

                        conn = sqlite3.connect(
                            DB_NAME
                        )

                        cursor = conn.cursor()

                        cursor.execute(
                            """
                            UPDATE reminders
                            SET status = 'sent'
                            WHERE id = ?
                            """,
                            (reminder_id,)
                        )

                        conn.commit()
                        conn.close()

                    except Exception as error:

                        print(
                            "Reminder send error:",
                            error
                        )


            except Exception as error:

                print(
                    "Reminder worker error:",
                    error
                )


            time.sleep(20)


    thread = threading.Thread(
        target=worker,
        daemon=True
    )

    thread.start()


# ==================================================
# REGISTER HANDLERS
# ==================================================

def register_reminder_handlers(
    bot,
    show_main_menu
):


    # ==============================================
    # REMINDER MENU
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
                "🏠 Main Menu"
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
    # ADD REMINDER
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
    # CANCEL
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        m.text == "❌ Cancel Reminder"
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
            "❌ Reminder creation cancelled."
        )

        reminder_menu(
            message
        )


    # ==============================================
    # VIEW REMINDERS
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        m.text == "📋 View Reminders"
    )
    def view_reminders(message):

        user_id = message.from_user.id
        chat_id = message.chat.id

        conn = sqlite3.connect(
            DB_NAME
        )

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                title,
                remind_at
            FROM reminders
            WHERE user_id = ?
            AND status = 'pending'
            ORDER BY remind_at ASC
            """,
            (user_id,)
        )

        reminders = cursor.fetchall()

        conn.close()


        if not reminders:

            bot.send_message(
                chat_id,
                """
📭 You don't have any upcoming reminders.
"""
            )

            return


        text = "📋 Upcoming Reminders\n\n"

        for reminder in reminders:

            reminder_id = reminder[0]
            title = reminder[1]
            remind_at = reminder[2]

            formatted = datetime.strptime(
                remind_at,
                "%Y-%m-%d %H:%M"
            ).strftime(
                "%d-%m-%Y %I:%M %p"
            )

            text += (
                f"⏰ #{reminder_id}\n"
                f"📚 {title}\n"
                f"🕒 {formatted}\n\n"
            )


        bot.send_message(
            chat_id,
            text
        )


    # ==============================================
    # DELETE REMINDER
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        m.text == "🗑 Delete Reminder"
    )
    def delete_reminder_menu(message):

        chat_id = message.chat.id
        user_id = message.from_user.id

        conn = sqlite3.connect(
            DB_NAME
        )

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                title,
                remind_at
            FROM reminders
            WHERE user_id = ?
            AND status = 'pending'
            ORDER BY remind_at ASC
            """,
            (user_id,)
        )

        reminders = cursor.fetchall()

        conn.close()


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
                f"#{reminder[0]} "
                f"- {reminder[1]}\n"
            )


        reminder_state[
            chat_id
        ] = "delete"


        bot.send_message(
            chat_id,
            text
        )


    # ==============================================
    # MAIN MENU
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        m.text == "🏠 Main Menu"
        and m.chat.id in reminder_state
    )
    def reminder_main_menu(message):

        chat_id = message.chat.id

        reminder_state.pop(
            chat_id,
            None
        )

        temp_reminder.pop(
            chat_id,
            None
        )

        name = (
            message.from_user.first_name
            or "Friend"
        )

        show_main_menu(
            chat_id,
            name
        )


    # ==============================================
    # REMINDER INPUT HANDLER
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        m.chat.id in reminder_state
    )
    def handle_reminder_input(message):

        chat_id = message.chat.id
        user_id = message.from_user.id

        if not message.text:
            return

        text = message.text.strip()

        state = reminder_state.get(
            chat_id
        )


        # ==========================================
        # TITLE
        # ==========================================

        if state == "title":

            if len(text) < 1:

                bot.send_message(
                    chat_id,
                    "❌ Please enter a title."
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

Use:

DD-MM-YYYY

Example:

25-10-2026
"""
            )

            return


        # ==========================================
        # DATE
        # ==========================================

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

Please use:

DD-MM-YYYY

Example:

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


        # ==========================================
        # TIME
        # ==========================================

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


            date_value = temp_reminder[
                chat_id
            ]["date"]


            reminder_datetime = datetime.combine(
                date_value,
                selected_time
            ).replace(
                tzinfo=TIMEZONE
            )


            now = datetime.now(
                TIMEZONE
            )


            if reminder_datetime <= now:

                bot.send_message(
                    chat_id,
                    """
❌ That time has already passed.

Please create the reminder again with a future date and time.
"""
                )

                reminder_state.pop(
                    chat_id,
                    None
                )

                temp_reminder.pop(
                    chat_id,
                    None
                )

                reminder_menu(
                    message
                )

                return


            title = temp_reminder[
                chat_id
            ]["title"]


            stored_time = reminder_datetime.strftime(
                "%Y-%m-%d %H:%M"
            )


            conn = sqlite3.connect(
                DB_NAME
            )

            cursor = conn.cursor()


            cursor.execute(
                """
                INSERT INTO reminders (
                    user_id,
                    chat_id,
                    title,
                    remind_at,
                    status
                )
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (
                    user_id,
                    chat_id,
                    title,
                    stored_time
                )
            )


            conn.commit()

            reminder_id = cursor.lastrowid

            conn.close()


            formatted = reminder_datetime.strftime(
                "%d-%m-%Y %I:%M %p"
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

🇱🇰 Timezone: Sri Lanka
"""
            )


            reminder_menu(
                message
            )

            return


        # ==========================================
        # DELETE
        # ==========================================

        if state == "delete":

            try:

                reminder_id = int(
                    text
                )

            except ValueError:

                bot.send_message(
                    chat_id,
                    """
❌ Send only the reminder number.

Example:

2
"""
                )

                return


            conn = sqlite3.connect(
                DB_NAME
            )

            cursor = conn.cursor()


            cursor.execute(
                """
                SELECT title
                FROM reminders
                WHERE id = ?
                AND user_id = ?
                AND status = 'pending'
                """,
                (
                    reminder_id,
                    user_id
                )
            )


            result = cursor.fetchone()


            if not result:

                conn.close()

                bot.send_message(
                    chat_id,
                    """
❌ Reminder not found.
"""
                )

                return


            cursor.execute(
                """
                DELETE FROM reminders
                WHERE id = ?
                AND user_id = ?
                """,
                (
                    reminder_id,
                    user_id
                )
            )


            conn.commit()
            conn.close()


            reminder_state.pop(
                chat_id,
                None
            )


            bot.send_message(
                chat_id,
                f"""
🗑 Reminder deleted.

📚 {result[0]}
"""
            )


            reminder_menu(
                message
            )