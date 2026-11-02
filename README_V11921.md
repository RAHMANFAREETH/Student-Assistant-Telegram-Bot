# V11.9.2.1 — Telegram Channel ZIP Importer (Windows companion)

## Preserve the working method

**The existing bot ZIP upload up to 20 MB stays exactly as it is.** This package makes **no change to the Render bot, GitHub, Dockerfile, Supabase, your age controls, or ZIP handling on the server**. Continue to send ZIPs of 20 MB or less using the current in-bot ZIP importer.

For ZIP messages larger than 20 MB on Telegram, this **optional local Windows companion** uses your own authorized Telegram **user account** (Telethon) to download the ZIP *automatically* to your PC, then safely extract each eligible book and upload it individually to your working `/mediabulk`. You do **not** need to manually download the ZIP in Telegram Desktop. You **do need a Windows PC with adequate disk space and internet access**; this cannot transfer ZIP data directly into Render and bypass Telegram's Bot API download restriction.

## Requirements

- Existing working bot V11.9.1 with unlimited Smart Bulk; existing source channel/group you can access; source messages must **not** have restricted forwarding/saving; redistribution rights for included books.
- Windows Python (your Python 3.14 is fine), your Telegram user account that is an authorized bot admin, Telegram API ID and API hash from https://my.telegram.org/apps.
- Local disk space for the downloaded ZIP **plus** space for one extracted book **plus** safety reserve; enough bandwidth. No total ZIP size limit in our code, but your physical disk/network and Telegram's file-size limits remain.
- Telethon: `python -m pip install "telethon>=1.42,<2"`

## Installation

Extract the package to `C:\Users\Pros\Desktop\StudentAssistantBot`. It contains three files:

- `IMPORT_TELEGRAM_ZIPS_V11921.py` — new Telegram-message-based front end.
- `IMPORT_LOCAL_BOOK_ZIPS_V1192.py` — existing local ZIP importer dependency, **same unchanged version**, supplied for convenience.
- `TEST_IMPORT_TELEGRAM_ZIPS_V11921.py` — offline tests.

**If you already have `IMPORT_LOCAL_BOOK_ZIPS_V1192.py` in your project, do not overwrite your modified copy without checking the differences.**

## Step 1: Run tests

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 -m unittest TEST_IMPORT_TELEGRAM_ZIPS_V11921 TEST_IMPORT_LOCAL_BOOK_ZIPS_V1192 -q
```

## Step 2: Copy a real Telegram ZIP message link

In Telegram Desktop, right-click the ZIP message → **Copy Message Link**. Example URLs (replace with your own):

- `https://t.me/c/1234567890/55` for private channels **your own account can access**.
- `https://t.me/AccessibleChannel/77` for public channels.

Use a **message** link pointing directly to the `.zip` document, not a channel URL or invite link. The importer does not join channels, scrape unknown channels or bypass protected-content restrictions.

## Step 3: Preview file without downloading

```powershell
python -X utf8 IMPORT_TELEGRAM_ZIPS_V11921.py --dry-run --link "https://t.me/c/1234567890/55"
```

The first use asks for your own Telegram API ID/hash (keep them secret), phone login confirmation, and possibly your Telegram 2-step password. This previews Telegram ZIP filename and size; it **does not download the archive** or inspect its contents yet.

## Step 4: Import the ZIP from Telegram automatically

After verifying rights to distribute **every book** inside the archive:

```powershell
python -X utf8 IMPORT_TELEGRAM_ZIPS_V11921.py --apply --link "https://t.me/c/1234567890/55" --language "Sinhala" --category "Education" --author "Unknown" --rights permission --rights-note "Verified redistribution permission for all included editions"
```

The program asks you to type `IMPORT` after showing the source and bot. It will:

1. Start `/mediabulk` and set the shared metadata, as your existing bot admin account.
2. Download the ZIP **to your Windows local application data folder**, reusing the same download on resume.
3. Preview safe book entries, extract one at a time locally, and upload `.pdf`, `.epub`, `.docx`, and `.txt` files through Telegram.
4. Request `/mediabulkstatus`. Check **Published** versus **Failed**, then send `/mediabulkdone` manually.

For multiple ZIP messages you can repeat `--link` or create a UTF-8 text file containing one message link per line and pass `--links-file "C:\Path\to\links.txt"`. If the archives contain mixed languages/categories, use separate runs with accurate metadata. Don't claim `permission` unless authorization is verified.

## Resume, disk usage and security

- The downloaded ZIP is saved at `%LOCALAPPDATA%\StudentAssistantBot\zip-bulk-import\telegram-zips` and kept so rerunning the same link can resume a partial upload. Clean it up manually after confirming publication; deleting it also removes the reusable download and a subsequent run must download again.
- A local checkpoint indicates **successfully sent to Telegram, not necessarily published** in the bot database; always review `/mediabulkstatus`.
- If the bot (Render) restarts, its in-memory Smart Bulk session may be lost. Restart a bulk session and check the published books before retrying.
- ZIP path traversal, symlinks, encryption, high decompression ratios, disk-space shortages and over-4 GB individual members are rejected or skipped by the unchanged local safety checks.
- Do not commit session credentials or checkpoint files to GitHub. Your Telegram API hash, phone login code and password should never be shared in chat.
- This does **not** remove Telegram's 20 MB public Bot API download limit, change the bot's existing 20 MB ZIP feature, or allow transfers from protected/inaccessible channels.
