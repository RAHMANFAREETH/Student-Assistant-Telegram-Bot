# Student Assistant Telegram Bot — V11.3 Advanced Library (all 18 features)

**Release candidate, not automatically deployed.** Additive update for the **same bot, same Render service, same Supabase project and same private book-storage channel**. Requires a working **V11.2 Advanced Digital Library**. Does not replace V11.2, the public Book Library, V8–V11 study tools, the adult-verification system or Gemini integration.

**This is one combined release containing all 18 requested feature areas.** Each area has at least one working bot/API workflow. The Mini App is an interactive Telegram web page served from the existing Flask service. No new paid API key or separate Render service is required. Open Library metadata lookup is **optional, admin-triggered and limited**.

## What is included

| # | Feature | Telegram command / behavior |
|---|---|---|
| 1 | Smart multilingual/typo-tolerant search | `/book TITLE`, `/booksmart TITLE` — Unicode-aware suggestions for latest 500 candidates when no close direct match. Arabic optional harakat ignored, Tamil/Sinhala vowel signs preserved. Existing automatic group message matching remains strict to prevent false positives. |
| 2 | Telegram inline search | `@YourBotUsername KEYWORD` in any chat; sends an inline result with private delivery link. Requires **@BotFather → /setinline**. |
| 3 | Related-book recommendations | `/bookrelated BOOK_UUID` and **Similar books** in the Mini App; based on category/author/series/language without AI. |
| 4 | Automatic book metadata | Admin: `/bookmeta ISBN`, `/bookmetafill UUID \| ISBN`; fetches book metadata from Open Library. Admin must review; **no copyrighted book files are downloaded**. |
| 5 | Book series and editions | Admin: `/bookedition UUID \| Series \| Volume \| Edition \| Translator \| Publisher \| Year`; readers: `/bookseries SERIES`. |
| 6 | Reading progress | Private: `/bookprogress UUID \| reading \| 30`, `/bookreading`; Mini App mark as completed. Status: `want`, `reading`, `completed`. |
| 7 | Book ratings and moderated reviews | Private: `/bookreview UUID \| 5 \| My comments`, `/bookreviews UUID`. Admin: `/bookreviewsadmin`, `/bookreviewmoderate REVIEW_UUID \| approved` (or `rejected`). Public reviews never show user IDs. |
| 8 | Reading challenges and opt-in reminders | `/bookchallenge 5 30`, `/bookchallengecheck`; opt-in: `/bookalert challenge \| daily`; notifier is separately enabled and best-effort. |
| 9 | Personal book collections | `/bookcollection NAME`, `/bookcollections`, `/bookcollectionadd COLLECTION_UUID \| BOOK_UUID`, `/bookcollectionview COLLECTION_UUID`. Scoped by authenticated user ID. |
| 10 | New-book alerts | `/bookalert category \| Psychology`, `/bookalert author \| Al-Ghazali`, `/bookalerts`; remove: `/bookalert off category \| Psychology`. Notifications enqueued after admin upload; best-effort worker delivers. |
| 11 | Request a book | `/bookrequest Title \| Optional Author`. Admin `/bookrequests`, `/bookrequestresolve REQUEST_UUID \| fulfilled`. 5 pending requests per user. |
| 12 | Student book submissions | `/booksubmit` then send one supported file with rights explanation. Goes to a **separate private review channel**; admin `/booksubmissions`, `/booksubmitapprove UUID RIGHTS_CHECKED` or `/booksubmitreject UUID`. Never auto-published. |
| 13 | Duplicate detection | Admin uploads checked using Telegram `file_unique_id` and ISBN before storage copying. Optional SHA-256 for files up to 8 MB (`BOOK_LIBRARY_HASH_SMALL_FILES=true`), which downloads those files briefly into memory; off by default. |
| 14 | CSV bulk metadata editing | Admin: `/bookbulk`, upload CSV then `/bookbulkapply`. Dry-run preview, max 30 existing IDs/120 KB per batch; cannot inject arbitrary files into catalog. |
| 15 | Broken-file/copyright reports | Private `/bookreport UUID \| copyright \| Explanation` or `broken_file`, `metadata`, `inappropriate`. Admin `/bookreports`, `/bookreportresolve REPORT_UUID \| resolved`; use existing `/bookremove UUID` to unlist immediately. |
| 16 | Advanced analytics | Admin `/bookanalytics`: top downloads, popular categories, explicit-search misses, daily aggregate counts. Search-miss logging never scans ordinary group conversations. |
| 17 | Telegram Mini App | **Open Library Mini App** button in private book menu, served by the same Flask app at `/library`. Search, filter, covers, details/previews, private delivery links, favorites, reading and collections. Every API call validates signed Telegram `initData` server-side. |
| 18 | Book descriptions and reading previews | Admin `/bookdescription UUID \| Description \| Authorized sample text`; readers `/bookinfo UUID` and Mini App About / Preview. Admin `/booklicense UUID \| public_domain` records declared rights classification. Only include excerpts you may lawfully distribute. |

