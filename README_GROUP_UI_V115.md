# Student Assistant Bot V11.5 — Group Menu Privacy & Five-Minute Cleanup

**Additive release.** Does not overwrite Book Library V11.1–V11.4, Gemini, verified-adult access, PDF tools, or group quiz battles. The only existing file modified by the installer is `main.py`.

## What changes

- In group chats, personal menu choices such as **📦 More Tools**, **↩️ All Categories**, **/start**, **/v8**, **/v9**, and **/study** now produce a private-bot link instead of a shared personal-workflow menu. The user's group selection is deleted on click when the bot has Delete Messages permission.
- An old group reply keyboard is closed **selectively** for the user who selected an option, where supported by the Telegram client.
- Public book results (`/book TITLE`, `/booklatest`) can remain in the group with URL buttons. Tapping a book opens the bot's private chat via the existing `?start=book_UUID` deep link, which sends the PDF; no file is posted to the group.
- Book-result messages, short navigation notices, and eligible group `/book` commands are queued for deletion after **300 seconds**. A Supabase queue survives Render restarts; a background worker checks about every 10 seconds while your service is running.
- Existing **private** Book Library callback menus retain V11.4's immediate deletion on selection (`BOOK_LIBRARY_AUTODELETE_MENU=true`). Existing personal Book Library callback menus in groups are rejected and removed if clicked. Public URL links are different: **Telegram does not inform the bot when a URL button was tapped**. They therefore disappear after five minutes, not immediately on click.
- Existing **group quiz** keyboards and callback buttons are intentionally excluded from the group-menu interception.

## Installation (Windows PowerShell)

1. Unzip these 5 files into `C:\Users\Pros\Desktop\StudentAssistantBot`.
2. Run `python INSTALL_GROUP_UI_V115.py --check` and review the diff. It should only add one block to `main.py` after `bot = telebot.TeleBot(...)` and before the Flask `app = ...` line.
3. Run `python -X utf8 -m unittest TEST_GROUP_UI_V115 -q` (22 focused tests).
4. Run `python INSTALL_GROUP_UI_V115.py --apply`, then `python INSTALL_GROUP_UI_V115.py --check` and `python -m py_compile main.py group_ui_v115.py`.
5. Run the full library regression suite in PowerShell:

```powershell
$oldPrivacy = $env:BOOK_LIBRARY_PRIVATE_GROUP_RESULTS
try {
    $env:BOOK_LIBRARY_PRIVATE_GROUP_RESULTS = 'false'
    python -X utf8 -m unittest TEST_BOOK_LIBRARY TEST_BOOK_PUBLIC_LATEST5 TEST_BOOK_LIBRARY_V112 TEST_BOOK_LIBRARY_V113 TEST_BOOK_LIBRARY_PRIVACY_V114 TEST_GROUP_UI_V115 -q
}
finally {
    if ($null -eq $oldPrivacy) {
        Remove-Item Env:BOOK_LIBRARY_PRIVATE_GROUP_RESULTS -ErrorAction SilentlyContinue
    } else { $env:BOOK_LIBRARY_PRIVATE_GROUP_RESULTS = $oldPrivacy }
}
```

**Expected:** 208 tests pass (186 existing + 22 new). Existing tests are run in the legacy public-group mode intentionally; your live Render settings are unaffected.

## Supabase migration

Back up your existing Supabase project, then review and execute the complete `SQL_GROUP_UI_V115.sql` in Supabase SQL Editor. This creates a separate queue table and two service-role-only SQL functions. It does **not** alter book records or personal study data.

## Safe Render rollout

First deploy with:

```dotenv
GROUP_UI_PROTECTION_ENABLED=false
GROUP_UI_TIMER_ENABLED=false
```

After the SQL migration and new GitHub commit are deployed and Render is **Live**, enable:

```dotenv
GROUP_UI_PROTECTION_ENABLED=true
GROUP_UI_PRIVATE_NAVIGATION=true
GROUP_UI_CLOSE_REPLY_KEYBOARD=true
GROUP_UI_DELETE_NAV_INPUT=true
GROUP_UI_TIMER_ENABLED=true
GROUP_UI_DELETE_AFTER_SECONDS=300
GROUP_UI_EXPIRE_BOOK_COMMANDS=true
GROUP_UI_AUTODELETE_CALLBACK=true

BOOK_LIBRARY_ENABLED=true
BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT=false
BOOK_LIBRARY_ALLOW_ALL_GROUPS=true
BOOK_LIBRARY_PRIVATE_GROUP_RESULTS=false
BOOK_LIBRARY_AUTODELETE_MENU=true
BOOK_LIBRARY_BOT_USERNAME=YOUR_REAL_BOT_USERNAME
```

`BOOK_LIBRARY_PRIVATE_GROUP_RESULTS=false` is an **existing V11.4 option**, not a code reversal: `false` deliberately displays public book-result URL links in groups so anyone can choose a public book. Set it back to `true` if you prefer group searches to display results only in the requester's private chat. Both modes continue to work.

Keep your existing storage channel IDs, review channel, V11.2/V11.3 flags, Gemini settings, and adult-verification mode unchanged.

## Git staging (no backup folders)

```powershell
git add -- group_ui_v115.py INSTALL_GROUP_UI_V115.py TEST_GROUP_UI_V115.py SQL_GROUP_UI_V115.sql README_GROUP_UI_V115.md
git add -p -- main.py
git diff --cached --check
git diff --cached --name-only
```

Review **exactly 6 intended files** (5 new + `main.py`). If correct:

```powershell
git commit -m "V11.5: Isolate group menus and expire public book links"
git push origin main
```

## Live test with two users

1. Add the bot as a group administrator with **Delete Messages** permission if you want it to remove users' `/book` commands and menu choices. Bots can delete their own eligible group messages without this permission, subject to Telegram limitations.
2. User A taps **📦 More Tools** in the group. Instead of a shared menu, a link to the private bot appears; User A's selected message is deleted where permitted. Other users' group sessions are untouched.
3. Send `/book Small Habits` in the group. Results contain public book-link URL buttons (with `BOOK_LIBRARY_PRIVATE_GROUP_RESULTS=false`).
4. Tap a book link from User A. Telegram opens the bot privately; if the user has not started it before, they may need to tap **Start**. The existing Book Library code copies the PDF from the private storage channel to User A's DM.
5. From User B, open the same public book: User B receives their own private copy, not User A's data.
6. Confirm the public group result and `/book` command disappear after roughly five minutes. Navigation notices also expire. Callback-based **private** menus disappear on authorized selection, where Telegram permits.
7. Confirm `/booklatest`, `/adult_admin` privately, `/v10`, `/v101` and an existing group quiz still work.

## Telegram and Render limitations

- **URL buttons do not generate callback queries.** Instant deletion on tapping a book link is not guaranteed; the supported fallback is time-based cleanup.
- Five-minute deletion is **best effort**, checked around every ten seconds. If Render is suspended, deletion will run after service resumes. Telegram generally limits message deletion to 48 hours after sending.
- Already-existing historical messages are not retroactively queued for deletion.
- User command deletion requires the group administrator's Telegram permission. Failed attempts are retried a limited number of times.
- The patch does not rework all historical feature-specific state dictionaries. It blocks old navigation from starting personal workflows in group chats and preserves existing group quiz behavior. A separate audit is still appropriate for any legacy group workflow that holds personal information.

Official Telegram documentation: https://core.telegram.org/bots/api (deleteMessage, ReplyKeyboardRemove, InlineKeyboardButton, callback queries).
