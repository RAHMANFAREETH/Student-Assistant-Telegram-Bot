import random

from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase
from subjects import (
    get_subjects,
    get_subject_by_id,
    subject_display,
)


flashcard_state = {}


GLOBAL_BUTTONS = {
    "📄 PDF Tools",
    "📝 Notes",
    "🌐 Translate",
    "⏰ Study Reminder",
    "📚 Subjects",
    "📅 Assignments",
    "📊 Dashboard",
    "🧠 Flashcards",
    "❓ Quiz",
    "📈 Progress",
    "ℹ️ Help",
}


def get_flashcards(
    user_id,
    subject_id=None,
    limit=100,
):
    query = (
        supabase
        .table("flashcards")
        .select(
            "id,user_id,subject_id,question,answer,"
            "times_seen,correct_count,wrong_count,mastered,created_at"
        )
        .eq("user_id", int(user_id))
    )

    if subject_id is not None:
        query = query.eq(
            "subject_id",
            int(subject_id),
        )

    result = (
        query
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return result.data or []


def get_flashcard(
    user_id,
    flashcard_id,
):
    result = (
        supabase
        .table("flashcards")
        .select(
            "id,user_id,subject_id,question,answer,"
            "times_seen,correct_count,wrong_count,mastered"
        )
        .eq("user_id", int(user_id))
        .eq("id", int(flashcard_id))
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def create_flashcard(
    user_id,
    subject_id,
    question,
    answer,
):
    payload = {
        "user_id": int(user_id),
        "subject_id": subject_id,
        "question": question.strip(),
        "answer": answer.strip(),
    }

    return (
        supabase
        .table("flashcards")
        .insert(payload)
        .execute()
    )


def delete_flashcard(
    user_id,
    flashcard_id,
):
    card = get_flashcard(
        user_id,
        flashcard_id,
    )

    if not card:
        return False

    (
        supabase
        .table("flashcards")
        .delete()
        .eq("user_id", int(user_id))
        .eq("id", int(flashcard_id))
        .execute()
    )

    return True


def update_flashcard_review(
    user_id,
    flashcard_id,
    knew_answer,
):
    card = get_flashcard(
        user_id,
        flashcard_id,
    )

    if not card:
        return False

    times_seen = int(
        card.get("times_seen") or 0
    ) + 1

    correct_count = int(
        card.get("correct_count") or 0
    )

    wrong_count = int(
        card.get("wrong_count") or 0
    )

    if knew_answer:
        correct_count += 1
    else:
        wrong_count += 1

    # Simple mastery rule:
    # at least 3 correct reviews and
    # correct answers are at least double wrong answers.
    mastered = (
        correct_count >= 3
        and correct_count >= (
            wrong_count * 2
        )
    )

    (
        supabase
        .table("flashcards")
        .update(
            {
                "times_seen": times_seen,
                "correct_count": correct_count,
                "wrong_count": wrong_count,
                "mastered": mastered,
            }
        )
        .eq("user_id", int(user_id))
        .eq("id", int(flashcard_id))
        .execute()
    )

    return True


def subject_label(
    user_id,
    subject_id,
):
    if not subject_id:
        return "No Subject"

    subject = get_subject_by_id(
        user_id,
        subject_id,
    )

    if not subject:
        return "No Subject"

    return subject_display(
        subject
    )


def register_flashcard_handlers(
    bot,
    show_main_menu,
):

    def show_flashcard_menu(
        chat_id
    ):
        flashcard_state.pop(
            chat_id,
            None,
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "➕ Add Flashcard"
            ),
            types.KeyboardButton(
                "📚 My Flashcards"
            ),
            types.KeyboardButton(
                "🎯 Study Flashcards"
            ),
            types.KeyboardButton(
                "🗑 Delete Flashcard"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "🧠 Flashcards\n\n"
                "Create cards by subject and "
                "review them until they are mastered."
            ),
            reply_markup=markup,
        )

    def choose_subject_for_action(
        message,
        next_step,
        prompt,
        allow_no_subject=False,
    ):
        subjects = get_subjects(
            message.from_user.id
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=1,
        )

        if allow_no_subject:
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
                "🔙 Flashcards Menu"
            )
        )

        flashcard_state[
            message.chat.id
        ] = {
            "step": next_step
        }

        if not subjects and not allow_no_subject:
            bot.send_message(
                message.chat.id,
                (
                    "📚 You need at least one subject first.\n\n"
                    "Open 📚 Subjects and add a subject."
                ),
            )
            return

        bot.send_message(
            message.chat.id,
            prompt,
            reply_markup=markup,
        )

    def parse_subject_button(
        text
    ):
        if text == "⏭ No Subject":
            return None

        if not text.startswith(
            "📚 #"
        ):
            return "invalid"

        try:
            token = text.split(
                " ",
                2,
            )[1]

            return int(
                token.replace(
                    "#",
                    ""
                )
            )

        except Exception:
            return "invalid"

    def send_random_card(
        message,
        subject_id,
    ):
        cards = get_flashcards(
            message.from_user.id,
            subject_id=subject_id,
            limit=100,
        )

        if not cards:
            bot.send_message(
                message.chat.id,
                (
                    "🧠 No flashcards found "
                    "for this subject."
                ),
            )
            show_flashcard_menu(
                message.chat.id
            )
            return

        # Prefer not-yet-mastered cards.
        unmastered = [
            card
            for card in cards
            if not card.get(
                "mastered"
            )
        ]

        pool = (
            unmastered
            if unmastered
            else cards
        )

        card = random.choice(
            pool
        )

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "👀 Show Answer",
                callback_data=(
                    f"fc_show:{card['id']}"
                ),
            )
        )

        bot.send_message(
            message.chat.id,
            (
                "🧠 FLASHCARD\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"❓ {card['question']}\n\n"
                "Think of the answer, then press "
                "👀 Show Answer."
            ),
            reply_markup=markup,
        )

    @bot.message_handler(
        commands=["flashcards"]
    )
    def flashcards_command(
        message
    ):
        show_flashcard_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🧠 Flashcards"
    )
    def flashcards_button(
        message
    ):
        show_flashcard_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "➕ Add Flashcard"
    )
    def add_flashcard_button(
        message
    ):
        choose_subject_for_action(
            message,
            next_step="add_subject",
            prompt=(
                "📚 Choose the subject for "
                "this flashcard."
            ),
            allow_no_subject=True,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📚 My Flashcards"
    )
    def my_flashcards_button(
        message
    ):
        cards = get_flashcards(
            message.from_user.id,
            limit=30,
        )

        if not cards:
            bot.send_message(
                message.chat.id,
                (
                    "🧠 You have no flashcards yet.\n\n"
                    "Choose ➕ Add Flashcard."
                ),
            )
            return

        parts = [
            "📚 My Flashcards\n"
        ]

        for card in cards:
            status = (
                "⭐ Mastered"
                if card.get("mastered")
                else "📖 Learning"
            )

            parts.append(
                (
                    f"\n#{card['id']} {status}\n"
                    f"📚 {subject_label(message.from_user.id, card.get('subject_id'))}\n"
                    f"❓ {card['question']}\n"
                    f"✅ {card['answer']}\n"
                )
            )

        text = "\n".join(
            parts
        )

        # Keep messages under Telegram's limit.
        for start in range(
            0,
            len(text),
            3800,
        ):
            bot.send_message(
                message.chat.id,
                text[
                    start:
                    start + 3800
                ],
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "🎯 Study Flashcards"
    )
    def study_flashcards_button(
        message
    ):
        choose_subject_for_action(
            message,
            next_step="study_subject",
            prompt=(
                "🎯 Choose the subject "
                "you want to study."
            ),
            allow_no_subject=False,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🗑 Delete Flashcard"
    )
    def delete_flashcard_button(
        message
    ):
        flashcard_state[
            message.chat.id
        ] = {
            "step": "delete"
        }

        bot.send_message(
            message.chat.id,
            (
                "🗑 Delete Flashcard\n\n"
                "Send the flashcard number.\n"
                "Example: 7"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔙 Flashcards Menu"
    )
    def back_flashcards(
        message
    ):
        show_flashcard_menu(
            message.chat.id
        )

    @bot.callback_query_handler(
        func=lambda call:
        bool(call.data)
        and call.data.startswith(
            "fc_show:"
        )
    )
    def show_answer_callback(
        call
    ):
        try:
            flashcard_id = int(
                call.data.split(
                    ":",
                    1,
                )[1]
            )

            card = get_flashcard(
                call.from_user.id,
                flashcard_id,
            )

            if not card:
                bot.answer_callback_query(
                    call.id,
                    "Flashcard not found."
                )
                return

            markup = types.InlineKeyboardMarkup(
                row_width=2
            )

            markup.add(
                types.InlineKeyboardButton(
                    "✅ I knew it",
                    callback_data=(
                        f"fc_rate:{flashcard_id}:1"
                    ),
                ),
                types.InlineKeyboardButton(
                    "🔁 Practice again",
                    callback_data=(
                        f"fc_rate:{flashcard_id}:0"
                    ),
                ),
            )

            bot.edit_message_text(
                (
                    "🧠 FLASHCARD\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    f"❓ {card['question']}\n\n"
                    f"✅ {card['answer']}"
                ),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
            )

            bot.answer_callback_query(
                call.id
            )

        except Exception as error:
            print(
                "Show flashcard answer error:",
                repr(error),
            )

            bot.answer_callback_query(
                call.id,
                "Could not open flashcard."
            )

    @bot.callback_query_handler(
        func=lambda call:
        bool(call.data)
        and call.data.startswith(
            "fc_rate:"
        )
    )
    def rate_flashcard_callback(
        call
    ):
        try:
            _, flashcard_id, knew = (
                call.data.split(
                    ":"
                )
            )

            flashcard_id = int(
                flashcard_id
            )

            knew_answer = (
                knew == "1"
            )

            update_flashcard_review(
                call.from_user.id,
                flashcard_id,
                knew_answer,
            )

            bot.answer_callback_query(
                call.id,
                (
                    "✅ Progress saved"
                    if knew_answer
                    else "🔁 Added to practice"
                ),
            )

            card = get_flashcard(
                call.from_user.id,
                flashcard_id,
            )

            subject_id = (
                card.get("subject_id")
                if card
                else None
            )

            # Use a lightweight pseudo-message object:
            class StudyMessage:
                pass

            pseudo = StudyMessage()
            pseudo.chat = call.message.chat
            pseudo.from_user = call.from_user

            send_random_card(
                pseudo,
                subject_id,
            )

        except Exception as error:
            print(
                "Rate flashcard error:",
                repr(error),
            )

            bot.answer_callback_query(
                call.id,
                "Could not save progress."
            )

    @bot.message_handler(
        func=lambda m:
        m.chat.id in flashcard_state,
        content_types=["text"],
    )
    def flashcard_state_handler(
        message
    ):
        chat_id = message.chat.id
        text = (
            message.text
            or ""
        ).strip()

        if text == "🏠 Main Menu":
            flashcard_state.pop(
                chat_id,
                None,
            )

            show_main_menu(
                chat_id,
                message.from_user.first_name
                or "Friend",
            )
            return

        if text == "🔙 Flashcards Menu":
            show_flashcard_menu(
                chat_id
            )
            return

        if (
            text.startswith("/")
            or text in GLOBAL_BUTTONS
        ):
            flashcard_state.pop(
                chat_id,
                None,
            )
            return ContinueHandling()

        state = flashcard_state.get(
            chat_id,
            {}
        )

        step = state.get(
            "step"
        )

        if step in {
            "add_subject",
            "study_subject",
        }:
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

            if step == "study_subject":
                flashcard_state.pop(
                    chat_id,
                    None,
                )

                send_random_card(
                    message,
                    subject_id,
                )
                return

            state["subject_id"] = (
                subject_id
            )
            state["step"] = "question"

            bot.send_message(
                chat_id,
                (
                    "❓ Send the question/front "
                    "of the flashcard."
                ),
            )
            return

        if step == "question":
            if len(text) < 1:
                bot.send_message(
                    chat_id,
                    "❌ Question cannot be empty.",
                )
                return

            if len(text) > 1500:
                bot.send_message(
                    chat_id,
                    "❌ Question is too long.",
                )
                return

            state["question"] = text
            state["step"] = "answer"

            bot.send_message(
                chat_id,
                (
                    "✅ Now send the answer/back "
                    "of the flashcard."
                ),
            )
            return

        if step == "answer":
            if len(text) < 1:
                bot.send_message(
                    chat_id,
                    "❌ Answer cannot be empty.",
                )
                return

            if len(text) > 2500:
                bot.send_message(
                    chat_id,
                    "❌ Answer is too long.",
                )
                return

            try:
                create_flashcard(
                    user_id=message.from_user.id,
                    subject_id=state.get(
                        "subject_id"
                    ),
                    question=state[
                        "question"
                    ],
                    answer=text,
                )

                flashcard_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    "✅ Flashcard saved!",
                )

                show_flashcard_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Create flashcard error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not save flashcard.",
                )

            return

        if step == "delete":
            try:
                flashcard_id = int(
                    text.replace(
                        "#",
                        ""
                    )
                )
            except ValueError:
                bot.send_message(
                    chat_id,
                    (
                        "❌ Send only the flashcard number.\n"
                        "Example: 7"
                    ),
                )
                return

            try:
                success = delete_flashcard(
                    message.from_user.id,
                    flashcard_id,
                )

                if not success:
                    bot.send_message(
                        chat_id,
                        "❌ Flashcard not found.",
                    )
                    return

                flashcard_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    "✅ Flashcard deleted.",
                )

                show_flashcard_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Delete flashcard error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not delete flashcard.",
                )

            return
