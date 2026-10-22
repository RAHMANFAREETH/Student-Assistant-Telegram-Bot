import sqlite3
from telebot import types
from config import DB_NAME

note_mode = {}
temp_note = {}


# ==================================================
# DATABASE
# ==================================================

def init_database():

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


init_database()


# ==================================================
# REGISTER NOTE HANDLERS
# ==================================================

def register_note_handlers(bot, show_main_menu):


    # ==============================================
    # NOTES MENU
    # ==============================================

    @bot.message_handler(
        func=lambda m: m.text == "📝 Notes"
    )
    def notes_menu(message):

        chat_id = message.chat.id

        note_mode.pop(chat_id, None)
        temp_note.pop(chat_id, None)

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2
        )

        markup.add(
            types.KeyboardButton("➕ Add Note"),
            types.KeyboardButton("📚 View Notes"),
            types.KeyboardButton("🔍 Search Notes"),
            types.KeyboardButton("🗑 Delete Note"),
            types.KeyboardButton("⬅️ Main Menu")
        )

        bot.send_message(
            chat_id,
            """
📝 My Notes

Choose an option:

➕ Add a new note
📚 View saved notes
🔍 Search notes
🗑 Delete a note
""",
            reply_markup=markup
        )


    # ==============================================
    # ADD NOTE
    # ==============================================

    @bot.message_handler(
        func=lambda m: m.text == "➕ Add Note"
    )
    def add_note(message):

        chat_id = message.chat.id

        note_mode[chat_id] = "waiting_title"

        temp_note[chat_id] = {}

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True
        )

        markup.add(
            types.KeyboardButton("❌ Cancel Note")
        )

        bot.send_message(
            chat_id,
            """
➕ Add Note

Send me the title of your note.

Example:

Database Lecture
""",
            reply_markup=markup
        )


    # ==============================================
    # CANCEL
    # ==============================================

    @bot.message_handler(
        func=lambda m: m.text == "❌ Cancel Note"
    )
    def cancel_note(message):

        chat_id = message.chat.id

        note_mode.pop(chat_id, None)
        temp_note.pop(chat_id, None)

        bot.send_message(
            chat_id,
            "❌ Note creation cancelled."
        )

        notes_menu(message)


    # ==============================================
    # VIEW NOTES
    # ==============================================

    @bot.message_handler(
        func=lambda m: m.text == "📚 View Notes"
    )
    def view_notes(message):

        user_id = message.from_user.id

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, title, content, created_at
            FROM notes
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,)
        )

        notes = cursor.fetchall()

        conn.close()

        if not notes:

            bot.send_message(
                message.chat.id,
                """
📭 You don't have any saved notes yet.

Press:

➕ Add Note
"""
            )

            return

        bot.send_message(
            message.chat.id,
            f"📚 You have {len(notes)} saved note(s):"
        )

        for note in notes:

            note_id = note[0]
            title = note[1]
            content = note[2]
            created = note[3]

            bot.send_message(
                message.chat.id,
                f"""
📝 Note #{note_id}

📌 {title}

{content}

🕒 {created}
"""
            )


    # ==============================================
    # SEARCH NOTES
    # ==============================================

    @bot.message_handler(
        func=lambda m: m.text == "🔍 Search Notes"
    )
    def search_notes(message):

        chat_id = message.chat.id

        note_mode[chat_id] = "search"

        bot.send_message(
            chat_id,
            """
🔍 Search Notes

Send a word or phrase.

Example:

Python
"""
        )


    # ==============================================
    # DELETE NOTE
    # ==============================================

    @bot.message_handler(
        func=lambda m: m.text == "🗑 Delete Note"
    )
    def delete_note(message):

        chat_id = message.chat.id
        user_id = message.from_user.id

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, title
            FROM notes
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,)
        )

        notes = cursor.fetchall()

        conn.close()

        if not notes:

            bot.send_message(
                chat_id,
                "📭 You don't have any notes to delete."
            )

            return

        text = "🗑 Send the Note ID you want to delete:\n\n"

        for note in notes:

            text += (
                f"#{note[0]} - {note[1]}\n"
            )

        note_mode[chat_id] = "delete"

        bot.send_message(
            chat_id,
            text
        )


    # ==============================================
    # BACK TO MAIN MENU
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        m.text == "⬅️ Main Menu"
        and (
            m.chat.id in note_mode
            or m.text == "⬅️ Main Menu"
        )
    )
    def note_back_main(message):

        chat_id = message.chat.id

        note_mode.pop(chat_id, None)
        temp_note.pop(chat_id, None)

        first_name = (
            message.from_user.first_name
            or "Friend"
        )

        show_main_menu(
            chat_id,
            first_name
        )


    # ==============================================
    # HANDLE NOTE TEXT
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        m.chat.id in note_mode
    )
    def handle_note_text(message):

        chat_id = message.chat.id
        user_id = message.from_user.id

        mode = note_mode.get(chat_id)


        # ==========================================
        # TITLE
        # ==========================================

        if mode == "waiting_title":

            title = message.text.strip()

            if len(title) < 1:

                bot.send_message(
                    chat_id,
                    "❌ Please send a valid title."
                )

                return

            if len(title) > 100:

                bot.send_message(
                    chat_id,
                    "❌ Keep the title below 100 characters."
                )

                return

            temp_note[chat_id]["title"] = title

            note_mode[chat_id] = "waiting_content"

            bot.send_message(
                chat_id,
                """
✅ Title saved.

Now send the content of your note.

You can write multiple sentences or paragraphs.
"""
            )


        # ==========================================
        # CONTENT
        # ==========================================

        elif mode == "waiting_content":

            content = message.text.strip()

            if not content:

                bot.send_message(
                    chat_id,
                    "❌ Note content cannot be empty."
                )

                return

            title = temp_note[
                chat_id
            ]["title"]

            conn = sqlite3.connect(
                DB_NAME
            )

            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO notes (
                    user_id,
                    title,
                    content
                )
                VALUES (?, ?, ?)
                """,
                (
                    user_id,
                    title,
                    content
                )
            )

            conn.commit()

            note_id = cursor.lastrowid

            conn.close()

            note_mode.pop(
                chat_id,
                None
            )

            temp_note.pop(
                chat_id,
                None
            )

            bot.send_message(
                chat_id,
                f"""
