# Student Assistant Telegram Bot — V11.8.8 Smart Bulk Upload

This is an **opt-in** enhancement to your deployed V11.8.7 bot, intended to reduce manually captioning every library file. It uses the existing V11.7 administrator upload and Telegram `copy_message` implementation and preserves V11.8.7's large-file behavior. **Do not deploy without checking your live repository, tests, and adult-access configuration.**

## What changes

- **📦 Bulk Import** admin button and `/mediabulk` start a private, 2-hour session when `LIBRARY_SMART_BULK_V1188_ENABLED=true`.
- Admin sets shared **language, category, rights declaration, author, and comment once** via `/mediabulkset`.
- Send up to **100 individual Telegram files per session**, in manageable multi-select batches through Telegram Desktop (Telegram may restrict how many files can be selected in one send).
- Each file's default title is inferred from its **filename**, preserving Tamil, Sinhala and Arabic characters. A simple caption overrides that file's title. A full `|`-separated caption overrides all shared fields for that file.
- Each file uses the existing `submit_media()` path, including exact Telegram `file_unique_id` (and optional SHA) duplicate check, `copy_message`, storage channel, Supabase row creation, cleanup on DB save failure, rights declaration and admin checks. Same filename alone is **not** considered proof of duplication.
- A private progress message is edited when supported; otherwise a status is sent periodically. `/mediabulkstatus` shows counts; `/mediabulkdone` finalizes. `/mediacancel` discards the session.
- Failed and duplicate files are counted and skipped without terminating the whole batch.
- **ZIP archives are not made unlimited.** The existing 20 MB ZIP download, 20-file, 40 MB expanded and per-entry extraction limits stay in place.
- No new Supabase migration, paid API, or additional Render service. Sessions are **process-local**: they reset when Render restarts or redeploys. There is no persistent queue or automatic resume.

## Safety and limitations

Only authorized administrators in private chats can configure/publish a smart batch. **One shared permission declaration is only suitable if you really have distribution rights to every file in the batch**; the bot cannot legally verify rights by itself. Individual files with different rights should be sent with fully specified captions or in separate batches.

Your V11.8.7 `copy_message()` transport is reused. This does not increase Telegram platform upload limits or grant access to files the bot cannot see. Original 4 GB files must already exist in Telegram. OCR, conversion, ZIP extraction and other operations may require smaller size limits and are NOT expanded.

Feature is **disabled by default**. If disabled, `/mediabulk` keeps its older 30-file behavior (including existing caption checks).

## Installation — Windows PowerShell

1. Extract `StudentAssistantBot_V11_8_8_Smart_Bulk_Upload.zip` into `C:\Users\Pros\Desktop\StudentAssistantBot` (the project root; don't extract to a nested folder).
2. Ensure the project's currently deployed V11.8.7 source is present and you have a Git backup/commit.
3. Run:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 INSTALL_SMART_BULK_V1188.py --check
python -X utf8 INSTALL_SMART_BULK_V1188.py --apply
python -m py_compile library_smart_bulk_v1188.py library_media_v117_bot.py
python -X utf8 -m unittest TEST_SMART_BULK_V1188 TEST_LIBRARY_LARGE_RELAY_V1187 TEST_LIBRARY_MEDIA_V117 TEST_GROUP_BOOK_ONLY_V116 TEST_LIBRARY_MANAGE_V118 -q
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

`--check` shows a unified diff and modifies nothing. `--apply` changes **only** `library_media_v117_bot.py` and backs up its previous version to `V1188_SMART_BULK_BACKUP_*`. The ZIP provides two new Python modules (`library_smart_bulk_v1188.py` and its test). The installer is idempotent and stops if source anchors don't match. If `--check` says `STOP`, do not force the patch.

4. Review staged changes; do not use `git add .` (your project contains many backups and unrelated files):

```powershell
git add -- library_media_v117_bot.py library_smart_bulk_v1188.py
# Optional regression-test source:
git add -- TEST_SMART_BULK_V1188.py
git diff --cached --check
git diff --cached --stat
git diff --cached --name-only
git diff --cached
```

5. **Only after reviewing and passing your Windows Python 3.14 tests**, commit/push your intended files. Confirm the new commit deploys successfully in the *existing* Render service.
6. Add environment variable `LIBRARY_SMART_BULK_V1188_ENABLED=true` on Render. Preserve `LIBRARY_MEDIA_V117_ENABLED`, `BOOK_LIBRARY_ENABLED`, approved-admin IDs, adult-access settings, all existing library channel IDs, and other security configuration.

## Telegram usage

In a **private** chat with your bot, as an administrator:

```
/mediabulk
```

Next, declare shared metadata for the current batch (example—**use a truthful license/permission that covers every file**):

```
/mediabulkset Tamil | Education | permission | Unknown | Distribution rights verified
```

Supported rights codes: `permission`, `public_domain`, `cc0`, `cc_by`, `cc_by_sa`. Then use Telegram Desktop → Attach → Files → select several files → send (documents, not compressed media). You do **not** need a caption on every document.

A file called `Tamil_Grammar_Book.pdf` gets the inferred title `Tamil Grammar Book` and shared language `Tamil`, category `Education`, etc. A plain caption like `Tamil Grammar Volume 1` overrides only its title. A fully qualified caption like `Tamil Grammar Volume 1 | Author Name | Tamil | Grammar | permission | Rights verified` overrides that file's shared metadata.

Show progress:

```
/mediabulkstatus
```

Finish and see summary:

```
/mediabulkdone
```

Or cancel:

```
/mediacancel
```

## Live verification checklist

- Admin-only and private-chat enforcement; unauthorized users rejected.
- Set shared metadata for Tamil books, send 3 different PDFs without captions. Verify title, language, category and permissions stored correctly.
- Resend the same Telegram document, verify it is counted as a duplicate and not republished.
- Upload a 63.9 MB PDF; confirm library copy and private delivery work as in V11.8.7.
- Send an invalid file or simulate a failed copy; verify the batch continues and reports failure.
- Check `/mediabulkstatus`, `/mediabulkdone`, and `/mediacancel`.
- Verify other PDF/OCR tools, admin functions, adult restrictions, group cleanup and existing library search remain working.

## Verification performed in the preparation environment

Python 3.13.5 offline: 29 direct V11.8.8 tests passed; 166 relevant integration/regression tests passed. The complete isolated regression run **passed 85/85 modules (1,710 tests, 1 skipped, 0 failures)** before the final callback-button test was added; that new test separately passed. Windows Python 3.14 and real Telegram/Supabase operations must be tested before release. Test doubles do not prove that Telegram accepts every 4 GB copy.
