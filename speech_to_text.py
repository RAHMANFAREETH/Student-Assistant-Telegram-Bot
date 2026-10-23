import os
import time

import requests


ASSEMBLYAI_BASE = "https://api.assemblyai.com"


def get_stt_api_key():
    return (
        os.getenv("ASSEMBLYAI_API_KEY")
        or ""
    ).strip()


def stt_is_configured():
    return bool(
        get_stt_api_key()
    )


def _headers():
    api_key = get_stt_api_key()

    if not api_key:
        raise RuntimeError(
            "ASSEMBLYAI_API_KEY is not configured."
        )

    return {
        "authorization": api_key,
    }


def upload_audio(audio_bytes):
    response = requests.post(
        f"{ASSEMBLYAI_BASE}/v2/upload",
        headers=_headers(),
        data=audio_bytes,
        timeout=90,
    )

    response.raise_for_status()

    data = response.json()

    upload_url = data.get(
        "upload_url"
    )

    if not upload_url:
        raise RuntimeError(
            "Speech service did not return an upload URL."
        )

    return upload_url


def transcribe_audio(
    audio_bytes,
    poll_timeout_seconds=120,
):
    """
    Optional speech-to-text for a finished Telegram voice note.
    Language detection is enabled.
    """

    upload_url = upload_audio(
        audio_bytes
    )

    payload = {
        "audio_url": upload_url,
        "language_detection": True,
    }

    create_response = requests.post(
        f"{ASSEMBLYAI_BASE}/v2/transcript",
        headers=_headers(),
        json=payload,
        timeout=60,
    )

    create_response.raise_for_status()

    create_data = create_response.json()

    transcript_id = create_data.get(
        "id"
    )

    if not transcript_id:
        raise RuntimeError(
            "Speech service did not create a transcript."
        )

    deadline = (
        time.monotonic()
        + poll_timeout_seconds
    )

    while time.monotonic() < deadline:

        status_response = requests.get(
            (
                f"{ASSEMBLYAI_BASE}"
                f"/v2/transcript/{transcript_id}"
            ),
            headers=_headers(),
            timeout=30,
        )

        status_response.raise_for_status()

        result = status_response.json()

        status = result.get(
            "status"
        )

        if status == "completed":
            return {
                "text": (
                    result.get("text")
                    or ""
                ).strip(),
                "language_code": (
                    result.get(
                        "language_code"
                    )
                    or result.get(
                        "language"
                    )
                ),
                "transcript_id": transcript_id,
            }

        if status == "error":
            raise RuntimeError(
                (
                    result.get("error")
                    or "Speech transcription failed."
                )
            )

        time.sleep(2)

    raise TimeoutError(
        (
            "Speech transcription took too long. "
            "Please try again later."
        )
    )
