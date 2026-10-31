# Student Assistant Telegram Bot — V11.7 All-in-One Media Library + Community Submissions

**Additive, opt-in update.** Keeps the existing Book Library (`book_library_items`), V11.3 community tools, V11.5 five-minute cleanup, V11.6 group-only-library routing, and V11.6.1 group menu. Does NOT introduce a new bot, new hosting service, paid API, or remove Gemini age restrictions.

## What is included

| Capability | Public Telegram groups | Private bot |
|---|---|---|
| PDF + images + audio + video + ZIP + DOCX + PPTX + EPUB + TXT search | `/book phrase` + `/booklatest`, `/mediapopular`; plain text when enabled | Search and delivery |
| File badges, mixed latest five, filters (type/language/author/category/min-max size/sort), related items | Temporary button links; group thumbnail of first result when available | Full previews, related files, private delivery |
| PDF first-page/image thumbnails, OCR text indexing, suggested metadata | Searchable approved catalog only | Upload review and file preview |
| Download counts, weekly popularity, multilingual text/aliases, favorites/reading status | Popular links (no personal data) | Favorite and reading progress |
| Resource requests, request statuses, user submissions, reviews/reports, audits | Not accessible | User/admin functions |
| Admin bulk uploads (sequential files or capped ZIP), duplicate checks, admin publish/hide/restore/rename/edit | Not accessible | `More Tools → 🛡️ Library Admin Panel` (authorized admins only) |
| Temporary messages deleted after 300 seconds | Existing V11.5 cleanup queue | Not applicable |

**Preserved legacy tools:** Gemini (existing verified-adult restrictions), PDF utilities, OCR/image tools, quizzes, existing book features, Office conversions and all previous student tools. Public library search is not restricted by the Gemini verification gate if `BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT=false`.

### Supported file types

- 📄 PDF
- 🖼️ Image (JPG/PNG/WebP/GIF as Telegram document; JPG photos supported)
- 🎧 Audio (MP3/M4A/OGG/WAV)
- 🎥 Video (MP4/MOV/MKV/WebM)
- 📦 ZIP (may also be a library item)
- 📝 DOCX / 📊 PPTX / 📚 EPUB / 📃 TXT

**Limits:** Admin single item 50 MB by default, community upload 20 MB by default; bulk ZIP 20 MB compressed / 20 entries / 40 MB expanded / 8 MB per file. The Telegram Bot API, hosting plan, and library channel may impose lower practical limits. Bulk ZIP import supports the common file formats listed in the upload prompt. No automatic virus-scanning engine is bundled: only publish reviewed, trusted files and avoid allowing executable archives in the public library.

## 1. Prepare local project

Working directory: `C:\Users\Pros\Desktop\StudentAssistantBot`.

