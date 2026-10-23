import re
from pathlib import Path

from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase
from subjects import (
    get_subjects,
    get_subject_by_id,
    subject_display,
)
from translation_documents import (
    SUPPORTED_DOCUMENT_EXTENSIONS,
    extract_text_from_document,
)
from translation_ocr import (
    extract_text_with_ocr,
    get_ocr_api_key,
)


material_state = {}

MAX_MATERIAL_CHARS = 100000
TELEGRAM_CHUNK_SIZE = 3600


from navigation import GLOBAL_BUTTONS


STOPWORDS = {
    # English
    "the", "and", "for", "that", "this", "with", "from", "have", "has",
    "was", "were", "are", "is", "be", "been", "being", "into", "about",
    "their", "there", "they", "them", "then", "than", "which", "when",
    "where", "what", "who", "why", "how", "can", "could", "would",
    "should", "will", "shall", "may", "might", "must", "not", "but",
    "also", "such", "these", "those", "its", "our", "your", "you",
    "his", "her", "him", "she", "he", "we", "it", "of", "to", "in",
    "on", "at", "by", "as", "or", "an", "a",
}


def get_materials(
    user_id,
    limit=50,
):
    result = (
        supabase
        .table("study_materials")
        .select(
            "id,user_id,subject_id,title,file_name,"
            "file_type,extracted_chars,created_at"
        )
        .eq("user_id", int(user_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return result.data or []


def get_material(
    user_id,
    material_id,
):
    result = (
        supabase
        .table("study_materials")
        .select(
            "id,user_id,subject_id,title,file_name,"
            "file_type,extracted_text,extracted_chars,created_at"
        )
        .eq("user_id", int(user_id))
        .eq("id", int(material_id))
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def save_material(
    user_id,
    subject_id,
    title,
    file_name,
    file_type,
    extracted_text,
):
    payload = {
        "user_id": int(user_id),
        "subject_id": subject_id,
        "title": title.strip(),
        "file_name": file_name,
        "file_type": file_type,
        "extracted_text": extracted_text,
        "extracted_chars": len(extracted_text),
    }

    return (
        supabase
        .table("study_materials")
        .insert(payload)
        .execute()
    )


def delete_material(
    user_id,
    material_id,
):
    material = get_material(
        user_id,
        material_id,
    )

    if not material:
        return False

    (
        supabase
        .table("study_materials")
        .delete()
        .eq("user_id", int(user_id))
        .eq("id", int(material_id))
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


def split_sentences(text):
    clean = re.sub(
        r"\s+",
        " ",
        (text or "").strip(),
    )

    if not clean:
        return []

    parts = re.split(
        r"(?<=[.!?؟。])\s+",
        clean,
    )

    sentences = [
        sentence.strip()
        for sentence in parts
        if len(sentence.strip()) >= 25
    ]

    if not sentences and clean:
        sentences = [
            clean[
                index:
                index + 500
            ].strip()
            for index in range(
                0,
                len(clean),
                500,
            )
            if clean[
                index:
                index + 500
            ].strip()
        ]

    return sentences


def tokenize_words(text):
    return [
        word.lower()
        for word in re.findall(
            r"[^\W\d_]{3,}",
            text,
            flags=re.UNICODE,
        )
        if word.lower()
        not in STOPWORDS
    ]


def summarize_text(
    text,
    max_sentences=7,
):
    sentences = split_sentences(
        text
    )

    if not sentences:
        return (
            "No readable sentences were found."
        )

    if len(sentences) <= max_sentences:
        return "\n\n".join(
            sentences
        )

    frequencies = {}

    for word in tokenize_words(
        text
    ):
        frequencies[word] = (
            frequencies.get(
                word,
                0,
            )
            + 1
        )

    if not frequencies:
        return "\n\n".join(
            sentences[:max_sentences]
        )

    scored = []

    for index, sentence in enumerate(
        sentences
    ):
        words = tokenize_words(
            sentence
        )

        if not words:
            continue

        score = sum(
            frequencies.get(
                word,
                0,
            )
            for word in words
        ) / max(
            len(words),
            1,
        )

        # Slight preference for earlier sentences.
        position_bonus = max(
            0,
            1 - (
                index
                / max(
                    len(sentences),
                    1,
                )
            )
        ) * 0.15

        scored.append(
            (
                score + position_bonus,
                index,
                sentence,
            )
        )

    top = sorted(
        scored,
        reverse=True,
    )[
        :max_sentences
    ]

    selected = sorted(
        top,
        key=lambda item:
        item[1],
    )

    return "\n\n".join(
        item[2]
        for item in selected
    )


def key_points(
    text,
    max_points=10,
):
    summary = summarize_text(
        text,
        max_sentences=max_points,
    )

    points = split_sentences(
        summary
    )

    if not points:
        points = [
            line.strip()
            for line in summary.splitlines()
            if line.strip()
        ]

    return points[
        :max_points
    ]


def send_long_text(
    bot,
    chat_id,
    text,
    heading=None,
):
    if heading:
        bot.send_message(
            chat_id,
            heading,
        )

    for start in range(
        0,
        len(text),
        TELEGRAM_CHUNK_SIZE,
    ):
        bot.send_message(
            chat_id,
            text[
                start:
                start + TELEGRAM_CHUNK_SIZE
            ],
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


def register_study_material_handlers(
    bot,
    show_main_menu,
):

    def show_material_menu(
        chat_id
    ):
        material_state.pop(
            chat_id,
            None,
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "➕ Add Material"
            ),
            types.KeyboardButton(
                "📂 My Materials"
            ),
            types.KeyboardButton(
                "📖 Read Material"
            ),
            types.KeyboardButton(
                "🔎 Search Materials"
            ),
            types.KeyboardButton(
                "🧾 Summarize Material"
            ),
            types.KeyboardButton(
                "✨ Key Points"
            ),
            types.KeyboardButton(
                "🗑 Delete Material"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "📚 Study Materials\n\n"
                "Save lecture documents by subject, "
                "search them, read extracted text, "
                "and create grounded summaries/key points.\n\n"
                "Supported uploads:\n"
                "• PDF\n"
                "• DOCX\n"
                "• TXT"
            ),
            reply_markup=markup,
        )

    def show_material_list(
        message
    ):
        try:
            materials = get_materials(
                message.from_user.id,
                limit=40,
            )

            if not materials:
                bot.send_message(
                    message.chat.id,
                    (
                        "📂 No study materials yet.\n\n"
                        "Choose ➕ Add Material."
                    ),
                )
                return

            parts = [
                "📂 My Study Materials\n"
            ]

            for material in materials:
                parts.append(
                    (
                        f"\n#{material['id']} "
                        f"{material['title']}\n"
                        f"📚 "
                        f"{subject_name(message.from_user.id, material.get('subject_id'))}\n"
                        f"📄 {material['file_type'].upper()} | "
                        f"{material.get('extracted_chars', 0):,} chars\n"
                    )
                )

            send_long_text(
                bot,
                message.chat.id,
                "\n".join(parts),
            )

        except Exception as error:
            print(
                "List materials error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not load study materials.",
            )

    @bot.message_handler(
        commands=["materials"]
    )
    def materials_command(
        message
    ):
        show_material_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📚 Study Materials"
    )
    def materials_button(
        message
    ):
        show_material_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "➕ Add Material"
    )
    def add_material_button(
        message
    ):
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
                "🔙 Materials Menu"
            )
        )

        material_state[
            message.chat.id
        ] = {
            "step": "choose_subject"
        }

        bot.send_message(
            message.chat.id,
            (
                "📚 Choose a subject for this material.\n\n"
                "You can also choose ⏭ No Subject."
            ),
            reply_markup=markup,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📂 My Materials"
    )
    def my_materials_button(
        message
    ):
        show_material_list(
            message
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📖 Read Material"
    )
    def read_material_button(
        message
    ):
        material_state[
            message.chat.id
        ] = {
            "step": "read_id"
        }

        bot.send_message(
            message.chat.id,
            (
                "📖 Send the material number.\n"
                "Example: 3"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔎 Search Materials"
    )
    def search_material_button(
        message
    ):
        material_state[
            message.chat.id
        ] = {
            "step": "search"
        }

        bot.send_message(
            message.chat.id,
            (
                "🔎 Send a word or phrase to search "
                "inside your saved materials."
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🧾 Summarize Material"
    )
    def summarize_material_button(
        message
    ):
        material_state[
            message.chat.id
        ] = {
            "step": "summary_id"
        }

        bot.send_message(
            message.chat.id,
            (
                "🧾 Send the material number you want summarized.\n"
                "Example: 3"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "✨ Key Points"
    )
    def key_points_button(
        message
    ):
        material_state[
            message.chat.id
        ] = {
            "step": "keypoints_id"
        }

        bot.send_message(
            message.chat.id,
            (
                "✨ Send the material number.\n"
                "Example: 3"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🗑 Delete Material"
    )
    def delete_material_button(
        message
    ):
        material_state[
            message.chat.id
        ] = {
            "step": "delete_id"
        }

        bot.send_message(
            message.chat.id,
            (
                "🗑 Send the material number to delete.\n"
                "Example: 3"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔙 Materials Menu"
    )
    def materials_back(
        message
    ):
        show_material_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        material_state.get(
            m.chat.id,
            {}
        ).get("step")
        == "waiting_file",
        content_types=["document"],
    )
    def material_document_handler(
        message
    ):
        chat_id = message.chat.id
        state = material_state.get(
            chat_id,
            {}
        )

        filename = (
            message.document.file_name
            or "material"
        )

        extension = Path(
            filename
        ).suffix.lower()

        if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
            bot.send_message(
                chat_id,
                (
                    "❌ Unsupported file.\n\n"
                    "Please upload PDF, DOCX, or TXT."
                ),
            )
            return

        status = bot.send_message(
            chat_id,
            "📄 Reading study material..."
        )

        try:
            info = bot.get_file(
                message.document.file_id
            )

            file_bytes = bot.download_file(
                info.file_path
            )

            extracted = extract_text_from_document(
                file_bytes,
                filename,
            )

            # OCR fallback for scanned PDFs.
            if (
                not extracted.strip()
                and extension == ".pdf"
                and get_ocr_api_key()
            ):
                bot.edit_message_text(
                    "🔎 Scanned PDF detected. Running OCR...",
                    chat_id,
                    status.message_id,
                )

                extracted = extract_text_with_ocr(
                    file_bytes,
                    filename,
                )

            if not extracted.strip():
                raise RuntimeError(
                    (
                        "No readable text was found. "
                        "If this is a scanned PDF, "
                        "make sure OCR_SPACE_API_KEY is configured."
                    )
                )

            if len(extracted) > MAX_MATERIAL_CHARS:
                raise ValueError(
                    (
                        "The extracted text is too large.\n\n"
                        f"Maximum: {MAX_MATERIAL_CHARS:,} characters\n"
                        f"Found: {len(extracted):,}"
                    )
                )

            title = Path(
                filename
            ).stem

            save_material(
                user_id=message.from_user.id,
                subject_id=state.get(
                    "subject_id"
                ),
                title=title,
                file_name=filename,
                file_type=(
                    extension.replace(
                        ".",
                        ""
                    )
                ),
                extracted_text=extracted,
            )

            material_state.pop(
                chat_id,
                None,
            )

            try:
                bot.delete_message(
                    chat_id,
                    status.message_id,
                )
            except Exception:
                pass

            bot.send_message(
                chat_id,
                (
                    "✅ Study material saved!\n\n"
                    f"📄 {title}\n"
                    f"📚 "
                    f"{subject_name(message.from_user.id, state.get('subject_id'))}\n"
                    f"📝 {len(extracted):,} characters extracted"
                ),
            )

            show_material_menu(
                chat_id
            )

        except Exception as error:
            print(
                "Study material upload error:",
                repr(error),
            )

            bot.send_message(
                chat_id,
                f"❌ {str(error)}",
            )

    @bot.message_handler(
        func=lambda m:
        m.chat.id in material_state,
        content_types=["text"],
    )
    def material_state_handler(
        message
    ):
        chat_id = message.chat.id
        text = (
            message.text
            or ""
        ).strip()

        if text == "🏠 Main Menu":
            material_state.pop(
                chat_id,
                None,
            )

            show_main_menu(
                chat_id,
                message.from_user.first_name
                or "Friend",
            )
            return

        if text == "🔙 Materials Menu":
            show_material_menu(
                chat_id
            )
            return

        if (
            text.startswith("/")
            or text in GLOBAL_BUTTONS
        ):
            material_state.pop(
                chat_id,
                None,
            )
            return ContinueHandling()

        state = material_state.get(
            chat_id,
            {}
        )

        step = state.get(
            "step"
        )

        if step == "choose_subject":
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

            state["subject_id"] = subject_id
            state["step"] = "waiting_file"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
            )

            markup.add(
                types.KeyboardButton(
                    "🔙 Materials Menu"
                ),
                types.KeyboardButton(
                    "🏠 Main Menu"
                ),
            )

            bot.send_message(
                chat_id,
                (
                    "📤 Upload your study document now.\n\n"
                    "Supported:\n"
                    "• PDF\n"
                    "• DOCX\n"
                    "• TXT"
                ),
                reply_markup=markup,
            )
            return

        if step in {
            "read_id",
            "summary_id",
            "keypoints_id",
            "delete_id",
        }:
            try:
                material_id = int(
                    text.replace(
                        "#",
                        ""
                    )
                )
            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Send only the material number.",
                )
                return

            try:
                material = get_material(
                    message.from_user.id,
                    material_id,
                )

                if not material:
                    bot.send_message(
                        chat_id,
                        "❌ Material not found.",
                    )
                    return

                if step == "read_id":
                    material_state.pop(
                        chat_id,
                        None,
                    )

                    send_long_text(
                        bot,
                        chat_id,
                        material[
                            "extracted_text"
                        ],
                        heading=(
                            f"📖 {material['title']}\n"
                            f"📚 "
                            f"{subject_name(message.from_user.id, material.get('subject_id'))}"
                        ),
                    )

                    show_material_menu(
                        chat_id
                    )
                    return

                if step == "summary_id":
                    material_state.pop(
                        chat_id,
                        None,
                    )

                    summary = summarize_text(
                        material[
                            "extracted_text"
                        ],
                        max_sentences=7,
                    )

                    send_long_text(
                        bot,
                        chat_id,
                        summary,
                        heading=(
                            f"🧾 Summary: {material['title']}\n\n"
                            "ℹ️ Extractive summary from the uploaded material."
                        ),
                    )

                    show_material_menu(
                        chat_id
                    )
                    return

                if step == "keypoints_id":
                    material_state.pop(
                        chat_id,
                        None,
                    )

                    points = key_points(
                        material[
                            "extracted_text"
                        ],
                        max_points=10,
                    )

                    if not points:
                        bot.send_message(
                            chat_id,
                            "❌ No key points could be extracted.",
                        )
                    else:
                        body = "\n\n".join(
                            (
                                f"• {point}"
                            )
                            for point in points
                        )

                        send_long_text(
                            bot,
                            chat_id,
                            body,
                            heading=(
                                f"✨ Key Points: {material['title']}"
                            ),
                        )

                    show_material_menu(
                        chat_id
                    )
                    return

                if step == "delete_id":
                    success = delete_material(
                        message.from_user.id,
                        material_id,
                    )

                    if not success:
                        bot.send_message(
                            chat_id,
                            "❌ Material not found.",
                        )
                        return

                    material_state.pop(
                        chat_id,
                        None,
                    )

                    bot.send_message(
                        chat_id,
                        "✅ Study material deleted.",
                    )

                    show_material_menu(
                        chat_id
                    )
                    return

            except Exception as error:
                print(
                    "Material action error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not process this material.",
                )
                return

        if step == "search":
            query_text = text.casefold()

            if len(query_text) < 2:
                bot.send_message(
                    chat_id,
                    "❌ Search term is too short.",
                )
                return

            try:
                # Fetch a limited set and search locally.
                result = (
                    supabase
                    .table("study_materials")
                    .select(
                        "id,subject_id,title,file_type,"
                        "extracted_chars,extracted_text"
                    )
                    .eq(
                        "user_id",
                        int(message.from_user.id),
                    )
                    .order(
                        "created_at",
                        desc=True,
                    )
                    .limit(100)
                    .execute()
                )

                matches = []

                for material in (
                    result.data
                    or []
                ):
                    haystack = (
                        f"{material.get('title', '')}\n"
                        f"{material.get('extracted_text', '')}"
                    ).casefold()

                    if query_text in haystack:
                        matches.append(
                            material
                        )

                material_state.pop(
                    chat_id,
                    None,
                )

                if not matches:
                    bot.send_message(
                        chat_id,
                        "🔎 No matching study materials found.",
                    )

                    show_material_menu(
                        chat_id
                    )
                    return

                parts = [
                    f"🔎 Search Results for: {text}\n"
                ]

                for material in matches[
                    :20
                ]:
                    extracted = (
                        material.get(
                            "extracted_text"
                        )
                        or ""
                    )

                    location = extracted.casefold().find(
                        query_text
                    )

                    if location >= 0:
                        start = max(
                            0,
                            location - 90,
                        )

                        end = min(
                            len(extracted),
                            location + 180,
                        )

                        preview = re.sub(
                            r"\s+",
                            " ",
                            extracted[
                                start:end
                            ],
                        ).strip()

                    else:
                        preview = ""

                    parts.append(
                        (
                            f"\n#{material['id']} {material['title']}\n"
                            f"📚 "
                            f"{subject_name(message.from_user.id, material.get('subject_id'))}\n"
                            f"📝 {preview}\n"
                        )
                    )

                send_long_text(
                    bot,
                    chat_id,
                    "\n".join(parts),
                )

                show_material_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Search materials error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Search failed.",
                )

            return

        if step == "waiting_file":
            bot.send_message(
                chat_id,
                (
                    "📤 Please upload a PDF, DOCX, or TXT file."
                ),
            )
            return
