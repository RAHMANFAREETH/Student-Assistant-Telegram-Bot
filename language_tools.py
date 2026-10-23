import io
import random
import re

from gtts import gTTS
from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase
from subjects import (
    get_subjects,
    get_subject_by_id,
    subject_display,
)


language_state = {}


LANGUAGES = {
    "தமிழ்": {
        "code": "ta",
        "name": "Tamil",
        "emoji": "🇱🇰",
    },
    "English": {
        "code": "en",
        "name": "English",
        "emoji": "🇬🇧",
    },
    "සිංහල": {
        "code": "si",
        "name": "Sinhala",
        "emoji": "🇱🇰",
    },
    "العربية": {
        "code": "ar",
        "name": "Arabic",
        "emoji": "🇸🇦",
    },
}


CODE_TO_LANGUAGE = {
    value["code"]: value
    for value in LANGUAGES.values()
}


ARABIC_DIACRITICS = re.compile(
    (
        r"[\u0610-\u061A"
        r"\u064B-\u065F"
        r"\u0670"
        r"\u06D6-\u06ED]"
    )
)


from navigation import GLOBAL_BUTTONS


def language_info(
    code
):
    return CODE_TO_LANGUAGE.get(
        code,
        {
            "code": code,
            "name": code,
            "emoji": "🌐",
        },
    )


def strip_arabic_harakat(
    text
):
    return ARABIC_DIACRITICS.sub(
        "",
        text or "",
    )


