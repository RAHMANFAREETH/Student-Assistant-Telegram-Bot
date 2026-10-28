from io import BytesIO
from pathlib import Path

from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
from telebot import types
from telebot.handler_backends import ContinueHandling

from navigation import should_yield_to_navigation
from text_pdf_v711 import (
    create_text_pdf, TextPdfError, MAX_TEXT_CHARS, MAX_TEXT_MESSAGES,
    PDF_TEXT_MODE, PDF_TEXT_BUTTON, PDF_TEXT_CREATE, PDF_TEXT_CLEAR,
)


# Per-chat PDF tool state.
pdf_state = {}


PDF_TOOL_MODES = {
    "merge",
    "extract_wait_pdf",
    "rotate_wait_pdf",
    "protect_wait_pdf",
    "images",
}


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


# ==================================================
# HELPERS
# ==================================================


def _download_telegram_file(bot, file_id):
    file_info = bot.get_file(file_id)
    return bot.download_file(file_info.file_path)


def _pdf_tools_menu(bot, chat_id):
    pdf_state[chat_id] = {
        "mode": "menu"
    }

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2,
    )

    markup.add(
        types.KeyboardButton("🔗 Merge PDFs"),
        types.KeyboardButton("✂️ Extract Pages"),
        types.KeyboardButton("🖼 Images → PDF"),
        types.KeyboardButton(PDF_TEXT_BUTTON),
        types.KeyboardButton("🔄 Rotate PDF"),
        types.KeyboardButton("🔐 Protect PDF"),
        types.KeyboardButton("🏠 Main Menu"),
    )

    bot.send_message(
        chat_id,
        (
            "📄 PDF Tools\n\n"
            "Choose a tool:\n\n"
            "🔗 Merge PDFs\n"
            "✂️ Extract Pages\n"
            "🖼 Images → PDF\n"
            "📝 Text → PDF\n"
            "🔄 Rotate PDF\n"
            "🔐 Protect PDF"
        ),
        reply_markup=markup,
    )


def _mode_keyboard(*buttons):
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2,
    )

    for row in buttons:
        if isinstance(row, (list, tuple)):
            markup.row(
                *[
                    types.KeyboardButton(text)
                    for text in row
                ]
            )
        else:
            markup.add(
                types.KeyboardButton(row)
            )

    return markup


def _safe_stem(filename, default="document"):
    if not filename:
        return default

    stem = Path(filename).stem.strip()
    return stem or default


def _parse_page_selection(text, total_pages):
    """
    Accepts examples such as:
    1
    1,3,5
    2-6
    1,3-5,8
    Returns zero-based unique page indexes in user order.
    """
    selected = []
    seen = set()

    for raw_part in text.split(","):
        part = raw_part.strip()

        if not part:
            continue

        if "-" in part:
            pieces = part.split("-", 1)

            if len(pieces) != 2:
                raise ValueError("Invalid page range.")

            start = int(pieces[0].strip())
            end = int(pieces[1].strip())

            if start > end:
                raise ValueError(
                    "Page range must go from smaller to larger number."
                )

            page_numbers = range(start, end + 1)

        else:
            page_numbers = [int(part)]

        for page_number in page_numbers:
            if page_number < 1 or page_number > total_pages:
                raise ValueError(
                    f"Page {page_number} is outside this PDF. "
                    f"Valid pages: 1-{total_pages}."
                )

            page_index = page_number - 1

            if page_index not in seen:
                seen.add(page_index)
                selected.append(page_index)

    if not selected:
        raise ValueError("Choose at least one page.")

    return selected


def _images_to_pdf(image_items):
    converted = []

    try:
        for item in image_items:
            image = Image.open(BytesIO(item))

            # Flatten transparent images onto white before PDF conversion.
            if image.mode in ("RGBA", "LA"):
                background = Image.new(
                    "RGB",
                    image.size,
                    "white",
                )
                alpha = image.getchannel("A")
                background.paste(
                    image.convert("RGB"),
                    mask=alpha,
                )
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")

            converted.append(image)

        if not converted:
            raise ValueError("No images were added.")

        output = BytesIO()
        output.name = "images_to_pdf.pdf"

        first = converted[0]
        rest = converted[1:]

        first.save(
            output,
            format="PDF",
            save_all=True,
            append_images=rest,
        )

        output.seek(0)
        return output

    finally:
        for image in converted:
            try:
                image.close()
            except Exception:
                pass


