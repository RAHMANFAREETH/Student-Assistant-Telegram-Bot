"""OCR.space adapter for Telegram images and scanned PDFs.

A scanned PDF is split into <=3-page and <1MB requests for OCR.space's
free API. This code never embeds OCR credentials in source files.
"""
import os
from io import BytesIO
from pathlib import Path

import requests

try:
    from PyPDF2 import PdfReader, PdfWriter
except ImportError:  # Newer distributions may use the pypdf package name.
    from pypdf import PdfReader, PdfWriter


OCR_ENDPOINT = "https://api.ocr.space/parse/image"
OCR_MAX_UPLOAD_BYTES = 1_000_000
OCR_MAX_PAGES_PER_CALL = 3
# Avoid unexpectedly making scores of external OCR requests in one bot update.
OCR_MAX_DOCUMENT_PAGES = 30


def get_ocr_api_key():
    return os.getenv("OCR_SPACE_API_KEY", "").strip()


def _detail(payload):
    """Return short, non-sensitive OCR API diagnostics."""
    if not isinstance(payload, dict):
        return ""
    parts = []
    for key in ("ErrorMessage", "ErrorDetails", "error", "details"):
        value = payload.get(key)
        if isinstance(value, list):
            value = "; ".join(map(str, value))
        if value:
            parts.append(str(value).strip())
    # Don't echo the uploaded file, headers, or API key to chat/logs.
    return "; ".join(parts)[:240]


def _recognize(file_bytes, *, is_pdf, api_key, filename="image.jpg"):
    # ASCII multipart names prevent servers rejecting non-ASCII source names.
    if is_pdf:
        upload_name, mime = "scanned_document.pdf", "application/pdf"
    elif file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        upload_name, mime = "scanned_image.png", "image/png"
    elif file_bytes.startswith((b"II*\x00", b"MM\x00*")):
        upload_name, mime = "scanned_image.tif", "image/tiff"
    elif file_bytes.startswith(b"BM"):
        upload_name, mime = "scanned_image.bmp", "image/bmp"
    elif Path(filename).suffix.lower() == ".png":
        upload_name, mime = "scanned_image.png", "image/png"
    else:
        upload_name, mime = "scanned_image.jpg", "image/jpeg"
    params = {
        "language": "auto",
        "OCREngine": "3",
        "isOverlayRequired": "false",
        "scale": "true",
    }
    if is_pdf:
        params["filetype"] = "PDF"
    try:
        response = requests.post(
            OCR_ENDPOINT,
            headers={"apikey": api_key},
            files={"file": (upload_name, file_bytes, mime)},
            data=params,
            timeout=(15, 120),
        )
    except requests.RequestException as error:
        raise RuntimeError(
            "OCR.space could not be reached. Try again later. "
            f"({type(error).__name__})"
        ) from error

    try:
        payload = response.json()
    except (ValueError, TypeError):
        payload = {}

    detail = _detail(payload)
    if response.status_code == 429:
        raise RuntimeError("OCR.space rate limit reached (HTTP 429). Try later.")
    if response.status_code == 400:
        msg = detail or "The OCR service rejected the uploaded file"
        raise RuntimeError(
            f"OCR.space HTTP 400: {msg}. "
            "The free API allows at most 1 MB and 3 PDF pages per request."
        )
    if response.status_code in (401, 403):
        raise RuntimeError(
            "OCR.space rejected OCR_SPACE_API_KEY. Check the key in Render."
        )
    if response.status_code >= 400:
        raise RuntimeError(
            f"OCR.space HTTP {response.status_code}: {detail or 'Request failed'}"
        )

    if not isinstance(payload, dict):
        raise RuntimeError("OCR.space returned an unexpected response.")
    if payload.get("IsErroredOnProcessing") or payload.get("OCRExitCode") in (2, 3, 4, 99, "2", "3", "4", "99"):
        raise RuntimeError(
            "OCR.space could not fully process this file: "
            + (detail or "unknown OCR error")
        )

    parts = [
        str(part.get("ParsedText") or "").strip()
        for part in (payload.get("ParsedResults") or [])
        if isinstance(part, dict)
    ]
    result = "\n\n".join(part for part in parts if part).strip()
    if not result:
        raise RuntimeError(
            "No readable text was found by OCR. "
            "For scanned documents, try a clearer scan or fewer pages."
        )
    return result


def _pdf_section(reader, start, end):
    writer = PdfWriter()
    for page_index in range(start, end):
        writer.add_page(reader.pages[page_index])
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _ocr_pdf_range(reader, start, end, api_key):
    """Keep a chunk at <=3 pages and <1MB (recursively split if needed)."""
    if end - start > OCR_MAX_PAGES_PER_CALL:
        return "\n\n".join(
            _ocr_pdf_range(reader, i, min(end, i + OCR_MAX_PAGES_PER_CALL), api_key)
            for i in range(start, end, OCR_MAX_PAGES_PER_CALL)
        )

    section = _pdf_section(reader, start, end)
    if len(section) > OCR_MAX_UPLOAD_BYTES:
        if end - start == 1:
            raise RuntimeError(
                f"Scanned PDF page {start + 1} exceeds the 1 MB OCR.space free limit "
                "even after splitting. Compress the PDF or upload a clearer, "
                "smaller image."
            )
        midpoint = (start + end) // 2
        return "\n\n".join((
            _ocr_pdf_range(reader, start, midpoint, api_key),
            _ocr_pdf_range(reader, midpoint, end, api_key),
        ))
    try:
        return _recognize(section, is_pdf=True, api_key=api_key)
    except RuntimeError as error:
        raise RuntimeError(f"OCR failed on PDF pages {start + 1}–{end}: {error}") from error


def extract_text_with_ocr(file_bytes, filename="image.jpg"):
    """Extract text from an image or all pages of a scanned PDF.

    Called by existing translate.py. No code changes are needed there.
    """
    api_key = get_ocr_api_key()
    if not api_key:
        raise RuntimeError("OCR_SPACE_API_KEY is not configured in Render.")
    if not isinstance(file_bytes, (bytes, bytearray)) or not file_bytes:
        raise ValueError("The uploaded file is empty.")

    is_pdf = (Path(filename).suffix.lower() == ".pdf" or bytes(file_bytes[:5]) == b"%PDF-")
    if not is_pdf:
        if len(file_bytes) > OCR_MAX_UPLOAD_BYTES:
            raise ValueError(
                "Image is larger than the 1 MB OCR.space free limit. "
                "Please compress it and try again."
            )
        return _recognize(bytes(file_bytes), is_pdf=False, api_key=api_key, filename=filename)

    try:
        reader = PdfReader(BytesIO(file_bytes), strict=False)
        if reader.is_encrypted:
            raise ValueError("Password-protected PDFs cannot be OCR processed.")
        pages = len(reader.pages)
    except ValueError:
        raise
    except Exception as error:
        raise ValueError(
            "The PDF cannot be opened. It may be damaged or unsupported."
        ) from error

    if pages == 0:
        raise ValueError("The PDF has no pages.")
    if pages > OCR_MAX_DOCUMENT_PAGES:
        raise ValueError(
            f"This PDF has {pages} scanned pages. Please split it into "
            f"files of no more than {OCR_MAX_DOCUMENT_PAGES} pages."
        )
    return _ocr_pdf_range(reader, 0, pages, api_key)