def normalize_text(
    text
):
    value = (
        text
        or ""
    ).replace(
        "\u0640",
        "",
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def text_stats(
    language_code,
    text,
):
    cleaned = normalize_text(
        text
    )

    words = [
        token
        for token in cleaned.split()
        if token
    ]

    non_space_chars = len(
        re.sub(
            r"\s+",
            "",
            cleaned,
        )
    )

    result = {
        "cleaned": cleaned,
        "words": len(words),
        "characters": len(cleaned),
        "non_space_characters": (
            non_space_chars
        ),
    }

    if language_code == "ar":
        result[
            "without_harakat"
        ] = strip_arabic_harakat(
            cleaned
        )

    return result


def create_tts(
    text,
    language_code,
):
    audio = io.BytesIO()

    tts = gTTS(
        text=text,
        lang=language_code,
        slow=False,
    )

    tts.write_to_fp(
        audio
    )

    audio.seek(0)
    audio.name = (
        f"{language_code}_pronunciation.mp3"
    )

    return audio


def get_vocabulary(
    user_id,
    language_code=None,
    limit=100,
):
    query = (
        supabase
        .table("language_vocabulary")
        .select(
            "id,user_id,subject_id,language_code,"
            "language_name,term,meaning,example_text,"
            "times_seen,correct_count,wrong_count,"
            "mastered,created_at"
        )
        .eq("user_id", int(user_id))
    )

    if language_code:
        query = query.eq(
            "language_code",
            language_code,
        )

    result = (
        query
        .order(
            "created_at",
            desc=True,
        )
        .limit(limit)
        .execute()
    )

    return result.data or []


def get_vocab_item(
    user_id,
    vocab_id,
):
    result = (
        supabase
        .table("language_vocabulary")
        .select(
            "id,user_id,subject_id,language_code,"
            "language_name,term,meaning,example_text,"
            "times_seen,correct_count,wrong_count,mastered"
        )
        .eq("user_id", int(user_id))
        .eq("id", int(vocab_id))
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def create_vocab_item(
    user_id,
    subject_id,
    language_code,
    language_name,
    term,
    meaning,
    example_text=None,
):
    result = (
        supabase
        .table("language_vocabulary")
        .insert(
            {
                "user_id": int(user_id),
                "subject_id": subject_id,
                "language_code": language_code,
                "language_name": language_name,
                "term": normalize_text(
                    term
                ),
                "meaning": meaning.strip(),
                "example_text": (
                    normalize_text(
                        example_text
                    )
                    if example_text
                    else None
                ),
            }
        )
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def delete_vocab_item(
    user_id,
    vocab_id,
):
    item = get_vocab_item(
        user_id,
        vocab_id,
    )

    if not item:
        return False

    (
        supabase
        .table("language_vocabulary")
        .delete()
        .eq("user_id", int(user_id))
        .eq("id", int(vocab_id))
        .execute()
    )

    return True


def update_vocab_review(
    user_id,
    vocab_id,
    knew_answer,
):
    item = get_vocab_item(
        user_id,
        vocab_id,
    )

    if not item:
        return False

    times_seen = int(
        item.get(
            "times_seen"
        )
        or 0
    ) + 1

    correct = int(
        item.get(
            "correct_count"
        )
        or 0
    )

    wrong = int(
        item.get(
            "wrong_count"
        )
        or 0
    )

    if knew_answer:
        correct += 1
    else:
        wrong += 1

    mastered = (
        correct >= 3
        and correct >= (
            wrong * 2
        )
    )

    (
        supabase
        .table("language_vocabulary")
        .update(
            {
                "times_seen": times_seen,
                "correct_count": correct,
                "wrong_count": wrong,
                "mastered": mastered,
            }
        )
        .eq("user_id", int(user_id))
        .eq("id", int(vocab_id))
        .execute()
    )

    return True


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


def parse_subject_button(
    text
):
    if text == "⏭ No Subject":
        return None

    if not text.startswith(
        "📚 #"
    ):
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


def make_language_keyboard(
    back_button="🔙 Language Menu",
):
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2,
    )

    for label in LANGUAGES:
        markup.add(
            types.KeyboardButton(
                label
            )
        )

    markup.add(
        types.KeyboardButton(
            back_button
        )
    )

    return markup


def register_language_tool_handlers(
    bot,
    show_main_menu,
):

    def show_language_menu(
        chat_id
    ):
        language_state.pop(
            chat_id,
            None,
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "➕ Add Vocabulary"
            ),
            types.KeyboardButton(
                "📚 My Vocabulary"
            ),
            types.KeyboardButton(
                "🎯 Practice Vocabulary"
            ),
            types.KeyboardButton(
                "🔊 Pronunciation"
            ),
            types.KeyboardButton(
                "🔤 Text Tools"
            ),
            types.KeyboardButton(
                "🗑 Delete Vocabulary"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "🌍 Language Study Tools\n\n"
                "Supported now:\n"
                "🇱🇰 தமிழ்\n"
                "🇬🇧 English\n"
                "🇱🇰 සිංහල\n"
                "🇸🇦 العربية\n\n"
                "Save vocabulary, practise meanings, "
                "hear pronunciation and inspect text."
            ),
            reply_markup=markup,
        )

    def send_practice_card(
        message,
        language_code,
    ):
        items = get_vocabulary(
            message.from_user.id,
            language_code=language_code,
            limit=100,
        )

        if not items:
            info = language_info(
                language_code
            )

            bot.send_message(
                message.chat.id,
                (
                    f"{info['emoji']} No {info['name']} "
                    "vocabulary saved yet."
                ),
            )
            return

        learning = [
            item
            for item in items
            if not item.get(
                "mastered"
            )
        ]

        pool = (
            learning
            if learning
            else items
        )

        item = random.choice(
            pool
        )

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "👀 Show Meaning",
                callback_data=(
                    f"lang_show:{item['id']}"
                ),
            )
        )

        info = language_info(
            language_code
        )

        bot.send_message(
            message.chat.id,
            (
                f"{info['emoji']} {info['name'].upper()} VOCABULARY\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"❓ {item['term']}\n\n"
                "Think of the meaning, then press "
                "👀 Show Meaning."
            ),
            reply_markup=markup,
        )

    @bot.message_handler(
        commands=["languages"]
    )
    def language_command(
        message
    ):
        show_language_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🌍 Language Tools"
    )
    def language_button(
        message
    ):
        show_language_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "➕ Add Vocabulary"
    )
    def add_vocab(
        message
    ):
        language_state[
            message.chat.id
        ] = {
            "step": "add_language"
        }

        bot.send_message(
            message.chat.id,
            "🌐 Choose the vocabulary language:",
            reply_markup=make_language_keyboard(),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📚 My Vocabulary"
    )
    def my_vocab(
        message
    ):
        items = get_vocabulary(
            message.from_user.id,
            limit=60,
        )

        if not items:
            bot.send_message(
                message.chat.id,
                "📚 No vocabulary saved yet.",
            )
            return

        parts = [
            "📚 MY VOCABULARY\n"
        ]

        for item in items:
            info = language_info(
                item.get(
                    "language_code"
                )
            )

            status = (
                "⭐ Mastered"
                if item.get(
                    "mastered"
                )
                else "📖 Learning"
            )

            example = (
                item.get(
                    "example_text"
                )
                or ""
            ).strip()

            example_line = (
                f"\n📝 {example}"
                if example
                else ""
            )

            parts.append(
                (
                    f"\n#{item['id']} "
                    f"{info['emoji']} {item['language_name']} "
                    f"— {status}\n"
                    f"🔤 {item['term']}\n"
                    f"💡 {item['meaning']}\n"
                    f"📚 "
                    f"{subject_name(message.from_user.id, item.get('subject_id'))}"
                    f"{example_line}\n"
                )
            )

        text = "\n".join(
            parts
        )

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
        m.text == "🎯 Practice Vocabulary"
    )
    def practice_vocab(
        message
    ):
        language_state[
            message.chat.id
        ] = {
            "step": "practice_language"
        }

        bot.send_message(
            message.chat.id,
            "🌐 Choose a language to practise:",
            reply_markup=make_language_keyboard(),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔊 Pronunciation"
    )
    def pronunciation(
        message
    ):
        language_state[
            message.chat.id
        ] = {
            "step": "pronunciation_language"
        }

        bot.send_message(
            message.chat.id,
            "🌐 Choose the language:",
            reply_markup=make_language_keyboard(),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔤 Text Tools"
    )
    def text_tools(
        message
    ):
        language_state[
            message.chat.id
        ] = {
            "step": "text_tools_language"
        }

        bot.send_message(
            message.chat.id,
            "🌐 Choose the text language:",
            reply_markup=make_language_keyboard(),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🗑 Delete Vocabulary"
    )
    def delete_vocab(
        message
    ):
        language_state[
            message.chat.id
        ] = {
            "step": "delete"
        }

        bot.send_message(
            message.chat.id,
            (
                "🗑 Send the vocabulary number.\n"
                "Example: 5"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔙 Language Menu"
    )
    def back_language(
        message
    ):
        show_language_menu(
            message.chat.id
        )

    @bot.callback_query_handler(
        func=lambda call:
        bool(call.data)
        and call.data.startswith(
            "lang_show:"
        )
    )
    def show_meaning(
        call
    ):
        try:
            vocab_id = int(
                call.data.split(
                    ":",
                    1,
                )[1]
            )

            item = get_vocab_item(
                call.from_user.id,
                vocab_id,
            )

            if not item:
                bot.answer_callback_query(
                    call.id,
                    "Vocabulary item not found."
                )
                return

            markup = types.InlineKeyboardMarkup(
                row_width=2
            )

            markup.add(
                types.InlineKeyboardButton(
                    "✅ I knew it",
                    callback_data=(
                        f"lang_rate:{vocab_id}:1"
                    ),
                ),
                types.InlineKeyboardButton(
                    "🔁 Practice again",
                    callback_data=(
                        f"lang_rate:{vocab_id}:0"
                    ),
                ),
            )

            example = (
                item.get(
                    "example_text"
                )
                or ""
            ).strip()

            example_text = (
                f"\n\n📝 {example}"
                if example
                else ""
            )

            info = language_info(
                item.get(
                    "language_code"
                )
            )

            bot.edit_message_text(
                (
                    f"{info['emoji']} {item['language_name'].upper()} VOCABULARY\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    f"🔤 {item['term']}\n\n"
                    f"💡 {item['meaning']}"
                    f"{example_text}"
                ),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
            )

            bot.answer_callback_query(
                call.id
            )

        except Exception as error:
            print(
                "Show vocabulary meaning error:",
                repr(error),
            )

            bot.answer_callback_query(
                call.id,
                "Could not open the vocabulary item."
            )

    @bot.callback_query_handler(
        func=lambda call:
        bool(call.data)
        and call.data.startswith(
            "lang_rate:"
        )
    )
    def rate_vocab(
        call
    ):
        try:
            _, vocab_id, knew = (
                call.data.split(
                    ":"
                )
            )

            vocab_id = int(
                vocab_id
            )

            item = get_vocab_item(
                call.from_user.id,
                vocab_id,
            )

            if not item:
                bot.answer_callback_query(
                    call.id,
                    "Vocabulary item not found."
                )
                return

            update_vocab_review(
                user_id=call.from_user.id,
                vocab_id=vocab_id,
                knew_answer=(
                    knew == "1"
                ),
            )

            bot.answer_callback_query(
                call.id,
                (
                    "✅ Progress saved"
                    if knew == "1"
                    else "🔁 Added to practice"
                ),
            )

            class PracticeMessage:
                pass

            pseudo = PracticeMessage()
            pseudo.chat = call.message.chat
            pseudo.from_user = call.from_user

            send_practice_card(
                pseudo,
                item[
                    "language_code"
                ],
            )

        except Exception as error:
            print(
                "Vocabulary review error:",
                repr(error),
            )

            bot.answer_callback_query(
                call.id,
                "Could not save progress."
            )

    @bot.message_handler(
        func=lambda m:
        m.chat.id in language_state,
        content_types=["text"],
    )
    def language_state_handler(
        message
    ):
        chat_id = message.chat.id
        text = (
            message.text
            or ""
        ).strip()

        if text == "🏠 Main Menu":
            language_state.pop(
                chat_id,
                None,
            )

            show_main_menu(
                chat_id,
                message.from_user.first_name
                or "Friend",
            )
            return

        if text == "🔙 Language Menu":
            show_language_menu(
                chat_id
            )
            return

        if (
            text.startswith("/")
            or text in GLOBAL_BUTTONS
        ):
            language_state.pop(
                chat_id,
                None,
            )
            return ContinueHandling()

        state = language_state.get(
            chat_id,
            {}
        )

        step = state.get(
            "step"
        )

        if step in {
            "add_language",
            "practice_language",
            "pronunciation_language",
            "text_tools_language",
        }:
            if text not in LANGUAGES:
                bot.send_message(
                    chat_id,
                    "❌ Choose a language using the buttons.",
                )
                return

            selected = LANGUAGES[
                text
            ]

            if step == "practice_language":
                language_state.pop(
                    chat_id,
                    None,
                )

                send_practice_card(
                    message,
                    selected[
                        "code"
                    ],
                )
                return

            if step == "pronunciation_language":
                state[
                    "language_code"
                ] = selected[
                    "code"
                ]

                state[
                    "language_name"
                ] = selected[
                    "name"
                ]

                state[
                    "step"
                ] = "pronunciation_text"

                bot.send_message(
                    chat_id,
                    (
                        f"🔊 Send {selected['name']} text "
                        "you want to hear."
                    ),
                )
                return

            if step == "text_tools_language":
                state[
                    "language_code"
                ] = selected[
                    "code"
                ]

                state[
                    "language_name"
                ] = selected[
                    "name"
                ]

                state[
                    "step"
                ] = "text_tools_text"

                bot.send_message(
                    chat_id,
                    (
                        f"🔤 Send the {selected['name']} text."
                    ),
                )
                return

            state[
                "language_code"
            ] = selected[
                "code"
            ]

            state[
                "language_name"
            ] = selected[
                "name"
            ]

            state[
                "step"
            ] = "subject"

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
                    "🔙 Language Menu"
                )
            )

            bot.send_message(
                chat_id,
                "📚 Choose a subject:",
                reply_markup=markup,
            )
            return

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

            state[
                "subject_id"
            ] = subject_id

            state[
                "step"
            ] = "term"

            bot.send_message(
                chat_id,
                (
                    f"🔤 Send the {state['language_name']} "
                    "word or phrase."
                ),
            )
            return

        if step == "term":
            if len(text) < 1:
                bot.send_message(
                    chat_id,
                    "❌ Term cannot be empty.",
                )
                return

            state[
                "term"
            ] = text

            state[
                "step"
            ] = "meaning"

            bot.send_message(
                chat_id,
                (
                    "💡 Send the meaning.\n\n"
                    "The meaning can be in any language."
                ),
            )
            return

        if step == "meaning":
            if len(text) < 1:
                bot.send_message(
                    chat_id,
                    "❌ Meaning cannot be empty.",
                )
                return

            state[
                "meaning"
            ] = text

            state[
                "step"
            ] = "example"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
            )

            markup.add(
                types.KeyboardButton(
                    "⏭ Skip Example"
                ),
                types.KeyboardButton(
                    "🔙 Language Menu"
                ),
            )

            bot.send_message(
                chat_id,
                (
                    "📝 Send an example sentence.\n\n"
                    "Or choose ⏭ Skip Example."
                ),
                reply_markup=markup,
            )
            return

        if step == "example":
            example = (
                None
                if text == "⏭ Skip Example"
                else text
            )

            try:
                item = create_vocab_item(
                    user_id=message.from_user.id,
                    subject_id=state.get(
                        "subject_id"
                    ),
                    language_code=state[
                        "language_code"
                    ],
                    language_name=state[
                        "language_name"
                    ],
                    term=state[
                        "term"
                    ],
                    meaning=state[
                        "meaning"
                    ],
                    example_text=example,
                )

                language_state.pop(
                    chat_id,
                    None,
                )

                if not item:
                    raise RuntimeError(
                        "Vocabulary item was not saved."
                    )

                info = language_info(
                    item[
                        "language_code"
                    ]
                )

                bot.send_message(
                    chat_id,
                    (
                        "✅ Vocabulary saved!\n\n"
                        f"{info['emoji']} {state['term']}\n"
                        f"💡 {state['meaning']}"
                    ),
                )

                show_language_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Create vocabulary error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not save vocabulary.",
                )

            return

        if step == "pronunciation_text":
            try:
                audio = create_tts(
                    text=text,
                    language_code=state[
                        "language_code"
                    ],
                )

                language_state.pop(
                    chat_id,
                    None,
                )

                bot.send_voice(
                    chat_id,
                    audio,
                    caption=(
                        f"🔊 {state['language_name']}\n"
                        f"{text}"
                    ),
                )

                show_language_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Pronunciation error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    (
                        "❌ Could not create pronunciation audio."
                    ),
                )

            return

        if step == "text_tools_text":
            stats = text_stats(
                state[
                    "language_code"
                ],
                text,
            )

            language_name = state[
                "language_name"
            ]

            language_state.pop(
                chat_id,
                None,
            )

            extra = ""

            if "without_harakat" in stats:
                extra = (
                    "\n\n🔡 Without ḥarakāt:\n"
                    f"{stats['without_harakat']}"
                )

            bot.send_message(
                chat_id,
                (
                    f"🔤 {language_name.upper()} TEXT TOOLS\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"

                    "📝 Cleaned text:\n"
                    f"{stats['cleaned']}"
                    f"{extra}\n\n"

                    f"📊 Words: {stats['words']}\n"
                    f"🔤 Characters: {stats['characters']}\n"
                    f"🔡 Characters without spaces: "
                    f"{stats['non_space_characters']}"
                ),
            )

            show_language_menu(
                chat_id
            )
            return

        if step == "delete":
            try:
                vocab_id = int(
                    text.replace(
                        "#",
                        ""
                    )
                )
            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Send only the vocabulary number.",
                )
                return

            try:
                success = delete_vocab_item(
                    message.from_user.id,
                    vocab_id,
                )

                if not success:
                    bot.send_message(
                        chat_id,
                        "❌ Vocabulary item not found.",
                    )
                    return

                language_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    "✅ Vocabulary deleted.",
                )

                show_language_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Delete vocabulary error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not delete vocabulary.",
                )

            return
