# Student Assistant V8.0 — Ten-feature Study Lab (release candidate)

**Status:** integrated offline candidate, **NOT DEPLOYED**. It is not a completed production release. This was built against the user-supplied V7.17 ZIP received 2026-10-29. All old production code is left intact until you run the installer. No new bot or Render service.

## Features included

| Feature | Candidate implementation | Limits / remaining work |
|---|---|---|
| 1. Document chat | Upload PDF/DOCX/TXT, question → ranked source passages with `[Page N]` for PDFs; `AI:` opt-in Cloudflare answer after explicit consent | Only searchable text; full conversational memory and advanced citations not implemented. AI is off until explicitly enabled. |
| 2. Past-paper analyzer | Extract numbered questions, frequent terms, optionally request Cloudflare summary after consent | Heuristics are not exam predictions, scanned PDFs require OCR, sophisticated topic clustering is pending |
| 3. Auto flashcards and quiz | Extract `Term: definition` pairs, preview; `SAVE` to existing flashcards/Supabase, `QUIZ` to build MCQs | Text definition extraction only, no general-purpose question generation; saving may be partial on DB errors |
| 4. Smart exam planner | Read existing Supabase exams and prepare a 7-day weighted draft schedule | Defaults to 60 min/day; not yet adaptive to per-day progress |
| 5. Lecture → notes | Summarize saved voice-note transcripts | Use existing Voice Notes / AssemblyAI transcription first; extraction is heuristic |
| 6. Progress dashboard | Show user-filtered counts from existing tables | Existing Dashboard still handles charts, GPA, trends |
| 7. Citation generator | Draft APA / Harvard / MLA from manually provided metadata | No automatic DOI/ISBN lookup; user must verify citation details |
| 8. Group quiz battles | Group admin privately creates question/answers, bot posts publicly; participants privately DM answers; persisted in Supabase; anonymous leaderboard | Requires SQL migration and membership/admin privileges; one question per battle, 15-minute expiry |
| 9. Telegram Mini App | HTTPS read-only dashboard with server-side Telegram initData HMAC verification, expiry and pilot allowlist | Not a complete graphical editor yet; no browser Supabase credentials |
| 10. Data backup | Existing academic JSON.GZ export exposed from the V8 hub | No restore/import yet; backup contains private student data |

These are ten **integrated starting workflows** in one package, not ten fully matured products. Existing V7.17 PDF and Office tools remain in place.

## Package contents

* `v8_engine.py` — pure extraction/analytics/citation algorithms
* `v8_bot.py` — Telegram handlers and existing Supabase module reuse
* `v8_miniapp.py` — static mobile dashboard + server-authenticated read-only API
* `SQL_V8_STUDY_LAB.sql` — persistent group quiz tables, no anonymous database grants
* `INSTALL_V8_STUDY_LAB.py` — idempotent integration in `main.py`, `navigation.py`, `ui_v57.py`; backups original files
* `TEST_V8_STUDY_LAB.py` — offline unit and simulated-bot tests

**No files from the uploaded `.git` folder, local backups, `.env`, or secrets are included.**

## Stage 1 — Install and test locally

1. Make a backup of your current `StudentAssistantBot` project; do not delete existing files.
2. Copy the six package files above plus this README into your current project root (beside `main.py`).
3. Open PowerShell in that project folder:

```powershell
python INSTALL_V8_STUDY_LAB.py --check
```

Review the proposed changes. They should only integrate the V8 imports/registration and the V8 category button; they do **not** replace V7.17 PDF modules, Docker or requirements.

```powershell
python INSTALL_V8_STUDY_LAB.py --apply
python -m py_compile v8_engine.py v8_bot.py v8_miniapp.py main.py ui_v57.py navigation.py
python -m unittest TEST_V8_STUDY_LAB -v
```

Then run existing regression tests in your current Python environment:

```powershell
python -m unittest TEST_V7_17_ADVANCED_PDF TEST_V7_13_OFFICE_PDF TEST_V7_15_PHOTO_CROP TEST_V7_16_DOCUMENT_SCANNER -q
python -m unittest TEST_V7_14_ENGINE_COMPAT TEST_V7_14_AUTO_CROP TEST_V7_13_IMAGE_FILTERS -q
```

Some old tests may be skipped or need external dependencies. **Stop on failures**, and don't deploy until investigated.

## Stage 2 — Supabase / security

To enable the multiplayer group feature, open Supabase SQL Editor and review/apply `SQL_V8_STUDY_LAB.sql`. The script creates `v8_quiz_battles` and `v8_quiz_answers`, enables RLS, and revokes access for anon/authenticated roles. The bot uses the existing **server-only** Supabase secret key. Never add that key to the Mini App or source control.

