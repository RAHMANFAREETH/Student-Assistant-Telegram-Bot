# V11.2 — Advanced Digital Library (all enhancements in one release)

This is an **additive update** to your existing V11.1 Student Assistant Book Library. It reuses the same Telegram bot, private storage channel, Supabase project, Render service and existing main-menu `📚 Book Library` button. Do **not** reinstall or replace `main.py` or `navigation.py`.

## All eight improvements, delivered together

1. **Categories** — browse by category; categories are added by administrators, previous books default to `General`.
2. **Author and language filters** — browse available authors/languages with Telegram buttons, or search explicitly by author/language.
3. **Pagination** — paginated search and browse results, five items per page, 10-minute navigation sessions. Buttons sent in groups may be used by group members; session tokens stay scoped to their original chat.
4. **ISBN catalog lookup** — add an optional valid ISBN-10/ISBN-13 and look it up with `/bookisbn`. No external ISBN service or copyrighted-book downloading.
5. **Book-cover previews** — administrators attach a cover photo; users can preview it privately before downloading.
6. **Favorites** — private, per-Telegram-account favorites stored in Supabase, without sharing private lists in groups.
7. **Delivery statistics** — aggregate per-book counters increment only **after Telegram confirms a copy**. Existing historical downloads are not backfilled; this tracks deliveries starting after V11.2 is enabled.
8. **Admin editing** — edit catalog metadata, assign/remove cover photos and list recent books with their IDs.

All previous functionality remains, including **public access for all ages**, automatic group title search if you enabled it, latest **five** books, original `/book` commands, private file delivery and the V7–V11 study tools with their existing separate access rules.

## What you need

- Previously installed, working V11.1 Book Library and the public/Latest5 patch.
- Existing `BOOK_LIBRARY_CHANNEL_ID`, `BOOK_LIBRARY_ADMIN_IDS`, a service-role Supabase connection already used by V11.1, and a working bot.
- The original `TEST_BOOK_LIBRARY.py` and `TEST_BOOK_PUBLIC_LATEST5.py` already in your project, for the full regression test.
- No new API key, Python dependency or Render service.

## Database migration — do this before enabling the new flag

1. Back up Supabase.
2. In **Supabase → SQL Editor**, inspect and run `SQL_BOOK_LIBRARY_V112.sql`.
3. This **adds columns** to `book_library_items` (`category`, `isbn`, `cover_file_id`, `download_count`), creates `book_library_favorites`, and creates three server-only RPC functions.
4. It does **not** delete your existing catalog, change the private channel, or alter older verification tables. Keep Row Level Security and the service-role key server-side. Do not publish the key or grant write access to public roles.

Check the migration:

```sql
SELECT column_name FROM information_schema.columns
WHERE table_schema='public' AND table_name='book_library_items'
  AND column_name IN ('category','isbn','cover_file_id','download_count')
ORDER BY column_name;

SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname='public' AND tablename IN
 ('book_library_items', 'book_library_favorites') ORDER BY tablename;
```

Expect all four columns and **both** tables to have `rowsecurity=true`.

## Windows installation

Extract the ZIP and copy all **six new files** into:

`C:\Users\Pros\Desktop\StudentAssistantBot`

Run in PowerShell:

```powershell
python INSTALL_BOOK_LIBRARY_V112.py --check
python INSTALL_BOOK_LIBRARY_V112.py --apply
python INSTALL_BOOK_LIBRARY_V112.py --check
python -m py_compile book_library_bot.py book_library_store.py book_library_v112_bot.py book_library_v112_store.py
python -m unittest TEST_BOOK_LIBRARY TEST_BOOK_PUBLIC_LATEST5 TEST_BOOK_LIBRARY_V112 -q
```

The installer changes **only** `book_library_bot.py` and `book_library_store.py`; it automatically backs them up into a `BOOK_V112_BACKUP_...` folder. It refuses unexpected code layouts instead of guessing. Repeating `--apply` is harmless and will report already installed. **Never commit the backup folder**.

Local test expectation on the bundled baseline: `Ran 105 tests ... OK`. If your prior tests differ, the number may differ, but all must pass before committing.

## Git commit and Render rollout

Keep `BOOK_LIBRARY_V112_ENABLED=false` for the first deployment. Stage only the 6 new + 2 modified files:

```powershell
git add -- book_library_v112_bot.py book_library_v112_store.py SQL_BOOK_LIBRARY_V112.sql INSTALL_BOOK_LIBRARY_V112.py TEST_BOOK_LIBRARY_V112.py README_BOOK_LIBRARY_V112.md
git add -p -- book_library_bot.py book_library_store.py
git diff --cached --check
git diff --cached --name-only
```

