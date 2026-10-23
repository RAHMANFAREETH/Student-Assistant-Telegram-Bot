import time
from collections import OrderedDict

from telebot import types
from deep_translator import GoogleTranslator, MyMemoryTranslator

from translation_history import (
    save_translation,
    get_translation_history,
    get_translation_by_id,
    clear_translation_history,
)
from translation_tts import build_pronunciation_audio
from translation_documents import (
    SUPPORTED_DOCUMENT_EXTENSIONS,
    extract_text_from_document,
    build_translated_text_file,
)
from translation_ocr import (
    extract_text_with_ocr,
    get_ocr_api_key,
)


translation_state = {}
last_translation_time = {}
translation_cache = OrderedDict()

MAX_CACHE_SIZE = 200
MAX_TEXT_INPUT_LENGTH = 12000
MAX_DOCUMENT_TEXT_LENGTH = 30000
TRANSLATION_CHUNK_SIZE = 3000
TELEGRAM_CHUNK_SIZE = 3800
USER_COOLDOWN = 1.2


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
    "🇹🇷 Turkish": "tr",
}

SOURCE_LANGUAGES = {
    "🔎 Auto Detect": "auto",
    **LANGUAGES,
}

LANGUAGE_BY_CODE = {
    code: name
    for name, code in LANGUAGES.items()
}

QUICK_PAIRS = {
    "⚡ English → Tamil": ("en", "ta"),
    "⚡ Tamil → English": ("ta", "en"),
    "⚡ Arabic → Tamil": ("ar", "ta"),
    "⚡ Tamil → Arabic": ("ta", "ar"),
    "⚡ Sinhala → Tamil": ("si", "ta"),
    "⚡ Tamil → Sinhala": ("ta", "si"),
}


def cache_get(key):
    if key not in translation_cache:
        return None

    value = translation_cache.pop(key)
    translation_cache[key] = value

    return value


def cache_save(key, value):
    if key in translation_cache:
        translation_cache.pop(key)

    translation_cache[key] = value

    while len(translation_cache) > MAX_CACHE_SIZE:
        translation_cache.popitem(
            last=False
        )


def split_long_text(
    text,
    max_size=TRANSLATION_CHUNK_SIZE,
):
    text = (text or "").strip()

    if len(text) <= max_size:
        return [text]

    chunks = []
    remaining = text

    while remaining:
        if len(remaining) <= max_size:
            chunks.append(remaining)
            break

        split_position = remaining.rfind(
            "\n",
            0,
            max_size,
        )

        if split_position < max_size // 2:
            split_position = remaining.rfind(
                ". ",
                0,
                max_size,
            )

            if split_position != -1:
                split_position += 1

        if split_position < max_size // 2:
            split_position = remaining.rfind(
                " ",
                0,
                max_size,
            )

        if split_position <= 0:
            split_position = max_size

        chunk = remaining[
            :split_position
        ].strip()

        if chunk:
            chunks.append(chunk)

        remaining = remaining[
            split_position:
        ].strip()

    return chunks


def translate_chunk(
    source,
    target,
    text,
):
    cache_key = (
        source,
        target,
        text,
    )

    cached = cache_get(
        cache_key
    )

    if cached:
        return cached, "Cache"

    google_error = None

    for attempt in range(2):
        try:
            result = GoogleTranslator(
                source=source,
                target=target,
            ).translate(text)

            if result:
                cache_save(
                    cache_key,
                    result,
                )

                return result, "Google"

        except Exception as error:
            google_error = error

            print(
                "Google translation error:",
                repr(error),
            )

            if attempt == 0:
                time.sleep(1.2)

    try:
        result = MyMemoryTranslator(
            source=source,
            target=target,
        ).translate(text)

        if result:
            cache_save(
                cache_key,
                result,
            )

            return result, "MyMemory"

    except Exception as error:
        print(
            "MyMemory translation error:",
            repr(error),
        )

    raise RuntimeError(
        f"Translation services failed: "
        f"{google_error}"
    )


