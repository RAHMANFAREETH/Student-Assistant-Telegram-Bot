"""AssemblyAI speech transcription for Student Assistant Bot V5.4.

Compatible with voice_notes.py:
    stt_is_configured(), transcribe_audio(audio_bytes)

Uses requests already present in requirements.txt; no new dependency needed.
"""
import os
import time

import requests


ASSEMBLYAI_BASE = "https://api.assemblyai.com"
# Universal-2 supports Tamil, Sinhala, English, Arabic and many other languages.
# Explicitly select this lower-cost multilingual model instead of relying on
# changing API defaults.
SPEECH_MODELS = ["universal-2"]
MAX_AUDIO_BYTES = 20 * 1024 * 1024
POLL_INTERVAL_SECONDS = 2


def get_stt_api_key():
    return (os.getenv("ASSEMBLYAI_API_KEY") or "").strip()


def stt_is_configured():
    return bool(get_stt_api_key())


def _headers():
    key = get_stt_api_key()
    if not key:
        raise RuntimeError(
            "Speech-to-text is not configured. Add ASSEMBLYAI_API_KEY to Render Environment."
        )
    return {"authorization": key}


def _response_json(response):
    try:
        result = response.json()
    except (ValueError, TypeError):
        raise RuntimeError("Speech service returned an invalid response.") from None
    if not isinstance(result, dict):
        raise RuntimeError("Speech service returned an unexpected response.")
    return result


def _checked_json(response):
    """Return data or raise a safe error (never expose token or URLs)."""
    status = response.status_code
    if status in (401, 403):
        raise RuntimeError(
            "AssemblyAI authentication failed. Verify ASSEMBLYAI_API_KEY in Render."
        )
    if status == 402:
        raise RuntimeError(
            "AssemblyAI credits may be exhausted. Check your AssemblyAI billing balance."
        )
    if status == 429:
        raise RuntimeError(
            "AssemblyAI rate limit reached. Try again later."
        )
    if status >= 500:
        raise RuntimeError(
            "AssemblyAI is temporarily unavailable. Try again later."
        )
    if status >= 400:
        raise RuntimeError(
            f"AssemblyAI rejected the request (HTTP {status}). Check the audio format."
        )
    return _response_json(response)


def _post(path, *, audio=None, payload=None, timeout=30):
    try:
        if audio is not None:
            response = requests.post(
                f"{ASSEMBLYAI_BASE}{path}", headers=_headers(),
                data=audio, timeout=timeout,
            )
        else:
            response = requests.post(
                f"{ASSEMBLYAI_BASE}{path}", headers=_headers(),
                json=payload, timeout=timeout,
            )
    except requests.Timeout:
        raise RuntimeError("Speech service timed out. Try again later.") from None
    except requests.RequestException:
        raise RuntimeError("Could not reach the speech service. Try again later.") from None
    return _checked_json(response)


def upload_audio(audio_bytes):
    if not isinstance(audio_bytes, bytes) or not audio_bytes:
        raise ValueError("No audio data was received from Telegram.")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise ValueError("Voice note is too large (maximum 20 MB).")
    data = _post("/v2/upload", audio=audio_bytes, timeout=60)
    url = data.get("upload_url")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise RuntimeError("Speech service did not return a valid upload URL.")
    return url


def transcribe_audio(audio_bytes, poll_timeout_seconds=120):
    """Transcribe Telegram voice audio; return text, language_code, transcript_id.

    The current voice_notes.py invokes this synchronously. For large-scale
    deployments, move job polling outside Telegram's webhook request.
    """
    if poll_timeout_seconds <= 0:
        raise ValueError("poll_timeout_seconds must be positive.")

    audio_url = upload_audio(audio_bytes)
    response = _post(
        "/v2/transcript",
        payload={
            "audio_url": audio_url,
            "speech_models": SPEECH_MODELS,
            "language_detection": True,
        },
        timeout=30,
    )
    transcript_id = response.get("id")
    if not transcript_id:
        raise RuntimeError("Speech service did not create a transcript.")

    deadline = time.monotonic() + poll_timeout_seconds
    while time.monotonic() < deadline:
        try:
            poll = requests.get(
                f"{ASSEMBLYAI_BASE}/v2/transcript/{transcript_id}",
                headers=_headers(), timeout=20,
            )
        except requests.Timeout:
            raise RuntimeError("Speech service timed out. Try again later.") from None
        except requests.RequestException:
            raise RuntimeError("Could not reach the speech service. Try again later.") from None
        data = _checked_json(poll)
        status = data.get("status")
        if status == "completed":
            return {
                "text": (data.get("text") or "").strip(),
                "language_code": data.get("language_code") or data.get("language"),
                "transcript_id": transcript_id,
            }
        if status == "error":
            # Provider error text can include internal IDs, URLs, etc.
            # Keep user-facing message generic and safe.
            raise RuntimeError("AssemblyAI could not transcribe this audio. Try a clearer recording.")
        if status not in ("queued", "processing"):
            raise RuntimeError("Unexpected transcription status. Try again later.")
        time.sleep(min(POLL_INTERVAL_SECONDS, max(0, deadline - time.monotonic())))

    raise TimeoutError(
        "Transcription is still processing. Try again later with a shorter recording."
    )
