import time
from collections import OrderedDict

from telebot import types
from deep_translator import (
    GoogleTranslator,
    MyMemoryTranslator
)


# ==================================================
# USER STATE
# ==================================================

translation_state = {}
last_translation_time = {}

translation_cache = OrderedDict()

MAX_CACHE_SIZE = 200
MAX_INPUT_LENGTH = 12000
TRANSLATION_CHUNK_SIZE = 3000
TELEGRAM_CHUNK_SIZE = 3800
USER_COOLDOWN = 1.2


# ==================================================
# LANGUAGES
# ==================================================

LANGUAGES = {
    "🇬🇧 English": "en",
    "🇱🇰 Tamil": "ta",
    "🇱🇰 Sinhala": "si",
    "🇸🇦 Arabic": "ar",
    "🇮🇳 Hindi": "hi",
    "🇵🇰 Urdu": "ur",
    "🇮🇳 Malayalam": "ml",
    "🇲🇾 Malay": "ms",
    "🇮🇩 Indonesian": "id",
    "🇫🇷 French": "fr",
    "🇩🇪 German": "de",
    "🇹🇷 Turkish": "tr"
}


SOURCE_LANGUAGES = {
    "🔎 Auto Detect": "auto",
    **LANGUAGES
}


LANGUAGE_BY_CODE = {
    code: name
    for name, code in LANGUAGES.items()
}


# ==================================================
# QUICK PAIRS
# ==================================================

QUICK_PAIRS = {
    "⚡ English → Tamil": (
        "en",
        "ta"
    ),

    "⚡ Tamil → English": (
        "ta",
        "en"
    ),

    "⚡ Arabic → Tamil": (
        "ar",
        "ta"
    ),

    "⚡ Tamil → Arabic": (
        "ta",
        "ar"
    ),

    "⚡ Sinhala → Tamil": (
        "si",
        "ta"
    ),

    "⚡ Tamil → Sinhala": (
        "ta",
        "si"
    )
}


# ==================================================
# CACHE
# ==================================================

def cache_get(key):

    if key not in translation_cache:
        return None

    result = translation_cache.pop(
        key
    )

    translation_cache[
        key
    ] = result

    return result


def cache_save(
    key,
    value
):

    if key in translation_cache:

        translation_cache.pop(
            key
        )

    translation_cache[
        key
    ] = value

    while (
        len(translation_cache)
        > MAX_CACHE_SIZE
    ):

        translation_cache.popitem(
            last=False
        )


# ==================================================
# SPLIT LONG TEXT
# ==================================================

def split_long_text(
    text,
    max_size=TRANSLATION_CHUNK_SIZE
):

    text = text.strip()

    if len(text) <= max_size:
        return [text]

    chunks = []

    remaining = text

    while remaining:

        if len(remaining) <= max_size:

            chunks.append(
                remaining
            )

            break

        split_position = (
            remaining.rfind(
                "\n",
                0,
                max_size
            )
        )

        if split_position < max_size // 2:

            split_position = (
                remaining.rfind(
                    ". ",
                    0,
                    max_size
                )
            )

            if split_position != -1:
                split_position += 1

        if split_position < max_size // 2:

            split_position = (
                remaining.rfind(
                    " ",
                    0,
                    max_size
                )
            )

        if split_position <= 0:

            split_position = max_size

        chunk = remaining[
            :split_position
        ].strip()

        if chunk:

            chunks.append(
                chunk
            )

        remaining = remaining[
            split_position:
        ].strip()

    return chunks


# ==================================================
# TRANSLATE ONE CHUNK
# ==================================================

def translate_chunk(
    source,
    target,
    text
):

    cache_key = (
        source,
        target,
        text
    )

    cached = cache_get(
        cache_key
    )

    if cached:

        return (
            cached,
            "Cache"
        )


    # ==============================================
    # GOOGLE
    # ==============================================

    google_error = None

    for attempt in range(2):

        try:

            result = GoogleTranslator(
                source=source,
                target=target
            ).translate(
                text
            )

            if result:

                cache_save(
                    cache_key,
                    result
                )

                return (
                    result,
                    "Google"
                )

        except Exception as error:

            google_error = error

            print(
                "Google translation error:",
                repr(error)
            )

            if attempt == 0:

                time.sleep(
                    1.2
                )


    # ==============================================
    # MYMEMORY FALLBACK
    # ==============================================

    try:

        result = MyMemoryTranslator(
            source=source,
            target=target
        ).translate(
            text
        )

        if result:

            cache_save(
                cache_key,
                result
            )

            return (
                result,
                "MyMemory"
            )

    except Exception as error:

        print(
            "MyMemory translation error:",
            repr(error)
        )


    raise RuntimeError(
        f"Translation services failed: "
        f"{google_error}"
    )


# ==================================================
# TRANSLATE COMPLETE TEXT
# ==================================================

