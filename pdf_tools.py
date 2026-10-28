from io import BytesIO
from pathlib import Path

from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
from telebot import types
from telebot.handler_backends import ContinueHandling

from image_filters_v713 import (
    FILTER_BUTTON, PREVIEW_BUTTON, REMOVE_BUTTON, BACK_BUTTON,
    FILTER_LABELS, FILTER_NAMES, MAX_IMAGE_BYTES, MAX_IMAGES,
    ImageFilterError, enqueue_image, selected_filter, make_preview,
    images_to_pdf,
)
from image_crop_v714 import (
    CROP_MENU_BUTTON, CROP_ORIGINAL_BUTTON, CROP_AUTO_BUTTON,
    CROP_NAMES, selected_crop,
)

from photo_crop_v715 import (
    PHOTO_CROP_BUTTON, PHOTO_CROP_MODE, PREVIEW_CROP_BUTTON,
    SAVE_CROP_BUTTON, CUSTOM_CROP_BUTTON, CHANGE_PHOTO_BUTTON,
    CANCEL_CROP_BUTTON, AUTO_PAGE_BUTTON, ORIGINAL_BUTTON, PRESETS,
    MAX_SOURCE_BYTES, VALID_EXTENSIONS, PhotoCropError,
    parse_custom_edges, read_image, create_cropped_image,
)

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
        types.KeyboardButton(PHOTO_CROP_BUTTON),
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
            f"{PHOTO_CROP_BUTTON}\n"
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


def _photo_crop_keyboard():
    return _mode_keyboard(
        ["⬜ Square 1:1", "📷 Portrait 4:5"],
        ["📱 Story 9:16", "🖼 Landscape 16:9"],
        [AUTO_PAGE_BUTTON, CUSTOM_CROP_BUTTON],
        [ORIGINAL_BUTTON, PREVIEW_CROP_BUTTON],
        [SAVE_CROP_BUTTON, CHANGE_PHOTO_BUTTON],
        ["🔙 PDF Tools", CANCEL_CROP_BUTTON],
        "🏠 Main Menu",
    )


def _image_tools_keyboard():
    return _mode_keyboard(
        [FILTER_BUTTON, PREVIEW_BUTTON],
        [CROP_MENU_BUTTON, REMOVE_BUTTON],
        ["✅ Create PDF", "🔙 PDF Tools"],
        "🏠 Main Menu",
    )


def _image_crop_keyboard():
    return _mode_keyboard(
        [CROP_ORIGINAL_BUTTON, CROP_AUTO_BUTTON],
        BACK_BUTTON,
        "🏠 Main Menu",
    )


