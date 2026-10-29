"""Private, local DOCX/PPTX -> PDF conversions using LibreOffice.

Requires libreoffice/soffice executable on the HOST, not a Python-only PDF
library. No third-party conversion API; inputs are deleted after each request.
"""
from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import zipfile

DOCX_BUTTON = "📄 DOCX → PDF"
PPTX_BUTTON = "📊 PPTX → PDF"
MAX_INPUT_BYTES = 12 * 1024 * 1024
MAX_OUTPUT_BYTES = 18 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 120 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 12000
TIMEOUT_SECONDS = 100

class OfficePdfError(Exception):
    """Safe message for Telegram users; must not contain their document text."""


def locate_libreoffice() -> str | None:
    """Optional OFFICE_CONVERTER_BINARY environment variable for local Windows."""
    override = os.getenv("OFFICE_CONVERTER_BINARY", "").strip().strip('"')
    if override:
        path = Path(override)
        return str(path) if path.is_file() else None
    for name in ("libreoffice", "soffice"):
        path = shutil.which(name)
        if path:
            return path
    if os.name == "nt":
        for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)")):
            if base:
                path = Path(base) / "LibreOffice" / "program" / "soffice.exe"
                if path.is_file():
                    return str(path)
    return None


def _safe_filename(filename: str, extension: str) -> str:
    # Telegram file names are untrusted: output filename must be basename only.
    name = str(filename or "upload").replace("\\", "/").split("/")[-1]
    stem = Path(name).stem
    stem = re.sub(r"[^\w.\- ]+", "_", stem, flags=re.UNICODE).strip(" ._")
    if not stem:
        stem = "converted"
    return stem[:75] + extension


def _validate_document(blob: bytes, kind: str) -> None:
    if kind not in ("docx", "pptx"):
        raise ValueError("Unsupported conversion type")
    if not blob or len(blob) > MAX_INPUT_BYTES:
        raise OfficePdfError("File too large. Maximum upload is 12 MB.")
    try:
        with zipfile.ZipFile(BytesIO(blob)) as zf:
            members = zf.infolist()
            if len(members) > MAX_ARCHIVE_ENTRIES:
                raise OfficePdfError("Document has too many embedded parts.")
            total = 0
            for info in members:
                member = info.filename.replace("\\", "/")
                if member.startswith("/") or any(p == ".." for p in member.split("/")):
                    raise OfficePdfError("Unsafe document structure.")
                total += info.file_size
                if total > MAX_UNCOMPRESSED_BYTES:
                    raise OfficePdfError("Document is too complex for conversion.")
            names = {x.filename for x in members}
            required = "word/document.xml" if kind == "docx" else "ppt/presentation.xml"
            if "[Content_Types].xml" not in names or required not in names:
                raise OfficePdfError(f"Please send a valid .{kind.upper()} document.")
            # Catch damaged archives without trusting file extension alone.
            if zf.testzip() is not None:
                raise OfficePdfError("The document appears damaged. Please re-save it.")
    except (zipfile.BadZipFile, EOFError, OSError):
        raise OfficePdfError("This is not a valid Office document.") from None


def _execute(command: list[str], workdir: str) -> subprocess.CompletedProcess:
    """Run office in a separate process, kill it on timeout, never use shell."""
    proc = subprocess.Popen(
        command,
        cwd=workdir,
        env={**os.environ, "HOME": workdir, "SAL_USE_VCLPLUGIN": "svp", "DISPLAY": ""},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=(os.name != "nt"),
    )
    try:
        stdout, stderr = proc.communicate(timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        if os.name != "nt":
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            proc.kill()
        proc.communicate()
        raise OfficePdfError("Conversion timed out. Try a smaller document.") from None
    return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)


