# Student Assistant Telegram Bot — V11.1 Book Library

**Release candidate** for the existing Python 3.12 / pyTelegramBotAPI / Flask / Render / Supabase Student Assistant Bot. Keeps V7–V11 code and uses **the same bot, Supabase project, and Render service**. No Gemini, new service, or new Python package is required.

## What it does

- Adds the **📚 Book Library** button directly on the **main keyboard**.
- Admin uploads a book in the bot's **private chat**, attaching a PDF/EPUB/DOCX/TXT document with caption `Title | Author | Language`.
- The bot **copies the Telegram message to a private storage channel** and inserts title, author, language, file size, storage channel ID and channel message ID into Supabase. **No book bytes are stored in Supabase.**
- Users search privately using **📚 Book Library**, `/book Title`, or `/booksearch Author`.
- Users in an **approved group** search using `/book Title`. Optional: enable ordinary group-text search after configuring @BotFather privacy mode (details below).
- Results show **inline buttons** (title, author, language, file size); clicking a result opens a `t.me/YOUR_BOT?start=book_UUID` link. The bot copies that book into the user's **private chat**.
- Each private delivery verifies the account's adult eligibility using the existing `study_access_v9.is_verified_adult` method by default.
- Admins can unlist books using `/bookremove BOOK_UUID` (does **not** delete the original storage-channel post).

### Important Telegram behavior

Telegram bots **cannot initiate a private chat with a user who has never started the bot**. Group results use a private deep link rather than trying to send files from a group callback. The user must tap **Start** the first time. This uses Telegram's official deep-link and `copyMessage` features. Source: https://core.telegram.org/bots/features and https://core.telegram.org/bots/api

Use only **public-domain, openly licensed, or otherwise lawfully shareable** books. This release does not search the internet for pirated copies.

## Contents

- `book_library_bot.py` — Telegram handlers, private delivery, admin upload and restricted group search.
- `book_library_store.py` — Supabase catalog operations.
- `SQL_BOOK_LIBRARY.sql` — private catalog and parameterized RPC function.
- `INSTALL_BOOK_LIBRARY.py` — preview, idempotent installation and source-file backups.
- `TEST_BOOK_LIBRARY.py` — offline tests.
- `README_BOOK_LIBRARY.md` — this guide.

**Integration modifies `main.py` and `navigation.py` only**; no `ui_v57.py` change is needed. The existing `/start` handler is extended to honor `book_UUID` links before it displays the normal menu.

## Step 1 — Create a private storage channel

1. In Telegram create a **private channel**, e.g. *Student Book Storage*.
2. Add **your existing bot as an administrator**. Give it **Post Messages** permission. For best-effort rollback if a database insert fails, grant **Delete Messages** too.
3. Find the channel's **numeric chat ID** starting with `-100`. For many private channels, a post link like `https://t.me/c/1234567890/9` indicates chat ID `-1001234567890`; verify against your actual channel. Do not confuse it with the post's message ID (9).
4. Keep the storage channel private. Do not use a group as file storage.

## Step 2 — Supabase (BEFORE enabling the bot)

Back up your existing Supabase database. Open **SQL Editor**, review and run **all** of `SQL_BOOK_LIBRARY.sql`.

Verify:

```sql
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname='public' AND tablename='book_library_items';

SELECT routine_name FROM information_schema.routines
WHERE routine_schema='public' AND routine_name='book_library_search';
```

Expected: table exists, `rowsecurity = true`, search function exists. Leave anonymous/authenticated roles without access; only the existing server-side `db.supabase` client should access the catalog.

## Step 3 — Install locally

Unzip into the existing project directory, for example:
`C:\Users\Pros\Desktop\StudentAssistantBot`

Run:

```powershell
python INSTALL_BOOK_LIBRARY.py --check
python -m unittest TEST_BOOK_LIBRARY -q
```

The preview should show only:

- `main.py`: Book Library early handler registration and a small `/start` deep-link check.
- `navigation.py`: one direct main-menu button and its navigation index entry.

If correct:

```powershell
python INSTALL_BOOK_LIBRARY.py --apply
python INSTALL_BOOK_LIBRARY.py --check
python -m py_compile book_library_bot.py book_library_store.py main.py navigation.py
python -m unittest TEST_BOOK_LIBRARY -q
```

The installer backs up modified source files to a `BOOK_LIBRARY_BACKUP_...` folder. Exclude that folder from Git.

