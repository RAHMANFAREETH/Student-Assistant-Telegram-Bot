import os
from datetime import datetime
from zoneinfo import ZoneInfo

from db import supabase


SRI_LANKA_TZ = ZoneInfo(
    "Asia/Colombo"
)


REQUIRED_ENV = [
    "BOT_TOKEN",
    "SUPABASE_URL",
    "SUPABASE_SECRET_KEY",
    "WEBHOOK_SECRET",
]


OPTIONAL_ENV = [
    "OCR_SPACE_API_KEY",
    "ASSEMBLYAI_API_KEY",
]


EXPECTED_TABLES = [
    "notes",
    "reminders",
    "subjects",
    "assignments",
    "study_materials",
    "timetable_entries",
    "study_sessions",
    "flashcards",
    "flashcard_reviews",
    "quiz_attempts",
    "voice_notes",
    "language_vocabulary",
    "exams",
    "attendance_records",
    "study_goals",
    "semesters",
    "course_results",
    "study_preferences",
    "revision_plans",
    "revision_tasks",
    "notification_preferences",
]


def check_environment():
    results = []

    for name in REQUIRED_ENV:
        results.append(
            {
                "name": name,
                "required": True,
                "ok": bool(
                    os.getenv(
                        name
                    )
                ),
            }
        )

    for name in OPTIONAL_ENV:
        results.append(
            {
                "name": name,
                "required": False,
                "ok": bool(
                    os.getenv(
                        name
                    )
                ),
            }
        )

    return results


def check_database_tables():
    results = []

    for table_name in EXPECTED_TABLES:
        try:
            (
                supabase
                .table(
                    table_name
                )
                .select("*")
                .limit(1)
                .execute()
            )

            results.append(
                {
                    "table": table_name,
                    "ok": True,
                    "error": None,
                }
            )

        except Exception as error:
            results.append(
                {
                    "table": table_name,
                    "ok": False,
                    "error": str(
                        error
                    ),
                }
            )

    return results


def build_health_report():
    env_results = (
        check_environment()
    )

    table_results = (
        check_database_tables()
    )

    required_ok = sum(
        1
        for item in env_results
        if item[
            "required"
        ]
        and item[
            "ok"
        ]
    )

    required_total = sum(
        1
        for item in env_results
        if item[
            "required"
        ]
    )

    tables_ok = sum(
        1
        for item in table_results
        if item[
            "ok"
        ]
    )

    now = datetime.now(
        SRI_LANKA_TZ
    )

    lines = [
        "🛠 SYSTEM HEALTH — V5.4",
        "━━━━━━━━━━━━━━━━━━",
        "",
        (
            "🕒 Checked: "
            + now.strftime(
                "%d-%m-%Y %I:%M %p"
            )
        ),
        "",
        (
            f"🔐 Required environment: "
            f"{required_ok}/{required_total}"
        ),
    ]

    for item in env_results:
        marker = (
            "✅"
            if item[
                "ok"
            ]
            else (
                "❌"
                if item[
                    "required"
                ]
                else "▫️"
            )
        )

        optional = (
            ""
            if item[
                "required"
            ]
            else " (optional)"
        )

        lines.append(
            (
                f"{marker} "
                f"{item['name']}"
                f"{optional}"
            )
        )

    lines.extend(
        [
            "",
            (
                f"🗄 Database tables: "
                f"{tables_ok}/"
                f"{len(table_results)}"
            ),
        ]
    )

    missing = [
        item[
            "table"
        ]
        for item in table_results
        if not item[
            "ok"
        ]
    ]

    if missing:
        lines.append(
            "❌ Missing/unavailable:"
        )

        for table_name in missing:
            lines.append(
                f"• {table_name}"
            )

    else:
        lines.append(
            "✅ All expected tables are available."
        )

    if (
        required_ok
        == required_total
        and tables_ok
        == len(
            table_results
        )
    ):
        lines.extend(
            [
                "",
                "🟢 Core system looks healthy.",
            ]
        )

    else:
        lines.extend(
            [
                "",
                (
                    "🟡 Review the missing items above "
                    "before deployment."
                ),
            ]
        )

    return "\n".join(
        lines
    )


def register_system_health_handlers(
    bot,
):
    @bot.message_handler(
        commands=[
            "healthcheck",
            "systemhealth",
        ]
    )
    def system_health_command(
        message
    ):
        # Diagnostics reveal infrastructure configuration and table names.
        # Deny access if no explicit admin IDs have been configured.
        admins = {
            int(value.strip())
            for value in os.getenv("AI_OPS_ADMIN_IDS", "").split(",")
            if value.strip().isascii() and value.strip().isdigit()
        }
        if (getattr(message.chat, "type", None) != "private"
                or int(message.from_user.id) not in admins):
            bot.send_message(message.chat.id,
                "🔒 System diagnostics are available to configured admins only.")
            return
        status = bot.send_message(
            message.chat.id,
            "🛠 Checking bot system health..."
        )

        try:
            report = build_health_report()

            try:
                bot.delete_message(
                    message.chat.id,
                    status.message_id,
                )
            except Exception:
                pass

            bot.send_message(
                message.chat.id,
                report,
            )

        except Exception as error:
            print(
                "System health error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                (
                    "❌ System health check failed.\n\n"
                    "Please check the Render logs privately."
                ),
            )