def convert_office_to_pdf(blob: bytes, filename: str, kind: str, *, binary: str | None = None) -> BytesIO:
    """Create a real PDF via Writer/Impress. Input/output stay in private temp dir."""
    if kind not in {"docx", "pptx"}:
        raise ValueError("Unsupported conversion type")
    if Path((filename or "").replace("\\", "/")).suffix.lower() != "." + kind:
        raise OfficePdfError(f"Please upload a .{kind.upper()} file for this tool.")
    _validate_document(blob, kind)
    lo_binary = binary or locate_libreoffice()
    if not lo_binary:
        raise OfficePdfError("Office conversion is not installed on this server. Ask the admin to enable LibreOffice.")

    with tempfile.TemporaryDirectory(prefix="student_office_pdf_") as temp:
        root = Path(temp)
        input_path = root / ("source." + kind)
        output_path = root / "source.pdf"
        profile = (root / "lo_profile").resolve().as_uri()
        input_path.write_bytes(blob)
        pdf_filter = "writer_pdf_Export" if kind == "docx" else "impress_pdf_Export"
        command = [
            str(lo_binary), f"-env:UserInstallation={profile}",
            "--headless", "--convert-to", f"pdf:{pdf_filter}",
            "--outdir", str(root), str(input_path),
        ]
        try:
            result = _execute(command, temp)
        except OfficePdfError:
            raise
        except (FileNotFoundError, PermissionError, OSError):
            raise OfficePdfError("LibreOffice could not start on this server.") from None
        if result.returncode != 0 or not output_path.exists():
            raise OfficePdfError("Conversion failed. Try reopening and saving the file in Office first.")
        size = output_path.stat().st_size
        if size < 8 or size > MAX_OUTPUT_BYTES:
            raise OfficePdfError("Converted PDF is empty or too large to send (max 18 MB).")
        pdf_bytes = output_path.read_bytes()
        if not pdf_bytes.startswith(b"%PDF-"):
            raise OfficePdfError("Office did not generate a valid PDF.")
    out = BytesIO(pdf_bytes)
    out.name = _safe_filename(filename, ".pdf")
    return out


# Prevent concurrent conversion from exhausting a small Render instance.
_conversion_slot = threading.BoundedSemaphore(1)


