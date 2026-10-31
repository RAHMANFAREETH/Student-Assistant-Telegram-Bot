# V10.1 Combined — All 12 Learning Intelligence Features

**Status: offline-tested release candidate; not yet installed/deployed.** This is a single combined update for the EXISTING Student Assistant Telegram Bot. Do not create a second bot, Gemini key, Render service or Supabase project. Python 3.12 compatible; uses existing V10 `v10_*.py`, V9.3 adult-access code, Gemini (`gemini_ai_studio_v59.py`), AssemblyAI (`speech_to_text.py`), OCR.space (`translation_ocr.py`) and `gTTS` (`requirements.txt` already includes it). No new Python dependencies.

> IMPORTANT: The functionality is not yet verified with real Telegram, Google Gemini, AssemblyAI, OCR.space, Google Translate TTS or the live Supabase database. These tests exercise mocks and offline behaviors. Gemini is generative and can be wrong; it is not an official grader. All Gemini calls still consume the EXISTING V10 Gemini shared daily quota (default 4 per UTC day), even if the provider later fails or returns malformed quiz JSON.

## Features — all 12 in one package

| # | Feature | Commands | Implementation and limits |
|---|---|---|---|
| 1 | Multi-document tutor with short follow-up memory | `/v101chat QUESTION`, `/v101confirm`, `/v101forget` | Gemini uses up to four relevant V10 excerpts and the last three prior Q/A turns. Chat turns are stored in owner-scoped Supabase, hidden from history after 14 days and removable on demand; periodic physical purge is **not** implemented. |
| 2 | Voice viva | `/v101viva TOPIC`, confirm, `/v101voice`, voice note, `/v101voicefeedback`, confirm | One Gemini question; speech sent to existing AssemblyAI only when user sends voice in a consented state. Short transcription preview; separate consent before Gemini feedback. 60sec / 2MB. No pronunciation assessment. Speech processing is best-effort on the existing Render worker; may be interrupted by restart/sleep. Typed `/v101answer ANSWER` is available. |
| 3 | Multilingual tutor | `/v101explain Tamil \| TOPIC` | Gemini explanation in Tamil, Sinhala, Arabic or English. Existing V10 adult gate, Gemini consent and quota. |
| 4 | Scanned PDF/photo OCR | `/v101ocr` → send PDF/JPG/PNG → `/v101ocrconfirm` → `/v101ocrsave` | Uses existing OCR.space adapter after document-specific consent; a second command saves extracted text to V10 private library. Provider limits may reject scans; OCR results have merged/approximate page references. OCR processing is best-effort on Render, not a durable job. |
| 5 | Adaptive practice exam | `/v101mock TOPIC`, confirm, `/v101submit A B C` | Gemini generates 3 MCQs from saved notes; code validates schema, grades chosen letters, stores incorrect answers in `v101_mock_mistakes`. AI questions/answer keys may contain errors. Mock quizzes are practice only; not an official timed exam. |
| 6 | Rubric-guided answer feedback | `/v101rubric QUESTION \| ANSWER \| CRITERIA`, confirm | Gemini formative suggestions with explicit marking criteria. Not official assessment. |
| 7 | 7/14/30-day roadmap | `/v101plan 7 \| Biology \| 60`, `/v101myplan` | Rule-based schedule using existing V10 coach priorities; saved privately in Supabase. Does not silently modify timetable/reminders. |
| 8 | Audio study summary | `/v101audio TOPIC` (or `/v101audio ta \| TOPIC`) → `/v101audioconfirm` | Text excerpt summary from saved notes, converted to MP3 by existing gTTS after explicit consent; text is sent to TTS provider. If TTS language not supported or text doesn't match selected language, choose another language. Audio isn't stored by this addon. |
| 9 | PDF notes → flashcards | `/v101cards TOPIC`, confirm, `/v101cardsave` | Gemini builds 1–5 checked-format cards from source excerpts; preview and separate save. Inserted into existing `flashcards`, available in `/v10due`. Verify correctness before saving. |
| 10 | Compare learning sources | `/v101compare TOPIC` (offline) or `/v101compareai TOPIC` → confirm | Distinct top source excerpts per document and term overlap, or cautious Gemini comparison. Neither proves contradictions. Requires 2 relevant saved documents. |
| 11 | Opt-in study rooms | `/v101roomcreate GOAL`, `/v101roomjoin CODE`, `/v101room`, `/v101roomquiz QUESTION \| ANSWER`, `/v101roomanswer ANSWER`, `/v101roomscore`, `/v101roomleave` | Private one-room-per-user membership, cryptographically random invite, 12-member maximum, owner-created shared exact-match quiz, aggregated anonymous scores. Asynchronous collaboration, **not** a real-time synchronized game. No private documents or personal AI chats shared. |
| 12 | Source support screening | `/v101check CLAIM` | Offline lexical overlap against top matching excerpts. **Not** factual verification or logical entailment. Always show original source and check facts independently. |

