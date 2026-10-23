from telebot import types


COURSES_URL = "https://t.me/tamil_courses_foryou"
PAST_PAPERS_URL = "https://t.me/PastpaperTamilmediumALOL"
ADMIN_URL = "https://t.me/Bestfriendlanka"


def build_resources_keyboard():
    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

    markup.add(
        types.InlineKeyboardButton(
            "📚 Tamil Medium Courses",
            url=COURSES_URL,
        ),
        types.InlineKeyboardButton(
            "📄 A/L O/L Past Papers",
            url=PAST_PAPERS_URL,
        ),
        types.InlineKeyboardButton(
            "👤 Contact Admin",
            url=ADMIN_URL,
        ),
    )

    return markup


def register_student_resource_handlers(
    bot,
    show_main_menu,
):

    def send_resources(
        chat_id
    ):
        bot.send_message(
            chat_id,
            (
                "📢 STUDENT RESOURCES\n"
                "━━━━━━━━━━━━━━━━━━\n\n"

                "Useful Tamil-medium student resources:\n\n"

                "📚 Tamil Medium Courses\n"
                "Join the courses group for learning resources "
                "and course-related content.\n\n"

                "📄 A/L & O/L Past Papers\n"
                "Open the past-paper group for Tamil-medium "
                "A/L and O/L exam resources.\n\n"

                "👤 Contact Admin\n"
                "Contact the bot administrator directly on Telegram.\n\n"

                "Tap a button below to open the resource."
            ),
            reply_markup=build_resources_keyboard(),
        )

    @bot.message_handler(
        commands=["resources"]
    )
    def resources_command(
        message
    ):
        send_resources(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📢 Student Resources"
    )
    def resources_button(
        message
    ):
        send_resources(
            message.chat.id
        )