These Telegram access flags control this **new V8 module only**. They do not automatically restrict every existing feature or verify age. Only authorize users whose eligibility you have independently verified. The existing AI provider's terms and limitations still apply.

```dotenv
V8_ENABLED=false
V8_ALLOWED_USER_IDS=123456789,987654321
V8_AI_ASSISTED=false
V8_PUBLIC_URL=https://YOUR-EXISTING-SERVICE.onrender.com
```

* Keep `V8_ENABLED=false` while installing/test-running the code without public exposure.
* For a controlled adult-only pilot, set `V8_ENABLED=true` and **real, verified allowed Telegram IDs** in Render. These are example IDs above; do not copy them.
* `V8_AI_ASSISTED=false` uses free, offline document and paper analysis; `true` enables opt-in Cloudflare AI after source-sharing consent, reusing the current safety guard and quota. It does **not** enable Gemini.
* `V8_PUBLIC_URL` must be your own live HTTPS Render service URL. The Mini App is launched inside Telegram. Its `/v8/api/overview` rejects requests without fresh, authentic Telegram-signed initData and a V8 allowlisted user.
* Service restarts erase temporary document sessions; saved flashcards, voice transcripts, exams and group quizzes use Supabase persistence. Sensitive document text is held only in bounded server RAM during a chat session.

## Stage 3 — Review Git and deploy once

Do not use `git add .`; the user's current project has many backup and unrelated files.

```powershell
git status --short
git add -- main.py ui_v57.py navigation.py v8_engine.py v8_bot.py v8_miniapp.py SQL_V8_STUDY_LAB.sql TEST_V8_STUDY_LAB.py INSTALL_V8_STUDY_LAB.py
git diff --cached --name-only
git diff --cached --check
git diff --cached --stat
```

Only after you have personally reviewed tests, staged changes and SQL should you commit and push:

```powershell
git commit -m "Add V8 study lab pilot workflows"
git push origin main
```

Render should rebuild the **existing** Docker service. Preserve the existing environment variables, Dockerfile and LibreOffice installation. Set `V8_ENABLED=true` only when the pilot access list and SQL are ready. Do not expose the entire bot publicly to minors merely by hiding V8 menu buttons; full age-gating is a separate system-level task.

## Stage 4 — Test all ten on your live Telegram bot

1. `/v8` in a private chat → V8 study menu.
2. `/v8doc` → upload a text PDF → ask a factual question → see page references. Optional `AI:` must require consent.
3. `/v8papers` → upload sample past paper → inspect extracted questions/terms.
4. `/v8cards` → upload text containing four `Term: definition` lines → choose QUIZ, then SAVE; verify existing Flashcards.
5. `/v8planner` → add a future exam using existing Exams → get a 7-day plan.
6. `/v8lecture` → transcribe and save a Voice Note using the existing feature → choose transcript ID.
7. `/v8progress` → verify private Supabase counts.
8. `/v8cite` → send `APA | Author | 2024 | Paper Title | Journal` → verify reference.
9. Add bot to a group. Use `/v8groupid` in group. Group admin privately creates `/v8battle_new -100... | Question | A | B | C | D | A`, and a group member privately replies `/v8answer -100... B`. Admin runs `/v8battle_end` in group. Confirm answer key isn't publicly visible before results.
10. `/v8app` → open Telegram Mini App; verify no data when opened outside Telegram. `/v8backup` → get JSON.GZ backup in private chat, no group access.

Run V7.17 PDF, Auto Crop, DOCX → PDF, PPTX → PDF, OCR, voice and AI smoke tests again after deploying. The offline test suite **does not replace real Render/Supabase/Telegram testing**.

## Known limitations / release blockers

* The full Python/Flask/Telegram/Supabase runtime was not available in this build environment. Runtime integration tests and provider calls still require your computer/Render.
* Uploaded PDF text may contain unusual layouts and scanned documents; use OCR before importing scanned PDFs.
* The Mini App is currently read-only; a full visual task-management UI is a later extension.
* In-memory document chat sessions are lost on restart (privacy-friendly; not resumable).
* The group quiz currently accepts an admin-provided question rather than generating questions from lecture sources.
* High load, malicious PDFs, large concurrent groups, SQL policies and provider eligibility need live validation before public enablement.
* V8 allowlisting is not identity/age verification or a global gate across older bot features.

## Rollback

You can instantly hide all new V8 features by setting `V8_ENABLED=false` in Render and redeploying/restarting. This leaves V7.17 features intact. The installer also creates a `V8_BACKUP_...` folder containing original versions of `main.py`, `navigation.py`, `ui_v57.py` for manual restoration. The new SQL tables are independent; do not drop them if they hold user quizzes until data is exported or archived.
