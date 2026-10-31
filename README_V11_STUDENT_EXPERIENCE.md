# V11.0 Student Experience & Performance — Safe Add-On

**Status:** Offline-tested release candidate, **not automatically deployed**. Built for the same existing Student Assistant Telegram bot, one Render web service, one Supabase project, existing Gemini AI Studio and age-verification configuration. Does **not** add any new API key, pip dependency or Supabase migration.

## What changes

V11 is a focused **navigation/operability update**, not a rewrite of V7–V10.1 engines. It adds a new **🚀 Study Center** entry to More Tools and seven commands:

| Command | What it does |
|---|---|
| `/study` or `/v11` | Fast inline-button Study Center. Menu generation uses **no Gemini or Supabase calls**. |
| `/studyhelp` or `/studyhelp docs` | Short, copyable walkthroughs for existing tools: docs, ai, practice, more, access, errors. |
| `/studystatus` | User-facing configuration status and a read-only adult verification check when verified-adult mode is active. This may query Supabase. |
| `/studycancel` | Clears **only the requesting user's temporary V10 and V10.1 in-memory sessions**, including pending upload/consent. Does not delete saved files or chats, does not cancel V8/V9, and does not make external provider requests. |
| `/studydiag` | Authorized administrator-only, private-chat configuration/module-presence check. Doesn't show keys, contents or users. It is not a live provider health check. |
| `/studyperf` | Administrator-only bounded **V11-only** handler processing timings/counters. No PII, in-memory and reset at restart; not an end-to-end benchmark. |

**Telegram button navigation:** Documents, Gemini, Practice, All Tools, Adult Access, Status, Troubleshooting and Cancel Pending; pages include a Back-to-Home button. Callbacks are single-use, tied to the exact Telegram user/private chat, expire in 5 minutes and are stored in a 256-entry bounded in-process cache. `/study` refreshes an expired menu. The older `v10:*`, `v101:*` and admin callbacks are untouched.

**Security:** This is a navigator/help system, **not an alternative authorization gate**. Menus explain existing commands but cannot grant adult access. All underlying V10/V10.1 AI/data actions retain their own verified-adult gates, consents, Gemini daily quota and provider-specific limits. Every V11 command requires a private chat; only `V91_ADMIN_USER_IDS` members can use the diagnostics. For actual approved/expired adult status use `/access_status`. It is safe to disable this add-on independently.

**Performance scope:** Study Center menus avoid DB/provider work. Local timings help diagnose V11 menu processing. No claims are made about faster PDF extraction, Gemini inference, Supabase queries or older V8/V9/V10 engines. Those remain unchanged.

## Package files (5 new files)

- `v11_center.py` — menus, safe callbacks, help, status, cancellation and admin diagnostics.
- `v11_metrics.py` — bounded, privacy-minimal local metrics.
- `INSTALL_V11_STUDENT_EXPERIENCE.py` — idempotent `--check` / `--apply`, preserving UTF-8 BOM and CRLF, with automatic backups.
- `TEST_V11_STUDENT_EXPERIENCE.py` — 52 offline tests (no live Telegram, Gemini or Supabase).
- `README_V11_STUDENT_EXPERIENCE.md` — this guide.

Installer adds only V11 registration to `main.py` (before V10.1), its menu label to `ui_v57.py`, and its global navigation button to `navigation.py`. It never edits V10, V10.1, adult access, provider, SQL, PDF, or older core modules.

## 1. Install locally (Windows PowerShell)

1. Back up the working bot folder. Extract the ZIP; copy all **5 new files** to `C:\Users\Pros\Desktop\StudentAssistantBot`.
2. Check proposed changes **before** applying:

```powershell
python INSTALL_V11_STUDENT_EXPERIENCE.py --check
python -m unittest TEST_V11_STUDENT_EXPERIENCE -q
```

3. Review the diff; it should show only V11 additions to **`main.py`, `ui_v57.py`, and `navigation.py`**. The main handler must be before `register_v101_handlers(bot)` and older V10 stateful handlers. If the expected anchors are missing, the installer stops without editing.
4. Apply the reviewed changes:

