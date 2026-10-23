from db import supabase


def save_translation(
    user_id,
    chat_id,
    source_language,
    target_language,
    original_text,
    translated_text,
    provider="",
    kind="text",
):
    try:
        payload = {
            "user_id": int(user_id),
            "chat_id": int(chat_id),
            "source_language": source_language,
            "target_language": target_language,
            "original_text": original_text,
            "translated_text": translated_text,
            "provider": provider or "",
            "kind": kind,
        }

        result = (
            supabase
            .table("translation_history")
            .insert(payload)
            .execute()
        )

        if result.data:
            return result.data[0].get("id")

    except Exception as error:
        print("Translation history save error:", repr(error))

    return None


def get_translation_history(user_id, limit=10):
    try:
        result = (
            supabase
            .table("translation_history")
            .select(
                "id,source_language,target_language,"
                "original_text,translated_text,provider,kind,created_at"
            )
            .eq("user_id", int(user_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return result.data or []

    except Exception as error:
        print("Translation history read error:", repr(error))
        return []


def get_translation_by_id(user_id, translation_id):
    try:
        result = (
            supabase
            .table("translation_history")
            .select(
                "id,source_language,target_language,"
                "original_text,translated_text,provider,kind,created_at"
            )
            .eq("user_id", int(user_id))
            .eq("id", int(translation_id))
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0]

    except Exception as error:
        print("Translation history item error:", repr(error))

    return None


def clear_translation_history(user_id):
    try:
        (
            supabase
            .table("translation_history")
            .delete()
            .eq("user_id", int(user_id))
            .execute()
        )
        return True

    except Exception as error:
        print("Translation history clear error:", repr(error))
        return False
