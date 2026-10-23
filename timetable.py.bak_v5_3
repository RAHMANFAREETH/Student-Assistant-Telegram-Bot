from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase
from subjects import (
    get_subjects,
    get_subject_by_id,
    subject_display,
)


timetable_state = {}
SRI_LANKA_TZ = ZoneInfo("Asia/Colombo")

DAY_NAMES = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}

DAY_BUTTONS = {
    "Mon": 0,
    "Tue": 1,
    "Wed": 2,
    "Thu": 3,
    "Fri": 4,
    "Sat": 5,
    "Sun": 6,
}

GLOBAL_BUTTONS = {
    "📄 PDF Tools",
    "📝 Notes",
    "🌐 Translate",
    "⏰ Study Reminder",
    "📚 Subjects",
    "📅 Assignments",
    "📚 Study Materials",
    "🧠 Flashcards",
    "❓ Quiz",
    "📊 Dashboard",
    "📈 Progress",
    "🗓 Timetable",
    "⏱ Study Planner",
    "ℹ️ Help",
}


def get_timetable_entries(
    user_id,
    day_of_week=None,
):
    query = (
        supabase
        .table("timetable_entries")
        .select(
            "id,user_id,subject_id,title,day_of_week,"
            "start_time,end_time,location,created_at"
        )
        .eq("user_id", int(user_id))
    )

    if day_of_week is not None:
        query = query.eq(
            "day_of_week",
            int(day_of_week),
        )

    result = (
        query
        .order("day_of_week")
        .order("start_time")
        .execute()
    )

    return result.data or []