```powershell
python INSTALL_V11_STUDENT_EXPERIENCE.py --apply
python INSTALL_V11_STUDENT_EXPERIENCE.py --check
python -m py_compile main.py ui_v57.py navigation.py v11_center.py v11_metrics.py
python -m unittest TEST_V11_STUDENT_EXPERIENCE -q
python -m unittest TEST_V10_ADVANCED_STUDY TEST_V10_GEMINI TEST_V101_COMBINED -q
```

In offline validation, **208 tests passed together** across V10, V10.1 and V11 (156 existing + 52 V11). Your current working tree may contain newer changes, so run local tests yourself and review their output.

5. Run existing V9.1/V9.2/V9.3 suites separately and V8/V9 test fixtures. Older V8/V9 test fixtures may need `STUDY_ACCESS_MODE=pilot` **locally for that process only**, with the value restored afterward. Never switch production to pilot just to satisfy tests.

## 2. GitHub staging (avoid backup folders)

Your working tree has many untracked backup/install files. **Do not run `git add .`**.

```powershell
git diff --cached --name-only
# Review any previously staged changes first.
git add -- v11_center.py v11_metrics.py INSTALL_V11_STUDENT_EXPERIENCE.py TEST_V11_STUDENT_EXPERIENCE.py README_V11_STUDENT_EXPERIENCE.md
git add -p -- main.py ui_v57.py navigation.py
git diff --cached --check
git diff --cached --name-only
git diff --cached --stat
```

Expected **8 intended files**: five new plus three existing integration files. Press `y` only for V11 hunks, `n` for unrelated edits; if a combined hunk can't be split, stop and review before committing.

```powershell
git commit -m "V11: Add fast Study Center and admin diagnostics"
git push origin main
git show origin/main:main.py | Select-String "register_v11_handlers"
```

**Verify the new `v11_center.py` and `v11_metrics.py` files are also pushed**, not only `main.py`; an import error would otherwise prevent Render startup.

## 3. Render rollout

1. Before the GitHub deployment, add this to the existing Render service:

```dotenv
V11_ENABLED=false
```

2. Keep your working `STUDY_ACCESS_MODE=verified_adults`, `V8_ENABLED`, `V9_ENABLED`, `V10_ENABLED`, `V101_ENABLED`, Gemini key and V9.1/V9.2/V9.3 settings unchanged. **No SQL migration is required** for V11.
3. Push, confirm the **exact new Git commit** is deployed, Render is **Live**, and the Telegram webhook still succeeds.
4. Set `V11_ENABLED=true`, save/deploy.
5. From your private verified-adult account test:

```text
/study
/studyhelp docs
/studystatus
/studycancel
/studydiag
/studyperf
/v10
/v101
/v8
/v9
/adult_admin
```

6. Tap each Study Center inline button once, then Home; an old button should safely say expired/used. An ordinary non-admin should be denied `/studydiag` and `/studyperf`.
7. Check Render logs for errors and verify existing V10.1 OCR/voice/Gemini consent and daily quota work as before.

## Disable / recover

If V11 has a problem, set **`V11_ENABLED=false`** and redeploy to hide its menu and disable its commands without affecting older study tools. To fully remove the registration, restore the three affected files from the generated `V11_BACKUP_...` folder and review Git history. Avoid overwriting subsequent changes without reviewing the diffs.

## Limitations

- V11's process-local tokens and performance counters reset on Render restart. Multiple workers do not share tokens; a callback may expire if a different worker receives it. Existing Render commonly uses one worker, but use a persistent store if you later scale horizontally.
- V11 displays convenient command guides; its inline buttons **do not automatically execute the old `/v10` or `/v101` command handlers**. They show the correct actions to send, avoiding private session corruption.
- Existing older upload/OCR, Gemini and voice operations still have their original latency, limits and provider costs. V11 adds no paid service, and is not a claim that the entire bot is faster.
- The test suite is offline; run manual live checks before inviting more users. Do not share Render/Supabase/Gemini credentials.