Verify the **eight intended filenames** (no backups, keys, `.env`, or unrelated changes). Then:

```powershell
git commit -m "V11.2: Advanced public digital library with filters and favorites"
git push origin main
```

Once Render is **Live** on the new commit and the SQL migration is complete, enable:

```dotenv
BOOK_LIBRARY_ENABLED=true
BOOK_LIBRARY_V112_ENABLED=true
BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT=false
BOOK_LIBRARY_ALLOW_ALL_GROUPS=true
BOOK_LIBRARY_AUTO_GROUP_SEARCH=true
```

Keep your existing `BOOK_LIBRARY_CHANNEL_ID`, `BOOK_LIBRARY_ADMIN_IDS` and other settings unchanged. `BOOK_LIBRARY_AUTO_GROUP_SEARCH=true` requires your bot to receive group text; preserve your current approved privacy arrangement and group moderation rules. You can set it `false` while retaining `/book TITLE` and `/booklatest`.

**Important:** This update does not remove existing adult-only gates on Gemini or restricted learning tools. Only Book Library access is public.

## Commands for students

| Command | Use | Private chat | Group |
|---|---|---|---|
| Tap `📚 Book Library` | Open menu, categories, favorites and browsing | ✓ | Library guidance |
| `/book TITLE` | Search title/author | ✓ | ✓ |
| `/booklatest` | Latest **5** books | ✓ | ✓ |
| `/bookbrowse` | Browse all books 5/page | ✓ | ✓ |
| `/bookcats` | Category list with buttons | ✓ | ✓ |
| `/bookcat Self-Help` | Show books in a category | ✓ | ✓ |
| `/bookauthors` | Authors with buttons | ✓ | ✓ |
| `/bookauthor Author Name` | Exact author filter | ✓ | ✓ |
| `/booklangs` | Languages with buttons | ✓ | ✓ |
| `/booklang Tamil` | Language filter | ✓ | ✓ |
| `/bookisbn 9780306406157` | Exact ISBN lookup | ✓ | ✓ |
| `/bookfavs` | My favorites | ✓ | Private only |
| `/bookpreview BOOK_UUID` | Cover and metadata | ✓ | Private only |
| `/bookfav BOOK_UUID` | Add/remove favorite | ✓ | Private only |

Book lists include **📥 Get Book** links and **🖼 Cover / Details** links, both pointing to the bot's **private chat**. The bot cannot directly initiate a chat with a new student; they may need to tap **Start**. Existing files remain in the private channel and are delivered with Telegram's `copy_message`.

## Commands for administrators (private bot chat only)

```text
/bookmanage
/bookstats
/bookedit BOOK_UUID | New Title | New Author | Language | Category | ISBN-or--
/bookcover BOOK_UUID
```

Use `/bookmanage` to find existing books' IDs. To attach a cover, send `/bookcover UUID`, then **send a Telegram photo within 3 minutes**. To remove a cover: `/bookcover UUID clear`. Metadata editing never changes the underlying stored file. The optional ISBN must have a valid check digit; enter `-` if absent.

### New upload captions

All three caption formats work:

```text
Small Habits, Big Changes | Student Assistant Library | English
Small Habits, Big Changes | Student Assistant Library | English | Self-Help
Book Title | Book Author | English | Science | 9780306406157
```

The **original three-part caption continues to work**. Category/ISBN in a new 4- or 5-part caption requires V11.2 enabled *after* the SQL migration.

## Privacy, limits and troubleshooting

- Favorites store Telegram numeric user IDs plus book IDs in a **restricted** Supabase table. Favorites are not displayed in groups. No date of birth or identity-document information is collected.
- Delivery statistics are **aggregate** counts, not unique-user analytics, and start at zero for existing books. Repeated deliveries are counted separately.
- Five results per page; pagination tokens expire after ten minutes and may be invalidated if Render restarts. Re-run your search to get new buttons.
- Cover previews are optional. If a photo file ID is no longer usable, users get a text-only preview.
- Filters and ISBN apply to the bot's **existing** catalog; the bot does not search the web or download books from external services.
- If a feature says `Catalog unavailable`, check SQL function names/permissions, service-role connection and Render logs. Keep `BOOK_LIBRARY_V112_ENABLED=false` until the migration is verified.
- If automatic group search is enabled, remind group members that the bot processes regular group text; use cooldowns and group moderation controls.
- Upload and distribute **only books you have permission to share**.

This is a locally tested release candidate. The 105 offline tests cover representative routing, permissions, store calls and installer compatibility. Live Telegram callback behavior, Supabase permission handling, delivery counts and photo reuse must be tested on Render before considering it production verified.
