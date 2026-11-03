"""V7.13: private-chat DOCX/PPTX -> PDF conversion, no external conversion API.

Uses LibreOffice for layout rendering IF installed, otherwise produces a clearly
labelled basic-content PDF locally with python-docx/python-pptx and fpdf2.
Existing PDF modes, AI modules, and database functions are unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import BadZipFile, ZipFile

from telebot import types
from text_pdf_v711 import find_fonts, TextPdfError, _paragraph_align, _normalise_input, _has_complex_script

DOCX_BUTTON = "📄 DOCX → PDF"
PPTX_BUTTON = "📊 PPTX → PDF"
MAX_INPUT_BYTES = 12 * 1024 * 1024
MAX_OUTPUT_BYTES = 45 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_ZIP_ENTRIES = 2500
MAX_SLIDES = 100
MAX_PARAGRAPHS = 5000
MAX_IMAGE_BYTES = 12 * 1024 * 1024
CONVERSION_TIMEOUT = 75


class OfficePdfError(Exception):
    """Friendly, non-sensitive errors for users."""


@dataclass
class ConversionResult:
    pdf: BytesIO
    backend: str
    warning: str = ""


def _validate_office_document(blob: bytes, kind: str) -> None:
    """Reject incorrect/oversized/macro-enabled OOXML files before parsing."""
    if kind not in ("docx", "pptx"):
        raise OfficePdfError("Choose DOCX or PPTX conversion.")
    if not blob:
        raise OfficePdfError("The uploaded file is empty.")
    if len(blob) > MAX_INPUT_BYTES:
        raise OfficePdfError("The file is too large. Maximum 12 MB.")
    try:
        with ZipFile(BytesIO(blob)) as archive:
            names = archive.namelist()
            if len(names) > MAX_ZIP_ENTRIES:
                raise OfficePdfError("The file contains too many internal parts.")
            needed = "word/document.xml" if kind == "docx" else "ppt/presentation.xml"
            if "[Content_Types].xml" not in names or needed not in names:
                raise OfficePdfError(f"Please upload a valid .{kind.upper()} document.")
            if any("vbaproject.bin" in name.lower() or "macros/" in name.lower() for name in names):
                raise OfficePdfError("Macro-enabled files are not supported.")
            total = sum(info.file_size for info in archive.infolist())
            if total > MAX_UNCOMPRESSED_BYTES:
                raise OfficePdfError("The uncompressed document is too large.")
            if any(info.flag_bits & 1 for info in archive.infolist()):
                raise OfficePdfError("Password-protected documents are not supported.")
            if any(info.file_size > MAX_UNCOMPRESSED_BYTES // 2 for info in archive.infolist()):
                raise OfficePdfError("The document contains an oversized part.")
    except OfficePdfError:
        raise
    except (BadZipFile, ValueError, OSError) as exc:
        raise OfficePdfError(f"Please upload a valid .{kind.upper()} document.") from exc


def _safe_filename(name: str, kind: str) -> str:
    stem = Path((name or "document").replace("\\", "/")).stem
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", stem).strip("_-")[:60]
    return f"{stem or kind}_converted.pdf"


def _libreoffice_executable() -> str | None:
    configured = os.getenv("OFFICE_PDF_LIBREOFFICE", "").strip()
    if configured:
        if Path(configured).is_file():
            return configured
        return shutil.which(configured)
    for candidate in ("libreoffice", "soffice"):
        found = shutil.which(candidate)
        if found:
            return found
    if os.name == "nt":
        for root in (os.getenv("PROGRAMFILES"), os.getenv("PROGRAMFILES(X86)")):
            if root:
                found = Path(root) / "LibreOffice" / "program" / "soffice.exe"
                if found.is_file():
                    return str(found)
    return None


def _with_libreoffice(blob: bytes, kind: str, binary: str) -> bytes:
    """Convert in a private disposable directory; never invoke a shell."""
    with tempfile.TemporaryDirectory(prefix="student_officepdf_") as directory:
        root = Path(directory)
        source = root / f"input.{kind}"
        source.write_bytes(blob)
        outdir = root / "out"
        outdir.mkdir()
        profile = root / "profile"
        profile.mkdir()
        pdf_filter = "writer_pdf_Export" if kind == "docx" else "impress_pdf_Export"
        command = [
            binary, f"-env:UserInstallation={profile.as_uri()}",
            "--headless", "--convert-to", f"pdf:{pdf_filter}",
            "--outdir", str(outdir), str(source),
        ]
        try:
            completed = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=CONVERSION_TIMEOUT, check=False, cwd=str(root),
            )
        except subprocess.TimeoutExpired as exc:
            raise OfficePdfError("Document conversion took too long. Try a smaller document.") from exc
        except OSError as exc:
            raise OfficePdfError("Document converter could not start.") from exc
        output = outdir / "input.pdf"
        if completed.returncode != 0 or not output.is_file():
            raise OfficePdfError("Could not convert this document. Check the file format.")
        if not 0 < output.stat().st_size <= MAX_OUTPUT_BYTES:
            raise OfficePdfError("The converted PDF is too large to send.")
        pdf = output.read_bytes()
        if not pdf.startswith(b"%PDF-"):
            raise OfficePdfError("The converter did not produce a valid PDF.")
        return pdf


def _init_pdf(format_name="A4", complex_script=False):
    try:
        from fpdf import FPDF
    except ImportError as exc:
        raise OfficePdfError("PDF conversion packages are missing; contact the administrator.") from exc
    try:
        fonts = find_fonts()
    except TextPdfError as exc:
        raise OfficePdfError(str(exc)) from exc
    pdf = FPDF(unit="mm", format=format_name)
    for family, file in fonts.items():
        pdf.add_font(family, fname=file)
    pdf.set_fallback_fonts(["Tamil", "Sinhala", "Arabic"], exact_match=False)
    try:
        pdf.set_text_shaping(True)
    except Exception as exc:
        if complex_script:
            raise OfficePdfError("Multilingual text rendering needs uharfbuzz. Install requirements.txt.") from exc
    pdf.set_title("Document converted by Student Assistant Bot")
    pdf.set_author("Student Assistant Bot")
    return pdf


def _add_wrapped(pdf, text: str, *, size=10.5, space=6.8, color=(35, 43, 53)):
    cleaned = _normalise_input(text or "")
    if not cleaned:
        pdf.ln(3)
        return
    pdf.set_font("Base", size=size)
    pdf.set_text_color(*color)
    for line in cleaned.split("\n"):
        if not line:
            pdf.ln(3)
            continue
        # Word sometimes contains exceedingly long unbreakable strings.
        # fpdf2 can wrap by character with its font metrics; fail cleanly if not.
        try:
            pdf.multi_cell(0, space, line[:15000], align=_paragraph_align(line),
                           new_x="LMARGIN", new_y="NEXT")
        except Exception as exc:
            raise OfficePdfError("Some text could not be laid out as PDF.") from exc


def _basic_docx(blob: bytes) -> bytes:
    try:
        from docx import Document
        from docx.oxml.ns import qn
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        document = Document(BytesIO(blob))
    except Exception as exc:
        raise OfficePdfError("This DOCX file could not be opened.") from exc
    complex_script = _has_complex_script(" ".join(p.text for p in document.paragraphs))
    if not complex_script:
        complex_script = any(_has_complex_script(c.text) for table in document.tables
                             for row in table.rows for c in row.cells)
    pdf = _init_pdf(complex_script=complex_script)
    pdf.set_margins(17, 17, 17)
    pdf.set_auto_page_break(True, margin=17)
    pdf.add_page()
    blocks = 0
    for elem in document.element.body.iterchildren():
        blocks += 1
        if blocks > MAX_PARAGRAPHS:
            raise OfficePdfError("This document is too long to convert in basic mode.")
        if elem.tag == qn("w:p"):
            p = Paragraph(elem, document)
            name = (p.style.name or "") if p.style is not None else ""
            text = p.text
            if name.lower().startswith("list bullet"):
                text = "• " + text
            elif name.lower().startswith("list number"):
                text = "- " + text
            if not text.strip():
                pdf.ln(3)
                continue
            heading = name.lower().startswith(("heading", "title", "subtitle"))
            _add_wrapped(pdf, text, size=14 if heading else 10.5,
                         space=8.5 if heading else 6.6,
                         color=(22, 63, 105) if heading else (38, 45, 55))
            pdf.ln(1.6)
        elif elem.tag == qn("w:tbl"):
            table = Table(elem, document)
            for row in table.rows:
                _add_wrapped(pdf, "  |  ".join(cell.text for cell in row.cells),
                             size=9.0, space=6.1)
            pdf.ln(3)
    # Basic renderer adds embedded images after the text (not at original positions).
    image_parts = []
    for part in document.part.related_parts.values():
        content_type = str(getattr(part, "content_type", ""))
        if content_type.startswith("image/"):
            raw = getattr(part, "blob", b"")
            if raw and len(raw) < MAX_IMAGE_BYTES:
                image_parts.append(raw)
    if image_parts:
        pdf.add_page()
        _add_wrapped(pdf, "Embedded images", size=13)
        for raw in image_parts[:35]:
            try:
                from PIL import Image
                with Image.open(BytesIO(raw)) as image:
                    width_px, height_px = image.size
                    if width_px * height_px > 35_000_000:
                        continue
                    if image.format not in ("PNG", "JPEG", "WEBP"):
                        continue
                # Do not enlarge beyond the PDF content width or 80mm height.
                scale = min(172 / width_px, 85 / height_px)
                w, h = width_px * scale, height_px * scale
                if pdf.get_y() + h > pdf.h - 18:
                    pdf.add_page()
                pdf.image(BytesIO(raw), x=17, y=pdf.get_y(), w=w, h=h)
                pdf.set_y(pdf.get_y() + h + 5)
            except Exception:
                continue
    result = bytes(pdf.output())
    if len(result) > MAX_OUTPUT_BYTES:
        raise OfficePdfError("The converted PDF is too large to send.")
    return result


def _emu_mm(emu):
    return float(emu) / 36000.0


def _rgb(value, default=(35, 43, 53)):
    """Resolve explicit RGB; theme colors safely use defaults."""
    try:
        value = value.rgb
        if value is not None:
            return tuple(value)
    except (AttributeError, TypeError):
        pass
    return default


def _basic_pptx(blob: bytes) -> bytes:
    try:
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE_TYPE
        deck = Presentation(BytesIO(blob))
    except Exception as exc:
        raise OfficePdfError("This PowerPoint file could not be opened.") from exc
    if not deck.slides:
        raise OfficePdfError("This presentation has no slides.")
    if len(deck.slides) > MAX_SLIDES:
        raise OfficePdfError("Maximum 100 slides for PPTX conversion.")
    width, height = _emu_mm(deck.slide_width), _emu_mm(deck.slide_height)
    if width <= 0 or height <= 0 or width > 1500 or height > 1500:
        raise OfficePdfError("The presentation has invalid slide dimensions.")
    complex_script = any(_has_complex_script(sh.text_frame.text) for sl in deck.slides
                         for sh in sl.shapes if getattr(sh, "has_text_frame", False))
    pdf = _init_pdf(format_name=(width, height), complex_script=complex_script)
    pdf.set_auto_page_break(False)
    for slide in deck.slides:
        pdf.add_page()
        # Slide backgrounds: render direct solid colors when available.
        try:
            fill = slide.background.fill
            if fill.type is not None and fill.fore_color.type is not None:
                color = _rgb(fill.fore_color, (255, 255, 255))
                pdf.set_fill_color(*color)
                pdf.rect(0, 0, width, height, style="F")
        except (AttributeError, ValueError, TypeError):
            pass
        for shape in slide.shapes:
            x, y = _emu_mm(shape.left), _emu_mm(shape.top)
            w, h = _emu_mm(shape.width), _emu_mm(shape.height)
            if w <= 0 or h <= 0:
                continue
            # Simplified geometry for common shapes; images retain size and position.
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                try:
                    raw = shape.image.blob
                    if len(raw) < MAX_IMAGE_BYTES:
                        pdf.image(BytesIO(raw), x=x, y=y, w=w, h=h, keep_aspect_ratio=True)
                except Exception:
                    pass
            else:
                try:
                    fill = shape.fill
                    if fill.type is not None and fill.fore_color.type is not None:
                        color = _rgb(fill.fore_color, (255, 255, 255))
                        pdf.set_fill_color(*color)
                        pdf.rect(x, y, w, h, style="F")
                except (AttributeError, ValueError, TypeError):
                    pass
            if not getattr(shape, "has_text_frame", False):
                continue
            text = _normalise_input(shape.text_frame.text)
            if not text:
                continue
            # A conservative, selectable-text rendering in the original text box.
            try:
                first_run = next(
                    (run for paragraph in shape.text_frame.paragraphs for run in paragraph.runs), None
                )
                pts = first_run.font.size.pt if first_run and first_run.font.size else 18
                font_mm = max(8, min(30, float(pts)))
                color = _rgb(first_run.font.color, (25, 28, 38)) if first_run else (25, 28, 38)
                pdf.set_text_color(*color)
                pdf.set_font("Base", size=font_mm)
                pdf.set_xy(max(0.5, x + 1), max(0.5, y + 1))
                content_w = max(1, min(w - 2, width - x - 1))
                line_height = font_mm * 0.43
                pdf.multi_cell(content_w, line_height, text=text[:4500],
                               align=_paragraph_align(text),
                               new_x="LEFT", new_y="NEXT")
            except Exception:
                # Do not discard the entire document because of one unsupported shape.
                continue
    result = bytes(pdf.output())
    if len(result) > MAX_OUTPUT_BYTES:
        raise OfficePdfError("The converted PDF is too large to send.")
    return result


def convert_document(blob: bytes, kind: str, filename: str = "document") -> ConversionResult:
    """Produce PDF, never sending the original document to an external API."""
    _validate_office_document(blob, kind)
    binary = _libreoffice_executable()
    if binary:
        pdf_bytes = _with_libreoffice(blob, kind, binary)
        backend, warning = "libreoffice", ""
    else:
        pdf_bytes = _basic_docx(blob) if kind == "docx" else _basic_pptx(blob)
        backend = "basic"
        warning = "Basic PDF: advanced formatting, diagrams, and animations may differ."
    if not pdf_bytes.startswith(b"%PDF-"):
        raise OfficePdfError("Conversion failed to create a valid PDF.")
    result = BytesIO(pdf_bytes)
    result.name = _safe_filename(filename, kind)
    result.seek(0)
    return ConversionResult(result, backend, warning)


def _is_private(message) -> bool:
    return getattr(getattr(message, "chat", None), "type", "private") == "private"


def register_office_pdf_v713(bot, pdf_state: dict, pdf_menu, mode_keyboard) -> None:
    """Register before the legacy PDF/document handlers, leaving them untouched."""
    modes = {"docx": "office_pdf_docx", "pptx": "office_pdf_pptx"}
    labels = {"docx": DOCX_BUTTON, "pptx": PPTX_BUTTON}

    @bot.message_handler(commands=["docxpdf", "pptxpdf"])
    @bot.message_handler(func=lambda m: getattr(m, "text", "") in (DOCX_BUTTON, PPTX_BUTTON))
    def start_office_pdf(message):
        if not _is_private(message):
            bot.send_message(message.chat.id, "🔒 Open a private chat with the bot to convert documents.")
            return
        incoming = message.text or ""
        command = incoming.split()[0].split("@", 1)[0] if incoming else ""
        kind = "pptx" if incoming == PPTX_BUTTON or command == "/pptxpdf" else "docx"
        pdf_state[message.chat.id] = {"mode": modes[kind]}
        bot.send_message(
            message.chat.id,
            f"{labels[kind]}\n\nSend one .{kind.upper()} file as a Telegram document "
            f"(maximum 12 MB).\nNo external conversion API is used.\n"
            "Advanced layout is preserved when LibreOffice is available; "
            "otherwise a basic PDF is created.",
            reply_markup=mode_keyboard(["🔙 PDF Tools", "🏠 Main Menu"], "❌ Cancel"),
        )

    @bot.message_handler(
        func=lambda m: getattr(m, "text", "") == "❌ Cancel"
        and pdf_state.get(m.chat.id, {}).get("mode") in modes.values(),
    )
    def cancel_office_pdf(message):
        pdf_menu(bot, message.chat.id)

    @bot.message_handler(
        func=lambda m: pdf_state.get(m.chat.id, {}).get("mode") in modes.values(),
        content_types=["document"],
    )
    def receive_office_pdf(message):
        chat_id = message.chat.id
        if not _is_private(message):
            pdf_state.pop(chat_id, None)
            bot.send_message(chat_id, "🔒 Private chats only.")
            return
        kind = "pptx" if pdf_state[chat_id]["mode"] == modes["pptx"] else "docx"
        document = getattr(message, "document", None)
        name = getattr(document, "file_name", "") or ""
        if Path(name).suffix.lower() != "." + kind:
            bot.send_message(chat_id, f"❌ Please upload a .{kind.upper()} file, not another format.")
            return
        size = getattr(document, "file_size", None)
        if size is not None and size > MAX_INPUT_BYTES:
            bot.send_message(chat_id, "❌ File too large (maximum 12 MB).")
            return
        bot.send_chat_action(chat_id, "upload_document")
        try:
            file_info = bot.get_file(document.file_id)
            blob = bot.download_file(file_info.file_path)
            answer = convert_document(blob, kind, name)
            try:
                caption = "✅ PDF ready!"
                if answer.warning:
                    caption += "\n⚠️ " + answer.warning
                bot.send_document(chat_id, answer.pdf, caption=caption)
            finally:
                answer.pdf.close()
        except OfficePdfError as exc:
            bot.send_message(chat_id, "❌ " + str(exc))
            return
        except Exception as exc:
            print("V7.13 office PDF error:", type(exc).__name__)
            bot.send_message(chat_id, "❌ Could not convert this document. Try a smaller valid file.")
            return
        pdf_menu(bot, chat_id)

    @bot.message_handler(
        func=lambda m: pdf_state.get(m.chat.id, {}).get("mode") in modes.values(),
        content_types=["photo"],
    )
    def reject_photo(message):
        kind = "PPTX" if pdf_state[message.chat.id]["mode"] == modes["pptx"] else "DOCX"
        bot.send_message(message.chat.id, f"📄 Send a {kind} file using Telegram's File/Document option.")
