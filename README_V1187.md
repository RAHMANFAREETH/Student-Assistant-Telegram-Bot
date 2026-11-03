# V11.8.7 — Telegram Library Large-File Relay

The change removes **application-imposed size limits** on *existing Telegram media* copied through `copy_message`. It does **not** remove limits imposed by Telegram or authorize downloading/processing 4 GB of data on Render.

## Why your 63.9 MB Tamil PDF was rejected

`book_library_bot.py` defaults to a 50 MiB cap (`BOOK_LIBRARY_MAX_BYTES=52428800`) and clamps it at 2 GiB. V11.7 media uploads also have a 50 MiB default and 100 MiB upper clamp; V11.3 and V11.7 community submissions have a 20 MiB default. These limits are unnecessary for approved Telegram-to-Telegram message copies.

## Changes

- `book_library_bot.py` — use `BOOK_LIBRARY_MAX_BYTES=0` as the default (unlimited **application** cap); retain positive administrator caps; reject negative configuration.
- `book_library_v113_bot.py` — use `BOOK_LIBRARY_SUBMISSION_MAX_BYTES=0` as the default for community review submissions; retain positive caps.
- `library_media_v117_bot.py` — use `LIBRARY_MEDIA_MAX_BYTES=0` and `LIBRARY_MEDIA_SUBMISSION_MAX_BYTES=0` as defaults for media copied through Telegram; retain positive caps.
- `TEST_BOOK_LIBRARY.py` — keep legacy 50 MB rejection test meaningful by setting that cap **in the test only**.
- `TEST_LIBRARY_LARGE_RELAY_V1187.py` — new tests cover 63.9 MB admin uploads, 4 GB metadata and copying, 4 GB review submissions, optional limits, original processing safety limits, and BIGINT database sizes.

**Unchanged:** adult-access controls, admin checks, rights-review workflow, Supabase schema, copying/storage permissions, ZIP extraction, hashing, OCR/PDF processing download limits, deployment Dockerfile, and existing bot handlers.

## Telegram's platform limits still apply

- Normal Telegram accounts can send files up to 2 GB; Premium accounts can upload files up to 4 GB to Telegram. Bot account Premium eligibility does not change.
- The standard cloud Bot API allows the bot to upload a **new** multipart file up to 50 MB and `getFile` downloads up to 20 MB. A self-hosted Bot API server supports uploads up to 2000 MB. None of those thresholds apply to *copying already-uploaded messages* using `copy_message` or reusing file IDs, subject to source accessibility, permissions, and Telegram's restrictions.
- A 4 GB file must **already be available in a Telegram message** visible to the bot (e.g. sent to bot by a Premium user), so the bot can copy it directly. It is not downloaded to Render.
- For large files, OCR/preview/advanced PDF conversion can be unavailable; library cataloging, searches, and delivery can still work.

## Install (Windows PowerShell)

Extract this ZIP into `C:\Users\Pros\Desktop\StudentAssistantBot` (**not** a nested subfolder), then run:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 PATCH_LIBRARY_LARGE_RELAY_V1187.py --check
python -X utf8 PATCH_LIBRARY_LARGE_RELAY_V1187.py --apply
python -m py_compile book_library_bot.py book_library_v113_bot.py library_media_v117_bot.py
python -X utf8 -m unittest TEST_LIBRARY_LARGE_RELAY_V1187 TEST_BOOK_LIBRARY TEST_BOOK_LIBRARY_V113 TEST_LIBRARY_MEDIA_V117 -q
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

`--check` never changes files. `--apply` backs up originals under `V1187_LARGE_RELAY_BACKUP_*`; aborts if source anchors have diverged. Do not overwrite conflicting files manually.

## Render environment

If the variables already exist with a positive cap, defaults will **not** override them. For admin uploads, set:

```
BOOK_LIBRARY_MAX_BYTES=0
LIBRARY_MEDIA_MAX_BYTES=0
```

For community submissions, optional (consider abuse and review capacity before removing these caps):

```
BOOK_LIBRARY_SUBMISSION_MAX_BYTES=0
LIBRARY_MEDIA_SUBMISSION_MAX_BYTES=0
```

Only modify Render values **after** source is pushed and deployment is successful. Do not remove adult verification, copyright/rights checks, moderator review, or Telegram message privacy.

## Git safety

Do **not** run `git add .`. Stage only three production files and this new test (and optionally the adjusted legacy test) after verifying on your Python 3.14 system. Backups, environment files and reports should never be committed.

Suggested staging, after reviewing `git diff` and results:

```powershell
git add -- book_library_bot.py book_library_v113_bot.py library_media_v117_bot.py TEST_BOOK_LIBRARY.py TEST_LIBRARY_LARGE_RELAY_V1187.py
git diff --cached --check
git diff --cached --stat
```

The installer itself is not required on Render after source changes are committed. Release after full regression and live Telegram copy/delivery tests.

## Verification

**Offline Python 3.13.5**: 168 focused tests passed, no failures. A full test run was interrupted before completion and has not been certified; confirm in Python 3.14 on Windows before deployment.
