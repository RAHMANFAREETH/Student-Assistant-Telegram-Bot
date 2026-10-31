# V11.6 — Book Library Only in Groups, All Other Tools Private

**Compatible add-on for your existing V11.5 Student Assistant Telegram Bot.**
This does **not** replace V11.1–V11.5, V8/V9/V10, adult verification, Gemini, or the Mini App. The installer **only adds an early registration block to `main.py`**. It requires `group_ui_v115.py` and the existing Book Library modules.

## Exact expected behavior

| Where | What works |
|---|---|
| Telegram group | `/book TITLE`, `/books`, `/booklatest`, `/latestbooks`, `/booksmart TITLE`, `/bookbrowse TITLE`, or a matching plain book title when enabled |
| Telegram group | The bot shows **public** matching book URL buttons in the group, with a notice that the result is scheduled to expire after 5 minutes |
| Telegram group | Tapping a book URL opens the **same bot in private**. Telegram may ask the user to press **Start**, then the bot copies the PDF from your existing private channel |
| Telegram group | Other commands (`/v8`, `/v9`, AI, PDF, old navigation, quizzes, admin, private favorites) are prevented from reaching legacy handlers. A brief private-chat redirect may appear, then expire |
| Telegram group | Normal conversation that does **not** match a book is left alone, without a bot reply; private data is never posted in public results |
| Private bot chat | All previously installed features and personal Book Library tools keep their existing handlers |

**Important:** Group quiz *operations* are intentionally blocked when this mode is on, because the request is **Book Library only in groups**. The code and records are not deleted. Turn `GROUP_BOOK_ONLY_V116_ENABLED=false` to restore your previous group behavior.

The public group result is not owned by one user; any member can request **their own** publicly listed PDF. This is expected. Personal favorites, reading progress, and admin commands remain private.

## Step 1 — Safe installation (PowerShell)

Extract the four supplied files into `C:\Users\Pros\Desktop\StudentAssistantBot`.

```powershell
python INSTALL_GROUP_BOOK_ONLY_V116.py --check
python -X utf8 -m unittest TEST_GROUP_BOOK_ONLY_V116 -q
```

Review the diff; it should add only three V11.6 registration lines after `install_group_ui_guard(bot)` in `main.py`. The installer uses a unique anchor, makes an automatic backup, and stops on unexpected layouts.

```powershell
python INSTALL_GROUP_BOOK_ONLY_V116.py --apply
python INSTALL_GROUP_BOOK_ONLY_V116.py --check
python -m py_compile main.py group_ui_v115.py group_books_only_v116.py
```

`--check` should now say "already integrated".

## Step 2 — Full library regression tests

Run with explicit UTF-8 (Windows Python 3.14 often defaults to `cp1252`):

```powershell
$oldPrivacy = $env:BOOK_LIBRARY_PRIVATE_GROUP_RESULTS
try {
    $env:BOOK_LIBRARY_PRIVATE_GROUP_RESULTS = 'false'
    python -X utf8 -m unittest TEST_BOOK_LIBRARY TEST_BOOK_PUBLIC_LATEST5 TEST_BOOK_LIBRARY_V112 TEST_BOOK_LIBRARY_V113 TEST_BOOK_LIBRARY_PRIVACY_V114 TEST_GROUP_UI_V115 TEST_GROUP_BOOK_ONLY_V116 -q
} finally {
    if ($null -eq $oldPrivacy) {
        Remove-Item Env:BOOK_LIBRARY_PRIVATE_GROUP_RESULTS -ErrorAction SilentlyContinue
    } else { $env:BOOK_LIBRARY_PRIVATE_GROUP_RESULTS = $oldPrivacy }
}
```

**Expected in the packaged compatibility snapshot:** 231 tests passed (208 prior + 23 V11.6). Your local results are authoritative.

## Step 3 — Supabase

**No new SQL migration is required.** Retain your previous `SQL_GROUP_UI_V115.sql` queue and existing Book Library migrations. Verify that the V11.5 group cleanup RPCs work before relying on scheduled deletion. The previous process-local fallback is not reliable across restarts.

## Step 4 — Git, without backup folders

```powershell
git add -- group_books_only_v116.py INSTALL_GROUP_BOOK_ONLY_V116.py TEST_GROUP_BOOK_ONLY_V116.py README_GROUP_BOOK_ONLY_V116.md
git add -p -- main.py
git diff --cached --check
git diff --cached --name-only
```

