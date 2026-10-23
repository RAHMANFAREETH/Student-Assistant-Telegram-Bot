import re

from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase


search_state = {}


from navigation import GLOBAL_BUTTONS


def _clean_preview(
    text,
    query,
    radius=100,
):
    text = (
        text
        or ""
    )

    clean = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    if not clean:
        return ""

    location = (
        clean.casefold()
        .find(
            query.casefold()
        )
    )

    if location < 0:
        return clean[
            :220
        ]

    start = max(
        0,
        location - radius,
    )

    end = min(
        len(clean),
        location
        + len(query)
        + radius,
    )

    prefix = (
        "…"
        if start > 0
        else ""
    )

    suffix = (
        "…"
        if end < len(clean)
        else ""
    )

    return (
        prefix
        + clean[
            start:end
        ]
        + suffix
    )


def _contains(
    query,
    *values
):
    needle = query.casefold()

    for value in values:
        if (
            value is not None
            and needle
            in str(value).casefold()
        ):
            return True

    return False


def search_user_data(
    user_id,
    query,
):
    matches = []

    # ==================================================
    # NOTES
    # ==================================================

    try:
        result = (
            supabase
            .table(
                "notes"
            )
            .select(
                "id,title,content"
            )
            .eq(
                "user_id",
                int(user_id),
            )
            .order(
                "created_at",
                desc=True,
            )
            .limit(100)
            .execute()
        )

        for item in (
            result.data
            or []
        ):
            if _contains(
                query,
                item.get(
                    "title"
                ),
                item.get(
                    "content"
                ),
            ):
                matches.append(
                    {
                        "type": "📝 Note",
                        "id": item[
                            "id"
                        ],
                        "title": item.get(
                            "title"
                        )
                        or "Untitled",
                        "preview": _clean_preview(
                            item.get(
                                "content"
                            ),
                            query,
                        ),
                    }
                )

    except Exception as error:
        print(
            "Global search notes error:",
            repr(error),
        )

    # ==================================================
    # STUDY MATERIALS
    # ==================================================

    try:
        result = (
            supabase
            .table(
                "study_materials"
            )
            .select(
                "id,title,extracted_text"
            )
            .eq(
                "user_id",
                int(user_id),
            )
            .order(
                "created_at",
                desc=True,
            )
            .limit(60)
            .execute()
        )

        for item in (
            result.data
            or []
        ):
            if _contains(
                query,
                item.get(
                    "title"
                ),
                item.get(
                    "extracted_text"
                ),
            ):
                matches.append(
                    {
                        "type": "📚 Material",
                        "id": item[
                            "id"
                        ],
                        "title": item.get(
                            "title"
                        )
                        or "Untitled",
                        "preview": _clean_preview(
                            item.get(
                                "extracted_text"
                            ),
                            query,
                        ),
                    }
                )

    except Exception as error:
        print(
            "Global search materials error:",
            repr(error),
        )

    # ==================================================
    # ASSIGNMENTS
    # ==================================================

    try:
        result = (
            supabase
            .table(
                "assignments"
            )
            .select(
                "id,title,description,status"
            )
            .eq(
                "user_id",
                int(user_id),
            )
            .order(
                "created_at",
                desc=True,
            )
            .limit(100)
            .execute()
        )

        for item in (
            result.data
            or []
        ):
            if _contains(
                query,
                item.get(
                    "title"
                ),
                item.get(
                    "description"
                ),
            ):
                matches.append(
                    {
                        "type": "📅 Assignment",
                        "id": item[
                            "id"
                        ],
                        "title": item.get(
                            "title"
                        )
                        or "Untitled",
                        "preview": (
                            f"Status: "
                            f"{item.get('status') or 'unknown'}"
                            + (
                                " | "
                                + _clean_preview(
                                    item.get(
                                        "description"
                                    ),
                                    query,
                                    radius=70,
                                )
                                if item.get(
                                    "description"
                                )
                                else ""
                            )
                        ),
                    }
                )

    except Exception as error:
        print(
            "Global search assignments error:",
            repr(error),
        )

    # ==================================================
    # EXAMS
    # ==================================================

    try:
        result = (
            supabase
            .table(
                "exams"
            )
            .select(
                "id,title,location,notes,exam_at"
            )
            .eq(
                "user_id",
                int(user_id),
            )
            .order(
                "exam_at"
            )
            .limit(100)
            .execute()
        )

        for item in (
            result.data
            or []
        ):
            if _contains(
                query,
                item.get(
                    "title"
                ),
                item.get(
                    "location"
                ),
                item.get(
                    "notes"
                ),
            ):
                matches.append(
                    {
                        "type": "📝 Exam",
                        "id": item[
                            "id"
                        ],
                        "title": item.get(
                            "title"
                        )
                        or "Untitled",
                        "preview": _clean_preview(
                            (
                                f"{item.get('location') or ''} "
                                f"{item.get('notes') or ''}"
                            ),
                            query,
                        ),
                    }
                )

    except Exception as error:
        print(
            "Global search exams error:",
            repr(error),
        )

    # ==================================================
    # GOALS
    # ==================================================

    try:
        result = (
            supabase
            .table(
                "study_goals"
            )
            .select(
                "id,title,description,status,target_date"
            )
            .eq(
                "user_id",
                int(user_id),
            )
            .order(
                "created_at",
                desc=True,
            )
            .limit(100)
            .execute()
        )

        for item in (
            result.data
            or []
        ):
            if _contains(
                query,
                item.get(
                    "title"
                ),
                item.get(
                    "description"
                ),
            ):
                matches.append(
                    {
                        "type": "🎯 Goal",
                        "id": item[
                            "id"
                        ],
                        "title": item.get(
                            "title"
                        )
                        or "Untitled",
                        "preview": (
                            f"Status: {item.get('status') or 'unknown'}"
                            + (
                                f" | Target: "
                                f"{item.get('target_date')}"
                                if item.get(
                                    "target_date"
                                )
                                else ""
                            )
                        ),
                    }
                )

    except Exception as error:
        print(
            "Global search goals error:",
            repr(error),
        )

    # ==================================================
    # VOICE NOTE TITLES + TRANSCRIPTS
    # ==================================================

    try:
        result = (
            supabase
            .table(
                "voice_notes"
            )
            .select(
                "id,title,transcript"
            )
            .eq(
                "user_id",
                int(user_id),
            )
            .order(
                "created_at",
                desc=True,
            )
            .limit(100)
            .execute()
        )

        for item in (
            result.data
            or []
        ):
            if _contains(
                query,
                item.get(
                    "title"
                ),
                item.get(
                    "transcript"
                ),
            ):
                matches.append(
                    {
                        "type": "🎙 Voice Note",
                        "id": item[
                            "id"
                        ],
                        "title": item.get(
                            "title"
                        )
                        or "Untitled",
                        "preview": _clean_preview(
                            item.get(
                                "transcript"
                            ),
                            query,
                        ),
                    }
                )

    except Exception as error:
        print(
            "Global search voice notes error:",
            repr(error),
        )

    # ==================================================
    # LANGUAGE VOCABULARY
    # ==================================================

    try:
        result = (
            supabase
            .table(
                "language_vocabulary"
            )
            .select(
                "id,language_name,term,meaning,example_text"
            )
            .eq(
                "user_id",
                int(user_id),
            )
            .order(
                "created_at",
                desc=True,
            )
            .limit(150)
            .execute()
        )

        for item in (
            result.data
            or []
        ):
            if _contains(
                query,
                item.get(
                    "term"
                ),
                item.get(
                    "meaning"
                ),
                item.get(
                    "example_text"
                ),
            ):
                matches.append(
                    {
                        "type": (
                            "🌍 "
                            + (
                                item.get(
                                    "language_name"
                                )
                                or "Vocabulary"
                            )
                        ),
                        "id": item[
                            "id"
                        ],
                        "title": item.get(
                            "term"
                        )
                        or "Vocabulary",
                        "preview": _clean_preview(
                            (
                                f"{item.get('meaning') or ''} "
                                f"{item.get('example_text') or ''}"
                            ),
                            query,
                        ),
                    }
                )

    except Exception as error:
        print(
            "Global search vocabulary error:",
            repr(error),
        )

    # ==================================================
    # FLASHCARDS
    # ==================================================

    try:
        result = (
            supabase
            .table(
                "flashcards"
            )
            .select(
                "id,question,answer,mastered"
            )
            .eq(
                "user_id",
                int(user_id),
            )
            .order(
                "created_at",
                desc=True,
            )
            .limit(150)
            .execute()
        )

        for item in (
            result.data
            or []
        ):
            if _contains(
                query,
                item.get(
                    "question"
                ),
                item.get(
                    "answer"
                ),
            ):
                matches.append(
                    {
                        "type": "🧠 Flashcard",
                        "id": item[
                            "id"
                        ],
                        "title": item.get(
                            "question"
                        )
                        or "Flashcard",
                        "preview": _clean_preview(
                            item.get(
                                "answer"
                            ),
                            query,
                        ),
                    }
                )

    except Exception as error:
        print(
            "Global search flashcards error:",
            repr(error),
        )

    return matches