# ==================================================
# REGISTER PDF HANDLERS
# ==================================================


def register_pdf_handlers(bot, show_main_menu):

    # ----------------------------------------------
    # OPEN PDF TOOLS
    # ----------------------------------------------

    @bot.message_handler(
        func=lambda message:
        message.text == "📄 PDF Tools"
    )
    def open_pdf_tools(message):
        _pdf_tools_menu(
            bot,
            message.chat.id,
        )

    # ----------------------------------------------
    # MAIN MENU - ONLY WHEN PDF TOOLS IS ACTIVE
    # ----------------------------------------------

    @bot.message_handler(
        func=lambda message:
        message.text == "🏠 Main Menu"
        and message.chat.id in pdf_state
    )
    def pdf_main_menu(message):
        pdf_state.pop(
            message.chat.id,
            None,
        )

        show_main_menu(
            message.chat.id,
            message.from_user.first_name or "Friend",
        )

    @bot.message_handler(
        func=lambda message:
        message.text == "🔙 PDF Tools"
        and message.chat.id in pdf_state
    )
    def back_to_pdf_tools(message):
        _pdf_tools_menu(
            bot,
            message.chat.id,
        )

    # ----------------------------------------------
    # TEXT TO PDF - private chats and in-memory text only.
    # ----------------------------------------------

    @bot.message_handler(commands=["textpdf"])
    @bot.message_handler(func=lambda m: getattr(m, "text", None) == PDF_TEXT_BUTTON)
    def start_text_to_pdf(message):
        chat_id = message.chat.id
        if getattr(message.chat, "type", "private") != "private":
            bot.send_message(chat_id, "🔒 Please open a private chat with this bot to create a text PDF.")
            return
        pdf_state[chat_id] = {"mode": PDF_TEXT_MODE, "parts": [], "length": 0}
        bot.send_message(
            chat_id,
            "📝 Text → PDF\n\n"
            "Paste or type your notes in one or several messages.\n"
            "Tamil • English • Sinhala • Arabic supported.\n\n"
            f"Maximum: {MAX_TEXT_CHARS:,} characters in {MAX_TEXT_MESSAGES} messages.\n"
            "When ready, tap ✅ Create Text PDF.\n"
            "The bot does not save this text to your Study Notes database.",
            reply_markup=_mode_keyboard(
                [PDF_TEXT_CREATE, PDF_TEXT_CLEAR],
                ["🔙 PDF Tools", "🏠 Main Menu"],
                "❌ Cancel",
            ),
        )

    @bot.message_handler(
        func=lambda m: getattr(m, "text", None) == PDF_TEXT_CLEAR
        and pdf_state.get(m.chat.id, {}).get("mode") == PDF_TEXT_MODE
    )
    def clear_text_to_pdf(message):
        state = pdf_state[message.chat.id]
        state.update(parts=[], length=0)
        bot.send_message(message.chat.id, "🧹 Text cleared. Send your new text.")

    @bot.message_handler(
        func=lambda m: getattr(m, "text", None) == "❌ Cancel"
        and pdf_state.get(m.chat.id, {}).get("mode") == PDF_TEXT_MODE
    )
    def cancel_text_to_pdf(message):
        _pdf_tools_menu(bot, message.chat.id)

    @bot.message_handler(
        func=lambda m: getattr(m, "text", None) == PDF_TEXT_CREATE
        and pdf_state.get(m.chat.id, {}).get("mode") == PDF_TEXT_MODE
    )
    def finish_text_to_pdf(message):
        chat_id = message.chat.id
        state = pdf_state.get(chat_id, {})
        parts = state.get("parts") or []
        if not parts:
            bot.send_message(chat_id, "❌ First send the text you want in the PDF.")
            return
        bot.send_chat_action(chat_id, "upload_document")
        try:
            output = create_text_pdf("\n\n".join(parts))
            bot.send_document(
                chat_id, output,
                caption="✅ Your Text PDF is ready! 📄",
            )
        except TextPdfError as error:
            # Configuration errors are safe to explain; never echo user text.
            bot.send_message(chat_id, "❌ " + str(error))
            return
        except Exception as error:
            print("Text PDF generation error:", type(error).__name__)
            bot.send_message(chat_id, "❌ PDF creation failed. Please try again.")
            return
        finally:
            # Do not leave the PDF bytes or a file descriptor open.
            if "output" in locals():
                output.close()
        _pdf_tools_menu(bot, chat_id)

    @bot.message_handler(
        func=lambda m: pdf_state.get(m.chat.id, {}).get("mode") == PDF_TEXT_MODE
        and should_yield_to_navigation(getattr(m, "text", None)),
        content_types=["text"],
    )
    def text_pdf_other_command(message):
        pdf_state.pop(message.chat.id, None)
        return ContinueHandling()

    @bot.message_handler(
        func=lambda m: pdf_state.get(m.chat.id, {}).get("mode") == PDF_TEXT_MODE,
        content_types=["text"],
    )
    def collect_text_for_pdf(message):
        chat_id = message.chat.id
        state = pdf_state.get(chat_id, {})
        part = (message.text or "").strip()
        if not part:
            bot.send_message(chat_id, "Please send text, not an empty message.")
            return
        if len(state.get("parts") or []) >= MAX_TEXT_MESSAGES:
            bot.send_message(chat_id, "⚠️ Message limit reached. Tap ✅ Create Text PDF.")
            return
        new_length = state.get("length", 0) + len(part) + (2 if state.get("parts") else 0)
        if new_length > MAX_TEXT_CHARS:
            bot.send_message(chat_id, f"⚠️ Too much text. Maximum {MAX_TEXT_CHARS:,} characters.\nTap ✅ Create Text PDF or 🧹 Clear Text.")
            return
        state.setdefault("parts", []).append(part)
        state["length"] = new_length
        bot.send_message(
            chat_id,
            f"✅ Text added! {len(state['parts'])} message(s), {new_length:,}/{MAX_TEXT_CHARS:,} characters.\n"
            "Send more text or tap ✅ Create Text PDF.",
        )

    @bot.message_handler(
        func=lambda m: pdf_state.get(m.chat.id, {}).get("mode") == PDF_TEXT_MODE,
        content_types=["document", "photo"],
    )
    def text_pdf_nontext(message):
        bot.send_message(message.chat.id, "📝 This tool converts typed/pasted text. Please send text messages, not files or photos.")

    # ----------------------------------------------
    # MERGE
    # ----------------------------------------------

    @bot.message_handler(
        func=lambda message:
        message.text == "🔗 Merge PDFs"
    )
    def start_merge(message):
        pdf_state[
            message.chat.id
        ] = {
            "mode": "merge",
            "files": [],
        }

        bot.send_message(
            message.chat.id,
            (
                "🔗 Merge PDFs\n\n"
                "Upload your PDF files one by one, in the order "
                "you want them merged.\n\n"
                "When finished, press ✅ Finish Merge."
            ),
            reply_markup=_mode_keyboard(
                ["✅ Finish Merge", "🔙 PDF Tools"],
                "🏠 Main Menu",
            ),
        )

    @bot.message_handler(
        func=lambda message:
        message.text == "✅ Finish Merge"
        and pdf_state.get(
            message.chat.id,
            {}
        ).get("mode") == "merge"
    )
    def finish_merge(message):
        state = pdf_state.get(
            message.chat.id,
            {}
        )

        files = state.get(
            "files",
            [],
        )

        if len(files) < 2:
            bot.send_message(
                message.chat.id,
                "❌ Upload at least 2 PDF files before merging.",
            )
            return

        status = bot.send_message(
            message.chat.id,
            "⏳ Merging PDFs...",
        )

        try:
            writer = PdfWriter()

            for pdf_bytes in files:
                reader = PdfReader(
                    BytesIO(pdf_bytes)
                )

                for page in reader.pages:
                    writer.add_page(page)

            output = BytesIO()
            output.name = "merged.pdf"
            writer.write(output)
            output.seek(0)

            bot.send_document(
                message.chat.id,
                output,
                caption="✅ PDFs merged successfully.",
            )

            pdf_state.pop(
                message.chat.id,
                None,
            )

            try:
                bot.delete_message(
                    message.chat.id,
                    status.message_id,
                )
            except Exception:
                pass

            _pdf_tools_menu(
                bot,
                message.chat.id,
            )

        except Exception as error:
            print(
                "PDF merge error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not merge those PDFs.",
            )

    # ----------------------------------------------
    # EXTRACT
    # ----------------------------------------------

    @bot.message_handler(
        func=lambda message:
        message.text == "✂️ Extract Pages"
    )
    def start_extract(message):
        pdf_state[
            message.chat.id
        ] = {
            "mode": "extract_wait_pdf",
        }

        bot.send_message(
            message.chat.id,
            (
                "✂️ Extract Pages\n\n"
                "Upload one PDF.\n"
                "After that I will ask which pages you want."
            ),
            reply_markup=_mode_keyboard(
                "🔙 PDF Tools",
                "🏠 Main Menu",
            ),
        )

    # ----------------------------------------------
    # IMAGES TO PDF
    # ----------------------------------------------

    @bot.message_handler(
        func=lambda message:
        message.text == "🖼 Images → PDF"
    )
    def start_images_to_pdf(message):
        pdf_state[
            message.chat.id
        ] = {
            "mode": "images",
            "images": [],
        }

        bot.send_message(
            message.chat.id,
            (
                "🖼 Images → PDF\n\n"
                "Send JPG, PNG or Telegram photos in the order "
                "you want them in the PDF.\n\n"
                "When finished, press ✅ Create PDF."
            ),
            reply_markup=_mode_keyboard(
                ["✅ Create PDF", "🔙 PDF Tools"],
                "🏠 Main Menu",
            ),
        )

    @bot.message_handler(
        func=lambda message:
        message.text == "✅ Create PDF"
        and pdf_state.get(
            message.chat.id,
            {}
        ).get("mode") == "images"
    )
    def finish_images_to_pdf(message):
        state = pdf_state.get(
            message.chat.id,
            {}
        )

        images = state.get(
            "images",
            [],
        )

        if not images:
            bot.send_message(
                message.chat.id,
                "❌ Send at least one image first.",
            )
            return

        status = bot.send_message(
            message.chat.id,
            "⏳ Creating PDF...",
        )

        try:
            output = _images_to_pdf(
                images
            )

            bot.send_document(
                message.chat.id,
                output,
                caption="✅ Image PDF created successfully.",
            )

            pdf_state.pop(
                message.chat.id,
                None,
            )

            try:
                bot.delete_message(
                    message.chat.id,
                    status.message_id,
                )
            except Exception:
                pass

            _pdf_tools_menu(
                bot,
                message.chat.id,
            )

        except Exception as error:
            print(
                "Images to PDF error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not create the PDF.",
            )

    # ----------------------------------------------
    # ROTATE
    # ----------------------------------------------

    @bot.message_handler(
        func=lambda message:
        message.text == "🔄 Rotate PDF"
    )
    def start_rotate(message):
        pdf_state[
            message.chat.id
        ] = {
            "mode": "rotate_wait_pdf",
        }

        bot.send_message(
            message.chat.id,
            (
                "🔄 Rotate PDF\n\n"
                "Upload one PDF."
            ),
            reply_markup=_mode_keyboard(
                "🔙 PDF Tools",
                "🏠 Main Menu",
            ),
        )

    # ----------------------------------------------
    # PROTECT
    # ----------------------------------------------

    @bot.message_handler(
        func=lambda message:
        message.text == "🔐 Protect PDF"
    )
    def start_protect(message):
        pdf_state[
            message.chat.id
        ] = {
            "mode": "protect_wait_pdf",
        }

        bot.send_message(
            message.chat.id,
            (
                "🔐 Protect PDF\n\n"
                "Upload one PDF.\n"
                "I will then ask for a password."
            ),
            reply_markup=_mode_keyboard(
                "🔙 PDF Tools",
                "🏠 Main Menu",
            ),
        )

    # ==================================================
    # DOCUMENT HANDLER
    # IMPORTANT: Runs ONLY when a PDF tool is active.
    # This prevents conflict with Translate Document.
    # ==================================================

    @bot.message_handler(
        func=lambda message:
        pdf_state.get(
            message.chat.id,
            {}
        ).get("mode")
        in PDF_TOOL_MODES,
        content_types=["document"],
    )
    def receive_pdf_document(message):
        chat_id = message.chat.id
        state = pdf_state.get(
            chat_id,
            {}
        )
        mode = state.get("mode")

        filename = (
            message.document.file_name
            or "document"
        )

        extension = Path(
            filename
        ).suffix.lower()

        try:
            file_bytes = _download_telegram_file(
                bot,
                message.document.file_id,
            )

            # --------------------------------------
            # IMAGE DOCUMENTS
            # --------------------------------------

            if mode == "images":
                if extension not in IMAGE_EXTENSIONS:
                    bot.send_message(
                        chat_id,
                        "❌ For Images → PDF, send JPG, JPEG, PNG or WEBP.",
                    )
                    return

                state.setdefault(
                    "images",
                    [],
                ).append(file_bytes)

                bot.send_message(
                    chat_id,
                    (
                        "✅ Image added.\n"
                        f"Total images: {len(state['images'])}"
                    ),
                )
                return

            # --------------------------------------
            # PDF-ONLY MODES
            # --------------------------------------

            if extension != ".pdf":
                bot.send_message(
                    chat_id,
                    "❌ Please upload a PDF file.",
                )
                return

            if mode == "merge":
                state.setdefault(
                    "files",
                    [],
                ).append(file_bytes)

                bot.send_message(
                    chat_id,
                    (
                        "✅ PDF added.\n"
                        f"Total PDFs: {len(state['files'])}\n\n"
                        "Send another PDF or press ✅ Finish Merge."
                    ),
                )
                return

            if mode == "extract_wait_pdf":
                reader = PdfReader(
                    BytesIO(file_bytes)
                )

                total_pages = len(
                    reader.pages
                )

                state.update(
                    {
                        "mode": "extract_pages",
                        "pdf_bytes": file_bytes,
                        "filename": filename,
                        "total_pages": total_pages,
                    }
                )

                bot.send_message(
                    chat_id,
                    (
                        f"✅ PDF received: {total_pages} pages.\n\n"
                        "Type the pages to extract.\n\n"
                        "Examples:\n"
                        "1\n"
                        "1,3,5\n"
                        "2-6\n"
                        "1,3-5,8"
                    ),
                    reply_markup=_mode_keyboard(
                        "🔙 PDF Tools",
                        "🏠 Main Menu",
                    ),
                )
                return

            if mode == "rotate_wait_pdf":
                state.update(
                    {
                        "mode": "rotate_angle",
                        "pdf_bytes": file_bytes,
                        "filename": filename,
                    }
                )

                bot.send_message(
                    chat_id,
                    "✅ PDF received. Choose rotation:",
                    reply_markup=_mode_keyboard(
                        ["90°", "180°", "270°"],
                        "🔙 PDF Tools",
                        "🏠 Main Menu",
                    ),
                )
                return

            if mode == "protect_wait_pdf":
                state.update(
                    {
                        "mode": "protect_password",
                        "pdf_bytes": file_bytes,
                        "filename": filename,
                    }
                )

                bot.send_message(
                    chat_id,
                    (
                        "✅ PDF received.\n\n"
                        "🔐 Send the password you want to use."
                    ),
                    reply_markup=_mode_keyboard(
                        "🔙 PDF Tools",
                        "🏠 Main Menu",
                    ),
                )
                return

        except Exception as error:
            print(
                "PDF document handler error:",
                repr(error),
            )

            bot.send_message(
                chat_id,
                "❌ I could not process that file.",
            )

    # ==================================================
    # PHOTO HANDLER
    # IMPORTANT: Runs ONLY for Images → PDF.
    # This prevents conflict with OCR Image → Translate.
    # ==================================================

    @bot.message_handler(
        func=lambda message:
        pdf_state.get(
            message.chat.id,
            {}
        ).get("mode") == "images",
        content_types=["photo"],
    )
    def receive_pdf_image_photo(message):
        chat_id = message.chat.id
        state = pdf_state.get(
            chat_id,
            {}
        )

        try:
            photo = message.photo[-1]

            image_bytes = _download_telegram_file(
                bot,
                photo.file_id,
            )

            state.setdefault(
                "images",
                [],
            ).append(image_bytes)

            bot.send_message(
                chat_id,
                (
                    "✅ Image added.\n"
                    f"Total images: {len(state['images'])}"
                ),
            )

        except Exception as error:
            print(
                "PDF photo handler error:",
                repr(error),
            )

            bot.send_message(
                chat_id,
                "❌ Could not read that image.",
            )

    # ==================================================
    # EXTRACT PAGE INPUT
    # ==================================================

    @bot.message_handler(
        func=lambda message:
        message.text is not None
        and pdf_state.get(
            message.chat.id,
            {}
        ).get("mode") == "extract_pages"
    )
    def extract_pages_input(message):
        state = pdf_state[
            message.chat.id
        ]

        try:
            selected_pages = _parse_page_selection(
                message.text,
                state["total_pages"],
            )

            reader = PdfReader(
                BytesIO(
                    state["pdf_bytes"]
                )
            )

            writer = PdfWriter()

            for page_index in selected_pages:
                writer.add_page(
                    reader.pages[page_index]
                )

            output = BytesIO()
            output.name = (
                f"{_safe_stem(state.get('filename'))}_extracted.pdf"
            )

            writer.write(output)
            output.seek(0)

            bot.send_document(
                message.chat.id,
                output,
                caption="✅ Selected pages extracted successfully.",
            )

            pdf_state.pop(
                message.chat.id,
                None,
            )

            _pdf_tools_menu(
                bot,
                message.chat.id,
            )

        except Exception as error:
            bot.send_message(
                message.chat.id,
                f"❌ {str(error)}",
            )

    # ==================================================
    # ROTATE ANGLE INPUT
    # ==================================================

    @bot.message_handler(
        func=lambda message:
        message.text is not None
        and pdf_state.get(
            message.chat.id,
            {}
        ).get("mode") == "rotate_angle"
    )
    def rotate_angle_input(message):
        state = pdf_state[
            message.chat.id
        ]

        value = (
            message.text
            .replace("°", "")
            .strip()
        )

        if value not in {
            "90",
            "180",
            "270",
        }:
            bot.send_message(
                message.chat.id,
                "❌ Choose 90°, 180° or 270°.",
            )
            return

        try:
            angle = int(value)

            reader = PdfReader(
                BytesIO(
                    state["pdf_bytes"]
                )
            )

            writer = PdfWriter()

            for page in reader.pages:
                page.rotate(angle)
                writer.add_page(page)

            output = BytesIO()
            output.name = (
                f"{_safe_stem(state.get('filename'))}_rotated.pdf"
            )

            writer.write(output)
            output.seek(0)

            bot.send_document(
                message.chat.id,
                output,
                caption=(
                    f"✅ PDF rotated {angle}° successfully."
                ),
            )

            pdf_state.pop(
                message.chat.id,
                None,
            )

            _pdf_tools_menu(
                bot,
                message.chat.id,
            )

        except Exception as error:
            print(
                "PDF rotate error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not rotate that PDF.",
            )

    # ==================================================
    # PASSWORD INPUT
    # ==================================================

    @bot.message_handler(
        func=lambda message:
        message.text is not None
        and pdf_state.get(
            message.chat.id,
            {}
        ).get("mode") == "protect_password"
    )
    def protect_password_input(message):
        state = pdf_state[
            message.chat.id
        ]

        password = message.text.strip()

        if not password:
            bot.send_message(
                message.chat.id,
                "❌ Password cannot be empty.",
            )
            return

        try:
            reader = PdfReader(
                BytesIO(
                    state["pdf_bytes"]
                )
            )

            writer = PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            writer.encrypt(password)

            output = BytesIO()
            output.name = (
                f"{_safe_stem(state.get('filename'))}_protected.pdf"
            )

            writer.write(output)
            output.seek(0)

            bot.send_document(
                message.chat.id,
                output,
                caption="✅ Password-protected PDF created.",
            )

            pdf_state.pop(
                message.chat.id,
                None,
            )

            _pdf_tools_menu(
                bot,
                message.chat.id,
            )

        except Exception as error:
            print(
                "PDF protect error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not protect that PDF.",
            )
