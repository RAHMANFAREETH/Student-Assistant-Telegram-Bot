from datetime import datetime, timedelta, time as dt_time, timezone
from zoneinfo import ZoneInfo

from db import supabase
from subjects import get_subject_by_id, subject_display


SRI_LANKA_TZ = ZoneInfo("Asia/Colombo")


def _utc_iso(local_dt):
    if local_dt.tzinfo is None:
        local_dt = local_dt.replace(
            tzinfo=SRI_LANKA_TZ
        )

    return (
        local_dt
        .astimezone(timezone.utc)
        .isoformat()
    )


def get_sessions_since(
    user_id,
    start_local,
):
    result = (
        supabase
        .table("study_sessions")
        .select(
            "id,subject_id,planned_minutes,actual_minutes,"
            "started_at,ended_at,status"
        )
        .eq("user_id", int(user_id))
        .eq("status", "completed")
        .gte(
            "started_at",
            _utc_iso(start_local),
        )
        .order(
            "started_at",
            desc=True,
        )
        .limit(300)
        .execute()
    )

    return result.data or []


def session_minutes(session):
    value = session.get(
        "actual_minutes"
    )

    if value is not None:
        return max(
            int(value),
            0,
        )

    return max(
        int(
            session.get(
                "planned_minutes"
            )
            or 0
        ),
        0,
    )


def build_study_analytics(
    user_id
):
    now = datetime.now(
        SRI_LANKA_TZ
    )

    today_start = datetime.combine(
        now.date(),
        dt_time.min,
        tzinfo=SRI_LANKA_TZ,
    )

    week_start = (
        today_start
        - timedelta(days=6)
    )

    sessions = get_sessions_since(
        user_id,
        week_start,
    )

    total_minutes = sum(
        session_minutes(session)
        for session in sessions
    )

    today_minutes = 0

    subject_totals = {}

    daily_totals = {
        (
            week_start.date()
            + timedelta(days=index)
        ): 0
        for index in range(7)
    }

    for session in sessions:
        minutes = session_minutes(
            session
        )

        started_raw = session.get(
            "started_at"
        )

        if started_raw:
            try:
                started = datetime.fromisoformat(
                    started_raw.replace(
                        "Z",
                        "+00:00",
                    )
                ).astimezone(
                    SRI_LANKA_TZ
                )

                if started.date() == now.date():
                    today_minutes += minutes

                if started.date() in daily_totals:
                    daily_totals[
                        started.date()
                    ] += minutes

            except Exception:
                pass

        subject_id = session.get(
            "subject_id"
        )

        subject_totals[
            subject_id
        ] = (
            subject_totals.get(
                subject_id,
                0,
            )
            + minutes
        )

    average = (
        round(
            total_minutes
            / len(sessions)
        )
        if sessions
        else 0
    )

    top_subject_text = (
        "No study sessions yet"
    )

    if subject_totals:
        top_subject_id = max(
            subject_totals,
            key=subject_totals.get,
        )

        top_minutes = (
            subject_totals[
                top_subject_id
            ]
        )

        if top_subject_id:
            subject = get_subject_by_id(
                user_id,
                top_subject_id,
            )

            top_name = (
                subject_display(
                    subject
                )
                if subject
                else "Unknown Subject"
            )
        else:
            top_name = "No Subject"

        top_subject_text = (
            f"{top_name} — {top_minutes} min"
        )

    day_lines = []

    for day, minutes in daily_totals.items():
        day_lines.append(
            (
                f"{day.strftime('%a')}: "
                f"{minutes} min"
            )
        )

    return (
        "📊 WEEKLY STUDY ANALYTICS\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"⏱ Today: {today_minutes} min\n"
        f"📅 Last 7 Days: {total_minutes} min\n"
        f"🎯 Sessions: {len(sessions)}\n"
        f"📐 Avg/Session: {average} min\n"
        f"🏆 Top Subject: {top_subject_text}\n\n"

        "📈 DAILY BREAKDOWN\n"
        + "\n".join(day_lines)
    )