All features require a private chat and **independently verified-adult access**. Even offline tools require `STUDY_ACCESS_MODE=verified_adults` and a valid record in `study_verified_adults`. Pilot-only IDs and self-declarations do not grant V10.1 access.

## Package files (8)

- `v101_bot.py`: V10.1 Telegram commands, one-shot consent, ephemeral state and voice/OCR/TTS routing.
- `v101_engine.py`: offline parsing, mock quizzes, roadmaps, source comparison and support screening.
- `v101_store.py`: user-scoped Supabase chat, plans, mistakes, flashcards, rooms and quiz data.
- `v101_gemini.py`: existing V10 Gemini client, adult gate and **shared** V10 Gemini quota (no independent allowance).
- `INSTALL_V101_COMBINED.py`: safe `--check` / `--apply` installer.
- `SQL_V101_ALL_FEATURES.sql`: seven additive tables with RLS plus an atomic room-join RPC.
- `TEST_V101_COMBINED.py`: offline tests.
- `README_V101_ALL_FEATURES.md`: this guide.

## Windows installation — DO NOT enable yet

1. Make a local backup. Extract the ZIP; copy all **8 new files** into `C:\Users\Pros\Desktop\StudentAssistantBot`. **Do not overwrite** any existing `v10_bot.py`, `main.py`, `navigation.py`, `ui_v57.py` or provider files from earlier versions.
2. Run:

```powershell
python INSTALL_V101_COMBINED.py --check
python -m py_compile v101_bot.py v101_engine.py v101_store.py v101_gemini.py INSTALL_V101_COMBINED.py
python -m unittest TEST_V101_COMBINED -q
python -m unittest TEST_V10_ADVANCED_STUDY TEST_V10_GEMINI -q
```

3. Check the proposed diff changes **only** `main.py`, `ui_v57.py` and `navigation.py`. Handler registration is inserted **before** V10 and older state handlers so OCR/voice uploads are routed correctly. If the dry-run finds unexpected code patterns, do not force the installer. When reviewed:

```powershell
python INSTALL_V101_COMBINED.py --apply
python INSTALL_V101_COMBINED.py --check
python -m py_compile main.py ui_v57.py navigation.py v101_bot.py v101_engine.py v101_store.py v101_gemini.py
python -m unittest TEST_V101_COMBINED -q
```

4. Run your previously passing V10, V9.3/V9.2/V9.1, V8 and V9 tests as separate commands. For the older V8/V9 test suites with hard-coded pilot IDs only, temporarily set `$env:STUDY_ACCESS_MODE='pilot'` in **local test PowerShell** and restore it in `finally`, just as in earlier testing. Never switch Render to pilot to satisfy old test fixtures.

5. **Before deploying**, back up and review `SQL_V101_ALL_FEATURES.sql`, then run in the existing Supabase SQL Editor. It creates seven new `v101_*` tables and `v101_join_study_room(bigint,text)`; it never drops/updates older tables. Check RLS:

```sql
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname='public' AND tablename LIKE 'v101_%' ORDER BY tablename;
SELECT proname FROM pg_proc
WHERE pronamespace='public'::regnamespace AND proname='v101_join_study_room';
```

