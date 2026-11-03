# Student Assistant Telegram Bot — V11.8.6 combined search update

This is **one ZIP** containing BOTH requested changes. Do not install the previous V11.8.5 ZIP separately.

## What changes

1. **Language selector and file list (V11.8.5)**: two-column choices such as Malayalam, Tamil, English, Hindi, Telugu, Kannada, Gujarati, Marathi, Punjabi, Sinhala and Arabic. Selecting Tamil in the private Book Library shows matching indexed PDFs, a size/title button for each file, paging and Back to Languages. Choosing Tamil inside `/book TITLE` filters the available search-result list and shows Tamil-only file buttons.
2. **Search progress and not-found feedback (V11.8.6)**: after a valid `/book TITLE` query, display `🔎 SEARCHING FOR FILES` while the existing catalog search runs. The bot then edits the same Telegram message to show paginated results; if no matches are found, it displays `😕 NO FILES FOUND`, spelling suggestions and a Google web-search link. Server errors show an **unavailable** notice instead of a misleading no-results message.
3. **Group privacy**: individual file buttons remain deep links to private bot previews, never a bulk group attachment. Group search messages, including progress and no-match messages, use the existing 5-minute deletion queue when that feature is enabled and its worker runs.
4. **Optional group plain-text searches**: Set `BOOK_LIBRARY_AUTO_GROUP_SEARCH=true` AND `LIBRARY_SEARCH_V1186_ALL_TEXT_ENABLED=true` in Render (also requires the existing V11.6 group guard and group/adult authorization). Then an ordinary message like `hbdbfbbfj` in an approved book-search group also triggers Searching → No Files Found. This is **off by default** to prevent spam in normal group conversations. Without it, users can always search explicitly using `/book TITLE`.
5. **No artificial loading delay** is added. Telegram may display the searching message briefly when the catalog responds quickly.

## Requirements

- Your existing V11.8.3 interactive search must already be installed, as indicated by `library_search_ui_v1183.py` and `PATCH_LIBRARY_SEARCH_UI_V1183.py`.
- The V11.7 media catalog must be enabled for `/book` queries to use these unified-search results: `LIBRARY_MEDIA_V117_ENABLED=true` with the normal Book Library and group-access settings.
- This ZIP includes all V11.8.5 components; it is **not** necessary to extract V11.8.5 first.
- Do not extract backups over your source or copy the entire older project archive.

## Windows PowerShell — local installation

Extract all the files from this ZIP directly into your existing **`C:\Users\Pros\Desktop\StudentAssistantBot`** folder, allowing the new patch files to be added, then run:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"

# Preview changes (no source files modified)
python -X utf8 PATCH_LIBRARY_SEARCH_COMBINED_V1186.py --check

# Apply language UI and new search feedback together
python -X utf8 PATCH_LIBRARY_SEARCH_COMBINED_V1186.py --apply

# Verify source syntax
python -m py_compile library_media_v117_bot.py library_search_ui_v1183.py book_library_v112_bot.py group_books_only_v116.py library_language_picker_v1185.py

# Test new and existing library features (offline, no network required)
python -X utf8 -m unittest TEST_LIBRARY_SEARCH_FEEDBACK_V1186 TEST_LIBRARY_LANGUAGE_PICKER_V1185 TEST_LIBRARY_SEARCH_UI_V1183 TEST_LIBRARY_MEDIA_V117 TEST_BOOK_LIBRARY_V112 TEST_BOOK_LIBRARY_PRIVACY_V114 TEST_BOOK_LIBRARY TEST_BOOK_PUBLIC_LATEST5 TEST_GROUP_BOOK_ONLY_V116 TEST_GROUP_LIBRARY_MENU_V1161 TEST_GROUP_UI_V115 TEST_LIBRARY_MANAGE_V118 -q

# Review changes
 git status --short
 git diff --check
```

`--apply` creates `V1186_BACKUP_<timestamp>` and is safe to rerun. It modifies **four existing production library/group modules and the historical V11.8.3 installer compatibility guard**. It does not change `main.py`, PDF/OCR utilities, V8/V9 modules, SQL schema or Render environment variables. Existing tests/fixtures included in the ZIP are additional local files.

## Telegram verification after release

- In an authorized group, send `/book The Psychology of Money`. Look for searching and then the two editions (if indexed correctly) in the final result buttons.
- Search a nonexistent title such as `/book hbdbfbbfj`: check that the same status becomes a no-files-found message with spelling advice.
- Click Language → Tamil; look for Tamil-only file buttons and pagination. Check Back/Change Language.
- Click a file button and verify the existing private bot delivery. Check that the group result is deleted after the configured five-minute expiry (provided the bot has deletion permission and the cleanup worker is operating).
- In private chat: Book Library → Languages → Tamil. Confirm matching PDF files display instead of only a language label.
- If Telegram rejects editing a message, the bot sends a replacement result and attempts to remove the old searching message.

## Important: Tamil book indexing is a separate metadata issue

Your screenshots showed `Student Assistant Library (3)` where Tamil should have appeared. No UI-only change can safely infer the language of an existing indexed record. Use your existing administrator edit commands to change the correct entry's catalog language to `Tamil`, and the English entry to `English`. **Do not reupload or delete the PDFs just to fix their language.** Captions for future uploads should use `Title | Author | Language | Category`, for example `The Psychology of Money | Morgan Housel | Tamil | Finance`.

## Test status and deployment gate

- Local sandbox Python 3.13: a fresh V11.8.3 working copy passed **308 focused tests (307 passed, 1 skipped)**. Installer dry run and repeated apply were also checked.
- NOT tested against your live Telegram group, Supabase database, Render service or Windows Python 3.14.
- Your latest affected-only Windows regression run still showed failing `TEST_V8_STUDY_LAB` and `TEST_V9_ACADEMIC_TOOLKIT` modules. Review those detailed failures and verify feature-access policies before pushing/redeploying.
- Telegram's maximum search-message size and callback constraints are preserved; search result sessions remain bounded and owner-restricted.

## Rollback

Find the latest `V1186_BACKUP_...` directory created by `--apply`. Restore its copies of:

- `library_media_v117_bot.py`
- `library_search_ui_v1183.py`
- `book_library_v112_bot.py`
- `group_books_only_v116.py`
- `PATCH_LIBRARY_SEARCH_UI_V1183.py`

Stop the running bot before manually restoring production source and test the restored files before deployment. This restores the pre-update search behavior. The additional helper/test files may remain harmlessly on disk.
