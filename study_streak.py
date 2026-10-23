from datetime import datetime, timedelta, time as dt_time, timezone
from zoneinfo import ZoneInfo

from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase
from study_preferences import (
    get_study_preferences,
    set_daily_target,
)


SRI_LANKA_TZ = ZoneInfo("Asia/Colombo")
streak_state = {}


from navigation import GLOBAL_BUTTONS


def _utc_iso(
    local_dt,
):
    if local_dt.tzinfo is None:
        local_dt = local_dt.replace(
            tzinfo=SRI_LANKA_TZ
        )

    return (
        local_dt
        .astimezone(timezone.utc)
        .isoformat()
    )


def _day_bounds(
    local_date,
):
    start = datetime.combine(
        local_date,
        dt_time.min,
        tzinfo=SRI_LANKA_TZ,
    )

    end = (
        start
        + timedelta(days=1)
    )

    return (
        _utc_iso(start),
        _utc_iso(end),
    )


def completed_minutes_for_date(
    user_id,
    local_date,
):
    start_iso, end_iso = (
        _day_bounds(
            local_date
        )
    )

    result = (
        supabase
        .table("study_sessions")
        .select(
            "actual_minutes,planned_minutes"
        )
        .eq(
            "user_id",
            int(user_id),
        )
        .eq(
            "status",
            "completed",
        )
        .gte(
            "started_at",
            start_iso,
        )
        .lt(
            "started_at",
            end_iso,
        )
        .execute()
    )

    total = 0

    for item in (
        result.data
        or []
    ):
        total += int(
            item.get(
                "actual_minutes"
            )
            or item.get(
                "planned_minutes"
            )
            or 0
        )

    return total


def calculate_streak(
    user_id,
    target_minutes,
):
    today = datetime.now(
        SRI_LANKA_TZ
    ).date()

    daily = []

    for offset in range(
        0,
        60,
    ):
        day = (
            today
            - timedelta(
                days=offset
            )
        )

        minutes = completed_minutes_for_date(
            user_id,
            day,
        )

        daily.append(
            (
                day,
                minutes,
            )
        )

    current_streak = 0

    # If today's goal is not complete yet, allow streak
    # to continue from yesterday rather than immediately
    # resetting the streak during the day.
    start_index = 0

    if (
        daily
        and daily[0][1]
        < target_minutes
    ):
        start_index = 1

    for _, minutes in daily[
        start_index:
    ]:
        if minutes >= target_minutes:
            current_streak += 1
        else:
            break

    best_streak = 0
    running = 0

    for _, minutes in reversed(
        daily
    ):
        if minutes >= target_minutes:
            running += 1
            best_streak = max(
                best_streak,
                running,
            )
        else:
            running = 0

    return {
        "current_streak": current_streak,
        "best_streak_60d": best_streak,
        "today_minutes": (
            daily[0][1]
            if daily
            else 0
        ),
        "last_7_days": daily[
            :7
        ],
    }


def register_study_streak_handlers(
    bot,
    show_main_menu,
):

    def show_streak_menu(
        chat_id,
        user_id,
    ):
        streak_state.pop(
            chat_id,
            None,
        )

        preferences = (
            get_study_preferences(
                user_id
            )
        )

        target = int(
            preferences.get(
                "daily_target_minutes"
            )
            or 60
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "🔥 View My Streak"
            ),
            types.KeyboardButton(
                "🎯 Set Daily Target"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "🔥 Study Streak\n\n"
                f"🎯 Daily target: {target} minutes\n\n"
                "A streak day counts when your completed "
                "study-session minutes reach your daily target."
            ),
            reply_markup=markup,
        )

    @bot.message_handler(
        commands=["streak"]
    )
    def streak_command(
        message
    ):
        show_streak_menu(
            message.chat.id,
            message.from_user.id,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔥 Study Streak"
    )
    def streak_button(
        message
    ):
        show_streak_menu(
            message.chat.id,
            message.from_user.id,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔥 View My Streak"
    )
    def view_streak(
        message
    ):
        try:
            preferences = (
                get_study_preferences(
                    message.from_user.id
                )
            )

            target = int(
                preferences.get(
                    "daily_target_minutes"
                )
                or 60
            )

            stats = calculate_streak(
                message.from_user.id,
                target,
            )

            lines = [
                "🔥 STUDY STREAK",
                "━━━━━━━━━━━━━━━━━━",
                "",
                f"🎯 Daily Target: {target} min",
                f"⏱ Today: {stats['today_minutes']} min",
                f"🔥 Current Streak: {stats['current_streak']} day(s)",
                f"🏆 Best Streak (last 60 days): "
                f"{stats['best_streak_60d']} day(s)",
                "",
                "📅 LAST 7 DAYS",
            ]

            for day, minutes in stats[
                "last_7_days"
            ]:
                marker = (
                    "✅"
                    if minutes >= target
                    else "▫️"
                )

                lines.append(
                    (
                        f"{marker} "
                        f"{day.strftime('%d-%m')} "
                        f"— {minutes} min"
                    )
                )

            bot.send_message(
                message.chat.id,
                "\n".join(lines),
            )

        except Exception as error:
            print(
                "Study streak error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not calculate study streak.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "🎯 Set Daily Target"
    )
    def set_target_button(
        message
    ):
        streak_state[
            message.chat.id
        ] = {
            "step": "target"
        }

        bot.send_message(
            message.chat.id,
            (
                "🎯 Send your daily study target in minutes.\n\n"
                "Examples:\n"
                "30\n"
                "60\n"
                "120"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.chat.id in streak_state,
        content_types=["text"],
    )
    def streak_state_handler(
        message
    ):
        chat_id = message.chat.id
        text = (
            message.text
            or ""
        ).strip()

        if text == "🏠 Main Menu":
            streak_state.pop(
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
            streak_state.pop(
                chat_id,
                None,
            )
            return ContinueHandling()

        state = streak_state.get(
            chat_id,
            {}
        )

        if state.get(
            "step"
        ) != "target":
            return

        try:
            minutes = int(
                text
            )

        except ValueError:
            bot.send_message(
                chat_id,
                "❌ Enter minutes as a whole number.",
            )
            return

        if not 1 <= minutes <= 1440:
            bot.send_message(
                chat_id,
                (
                    "❌ Target must be between "
                    "1 and 1440 minutes."
                ),
            )
            return

        try:
            set_daily_target(
                message.from_user.id,
                minutes,
            )

            streak_state.pop(
                chat_id,
                None,
            )

            bot.send_message(
                chat_id,
                (
                    "✅ Daily study target updated!\n\n"
                    f"🎯 {minutes} minutes per day"
                ),
            )

            show_streak_menu(
                chat_id,
                message.from_user.id,
            )

        except Exception as error:
            print(
                "Set daily target error:",
                repr(error),
            )

            bot.send_message(
                chat_id,
                "❌ Could not update daily target.",
            )