def translate_complete_text(
    source,
    target,
    text,
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
                chunk,
            )
        )

        translated_chunks.append(
            result
        )

        providers.append(
            provider
        )

        if index < len(chunks) - 1:
            time.sleep(0.4)

    final_text = "\n\n".join(
        translated_chunks
    )

    provider_name = (
        providers[0]
        if len(set(providers)) == 1
        else "Multiple"
    )

    return final_text, provider_name


def language_name(code):
    if code == "auto":
        return "🔎 Auto Detect"

    return LANGUAGE_BY_CODE.get(
        code,
        code,
    )


def short_preview(
    text,
    limit=220,
):
    text = " ".join(
        (text or "").split()
    )

    if len(text) <= limit:
        return text

    return (
        text[:limit].rstrip()
        + "…"
    )


def create_result_markup(
    translated_text,
    history_id,
):
    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    buttons = []

    if (
        1
        <= len(translated_text)
        <= 256
    ):
        buttons.append(
            types.InlineKeyboardButton(
                "📋 Copy",
                copy_text=types.CopyTextButton(
                    translated_text
                ),
            )
        )

    if history_id:
        buttons.append(
            types.InlineKeyboardButton(
                "🔊 Listen",
                callback_data=(
                    f"tts:{history_id}"
                ),
            )
        )

    if buttons:
        markup.add(*buttons)
        return markup

    return None


def send_translation_result(
    bot,
    message,
    source,
    target,
    original_text,
    translated_text,
    provider,
    kind="text",
):
    history_id = save_translation(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        source_language=source,
        target_language=target,
        original_text=original_text,
        translated_text=translated_text,
        provider=provider,
        kind=kind,
    )

    header = (
        "✅ Translation Complete\n\n"
        f"From: {language_name(source)}\n"
        f"To: {language_name(target)}\n"
        "\n──────────────\n\n"
    )

    complete_message = (
        header
        + translated_text
    )

    markup = create_result_markup(
        translated_text,
        history_id,
    )

    if len(
        complete_message
    ) <= TELEGRAM_CHUNK_SIZE:
        bot.send_message(
            message.chat.id,
            complete_message,
            reply_markup=markup,
        )
        return

    bot.send_message(
        message.chat.id,
        header,
    )

    chunks = [
        translated_text[
            index:
            index + TELEGRAM_CHUNK_SIZE
        ]
        for index in range(
            0,
            len(translated_text),
            TELEGRAM_CHUNK_SIZE,
        )
    ]

    for index, chunk in enumerate(
        chunks
    ):
        bot.send_message(
            message.chat.id,
            chunk,
            reply_markup=(
                markup
                if index
                == len(chunks) - 1
                else None
            ),
        )