def register_office_to_pdf_handlers(bot, open_pdf_tools, clear_pdf_state, show_main_menu):
    """Register BEFORE other generic PDF/document handlers, called from pdf_tools.py.

    Returns mode dict for tests; no user document is retained after processing.
    """
    from telebot import types
    from telebot.handler_backends import ContinueHandling

    state = {}
    supported_buttons = {DOCX_BUTTON: "docx", PPTX_BUTTON: "pptx"}

    def _private(m):
        return getattr(getattr(m, "chat", None), "type", None) == "private"

    def _menu():
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        keyboard.row(types.KeyboardButton("🔙 PDF Tools"), types.KeyboardButton("🏠 Main Menu"))
        keyboard.add(types.KeyboardButton("❌ Cancel"))
        return keyboard

    @bot.message_handler(commands=["docxpdf", "pptxpdf"])
    @bot.message_handler(func=lambda m: getattr(m, "text", "") in supported_buttons)
    def start(m):
        chat_id = m.chat.id
        if not _private(m):
            bot.send_message(chat_id, "🔒 Please use this tool in a private chat with the bot.")
            return
        text = (m.text or "").split(" ", 1)[0].split("@", 1)[0].lower()
        kind = (supported_buttons.get(m.text) or ("pptx" if text == "/pptxpdf" else "docx"))
        clear_pdf_state(chat_id)
        state[chat_id] = {"kind": kind, "busy": False}
        bot.send_message(
            chat_id,
            f"📄 {kind.upper()} → PDF\n\nUpload one .{kind} file (maximum 12 MB).\n"
            "I will convert and send the PDF here.\n"
            "Formatting is preserved as closely as LibreOffice allows.\n"
            "Use 🔙 PDF Tools or ❌ Cancel to exit.",
            reply_markup=_menu(),
        )

    @bot.message_handler(func=lambda m: m.chat.id in state and getattr(m, "text", "") in ("🔙 PDF Tools", "❌ Cancel"))
    def back(m):
        state.pop(m.chat.id, None)
        open_pdf_tools(m.chat.id)

    @bot.message_handler(func=lambda m: m.chat.id in state and getattr(m, "text", "") == "🏠 Main Menu")
    def main_menu(m):
        state.pop(m.chat.id, None)
        show_main_menu(m.chat.id, getattr(m.from_user, "first_name", None) or "Friend")

    @bot.message_handler(
        content_types=["text"],
        func=lambda m: m.chat.id in state and (
            (getattr(m, "text", "") or "").startswith("/") or
            getattr(m, "text", "") in (
                "📄 PDF Tools", "🔗 Merge PDFs", "✂️ Extract Pages", "🖼 Images → PDF",
                "📝 Text → PDF", "🔄 Rotate PDF", "🔐 Protect PDF",
                "🎙 Voice Notes", "🎙 Voice & PDF", "🖼 Photo/Image Crop", "📸 Scan Document",
                "ℹ️ Help", "🏠 Main Menu", "⬅️ Main Menu",
            )
        ),
    )
    def yield_other_tools(m):
        state.pop(m.chat.id, None)
        return ContinueHandling()

    @bot.message_handler(content_types=["text"], func=lambda m: m.chat.id in state)
    def awaiting_file(m):
        selected = state[m.chat.id]["kind"].upper()
        bot.send_message(m.chat.id, f"📎 Please attach a .{selected} file as a Telegram document, not pasted text.")

    @bot.message_handler(content_types=["document"], func=lambda m: m.chat.id in state)
    def document_to_pdf(m):
        chat_id = m.chat.id
        kind = state[chat_id]["kind"]
        if state[chat_id].get("busy"):
            bot.send_message(chat_id, "⏳ Your previous document is still converting. Please wait.")
            return
        document = m.document
        filename = str(getattr(document, "file_name", "") or "")
        if not filename.lower().endswith("." + kind):
            bot.send_message(chat_id, f"❌ Please upload a .{kind.upper()} file. Other PDF tools have separate buttons.")
            return
        if getattr(document, "file_size", 0) and document.file_size > MAX_INPUT_BYTES:
            bot.send_message(chat_id, "❌ File too large. Maximum upload: 12 MB.")
            return
        if not _conversion_slot.acquire(blocking=False):
            bot.send_message(chat_id, "⏳ Another conversion is in progress. Try again shortly.")
            return
        # Return from the Telegram webhook quickly. A large PPTX can take >10s;
        # processing it synchronously can cause Telegram to retry the update.
        job_token = object()
        state[chat_id]["busy"] = True
        state[chat_id]["job_token"] = job_token

        def _still_current():
            return state.get(chat_id, {}).get("job_token") is job_token

        def _convert_in_background():
            try:
                file_info = bot.get_file(document.file_id)
                blob = bot.download_file(file_info.file_path)
                pdf = convert_office_to_pdf(blob, filename, kind)
                try:
                    if _still_current():
                        bot.send_document(chat_id, pdf, caption="✅ Converted PDF is ready! 📄")
                finally:
                    pdf.close()
                if _still_current():
                    state.pop(chat_id, None)
                    open_pdf_tools(chat_id)
            except OfficePdfError as exc:
                if _still_current():
                    bot.send_message(chat_id, "❌ " + str(exc) + "\nPlease upload a different file or tap Cancel.")
            except Exception as exc:
                print("Office PDF conversion failed:", type(exc).__name__)
                if _still_current():
                    bot.send_message(chat_id, "❌ Conversion failed temporarily. Try again later.")
            finally:
                active = state.get(chat_id)
                if active and active.get("job_token") is job_token:
                    active["busy"] = False
                    active.pop("job_token", None)
                _conversion_slot.release()

        try:
            bot.send_message(chat_id, "⏳ Converting your file to PDF. Please wait...")
            threading.Thread(
                target=_convert_in_background,
                name="office_pdf_converter",
                daemon=True,
            ).start()
        except Exception as exc:
            # Critical: prevent a locked converter if thread creation fails.
            print("Office PDF worker start failed:", type(exc).__name__)
            if _still_current():
                state[chat_id]["busy"] = False
                state[chat_id].pop("job_token", None)
            _conversion_slot.release()
            bot.send_message(chat_id, "❌ Unable to start conversion. Please retry later.")

    @bot.message_handler(content_types=["photo"], func=lambda m: m.chat.id in state)
    def cannot_convert_photo(m):
        bot.send_message(m.chat.id, "Please upload a DOCX or PPTX document, not an image.")

    return state
