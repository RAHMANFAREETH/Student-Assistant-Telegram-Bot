STUDENT ASSISTANT BOT V4.5 MULTILINGUAL
======================================

THIS REPLACES THE OLD ARABIC-ONLY V4.5 PACKAGE.

🌍 LANGUAGE TOOLS
-----------------
Currently supported:
- Tamil
- English
- Sinhala
- Arabic

Features:
- Save vocabulary
- Organize vocabulary by subject
- Meaning can be written in any language
- Optional example sentence
- List vocabulary from all languages
- Practice by selected language
- "I knew it" / "Practice again"
- Automatic mastery tracking
- Text-to-speech pronunciation
- Text statistics

Arabic receives one additional text tool:
- Remove ḥarakāt

Mastery rule:
- at least 3 correct reviews
- correct reviews >= 2 × wrong reviews


🎙 VOICE NOTES
--------------
Works for any language or subject.

Features:
- Save Telegram voice messages
- Organize by subject
- Replay voice messages
- Delete voice notes
- Optional speech-to-text
- Store and view transcripts

Telegram keeps the audio itself.
Supabase stores the Telegram file ID and metadata.


📝 OPTIONAL SPEECH-TO-TEXT
--------------------------
Not required for V4.5.

If you configure ASSEMBLYAI_API_KEY:
- the bot can transcribe saved voice notes
- detected language is saved with the transcript

Without it:
- Voice Notes still work
- Playback still works
- All Language Tools still work


SECURITY
--------
Never commit:
ASSEMBLYAI_API_KEY

Keep secrets only in:
- local .env
- Render Environment