1. Make a backup of your Git repository and Supabase schema before migration.
2. Extract all release files at the **top level** of the current project, alongside `main.py`, `book_library_bot.py`, and `group_ui_v115.py`. Do not place them into a nested folder.
3. Keep all existing V11.6.1 files intact. The patch will refuse unexpected older source layouts rather than overwrite them.

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python INSTALL_LIBRARY_MEDIA_V117.py --check
```

Review its proposed 5-file diff. Then:

```powershell
python INSTALL_LIBRARY_MEDIA_V117.py --apply
python INSTALL_LIBRARY_MEDIA_V117.py --check
python -m py_compile library_media_v117_store.py library_media_v117_processing.py library_media_v117_bot.py book_library_bot.py group_books_only_v116.py group_ui_v115.py ui_v57.py navigation.py
```

The main installer modifies **only** `book_library_bot.py`, `group_books_only_v116.py`, `group_ui_v115.py`, `ui_v57.py`, `navigation.py`, and creates a timestamped backup folder. `main.py` is deliberately untouched.

### Optional recommended OCR Docker installation

The release includes an optional installer adding free Tesseract packages for English/Tamil/Arabic/Sinhala. It **preserves existing LibreOffice and Docker instructions**. Run only if your Dockerfile still has the compatible `apt-get install -y --no-install-recommends ... ca-certificates` block:

```powershell
python INSTALL_LIBRARY_OCR_DOCKER_V117.py --check
python INSTALL_LIBRARY_OCR_DOCKER_V117.py --apply
python INSTALL_LIBRARY_OCR_DOCKER_V117.py --check
```

If this installer reports a layout mismatch, **do not force it**. Review your current Dockerfile and add the packages into the existing apt list manually: `tesseract-ocr tesseract-ocr-eng tesseract-ocr-tam tesseract-ocr-ara tesseract-ocr-sin`. Preserve LibreOffice and other dependencies. This step increases the Docker image size and build time. After deploying it, enable `LIBRARY_MEDIA_OCR_ENABLED=true`; otherwise leave the flag false. OCR is best-effort (image/first PDF page), not guaranteed accurate for every scan. Photo previews work without OCR, and existing legacy PDF cover images are reused.

## 2. Run all regression tests BEFORE deploying

The new release's offline tests must be run **after** the main install, because tests inspect the patched group-link recognizer:

```powershell
python -X utf8 -m unittest TEST_LIBRARY_MEDIA_V117 -q
python -X utf8 -m unittest TEST_BOOK_LIBRARY TEST_BOOK_PUBLIC_LATEST5 TEST_BOOK_LIBRARY_V112 TEST_BOOK_LIBRARY_V113 TEST_BOOK_LIBRARY_PRIVACY_V114 TEST_GROUP_UI_V115 TEST_GROUP_BOOK_ONLY_V116 TEST_GROUP_LIBRARY_MENU_V1161 TEST_LIBRARY_MEDIA_V117 -q
```

On the supplied V11.6.1 baseline these ran **310 tests successfully**. Warnings from deliberately simulated Supabase failures are not production evidence. Local test results may differ if your installed source version differs; send any traceback before forcing changes.

## 3. Apply the additive Supabase migration

In **Supabase → SQL Editor**, carefully review and execute `SQL_LIBRARY_MEDIA_V117.sql` as an authorized administrator.

- Creates `library_media_v117`, its favorites/reading/audit/download tables, and constrained SQL functions.
- Expands statuses on the existing `book_library_requests` table (`pending`, `fulfilled`, `found`, `uploaded`, `rejected`).
- Leaves all existing book records unchanged; does not alter V11.5 cleanup tables or V11.3 submissions.
- Enables Row Level Security and revokes direct anonymous/authenticated access to new media tables. The existing bot's service-role client is required.

**Safety:** Back up the current database/schema before SQL. Applying this migration has not been validated against your live Supabase schema, so check the SQL Editor for errors; do not enable V11.7 until it succeeds. Never share Supabase `service_role` keys publicly.

## 4. Stage ONLY the intended files and push GitHub

New files (8):

```powershell
git add -- library_media_v117_store.py library_media_v117_processing.py library_media_v117_bot.py SQL_LIBRARY_MEDIA_V117.sql INSTALL_LIBRARY_MEDIA_V117.py INSTALL_LIBRARY_OCR_DOCKER_V117.py TEST_LIBRARY_MEDIA_V117.py README_LIBRARY_MEDIA_V117.md
```

Existing files: review the integration changes interactively; stage only V11.7 changes:

```powershell
git add -p -- book_library_bot.py group_books_only_v116.py group_ui_v115.py ui_v57.py navigation.py
```

Only if you opted into OCR and its Dockerfile patch:

```powershell
git add -p -- Dockerfile
```

Verify:

```powershell
git diff --cached --check
git diff --cached --name-only
```

Expected: 8 new files + 5 modified integration files; + `Dockerfile` if OCR installed. **Do not use `git add .` or `git add -A`**, because this project contains unrelated backups. Then:

```powershell
git commit -m "V11.7: All-in-one media library and admin review panel"
git push origin main
```

## 5. Render environment — safe enablement order

**First**, set `LIBRARY_MEDIA_V117_ENABLED=false` (or leave it unset) and deploy the code. **Next**, confirm the Supabase migration completed. **Then** enable the release and redeploy. Preserve all other env variables and IDs.

```dotenv
LIBRARY_MEDIA_V117_ENABLED=true
LIBRARY_MEDIA_OCR_ENABLED=true
LIBRARY_MEDIA_GROUP_THUMBNAILS=true
LIBRARY_MEDIA_GROUP_DELETE=false
LIBRARY_MEDIA_MAX_BYTES=52428800
LIBRARY_MEDIA_SUBMISSION_MAX_BYTES=20971520
LIBRARY_MEDIA_PROCESS_LIMIT_BYTES=8388608

