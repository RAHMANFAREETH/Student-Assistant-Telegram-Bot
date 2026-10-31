# Student Assistant Telegram Bot — V11.8 Manage Library Files

This is an **additive V11.8 patch** for a project that already has V11.7 installed. It does **not** overwrite the older PDF library, remove the media library, alter `main.py`, or change the study tools or group search behavior.

## What this patch does

**Private admin workflow:** `More Tools → 🛡️ Library Admin Panel → 📁 Manage Library Files`.

An authorized admin can:

- Search both existing PDF books (`book_library_items`) and newer media (`library_media_v117`) by title, including hidden items; locate any record by exact UUID.
- Preview the original PDF/image/audio/video/other stored file privately.
- Rename the **catalog title** without changing the original Telegram filename.
- Hide and restore both legacy PDFs and new media without deleting storage.
- Request permanent deletion, with a separate short-lived, one-time confirmation.
- Record changes in the existing `library_media_v117_audit` table (best effort; inspect Render logs if audit insertion fails).

The patch uses your **existing V11.7 Supabase migration**. No new SQL or Render service is required.

### Important Telegram limitation

Telegram's Bot API `deleteMessage` ordinarily only deletes messages **under 48 hours old**. It is common for old storage-channel PDFs/images to be older than that.

When Delete Permanently is confirmed, V11.8:

1. Checks that the channel message is not referenced by another catalog item.
2. Hides the item so users no longer receive it through library searches.
3. Asks Telegram to delete the original storage-channel message.
4. Removes the Supabase catalog record **only after Telegram confirms deletion**.

If Telegram cannot delete the message, the catalog remains **hidden**, and the bot provides the specific private-channel chat ID and message ID. An authorized admin can delete the storage-channel post **manually in Telegram**, open the hidden item again, and explicitly choose **“I removed channel file — Purge catalog.”** This is an admin attestation: the bot cannot independently verify that manual deletion happened. Do not use that option unless the channel post is gone. Past copies already delivered to users are not recoverable by this process.

Permanent deletion cascades through dependent Supabase favorites, reading progress and downloads when their tables' foreign keys have `ON DELETE CASCADE`. **Back up your database before enabling deletion.**

## Step-by-step installation (Windows PowerShell)

1. Save and extract `Student_Assistant_Bot_V11_8_Manage_Library_Files.zip` into your current project directory. It contains four new files and does not include your private credentials.

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python INSTALL_LIBRARY_MANAGE_V118.py --check
python -X utf8 -m unittest TEST_LIBRARY_MANAGE_V118 -q
```

`--check` must show a small diff against **only** `library_media_v117_bot.py`. New tests run offline without a Telegram bot connection or Supabase access.

2. Apply the patch (the installer automatically backs up the old file):

```powershell
python INSTALL_LIBRARY_MANAGE_V118.py --apply
python INSTALL_LIBRARY_MANAGE_V118.py --check
python -m py_compile library_media_v117_bot.py library_manage_v118.py
```

3. Run your complete existing Book Library regression suite:

```powershell
python -X utf8 -m unittest TEST_BOOK_LIBRARY TEST_BOOK_PUBLIC_LATEST5 TEST_BOOK_LIBRARY_V112 TEST_BOOK_LIBRARY_V113 TEST_BOOK_LIBRARY_PRIVACY_V114 TEST_GROUP_UI_V115 TEST_GROUP_BOOK_ONLY_V116 TEST_GROUP_LIBRARY_MENU_V1161 TEST_LIBRARY_MEDIA_V117 TEST_LIBRARY_MANAGE_V118 -q
```

**Prepared package:** 338 offline tests passed. Your actual project may contain additional local changes, so check the result on your machine before deploying.

4. Stage ONLY the new files and the intended integration hunk:

```powershell
git add -- library_manage_v118.py INSTALL_LIBRARY_MANAGE_V118.py TEST_LIBRARY_MANAGE_V118.py README_LIBRARY_MANAGE_V118.md
git add -p -- library_media_v117_bot.py
git diff --cached --check
git diff --cached --name-only
```

Make sure **exactly five files** are listed and that no unrelated code is staged. If correct:

```powershell
git commit -m "V11.8: Add unified library file management and safe deletion"
git push origin main
```

5. **Render rollout:** deploy first with `LIBRARY_MANAGE_V118_ENABLED=false`. Once the new code is Live, confirm V11.7 is enabled and your current Book Library works. Then set:

```dotenv
LIBRARY_MEDIA_V117_ENABLED=true
LIBRARY_MANAGE_V118_ENABLED=true
```

Keep all existing Book Library, group, storage-channel, administrator, Gemini, Render, and verification settings intact. **Do not create a new Supabase table** for this patch.

6. Open the bot privately using an existing authorized Book Library administrator account:

```
/libraryadmin
```

Tap **📁 Manage Library Files**, or send:

```
/librarymanage
/librarymanage Arabic
/librarymanage b:11111111-2222-4333-8444-555555555555
```

The UUID example is illustrative; use your actual ID. Select any result to inspect it. The panel supplies a title-rename command you can copy and edit:

```
/librarysettitle b:YOUR_BOOK_UUID | Arabic Grammar — Volume One
/librarysettitle m:YOUR_MEDIA_UUID | Arabic Grammar Diagram
```

- `b:` = original book/PDF catalog.
- `m:` = V11.7 media catalog (including newer PDFs and images).

### Live acceptance checklist

- Open `/libraryadmin` in private chat. See **📁 Manage Library Files**.
- Search a known legacy PDF and an image from the V11.7 catalog.
- Preview each original file privately.
- Rename a test item; verify its searchable title changes, not the Telegram document filename.
- Hide a test item; verify the group search stops returning it and existing private deep links fail to deliver it.
- Restore that item; verify it becomes searchable again.
- Test permanent deletion **only on a disposable file** and verify its catalog record is gone.
- For an older disposable channel message, verify a Telegram deletion failure leaves the item hidden and requires manual channel deletion before the final catalog purge.
- Check that group Book Library search and five-minute results cleanup still work.
- Check Render logs for `Admin action succeeded but audit insert failed` or unexpected database errors.

### Rollback

Set `LIBRARY_MANAGE_V118_ENABLED=false` in Render to disable the new management actions without affecting the rest of V11.7. The new menu button is also hidden when the flag is off. The installer's `V118_MANAGEMENT_BACKUP_*` directory contains the original `library_media_v117_bot.py` if you need to revert the integration. A rollback does **not** undo intentional file deletions.

### Security notes

- Only authorized library admins in their own **private** bot chat can invoke actions or callback buttons.
- Every mutation re-checks admin authorization and performs a server-side record lookup.
- Confirmation tokens expire after three minutes and are consumed once. Tokens are local to a running bot process; if Render restarts, a pending confirmation simply expires.
- File storage-channel IDs are shown only to authorized administrators.
- Uploaded community files that are still **pending review** are not managed here; use your existing V11.7 moderation panel.
- Both legacy PDF and media libraries stay publicly searchable in groups **only** when items are active/approved. All admin actions remain private.
