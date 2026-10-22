import os
import io

from telebot import types
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from PIL import Image, ImageOps


# ==================================================
# USER DATA
# ==================================================

user_mode = {}

merge_files = {}
extract_files = {}
image_files = {}
rotate_files = {}
protect_files = {}


# ==================================================
# PAGE PARSER
# ==================================================

def parse_pages(text, total_pages):

    selected = []

    text = text.replace(" ", "")

    for part in text.split(","):

        if not part:
            continue

        if "-" in part:

            pieces = part.split("-")

            if len(pieces) != 2:
                raise ValueError("Invalid page range.")

            start = int(pieces[0])
            end = int(pieces[1])

            if start > end:
                raise ValueError(
                    f"Invalid range: {part}"
                )

            for page in range(start, end + 1):

                if page < 1 or page > total_pages:
                    raise ValueError(
                        f"Page {page} does not exist."
                    )

                selected.append(page)

        else:

            page = int(part)

            if page < 1 or page > total_pages:
                raise ValueError(
                    f"Page {page} does not exist."
                )

            selected.append(page)

    if not selected:
        raise ValueError(
            "No pages selected."
        )

    return selected


# ==================================================
# REGISTER ALL PDF HANDLERS
# ==================================================

def register_pdf_handlers(bot, show_main_menu):


    # ==============================================
    # PDF TOOLS MENU
    # ==============================================

    @bot.message_handler(
        func=lambda m: m.text == "📄 PDF Tools"
    )
    def pdf_tools(message):

        chat_id = message.chat.id

        user_mode.pop(chat_id, None)

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2
        )

        markup.add(
            types.KeyboardButton("🔗 Merge PDF"),
            types.KeyboardButton("✂️ Extract Pages"),

            types.KeyboardButton("🖼 Images → PDF"),
            types.KeyboardButton("🔄 Rotate PDF"),

            types.KeyboardButton("🔒 Protect PDF"),
            types.KeyboardButton("🗑 Clear Files"),

            types.KeyboardButton("⬅️ Main Menu")
        )

        bot.send_message(
            chat_id,
            """
📄 PDF Tools

Choose an option:
""",
            reply_markup=markup
        )


    # ==============================================
    # BACK TO PDF MENU
    # ==============================================

    @bot.message_handler(
        func=lambda m: m.text == "⬅️ PDF Tools"
    )
    def back_pdf(message):

        pdf_tools(message)


    # ==============================================
    # BACK TO MAIN
    # ==============================================

    @bot.message_handler(
        func=lambda m: m.text == "⬅️ Main Menu"
    )
    def back_main(message):

        chat_id = message.chat.id

        user_mode.pop(chat_id, None)

        name = (
            message.from_user.first_name
            or "Friend"
        )

        show_main_menu(
            chat_id,
            name
        )


    # ==============================================
    # MERGE PDF
    # ==============================================

    @bot.message_handler(
        func=lambda m: m.text == "🔗 Merge PDF"
    )
    def merge_menu(message):

        chat_id = message.chat.id

        user_mode[chat_id] = "merge"
        merge_files[chat_id] = []

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2
        )

        markup.add(
            types.KeyboardButton("✅ Merge Now"),
            types.KeyboardButton("🗑 Clear Files"),
            types.KeyboardButton("⬅️ PDF Tools")
        )

        bot.send_message(
            chat_id,
            """
🔗 PDF Merger

Send your PDFs one by one.

⚠️ Send them in the order you want.

When finished press:

✅ Merge Now
""",
            reply_markup=markup
        )


    # ==============================================
    # EXTRACT
    # ==============================================

    @bot.message_handler(
        func=lambda m: m.text == "✂️ Extract Pages"
    )
    def extract_menu(message):

        chat_id = message.chat.id

        user_mode[chat_id] = "extract"

        extract_files.pop(
            chat_id,
            None
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2
        )

        markup.add(
            types.KeyboardButton("🗑 Clear Files"),
            types.KeyboardButton("⬅️ PDF Tools")
        )

        bot.send_message(
            chat_id,
            """
✂️ Extract PDF Pages

Send ONE PDF.

After that send pages like:

1-3

2,5,8

1-3,7,10-12
""",
            reply_markup=markup
        )


    # ==============================================
    # IMAGE TO PDF
    # ==============================================

    @bot.message_handler(
        func=lambda m: m.text == "🖼 Images → PDF"
    )
    def image_menu(message):

        chat_id = message.chat.id

        user_mode[chat_id] = "images"

        image_files[chat_id] = []

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2
        )

        markup.add(
            types.KeyboardButton("✅ Create PDF"),
            types.KeyboardButton("🗑 Clear Files"),
            types.KeyboardButton("⬅️ PDF Tools")
        )

        bot.send_message(
            chat_id,
            """
🖼 Images → PDF

Send your images one by one.

Supported:

✅ JPG
✅ JPEG
✅ PNG
✅ Telegram Photos

When finished press:

✅ Create PDF
""",
            reply_markup=markup
        )


    # ==============================================
    # ROTATE
    # ==============================================

    @bot.message_handler(
        func=lambda m: m.text == "🔄 Rotate PDF"
    )
    def rotate_menu(message):

        chat_id = message.chat.id

        user_mode[chat_id] = "rotate"

        rotate_files.pop(
            chat_id,
            None
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2
        )

        markup.add(
            types.KeyboardButton("🗑 Clear Files"),
            types.KeyboardButton("⬅️ PDF Tools")
        )

        bot.send_message(
            chat_id,
            """
🔄 Rotate PDF

Send ONE PDF.

After uploading, choose:

↻ 90°
↻ 180°
↻ 270°

This version rotates all pages.
""",
            reply_markup=markup
        )


    # ==============================================
    # PROTECT
    # ==============================================

    @bot.message_handler(
        func=lambda m: m.text == "🔒 Protect PDF"
    )
    def protect_menu(message):

        chat_id = message.chat.id

        user_mode[chat_id] = "protect"

        protect_files.pop(
            chat_id,
            None
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2
        )

        markup.add(
            types.KeyboardButton("🗑 Clear Files"),
            types.KeyboardButton("⬅️ PDF Tools")
        )

        bot.send_message(
            chat_id,
            """
🔒 Password Protect PDF

Send ONE PDF file.

After uploading it,
I will ask you for a password.
""",
            reply_markup=markup
        )


    # ==============================================
    # CLEAR
    # ==============================================

    @bot.message_handler(
        func=lambda m: m.text == "🗑 Clear Files"
    )
    def clear_files(message):

        chat_id = message.chat.id

        merge_files.pop(chat_id, None)
        extract_files.pop(chat_id, None)
        image_files.pop(chat_id, None)
        rotate_files.pop(chat_id, None)
        protect_files.pop(chat_id, None)

        mode = user_mode.get(chat_id)

        if mode == "merge":
            merge_files[chat_id] = []

        elif mode == "images":
            image_files[chat_id] = []

        bot.send_message(
            chat_id,
            "🗑 Uploaded files cleared."
        )


    # ==============================================
    # RECEIVE TELEGRAM PHOTO
    # ==============================================

    @bot.message_handler(
        content_types=["photo"]
    )
    def receive_photo(message):

        chat_id = message.chat.id

        if user_mode.get(chat_id) != "images":

            bot.reply_to(
                message,
                """
❌ Select:

📄 PDF Tools
→ 🖼 Images → PDF

before sending photos.
"""
            )

            return

        try:

            photo = message.photo[-1]

            file_info = bot.get_file(
                photo.file_id
            )

            data = bot.download_file(
                file_info.file_path
            )

            if chat_id not in image_files:
                image_files[chat_id] = []

            image_files[chat_id].append(
                data
            )

            count = len(
                image_files[chat_id]
            )

            bot.reply_to(
                message,
                f"""
✅ Image #{count} received

Total images: {count}

Send another or press:

✅ Create PDF
"""
            )

        except Exception as e:

            bot.reply_to(
                message,
                f"❌ Image error:\n{e}"
            )


    # ==============================================
    # RECEIVE DOCUMENT
    # ==============================================

    @bot.message_handler(
        content_types=["document"]
    )
    def receive_document(message):

        chat_id = message.chat.id

        mode = user_mode.get(chat_id)

        file_name = (
            message.document.file_name
            or "file"
        )

        try:

            file_info = bot.get_file(
                message.document.file_id
            )

            data = bot.download_file(
                file_info.file_path
            )


            # ======================================
            # MERGE
            # ======================================

            if mode == "merge":

                if not file_name.lower().endswith(".pdf"):

                    bot.reply_to(
                        message,
                        "❌ Send PDF files only."
                    )

                    return

                merge_files.setdefault(
                    chat_id,
                    []
                )

                merge_files[chat_id].append(
                    {
                        "name": file_name,
                        "data": data
                    }
                )

                count = len(
                    merge_files[chat_id]
                )

                bot.reply_to(
                    message,
                    f"""
✅ PDF #{count} received

📄 {file_name}

Total PDFs: {count}
"""
                )


            # ======================================
            # EXTRACT
            # ======================================

            elif mode == "extract":

                if not file_name.lower().endswith(".pdf"):

                    bot.reply_to(
                        message,
                        "❌ Send a PDF file."
                    )

                    return

                reader = PdfReader(
                    io.BytesIO(data)
                )

                pages = len(
                    reader.pages
                )

                extract_files[chat_id] = {
                    "name": file_name,
                    "data": data,
                    "pages": pages
                }

                bot.reply_to(
                    message,
                    f"""
✅ PDF received

📄 {file_name}

📚 Total pages: {pages}

Now send page numbers.

Example:

1-3,6,10-12
"""
                )


            # ======================================
            # IMAGE DOCUMENT
            # ======================================

            elif mode == "images":

                ext = os.path.splitext(
                    file_name
                )[1].lower()

                if ext not in [
                    ".jpg",
                    ".jpeg",
                    ".png"
                ]:

                    bot.reply_to(
                        message,
                        """
❌ Supported:

JPG
JPEG
PNG
"""
                    )

                    return

                test_image = Image.open(
                    io.BytesIO(data)
                )

                test_image.verify()
                test_image.close()

                image_files.setdefault(
                    chat_id,
                    []
                )

                image_files[chat_id].append(
                    data
                )

                count = len(
                    image_files[chat_id]
                )

                bot.reply_to(
                    message,
                    f"""
✅ Image #{count} received

🖼 {file_name}

Total: {count}
"""
                )


            # ======================================
            # ROTATE
            # ======================================

            elif mode == "rotate":

                if not file_name.lower().endswith(".pdf"):

                    bot.reply_to(
                        message,
                        "❌ Send a PDF file."
                    )

                    return

                reader = PdfReader(
                    io.BytesIO(data)
                )

                pages = len(
                    reader.pages
                )

                rotate_files[chat_id] = {
                    "name": file_name,
                    "data": data
                }

                markup = types.ReplyKeyboardMarkup(
                    resize_keyboard=True,
                    row_width=3
                )

                markup.add(
                    types.KeyboardButton("↻ 90°"),
                    types.KeyboardButton("↻ 180°"),
                    types.KeyboardButton("↻ 270°"),
                    types.KeyboardButton("⬅️ PDF Tools")
                )

                bot.reply_to(
                    message,
                    f"""
✅ PDF received

📄 {file_name}

📚 Pages: {pages}

Choose rotation:
""",
                    reply_markup=markup
                )


            # ======================================
            # PROTECT
            # ======================================

            elif mode == "protect":

                if not file_name.lower().endswith(".pdf"):

                    bot.reply_to(
                        message,
                        "❌ Send a PDF file."
                    )

                    return

                reader = PdfReader(
                    io.BytesIO(data)
                )

                pages = len(
                    reader.pages
                )

                protect_files[chat_id] = {
                    "name": file_name,
                    "data": data
                }

                bot.reply_to(
                    message,
                    f"""
✅ PDF received

📄 {file_name}

📚 Pages: {pages}

🔑 Now send the password you want to use.

Example:

MyPDF123
"""
                )


            else:

                bot.reply_to(
                    message,
                    """
❌ Choose a tool first.

📄 PDF Tools
"""
                )


        except Exception as e:

            bot.reply_to(
                message,
                f"""
❌ Failed to process file.

Error:
{e}
"""
            )


    # ==============================================
    # MERGE NOW
    # ==============================================

    @bot.message_handler(
        func=lambda m: m.text == "✅ Merge Now"
    )
    def merge_now(message):

        chat_id = message.chat.id

        files = merge_files.get(
            chat_id,
            []
        )

        if len(files) < 2:

            bot.send_message(
                chat_id,
                "❌ Send at least 2 PDFs."
            )

            return

        status = bot.send_message(
            chat_id,
            "⏳ Merging PDFs..."
        )

        try:

            merger = PdfMerger()

            for pdf in files:

                merger.append(
                    io.BytesIO(
                        pdf["data"]
                    )
                )

            output = io.BytesIO()

            merger.write(output)
            merger.close()

            output.seek(0)

            output.name = "Merged_PDF.pdf"

            bot.send_document(
                chat_id,
                output,
                caption=f"""
✅ PDFs merged!

Files merged: {len(files)}
"""
            )

            merge_files[chat_id] = []

            try:

                bot.delete_message(
                    chat_id,
                    status.message_id
                )

            except Exception:
                pass


        except Exception as e:

            bot.send_message(
                chat_id,
                f"""
❌ Merge failed.

{e}
"""
            )


    # ==============================================
    # CREATE IMAGE PDF
    # ==============================================

    @bot.message_handler(
        func=lambda m: m.text == "✅ Create PDF"
    )
    def create_image_pdf(message):

        chat_id = message.chat.id

        data_list = image_files.get(
            chat_id,
            []
        )

        if not data_list:

            bot.send_message(
                chat_id,
                "❌ Send images first."
            )

            return

        status = bot.send_message(
            chat_id,
            "⏳ Creating PDF..."
        )

        images = []

        try:

            for data in data_list:

                img = Image.open(
                    io.BytesIO(data)
                )

                img = ImageOps.exif_transpose(
                    img
                )

                img.load()

                if img.mode != "RGB":

                    if "A" in img.getbands():

                        background = Image.new(
                            "RGB",
                            img.size,
                            "white"
                        )

                        background.paste(
                            img,
                            mask=img.getchannel("A")
                        )

                        img = background

                    else:

                        img = img.convert(
                            "RGB"
                        )

                images.append(img)

            output = io.BytesIO()

            images[0].save(
                output,
                "PDF",
                save_all=True,
                append_images=images[1:]
            )

            output.seek(0)

            output.name = "Images_To_PDF.pdf"

            bot.send_document(
                chat_id,
                output,
                caption=f"""
✅ PDF created

Images: {len(images)}
"""
            )

            image_files[chat_id] = []

            try:

                bot.delete_message(
                    chat_id,
                    status.message_id
                )

            except Exception:
                pass


        except Exception as e:

            bot.send_message(
                chat_id,
                f"""
❌ PDF creation failed.

{e}
"""
            )

        finally:

            for img in images:

                try:
                    img.close()

                except Exception:
                    pass


    # ==============================================
    # ROTATE FUNCTION
    # ==============================================

    def rotate_pdf(message, angle):

        chat_id = message.chat.id

        data = rotate_files.get(
            chat_id
        )

        if not data:

            bot.send_message(
                chat_id,
                "❌ Please upload a PDF first."
            )

            return

        status = bot.send_message(
            chat_id,
            f"⏳ Rotating PDF {angle}°..."
        )

        try:

            reader = PdfReader(
                io.BytesIO(
                    data["data"]
                )
            )

            writer = PdfWriter()

            for page in reader.pages:

                page.rotate(angle)

                writer.add_page(
                    page
                )

            output = io.BytesIO()

            writer.write(
                output
            )

            output.seek(0)

            output.name = (
                f"Rotated_{angle}_PDF.pdf"
            )

            bot.send_document(
                chat_id,
                output,
                caption=f"""
✅ PDF rotated successfully

🔄 Rotation: {angle}°
"""
            )

            rotate_files.pop(
                chat_id,
                None
            )

            try:

                bot.delete_message(
                    chat_id,
                    status.message_id
                )

            except Exception:
                pass


        except Exception as e:

            bot.send_message(
                chat_id,
                f"""
❌ Rotation failed.

{e}
"""
            )


    @bot.message_handler(
        func=lambda m: m.text == "↻ 90°"
    )
    def rotate_90(message):

        rotate_pdf(
            message,
            90
        )


    @bot.message_handler(
        func=lambda m: m.text == "↻ 180°"
    )
    def rotate_180(message):

        rotate_pdf(
            message,
            180
        )


    @bot.message_handler(
        func=lambda m: m.text == "↻ 270°"
    )
    def rotate_270(message):

        rotate_pdf(
            message,
            270
        )


    # ==============================================
    # EXTRACT PAGE NUMBERS
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        user_mode.get(m.chat.id) == "extract"
        and m.chat.id in extract_files
    )
    def extract_pages(message):

        chat_id = message.chat.id

        data = extract_files[
            chat_id
        ]

        try:

            pages = parse_pages(
                message.text,
                data["pages"]
            )

            status = bot.send_message(
                chat_id,
                "⏳ Extracting pages..."
            )

            reader = PdfReader(
                io.BytesIO(
                    data["data"]
                )
            )

            writer = PdfWriter()

            for number in pages:

                writer.add_page(
                    reader.pages[
                        number - 1
                    ]
                )

            output = io.BytesIO()

            writer.write(
                output
            )

            output.seek(0)

            output.name = (
                "Extracted_Pages.pdf"
            )

            bot.send_document(
                chat_id,
                output,
                caption=f"""
✅ Pages extracted

Pages:
{", ".join(map(str, pages))}
"""
            )

            extract_files.pop(
                chat_id,
                None
            )

            user_mode.pop(
                chat_id,
                None
            )

            try:

                bot.delete_message(
                    chat_id,
                    status.message_id
                )

            except Exception:
                pass


        except ValueError as e:

            bot.send_message(
                chat_id,
                f"""
❌ Invalid page selection.

{e}

Examples:

1-3
2,5,8
1-3,7,10-12
"""
            )


        except Exception as e:

            bot.send_message(
                chat_id,
                f"""
❌ Extraction failed.

{e}
"""
            )


    # ==============================================
    # PROTECT PDF PASSWORD
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        user_mode.get(m.chat.id) == "protect"
        and m.chat.id in protect_files
    )
    def protect_pdf(message):

        chat_id = message.chat.id

        password = message.text.strip()

        if len(password) < 4:

            bot.send_message(
                chat_id,
                """
❌ Password is too short.

Use at least 4 characters.
"""
            )

            return

        data = protect_files[
            chat_id
        ]

        status = bot.send_message(
            chat_id,
            "⏳ Protecting PDF..."
        )

        try:

            reader = PdfReader(
                io.BytesIO(
                    data["data"]
                )
            )

            writer = PdfWriter()

            for page in reader.pages:

                writer.add_page(
                    page
                )

            # AES-256 when supported
            try:

                writer.encrypt(
                    password,
                    algorithm="AES-256"
                )

            except TypeError:

                writer.encrypt(
                    password
                )

            output = io.BytesIO()

            writer.write(
                output
            )

            output.seek(0)

            output.name = (
                "Protected_PDF.pdf"
            )

            bot.send_document(
                chat_id,
                output,
                caption="""
🔒 PDF protected successfully!

⚠️ Remember your password.
"""
            )

            protect_files.pop(
                chat_id,
                None
            )

            user_mode.pop(
                chat_id,
                None
            )

            try:

                bot.delete_message(
                    chat_id,
                    status.message_id
                )

            except Exception:
                pass


        except Exception as e:

            bot.send_message(
                chat_id,
                f"""
❌ PDF protection failed.

{e}
"""
            )