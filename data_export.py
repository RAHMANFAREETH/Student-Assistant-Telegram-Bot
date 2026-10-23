import gzip
import io
import json
from datetime import datetime, timezone

from telebot import types

from db import supabase


EXPORT_TABLES = [
    "subjects",
    "notes",
    "reminders",
    "assignments",
    "study_materials",
    "timetable_entries",
    "study_sessions",
    "flashcards",
    "quiz_attempts",
    "voice_notes",
    "language_vocabulary",
    "exams",
    "attendance_records",
    "study_goals",
    "semesters",
    "course_results",
]


TABLE_LIMITS = {
    "study_materials": 250,
    "voice_notes": 500,
}


DEFAULT_LIMIT = 2000


def _fetch_table(
    user_id,
    table_name,
):
    limit = TABLE_LIMITS.get(
        table_name,
        DEFAULT_LIMIT,
    )

    result = (
        supabase
        .table(
            table_name
        )
        .select("*")
        .eq(
            "user_id",
            int(user_id),
        )
        .limit(limit)
        .execute()
    )

    return (
        result.data
        or []
    )


def build_user_export(
    user_id,
):
    data = {}

    warnings = []

    for table_name in EXPORT_TABLES:
        try:
            rows = _fetch_table(
                user_id,
                table_name,
            )

            data[
                table_name
            ] = rows

        except Exception as error:
            print(
                f"Export table error ({table_name}):",
                repr(error),
            )

            data[
                table_name
            ] = []

            warnings.append(
                table_name
            )

    payload = {
        "export_format": (
            "Student Assistant Bot Academic Export"
        ),
        "version": "4.8",
        "generated_at_utc": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "user_id": int(
            user_id
        ),
        "warnings": (
            (
                "Some tables could not be read: "
                + ", ".join(
                    warnings
                )
            )
            if warnings
            else None
        ),
        "data": data,
    }

    return payload


def make_export_file(
    user_id,
):
    payload = build_user_export(
        user_id
    )

    json_bytes = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        default=str,
    ).encode(
        "utf-8"
    )

    compressed = gzip.compress(
        json_bytes,
        compresslevel=9,
    )

    buffer = io.BytesIO(
        compressed
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    buffer.name = (
        f"student_assistant_backup_{timestamp}.json.gz"
    )

    return (
        buffer,
        len(json_bytes),
        len(compressed),
    )


def register_data_export_handlers(
    bot,
    show_main_menu,
):

    @bot.message_handler(
        commands=["export"]
    )
    def export_command(
        message
    ):
        export_user_data(
            message
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📦 Export My Data"
    )
    def export_button(
        message
    ):
        export_user_data(
            message
        )

    def export_user_data(
        message
    ):
        status = bot.send_message(
            message.chat.id,
            (
                "📦 Preparing your private academic backup..."
            ),
        )

        try:
            (
                file_buffer,
                raw_size,
                compressed_size,
            ) = make_export_file(
                message.from_user.id
            )

            try:
                bot.delete_message(
                    message.chat.id,
                    status.message_id,
                )
            except Exception:
                pass

            bot.send_document(
                message.chat.id,
                file_buffer,
                caption=(
                    "📦 Student Assistant Backup\n\n"
                    "Contains only your academic rows from "
                    "the bot database.\n"
                    "It does not contain BOT_TOKEN, API keys, "
                    "Supabase keys, or webhook secrets.\n\n"
                    f"Raw JSON: "
                    f"{raw_size / 1024:.1f} KB\n"
                    f"Compressed: "
                    f"{compressed_size / 1024:.1f} KB"
                ),
            )

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
            )

            markup.add(
                types.KeyboardButton(
                    "🏠 Main Menu"
                )
            )

            bot.send_message(
                message.chat.id,
                (
                    "✅ Export complete.\n\n"
                    "Keep this file private because it may "
                    "contain your notes, deadlines, transcripts, "
                    "grades, and study records."
                ),
                reply_markup=markup,
            )

        except Exception as error:
            print(
                "Data export error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not create your data export.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "🏠 Main Menu"
    )
    def export_main_menu(
        message
    ):
        show_main_menu(
            message.chat.id,
            message.from_user.first_name
            or "Friend",
        )
