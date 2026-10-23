import random

from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase
from subjects import (
    get_subjects,
    get_subject_by_id,
    subject_display,
)
from flashcards import get_flashcards


quiz_state = {}


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


def save_quiz_attempt(
    user_id,
    subject_id,
    total_questions,
    correct_answers,
):
    wrong_answers = (
        total_questions
        - correct_answers
    )

    score_percent = round(
        (
            correct_answers
            / total_questions
            * 100
        ),
        2,
    )

    (
        supabase
        .table("quiz_attempts")
        .insert(
            {
                "user_id": int(user_id),
                "subject_id": subject_id,
                "total_questions": total_questions,
                "correct_answers": correct_answers,
                "wrong_answers": wrong_answers,
                "score_percent": score_percent,
            }
        )
        .execute()
    )

    return score_percent


def register_quiz_handlers(
    bot,
    show_main_menu,
):

    def show_quiz_menu(
        chat_id
    ):
        quiz_state.pop(
            chat_id,
            None,
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "▶️ Start Quiz"
            ),
            types.KeyboardButton(
                "📊 Quiz History"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "❓ Quiz Engine\n\n"
                "Quizzes are created from your "
                "saved flashcards.\n\n"
                "You need at least 4 flashcards "
                "in a subject for MCQ mode."
            ),
            reply_markup=markup,
        )

    def parse_subject_button(
        text
    ):
        if not text.startswith(
            "📚 #"
        ):
            return None

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
            return None

    def send_next_question(
        chat_id,
        user_id,
    ):
        state = quiz_state.get(
            user_id
        )

        if not state:
            bot.send_message(
                chat_id,
                "❌ Quiz session expired.",
            )
            return

        index = state[
            "current_index"
        ]

        questions = state[
            "questions"
        ]

        if index >= len(questions):
            correct = state[
                "correct"
            ]

            total = len(
                questions
            )

            try:
                score = save_quiz_attempt(
                    user_id=user_id,
                    subject_id=state[
                        "subject_id"
                    ],
                    total_questions=total,
                    correct_answers=correct,
                )
            except Exception as error:
                print(
                    "Save quiz attempt error:",
                    repr(error),
                )

                score = round(
                    correct
                    / total
                    * 100,
                    2,
                )

            quiz_state.pop(
                user_id,
                None,
            )

            if score >= 80:
                result_text = (
                    "🌟 Excellent work!"
                )
            elif score >= 60:
                result_text = (
                    "👍 Good job!"
                )
            else:
                result_text = (
                    "📚 Keep practicing."
                )

            bot.send_message(
                chat_id,
                (
                    "🏁 QUIZ COMPLETE\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    f"✅ Correct: {correct}/{total}\n"
                    f"❌ Wrong: {total - correct}/{total}\n"
                    f"📊 Score: {score}%\n\n"
                    f"{result_text}"
                ),
            )
            return

        item = questions[
            index
        ]

        correct_answer = item[
            "answer"
        ]

        all_cards = state[
            "all_cards"
        ]

        distractor_pool = list(
            {
                card["answer"]
                for card in all_cards
                if card["answer"]
                != correct_answer
            }
        )

        random.shuffle(
            distractor_pool
        )

        distractors = distractor_pool[
            :3
        ]

        if len(distractors) < 3:
            bot.send_message(
                chat_id,
                (
                    "❌ Not enough different answers "
                    "to create this quiz."
                ),
            )

            quiz_state.pop(
                user_id,
                None,
            )
            return

        options = [
            correct_answer,
            *distractors,
        ]

        random.shuffle(
            options
        )

        state[
            "current_options"
        ] = options

        state[
            "correct_option_index"
        ] = options.index(
            correct_answer
        )

        markup = types.InlineKeyboardMarkup(
            row_width=1
        )

        for option_index, option in enumerate(
            options
        ):
            # Keep button text manageable.
            display = (
                option
                if len(option) <= 80
                else option[:77] + "..."
            )

            markup.add(
                types.InlineKeyboardButton(
                    display,
                    callback_data=(
                        f"quiz_answer:"
                        f"{option_index}"
                    ),
                )
            )

        bot.send_message(
            chat_id,
            (
                f"❓ Question {index + 1}/{len(questions)}\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"{item['question']}"
            ),
            reply_markup=markup,
        )

    @bot.message_handler(
        commands=["quiz"]
    )
    def quiz_command(
        message
    ):
        show_quiz_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "❓ Quiz"
    )
    def quiz_button(
        message
    ):
        show_quiz_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "▶️ Start Quiz"
    )
    def start_quiz_button(
        message
    ):
        subjects = get_subjects(
            message.from_user.id
        )

        if not subjects:
            bot.send_message(
                message.chat.id,
                (
                    "📚 Add a subject and flashcards first."
                ),
            )
            return

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=1,
        )

        valid_subjects = []

        for subject in subjects:
            cards = get_flashcards(
                message.from_user.id,
                subject_id=subject[
                    "id"
                ],
                limit=100,
            )

            # Need four distinct answers for a 4-option MCQ.
            distinct_answers = {
                card["answer"]
                for card in cards
            }

            if (
                len(cards) >= 4
                and len(distinct_answers) >= 4
            ):
                valid_subjects.append(
                    subject
                )

                markup.add(
                    types.KeyboardButton(
                        (
                            f"📚 #{subject['id']} "
                            f"{subject_display(subject)}"
                        )
                    )
                )

        if not valid_subjects:
            bot.send_message(
                message.chat.id,
                (
                    "❌ No subject has enough flashcards yet.\n\n"
                    "Add at least 4 flashcards with different answers "
                    "to one subject."
                ),
            )
            return

        markup.add(
            types.KeyboardButton(
                "🔙 Quiz Menu"
            )
        )

        quiz_state[
            message.from_user.id
        ] = {
            "step": "choose_subject",
            "chat_id": message.chat.id,
        }

        bot.send_message(
            message.chat.id,
            "📚 Choose a subject for the quiz:",
            reply_markup=markup,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📊 Quiz History"
    )
    def quiz_history(
        message
    ):
        try:
            result = (
                supabase
                .table("quiz_attempts")
                .select(
                    "id,subject_id,total_questions,"
                    "correct_answers,wrong_answers,"
                    "score_percent,created_at"
                )
                .eq(
                    "user_id",
                    int(message.from_user.id),
                )
                .order(
                    "created_at",
                    desc=True,
                )
                .limit(10)
                .execute()
            )

            rows = result.data or []

            if not rows:
                bot.send_message(
                    message.chat.id,
                    "📊 No quiz attempts yet.",
                )
                return

            parts = [
                "📊 Recent Quiz History\n"
            ]

            for row in rows:
                subject = get_subject_by_id(
                    message.from_user.id,
                    row.get(
                        "subject_id"
                    ),
                )

                subject_name = (
                    subject_display(subject)
                    if subject
                    else "No Subject"
                )

                parts.append(
                    (
                        f"\n📚 {subject_name}\n"
                        f"✅ {row['correct_answers']}/"
                        f"{row['total_questions']}\n"
                        f"📊 {row['score_percent']}%\n"
                    )
                )

            bot.send_message(
                message.chat.id,
                "\n".join(parts),
            )

        except Exception as error:
            print(
                "Quiz history error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not load quiz history.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔙 Quiz Menu"
    )
    def back_quiz_menu(
        message
    ):
        quiz_state.pop(
            message.from_user.id,
            None,
        )

        show_quiz_menu(
            message.chat.id
        )

    @bot.callback_query_handler(
        func=lambda call:
        bool(call.data)
        and call.data.startswith(
            "quiz_answer:"
        )
    )
    def answer_callback(
        call
    ):
        state = quiz_state.get(
            call.from_user.id
        )

        if not state:
            bot.answer_callback_query(
                call.id,
                "Quiz session expired."
            )
            return

        try:
            option_index = int(
                call.data.split(
                    ":",
                    1,
                )[1]
            )

            correct_index = state[
                "correct_option_index"
            ]

            item = state[
                "questions"
            ][
                state[
                    "current_index"
                ]
            ]

            if option_index == correct_index:
                state["correct"] += 1

                bot.answer_callback_query(
                    call.id,
                    "✅ Correct!"
                )

                feedback = (
                    "✅ Correct!"
                )

            else:
                bot.answer_callback_query(
                    call.id,
                    "❌ Wrong"
                )

                feedback = (
                    "❌ Wrong\n\n"
                    f"Correct answer:\n"
                    f"{item['answer']}"
                )

            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=None,
            )

            bot.send_message(
                call.message.chat.id,
                feedback,
            )

            state[
                "current_index"
            ] += 1

            send_next_question(
                call.message.chat.id,
                call.from_user.id,
            )

        except Exception as error:
            print(
                "Quiz answer error:",
                repr(error),
            )

            bot.answer_callback_query(
                call.id,
                "Could not process answer."
            )

    @bot.message_handler(
        func=lambda m:
        m.from_user.id in quiz_state,
        content_types=["text"],
    )
    def quiz_state_handler(
        message
    ):
        text = (
            message.text
            or ""
        ).strip()

        user_id = (
            message.from_user.id
        )

        state = quiz_state.get(
            user_id,
            {}
        )

        if text == "🏠 Main Menu":
            quiz_state.pop(
                user_id,
                None,
            )

            show_main_menu(
                message.chat.id,
                message.from_user.first_name
                or "Friend",
            )
            return

        if text == "🔙 Quiz Menu":
            quiz_state.pop(
                user_id,
                None,
            )

            show_quiz_menu(
                message.chat.id
            )
            return

        if (
            text.startswith("/")
            or text in GLOBAL_BUTTONS
        ):
            quiz_state.pop(
                user_id,
                None,
            )
            return ContinueHandling()

        if state.get(
            "step"
        ) == "choose_subject":
            subject_id = parse_subject_button(
                text
            )

            if not subject_id:
                bot.send_message(
                    message.chat.id,
                    "❌ Choose a subject using the buttons.",
                )
                return

            subject = get_subject_by_id(
                user_id,
                subject_id,
            )

            if not subject:
                bot.send_message(
                    message.chat.id,
                    "❌ Subject not found.",
                )
                return

            cards = get_flashcards(
                user_id,
                subject_id=subject_id,
                limit=100,
            )

            distinct_answers = {
                card["answer"]
                for card in cards
            }

            if (
                len(cards) < 4
                or len(distinct_answers) < 4
            ):
                bot.send_message(
                    message.chat.id,
                    (
                        "❌ This subject needs at least "
                        "4 flashcards with different answers."
                    ),
                )
                return

            quiz_length = min(
                5,
                len(cards),
            )

            questions = random.sample(
                cards,
                quiz_length,
            )

            quiz_state[
                user_id
            ] = {
                "step": "running",
                "chat_id": message.chat.id,
                "subject_id": subject_id,
                "all_cards": cards,
                "questions": questions,
                "current_index": 0,
                "correct": 0,
            }

            bot.send_message(
                message.chat.id,
                (
                    "▶️ Quiz started!\n\n"
                    f"📚 {subject_display(subject)}\n"
                    f"❓ Questions: {quiz_length}"
                ),
                reply_markup=types.ReplyKeyboardRemove(),
            )

            send_next_question(
                message.chat.id,
                user_id,
            )
            return