def translate_complete_text(
    source,
    target,
    text
):

    chunks = split_long_text(
        text
    )

    translated_chunks = []

    providers = []

    for index, chunk in enumerate(
        chunks
    ):

        result, provider = (
            translate_chunk(
                source,
                target,
                chunk
            )
        )

        translated_chunks.append(
            result
        )

        providers.append(
            provider
        )

        # Reduce rate-limit problems
        if index < len(chunks) - 1:

            time.sleep(
                0.4
            )

    final_text = "\n\n".join(
        translated_chunks
    )

    provider_name = (
        providers[0]
        if len(set(providers)) == 1
        else "Multiple"
    )

    return (
        final_text,
        provider_name
    )


# ==================================================
# LANGUAGE NAME
# ==================================================

def language_name(code):

    if code == "auto":

        return "🔎 Auto Detect"

    return LANGUAGE_BY_CODE.get(
        code,
        code
    )


# ==================================================
# SEND TRANSLATION RESULT
# ==================================================

def send_translation_result(
    bot,
    chat_id,
    source,
    target,
    translated_text,
    provider=None
):

    source_name = language_name(
        source
    )

    target_name = language_name(
        target
    )

    header = (
        "✅ Translation Complete\n\n"
        f"From: {source_name}\n"
        f"To: {target_name}\n"
        "\n──────────────\n\n"
    )

    complete_message = (
        header
        + translated_text
    )


    # ==============================================
    # SHORT RESULT
    # ==============================================

    if len(
        complete_message
    ) <= TELEGRAM_CHUNK_SIZE:

        markup = None

        # Telegram CopyTextButton supports
        # short copyable text
        if (
            1
            <= len(translated_text)
            <= 256
        ):

            markup = (
                types
                .InlineKeyboardMarkup()
            )

            copy_button = (
                types.InlineKeyboardButton(
                    "📋 Copy Translation",
                    copy_text=types.CopyTextButton(
                        translated_text
                    )
                )
            )

            markup.add(
                copy_button
            )

        bot.send_message(
            chat_id,
            complete_message,
            reply_markup=markup
        )


    # ==============================================
    # LONG RESULT
    # ==============================================

    else:

        bot.send_message(
            chat_id,
            header
        )

        for index in range(
            0,
            len(translated_text),
            TELEGRAM_CHUNK_SIZE
        ):

            bot.send_message(
                chat_id,
                translated_text[
                    index:
                    index
                    + TELEGRAM_CHUNK_SIZE
                ]
            )


    print(
        "Translation provider:",
        provider
    )


# ==================================================
# REGISTER TRANSLATOR
# ==================================================

