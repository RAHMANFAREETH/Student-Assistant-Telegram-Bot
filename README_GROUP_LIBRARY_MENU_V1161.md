# V11.6.1 — Fix Book Library Menu in Telegram Groups

This is a **small compatibility patch** for your existing V11.6 Student Assistant Telegram Bot. It does **not** replace V11.1–V11.6, V8–V10, Gemini, verified-adult access, the private book-storage channel, or your Supabase catalog.

## Why this fix is needed

In V11.5, the **📚 Book Library** reply-keyboard label is classified as personal navigation and intercepted before V11.6 runs. Meanwhile, V11.6 only handles group `/book TITLE` and `/booklatest`, not a group-specific Book Library menu. Therefore, the full menu remains visible in **private chats** but pressing the label in a **group** does not open the desired menu.

## Correct behavior

| Where | Outcome |
|---|---|
| Telegram group: `/bookmenu` or `/library` | Public Book Library mini menu appears, with **Search a Book**, **Latest 5 Books**, and **Full Library in Private Bot**. |
| Telegram group: `📚 Book Library` | Same mini menu, provided the bot receives the group message. |
| Group: Search button | Closes the requesting user's menu and explains to type `/book TITLE` (or matching title if free-text search is enabled). |
| Group: Latest 5 button | Closes the requesting user's menu and posts the newest five books as Telegram buttons. |
| Group: `/book small` or `small` | Existing public group book results remain in the group; each book URL opens the private bot for PDF delivery. |
| Group: owner-only mini menu | Other users cannot operate that person's temporary menu. Every user may request their own public book by URL. |
| Group: after ~5 minutes | Unused mini menu and temporary book results expire using your existing V11.5 deletion queue (best effort). |
| Private bot | Full Library, personal books/favorites, Gemini, PDF, quizzes, adult verification, all other features preserved. |

For the menu, pressing an inline callback action deletes the old menu immediately when Telegram permits. Clicking a **URL book button** does *not* trigger a callback: the public result is deleted on the scheduled timer, not on click.

## 1. Local installation

Extract the four files in this ZIP into `C:\Users\Pros\Desktop\StudentAssistantBot`.

```powershell
python INSTALL_GROUP_LIBRARY_MENU_V1161.py --check
python -X utf8 -m unittest TEST_GROUP_LIBRARY_MENU_V1161 -q
```

The `--check` preview should add *only one 3-line registration block* to `main.py`, **before** the V11.5 `install_group_ui_guard(bot)` line. If correct:

```powershell
python INSTALL_GROUP_LIBRARY_MENU_V1161.py --apply
python INSTALL_GROUP_LIBRARY_MENU_V1161.py --check
python -m py_compile group_library_menu_v1161.py main.py
```

## 2. Full regression tests

```powershell
$oldPrivacy = $env:BOOK_LIBRARY_PRIVATE_GROUP_RESULTS
try {
    $env:BOOK_LIBRARY_PRIVATE_GROUP_RESULTS = 'false'
    python -X utf8 -m unittest TEST_BOOK_LIBRARY TEST_BOOK_PUBLIC_LATEST5 TEST_BOOK_LIBRARY_V112 TEST_BOOK_LIBRARY_V113 TEST_BOOK_LIBRARY_PRIVACY_V114 TEST_GROUP_UI_V115 TEST_GROUP_BOOK_ONLY_V116 TEST_GROUP_LIBRARY_MENU_V1161 -q
}
finally {
    if ($null -eq $oldPrivacy) {
        Remove-Item Env:BOOK_LIBRARY_PRIVATE_GROUP_RESULTS -ErrorAction SilentlyContinue
    } else {
        $env:BOOK_LIBRARY_PRIVATE_GROUP_RESULTS = $oldPrivacy
    }
}
```

Expected: **254 tests, OK** (in the bundled integration copy; verify in your local repository). A warning about Supabase during a mocked test need not indicate a production failure.

