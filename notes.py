from telebot import types
from db import supabase


note_mode = {}
temp_note = {}


def register_note_handlers(
    bot,
    show_main_menu
):

    # ==========================================
    # NOTES MENU
    # ==========================================

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
            types.KeyboardButton("🏠 Main Menu")
        )

        bot.send_message(
            chat_id,
            """
📝 My Notes

Choose an option:

➕ Add Note
📚 View Notes
🔍 Search Notes
🗑 Delete Note
""",
            reply_markup=markup
        )


    # ==========================================
    # CANCEL
    # ==========================================

    @bot.message_handler(
        func=lambda m:
        m.text == "❌ Cancel Note"
        and m.chat.id in note_mode
    )
    def cancel_note(message):

        chat_id = message.chat.id

        note_mode.pop(chat_id, None)
        temp_note.pop(chat_id, None)

        bot.send_message(
            chat_id,
            "❌ Operation cancelled."
        )

        notes_menu(message)


    # ==========================================
    # ADD NOTE
    # ==========================================

    @bot.message_handler(
        func=lambda m: m.text == "➕ Add Note"
    )
    def add_note(message):

        chat_id = message.chat.id

        note_mode[chat_id] = "title"
        temp_note[chat_id] = {}

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True
        )

        markup.add(
            types.KeyboardButton(
                "❌ Cancel Note"
            )
        )

        bot.send_message(
            chat_id,
            """
➕ Add Note

Send the title of your note.

Example:

Python Lecture
""",
            reply_markup=markup
        )


    # ==========================================
    # VIEW NOTES
    # ==========================================

    @bot.message_handler(
        func=lambda m: m.text == "📚 View Notes"
    )
    def view_notes(message):

        user_id = message.from_user.id
        chat_id = message.chat.id

        try:

            response = (
                supabase
                .table("notes")
                .select(
                    "id,title,content,created_at"
                )
                .eq(
                    "user_id",
                    user_id
                )
                .order(
                    "id",
                    desc=True
                )
                .execute()
            )

            notes = response.data or []

            if not notes:

                bot.send_message(
                    chat_id,
                    """
📭 You don't have any saved notes yet.
"""
                )

                return

            bot.send_message(
                chat_id,
                f"📚 Saved notes: {len(notes)}"
            )

            for note in notes:

                bot.send_message(
                    chat_id,
                    f"""
📝 Note #{note["id"]}

📌 {note["title"]}

{note["content"]}
"""
                )

        except Exception as e:

            print(
                "View notes error:",
                e
            )

            bot.send_message(
                chat_id,
                "❌ Failed to load notes."
            )


    # ==========================================
    # SEARCH
    # ==========================================

    @bot.message_handler(
        func=lambda m: m.text == "🔍 Search Notes"
    )
    def search_notes(message):

        chat_id = message.chat.id

        note_mode[chat_id] = "search"

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True
        )

        markup.add(
            types.KeyboardButton(
                "❌ Cancel Note"
            )
        )

        bot.send_message(
            chat_id,
            """
🔍 Search Notes

Send a word or phrase.

Example:

Python
""",
            reply_markup=markup
        )


    # ==========================================
    # DELETE MENU
    # ==========================================

    @bot.message_handler(
        func=lambda m: m.text == "🗑 Delete Note"
    )
    def delete_note_menu(message):

        chat_id = message.chat.id
        user_id = message.from_user.id

        try:

            response = (
                supabase
                .table("notes")
                .select(
                    "id,title"
                )
                .eq(
                    "user_id",
                    user_id
                )
                .order(
                    "id",
                    desc=True
                )
                .execute()
            )

            notes = response.data or []

            if not notes:

                bot.send_message(
                    chat_id,
                    "📭 No notes to delete."
                )

                return

            text = (
                "🗑 Send the Note ID "
                "you want to delete:\n\n"
            )

            for note in notes:

                text += (
                    f'#{note["id"]} - '
                    f'{note["title"]}\n'
                )

            note_mode[chat_id] = "delete"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True
            )

            markup.add(
                types.KeyboardButton(
                    "❌ Cancel Note"
                )
            )

            bot.send_message(
                chat_id,
                text,
                reply_markup=markup
            )

        except Exception as e:

            print(
                "Delete menu error:",
                e
            )

            bot.send_message(
                chat_id,
                "❌ Failed to load notes."
            )


    # ==========================================
    # NOTE INPUT
    # ==========================================

    @bot.message_handler(
        func=lambda m:
        m.chat.id in note_mode
    )
    def handle_note_input(message):

        if not message.text:
            return

        chat_id = message.chat.id
        user_id = message.from_user.id

        text = message.text.strip()

        # V6.5.1: navigation must never be saved as a note.
        if text in ("🏠 Main Menu", "⬅️ Main Menu"):
            note_mode.pop(chat_id, None)
            temp_note.pop(chat_id, None)
            show_main_menu(chat_id, message.from_user.first_name or "Friend")
            return


        mode = note_mode.get(
            chat_id
        )


        # ======================================
        # TITLE
        # ======================================

        if mode == "title":

            if not text:

                bot.send_message(
                    chat_id,
                    "❌ Enter a valid title."
                )

                return

            temp_note[
                chat_id
            ]["title"] = text

            note_mode[
                chat_id
            ] = "content"

            bot.send_message(
                chat_id,
                """
✅ Title saved.

Now send the note content.
"""
            )

            return


        # ======================================
        # CONTENT
        # ======================================

        if mode == "content":

            title = temp_note[
                chat_id
            ]["title"]

            try:

                response = (
                    supabase
                    .table("notes")
                    .insert(
                        {
                            "user_id": user_id,
                            "title": title,
                            "content": text
                        }
                    )
                    .select("id")
                    .execute()
                )

                note_id = (
                    response.data[0]["id"]
                    if response.data
                    else "Saved"
                )

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

                notes_menu(
                    message
                )

            except Exception as e:

                print(
                    "Save note error:",
                    e
                )

                bot.send_message(
                    chat_id,
                    "❌ Failed to save note."
                )

            return


        # ======================================
        # SEARCH
        # ======================================

        if mode == "search":

            keyword = text.casefold()

            try:

                response = (
                    supabase
                    .table("notes")
                    .select(
                        "id,title,content"
                    )
                    .eq(
                        "user_id",
                        user_id
                    )
                    .order(
                        "id",
                        desc=True
                    )
                    .execute()
                )

                notes = response.data or []

                results = [
                    note
                    for note in notes
                    if (
                        keyword
                        in note[
                            "title"
                        ].casefold()
                        or
                        keyword
                        in note[
                            "content"
                        ].casefold()
                    )
                ]

                note_mode.pop(
                    chat_id,
                    None
                )

                if not results:

                    bot.send_message(
                        chat_id,
                        "🔍 No matching notes found."
                    )

                    notes_menu(
                        message
                    )

                    return

                bot.send_message(
                    chat_id,
                    f"""
🔍 Results found: {len(results)}
"""
                )

                for note in results:

                    bot.send_message(
                        chat_id,
                        f"""
📝 Note #{note["id"]}

📌 {note["title"]}

{note["content"]}
"""
                    )

                notes_menu(
                    message
                )

            except Exception as e:

                print(
                    "Search error:",
                    e
                )

                bot.send_message(
                    chat_id,
                    "❌ Note search failed."
                )

            return


        # ======================================
        # DELETE
        # ======================================

        if mode == "delete":

            try:

                note_id = int(text)

            except ValueError:

                bot.send_message(
                    chat_id,
                    """
❌ Send only the Note ID number.

Example:

3
"""
                )

                return

            try:

                response = (
                    supabase
                    .table("notes")
                    .select(
                        "id,title"
                    )
                    .eq(
                        "id",
                        note_id
                    )
                    .eq(
                        "user_id",
                        user_id
                    )
                    .execute()
                )

                if not response.data:

                    bot.send_message(
                        chat_id,
                        "❌ Note not found."
                    )

                    return

                title = response.data[
                    0
                ]["title"]

                (
                    supabase
                    .table("notes")
                    .delete()
                    .eq(
                        "id",
                        note_id
                    )
                    .eq(
                        "user_id",
                        user_id
                    )
                    .execute()
                )

                note_mode.pop(
                    chat_id,
                    None
                )

                bot.send_message(
                    chat_id,
                    f"""
🗑 Note deleted!

📌 {title}
"""
                )

                notes_menu(
                    message
                )

            except Exception as e:

                print(
                    "Delete note error:",
                    e
                )

                bot.send_message(
                    chat_id,
                    "❌ Failed to delete note."
                )