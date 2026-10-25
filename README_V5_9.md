# Student Assistant Telegram Bot V5.9 — Google AI Studio Developer Integration

**For your existing StudentAssistantBot project** (V5.8). This is **not** a new Telegram bot or Render deployment. This upgrade adds an actual Gemini API client and a local developer console to the *same Python project*, while leaving the public Telegram bot unchanged.

## What is working in this package

- Google AI Studio Gemini `gemini-3.1-flash-lite` REST API connector (`gemini_ai_studio_v59.py`).
- Local interactive developer tester (`GEMINI_V5_9_DEV_TEST.py`), supporting Ask, Explain, Maths, Quiz, Language and output in English/Tamil/Sinhala/Arabic.
- Hidden API key entry using Python `getpass`; or existing `GEMINI_API_KEY` / `GOOGLE_API_KEY` environment variables.
- Offline tests (`TEST_V5_9_GEMINI.py`) with **no real requests and no API key**.
- Local-only file check (`VERIFY_V5_9.py`) that never edits `main.py`.
- No new Supabase tables, Render environment settings or package dependencies.

## Important compliance restriction

Google Gemini API Additional Terms (effective March 23, 2026) prohibit API Clients likely accessed by people under 18. Your public Student Assistant Bot serves mixed ages, potentially O/L/A/L students, so **do not register this module with Telegram or route public messages to it**. The local test console is solely for the adult developer to verify their own AI Studio key and API integration. A Telegram allowlist or a self-declared age button by itself cannot settle the restriction.

Official terms: https://ai.google.dev/gemini-api/terms
Official model: https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite
Official REST API: https://ai.google.dev/api/generate-content

## Installation — Windows VS Code PowerShell

1. Your current V5.8 folder is `C:\Users\Pros\Desktop\StudentAssistantBot`. Make sure existing V5.8 tests are passing (the recent encoding fix uses `.read_text(encoding="utf-8")`). Back up your project or commit it.
2. Extract ZIP, and copy all 5 files from it into your existing folder. **Do not overwrite any existing bot module**: V5.9 uses new filenames only.
3. In VS Code Terminal:

   ```powershell
   python VERIFY_V5_9.py
   python -m py_compile gemini_ai_studio_v59.py GEMINI_V5_9_DEV_TEST.py VERIFY_V5_9.py
   python -m unittest TEST_V5_9_GEMINI.py -v
   python GEMINI_V5_9_DEV_TEST.py --dry-run
   ```

4. For the **first real Google AI Studio test**, run:

   ```powershell
   python GEMINI_V5_9_DEV_TEST.py --smoke
   ```

   When the console says `Paste your Google AI Studio API key (hidden):`, paste the key you already generated. Input will not be echoed. **Do not share your key in screenshots, chats, `.env` commits or GitHub.** The tool sends one harmless photosynthesis prompt; it does not send Telegram chat messages or student records. Requires network and model quota.

5. Example private multilingual test, run locally:

   ```powershell
   python GEMINI_V5_9_DEV_TEST.py --task explain --language tamil
   ```

   Type your **own non-personal** question when prompted, and enter the key when prompted. You can also use `--task maths`, `--task quiz`, or `--language sinhala` / `arabic` / `english`.

6. If all tests pass, commit only these new files. They do not need Render redeployment because your Telegram bot does not import them:

   ```powershell
   git add gemini_ai_studio_v59.py GEMINI_V5_9_DEV_TEST.py VERIFY_V5_9.py TEST_V5_9_GEMINI.py README_V5_9.md
   git commit -m "Add V5.9 private Gemini AI Studio developer client"
   git push origin main
   ```

## Common errors

- **401/403**: check API key and Google AI Studio account access.
- **404**: model not enabled for key/region, or unavailable.
- **429**: rate limits or free-tier usage quota reached; check AI Studio dashboard.
- **Connection failed**: network/TLS issue or Google service unavailable.
- The console **never prints raw API responses on failures**; this protects key and private error information.
- On PowerShell, Python snippets belong in `.py` files, not typed directly at `PS ...>`.

## What is not included

- No `/gemini` command and no mixed-age public Telegram routing.
- No automatic Gemini fallback from Cloudflare.
- No new Telegram token or second bot.
- No access to saved notes, PDF text, Supabase data, or user messages.
- No actual API request was made when building these files. You test with your own key locally.

## Future integration

If a genuinely adult-only application/service becomes suitable under Google's current terms and available-region/privacy requirements, reuse this tested client behind explicit server-side access controls and a separately reviewed deployment. Do not copy student content into AI Studio without consent and a privacy review. Until then, keep Cloudflare AI in the existing public bot.