There should be **exactly five intended files** (four new + `main.py`). Stage only the V11.6 block in `main.py`, not unrelated changes.

```powershell
git commit -m "V11.6: Restrict groups to Book Library and expire public results"
git push origin main
```

## Step 5 — Render environment

Set this initially while deploying the new commit:

```dotenv
GROUP_BOOK_ONLY_V116_ENABLED=false
```

After Render is Live and the earlier V11.5 SQL queue is confirmed, set:

```dotenv
GROUP_BOOK_ONLY_V116_ENABLED=true
GROUP_UI_PROTECTION_ENABLED=true
GROUP_UI_PRIVATE_NAVIGATION=true
GROUP_UI_CLOSE_REPLY_KEYBOARD=true
GROUP_UI_DELETE_NAV_INPUT=true
GROUP_UI_TIMER_ENABLED=true
GROUP_UI_DELETE_AFTER_SECONDS=300
GROUP_UI_EXPIRE_BOOK_COMMANDS=true
GROUP_UI_AUTODELETE_CALLBACK=true

BOOK_LIBRARY_ENABLED=true
BOOK_LIBRARY_V112_ENABLED=true
BOOK_LIBRARY_V113_ENABLED=true
BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT=false
BOOK_LIBRARY_ALLOW_ALL_GROUPS=true
BOOK_LIBRARY_AUTO_GROUP_SEARCH=true
BOOK_LIBRARY_PRIVATE_GROUP_RESULTS=false
BOOK_LIBRARY_AUTODELETE_MENU=true
```

Keep unchanged your existing `BOOK_LIBRARY_CHANNEL_ID`, `BOOK_LIBRARY_REVIEW_CHANNEL_ID`, `BOOK_LIBRARY_BOT_USERNAME`, administrator IDs, Gemini key, and `STUDY_ACCESS_MODE=verified_adults` (for adult-only AI tools).

If you want only one or two approved groups, set `BOOK_LIBRARY_ALLOW_ALL_GROUPS=false` and put the approved group IDs in `BOOK_LIBRARY_GROUP_IDS`.

## Step 6 — Telegram group permissions and tests

Add the bot to the group as administrator with **Delete Messages** if you want its cleanup to delete users' `/book` commands. Telegram bots can generally delete their own recent group messages; deleting others' messages requires appropriate permissions. Telegram's normal `deleteMessage` limit is 48 hours, much longer than the requested 5 minutes.

For plain titles such as `small` (not `/book small`), the bot must receive ordinary group messages: use admin status with suitable access or review BotFather `/setprivacy`. Turning group privacy off means the bot sees ordinary group messages; announce this to members and test in a small group first. Commands `/book small` and `/booklatest` work without turning off group privacy.

From two test accounts, after both start the bot privately:

1. In a group, User A types `/book Small Habits`. It displays matching book URL buttons **in the group**, plus the 5-minute notice.
2. User B clicks the same public book: **User B's** own private bot chat receives the PDF. Group users do not receive User A's private data.
3. User A types `small` in the group. It searches only when `BOOK_LIBRARY_AUTO_GROUP_SEARCH=true` and an actual matching book exists.
4. Type `/booklatest`: the newest five public books appear in the group.
5. Wait about five minutes while the Render worker is running. The group result (and the command if allowed) should disappear. Past messages created before V11.5 aren't retroactively cleaned.
6. Type `/v10`, `/v9`, `/pdfmerge`, `/bookfavs`, or press **📦 More Tools** in the group. No personal tool should execute there. The short redirect may be posted; it too expires.
7. Open the bot privately and use `/v10`, `/bookfavs`, `/adult_admin` (admin account), and the other previous tools. They should continue working.

**Telegram limitation:** URL button clicks do not create bot callback updates, so a public result cannot be reliably deleted on click. It is deleted **on the five-minute schedule**, which is best-effort while the Render worker is active. Private inline menus can still be removed immediately after valid callback selections.

## Emergency rollback

Change only:

```dotenv
GROUP_BOOK_ONLY_V116_ENABLED=false
```

Save/deploy. The previous V11.5 handlers resume their earlier behavior without removing code or migrating data. Do not delete the V11.5 deletion queue.
