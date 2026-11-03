# Student Assistant Telegram Bot — V9.0 Academic Toolkit (release candidate)

**Status:** offline-tested release candidate, **not deployed**. All 14 tools are bundled in **one release**, with a single intended Git commit and a single Render code deployment. Do not deploy before checking your *latest* local V8.0 project.

## What's new

| Feature | Working scope in this release candidate | Important limitation |
| --- | --- | --- |
| 📸 Math Solver | Safely solves simple typed linear/quadratic equations; optional OCR photo input | Not a vision AI or a general calculus solver; photo OCR requires explicit consent |
| 🧠 Mind Map Generator | Extracts topics from PDF/DOCX/TXT and renders a simple PNG map | Topic extraction is heuristic, not semantic comprehension |
| 📊 Presentation Maker | Produces an **editable PPTX** (up to 11 slides) from uploaded notes | Slides need editorial and design review |
| 🔬 Diagram Label Reader | Reads labels from a diagram photo with OCR | Does **not** interpret arrows or visual relationships; not a true diagram explainer |
| 📋 Assignment Checker | Word count, section/citation heuristics | Not plagiarism or rubric compliance verification |
| 📖 Syllabus Tracker | Save, list and mark personal syllabus topics complete | Currently accepts typed topic lists; manual progress tracking |
| 🧮 Formula Sheet | Extracts candidate formula lines to a DOCX | Extraction may include non-formula equations |
| 🖼 Timetable Photo Import | OCR preview with explicit **SAVE TIMETABLE** confirmation; writes to existing timetable | Accepts `Mon 09:00-10:30 Subject` style lines; other layouts may not parse |
| 🔎 Document Comparison | Reports text line differences between two PDF/DOCX/TXT files | Does not compare visual layout or image changes |
| 📓 Mistake Notebook | Save and mark a student's incorrect questions as mastered | Manual collection; no automatic quiz interception yet |
| 🍅 Focus Timer | Stores a 5–90 minute session and checks completion by command | **No automatic Telegram alerts**; user checks `status` and `finish` |
| 📤 Anki Export | Exports existing flashcards as importable TSV | Not an `.apkg` deck package |
| 🔍 Citation Verifier | Fetches DOI/ISBN bibliographic metadata from Crossref/Open Library | Requires internet; source metadata isn't a guarantee of citation correctness |
| 👥 Study Rooms | Invite-code shared rooms and notes, server-side access checks | Text-based; no live video/chat or collaborative editor |

The original V7.17 PDF tools, V8.0 study workflows, Docker + LibreOffice, and Supabase services are **not replaced**. V9 adds a separate opt-in Telegram menu under **📦 More Tools**.

## Safeguards

- `V9_ENABLED=false` (default). V9 access also requires the existing `V8_ENABLED=true` and a Telegram ID in `V8_ALLOWED_USER_IDS`. Do not treat this as age verification.
- The V9 code **does not** call Gemini or AI language models. The math engine uses local SymPy, and document processing uses your V8 `extract_document`.
- OCR photo tools use your existing `OCR_SPACE_API_KEY`, and *only transmit a photo after* the user replies `I AGREE OCR`. Photos must be <950 KB. OCR.space is an external service; review its privacy policy before using student documents.
- The external citation verifier only requests structured DOI/ISBN metadata from two fixed HTTPS hosts. No arbitrary URL fetching.
- Uploaded source files and photo bytes are held in process memory for at most 12 minutes or until `/v9cancel` (a restart clears them). No uploaded documents are saved to Supabase by V9.
- V9 creates new Supabase tables; all have RLS enabled and anon/authenticated privileges revoked. Backend uses existing server-side secret key. Application code verifies Telegram user ID or room membership.
- PDFs must contain selectable text; use your existing OCR features for scanned pages.
- No new Telegram bot, Render service, paid API, or Gemini integration required. `sympy>=1.13,<2` is the only new Python dependency.

## Install locally (Windows PowerShell)

