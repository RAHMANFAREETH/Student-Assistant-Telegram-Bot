# Student Assistant Bot V5.4 — AssemblyAI Voice Transcription Update

This is a **small replacement module**, not a complete standalone bot.

## Already present in your V5.4 project

The original V5.4 project already has:

- `voice_notes.py` with `/voice`, **➕ Add Voice Note**, **📝 Transcribe Voice**, and **📄 View Transcript**.
- `speech_to_text.py` with an AssemblyAI `/v2/upload` and `/v2/transcript` integration.
- `requests` installed through `requirements.txt`.
- Supabase `voice_notes` columns for saving the transcript and detected language.

This patch improves the existing `speech_to_text.py`. It explicitly uses multilingual `universal-2`, handles 401/402/429/5xx errors, bounds input size, and retains the original functions expected by `voice_notes.py`.

## 1. Back up and copy

Back up your existing `speech_to_text.py` before replacing it. Copy **only** these files into your `StudentAssistantBot` project:

- `speech_to_text.py` (replace)
- `TEST_ASSEMBLYAI_V54.py` (add)

Do not replace `main.py`, `voice_notes.py`, `translate.py`, `db.py`, `config.py`, `.env`, or SQL files.

## 2. Add key in Render

In your existing Render service > Environment, set:

- Key: `ASSEMBLYAI_API_KEY`
- Value: your **full secret API key** copied from AssemblyAI dashboard

Save the settings securely. Your local `.env` can have the same key if you do local tests; never upload `.env` to GitHub.

## 3. Test code locally (does not use paid API)

From the project root in VS Code PowerShell:

```powershell
python -m py_compile speech_to_text.py voice_notes.py
python -m unittest TEST_ASSEMBLYAI_V54.py -v
```

Expected: 12 offline tests, OK.

## 4. Commit only changed code

```powershell
git status
git add speech_to_text.py TEST_ASSEMBLYAI_V54.py
git diff --cached --check
git commit -m "Improve AssemblyAI multilingual voice transcription"
git push origin main
```

Do not use `git add .` unless you have reviewed all untracked files and know no secrets are present.

## 5. Render and Telegram live test

Wait for Render > Deploys > **Live** on the commit containing the updated module.

1. Open Telegram and send `/voice` (or tap **🎙 Voice Notes**).
2. Tap **➕ Add Voice Note**, choose a subject or **⏭ No Subject**, then enter a title.
3. Record a clear **15–30 second** Telegram voice message. Auto-detection is less reliable with very short speech.
4. Tap **📝 Transcribe Voice**. Enter the **numeric note ID** shown after saving.
5. After it finishes, open **📄 View Transcript** and enter the same ID to verify the saved text.
6. Try English first, then a clear Tamil or Sinhala recording, or Arabic.

If the bot displays a failure, share the text from **Render > Logs** with any API credentials redacted.

## Constraints

- **Trial, not permanently free**: AssemblyAI Free accounts include up to **$50 of trial credits**. The quota can run out.
- **Third-party processing**: Uploaded Telegram voice messages are forwarded to AssemblyAI for transcription. Tell students, avoid sensitive recordings without informed consent, and provide data retention/privacy terms.
- **Webhook timeout risk**: Existing `voice_notes.py` waits for transcription inside the Telegram webhook request. Slow or long recordings can exceed Render/Gunicorn request timeouts or be reprocessed after retries. For production at scale, replace this with a persistent Supabase job queue + separate worker or authenticated AssemblyAI callback. This patch intentionally does not change that architecture or make background-completion claims.
- **Not a ChatGPT replacement**: This module is **speech-to-text**, not the conversational **Ask AI** feature; that requires a separately selected LLM provider and its policy compliance.
- No new SQL, pip package, or paid AI subscription needed to install this patch. Live transcription uses your AssemblyAI trial credits.
