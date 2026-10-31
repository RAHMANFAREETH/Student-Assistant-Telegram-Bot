# V11.1 Book Library — Public Access & Latest Five Patch

For the **existing Student Assistant Telegram Bot**, one Render service and Supabase project. This patch modifies **only** `book_library_bot.py` and `book_library_store.py`. It does not change Gemini, V8–V11 tools, administrator permissions, the storage channel, or the database schema.

## Changes

1. **Everyone can use the library in private chat**, including students who are not verified adults. Set `BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT=false` in Render; the patch also makes this the library's default if the setting is omitted. Adult verification for other tools is unchanged.
2. **Users can search in any group containing the bot** if you explicitly set `BOOK_LIBRARY_ALLOW_ALL_GROUPS=true` (new setting). Otherwise, `BOOK_LIBRARY_GROUP_IDS` remains the allowlist.
3. **Latest Books displays at most five items**, ordered by `added_at` descending, excluding inactive books. These are the books *already uploaded* to `book_library_items`; you do **not** have to reupload them. As you upload new books, the newest five replace the older ones in the list.
4. New commands `/booklatest` and `/latestbooks` work in private chat or permitted groups, with links for private delivery. In groups, `/books` without a title also shows the latest five.
5. Automatic search for regular group messages (for example, typing just `Ihya`) **stays disabled by default**. Commands `/book Ihya` and `/booklatest` work with Telegram group privacy mode on. If you choose to enable automatic free-text search, turn on `BOOK_LIBRARY_AUTO_GROUP_SEARCH=true`, review Telegram privacy implications, and use @BotFather /setprivacy to disable privacy mode. This does not change the Latest Books limit.

## Install on Windows

Copy these **three patch files** to your existing project folder, `C:\Users\Pros\Desktop\StudentAssistantBot`:
- `PATCH_BOOK_LIBRARY_PUBLIC_LATEST5.py`
- `TEST_BOOK_PUBLIC_LATEST5.py`
- `README_BOOK_LIBRARY_PUBLIC_LATEST5.md`

Before applying, run:

```powershell
python PATCH_BOOK_LIBRARY_PUBLIC_LATEST5.py --check
```

Expect a preview changing **only** `book_library_bot.py` and `book_library_store.py`.

Apply and test:

```powershell
python PATCH_BOOK_LIBRARY_PUBLIC_LATEST5.py --apply
python -m py_compile book_library_bot.py book_library_store.py main.py navigation.py
python -m unittest TEST_BOOK_LIBRARY TEST_BOOK_PUBLIC_LATEST5 -q
python PATCH_BOOK_LIBRARY_PUBLIC_LATEST5.py --check
```

Expected: **56 tests**, `OK`, and the second `--check` reports already installed. The patch creates a `BOOK_PUBLIC_LATEST5_BACKUP_...` folder when it modifies files; keep the backup locally and **do not commit it**.

## Render configuration

Set the following in **Render → Environment**:

```dotenv
BOOK_LIBRARY_ENABLED=true
BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT=false
BOOK_LIBRARY_ALLOW_ALL_GROUPS=true
BOOK_LIBRARY_AUTO_GROUP_SEARCH=false
```

Keep your existing `BOOK_LIBRARY_CHANNEL_ID`, `BOOK_LIBRARY_ADMIN_IDS` and verified-adult / Gemini / V8–V11 settings unchanged. You may leave `BOOK_LIBRARY_GROUP_IDS` configured; the new all-groups flag overrides the allowlist for this library only. To restrict groups again, set `BOOK_LIBRARY_ALLOW_ALL_GROUPS=false`.

## Stage only the intended changes

```powershell
git add -- PATCH_BOOK_LIBRARY_PUBLIC_LATEST5.py TEST_BOOK_PUBLIC_LATEST5.py README_BOOK_LIBRARY_PUBLIC_LATEST5.md
git add -p -- book_library_bot.py book_library_store.py
git diff --cached --check
git diff --cached --name-only
```

Expect **five** files staged. Confirm the diff, then:

```powershell
git commit -m "Book Library: public groups and latest five uploads"
git push origin main
```

Only enable the new Render configuration once Render shows **Live** for this commit.

## Telegram tests

1. From an unverified student's private chat: tap `📚 Book Library`, then **Latest Books**. Expect **up to five newest books**; no adult verification is required.
2. From any group with the bot added: send `/booklatest` or `/books`. Expect up to five books, shown as buttons opening **private delivery**.
3. In the group: send `/book Small Habits` (or another uploaded book title). Expect matching results.
4. Tap a book. A new user may need to press **Start** in the bot's private chat before receiving the file.
5. Upload a new lawfully distributable book as admin and repeat **Latest Books**; the newly uploaded title should appear first.
6. Confirm only an authorized administrator can upload or unlist books, and V8/V9/Gemini still require their original authorization.

**Troubleshooting**
- No latest results: verify the books are active in `book_library_items`, that the Supabase credentials are correct, and that uploads previously returned `Added to Book Library`.
- Group command ignored: verify the bot is a member and receiving commands; use `/booklatest@YourBotUsername` if needed. Group privacy mode normally permits commands addressed specifically to the bot.
- Empty group list: with `BOOK_LIBRARY_ALLOW_ALL_GROUPS=false`, add the group ID to `BOOK_LIBRARY_GROUP_IDS`.
- No automatic response when someone types a title without `/book`: normal while `BOOK_LIBRARY_AUTO_GROUP_SEARCH=false`.
- This patch doesn't alter file storage: the private channel and channel ID must remain configured and the bot must be a posting admin.

Only share books you are authorized to distribute. The library is public to all ages when configured as above.
