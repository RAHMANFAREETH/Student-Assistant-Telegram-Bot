"""V7.11 - private, in-memory Text to PDF conversion (no AI or database calls).

PDF generation uses fpdf2 with HarfBuzz shaping and Noto Unicode fonts.
Unicode font files are obtained separately on the user's own deployment by
INSTALL_TEXT_PDF_FONTS.py; none are bundled with this source distribution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import os
from pathlib import Path
import unicodedata

MAX_TEXT_CHARS = 20_000
MAX_TEXT_MESSAGES = 30
PDF_TEXT_MODE = "text_pdf_collect"
PDF_TEXT_BUTTON = "📝 Text → PDF"
PDF_TEXT_CREATE = "✅ Create Text PDF"
PDF_TEXT_CLEAR = "🧹 Clear Text"


class TextPdfError(Exception):
    """A recoverable PDF creation/configuration error."""


FONT_FILES = {
    "Base": "NotoSans-Regular.ttf",
    "Tamil": "NotoSansTamil-Regular.ttf",
    "Sinhala": "NotoSansSinhala-Regular.ttf",
    "Arabic": "NotoSansArabic-Regular.ttf",
}


def _candidate_font_locations(filename: str):
    configured = os.environ.get("TEXT_PDF_FONT_DIR", "").strip()
    if configured:
        yield Path(configured) / filename
    yield Path(__file__).resolve().parent / "pdf_fonts" / filename
    yield Path("/usr/share/fonts/truetype/noto") / filename
    yield Path("/usr/share/fonts/truetype") / filename
    if filename == "NotoSans-Regular.ttf":
        yield Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    if os.name == "nt" and filename == "NotoSans-Regular.ttf":
        yield Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arial.ttf"


def find_fonts():
    """Find all four expected fonts on the bot server; never download at runtime."""
    resolved = {}
    missing = []
    for family, filename in FONT_FILES.items():
        path = next((p for p in _candidate_font_locations(filename) if p.is_file()), None)
        if path:
            resolved[family] = str(path)
        else:
            missing.append(filename)
    if missing:
        raise TextPdfError(
            "Required PDF fonts are missing: " + ", ".join(missing)
            + ". Ask the bot administrator to run INSTALL_TEXT_PDF_FONTS.py "
            "during the Render build."
        )
    return resolved


def _normalise_input(text: str) -> str:
    """Plain text only. No HTML/markdown evaluation, file reads, or URL fetches."""
    if not isinstance(text, str):
        raise TextPdfError("Please send a text message.")
    normal = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    # Keep tabs readable; remove other control characters (except linefeeds).
    normal = "".join(
        "    " if ch == "\t" else ch
        for ch in normal
        if ch == "\n" or ch == "\t" or unicodedata.category(ch) != "Cc"
    )
    return normal.strip()


def _has_complex_script(text: str) -> bool:
    return any(
        (0x0B80 <= ord(c) <= 0x0BFF)
        or (0x0D80 <= ord(c) <= 0x0DFF)
        or (0x0600 <= ord(c) <= 0x08FF)
        or (0xFB50 <= ord(c) <= 0xFEFF)
        for c in text
    )


def _paragraph_align(text: str) -> str:
    """Use the paragraph's first strong directional character for alignment."""
    for char in text:
        kind = unicodedata.bidirectional(char)
        if kind in {"R", "AL"}:
            return "R"
        if kind == "L":
            return "L"
    return "L"


def create_text_pdf(text: str, *, now=None) -> BytesIO:
    """Produce an A4 selectable-text PDF in memory, with page numbering.

    The bot does not persist submitted text to disk or to Supabase.
    """
    content = _normalise_input(text)
    if not content:
        raise TextPdfError("Send some text before creating the PDF.")
    if len(content) > MAX_TEXT_CHARS:
        raise TextPdfError(f"Text is too long (maximum {MAX_TEXT_CHARS:,} characters).")
    fonts = find_fonts()

    try:
        from fpdf import FPDF
    except ImportError as exc:
        raise TextPdfError("PDF library missing: install the updated requirements.txt.") from exc

    class NotesPDF(FPDF):
        def footer(self):
            self.set_y(-14)
            self.set_font("Base", size=8)
            self.set_text_color(95, 107, 117)
            self.cell(0, 7, text=f"Page {self.page_no()}", align="C")

    pdf = NotesPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(left=17, top=18, right=17)
    pdf.set_title("Text Notes")
    pdf.set_author("Student Assistant Bot")
    for family, path in fonts.items():
        pdf.add_font(family, fname=path)
    pdf.set_fallback_fonts(["Tamil", "Sinhala", "Arabic"], exact_match=False)

    try:
        pdf.set_text_shaping(True)
    except Exception as exc:
        # Latin text can remain searchable with fpdf2's native font handling.
        # Complex scripts must NEVER silently render without shaping.
        if _has_complex_script(content):
            raise TextPdfError(
                "Multilingual PDF support needs uharfbuzz. "
                "Ask the administrator to install the updated requirements.txt."
            ) from exc

    pdf.add_page()
    pdf.set_text_color(27, 49, 63)
    pdf.set_font("Base", size=15)
    pdf.cell(0, 10, text="Text Notes", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(195, 211, 218)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(5)
    pdf.set_text_color(30, 37, 45)
    pdf.set_font("Base", size=11)

    for line in content.split("\n"):
        if not line.strip():
            if pdf.get_y() + 8 >= pdf.h - pdf.b_margin:
                pdf.add_page()
            else:
                pdf.ln(6)
            continue
        try:
            pdf.multi_cell(
                w=0,
                h=7.5,
                text=line,
                align=_paragraph_align(line),
                new_x="LMARGIN",
                new_y="NEXT",
            )
        except Exception as exc:
            raise TextPdfError("Could not lay out this text. Try shorter lines.") from exc

    current = now if now is not None else datetime.now(timezone.utc)
    try:
        payload = pdf.output()
    except Exception as exc:
        raise TextPdfError("Could not generate PDF. Check the installed Unicode fonts.") from exc

    output = BytesIO(bytes(payload))
    output.name = f"text_notes_{current:%Y%m%d_%H%M%S}.pdf"
    output.seek(0)
    return output
