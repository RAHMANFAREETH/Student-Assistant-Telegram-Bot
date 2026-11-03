# Student Assistant Telegram Bot V5.7 — Student-friendly Navigation

**Upgrade for the existing V5.6 Cloudflare AI bot**. No new Telegram bot, no new Render service, no new API key, and no changes to your V5.4–V5.6 feature modules.

## What changes

- Main keyboard is shortened from 33 direct feature choices to **8 categories + Help + Menu Language** (10 buttons).
- Each category opens the **original exact Telegram feature button labels**; old handlers, Supabase data and feature workflows are preserved.
- Beginner help guides: Getting Started, Ask AI, Ask My PDF, Flashcards, Study Planning, Voice Notes, and Privacy.
- Guidance text in English, Tamil, Sinhala and Arabic. **Feature button labels stay in English** for compatibility with your current handlers; this is *not* a full translation of every existing module's interface.
- Language preference persists using an *optional* new Supabase table. Without SQL, it is temporary and can reset when Render restarts.

Main categories:

- 🤖 AI & Questions → Ask AI, Ask My Notes, Ask My PDF
- 📚 Study Tools → Subjects, Notes, Study Materials, Global Search
- 📅 Plans & Reminders → Assignments, Timetable, Exams, Study Planner, Reminders, Goals, Smart Notifications
- 🧠 Practice & Quiz → Flashcards, Due Reviews, Review Stats, Quiz, Revision Planner
- 🌍 Languages → Translate, Language Tools
- 📊 My Progress → Today Hub, Dashboard, Progress, Attendance, GPA, Semesters, Study Streak, Smart Insights
- 🎙 Voice & PDF → PDF Tools, Voice Notes
- 📦 More Tools → Student Resources, Export, existing Help

## Install

1. **Back up** `C:\Users\Pros\Desktop\StudentAssistantBot` and check `git status` before changes. Do not upload `.env` or API secrets.
2. Extract ZIP and copy these *new* files to the **existing** `StudentAssistantBot` folder:
   - `ui_v57.py`
   - `INSTALL_V5_7.py`
   - `TEST_V5_7_UI.py`
   - `SQL_V5_7_UI.sql`
   - `GEMINI_AI_STUDIO_PLAN.md` (documentation)
3. Optional but recommended: Run `SQL_V5_7_UI.sql` in your **existing** Supabase project's SQL Editor to preserve chosen menu guidance language after restart. This adds only `ui_language_v57` and does not touch existing tables.
4. In VS Code PowerShell terminal, in your existing project folder, run:

```powershell
python INSTALL_V5_7.py
python -m py_compile main.py navigation.py ui_v57.py
python -m unittest TEST_V5_7_UI.py -v
```

The installer **patches your existing `main.py` and `navigation.py`**. Do NOT replace either file with a generic older version. It creates `main.py.before_v57.bak` and `navigation.py.before_v57.bak`. Re-running the installer after success makes no more changes.

5. Review:

```powershell
git status
git diff -- main.py navigation.py
```

Confirm there are no API keys, credentials or `.env` among staged files.

6. If syntax and tests pass, deploy through your existing GitHub/Render flow:

```powershell
git add main.py navigation.py ui_v57.py INSTALL_V5_7.py TEST_V5_7_UI.py SQL_V5_7_UI.sql GEMINI_AI_STUDIO_PLAN.md
git commit -m "Add V5.7 student friendly navigation and guides"
git push origin main
```

Render should deploy the newest commit. If auto-deploy is off, deploy the newest commit manually.

## Test in Telegram

1. `/start` → see **10 main keyboard buttons** instead of a very long list.
2. `🤖 AI & Questions` → `🤖 Ask AI` → ask a question; return with Main Menu.
3. `🤖 AI & Questions` → `📝 Ask My Notes`, `📄 Ask My PDF`; these still call your V5.6 handlers.
4. `🌍 Languages` → `🌐 Translate`; verify Azure translation still works.
5. `🎙 Voice & PDF` → `🎙 Voice Notes`; verify AssemblyAI transcription and PDF Tools.
6. `🧠 Practice & Quiz` → `🧠 Flashcards` / `🧠 Due Reviews`; verify V5.4.
7. `❓ Help & Tutorial` → `📄 Ask My PDF Guide`; verify step-by-step instructions.
8. `/language` → `🇱🇰 தமிழ்` → `/start`; intro should be Tamil; restart Render and verify the selection persists if SQL was run.
9. `/guide` and `/categories` should work.

**Keep existing feature buttons exactly as they are.** Do not manually translate labels in feature modules: their message handlers often compare button strings literally.

## If something fails

- `python -m py_compile ...` checks syntax, not full Telegram/Supabase integration.
- If install reports missing V5.6 AI handlers, finish V5.6 integration first and rerun; the installer will not silently change the wrong project.
- If preferences reset, run the SQL script and check that your server uses its trusted Supabase service-role client.
- If a category press gets consumed by an old feature's state, share the Render logs and exact action; the installer registers category handlers before old stateful handlers, but live workflows need testing.
- To roll back the files without deleting notes/data, copy `main.py.before_v57.bak` to `main.py` and `navigation.py.before_v57.bak` to `navigation.py`, then commit/push those changes. Do not delete Supabase data.

## Google AI Studio / Gemini is NOT forgotten

Read `GEMINI_AI_STUDIO_PLAN.md`. This public, mixed-age student bot continues to use working Cloudflare AI. Gemini 3.1 Flash Lite is documented as a potential future **separate, compliant adult-only service**, not silently routed into the public bot. **No Gemini API key or second bot is required for V5.7.**