def _image_filter_keyboard():
    choices = list(FILTER_LABELS)
    return _mode_keyboard(
        *[choices[i:i + 2] for i in range(0, len(choices), 2)],
        BACK_BUTTON,
        "🏠 Main Menu",
    )


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

    # V7.15: standalone photo crop. Registered before the legacy PDF upload
    # handlers; all predicates require this dedicated mode (no OCR interference).
    @bot.message_handler(commands=["cropimage", "imagecrop"])
    @bot.message_handler(func=lambda m: getattr(m, "text", None) == PHOTO_CROP_BUTTON)
    def start_photo_crop(message):
        chat_id = message.chat.id
        if getattr(message.chat, "type", "private") != "private":
            bot.send_message(chat_id, "🔒 Please open the bot in a private chat to crop photos.")
            return
        pdf_state[chat_id] = {"mode": PHOTO_CROP_MODE, "image": None,
                              "selection": ORIGINAL_BUTTON, "edges": None,
                              "await_edges": False}
        bot.send_message(chat_id,
            "✂️ Photo/Image Crop\n\n"
            "Send one photo, or a JPG/PNG/WEBP file as a document for best quality.\n"
            "Then choose Square, Portrait, Story, Landscape, Auto Page or Custom Edges.\n"
            "Your original is not changed. No PDF is required.",
            reply_markup=_photo_crop_keyboard())

    @bot.message_handler(
        func=lambda m: pdf_state.get(m.chat.id, {}).get("mode") == PHOTO_CROP_MODE
        and getattr(m, "text", None) == CANCEL_CROP_BUTTON,
        content_types=["text"])
    def cancel_photo_crop(message):
        _pdf_tools_menu(bot, message.chat.id)

    @bot.message_handler(
        func=lambda m: pdf_state.get(m.chat.id, {}).get("mode") == PHOTO_CROP_MODE
        and getattr(m, "text", None) == "🔙 PDF Tools",
        content_types=["text"])
    def back_from_photo_crop(message):
        _pdf_tools_menu(bot, message.chat.id)

    @bot.message_handler(
        func=lambda m: pdf_state.get(m.chat.id, {}).get("mode") == PHOTO_CROP_MODE
        and getattr(m, "text", None) == CHANGE_PHOTO_BUTTON,
        content_types=["text"])
    def replace_photo_crop(message):
        state = pdf_state[message.chat.id]
        state.update(image=None, selection=ORIGINAL_BUTTON, edges=None, await_edges=False)
        bot.send_message(message.chat.id, "🔄 Send another photo or image document.",
                         reply_markup=_photo_crop_keyboard())

    @bot.message_handler(
        func=lambda m: pdf_state.get(m.chat.id, {}).get("mode") == PHOTO_CROP_MODE
        and getattr(m, "text", None) == CUSTOM_CROP_BUTTON,
        content_types=["text"])
    def start_custom_crop(message):
        state = pdf_state[message.chat.id]
        if not state.get("image"):
            bot.send_message(message.chat.id, "❌ Send a photo first.")
            return
        state["await_edges"] = True
        bot.send_message(message.chat.id,
            "📐 Custom Edges\n\nSend 4 percentages: LEFT TOP RIGHT BOTTOM.\n"
            "Example: 10 5 90 95 (remove 10% from each side and 5% top/bottom).\n"
            "Coordinates start at the top-left corner.")

    def _render_crop_preview(chat_id, state):
        if not state.get("image"):
            bot.send_message(chat_id, "❌ Send a photo first.")
            return
        try:
            output = create_cropped_image(state["image"], state["selection"],
                                           state.get("edges"), preview=True)
            try:
                bot.send_photo(chat_id, output,
                    caption=f"👁 Crop preview: {state['selection']}\n"
                            "Choose another crop or tap ✅ Save Cropped Image.",
                    reply_markup=_photo_crop_keyboard())
            finally:
                output.close()
        except PhotoCropError as error:
            bot.send_message(chat_id, str(error))
        except Exception as error:
            print("Photo crop preview failed:", type(error).__name__)
            bot.send_message(chat_id, "❌ Could not preview the crop. Try another photo.")

    @bot.message_handler(
        func=lambda m: pdf_state.get(m.chat.id, {}).get("mode") == PHOTO_CROP_MODE
        and getattr(m, "text", None) in (set(PRESETS) | {AUTO_PAGE_BUTTON, ORIGINAL_BUTTON}),
        content_types=["text"])
    def select_photo_crop(message):
        state = pdf_state[message.chat.id]
        if not state.get("image"):
            bot.send_message(message.chat.id, "❌ Send a photo first.")
            return
        state["selection"] = message.text
        state["edges"] = None
        state["await_edges"] = False
        _render_crop_preview(message.chat.id, state)

    @bot.message_handler(
        func=lambda m: pdf_state.get(m.chat.id, {}).get("mode") == PHOTO_CROP_MODE
        and getattr(m, "text", None) == PREVIEW_CROP_BUTTON,
        content_types=["text"])
    def preview_photo_crop(message):
        _render_crop_preview(message.chat.id, pdf_state[message.chat.id])

    @bot.message_handler(
        func=lambda m: pdf_state.get(m.chat.id, {}).get("mode") == PHOTO_CROP_MODE
        and getattr(m, "text", None) == SAVE_CROP_BUTTON,
        content_types=["text"])
    def save_photo_crop(message):
        chat_id = message.chat.id
        state = pdf_state[chat_id]
        if not state.get("image"):
            bot.send_message(chat_id, "❌ Send a photo first.")
            return
        try:
            output = create_cropped_image(state["image"], state["selection"],
                                           state.get("edges"))
            try:
                bot.send_document(chat_id, output,
                    caption="✅ Cropped image ready! Sent as a file to preserve quality.")
            finally:
                output.close()
        except PhotoCropError as error:
            bot.send_message(chat_id, str(error))
            return
        except Exception as error:
            print("Photo crop save failed:", type(error).__name__)
            bot.send_message(chat_id, "❌ Could not crop the photo. Try another photo.")
            return
        _pdf_tools_menu(bot, chat_id)

    @bot.message_handler(
        func=lambda m: pdf_state.get(m.chat.id, {}).get("mode") == PHOTO_CROP_MODE,
        content_types=["photo", "document"])
    def receive_photo_for_crop(message):
        chat_id = message.chat.id
        if getattr(message.chat, "type", "private") != "private":
            bot.send_message(chat_id, "🔒 Use this tool in a private chat.")
            return
        try:
            if message.content_type == "photo":
                entry = message.photo[-1]
            else:
                entry = message.document
                ext = Path(entry.file_name or "").suffix.lower()
                if ext not in VALID_EXTENSIONS:
                    bot.send_message(chat_id, "❌ Please upload JPG, PNG or WEBP, not PDF/other files.")
                    return
            if (getattr(entry, "file_size", 0) or 0) > MAX_SOURCE_BYTES:
                bot.send_message(chat_id, "❌ Image is larger than 12 MB.")
                return
            data = _download_telegram_file(bot, entry.file_id)
            with read_image(data) as verified:
                dimensions = verified.size
            state = pdf_state[chat_id]
            state.update(image=data, selection=ORIGINAL_BUTTON, edges=None, await_edges=False)
            bot.send_message(chat_id,
                f"✅ Photo received ({dimensions[0]} × {dimensions[1]} pixels).\n"
                "Select a crop style. A preview will appear automatically.",
                reply_markup=_photo_crop_keyboard())
        except PhotoCropError as error:
            bot.send_message(chat_id, str(error))
        except Exception as error:
            print("Photo crop upload failed:", type(error).__name__)
            bot.send_message(chat_id, "❌ Could not open that image. Please try JPG/PNG.")

    @bot.message_handler(
        func=lambda m: pdf_state.get(m.chat.id, {}).get("mode") == PHOTO_CROP_MODE
        and getattr(m, "text", None) not in ("🔙 PDF Tools", "🏠 Main Menu")
        and not should_yield_to_navigation(getattr(m, "text", None)),
        content_types=["text"])
    def receive_photo_crop_text(message):
        state = pdf_state[message.chat.id]
        if state.get("await_edges"):
            try:
                edges = parse_custom_edges(message.text or "")
                # Preview validation first; only update state on valid crop.
                output = create_cropped_image(state["image"], CUSTOM_CROP_BUTTON,
                                               edges, preview=True)
                output.close()
            except PhotoCropError as error:
                bot.send_message(message.chat.id, str(error))
                return
            state.update(selection=CUSTOM_CROP_BUTTON, edges=edges, await_edges=False)
            _render_crop_preview(message.chat.id, state)
        else:
            bot.send_message(message.chat.id,
                "✂️ Choose a crop button, send a photo, or tap 📐 Custom Edges.",
                reply_markup=_photo_crop_keyboard())

    @bot.message_handler(
        func=lambda m: pdf_state.get(m.chat.id, {}).get("mode") == PHOTO_CROP_MODE
        and should_yield_to_navigation(getattr(m, "text", None))
        and getattr(m, "text", None) not in ("🔙 PDF Tools", "🏠 Main Menu"),
        content_types=["text"])
    def crop_yield_to_other_tools(message):
        pdf_state.pop(message.chat.id, None)
        return ContinueHandling()



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
            "image_filter": "original",
            "image_autocrop": False,
        }

        bot.send_message(
            message.chat.id,
            (
                "🖼 Images → PDF\n\n"
                "Send JPG, PNG or Telegram photos in the order "
                "you want them in the PDF.\n\n"
                "Default: Original image, Original filter (no crop).\n"
                "Optional: ✂️ Crop Mode → Auto Crop to remove desk edges.\n"
                "Choose 🎨 Choose Filter for scan/color effects.\n"
                "Use 👁 Preview Last to see the effect before converting.\n"
                f"Maximum {MAX_IMAGES} images. Press ✅ Create PDF when ready."
            ),
            reply_markup=_image_tools_keyboard(),
        )

    @bot.message_handler(commands=["imagefilters"])
    @bot.message_handler(
        func=lambda m: getattr(m, "text", None) == FILTER_BUTTON
        and pdf_state.get(m.chat.id, {}).get("mode") == "images"
    )
    def open_image_filter_picker(message):
        chat_id = message.chat.id
        state = pdf_state.get(chat_id, {})
        if state.get("mode") != "images":
            bot.send_message(chat_id, "🖼 First open PDF Tools → Images → PDF.")
            return
        code = selected_filter(state)
        bot.send_message(
            chat_id,
            f"🎨 Choose a filter for all {len(state.get('images', []))} images.\n"
            f"Current: {FILTER_NAMES[code]}\n\n"
            "Your original photos stay unchanged.",
            reply_markup=_image_filter_keyboard(),
        )

    @bot.message_handler(
        func=lambda m: getattr(m, "text", None) in FILTER_LABELS
        and pdf_state.get(m.chat.id, {}).get("mode") == "images"
    )
    def choose_image_filter(message):
        state = pdf_state[message.chat.id]
        state["image_filter"] = FILTER_LABELS[message.text]
        bot.send_message(
            message.chat.id,
            f"✅ Filter selected: {message.text}\n"
            "Send more photos, preview the last image, or create your PDF.",
            reply_markup=_image_tools_keyboard(),
        )

    @bot.message_handler(
        func=lambda m: getattr(m, "text", None) == CROP_MENU_BUTTON
        and pdf_state.get(m.chat.id, {}).get("mode") == "images"
    )
    def open_crop_picker(message):
        state = pdf_state[message.chat.id]
        bot.send_message(
            message.chat.id,
            "✂️ Crop Mode\n\n"
            f"Current: {CROP_NAMES[selected_crop(state)]}\n"
            "Original keeps the whole image (default).\n"
            "Auto Crop tries to remove a clearly visible desk/background. "
            "If it cannot detect the page safely, it keeps the original.",
            reply_markup=_image_crop_keyboard(),
        )

    @bot.message_handler(
        func=lambda m: getattr(m, "text", None) in (CROP_ORIGINAL_BUTTON, CROP_AUTO_BUTTON)
        and pdf_state.get(m.chat.id, {}).get("mode") == "images"
    )
    def choose_crop_mode(message):
        state = pdf_state[message.chat.id]
        state["image_autocrop"] = (message.text == CROP_AUTO_BUTTON)
        bot.send_message(
            message.chat.id,
            f"✅ Crop Mode: {CROP_NAMES[selected_crop(state)]}\n"
            "Use 👁 Preview Last before creating the PDF.",
            reply_markup=_image_tools_keyboard(),
        )

    @bot.message_handler(
        func=lambda m: getattr(m, "text", None) == BACK_BUTTON
        and pdf_state.get(m.chat.id, {}).get("mode") == "images"
    )
    def return_to_image_mode(message):
        state = pdf_state[message.chat.id]
        bot.send_message(
            message.chat.id,
            f"🖼 {len(state.get('images', []))} image(s) added. "
            f"Filter: {FILTER_NAMES[selected_filter(state)]}",
            reply_markup=_image_tools_keyboard(),
        )

    @bot.message_handler(
        func=lambda m: getattr(m, "text", None) == PREVIEW_BUTTON
        and pdf_state.get(m.chat.id, {}).get("mode") == "images"
    )
    def preview_filtered_image(message):
        state = pdf_state[message.chat.id]
        images = state.get("images", [])
        if not images:
            bot.send_message(message.chat.id, "❌ Send an image first to preview it.")
            return
        try:
            output = make_preview(images[-1], selected_filter(state),
                                  auto_crop=selected_crop(state))
            try:
                bot.send_photo(
                    message.chat.id, output,
                    caption=f"👁 Preview: {FILTER_NAMES[selected_filter(state)]}\n"
                            f"Crop: {CROP_NAMES[selected_crop(state)]}\n"
                            "Preview shows the settings for every PDF page.",
                )
            finally:
                output.close()
        except ImageFilterError as error:
            bot.send_message(message.chat.id, str(error))
        except Exception as error:
            print("Image filter preview error:", type(error).__name__)
            bot.send_message(message.chat.id, "❌ Preview failed. Try another image.")

    @bot.message_handler(
        func=lambda m: getattr(m, "text", None) == REMOVE_BUTTON
        and pdf_state.get(m.chat.id, {}).get("mode") == "images"
    )
    def remove_last_image(message):
        images = pdf_state[message.chat.id].setdefault("images", [])
        if not images:
            bot.send_message(message.chat.id, "❌ No images to remove.")
            return
        images.pop()
        bot.send_message(
            message.chat.id,
            f"🗑 Last image removed. Remaining: {len(images)}",
            reply_markup=_image_tools_keyboard(),
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
            output = images_to_pdf(images, selected_filter(state),
                                   auto_crop=selected_crop(state))

            try:
                bot.send_document(
                    message.chat.id,
                    output,
                    caption=f"✅ PDF ready! Filter: {FILTER_NAMES[selected_filter(state)]} "
                            f"• Crop: {CROP_NAMES[selected_crop(state)]} "
                            f"• Pages: {len(images)}",
                )
            finally:
                output.close()

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
            if mode == "images" and (getattr(message.document, "file_size", 0) or 0) > MAX_IMAGE_BYTES:
                bot.send_message(chat_id, "❌ Image too large (12 MB maximum).")
                return
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

                total = enqueue_image(state, file_bytes)

                bot.send_message(
                    chat_id,
                    f"✅ Image added. Total: {total}/{MAX_IMAGES}. "
                    f"Filter: {FILTER_NAMES[selected_filter(state)]}",
                    reply_markup=_image_tools_keyboard(),
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

        except ImageFilterError as error:
            bot.send_message(chat_id, str(error))
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
            if (getattr(photo, "file_size", 0) or 0) > MAX_IMAGE_BYTES:
                bot.send_message(chat_id, "❌ Photo too large (12 MB maximum).")
                return

            image_bytes = _download_telegram_file(
                bot,
                photo.file_id,
            )

            total = enqueue_image(state, image_bytes)

            bot.send_message(
                chat_id,
                f"✅ Image added. Total: {total}/{MAX_IMAGES}. "
                f"Filter: {FILTER_NAMES[selected_filter(state)]}",
                reply_markup=_image_tools_keyboard(),
            )

        except ImageFilterError as error:
            bot.send_message(chat_id, str(error))
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
