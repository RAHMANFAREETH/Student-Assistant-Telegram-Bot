"""Offline CI smoke test using the actual Student Assistant DOCX->PDF converter.

Produces a generated, nonsensitive DOCX, converted PDF and rendered preview.
No bot token, Telegram account, network request, or production database needed.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from pypdf import PdfReader
import pypdfium2 as pdfium

from office_to_pdf_v713 import OfficePdfError, convert_office_to_pdf
from office_font_catalog_v130 import missing_exact_fonts

SAMPLES = (
    ("Tamil", "வணக்கம்! தமிழ் மொழி நமது பெருமை.", "Noto Sans Tamil", False),
    ("English", "Student Assistant Four-Language PDF Test", "Liberation Sans", False),
    ("Arabic", "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "Noto Naskh Arabic", True),
    ("Sinhala", "ආයුබෝවන්! සිංහල භාෂාව අපේ උරුමයයි.", "Noto Sans Sinhala", False),
)


def add_sample(doc: Document, label: str, text: str, font: str, rtl: bool) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(18)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT if rtl else WD_ALIGN_PARAGRAPH.LEFT
    if rtl:
        ppr = paragraph._p.get_or_add_pPr()
        bidi = OxmlElement("w:bidi")
        bidi.set(qn("w:val"), "1")
        ppr.append(bidi)
    run = paragraph.add_run(text)
    run.font.name = font
    run.font.size = Pt(17)
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.rFonts
    if fonts is not None:
        for attr in ("w:eastAsia", "w:cs"):
            fonts.set(qn(attr), font)
    if rtl:
        flag = OxmlElement("w:rtl")
        flag.set(qn("w:val"), "1")
        rpr.append(flag)


def document_blob(rows=SAMPLES) -> bytes:
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = sec.bottom_margin = Inches(0.7)
    sec.left_margin = sec.right_margin = Inches(0.75)
    doc.add_heading("Student Assistant - Four-Language PDF QA", level=1)
    doc.add_paragraph("Check every line visually in the generated PDF and PNG.")
    for label, text, font, rtl in rows:
        doc.add_heading(f"{label} - {font}", level=2)
        add_sample(doc, label, text, font, rtl)
    data = BytesIO()
    doc.save(data)
    return data.getvalue()


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python QA_V130_MULTISCRIPT_PDF.py OUTPUT_DIRECTORY", file=sys.stderr)
        return 2
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    blob = document_blob()
    (out / "V13_Four_Languages.docx").write_bytes(blob)
    try:
        pdf_stream = convert_office_to_pdf(blob, "V13_Four_Languages.docx", "docx")
    except OfficePdfError as exc:
        print(f"ERROR: The real Office converter refused the document: {exc}", file=sys.stderr)
        return 1
    pdf = pdf_stream.getvalue()
    assert pdf.startswith(b"%PDF-"), "Office converter did not produce PDF"
    (out / "V13_Four_Languages.pdf").write_bytes(pdf)
    reader = PdfReader(BytesIO(pdf))
    assert len(reader.pages) >= 1, "No PDF pages"
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Student Assistant" in extracted, "English heading not extractable from converted PDF"

    doc = pdfium.PdfDocument(pdf)
    for i in range(len(doc)):
        page = doc[i]
        page.render(scale=1.8).to_pil().save(out / f"V13_Four_Languages_page_{i+1}.png")
        page.close()
    doc.close()

    # Negative safety check: only enforce refusal when the specific font is missing.
    sakkal_blob = document_blob((("Arabic", "اللغة العربية", "Sakkal Majalla", True),))
    missing = missing_exact_fonts(sakkal_blob, "docx", policy="priority")
    if "Sakkal Majalla" in missing:
        try:
            convert_office_to_pdf(sakkal_blob, "Sakkal_Test.docx", "docx")
        except OfficePdfError:
            sakkal_result = "PASS: missing Sakkal Majalla was blocked"
        else:
            raise AssertionError("Missing Sakkal Majalla was silently substituted")
    else:
        sakkal_result = "SKIPPED: Sakkal Majalla appears installed; inspect exact rendering separately"

    summary = (
        "PASS: Actual Student Assistant DOCX to PDF conversion succeeded\n"
        f"PDF pages: {len(reader.pages)}\n"
        "Generated English, Tamil, Arabic, and Sinhala text on DOCX/PDF.\n"
        "PDF source, generated PDF, and PNG previews saved for visual inspection.\n"
        "Extraction of English heading passed. Native-script shaping is NOT automatically validated.\n"
        + sakkal_result + "\n"
    )
    (out / "V13_QA_RESULT.txt").write_text(summary, encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
