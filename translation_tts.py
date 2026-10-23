from io import BytesIO
from gtts import gTTS


MAX_TTS_CHARACTERS = 2500


def build_pronunciation_audio(text, language):
    clean_text = (text or "").strip()

    if not clean_text:
        raise ValueError("No text available for pronunciation.")

    truncated = False

    if len(clean_text) > MAX_TTS_CHARACTERS:
        clean_text = clean_text[:MAX_TTS_CHARACTERS]
        truncated = True

    audio = BytesIO()
    audio.name = "pronunciation.mp3"

    tts = gTTS(
        text=clean_text,
        lang=language,
        slow=False,
    )

    tts.write_to_fp(audio)
    audio.seek(0)

    return audio, truncated