Run your existing V8–V11 regression tests before the commit; some legacy V8/V9 test fixtures require temporary `STUDY_ACCESS_MODE=pilot` **locally**, not on Render.

## Step 4 — Render environment settings

Initial deployment (do not enable until SQL and code are deployed):

```dotenv
BOOK_LIBRARY_ENABLED=false
BOOK_LIBRARY_CHANNEL_ID=-1001234567890
BOOK_LIBRARY_ADMIN_IDS=YOUR_ADMIN_TELEGRAM_ID
BOOK_LIBRARY_GROUP_IDS=-1009876543210
BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT=true
BOOK_LIBRARY_AUTO_GROUP_SEARCH=false
BOOK_LIBRARY_MAX_BYTES=52428800
```

Replace both example IDs. `BOOK_LIBRARY_ADMIN_IDS` may be omitted to reuse your existing `V91_ADMIN_USER_IDS`; a dedicated admin allowlist is recommended. `BOOK_LIBRARY_BOT_USERNAME` is optional; the bot uses `getMe()` if omitted.

**Keep your existing `STUDY_ACCESS_MODE=verified_adults` and all V7–V11 configuration unchanged.** Enable `BOOK_LIBRARY_ENABLED=true` only after successful Render deployment and SQL migration.

Set `BOOK_LIBRARY_GROUP_IDS` to an **explicit allowlist** of approved Telegram group numeric IDs. Without it, group searches are denied (private searching still works). Your current `/id` command in the group may show its chat ID.

### Group messages without `/book`

The default is safer: users type `/book Ibn Kathir` in the approved group, and Telegram Group Privacy Mode can stay enabled.

To match the movie bot's *any text* group behavior:

1. Set `BOOK_LIBRARY_AUTO_GROUP_SEARCH=true` on Render.
2. In Telegram, use **@BotFather → /setprivacy → your bot → Disable**. Some groups require re-adding the bot for the change to take effect.
3. **Only use in approved groups**, set `BOOK_LIBRARY_GROUP_IDS` accurately. Telegram will expose ordinary group messages to your bot; do not enable this in unrelated groups, especially those containing private/sensitive discussions.
4. The bot silently ignores nonmatching queries, and throttles matching searches per user. Results are capped at 6 buttons per group message. If other group features conflict, turn automatic group search back off and use `/book Title`.

## Step 5 — Stage, commit and deploy safely

```powershell
git add -- book_library_bot.py book_library_store.py SQL_BOOK_LIBRARY.sql INSTALL_BOOK_LIBRARY.py TEST_BOOK_LIBRARY.py README_BOOK_LIBRARY.md
git add -p -- main.py navigation.py
git diff --cached --check
git diff --cached --name-only
```

Review the exact eight files and hunk contents. Avoid `git add .`, backups and `.env` secrets.

```powershell
git commit -m "V11.1: Add private-channel Book Library"
git push origin main
```

After Render reports **Live**, change `BOOK_LIBRARY_ENABLED=true`, save/deploy, then test the live workflow. No new Render instance, Gemini key, or Docker change is required.

## Step 6 — Live Telegram acceptance test

1. From a library administrator's private chat, send a **lawfully shareable test PDF** with caption:
   `Ihya Ulumuddin | Al-Ghazali | Arabic`
2. Expected bot reply: `✅ Added to Book Library` with a unique catalog UUID.
3. Verify the file also appears in the private storage channel.
4. From a **verified adult** account, tap **📚 Book Library → 🔎 Search a Book**, then type `Ihya` (or send `/book Ihya`).
5. Tap the result; open the bot in private and tap **Start** if prompted. Expect a copied file from the storage channel.
6. In an approved group, send `/book Ihya`. Confirm that the **same file** can be requested privately without dumping files into the group.
7. Verify that a nonverified account cannot receive the file; test `BOOK_LIBRARY_AUTO_GROUP_SEARCH` only if needed.
8. Verify existing V8, V9, Gemini, `/study`, `/v10`, `/v101`, admin features and document conversions still work.
9. To unlist a test book: `/bookremove BOOK_UUID` from an authorized administrator's private chat.

**Limitations:** This is a tested local-release candidate, not a proven production deployment. The library indexes metadata only, does not automatically extract PDF text, does not implement DRM, and cannot guarantee delivery if a post is deleted or the bot loses storage-channel permissions. It does not automatically check the legal licensing of uploaded content.
