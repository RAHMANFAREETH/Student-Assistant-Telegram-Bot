from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase


notification_state = {}


from navigation import GLOBAL_BUTTONS


DOW_NAMES = {
    0: "Sunday",
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
}


DOW_INPUT = {
    "sun": 0,
    "sunday": 0,
    "0": 0,

    "mon": 1,
    "monday": 1,
    "1": 1,

    "tue": 2,
    "tues": 2,
    "tuesday": 2,
    "2": 2,

    "wed": 3,
    "wednesday": 3,
    "3": 3,

    "thu": 4,
    "thur": 4,
    "thurs": 4,
    "thursday": 4,
    "4": 4,

    "fri": 5,
    "friday": 5,
    "5": 5,

    "sat": 6,
    "saturday": 6,
    "6": 6,
}


def get_notification_preferences(
    user_id,
):
    result = (
        supabase
        .table(
            "notification_preferences"
        )
        .select(
            "user_id,chat_id,timezone,"
            "daily_brief_enabled,daily_brief_hour,"
            "weekly_review_enabled,weekly_review_dow,"
            "weekly_review_hour,"
            "last_daily_brief_date,last_weekly_review_date"
        )
        .eq(
            "user_id",
            int(user_id),
        )
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def ensure_notification_preferences(
    user_id,
    chat_id,
):
    current = get_notification_preferences(
        user_id
    )

    if current:
        if int(
            current.get(
                "chat_id"
            )
            or 0
        ) != int(
            chat_id
        ):
            (
                supabase
                .table(
                    "notification_preferences"
                )
                .update(
                    {
                        "chat_id": int(
                            chat_id
                        )
                    }
                )
                .eq(
                    "user_id",
                    int(user_id),
                )
                .execute()
            )

            current[
                "chat_id"
            ] = int(
                chat_id
            )

        return current

    payload = {
        "user_id": int(
            user_id
        ),
        "chat_id": int(
            chat_id
        ),
        "timezone": "Asia/Colombo",
        "daily_brief_enabled": True,
        "daily_brief_hour": 7,
        "weekly_review_enabled": True,
        "weekly_review_dow": 0,
        "weekly_review_hour": 18,
    }

    result = (
        supabase
        .table(
            "notification_preferences"
        )
        .insert(
            payload
        )
        .execute()
    )

    return (
        result.data[0]
        if result.data
        else payload
    )


def update_notification_preferences(
    user_id,
    **changes,
):
    changes[
        "updated_at"
    ] = datetime.now().astimezone().isoformat()

    result = (
        supabase
        .table(
            "notification_preferences"
        )
        .update(
            changes
        )
        .eq(
            "user_id",
            int(user_id),
        )
        .execute()
    )

    return (
        result.data[0]
        if result.data
        else changes
    )


def hour_label(
    hour,
):
    hour = int(
        hour
    )

    suffix = (
        "AM"
        if hour < 12
        else "PM"
    )

    display = (
        hour % 12
    )

    if display == 0:
        display = 12

    return (
        f"{display:02d}:00 {suffix}"
    )


def format_settings(
    prefs,
):
    daily = (
        "✅ ON"
        if prefs.get(
            "daily_brief_enabled"
        )
        else "❌ OFF"
    )

    weekly = (
        "✅ ON"
        if prefs.get(
            "weekly_review_enabled"
        )
        else "❌ OFF"
    )

    dow = DOW_NAMES.get(
        int(
            prefs.get(
                "weekly_review_dow"
            )
            or 0
        ),
        "Sunday",
    )

    return (
        "🔔 SMART NOTIFICATION SETTINGS\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"🌍 Timezone: "
        f"{prefs.get('timezone') or 'Asia/Colombo'}\n\n"

        f"☀️ Daily Brief: {daily}\n"
        f"🕒 Brief Time: "
        f"{hour_label(prefs.get('daily_brief_hour') or 7)}\n\n"

        f"📅 Weekly Review: {weekly}\n"
        f"📆 Weekly Day: {dow}\n"
        f"🕒 Weekly Time: "
        f"{hour_label(prefs.get('weekly_review_hour') or 18)}"
    )


def register_notification_preference_handlers(
    bot,
    show_main_menu,
):

    def show_notification_menu(
        message,
    ):
        notification_state.pop(
            message.chat.id,
            None,
        )

        try:
            prefs = ensure_notification_preferences(
                message.from_user.id,
                message.chat.id,
            )

        except Exception as error:
            print(
                "Notification preferences load error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                (
                    "❌ Could not load notification settings.\n\n"
                    "Make sure V5.1 SQL was run in Supabase."
                ),
            )
            return

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "☀️ Toggle Daily Brief"
            ),
            types.KeyboardButton(
                "🕒 Set Brief Time"
            ),

            types.KeyboardButton(
                "📅 Toggle Weekly Review"
            ),
            types.KeyboardButton(
                "📆 Set Weekly Schedule"
            ),

            types.KeyboardButton(
                "🌍 Set Timezone"
            ),
            types.KeyboardButton(
                "⚙️ View Notification Settings"
            ),

            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            message.chat.id,
            format_settings(
                prefs
            ),
            reply_markup=markup,
        )

    @bot.message_handler(
        commands=["notifications"]
    )
    def notifications_command(
        message
    ):
        show_notification_menu(
            message
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔔 Smart Notifications"
    )
    def notifications_button(
        message
    ):
        show_notification_menu(
            message
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "⚙️ View Notification Settings"
    )
    def view_notification_settings(
        message
    ):
        show_notification_menu(
            message
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "☀️ Toggle Daily Brief"
    )
    def toggle_daily(
        message
    ):
        try:
            prefs = ensure_notification_preferences(
                message.from_user.id,
                message.chat.id,
            )

            new_value = not bool(
                prefs.get(
                    "daily_brief_enabled"
                )
            )

            update_notification_preferences(
                message.from_user.id,
                daily_brief_enabled=new_value,
            )

            bot.send_message(
                message.chat.id,
                (
                    "✅ Daily Brief "
                    + (
                        "enabled."
                        if new_value
                        else "disabled."
                    )
                ),
            )

            show_notification_menu(
                message
            )

        except Exception as error:
            print(
                "Toggle daily brief error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not update Daily Brief.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "📅 Toggle Weekly Review"
    )
    def toggle_weekly(
        message
    ):
        try:
            prefs = ensure_notification_preferences(
                message.from_user.id,
                message.chat.id,
            )

            new_value = not bool(
                prefs.get(
                    "weekly_review_enabled"
                )
            )

            update_notification_preferences(
                message.from_user.id,
                weekly_review_enabled=new_value,
            )

            bot.send_message(
                message.chat.id,
                (
                    "✅ Weekly Review "
                    + (
                        "enabled."
                        if new_value
                        else "disabled."
                    )
                ),
            )

            show_notification_menu(
                message
            )

        except Exception as error:
            print(
                "Toggle weekly review error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not update Weekly Review.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "🕒 Set Brief Time"
    )
    def set_brief_time(
        message
    ):
        ensure_notification_preferences(
            message.from_user.id,
            message.chat.id,
        )

        notification_state[
            message.chat.id
        ] = {
            "step": "daily_hour"
        }

        bot.send_message(
            message.chat.id,
            (
                "🕒 Send the Daily Brief hour "
                "using 24-hour time.\n\n"
                "Examples:\n"
                "7\n"
                "07\n"
                "14\n\n"
                "The brief is sent once during that hour."
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📆 Set Weekly Schedule"
    )
    def set_weekly_schedule(
        message
    ):
        ensure_notification_preferences(
            message.from_user.id,
            message.chat.id,
        )

        notification_state[
            message.chat.id
        ] = {
            "step": "weekly_day"
        }

        bot.send_message(
            message.chat.id,
            (
                "📆 Send the day for Weekly Review.\n\n"
                "Examples:\n"
                "Sunday\n"
                "Friday\n"
                "Mon"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🌍 Set Timezone"
    )
    def set_timezone_button(
        message
    ):
        ensure_notification_preferences(
            message.from_user.id,
            message.chat.id,
        )

        notification_state[
            message.chat.id
        ] = {
            "step": "timezone"
        }

        bot.send_message(
            message.chat.id,
            (
                "🌍 Send an IANA timezone name.\n\n"
                "Examples:\n"
                "Asia/Colombo\n"
                "Asia/Dubai\n"
                "Europe/London\n"
                "America/New_York"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.chat.id in notification_state,
        content_types=["text"],
    )
    def notification_state_handler(
        message
    ):
        chat_id = message.chat.id
        text = (
            message.text
            or ""
        ).strip()

        if text == "🏠 Main Menu":
            notification_state.pop(
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
            text.startswith("/")
            or text in GLOBAL_BUTTONS
        ):
            notification_state.pop(
                chat_id,
                None,
            )
            return ContinueHandling()

        state = notification_state.get(
            chat_id,
            {}
        )

        step = state.get(
            "step"
        )

        if step == "daily_hour":
            try:
                hour = int(
                    text
                )

            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Enter an hour from 0 to 23.",
                )
                return

            if not 0 <= hour <= 23:
                bot.send_message(
                    chat_id,
                    "❌ Hour must be between 0 and 23.",
                )
                return

            update_notification_preferences(
                message.from_user.id,
                daily_brief_hour=hour,
                last_daily_brief_date=None,
            )

            notification_state.pop(
                chat_id,
                None,
            )

            bot.send_message(
                chat_id,
                (
                    "✅ Daily Brief time updated to "
                    f"{hour_label(hour)}."
                ),
            )

            show_notification_menu(
                message
            )
            return

        if step == "weekly_day":
            day = DOW_INPUT.get(
                text.casefold()
            )

            if day is None:
                bot.send_message(
                    chat_id,
                    (
                        "❌ Invalid day.\n"
                        "Example: Sunday"
                    ),
                )
                return

            state[
                "weekly_dow"
            ] = day

            state[
                "step"
            ] = "weekly_hour"

            bot.send_message(
                chat_id,
                (
                    "🕒 Now send the Weekly Review hour "
                    "from 0 to 23.\n\n"
                    "Example: 18"
                ),
            )
            return

        if step == "weekly_hour":
            try:
                hour = int(
                    text
                )

            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Enter an hour from 0 to 23.",
                )
                return

            if not 0 <= hour <= 23:
                bot.send_message(
                    chat_id,
                    "❌ Hour must be between 0 and 23.",
                )
                return

            update_notification_preferences(
                message.from_user.id,
                weekly_review_dow=state[
                    "weekly_dow"
                ],
                weekly_review_hour=hour,
                last_weekly_review_date=None,
            )

            day_name = DOW_NAMES[
                state[
                    "weekly_dow"
                ]
            ]

            notification_state.pop(
                chat_id,
                None,
            )

            bot.send_message(
                chat_id,
                (
                    "✅ Weekly Review schedule updated.\n\n"
                    f"📆 {day_name}\n"
                    f"🕒 {hour_label(hour)}"
                ),
            )

            show_notification_menu(
                message
            )
            return

        if step == "timezone":
            try:
                ZoneInfo(
                    text
                )

            except ZoneInfoNotFoundError:
                bot.send_message(
                    chat_id,
                    (
                        "❌ Unknown timezone.\n\n"
                        "Use an IANA name such as:\n"
                        "Asia/Colombo"
                    ),
                )
                return

            update_notification_preferences(
                message.from_user.id,
                timezone=text,
                last_daily_brief_date=None,
                last_weekly_review_date=None,
            )

            notification_state.pop(
                chat_id,
                None,
            )

            bot.send_message(
                chat_id,
                (
                    "✅ Timezone updated.\n\n"
                    f"🌍 {text}"
                ),
            )

            show_notification_menu(
                message
            )
            return