✅ Note saved successfully!

📝 Note ID: {note_id}

📌 {title}
"""
            )

            notes_menu(message)


        # ==========================================
        # SEARCH
        # ==========================================

        elif mode == "search":

            keyword = message.text.strip()

            if not keyword:

                bot.send_message(
                    chat_id,
                    "❌ Please enter something to search."
                )

                return

            conn = sqlite3.connect(
                DB_NAME
            )

            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, title, content
                FROM notes
                WHERE user_id = ?
                AND (
                    title LIKE ?
                    OR content LIKE ?
                )
                ORDER BY id DESC
                """,
                (
                    user_id,
                    f"%{keyword}%",
                    f"%{keyword}%"
                )
            )

            results = cursor.fetchall()

            conn.close()

            note_mode.pop(
                chat_id,
                None
            )

            if not results:

                bot.send_message(
                    chat_id,
                    f"""
🔍 No notes found for:

{keyword}
"""
                )

                notes_menu(message)

                return

            bot.send_message(
                chat_id,
                f"""
🔍 Search results for:

{keyword}

Found: {len(results)}
"""
            )

            for note in results:

                bot.send_message(
                    chat_id,
                    f"""
📝 Note #{note[0]}

📌 {note[1]}

{note[2]}
"""
                )

            notes_menu(message)


        # ==========================================
        # DELETE
        # ==========================================

        elif mode == "delete":

            try:

                note_id = int(
                    message.text.strip()
                )

            except ValueError:

                bot.send_message(
                    chat_id,
                    """
❌ Invalid Note ID.

Send only the number.

Example:

3
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
                FROM notes
                WHERE id = ?
                AND user_id = ?
                """,
                (
                    note_id,
                    user_id
                )
            )

            note = cursor.fetchone()

            if not note:

                conn.close()

                bot.send_message(
                    chat_id,
                    """
❌ Note not found.

Make sure you entered the correct Note ID.
"""
                )

                return

            cursor.execute(
                """
                DELETE FROM notes
                WHERE id = ?
                AND user_id = ?
                """,
                (
                    note_id,
                    user_id
                )
            )

            conn.commit()
            conn.close()

            note_mode.pop(
                chat_id,
                None
            )

            bot.send_message(
                chat_id,
                f"""
🗑 Note deleted successfully!

📌 {note[0]}
"""
            )

            notes_menu(message)