def register_global_search_handlers(
    bot,
    show_main_menu,
):

    def show_search_menu(
        chat_id
    ):
        search_state.pop(
            chat_id,
            None,
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "🔎 Search Everything"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "🔎 Global Search\n\n"
                "Search across:\n"
                "• Notes\n"
                "• Study materials\n"
                "• Assignments\n"
                "• Exams\n"
                "• Study goals\n"
                "• Voice transcripts\n"
                "• Vocabulary\n"
                "• Flashcards"
            ),
            reply_markup=markup,
        )

    @bot.message_handler(
        commands=["search"]
    )
    def search_command(
        message
    ):
        show_search_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔎 Global Search"
    )
    def search_button(
        message
    ):
        show_search_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔎 Search Everything"
    )
    def start_search(
        message
    ):
        search_state[
            message.chat.id
        ] = {
            "step": "query"
        }

        bot.send_message(
            message.chat.id,
            (
                "🔎 Send a word or phrase.\n\n"
                "Example:\n"
                "phonetics"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.chat.id in search_state,
        content_types=["text"],
    )
    def search_state_handler(
        message
    ):
        chat_id = message.chat.id
        query = (
            message.text
            or ""
        ).strip()

        if query == "🏠 Main Menu":
            search_state.pop(
                chat_id,
                None,
            )

            show_main_menu(
                chat_id,
                message.from_user.first_name
                or "Friend",
            )
            return

        if (
            query.startswith("/")
            or query in GLOBAL_BUTTONS
        ):
            search_state.pop(
                chat_id,
                None,
            )
            return ContinueHandling()

        if len(query) < 2:
            bot.send_message(
                chat_id,
                "❌ Search term is too short.",
            )
            return

        status = bot.send_message(
            chat_id,
            "🔎 Searching your academic data..."
        )

        try:
            matches = search_user_data(
                message.from_user.id,
                query,
            )

            search_state.pop(
                chat_id,
                None,
            )

            try:
                bot.delete_message(
                    chat_id,
                    status.message_id,
                )
            except Exception:
                pass

            if not matches:
                bot.send_message(
                    chat_id,
                    (
                        f"🔎 No results for:\n"
                        f"{query}"
                    ),
                )

                show_search_menu(
                    chat_id
                )
                return

            parts = [
                (
                    f"🔎 RESULTS FOR: {query}\n"
                    f"Found: {len(matches)}"
                )
            ]

            for item in matches[
                :30
            ]:
                preview = (
                    item.get(
                        "preview"
                    )
                    or ""
                ).strip()

                preview_text = (
                    f"\n{preview}"
                    if preview
                    else ""
                )

                parts.append(
                    (
                        f"\n\n{item['type']} "
                        f"#{item['id']}\n"
                        f"{item['title']}"
                        f"{preview_text}"
                    )
                )

            if len(
                matches
            ) > 30:
                parts.append(
                    (
                        f"\n\n… and "
                        f"{len(matches) - 30} more results."
                    )
                )

            text = "".join(
                parts
            )

            for start in range(
                0,
                len(text),
                3800,
            ):
                bot.send_message(
                    chat_id,
                    text[
                        start:
                        start + 3800
                    ],
                )

            show_search_menu(
                chat_id
            )

        except Exception as error:
            print(
                "Global search error:",
                repr(error),
            )

            bot.send_message(
                chat_id,
                "❌ Search failed.",
            )