BOOK_LIBRARY_ENABLED=true
BOOK_LIBRARY_V112_ENABLED=true
BOOK_LIBRARY_V113_ENABLED=true
BOOK_LIBRARY_PRIVATE_GROUP_RESULTS=false
BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT=false
BOOK_LIBRARY_AUTO_GROUP_SEARCH=true
BOOK_LIBRARY_ALLOW_ALL_GROUPS=true
GROUP_UI_PROTECTION_ENABLED=true
GROUP_UI_TIMER_ENABLED=true
GROUP_UI_DELETE_AFTER_SECONDS=300
GROUP_BOOK_ONLY_V116_ENABLED=true
GROUP_LIBRARY_MENU_V1161_ENABLED=true
```

Set `LIBRARY_MEDIA_OCR_ENABLED=false` if the Docker OCR packages have not been installed. For selected groups only, keep your existing `BOOK_LIBRARY_GROUP_IDS` and `BOOK_LIBRARY_ALLOW_ALL_GROUPS=false`, rather than opening all groups. Preserve `BOOK_LIBRARY_CHANNEL_ID`, `BOOK_LIBRARY_REVIEW_CHANNEL_ID`, `BOOK_LIBRARY_ADMIN_IDS`, your bot username, your Supabase service-role credentials and existing Gemini/adult verification flags. **The review channel must be DIFFERENT from the public PDF storage channel.** Existing V11.5 DB cleanup migration and bot group deletion rights must already work for reliable five-minute cleanup.

### Block direct group uploads

Best protection: Telegram **group administrators → Permissions**: disable member media/document posting if the group’s policy requires it; maintain ordinary text messages for searching. Alternatively, after giving the bot Delete Messages rights, set `LIBRARY_MEDIA_GROUP_DELETE=true` to attempt to delete member-posted media through the bot. This is not retroactive and can fail due to Telegram permissions or uptime. Restrict member permissions first; bot deletion is a supplementary measure. Avoid enabling file deletion until tested with a separate member account and moderator present.

## 6. Test real Telegram behavior

1. **Private admin:** Open bot → **More Tools** → `🛡️ Library Admin Panel`, or send `/libraryadmin`. Confirm an ordinary student does not see/operate the panel. Review Requests & Status, Pending Contributions and Analytics.
2. **Admin adds image:** `/mediaupload`; send a photo with caption (spaces around `|` recommended):

   `Arabic Grammar Chart | Lecturer | Arabic | Grammar | permission | I own this chart and authorize sharing | نحو, Arabic chart`

3. **Group search:** `/book Arabic Grammar` and `/booklatest`. See PDF/image badges and public URL buttons; if available, the first image thumbnail appears. Open result and confirm private preview → **Get File** → file copied privately. Check group result disappears after **about 300 seconds**.
4. **Community submission:** A different student opens the bot privately, sends `/booksubmit` then a file with caption:

   `My Arabic Notes | Contributor | Arabic | Grammar | I created this material and permit redistribution | Useful for beginners | نحو`

   The bot copies it into `BOOK_LIBRARY_REVIEW_CHANNEL_ID` as **pending**; nothing appears publicly. Admin reviews original and rights, optionally renames its catalog title, then approves or rejects from **More Tools → Library Admin Panel → Pending Contributions**. Contributor receives Telegram confirmation; approved media becomes searchable in the group.
5. **Requests:** Student `/bookrequest Arabic exercises` in private. Admin → Library Admin Panel → Requests & Status → Found / Uploaded / Reject. The requester should receive a status notification; `/mediarequests` shows their history.
6. **Filtering:** In a group `/book Grammar type:image lang:Arabic sort:newest`. In private `/mediafind Grammar type:pdf sort:popular`, `/medialatest`, `/mediafavorites`, `/mediareading`, `/mediapopular`.
7. **Group guard:** Try a Gemini/PDF or admin command in group. It should not execute in the group. Open bot privately and confirm previous functions still work.
8. **OCR:** After OCR enabled, upload small printed image with recognizable Tamil/Arabic/English text, then search words that appear inside. OCR output/metadata are suggestions, not automatic publish decisions.

## 7. Reference commands

| Command | Purpose |
|---|---|
| `/book phrase` | Group/private unified library search |
| `/booklatest` | Latest five from old PDF + new media collections |
| `/mediapopular` | Popular approved media (group or private) |
| `/mediafind phrase type:image lang:Tamil sort:newest` | Private advanced search |
| `/mediafavorites` | Personal media bookmarks |
| `/mediareading` | Personal reading progress |
| `/mediaprogress UUID | reading | 40` | Record an individual item’s reading progress |
| `/booksubmit` | Private student submission for review |
| `/mediamyuploads` | Private submission status |
| `/bookrequest TITLE`, `/mediarequests` | Existing request system with new statuses |
| `/libraryadmin` | Private administrator panel |
| `/mediaupload`, `/mediabulk` | Admin one-file or bulk media uploads |
| `/libraryrename UUID | New Title` | Rename **catalog title** (not original Telegram filename) |
| `/libraryedit UUID | category | Education` | Edit allowed metadata |
| `/libraryhide UUID`, `/libraryrestore UUID` | Admin visibility control |
| `/libraryaudit` | Recent admin actions |
| `/mediacancel` | Cancel an in-progress upload session |

**Limitations:** The same file cannot be delivered to a bot private chat until the user has started the bot. Telegram does not notify a bot when a public URL button is tapped, so group result cleanup happens via the existing five-minute queue. OCR and PDF thumbnails are resource-limited and optional. Image query result lists are Telegram text/buttons plus a first-result cover, not a native visual grid. Automatic transliteration has a small built-in alias set; the admin can add aliases for other cross-language searches. Popularity is calculated for new media from anonymous delivery events; existing book statistics remain in their original system. ZIP files are not scanned for malware; review trusted sources only. Bulk ZIP import is intentionally capped and basic, not a substitute for manual metadata/rights checking.

## 8. Safe rollback

If there is a live problem: set **`LIBRARY_MEDIA_V117_ENABLED=false`**, then redeploy. The original group book search and legacy private tools run as before. Keep the additive SQL tables and existing library items while investigating; do **not** delete old records, storage channels, or earlier scripts. If you intentionally need code rollback, restore only the five files from the `V117_LIBRARY_BACKUP_*` folder or revert the V11.7 Git commit. Docker OCR can remain installed with the feature disabled.

**Validation scope:** 310 offline tests were run against a constructed V11.6.1 baseline; **no live Render, Telegram group, private storage channel or Supabase production migration has been performed by the assistant**. Verify the checklist yourself before declaring the deployment live.
