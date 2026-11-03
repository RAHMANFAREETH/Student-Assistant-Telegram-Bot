# V11.9.2 — Large ZIP Book Importer (local Windows tool)

## Why this exists

The Telegram **public Bot API** cannot download files larger than 20 MB with `getFile`. Your Student Assistant Bot's old ZIP importer must download/unpack ZIPs on Render. Removing its 20 MB check alone will **not** work. However, forwarding or sending individual files already on Telegram can bypass the bot's 20 MB download limit.

This is **not a production bot upgrade**. It is a stand-alone Windows tool that can read a local ZIP archive of **any total size**, extract one book at a time on your PC, send each as a document via your own authorized Telegram account using Telethon, and let your existing `/mediabulk` handler save the file using Telegram-to-Telegram copying.

- No fixed total ZIP archive cap.
- No 100-document cap in this local tool; requires deployed V11.8.8.4+ unlimited Smart Bulk.
- No fixed two-hour session for the deployed Smart Bulk, but Render restarts still clear sessions.
- Does **not** send the ZIP itself to the bot; sends extracted PDFs/EPUBs/DOCXs/TXTs individually.
- Keeps ZIP decompression **on your Windows computer**, not Render. Uses temporary disk storage for *one file at a time*.
- The tool never changes your bot, Supabase, Render configuration or access controls.
- File-by-file upload limits from Telegram user accounts remain: generally 2 GB for regular accounts, up to 4 GB for Premium. A single ZIP member >4 GB is skipped; actual Telegram server errors may apply at smaller sizes.
- File types: `.pdf`, `.epub`, `.docx`, `.txt`. Nested ZIPs are not imported.
- Safety: blocks path traversal, symlinks, encrypted ZIP members, high decompression-ratio archives, very large single members, and operations without sufficient free disk space. These are necessary safety rules, **not a fixed ZIP archive size cap**.
- Titles are inferred from the **original names of the files inside the ZIP**. Corrupt or unhelpful names need manual metadata correction later.
- It requires explicit, truthful rights confirmation before sending documents.

## Install

1. Extract this package to `C:\Users\Pros\Desktop\StudentAssistantBot` (same folder as your bot) or a separate local folder.
2. Install the dependency in your Windows terminal:

```powershell
python -m pip install "telethon>=1.42,<2"
```

3. Make sure `@Student_Sl_Assistant_bot` is live and `/mediabulk` works in private chat, using your **authorized administrator** Telegram account.
4. Obtain Telegram `api_id` and `api_hash` from `https://my.telegram.org/apps`. On the first real import, enter them when prompted. The script will then prompt for your phone/login code and, if necessary, two-step verification. Keep these **private**. Do not share your API hash, login code or `*.session` files; do not commit them to GitHub.

## Preview your ZIP archive safely

Change the file path to your own downloaded ZIP:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 IMPORT_LOCAL_BOOK_ZIPS_V1192.py --dry-run --source "D:\Books\SinhalaBooks.zip"
```

You may point `--source` to a folder containing several `.zip` archives to process them in filename order:

```powershell
python -X utf8 IMPORT_LOCAL_BOOK_ZIPS_V1192.py --dry-run --source "D:\Books\ZIP_Collections"
```

Dry-run is offline: it does not need credentials or modify your Telegram bot.

## Start importing

Use the same file path and choose *accurate* shared metadata for each ZIP (mixed language/categories may need separate runs). For example, **only if you genuinely have permission to distribute all files**:

```powershell
python -X utf8 IMPORT_LOCAL_BOOK_ZIPS_V1192.py --apply --source "D:\Books\SinhalaBooks.zip" --bot "@Student_Sl_Assistant_bot" --language "Sinhala" --category "Education" --author "Unknown" --rights permission --rights-note "Verified distribution permission for every included edition"
```

For genuine public-domain works, use `--rights public_domain` and an accurate rights explanation identifying the source and edition. Don't assume an entire ZIP is public domain just because it is shared on Telegram.

The tool will:

1. Ask you to confirm destination bot and rights with `IMPORT`.
2. Start `/mediabulk` privately as your Telegram **user** account.
3. Set shared metadata using `/mediabulkset`.
4. Extract and upload each supported book individually (not the ZIP).
5. Save a local checkpoint after Telegram confirms sending each book.
6. Request `/mediabulkstatus` when done.

**Review** the bot's Published / Failed counts before manually sending `/mediabulkdone`. The tool **does not** close the session automatically.

## Resume after interruption

Rerun the same `--apply` command. The local checkpoint identifies the last file successfully **sent to Telegram**, not proof that your bot **published** it. Check `/mediabulkstatus` and the library before continuing. You can restart the entire archive using `--reset-checkpoint`, but doing so may re-send duplicates.

A ZIP archive that changes size or modification time generates a new checkpoint. Files are never written inside the bot project unless you choose to put the ZIP source there; Telegram login sessions and checkpoints live in `%LOCALAPPDATA%\StudentAssistantBot\zip-bulk-import`.

## Tests (safe offline)

```powershell
python -X utf8 -m unittest TEST_IMPORT_LOCAL_BOOK_ZIPS_V1192 -q
```

Test coverage: archive discovery, Tamil/Arabic Unicode names, path traversal, symlink/encrypted member rejection, ZIP-bomb ratio, >4 GB member rejection, disk space check, one-by-one extraction, local checkpoints, resumption, private rights confirmation, and over 100 documents processed through the fake Telegram upload client.

## Keep these safety and deployment boundaries

- **Do not** remove the server's `getFile` 20 MB download constraint or its ZIP guard by setting an environment variable. The Bot API will still reject larger downloads.
- A local Bot API server is an alternative infrastructure project that can download larger files, but it requires a suitable host with sufficient memory/disk, hardened ZIP extraction, and a different Telegram API configuration. It is not required for this local importer.
- Avoid importing files you cannot legally redistribute. The bot's regular age/access rules continue to apply.
- If a ZIP contains malicious or corrupted files, skip and inspect locally; do not bypass the ZIP safety checks.
- Frequent large uploads may hit Telegram rate limits. The script stops at a rate limit and can be resumed; default delay is 2 seconds between files.
- If Render restarts during a long import, the Smart Bulk session may close. Restart a new session in your bot and resume locally only after checking failed/unsaved files.