Book IDs are shown in the existing admin `/bookmanage`. Public book links also encode the catalog UUID; users can primarily discover books using buttons or the Mini App.

## Before you install

1. Keep V11.2 operational and backed up. Current Render environment should contain:
   ```dotenv
   BOOK_LIBRARY_ENABLED=true
   BOOK_LIBRARY_V112_ENABLED=true
   BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT=false
   BOOK_LIBRARY_ALLOW_ALL_GROUPS=true
   BOOK_LIBRARY_AUTO_GROUP_SEARCH=true
   ```
   Your Book Library stays public to **all ages**. Gemini/AI access restrictions are separate and remain unchanged.
2. Back up Supabase and your local Git repository. Do **not** add credentials or backup folders to Git.
3. Create a **second private Telegram channel for student-submission review**. Add your existing bot as administrator with permission to post. Set `BOOK_LIBRARY_REVIEW_CHANNEL_ID` to its real negative numeric ID. This must differ from `BOOK_LIBRARY_CHANNEL_ID`. The original storage channel remains unchanged.
4. For inline search, in **@BotFather** use `/setinline` for the bot and enable the inline feature. This does not require disabling group privacy.

## Step 1 — Install the Supabase migration

In Supabase → SQL Editor, review and run `SQL_BOOK_LIBRARY_V113.sql` **before enabling V11.3**. This is an additive, transactional migration: it adds book metadata columns, new personal/review/admin tables, server-only functions, RLS and role restrictions. It does not delete catalog data, favorites or Telegram storage posts.

Check that it succeeded:

```sql
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname='public' AND tablename IN (
'book_library_reading_progress','book_library_reviews','book_library_challenges',
'book_library_collections','book_library_collection_items','book_library_subscriptions',
'book_library_requests','book_library_submissions','book_library_reports',
'book_library_search_misses','book_library_daily_stats','book_library_notifications'
) ORDER BY tablename;
```

Expect **12 tables**, all `rowsecurity=true`. (The existing V11.2 tables are retained.)

## Step 2 — Install V11.3 on Windows

Extract all **11 new files** from the ZIP into your existing folder:

`C:\Users\Pros\Desktop\StudentAssistantBot`

In PowerShell:

```powershell
python INSTALL_BOOK_LIBRARY_V113.py --check
python -m unittest TEST_BOOK_LIBRARY_V113 -q
```

Review the diff carefully. The installer modifies only `book_library_bot.py`, `book_library_store.py` and `main.py`; the existing V11.2 handlers remain in place. To apply:

```powershell
python INSTALL_BOOK_LIBRARY_V113.py --apply
python INSTALL_BOOK_LIBRARY_V113.py --check
python -m py_compile book_library_v113_bot.py book_library_v113_store.py book_library_v113_web.py book_library_v113_notify.py main.py book_library_bot.py book_library_store.py
```

The installer is idempotent; it writes a `BOOK_V113_BACKUP_...` folder with original source files. Exclude this backup from Git.

Run the complete library tests with the *new flag off in your local shell* so legacy fixtures continue to use their expected V11.2 behavior:

```powershell
$previous = $env:BOOK_LIBRARY_V113_ENABLED
try {
  $env:BOOK_LIBRARY_V113_ENABLED = 'false'
  python -m unittest TEST_BOOK_LIBRARY TEST_BOOK_PUBLIC_LATEST5 TEST_BOOK_LIBRARY_V112 TEST_BOOK_LIBRARY_V113 -q
} finally {
  if ($null -eq $previous) { Remove-Item Env:BOOK_LIBRARY_V113_ENABLED -ErrorAction SilentlyContinue }
  else { $env:BOOK_LIBRARY_V113_ENABLED = $previous }
}
```

Expected offline count from the release candidate: **165 tests**, then `OK`. These tests simulate the interactions; they do not prove live Supabase, Telegram inline, Open Library or Mini App behavior.

## Step 3 — Safe Git staging and deployment

First set on Render **before pushing**:

```dotenv
BOOK_LIBRARY_V113_ENABLED=false
BOOK_LIBRARY_MINIAPP_ENABLED=false
BOOK_LIBRARY_NOTIFIER_ENABLED=false
BOOK_LIBRARY_REVIEW_CHANNEL_ID=-100YOUR_REAL_REVIEW_CHANNEL_ID
BOOK_LIBRARY_MINIAPP_URL=https://student-assistant-telegram-bot.onrender.com/library
BOOK_LIBRARY_BOT_USERNAME=YOUR_BOT_USERNAME_WITHOUT_AT
BOOK_LIBRARY_HASH_SMALL_FILES=false
```

Do not use literal placeholder values for the review channel/username. Keep every existing Render variable, Gemini key and verified-adult setting unchanged.

Stage **only** these 11 new files:

```powershell
git add -- book_library_v113_store.py book_library_v113_bot.py book_library_v113_web.py book_library_v113_notify.py
git add -- book_library_v113_miniapp.html book_library_v113_style.css book_library_v113_app.js
git add -- SQL_BOOK_LIBRARY_V113.sql INSTALL_BOOK_LIBRARY_V113.py TEST_BOOK_LIBRARY_V113.py README_BOOK_LIBRARY_V113.md
```

Stage only the V11.3 hunks from the 3 modified files:

```powershell
git add -p -- book_library_bot.py book_library_store.py main.py
git diff --cached --check
git diff --cached --name-only
git diff --cached --stat
```

Expect **14 files**: 11 new, 3 integration files. Do not use `git add .`, and do not stage backups or secrets.

```powershell
git commit -m "V11.3: Add all 18 advanced library features and Mini App"
git push origin main
```

Wait for Render to finish deployment **before** turning on new flags. The default-disabled integration should not change the active V11.2 behavior.

## Step 4 — Enable core commands first

After verifying the SQL and Render deployment, set:

```dotenv
BOOK_LIBRARY_V113_ENABLED=true
BOOK_LIBRARY_MINIAPP_ENABLED=false
BOOK_LIBRARY_NOTIFIER_ENABLED=false
```

Save/deploy. Test `/booklatest`, `/book Small Habits`, `/bookbrowse`, `/booksmart Small Habbits`, `/bookrequest Test Book` and `/bookreading` from permitted public accounts. Test admin `/bookanalytics`, `/bookmeta 9780140328721`, `/booksubmissions` and `/bookreports`. Check that existing V8/V9/Gemini/adult admin functions still work.

**Only then** enable the Mini App:

```dotenv
BOOK_LIBRARY_MINIAPP_ENABLED=true
BOOK_LIBRARY_MINIAPP_URL=https://student-assistant-telegram-bot.onrender.com/library
```

Open a private chat with the bot → **📚 Book Library → Open Library Mini App**. Launch **inside Telegram**; direct external browsers won't have signed Telegram initData and API calls will be rejected. A URL with `https://` is required. No additional Render service is necessary.

**Finally**, if opt-in alerts and reading-challenge reminders have been verified, optionally enable:

```dotenv
BOOK_LIBRARY_NOTIFIER_ENABLED=true
BOOK_LIBRARY_NOTIFY_INTERVAL_SECONDS=300
```

The notifier uses the existing service and atomic Supabase claims; deliveries are **best effort**, not guaranteed while Render sleeps/restarts. Do not advertise guaranteed reminders without always-on scheduling.

## Security and privacy notes

- Files stay in Telegram channels; public catalog metadata stays in server-side Supabase. Mini App API does not reveal channel IDs, message IDs, bot token, user IDs of contributors, or Supabase credentials.
- Telegram Mini App server verifies `initData` signature and freshness for **each API request**, then derives the user ID itself. A user-supplied ID never grants favorites or progress access. No API data is available anonymously.
- Reviews are moderated; student uploads are **not** published before administrator rights review. The review channel is a separate private channel.
- Use only **public-domain, permissively licensed or explicitly authorized** books and previews. An ISBN or permission claim does not prove distribution rights. The operator must independently review submitted rights; the bot cannot do this automatically.
- The new alert and Mini App switches are separate from `STUDY_ACCESS_MODE`. Keep `BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT=false` for public book access; **do not disable adult gating for Gemini and other age-restricted tools**.
- Automatic group-text search was already enabled in V11.1/V11.2. It remains strict substring-based to avoid replying to unrelated messages; fuzzy results apply to **explicit** search commands and Mini App searches.
- Open Library APIs are intended for human-driven metadata lookups, not bulk harvesting. Lookups are admin-triggered and cached; respect Open Library usage limits. See https://openlibrary.org/developers/api.
- SHA-256 duplicate checks are **off by default**; switching on downloads small incoming files into memory, capped at 8 MB. Telegram file ID and ISBN checks work without downloading file bytes.
- Daily analytics aggregate counts. The search-miss table records **only explicit search terms** (which can still be sensitive); don't log ordinary group conversations or store readers' private downloads.
- Public reviews include no user ID in returned fields, and browser-rendered user text is inserted with `textContent`, not `innerHTML`.

## Limitations and next checks

This package is an **offline-tested release candidate**. Check SQL migration success on *your* Supabase instance, Telegram message routing, Mini App launch, group behavior, Open Library availability, existing Render worker resource limits, and actual private file delivery before treating it as production-ready.

Fuzzy reranking and related-book suggestions read a **bounded catalog sample** (500 and 250 rows respectively); very large libraries may need PostgreSQL search indexes in a later optimization. Reminder delivery is best-effort while your single Render service is running. Bulk CSV updates metadata for **existing** book UUIDs; it does not upload new book files. Challenges count books marked completed during the challenge, not actual reading time. Automated copyright verification is not provided.