## 3. Commit ONLY V11.6.1 files

```powershell
git add -- group_library_menu_v1161.py INSTALL_GROUP_LIBRARY_MENU_V1161.py TEST_GROUP_LIBRARY_MENU_V1161.py README_GROUP_LIBRARY_MENU_V1161.md
git add -p -- main.py
git diff --cached --check
git diff --cached --name-only
```

Exactly **five files** should be staged: four new plus `main.py`. The only `main.py` change is V11.6.1 registration ahead of V11.5. Never stage local backups or secrets. Then:

```powershell
git commit -m "V11.6.1: Show Book Library menu only in groups"
git push origin main
```

## 4. Render settings

First deploy the new code with `GROUP_LIBRARY_MENU_V1161_ENABLED=false`.
After Render is Live and V11.5 group deletion is working, set:

```dotenv
GROUP_LIBRARY_MENU_V1161_ENABLED=true
GROUP_BOOK_ONLY_V116_ENABLED=true
GROUP_UI_PROTECTION_ENABLED=true
GROUP_UI_PRIVATE_NAVIGATION=true
GROUP_UI_TIMER_ENABLED=true
GROUP_UI_DELETE_AFTER_SECONDS=300
GROUP_UI_DELETE_NAV_INPUT=true
BOOK_LIBRARY_ENABLED=true
BOOK_LIBRARY_V112_ENABLED=true
BOOK_LIBRARY_V113_ENABLED=true
BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT=false
BOOK_LIBRARY_ALLOW_ALL_GROUPS=true
BOOK_LIBRARY_AUTO_GROUP_SEARCH=true
BOOK_LIBRARY_PRIVATE_GROUP_RESULTS=false
```

Keep all existing private-channel IDs, Gemini settings, `/start` deep-link delivery handler, and adult-verification settings unchanged. **No new SQL migration** is needed: this uses the V11.5 deletion queue. Keep `BOOK_LIBRARY_NOTIFIER_ENABLED` at whichever setting already works for your V11.3 notifier.

## 5. Test in the actual Telegram group

1. Check bot is a member and has **Delete Messages** permission (needed to delete the group members' commands; it can usually delete its own group messages).
2. Send `/bookmenu` in the group. The small group Book Library menu should appear. If `/bookmenu` works but sending `📚 Book Library` doesn't, the bot is not receiving ordinary group messages. Review its group Privacy Mode in BotFather, or make the bot a group admin. Group privacy settings may require re-adding the bot.
3. Tap **Search a Book**: the group's small menu should disappear; type `/book Small Habits` in the group.
4. Matching book results should be posted **in the group**. Tap a book link: Telegram opens the **private bot chat** and sends the PDF (user may need to press Start first).
5. Open `/bookmenu` again. Tap **Latest 5 Books**: the group should get the latest five items, and the old temporary menu should disappear.
6. Use two accounts: User B should be unable to select User A's temporary **menu** buttons, but may independently request the same **public book** via its URL.
7. Leave a result untouched for five minutes. The V11.5 timer should remove the bot's public result when the worker is running and deletion is allowed.
8. Send `/v10`, `/v9` or `📦 More Tools` in the group: these personal functions should *not* execute there. They remain available in the private bot.

## Notes and rollback

- URL clicks do not produce a callback. The results are timer-deleted, not deleted on URL click.
- Ordinary text like `small` requires the bot to receive non-command group messages. When Telegram Privacy Mode is enabled for a non-admin bot, it may only see commands or replies rather than arbitrary text. Prefer `/book small` as a reliable fallback.
- When the bot restarts, temporary owner-only menu callbacks stored in local memory expire; users can send `/bookmenu` again. No personal data is exposed.
- Telegram's `deleteMessage` has a 48-hour maximum age and permission requirements, but the configured timer is five minutes.
- **Rollback:** set `GROUP_LIBRARY_MENU_V1161_ENABLED=false` and Save and Deploy. Do not remove any existing Book Library modules or database tables.
