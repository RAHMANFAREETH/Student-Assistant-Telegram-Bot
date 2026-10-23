from telebot import types

from db import supabase


def _count(
    table,
    user_id,
    **filters,
):
    try:
        query = (
            supabase
            .table(table)
            .select("id")
            .eq("user_id", int(user_id))
        )

        for key, value in filters.items():
            query = query.eq(
                key,
                value,
            )

        result = query.execute()

        return len(
            result.data or []
        )

    except Exception as error:
        print(
            f"Progress count error ({table}):",
            repr(error),
        )
        return 0


def _quiz_stats(user_id):
    try:
        result = (
            supabase
            .table("quiz_attempts")
            .select(
                "score_percent,correct_answers,total_questions"
            )
            .eq(
                "user_id",
                int(user_id),
            )
            .order(
                "created_at",
                desc=True,
            )
            .limit(50)
            .execute()
        )

        rows = result.data or []

        if not rows:
            return {
                "attempts": 0,
                "average": 0,
                "best": 0,
            }

        scores = [
            float(
                row.get(
                    "score_percent"
                )
                or 0
            )
            for row in rows
        ]

        return {
            "attempts": len(rows),
            "average": round(
                sum(scores)
                / len(scores),
                1,
            ),
            "best": round(
                max(scores),
                1,
            ),
        }

    except Exception as error:
        print(
            "Progress quiz stats error:",
            repr(error),
        )

        return {
            "attempts": 0,
            "average": 0,
            "best": 0,
        }


def build_progress(user_id):
    total_cards = _count(
        "flashcards",
        user_id,
    )

    mastered_cards = _count(
        "flashcards",
        user_id,
        mastered=True,
    )

    learning_cards = max(
        total_cards
        - mastered_cards,
        0,
    )

    if total_cards:
        mastery_percent = round(
            mastered_cards
            / total_cards
            * 100
        )
    else:
        mastery_percent = 0

    quiz = _quiz_stats(
        user_id
    )

    completed_assignments = _count(
        "assignments",
        user_id,
        status="completed",
    )

    pending_assignments = _count(
        "assignments",
        user_id,
        status="pending",
    )

    return (
        "📈 STUDY PROGRESS\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "🧠 FLASHCARDS\n"
        f"📚 Total: {total_cards}\n"
        f"⭐ Mastered: {mastered_cards}\n"
        f"📖 Learning: {learning_cards}\n"
        f"📈 Mastery: {mastery_percent}%\n\n"

        "❓ QUIZZES\n"
        f"🧪 Attempts: {quiz['attempts']}\n"
        f"📊 Average: {quiz['average']}%\n"
        f"🏆 Best: {quiz['best']}%\n\n"

        "📅 ASSIGNMENTS\n"
        f"✅ Completed: {completed_assignments}\n"
        f"📌 Pending: {pending_assignments}"
    )


def register_progress_handlers(
    bot,
    show_main_menu,
):

    def send_progress(message):
        try:
            text = build_progress(
                message.from_user.id
            )

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
                row_width=2,
            )

            markup.add(
                types.KeyboardButton(
                    "🧠 Flashcards"
                ),
                types.KeyboardButton(
                    "❓ Quiz"
                ),
                types.KeyboardButton(
                    "📊 Dashboard"
                ),
                types.KeyboardButton(
                    "🔄 Refresh Progress"
                ),
                types.KeyboardButton(
                    "🏠 Main Menu"
                ),
            )

            bot.send_message(
                message.chat.id,
                text,
                reply_markup=markup,
            )

        except Exception as error:
            print(
                "Progress error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not load study progress.",
            )

    @bot.message_handler(
        commands=["progress"]
    )
    def progress_command(
        message
    ):
        send_progress(
            message
        )

    @bot.message_handler(
        func=lambda m:
        m.text in {
            "📈 Progress",
            "🔄 Refresh Progress",
        }
    )
    def progress_button(
        message
    ):
        send_progress(
            message
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🏠 Main Menu"
    )
    def progress_main_menu(
        message
    ):
        show_main_menu(
            message.chat.id,
            message.from_user.first_name
            or "Friend",
        )