def register_translation_handlers(
    bot,
    show_main_menu,
):

    def show_translation_menu(
        chat_id
    ):
        translation_state[
            chat_id
        ] = {
            "step": "menu"
        }

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
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
                "📄 Translate Document"
            ),
            types.KeyboardButton(
                "🖼 OCR Image → Translate"
            ),
            types.KeyboardButton(
                "🕘 Translation History"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "🌐 Advanced Translator\n\n"
                "⚡ Quick translation\n"
                "⚙️ Custom languages\n"
                "📄 TXT / PDF / DOCX\n"
                "🖼 Image OCR + translation\n"
                "🕘 Translation history\n"
                "🔊 Pronunciation\n\n"
                "Reply to any text with:\n"
                "/tr ta\n"
                "/tr en\n"
                "/tr ar\n"
                "/tr si"
            ),
            reply_markup=markup,
        )

    def show_source_menu(
        chat_id
    ):
        translation_state[
            chat_id
        ] = {
            "step": "source"
        }

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
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
            ),
        )

        bot.send_message(
            chat_id,
            (
                "🌐 Choose the source language.\n\n"
                "If you are unsure, choose:\n"
                "🔎 Auto Detect"
            ),
            reply_markup=markup,
        )

    def show_target_menu(
        chat_id,
        step="target",
        prompt=(
            "Choose the target language:"
        ),
    ):
        state = (
            translation_state
            .setdefault(
                chat_id,
                {}
            )
        )

        state["step"] = step

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        for name in LANGUAGES:
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
            ),
        )

        bot.send_message(
            chat_id,
            prompt,
            reply_markup=markup,
        )

    def show_ready_menu(
        chat_id
    ):
        state = translation_state[
            chat_id
        ]

        state["step"] = "text"

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        if (
            state.get("source")
            != "auto"
        ):
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
                "🕘 Translation History"
            ),
            types.KeyboardButton(
                "🔙 Translator Menu"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "🌐 Translator Ready\n\n"
                f"From: "
                f"{language_name(state['source'])}\n"
                f"To: "
                f"{language_name(state['target'])}\n\n"
                "📝 Send the text you want translated."
            ),
            reply_markup=markup,
        )

    def show_history(
        message
    ):
        rows = get_translation_history(
            message.from_user.id,
            limit=10,
        )

        if not rows:
            bot.send_message(
                message.chat.id,
                (
                    "🕘 Your translation "
                    "history is empty."
                ),
            )
            return

        parts = [
            "🕘 Recent Translation History\n"
        ]

        for number, row in enumerate(
            rows,
            start=1,
        ):
            parts.append(
                (
                    f"\n{number}. "
                    f"{language_name(row['source_language'])}"
                    f" → "
                    f"{language_name(row['target_language'])}"
                    f" [{row.get('kind', 'text')}]\n"
                    f"📝 "
                    f"{short_preview(row['original_text'], 120)}\n"
                    f"✅ "
                    f"{short_preview(row['translated_text'], 160)}"
                )
            )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "🗑 Clear Translation History"
            ),
            types.KeyboardButton(
                "🔙 Translator Menu"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            message.chat.id,
            "\n".join(parts),
            reply_markup=markup,
        )

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

    @bot.message_handler(
        commands=["translate"]
    )
    def translate_command(
        message
    ):
        show_translation_menu(
            message.chat.id
        )

    @bot.message_handler(
        commands=["tr"]
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
                (
                    "❌ Usage:\n\n"
                    "Reply to a message and send:\n"
                    "/tr ta\n"
                    "/tr en\n"
                    "/tr ar\n"
                    "/tr si"
                ),
            )
            return

        target = (
            parts[1]
            .strip()
            .lower()
        )

        if (
            target
            not in LANGUAGE_BY_CODE
        ):
            supported = ", ".join(
                LANGUAGE_BY_CODE.keys()
            )

            bot.send_message(
                chat_id,
                (
                    "❌ Unsupported language.\n\n"
                    f"Supported codes:\n"
                    f"{supported}"
                ),
            )
            return

        replied = (
            message.reply_to_message
        )

        if not replied:
            bot.send_message(
                chat_id,
                (
                    "❌ Reply to a text message first.\n\n"
                    "Then send:\n"
                    "/tr ta"
                ),
            )
            return

        original_text = (
            replied.text
            or replied.caption
        )

        if not original_text:
            bot.send_message(
                chat_id,
                (
                    "❌ That message "
                    "does not contain text."
                ),
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
                    original_text,
                )
            )

            try:
                bot.delete_message(
                    chat_id,
                    status.message_id,
                )
            except Exception:
                pass

            send_translation_result(
                bot=bot,
                message=message,
                source="auto",
                target=target,
                original_text=original_text,
                translated_text=result,
                provider=provider,
                kind="reply",
            )

        except Exception as error:
            print(
                "Quick translation error:",
                repr(error),
            )

            bot.send_message(
                chat_id,
                (
                    "❌ Translation service "
                    "is temporarily unavailable."
                ),
            )

    @bot.callback_query_handler(
        func=lambda call:
        bool(call.data)
        and call.data.startswith(
            "tts:"
        )
    )
    def translation_tts_callback(
        call
    ):
        try:
            translation_id = int(
                call.data.split(
                    ":",
                    1,
                )[1]
            )

        except Exception:
            bot.answer_callback_query(
                call.id,
                "Invalid translation."
            )
            return

        row = get_translation_by_id(
            call.from_user.id,
            translation_id,
        )

        if not row:
            bot.answer_callback_query(
                call.id,
                "Translation not found."
            )
            return

        language = row.get(
            "target_language"
        )

        if (
            language
            not in LANGUAGE_BY_CODE
        ):
            bot.answer_callback_query(
                call.id,
                (
                    "Pronunciation unavailable "
                    "for this language."
                ),
            )
            return

        bot.answer_callback_query(
            call.id,
            "Creating pronunciation…"
        )

        try:
            audio, truncated = (
                build_pronunciation_audio(
                    row.get(
                        "translated_text",
                        ""
                    ),
                    language,
                )
            )

            caption = (
                "🔊 Pronunciation"
            )

            if truncated:
                caption += (
                    "\n\nℹ️ First 2,500 "
                    "characters only."
                )

            bot.send_voice(
                call.message.chat.id,
                audio,
                caption=caption,
            )

        except Exception as error:
            print(
                "TTS error:",
                repr(error),
            )

            bot.send_message(
                call.message.chat.id,
                (
                    "❌ Pronunciation is "
                    "temporarily unavailable."
                ),
            )

    @bot.message_handler(
        content_types=["document"]
    )
    def translation_document_handler(
        message
    ):
        state = translation_state.get(
            message.chat.id
        )

        if not state:
            return

        if state.get("step") not in {
            "waiting_document",
            "waiting_ocr_image",
        }:
            return

        filename = (
            message.document.file_name
            or "document"
        )

        status = bot.send_message(
            message.chat.id,
            "⏳ Reading file..."
        )

        try:
            file_info = bot.get_file(
                message.document.file_id
            )

            file_bytes = (
                bot.download_file(
                    file_info.file_path
                )
            )

            if (
                state.get("step")
                == "waiting_ocr_image"
            ):
                extracted_text = (
                    extract_text_with_ocr(
                        file_bytes,
                        filename,
                    )
                )

                kind = "ocr"

            else:
                extension = (
                    "."
                    + filename.rsplit(
                        ".",
                        1,
                    )[-1].lower()
                    if "." in filename
                    else ""
                )

                if (
                    extension
                    not in SUPPORTED_DOCUMENT_EXTENSIONS
                ):
                    raise ValueError(
                        "Please send TXT, PDF, or DOCX."
                    )

                extracted_text = (
                    extract_text_from_document(
                        file_bytes,
                        filename,
                    )
                )

                if (
                    not extracted_text
                    and extension == ".pdf"
                ):
                    if not get_ocr_api_key():
                        raise RuntimeError(
                            "This PDF appears scanned. "
                            "Configure OCR_SPACE_API_KEY."
                        )

                    extracted_text = (
                        extract_text_with_ocr(
                            file_bytes,
                            filename,
                        )
                    )

                kind = "document"

            if not extracted_text.strip():
                raise RuntimeError(
                    "No readable text found."
                )

            if (
                len(extracted_text)
                > MAX_DOCUMENT_TEXT_LENGTH
            ):
                raise ValueError(
                    (
                        "Document too long. "
                        f"Maximum extracted text: "
                        f"{MAX_DOCUMENT_TEXT_LENGTH:,} "
                        "characters."
                    )
                )

            bot.edit_message_text(
                (
                    "✅ Text extracted.\n"
                    f"📝 "
                    f"{len(extracted_text):,} "
                    "characters\n\n"
                    "⏳ Translating..."
                ),
                message.chat.id,
                status.message_id,
            )

            translated, provider = (
                translate_complete_text(
                    "auto",
                    state["target"],
                    extracted_text,
                )
            )

            output, output_name = (
                build_translated_text_file(
                    translated,
                    filename,
                )
            )

            history_id = (
                save_translation(
                    user_id=(
                        message.from_user.id
                    ),
                    chat_id=(
                        message.chat.id
                    ),
                    source_language="auto",
                    target_language=(
                        state["target"]
                    ),
                    original_text=(
                        extracted_text
                    ),
                    translated_text=(
                        translated
                    ),
                    provider=provider,
                    kind=kind,
                )
            )

            markup = create_result_markup(
                translated,
                history_id,
            )

            bot.send_document(
                message.chat.id,
                output,
                caption=(
                    "✅ Document Translation Complete\n\n"
                    f"To: "
                    f"{language_name(state['target'])}\n"
                    f"Output: {output_name}"
                ),
                reply_markup=markup,
            )

            try:
                bot.delete_message(
                    message.chat.id,
                    status.message_id,
                )
            except Exception:
                pass

        except Exception as error:
            print(
                "Document translation error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                f"❌ {str(error)}",
            )

    @bot.message_handler(
        content_types=["photo"]
    )
    def translation_photo_handler(
        message
    ):
        state = translation_state.get(
            message.chat.id
        )

        if not state:
            return

        if (
            state.get("step")
            != "waiting_ocr_image"
        ):
            return

        status = bot.send_message(
            message.chat.id,
            "🔎 Reading text from image..."
        )

        try:
            photo = message.photo[-1]

            file_info = bot.get_file(
                photo.file_id
            )

            file_bytes = (
                bot.download_file(
                    file_info.file_path
                )
            )

            extracted_text = (
                extract_text_with_ocr(
                    file_bytes,
                    "telegram_photo.jpg",
                )
            )

            if (
                len(extracted_text)
                > MAX_DOCUMENT_TEXT_LENGTH
            ):
                raise ValueError(
                    "OCR text is too long."
                )

            bot.edit_message_text(
                (
                    "✅ OCR complete.\n"
                    f"📝 "
                    f"{len(extracted_text):,} "
                    "characters\n\n"
                    "⏳ Translating..."
                ),
                message.chat.id,
                status.message_id,
            )

            translated, provider = (
                translate_complete_text(
                    "auto",
                    state["target"],
                    extracted_text,
                )
            )

            try:
                bot.delete_message(
                    message.chat.id,
                    status.message_id,
                )
            except Exception:
                pass

            send_translation_result(
                bot=bot,
                message=message,
                source="auto",
                target=state["target"],
                original_text=(
                    extracted_text
                ),
                translated_text=translated,
                provider=provider,
                kind="ocr",
            )

        except Exception as error:
            print(
                "OCR photo error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                (
                    f"❌ OCR failed: "
                    f"{str(error)}"
                ),
            )

    @bot.message_handler(
        func=lambda m:
        m.chat.id
        in translation_state
    )
    def translation_state_handler(
        message
    ):
        chat_id = message.chat.id

        if not message.text:
            return

        text = message.text.strip()

        state = (
            translation_state
            .get(chat_id)
        )

        if not state:
            return

        if text == "🏠 Main Menu":
            translation_state.pop(
                chat_id,
                None,
            )

            show_main_menu(
                chat_id,
                (
                    message.from_user.first_name
                    or "Friend"
                ),
            )
            return

        if text == "🔙 Translator Menu":
            show_translation_menu(
                chat_id
            )
            return

        if text == "🕘 Translation History":
            show_history(
                message
            )
            return

        if (
            text
            == "🗑 Clear Translation History"
        ):
            if clear_translation_history(
                message.from_user.id
            ):
                bot.send_message(
                    chat_id,
                    (
                        "✅ Translation "
                        "history cleared."
                    ),
                )
            else:
                bot.send_message(
                    chat_id,
                    (
                        "❌ Could not clear "
                        "history."
                    ),
                )
            return

        if text == "📄 Translate Document":
            translation_state[
                chat_id
            ] = {
                "step": "document_target"
            }

            show_target_menu(
                chat_id,
                step="document_target",
                prompt=(
                    "📄 Document Translation\n\n"
                    "Choose target language:"
                ),
            )
            return

        if (
            text
            == "🖼 OCR Image → Translate"
        ):
            if not get_ocr_api_key():
                bot.send_message(
                    chat_id,
                    (
                        "❌ OCR is not configured.\n\n"
                        "Add OCR_SPACE_API_KEY "
                        "to Render Environment."
                    ),
                )
                return

            translation_state[
                chat_id
            ] = {
                "step": "ocr_target"
            }

            show_target_menu(
                chat_id,
                step="ocr_target",
                prompt=(
                    "🖼 OCR Image → Translate\n\n"
                    "Choose target language:"
                ),
            )
            return

        if text in QUICK_PAIRS:
            source, target = (
                QUICK_PAIRS[text]
            )

            translation_state[
                chat_id
            ] = {
                "step": "text",
                "source": source,
                "target": target,
            }

            show_ready_menu(
                chat_id
            )
            return

        if text == "⚙️ Choose Languages":
            show_source_menu(
                chat_id
            )
            return

        if text == "🔁 Change Languages":
            show_source_menu(
                chat_id
            )
            return

        if text == "🔄 Swap Languages":
            source = state.get(
                "source"
            )

            target = state.get(
                "target"
            )

            if (
                not source
                or not target
                or source == "auto"
            ):
                bot.send_message(
                    chat_id,
                    (
                        "❌ Auto Detect cannot "
                        "be swapped."
                    ),
                )
                return

            state["source"] = target
            state["target"] = source

            show_ready_menu(
                chat_id
            )
            return

        if (
            state.get("step")
            == "source"
        ):
            if (
                text
                not in SOURCE_LANGUAGES
            ):
                bot.send_message(
                    chat_id,
                    (
                        "❌ Choose a source "
                        "language using buttons."
                    ),
                )
                return

            state["source"] = (
                SOURCE_LANGUAGES[text]
            )

            show_target_menu(
                chat_id
            )
            return

        if state.get("step") in {
            "target",
            "document_target",
            "ocr_target",
        }:
            if text not in LANGUAGES:
                bot.send_message(
                    chat_id,
                    (
                        "❌ Choose target "
                        "language using buttons."
                    ),
                )
                return

            target = LANGUAGES[
                text
            ]

            if (
                state.get("step")
                == "target"
            ):
                source = state.get(
                    "source"
                )

                if (
                    source != "auto"
                    and source == target
                ):
                    bot.send_message(
                        chat_id,
                        (
                            "❌ Source and target "
                            "are the same."
                        ),
                    )
                    return

                state["target"] = target

                show_ready_menu(
                    chat_id
                )
                return

            if (
                state.get("step")
                == "document_target"
            ):
                translation_state[
                    chat_id
                ] = {
                    "step": "waiting_document",
                    "target": target,
                }

                bot.send_message(
                    chat_id,
                    (
                        "📄 Send document now.\n\n"
                        "Supported:\n"
                        "• TXT\n"
                        "• PDF\n"
                        "• DOCX\n\n"
                        "Scanned PDFs use OCR "
                        "when OCR is configured."
                    ),
                )
                return

            if (
                state.get("step")
                == "ocr_target"
            ):
                translation_state[
                    chat_id
                ] = {
                    "step": "waiting_ocr_image",
                    "target": target,
                }

                bot.send_message(
                    chat_id,
                    (
                        "🖼 Send image now.\n\n"
                        "You can send:\n"
                        "• Telegram photo\n"
                        "• JPG / PNG file\n"
                        "• PDF for OCR"
                    ),
                )
                return

        if (
            state.get("step")
            == "text"
        ):
            if (
                len(text)
                > MAX_TEXT_INPUT_LENGTH
            ):
                bot.send_message(
                    chat_id,
                    (
                        "❌ Text too long.\n\n"
                        f"Maximum: "
                        f"{MAX_TEXT_INPUT_LENGTH:,} "
                        "characters"
                    ),
                )
                return

            now = time.time()

            last_time = (
                last_translation_time
                .get(
                    chat_id,
                    0,
                )
            )

            if (
                now - last_time
                < USER_COOLDOWN
            ):
                bot.send_message(
                    chat_id,
                    (
                        "⏳ Please wait a moment "
                        "before another translation."
                    ),
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
                        state["source"],
                        state["target"],
                        text,
                    )
                )

                try:
                    bot.delete_message(
                        chat_id,
                        status.message_id,
                    )
                except Exception:
                    pass

                send_translation_result(
                    bot=bot,
                    message=message,
                    source=state["source"],
                    target=state["target"],
                    original_text=text,
                    translated_text=result,
                    provider=provider,
                    kind="text",
                )

            except Exception as error:
                print(
                    "Translation error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    (
                        "❌ Translation failed. "
                        "Please try again shortly."
                    ),
                )

            return

        if (
            state.get("step")
            == "waiting_document"
        ):
            bot.send_message(
                chat_id,
                (
                    "📄 Upload TXT, PDF, "
                    "or DOCX."
                ),
            )
            return

        if (
            state.get("step")
            == "waiting_ocr_image"
        ):
            bot.send_message(
                chat_id,
                (
                    "🖼 Send an image "
                    "or PDF."
                ),
            )
            return
