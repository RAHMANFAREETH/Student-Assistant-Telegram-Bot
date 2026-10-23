from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase
from subjects import (
    get_subjects,
    get_subject_by_id,
    subject_display,
)
from speech_to_text import (
    stt_is_configured,
    transcribe_audio,
)


voice_note_state = {}


from navigation import GLOBAL_BUTTONS


def get_voice_notes(
    user_id,
    limit=50,
):
    result = (
        supabase
        .table("voice_notes")
        .select(
            "id,user_id,subject_id,title,"
            "telegram_file_id,telegram_file_unique_id,"
            "duration_seconds,transcript,"
            "transcript_language,created_at"
        )
        .eq("user_id", int(user_id))
        .order(
            "created_at",
            desc=True,
        )
        .limit(limit)
        .execute()
    )

    return result.data or []


def get_voice_note(
    user_id,
    note_id,
):
    result = (
        supabase
        .table("voice_notes")
        .select(
            "id,user_id,subject_id,title,"
            "telegram_file_id,telegram_file_unique_id,"
            "duration_seconds,transcript,"
            "transcript_language,created_at"
        )
        .eq("user_id", int(user_id))
        .eq("id", int(note_id))
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def create_voice_note(
    user_id,
    subject_id,
    title,
    file_id,
    file_unique_id,
    duration_seconds,
):
    payload = {
        "user_id": int(user_id),
        "subject_id": subject_id,
        "title": title.strip(),
        "telegram_file_id": file_id,
        "telegram_file_unique_id": (
            file_unique_id
            or None
        ),
        "duration_seconds": (
            int(duration_seconds)
            if duration_seconds is not None
            else None
        ),
    }

    result = (
        supabase
        .table("voice_notes")
        .insert(payload)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def save_transcript(
    user_id,
    note_id,
    transcript,
    language_code=None,
):
    (
        supabase
        .table("voice_notes")
        .update(
            {
                "transcript": transcript,
                "transcript_language": (
                    language_code
                    or None
                ),
            }
        )
        .eq("user_id", int(user_id))
        .eq("id", int(note_id))
        .execute()
    )


def delete_voice_note(
    user_id,
    note_id,
):
    note = get_voice_note(
        user_id,
        note_id,
    )

    if not note:
        return False

    (
        supabase
        .table("voice_notes")
        .delete()
        .eq("user_id", int(user_id))
        .eq("id", int(note_id))
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


def parse_subject_button(text):
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


def register_voice_note_handlers(
    bot,
    show_main_menu,
):

    def show_voice_menu(chat_id):
        voice_note_state.pop(
            chat_id,
            None,
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "➕ Add Voice Note"
            ),
            types.KeyboardButton(
                "🎙 My Voice Notes"
            ),
            types.KeyboardButton(
                "▶️ Play Voice Note"
            ),
            types.KeyboardButton(
                "📝 Transcribe Voice"
            ),
            types.KeyboardButton(
                "📄 View Transcript"
            ),
            types.KeyboardButton(
                "🗑 Delete Voice Note"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        stt_status = (
            "✅ Optional speech-to-text configured"
            if stt_is_configured()
            else (
                "ℹ️ Speech-to-text is optional "
                "and currently disabled"
            )
        )

        bot.send_message(
            chat_id,
            (
                "🎙 Voice Notes\n\n"
                "Save lecture explanations, revision notes, "
                "ideas, and spoken study notes in any language.\n\n"
                "Telegram keeps the audio; "
                "the bot stores the Telegram file ID.\n\n"
                f"{stt_status}"
            ),
            reply_markup=markup,
        )

    def list_voice_notes(message):
        notes = get_voice_notes(
            message.from_user.id,
            limit=40,
        )

        if not notes:
            bot.send_message(
                message.chat.id,
                (
                    "🎙 No voice notes yet.\n\n"
                    "Choose ➕ Add Voice Note."
                ),
            )
            return

        parts = [
            "🎙 MY VOICE NOTES\n"
        ]

        for note in notes:
            duration = (
                note.get(
                    "duration_seconds"
                )
                or 0
            )

            transcript_status = (
                "📝 Transcribed"
                if (
                    note.get(
                        "transcript"
                    )
                    or ""
                ).strip()
                else "🔇 No transcript"
            )

            parts.append(
                (
                    f"\n#{note['id']} "
                    f"{note['title']}\n"
                    f"📚 "
                    f"{subject_name(message.from_user.id, note.get('subject_id'))}\n"
                    f"⏱ {duration} sec\n"
                    f"{transcript_status}\n"
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
        commands=["voice"]
    )
    def voice_command(message):
        show_voice_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🎙 Voice Notes"
    )
    def voice_menu_button(message):
        show_voice_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🎙 My Voice Notes"
    )
    def my_voice_notes(message):
        list_voice_notes(
            message
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "➕ Add Voice Note"
    )
    def add_voice_note(message):
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
                "🔙 Voice Menu"
            )
        )

        voice_note_state[
            message.chat.id
        ] = {
            "step": "subject"
        }

        bot.send_message(
            message.chat.id,
            "📚 Choose a subject for the voice note:",
            reply_markup=markup,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "▶️ Play Voice Note"
    )
    def play_voice_note(message):
        voice_note_state[
            message.chat.id
        ] = {
            "step": "play"
        }

        bot.send_message(
            message.chat.id,
            (
                "▶️ Send the voice-note number.\n"
                "Example: 3"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📝 Transcribe Voice"
    )
    def transcribe_voice_button(message):
        if not stt_is_configured():
            bot.send_message(
                message.chat.id,
                (
                    "ℹ️ Speech-to-text is optional and "
                    "is not configured.\n\n"
                    "Add ASSEMBLYAI_API_KEY to your local "
                    ".env and Render Environment if you want it.\n\n"
                    "Saving and replaying voice notes still works."
                ),
            )
            return

        voice_note_state[
            message.chat.id
        ] = {
            "step": "transcribe"
        }

        bot.send_message(
            message.chat.id,
            (
                "📝 Send the voice-note number "
                "you want to transcribe."
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📄 View Transcript"
    )
    def view_transcript_button(message):
        voice_note_state[
            message.chat.id
        ] = {
            "step": "view_transcript"
        }

        bot.send_message(
            message.chat.id,
            (
                "📄 Send the voice-note number.\n"
                "Example: 3"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🗑 Delete Voice Note"
    )
    def delete_voice_button(message):
        voice_note_state[
            message.chat.id
        ] = {
            "step": "delete"
        }

        bot.send_message(
            message.chat.id,
            (
                "🗑 Send the voice-note number.\n"
                "Example: 3"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔙 Voice Menu"
    )
    def back_voice_menu(message):
        show_voice_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        voice_note_state.get(
            m.chat.id,
            {}
        ).get("step")
        == "waiting_voice",
        content_types=["voice"],
    )
    def voice_upload_handler(message):
        chat_id = message.chat.id
        state = voice_note_state.get(
            chat_id,
            {}
        )

        try:
            note = create_voice_note(
                user_id=message.from_user.id,
                subject_id=state.get(
                    "subject_id"
                ),
                title=state[
                    "title"
                ],
                file_id=message.voice.file_id,
                file_unique_id=(
                    message.voice.file_unique_id
                ),
                duration_seconds=(
                    message.voice.duration
                ),
            )

            voice_note_state.pop(
                chat_id,
                None,
            )

            if not note:
                raise RuntimeError(
                    "Voice note was not saved."
                )

            bot.send_message(
                chat_id,
                (
                    "✅ Voice note saved!\n\n"
                    f"🎙 #{note['id']} "
                    f"{state['title']}\n"
                    f"📚 "
                    f"{subject_name(message.from_user.id, state.get('subject_id'))}\n"
                    f"⏱ {message.voice.duration} sec"
                ),
            )

            show_voice_menu(
                chat_id
            )

        except Exception as error:
            print(
                "Save voice note error:",
                repr(error),
            )

            bot.send_message(
                chat_id,
                "❌ Could not save the voice note.",
            )

    @bot.message_handler(
        func=lambda m:
        m.chat.id in voice_note_state,
        content_types=["text"],
    )
    def voice_state_handler(message):
        chat_id = message.chat.id
        text = (
            message.text
            or ""
        ).strip()

        if text == "🏠 Main Menu":
            voice_note_state.pop(
                chat_id,
                None,
            )

            show_main_menu(
                chat_id,
                message.from_user.first_name
                or "Friend",
            )
            return

        if text == "🔙 Voice Menu":
            show_voice_menu(
                chat_id
            )
            return

        if (
            text.startswith("/")
            or text in GLOBAL_BUTTONS
        ):
            voice_note_state.pop(
                chat_id,
                None,
            )
            return ContinueHandling()

        state = voice_note_state.get(
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

            state[
                "subject_id"
            ] = subject_id

            state[
                "step"
            ] = "title"

            bot.send_message(
                chat_id,
                (
                    "📝 Give this voice note a title.\n\n"
                    "Example:\n"
                    "Database Lecture 3"
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
            state["step"] = "waiting_voice"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
            )

            markup.add(
                types.KeyboardButton(
                    "🔙 Voice Menu"
                ),
                types.KeyboardButton(
                    "🏠 Main Menu"
                ),
            )

            bot.send_message(
                chat_id,
                (
                    "🎙 Now send a Telegram voice message.\n\n"
                    "Use Telegram's microphone button."
                ),
                reply_markup=markup,
            )
            return

        if step == "waiting_voice":
            bot.send_message(
                chat_id,
                (
                    "🎙 Please send a Telegram voice message, "
                    "not text."
                ),
            )
            return

        if step in {
            "play",
            "transcribe",
            "view_transcript",
            "delete",
        }:
            try:
                note_id = int(
                    text.replace(
                        "#",
                        ""
                    )
                )
            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Send only the voice-note number.",
                )
                return

            note = get_voice_note(
                message.from_user.id,
                note_id,
            )

            if not note:
                bot.send_message(
                    chat_id,
                    "❌ Voice note not found.",
                )
                return

            if step == "play":
                voice_note_state.pop(
                    chat_id,
                    None,
                )

                bot.send_voice(
                    chat_id,
                    note[
                        "telegram_file_id"
                    ],
                    caption=(
                        f"🎙 #{note['id']} "
                        f"{note['title']}\n"
                        f"📚 "
                        f"{subject_name(message.from_user.id, note.get('subject_id'))}"
                    ),
                )

                show_voice_menu(
                    chat_id
                )
                return

            if step == "view_transcript":
                voice_note_state.pop(
                    chat_id,
                    None,
                )

                transcript = (
                    note.get(
                        "transcript"
                    )
                    or ""
                ).strip()

                if not transcript:
                    bot.send_message(
                        chat_id,
                        (
                            "📄 This voice note does not "
                            "have a transcript yet."
                        ),
                    )
                else:
                    language = (
                        note.get(
                            "transcript_language"
                        )
                        or "auto"
                    )

                    for start in range(
                        0,
                        len(transcript),
                        3600,
                    ):
                        prefix = (
                            f"📄 {note['title']}\n"
                            f"🌐 Language: {language}\n\n"
                            if start == 0
                            else ""
                        )

                        bot.send_message(
                            chat_id,
                            prefix
                            + transcript[
                                start:
                                start + 3600
                            ],
                        )

                show_voice_menu(
                    chat_id
                )
                return

            if step == "delete":
                try:
                    success = delete_voice_note(
                        message.from_user.id,
                        note_id,
                    )

                    if not success:
                        raise RuntimeError(
                            "Voice note not found."
                        )

                    voice_note_state.pop(
                        chat_id,
                        None,
                    )

                    bot.send_message(
                        chat_id,
                        "✅ Voice note deleted.",
                    )

                    show_voice_menu(
                        chat_id
                    )

                except Exception as error:
                    print(
                        "Delete voice note error:",
                        repr(error),
                    )

                    bot.send_message(
                        chat_id,
                        "❌ Could not delete the voice note.",
                    )

                return

            if step == "transcribe":
                voice_note_state.pop(
                    chat_id,
                    None,
                )

                status_message = bot.send_message(
                    chat_id,
                    (
                        "📝 Transcribing voice note...\n"
                        "This may take a little time."
                    ),
                )

                try:
                    file_info = bot.get_file(
                        note[
                            "telegram_file_id"
                        ]
                    )

                    audio_bytes = bot.download_file(
                        file_info.file_path
                    )

                    result = transcribe_audio(
                        audio_bytes
                    )

                    transcript = (
                        result.get(
                            "text"
                        )
                        or ""
                    ).strip()

                    if not transcript:
                        raise RuntimeError(
                            "No speech text was detected."
                        )

                    save_transcript(
                        user_id=message.from_user.id,
                        note_id=note_id,
                        transcript=transcript,
                        language_code=(
                            result.get(
                                "language_code"
                            )
                        ),
                    )

                    try:
                        bot.delete_message(
                            chat_id,
                            status_message.message_id,
                        )
                    except Exception:
                        pass

                    bot.send_message(
                        chat_id,
                        (
                            "✅ Transcription completed!\n\n"
                            f"🎙 {note['title']}\n"
                            f"🌐 Language: "
                            f"{result.get('language_code') or 'auto'}"
                        ),
                    )

                    for start in range(
                        0,
                        len(transcript),
                        3600,
                    ):
                        bot.send_message(
                            chat_id,
                            transcript[
                                start:
                                start + 3600
                            ],
                        )

                except Exception as error:
                    print(
                        "Voice transcription error:",
                        repr(error),
                    )

                    bot.send_message(
                        chat_id,
                        (
                            "❌ Transcription failed:\n"
                            f"{str(error)}"
                        ),
                    )

                show_voice_menu(
                    chat_id
                )
                return
