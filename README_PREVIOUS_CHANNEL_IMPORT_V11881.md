# Student Assistant Telegram Bot — V11.8.8.1 Previous Channel Import

This is an **add-on to V11.8.8 Smart Bulk Upload**. It supports both:

1. **Manual forwarding** of old file messages from your own Telegram channel to the bot's private admin chat, after `/mediabulk` and `/mediabulkset`.
2. **Automated historical import** of existing PDF/EPUB/DOCX/TXT channel posts from a channel you **own/administer** using a *local* Telethon user client. Each file is forwarded server-to-server into the bot's smart bulk workflow; your computer and Render **do not download the file bytes**.

## Critical limitation

The standard **Bot API cannot fetch a channel's old history on demand**; merely making your bot a channel admin only enables future `channel_post` updates. Historical import therefore runs on **your own Windows PC, authenticated as the same Telegram USER account authorized as the bot administrator**. This is NOT a way to bypass protected content. Do not import third-party material without redistribution rights.

Telegram documentation:
- https://core.telegram.org/bots/api
- https://docs.telethon.dev/en/stable/modules/client.html
- https://core.telegram.org/api/content-protection
- https://my.telegram.org/

## Install the compatibility patch first

Ensure V11.8.8 `library_smart_bulk_v1188.py` and `library_media_v117_bot.py` are already installed locally. Extract this ZIP into your current project root (`C:\Users\Pros\Desktop\StudentAssistantBot`). It is safe to open the ZIP and inspect all code before use.

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"

python -X utf8 PATCH_PREVIOUS_CHANNEL_CAPTIONS_V11881.py --check
python -X utf8 PATCH_PREVIOUS_CHANNEL_CAPTIONS_V11881.py --apply

python -m py_compile library_media_v117_bot.py library_smart_bulk_v1188.py IMPORT_PREVIOUS_CHANNEL_FILES_V11881.py
python -X utf8 -m unittest TEST_PREVIOUS_CHANNEL_IMPORT_V11881 TEST_SMART_BULK_V1188 TEST_LIBRARY_LARGE_RELAY_V1187 TEST_LIBRARY_MEDIA_V117 -q
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

The guarded patch changes **only `library_smart_bulk_v1188.py`**, keeps a timestamped backup and is idempotent. It tells Smart Bulk to disregard old captions on forwarded channel messages, using the **filename** and **your admin-approved shared metadata** instead. Your nonforwarded admin-upload captions continue to work as before. **No change to database, OCR, ZIP, group routing, adult access, or V11.8.7 file relay.** The local importer script and tests are new files.

If the patch says STOP, don't force it. Send the output for review.

## Deploy V11.8.8 and compatibility to your existing Render service

V11.8.8 was not yet confirmed deployed. Review all changes first; stage only intended files, not backups or secrets:

```powershell
git status --short
git add -- library_media_v117_bot.py library_smart_bulk_v1188.py
# Optional: stage tests and safe utility source after reviewing:
# git add -- TEST_SMART_BULK_V1188.py TEST_PREVIOUS_CHANNEL_IMPORT_V11881.py IMPORT_PREVIOUS_CHANNEL_FILES_V11881.py
# If you applied the earlier test-only group fix, review its test change separately.
git diff --cached --check
git diff --cached --stat
git diff --cached
```

After Windows regression passes, commit/push and confirm your existing Render service deployed that commit. Add on Render:

```
LIBRARY_SMART_BULK_V1188_ENABLED=true
```

Preserve all existing bot environment variables, channel IDs, permissions, adult-access gates and V11.8.7 file relay settings.

## Manual: forward previous channel files

1. Start **private admin chat** with your bot, type `/mediabulk`.
2. Set truthful shared batch metadata, e.g. `/mediabulkset Tamil | Education | permission | Unknown | Licensed for distribution` (only if true for every file).
3. Open the source channel in Telegram Desktop, select multiple historical PDF posts, **Forward** to the bot.
4. Check `/mediabulkstatus`, then finish `/mediabulkdone`.

One smart batch accepts up to 100 files. Split larger collections into multiple sessions. Protected posts cannot be forwarded.

## Automatic: import *previous* files without manual selection

### 1. Install local Telethon, not on Render

```powershell
python -m pip install "telethon>=1.42,<2"
```

