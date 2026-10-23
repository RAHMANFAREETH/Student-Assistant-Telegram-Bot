TELEGRAM_SAFE_TEXT_LIMIT = 3800


def split_telegram_text(
    text,
    limit=TELEGRAM_SAFE_TEXT_LIMIT,
):
    """
    Split long Telegram text safely.
    Tries to split on a newline first.
    """

    text = str(
        text
        or ""
    )

    if not text:
        return [""]

    parts = []

    while len(text) > limit:
        split_at = text.rfind(
            "\n",
            0,
            limit,
        )

        if split_at < limit // 2:
            split_at = limit

        parts.append(
            text[
                :split_at
            ]
        )

        text = text[
            split_at:
        ].lstrip(
            "\n"
        )

    if text:
        parts.append(
            text
        )

    return parts


def safe_delete_message(
    bot,
    chat_id,
    message_id,
):
    try:
        bot.delete_message(
            chat_id,
            message_id,
        )

        return True

    except Exception:
        return False


def clear_state(
    state_store,
    chat_id,
):
    try:
        state_store.pop(
            chat_id,
            None,
        )
    except Exception:
        pass


def parse_int(
    value,
    minimum=None,
    maximum=None,
):
    number = int(
        str(value).strip()
    )

    if (
        minimum is not None
        and number < minimum
    ):
        raise ValueError(
            f"Value must be at least {minimum}."
        )

    if (
        maximum is not None
        and number > maximum
    ):
        raise ValueError(
            f"Value must be at most {maximum}."
        )

    return number
