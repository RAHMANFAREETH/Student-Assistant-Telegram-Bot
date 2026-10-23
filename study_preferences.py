from datetime import datetime, timezone

from db import supabase


DEFAULT_DAILY_TARGET = 60


def get_study_preferences(
    user_id,
):
    result = (
        supabase
        .table("study_preferences")
        .select(
            "user_id,daily_target_minutes,"
            "created_at,updated_at"
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

    return {
        "user_id": int(user_id),
        "daily_target_minutes": (
            DEFAULT_DAILY_TARGET
        ),
    }


def set_daily_target(
    user_id,
    minutes,
):
    minutes = int(minutes)

    if not 1 <= minutes <= 1440:
        raise ValueError(
            "Daily study target must be between 1 and 1440 minutes."
        )

    payload = {
        "user_id": int(user_id),
        "daily_target_minutes": minutes,
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    result = (
        supabase
        .table("study_preferences")
        .upsert(
            payload,
            on_conflict="user_id",
        )
        .execute()
    )

    return (
        result.data[0]
        if result.data
        else payload
    )