def get_timetable_entry(
    user_id,
    entry_id,
):
    result = (
        supabase
        .table("timetable_entries")
        .select(
            "id,user_id,subject_id,title,day_of_week,"
            "start_time,end_time,location"
        )
        .eq("user_id", int(user_id))
        .eq("id", int(entry_id))
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def create_timetable_entry(
    user_id,
    subject_id,
    title,
    day_of_week,
    start_time,
    end_time,
    location=None,
):
    payload = {
        "user_id": int(user_id),
        "subject_id": subject_id,
        "title": title.strip(),
        "day_of_week": int(day_of_week),
        "start_time": start_time.strftime("%H:%M:%S"),
        "end_time": end_time.strftime("%H:%M:%S"),
        "location": (
            location.strip()
            if location
            else None
        ),
    }

    return (
        supabase
        .table("timetable_entries")
        .insert(payload)
        .execute()
    )


def delete_timetable_entry(
    user_id,
    entry_id,
):
    entry = get_timetable_entry(
        user_id,
        entry_id,
    )

    if not entry:
        return False

    (
        supabase
        .table("timetable_entries")
        .delete()
        .eq("user_id", int(user_id))
        .eq("id", int(entry_id))
        .execute()
    )

    return True


def parse_time(value):
    value = value.strip()

    for fmt in (
        "%H:%M",
        "%I:%M %p",
    ):
        try:
            return datetime.strptime(
                value,
                fmt,
            ).time()

        except ValueError:
            pass

    return None


def format_db_time(value):
    if not value:
        return "--:--"

    text = str(value)

    for fmt in (
        "%H:%M:%S",
        "%H:%M",
    ):
        try:
            parsed = datetime.strptime(
                text,
                fmt,
            )

            return parsed.strftime(
                "%I:%M %p"
            )

        except ValueError:
            pass

    return text


def subject_name(
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


def format_entry(
    user_id,
    entry,
):
    location = (
        entry.get("location")
        or ""
    ).strip()

    location_text = (
        f"\n📍 {location}"
        if location
        else ""
    )

    return (
        f"#{entry['id']} {entry['title']}\n"
        f"📚 {subject_name(user_id, entry.get('subject_id'))}\n"
        f"🕒 {format_db_time(entry.get('start_time'))}"
        f" – {format_db_time(entry.get('end_time'))}"
        f"{location_text}"
    )


def parse_subject_button(text):
    if text == "⏭ No Subject":
        return None

    if not text.startswith("📚 #"):
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


def register_timetable_handlers(
    bot,
    show_main_menu,
):

    def show_timetable_menu(
        chat_id
    ):
        timetable_state.pop(
            chat_id,
            None,
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "➕ Add Class"
            ),
            types.KeyboardButton(
                "📅 Today's Timetable"
            ),
            types.KeyboardButton(
                "🗓 Weekly Timetable"
            ),
            types.KeyboardButton(
                "🗑 Delete Class"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "🗓 Timetable\n\n"
                "Save your recurring weekly classes "
                "and quickly check today's schedule."
            ),
            reply_markup=markup,
        )

    def show_day_entries(
        message,
        day_number,
    ):
        entries = get_timetable_entries(
            message.from_user.id,
            day_of_week=day_number,
        )

        heading = (
            f"📅 {DAY_NAMES[day_number]}\n"
        )

        if not entries:
            bot.send_message(
                message.chat.id,
                (
                    heading
                    + "\n✅ No classes scheduled."
                ),
            )
            return

        parts = [
            heading
        ]

        for entry in entries:
            parts.append(
                "\n"
                + format_entry(
                    message.from_user.id,
                    entry,
                )
                + "\n"
            )

        bot.send_message(
            message.chat.id,
            "\n".join(parts),
        )

    @bot.message_handler(
        commands=["timetable"]
    )
    def timetable_command(message):
        show_timetable_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🗓 Timetable"
    )
    def timetable_button(message):
        show_timetable_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📅 Today's Timetable"
    )
    def today_timetable(message):
        now = datetime.now(
            SRI_LANKA_TZ
        )

        show_day_entries(
            message,
            now.weekday(),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🗓 Weekly Timetable"
    )
    def weekly_timetable(message):
        entries = get_timetable_entries(
            message.from_user.id
        )

        if not entries:
            bot.send_message(
                message.chat.id,
                (
                    "🗓 Weekly Timetable\n\n"
                    "No classes have been added yet."
                ),
            )
            return

        by_day = {
            day: []
            for day in range(7)
        }

        for entry in entries:
            by_day[
                int(
                    entry["day_of_week"]
                )
            ].append(entry)

        parts = [
            "🗓 WEEKLY TIMETABLE\n"
            "━━━━━━━━━━━━━━━━━━"
        ]

        for day in range(7):
            if not by_day[day]:
                continue

            parts.append(
                f"\n\n📅 {DAY_NAMES[day]}"
            )

            for entry in by_day[day]:
                parts.append(
                    "\n\n"
                    + format_entry(
                        message.from_user.id,
                        entry,
                    )
                )

        text = "\n".join(parts)

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
        m.text == "➕ Add Class"
    )
    def add_class(message):
        subjects = get_subjects(
            message.from_user.id
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=1,
        )

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
                "🔙 Timetable Menu"
            )
        )

        timetable_state[
            message.chat.id
        ] = {
            "step": "subject"
        }

        bot.send_message(
            message.chat.id,
            "📚 Choose the class subject:",
            reply_markup=markup,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🗑 Delete Class"
    )
    def delete_class(message):
        timetable_state[
            message.chat.id
        ] = {
            "step": "delete"
        }

        bot.send_message(
            message.chat.id,
            (
                "🗑 Send the timetable entry number.\n"
                "Example: 4"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔙 Timetable Menu"
    )
    def back_timetable(message):
        show_timetable_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.chat.id in timetable_state,
        content_types=["text"],
    )
    def timetable_state_handler(
        message
    ):
        chat_id = message.chat.id
        text = (
            message.text
            or ""
        ).strip()

        if text == "🏠 Main Menu":
            timetable_state.pop(
                chat_id,
                None,
            )

            show_main_menu(
                chat_id,
                message.from_user.first_name
                or "Friend",
            )
            return

        if text == "🔙 Timetable Menu":
            show_timetable_menu(
                chat_id
            )
            return

        if (
            text.startswith("/")
            or text in GLOBAL_BUTTONS
        ):
            timetable_state.pop(
                chat_id,
                None,
            )
            return ContinueHandling()

        state = timetable_state.get(
            chat_id,
            {}
        )

        step = state.get(
            "step"
        )

        if step == "subject":
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

            state["subject_id"] = subject_id
            state["step"] = "title"

            bot.send_message(
                chat_id,
                (
                    "📝 Send the class title.\n\n"
                    "Example:\n"
                    "Arabic Grammar Lecture"
                ),
            )
            return

        if step == "title":
            if len(text) < 2:
                bot.send_message(
                    chat_id,
                    "❌ Enter a valid title.",
                )
                return

            if len(text) > 150:
                bot.send_message(
                    chat_id,
                    "❌ Title is too long.",
                )
                return

            state["title"] = text
            state["step"] = "day"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
                row_width=4,
            )

            markup.add(
                *[
                    types.KeyboardButton(
                        button
                    )
                    for button in DAY_BUTTONS
                ]
            )

            bot.send_message(
                chat_id,
                "📅 Choose the day:",
                reply_markup=markup,
            )
            return

        if step == "day":
            if text not in DAY_BUTTONS:
                bot.send_message(
                    chat_id,
                    "❌ Choose a day using the buttons.",
                )
                return

            state["day_of_week"] = (
                DAY_BUTTONS[text]
            )

            state["step"] = "start_time"

            bot.send_message(
                chat_id,
                (
                    "🕒 Send start time.\n\n"
                    "Examples:\n"
                    "08:30\n"
                    "01:30 PM"
                ),
            )
            return

        if step == "start_time":
            value = parse_time(
                text
            )

            if not value:
                bot.send_message(
                    chat_id,
                    (
                        "❌ Invalid time.\n"
                        "Use 08:30 or 01:30 PM."
                    ),
                )
                return

            state["start_time"] = value
            state["step"] = "end_time"

            bot.send_message(
                chat_id,
                "🕒 Send end time:",
            )
            return

        if step == "end_time":
            value = parse_time(
                text
            )

            if not value:
                bot.send_message(
                    chat_id,
                    "❌ Invalid end time.",
                )
                return

            if value <= state[
                "start_time"
            ]:
                bot.send_message(
                    chat_id,
                    (
                        "❌ End time must be after "
                        "the start time."
                    ),
                )
                return

            state["end_time"] = value
            state["step"] = "location"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
            )

            markup.add(
                types.KeyboardButton(
                    "⏭ Skip Location"
                ),
                types.KeyboardButton(
                    "🔙 Timetable Menu"
                ),
            )

            bot.send_message(
                chat_id,
                (
                    "📍 Send classroom/location.\n\n"
                    "Or choose ⏭ Skip Location."
                ),
                reply_markup=markup,
            )
            return

        if step == "location":
            location = (
                None
                if text == "⏭ Skip Location"
                else text
            )

            try:
                create_timetable_entry(
                    user_id=message.from_user.id,
                    subject_id=state.get(
                        "subject_id"
                    ),
                    title=state[
                        "title"
                    ],
                    day_of_week=state[
                        "day_of_week"
                    ],
                    start_time=state[
                        "start_time"
                    ],
                    end_time=state[
                        "end_time"
                    ],
                    location=location,
                )

                timetable_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    (
                        "✅ Class added!\n\n"
                        f"📅 {DAY_NAMES[state['day_of_week']]}\n"
                        f"🕒 "
                        f"{state['start_time'].strftime('%I:%M %p')}"
                        " – "
                        f"{state['end_time'].strftime('%I:%M %p')}"
                    ),
                )

                show_timetable_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Create timetable entry error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not save the class.",
                )

            return

        if step == "delete":
            try:
                entry_id = int(
                    text.replace(
                        "#",
                        ""
                    )
                )
            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Send only the entry number.",
                )
                return

            try:
                success = delete_timetable_entry(
                    message.from_user.id,
                    entry_id,
                )

                if not success:
                    bot.send_message(
                        chat_id,
                        "❌ Timetable entry not found.",
                    )
                    return

                timetable_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    "✅ Timetable entry deleted.",
                )

                show_timetable_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Delete timetable error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not delete the entry.",
                )

            return