All seven tables should show `rowsecurity=true`. Keep your Supabase service-role key on the server only; do not grant anonymous access. Test with two verified adult accounts to confirm isolation and room membership rules.

6. **Selective Git staging:**

```powershell
git diff --cached --name-only
git add -- v101_bot.py v101_engine.py v101_store.py v101_gemini.py INSTALL_V101_COMBINED.py TEST_V101_COMBINED.py SQL_V101_ALL_FEATURES.sql README_V101_ALL_FEATURES.md
git add -p -- main.py ui_v57.py navigation.py
git diff --cached --check
git diff --cached --name-only
```

Review **11 intended files** (8 new + 3 existing integration edits); don't use `git add .`, don't commit backups or API keys. Then only after tests and SQL review:

```powershell
git commit -m "V10.1: Add twelve combined Gemini study enhancements"
git push origin main
```

7. Render environment: **start disabled** until code is Live and SQL migration succeeds.

```dotenv
V101_ENABLED=false
V10_ENABLED=true
V10_GEMINI_ENABLED=true
V10_GEMINI_DAILY_LIMIT=4
STUDY_ACCESS_MODE=verified_adults
```

Keep your existing `GEMINI_API_KEY`, `ASSEMBLYAI_API_KEY`, `OCR_SPACE_API_KEY`, existing V8/V9/V9.1/V9.2/V9.3 settings unchanged. `V101_ENABLED=true` activates all 12 workflows together after deployment. Individual provider availability and quota still affect corresponding features. Avoid changing the Gemini model or old quotas casually.

8. After Render is Live, set `V101_ENABLED=true`, deploy the environment change, then in Telegram send `/v101`. Verify each of the 12 features sequentially, especially consent, adult verification, stored-record deletion, voice/OCR cancellation, study-room privacy and existing `/v8`, `/v9`, `/v10`, `/adult_admin`, and `/access_health`.

## Privacy and operational limits

- AI prompts, quiz text, source excerpts and answers sent to Gemini require one-time `/v101confirm`. No automatic AI calls on upload; up to four short page snippets are used. Gemini Free-tier data-use terms may allow use of prompt content for product improvement; avoid sensitive/private records. The API key is never shown to Telegram.
- `/v101chat` opts into storing short Q/A turns. `/v101forget` deletes **all** V10.1 chat history for that account. Messages expire **from active lookup** at 14 days; expiry is not a database purge. Deleting a V10 document via `/v10delete` does not automatically erase Q/A text that referenced it. Use `/v101forget` as well when deleting source records.
- AssemblyAI receives voice audio only after the user actively requests voice reply and sends a recording, and Gemini receives the transcript only after `/v101voicefeedback` and `/v101confirm`. OCR.space receives a document only after `/v101ocrconfirm`. Google TTS receives excerpt text only after `/v101audioconfirm`.
- In-memory states are temporary (10-minute TTL and max 40 users per instance) and **not durable across Render restarts**; these one-shot workflows may need restarting after a worker restart. Scanned OCR and speech use capped best-effort background threads, not a job queue. Consider durable task storage for production scaling.
- Existing V10 `v10_documents` caps (six files, 5MB file, 45k text/40 chunks) still apply. OCR image files are stored as `.txt` extracts. OCR page information may be merged; do not claim exact page citations.
- Room invitation codes are bearer invites; do not post them publicly. Room chats, personal AI answers and documents are NOT shared. Room exact-match questions are not AI-evaluated, and aggregated counts are not a meaningful educational ranking. The service-role database function enforces room capacity atomically.
- **Security:** all tools require private chat and verified-adult access, not pilot access. User data is scoped to Telegram UID in DB queries. Bot must use server-side Supabase `service_role`. Never send screenshots of credentials or service-role keys.
- No new billed APIs introduced, but existing Gemini, AssemblyAI, OCR.space and gTTS use provider resources and may have restrictions/costs; usage is not guaranteed to remain free. The default shared Gemini quota of 4/day may prevent testing every AI command in one day. Do not bypass verified age to run tests.
- This is a candidate built/tested offline, not a claim that live provider integrations are already successful. Start a limited verified-adult pilot and inspect Render errors before a broad rollout.
