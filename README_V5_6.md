# Student Assistant Bot V5.6 — Ask My Notes & Ask My PDF

**For the EXISTING V5.5 Cloudflare-powered StudentAssistantBot.** This is a safe add-on, **not a replacement project**.

## New commands and keyboard buttons

- `📝 Ask My Notes` or `/asknotes`: choose one of your existing saved Notes, consent, and ask questions.
- `📄 Ask My PDF` or `/askpdf`: choose an existing PDF saved under **Study Materials**, consent, and ask questions about its extracted text.
- `/aicontextcancel`: stop the selected-source conversation.

Only the selected student's own records are queried using their Telegram `user_id`. Private-chat only. The source text is sent to **Cloudflare Workers AI** only after **I AGREE** consent. Existing cloud AI daily quotas and Llama Guard safety checks are reused; no separate Supabase table or new API key is needed. No new AI chat transcripts are stored in Supabase.

## Installation: follow these steps exactly

1. **Back up** your current working `StudentAssistantBot` folder; keep the current `main.py`, `navigation.py`, and `ai_study_assistant.py` safe.
2. Extract this ZIP. Copy **three files** to your existing project: `study_context_ai.py`, `INSTALL_V5_6.py`, `TEST_V5_6_CONTEXT.py` (and optionally this README). **Do not replace** your working V5.5 `ai_study_assistant.py` or other modules.
3. In VS Code Terminal, in the `StudentAssistantBot` folder, run:

```powershell
python INSTALL_V5_6.py
python -m py_compile main.py navigation.py ai_study_assistant.py study_context_ai.py
python -m unittest TEST_V5_6_CONTEXT.py -v
```

The installer makes `main.py.before_v56.bak` and `navigation.py.before_v56.bak` on the first run, and only inserts minimal imports, registrations, and 2 main-menu buttons. It does **not** rewrite Azure Translation, OCR, AssemblyAI, Flask webhook, or your existing Cloudflare AI code. Running the installer again is safe and produces no further changes.

4. Review changed files, make sure no secrets are staged, then commit:

```powershell
git diff -- main.py navigation.py
git add main.py navigation.py study_context_ai.py INSTALL_V5_6.py TEST_V5_6_CONTEXT.py
git diff --cached --stat
git commit -m "Add V5.6 Ask My Notes and PDF"
git push origin main
```

5. On Render confirm the new deployment is **Live**. Test Telegram in a private chat:

    - Save a short note via `📝 Notes` and a PDF via `📚 Study Materials` (including OCR extraction if scanned).
    - Send `/asknotes` or press `📝 Ask My Notes`.
    - Select the displayed ID; reply `I AGREE`; ask a question about that note.
    - Use `/aicontextcancel`, then `/askpdf`; select one of your already-saved PDFs and ask a question.
    - Verify `/ai`, `/start`, Azure translation, Voice Notes, and original Flashcards still work.

## Limitations and safety

- **Not direct file upload:** `Ask My PDF` uses PDFs **already saved** in Study Materials. If a PDF is scanned, it needs OCR-extracted text in the existing Study Materials workflow.
- **Partial-document retrieval:** for longer sources, a small subset of short text excerpts is selected with a simple word-overlap method; answers may miss information elsewhere in the document. Answers are marked as excerpt-based, not complete-document analysis.
- **Source text is shared with Cloudflare:** ask students not to use sensitive personal, medical, school-record or confidential material. Consent is required before the first question for each source. Refer to your provider's terms and local privacy rules before using this with minors.
- AI may make mistakes; always verify facts with the original note/PDF.
- Cloudflare daily free quota is shared across the whole bot; `AI_DAILY_LIMIT` still applies to each student.
- Uses V5.5's process-local worker pool, not a durable job queue. Render restarts can cancel pending AI responses.
- The **Google Gemini API is not wired to the mixed-age public bot**: Google prohibits services likely to be accessed by under-18s from using its Gemini API. No new `GEMINI_API_KEY` setting is needed.

## Test status

The new module passed 10 offline unit tests, including user isolation, consent, PDF filtering, shared AI quota/moderation, bounded retrieval, and idempotent installation. The installer was also verified twice against V5.4 + V5.5 Python source: static compilation passed and second run made no changes. **Live Supabase/Telegram/Cloudflare integration is not yet verified.**
