import os
import requests


OCR_ENDPOINT = "https://api.ocr.space/parse/image"


def get_ocr_api_key():
    return os.getenv("OCR_SPACE_API_KEY")


def extract_text_with_ocr(file_bytes, filename="image.jpg"):
    api_key = get_ocr_api_key()

    if not api_key:
        raise RuntimeError(
            "OCR_SPACE_API_KEY is not configured."
        )

    response = requests.post(
        OCR_ENDPOINT,
        headers={
            "apikey": api_key,
        },
        files={
            "file": (
                filename,
                file_bytes,
            )
        },
        data={
            "language": "auto",
            "OCREngine": "3",
            "isOverlayRequired": "false",
            "scale": "true",
        },
        timeout=120,
    )

    response.raise_for_status()
    payload = response.json()

    if payload.get("IsErroredOnProcessing"):
        messages = payload.get("ErrorMessage") or []

        if isinstance(messages, list):
            message = " ".join(
                str(item)
                for item in messages
            )
        else:
            message = str(messages)

        raise RuntimeError(
            message
            or "OCR processing failed."
        )

    text_parts = []

    for result in payload.get(
        "ParsedResults",
        []
    ):
        text = (
            result.get("ParsedText")
            or ""
        ).strip()

        if text:
            text_parts.append(text)

    final_text = "\n\n".join(
        text_parts
    ).strip()

    if not final_text:
        raise RuntimeError(
            "No readable text was found."
        )

    return final_text