At https://my.telegram.org, open **API Development Tools** and register a Telegram application to obtain your own **API ID** and **API hash**. These are NOT your bot token. **Never paste your API hash, OTP/login code, password, session file or bot token into ChatGPT, GitHub, Render logs, or a Telegram chat.** The script prompts for the ID and hash locally and logs into your real Telegram **user** account on your PC, using the regular Telegram sign-in flow.

The login session file is saved OUTSIDE the project, under:

```
%LOCALAPPDATA%\StudentAssistantBot\previous-channel-import\telegram-user.session
```

Protect this file like a password and never commit it. Close the application when finished. You can terminate this local session from Telegram Settings > Devices.

### 2. List your own channels

```powershell
python -X utf8 IMPORT_PREVIOUS_CHANNEL_FILES_V11881.py --list-channels
```

The script will display the title and numeric ID or @username of channels which your account owns/administers.

### 3. Preview old files; this sends nothing

Replace **both** placeholders below with the actual source channel and bot username:

```powershell
python -X utf8 IMPORT_PREVIOUS_CHANNEL_FILES_V11881.py --dry-run --source "@YOUR_SOURCE_CHANNEL" --bot "@YOUR_BOT_USERNAME" --max-files 50
```

### 4. Start an automated batch (after Render V11.8.8 is live)

Example: **only if you really have distribution rights to every file**:

```powershell
python -X utf8 IMPORT_PREVIOUS_CHANNEL_FILES_V11881.py --apply --source "@YOUR_SOURCE_CHANNEL" --bot "@YOUR_BOT_USERNAME" --max-files 50 --language "Tamil" --category "Education" --author "Unknown" --rights permission --rights-note "Written distribution permission confirmed"
```

Confirm by typing `IMPORT` when the exact channel and bot appear. The importer sends `/mediabulk` and `/mediabulkset` from your user account, **waits for an acknowledgment from the bot**, then forwards older channel documents in chronological order, with a default **2-second delay** to avoid flooding. It drops channel caption text so filename-based titles are used. `--max-files` is limited to **1–100** per batch to respect V11.8.8. The default is 50.

After a batch, open your bot and inspect `/mediabulkstatus`. Verify published, skipped, and failed counts, and use `/mediabulkdone` only after all Telegram operations finish. For the next batch, run the same command again: it resumes from a checkpoint saved outside the repository.

A **checkpoint means the file was forwarded, not that Supabase confirmed it was published.** Inspect failures before the next batch. To retry history from the beginning, use `--reset-checkpoint` (existing exact duplicates should be skipped by your bot). If a history section contains many non-document posts, increase `--scan-limit 2000` to a reasonable number.

### For private channels

The `--list-channels` output gives the numeric channel ID. Pass it as a quoted string to `--source`. The script must be logged in to an account that actually owns/administers the private channel.

## Safety and limitations

- This script forwards **PDF, EPUB, DOCX, TXT** Telegram documents only. No ZIP extraction, PDF/OCR processing, mass downloading, or media scraping.
- **Does not bypass Telegram's protected-content flag**. A channel that restricts forwarding cannot be imported by this mechanism. Do not attempt to circumvent it.
- It imports only channels the authenticated account **owns/administers**, and forwards only to a Telegram **bot** that the user explicitly confirms.
- One new private Smart Bulk session is started per run. The script is resumable but not a permanent background service.
- Existing V11.8.7 large-file relaying and Telegram's platform restrictions still apply. A genuine 4 GB file has not been live-verified by this offline test suite.
- Telegram may rate-limit forwarding, restrict content, or refuse particular media; respect errors and retry later if prompted. Avoid sending huge batches too fast.
- Do not store Telegram API credentials or the user-session file on Render. No new paid API, database table, bot token, or service is needed.
- This utility does not automatically subscribe to future source-channel posts; it can be run again to import newer messages. An always-on sync would require a separately designed, opt-in channel-post handler.

## Verification performed by patch author

- Guarded patch `--check`, `--apply`, and new importer's offline tests succeeded in Linux Python 3.13.5.
- 14 new historical-import tests passed (including protected channel handling, admin-only source, credential/session directory isolation, dry-run, manual-forward captions, checkpoint resume, no confirmation/no sends, and bot acknowledgments mocked).
- Combined focused suite of **109 tests** passed including V11.8.8, large-file relay, unified media library and the new historical importer.
- A full isolated regression was attempted but the execution window ended before completion (first 37/86 modules passed). **Do not treat that as a completed full-regression pass.** Run the full suite on Windows Python 3.14 before deploying.
- No real Telegram account, Premium 4 GB transfer, source-channel history or Supabase connection was exercised during offline tests.