1. Make a safe backup of your *current* `StudentAssistantBot` folder. The ZIP is **not** a full project replacement.
2. Extract the ZIP and copy all six files into your existing bot folder (alongside `main.py`). Do not copy over your V8 or V7 modules.
3. Run:

   ```powershell
   python INSTALL_V9_ACADEMIC_TOOLKIT.py --check
   ```

   Confirm the only proposed edits are in `main.py`, `navigation.py`, `ui_v57.py`, `requirements.txt`.
4. If `CHECK OK` and you have reviewed the diff:

   ```powershell
   python INSTALL_V9_ACADEMIC_TOOLKIT.py --apply
   python -m pip install "sympy>=1.13,<2"
   python -m py_compile v9_engine.py v9_bot.py main.py navigation.py ui_v57.py
   python -m unittest TEST_V9_ACADEMIC_TOOLKIT TEST_V8_STUDY_LAB -q
   ```

5. Run your **full previously passing V7.17/V8.0 regression command**, especially PDF, Scanner, Auto Crop, Office conversions, group quizzes, and UI. The 83 isolated V8+V9 tests run in the release development environment are *not* a substitute for local regression tests.
6. Keep `V9_ENABLED=false`. Apply `SQL_V9_ACADEMIC_TOOLKIT.sql` in **your existing Supabase project** using SQL Editor (review SQL first). It creates six new tables and no drop/delete commands. Back up production data before migrating.
7. In Render Environment set `V9_ENABLED=false` initially. Keep `V8_ENABLED=true` only for your verified pilot and keep your existing `V8_ALLOWED_USER_IDS` restricted to approved accounts. Do not disclose the bot token or database keys.

## Safe Git staging (only after tests and SQL review)

First ensure `git status -sb` shows a clean or understood working branch synchronized with `origin/main`. Check for previously staged unrelated files:

```powershell
git fetch origin
git status -sb
git diff --cached --name-only
```

Stage only these V9 files; review exactly what is staged:

```powershell
git add -- main.py navigation.py ui_v57.py requirements.txt
git add -- v9_engine.py v9_bot.py TEST_V9_ACADEMIC_TOOLKIT.py
git add -- INSTALL_V9_ACADEMIC_TOOLKIT.py SQL_V9_ACADEMIC_TOOLKIT.sql
git diff --cached --name-only
git diff --cached --check
git diff --cached --stat
```

There should be **9 intended files**. No `.env`, backups, local reports, or credentials.

**Only after the complete local regression suite passes and the configuration is safe:**

```powershell
git commit -m "Add V9.0 Academic Toolkit pilot"
git push origin main
```

On Render, verify the new commit becomes **Live** while V9 is **disabled**. Test existing V8/V7 functionality. Then set `V9_ENABLED=true` and Save and Deploy. Use `/v9` in Telegram as your existing approved adult tester. Test all 14 workflows.

If the new code causes problems, set `V9_ENABLED=false` and redeploy that setting. For critical failures roll back to your previous successful Render deployment.

### Dependencies and configuration

```text
V9_ENABLED=false              # new; keep disabled until all checks pass
V8_ENABLED=true               # already configured for V8 pilot; don't broaden access
V8_ALLOWED_USER_IDS=<your approved Telegram IDs>
OCR_SPACE_API_KEY=<existing key, optional for OCR photo tools>
```

**Do not set `V9_ENABLED=true` before applying SQL migration and verifying V8 access control.**

### Verification limitations

The release was tested **offline** with existing V8 components (83 V8 + V9 test executions, with additional isolated unit tests). Real Telegram message routing, Render memory/cold starts, OCR.space limits, Crossref/Open Library availability, row access for multiple real accounts, Supabase schema and the existing 209-test V8 regression suite must be checked locally/in the approved pilot. The 14 tools are MVP workflows; particularly diagram explanation, automatic timer alerts and automatic quiz mistake capture need further engineering to be fully featured.