def register_translation_handlers(
    bot,
    show_main_menu
):


    # ==============================================
    # TRANSLATOR HOME
    # ==============================================

    def show_translation_menu(
        chat_id
    ):

        translation_state[
            chat_id
        ] = {
            "step": "menu"
        }

        markup = (
            types.ReplyKeyboardMarkup(
                resize_keyboard=True,
                row_width=2
            )
        )

        markup.add(
            types.KeyboardButton(
                "⚡ English → Tamil"
            ),

            types.KeyboardButton(
                "⚡ Tamil → English"
            ),

            types.KeyboardButton(
                "⚡ Arabic → Tamil"
            ),

            types.KeyboardButton(
                "⚡ Tamil → Arabic"
            ),

            types.KeyboardButton(
                "⚡ Sinhala → Tamil"
            ),

            types.KeyboardButton(
                "⚡ Tamil → Sinhala"
            ),

            types.KeyboardButton(
                "⚙️ Choose Languages"
            ),

            types.KeyboardButton(
                "🏠 Main Menu"
            )
        )

        bot.send_message(
            chat_id,
            """
🌐 Advanced Translator

Choose a quick translation pair
or select your own languages.

⚡ Quick Translation
⚙️ Custom Languages

You can also reply to any text with:

/tr ta

Example:
/tr en
/tr ar
/tr si
""",
            reply_markup=markup
        )


    # ==============================================
    # SOURCE LANGUAGE MENU
    # ==============================================

    def show_source_menu(
        chat_id
    ):

        translation_state[
            chat_id
        ] = {
            "step": "source"
        }

        markup = (
            types.ReplyKeyboardMarkup(
                resize_keyboard=True,
                row_width=2
            )
        )

        for name in SOURCE_LANGUAGES:

            markup.add(
                types.KeyboardButton(
                    name
                )
            )

        markup.add(
            types.KeyboardButton(
                "🔙 Translator Menu"
            ),

            types.KeyboardButton(
                "🏠 Main Menu"
            )
        )

        bot.send_message(
            chat_id,
            """
🌐 Source Language

Choose the language of your text.

If you are unsure, choose:

🔎 Auto Detect
""",
            reply_markup=markup
        )


    # ==============================================
    # TARGET LANGUAGE MENU
    # ==============================================

    def show_target_menu(
        chat_id
    ):

        state = translation_state[
            chat_id
        ]

        state[
            "step"
        ] = "target"

        markup = (
            types.ReplyKeyboardMarkup(
                resize_keyboard=True,
                row_width=2
            )
        )

        for name in LANGUAGES:

            markup.add(
                types.KeyboardButton(
                    name
                )
            )

        markup.add(
            types.KeyboardButton(
                "🔙 Change Source"
            ),

            types.KeyboardButton(
                "🏠 Main Menu"
            )
        )

        bot.send_message(
            chat_id,
            f"""
✅ Source:

{language_name(state["source"])}

Now choose the target language:
""",
            reply_markup=markup
        )


    # ==============================================
    # READY MENU
    # ==============================================

    def show_ready_menu(
        chat_id
    ):

        state = translation_state[
            chat_id
        ]

        state[
            "step"
        ] = "text"

        markup = (
            types.ReplyKeyboardMarkup(
                resize_keyboard=True,
                row_width=2
            )
        )

        if state[
            "source"
        ] != "auto":

            markup.add(
                types.KeyboardButton(
                    "🔄 Swap Languages"
                )
            )

        markup.add(
            types.KeyboardButton(
                "🔁 Change Languages"
            ),

            types.KeyboardButton(
                "🔙 Translator Menu"
            ),

            types.KeyboardButton(
                "🏠 Main Menu"
            )
        )

        bot.send_message(
            chat_id,
            f"""
🌐 Translator Ready

From:
{language_name(state["source"])}

To:
{language_name(state["target"])}

📝 Send the text you want translated.

You can keep sending more text using
the same language pair.
""",
            reply_markup=markup
        )


    # ==============================================
    # TRANSLATE MENU BUTTON
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        m.text == "🌐 Translate"
    )
    def translator_button(
        message
    ):

        show_translation_menu(
            message.chat.id
        )


    # ==============================================
    # /translate
    # ==============================================

    @bot.message_handler(
        commands=[
            "translate"
        ]
    )
    def translate_command(
        message
    ):

        show_translation_menu(
            message.chat.id
        )


    # ==============================================
    # /tr TARGET
    #
    # Reply to a Telegram message:
    #
    # /tr ta
    # /tr en
    # /tr ar
    # ==============================================

    @bot.message_handler(
        commands=[
            "tr"
        ]
    )
    def quick_reply_translate(
        message
    ):

        chat_id = message.chat.id

        parts = (
            message.text
            .strip()
            .split()
        )

        if len(parts) != 2:

            bot.send_message(
                chat_id,
                """
❌ Usage:

Reply to a message and send:

/tr ta
/tr en
/tr ar
/tr si

Example:

Reply to English text with:

/tr ta
"""
            )

            return

        target = (
            parts[1]
            .strip()
            .lower()
        )

        if target not in LANGUAGE_BY_CODE:

            supported = ", ".join(
                LANGUAGE_BY_CODE.keys()
            )

            bot.send_message(
                chat_id,
                f"""
❌ Unsupported target language.

Supported codes:

{supported}
"""
            )

            return

        replied = (
            message.reply_to_message
        )

        if not replied:

            bot.send_message(
                chat_id,
                """
❌ Reply to a text message first.

Then send, for example:

/tr ta
"""
            )

            return

        original_text = (
            replied.text
            or replied.caption
        )

        if not original_text:

            bot.send_message(
                chat_id,
                """
❌ That message does not contain text.
"""
            )

            return

        status = bot.send_message(
            chat_id,
            "⏳ Translating..."
        )

        try:

            result, provider = (
                translate_complete_text(
                    "auto",
                    target,
                    original_text
                )
            )

            try:

                bot.delete_message(
                    chat_id,
                    status.message_id
                )

            except Exception:
                pass

            send_translation_result(
                bot,
                chat_id,
                "auto",
                target,
                result,
                provider
            )

        except Exception as error:

            print(
                "Quick translation error:",
                repr(error)
            )

            try:

                bot.delete_message(
                    chat_id,
                    status.message_id
                )

            except Exception:
                pass

            bot.send_message(
                chat_id,
                """
❌ Translation service is temporarily unavailable.

Please try again shortly.
"""
            )


    # ==============================================
    # TRANSLATOR STATE HANDLER
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        m.chat.id
        in translation_state
    )
    def translation_handler(
        message
    ):

        chat_id = (
            message.chat.id
        )

        if not message.text:

            bot.send_message(
                chat_id,
                "❌ Please send text."
            )

            return

        text = (
            message.text
            .strip()
        )

        state = (
            translation_state
            .get(chat_id)
        )

        if not state:

            return


        # ==========================================
        # MAIN MENU
        # ==========================================

        if text == "🏠 Main Menu":

            translation_state.pop(
                chat_id,
                None
            )

            first_name = (
                message
                .from_user
                .first_name
                or "Friend"
            )

            show_main_menu(
                chat_id,
                first_name
            )

            return


        # ==========================================
        # TRANSLATOR MENU
        # ==========================================

        if text == "🔙 Translator Menu":

            show_translation_menu(
                chat_id
            )

            return


        # ==========================================
        # CHANGE SOURCE
        # ==========================================

        if text == "🔙 Change Source":

            show_source_menu(
                chat_id
            )

            return


        # ==========================================
        # CHANGE LANGUAGES
        # ==========================================

        if text == "🔁 Change Languages":

            show_source_menu(
                chat_id
            )

            return


        # ==========================================
        # SWAP
        # ==========================================

        if text == "🔄 Swap Languages":

            source = state.get(
                "source"
            )

            target = state.get(
                "target"
            )

            if source == "auto":

                bot.send_message(
                    chat_id,
                    """
❌ Auto Detect cannot be swapped.

Choose a specific source language first.
"""
                )

                return

            state[
                "source"
            ] = target

            state[
                "target"
            ] = source

            bot.send_message(
                chat_id,
                f"""
🔄 Languages swapped!

From:
{language_name(state["source"])}

To:
{language_name(state["target"])}
"""
            )

            show_ready_menu(
                chat_id
            )

            return


        # ==========================================
        # QUICK LANGUAGE PAIRS
        # ==========================================

        if text in QUICK_PAIRS:

            source, target = (
                QUICK_PAIRS[text]
            )

            translation_state[
                chat_id
            ] = {
                "step": "text",
                "source": source,
                "target": target
            }

            show_ready_menu(
                chat_id
            )

            return


        # ==========================================
        # CUSTOM LANGUAGES
        # ==========================================

        if text == "⚙️ Choose Languages":

            show_source_menu(
                chat_id
            )

            return


        # ==========================================
        # SOURCE
        # ==========================================

        if state[
            "step"
        ] == "source":

            if text not in SOURCE_LANGUAGES:

                bot.send_message(
                    chat_id,
                    """
❌ Please choose a language using the buttons.
"""
                )

                return

            state[
                "source"
            ] = SOURCE_LANGUAGES[
                text
            ]

            show_target_menu(
                chat_id
            )

            return


        # ==========================================
        # TARGET
        # ==========================================

        if state[
            "step"
        ] == "target":

            if text not in LANGUAGES:

                bot.send_message(
                    chat_id,
                    """
❌ Please choose a target language using the buttons.
"""
                )

                return

            target = LANGUAGES[
                text
            ]

            source = state.get(
                "source"
            )

            if (
                source != "auto"
                and source == target
            ):

                bot.send_message(
                    chat_id,
                    """
❌ Source and target languages are the same.

Choose another target language.
"""
                )

                return

            state[
                "target"
            ] = target

            show_ready_menu(
                chat_id
            )

            return


        # ==========================================
        # TRANSLATE TEXT
        # ==========================================

        if state[
            "step"
        ] == "text":

            # --------------------------------------
            # SIZE CHECK
            # --------------------------------------

            if len(text) > MAX_INPUT_LENGTH:

                bot.send_message(
                    chat_id,
                    f"""
❌ Text is too long.

Maximum:
{MAX_INPUT_LENGTH:,} characters

Please divide it into smaller parts.
"""
                )

                return


            # --------------------------------------
            # RATE LIMIT
            # --------------------------------------

            now = time.time()

            last_time = (
                last_translation_time
                .get(
                    chat_id,
                    0
                )
            )

            if (
                now - last_time
                < USER_COOLDOWN
            ):

                bot.send_message(
                    chat_id,
                    """
⏳ Please wait a moment before sending another translation.
"""
                )

                return

            last_translation_time[
                chat_id
            ] = now


            status = bot.send_message(
                chat_id,
                "⏳ Translating..."
            )


            try:

                result, provider = (
                    translate_complete_text(
                        state[
                            "source"
                        ],

                        state[
                            "target"
                        ],

                        text
                    )
                )


                try:

                    bot.delete_message(
                        chat_id,
                        status.message_id
                    )

                except Exception:
                    pass


                send_translation_result(
                    bot,
                    chat_id,
                    state[
                        "source"
                    ],
                    state[
                        "target"
                    ],
                    result,
                    provider
                )


            except Exception as error:

                print(
                    "Translation error:",
                    repr(error)
                )

                try:

                    bot.delete_message(
                        chat_id,
                        status.message_id
                    )

                except Exception:
                    pass


                bot.send_message(
                    chat_id,
                    """
❌ Translation failed.

Google and backup translation services are temporarily unavailable.

Please try again shortly.
"""
                )