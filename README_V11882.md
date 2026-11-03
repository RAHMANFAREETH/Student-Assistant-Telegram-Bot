# Student Assistant Telegram Bot V11.8.8.2 — Individual Forwarded Book Upload

Adds a **separate, opt-in, private administrator** method for forwarding ONE Telegram-hosted PDF/EPUB/DOCX/TXT from any accessible, unprotected channel or group, **assigning the exact title/author/language/category instead of relying on the filename**, reviewing details, and confirming publication. The administrator must have redistribution rights. It does not bypass protected Telegram content or retrieve inaccessible history.

## Requirements and safety

- Existing V11.8.8 Smart Bulk Upload and V11.8.7 Large File Relay must be installed; this add-on does not alter either implementation.
- No DB changes. No new bot. No large-file downloading. Existing `submit_media()` handles Telegram `copy_message`, duplicate detection, database catalog creation, backup cleanup and permission checks. Processing and platform limits remain unchanged.
- Opt-in setting: `LIBRARY_INDIVIDUAL_FORWARD_V11882_ENABLED=true` in the **existing Render service**, only after testing and deployment.
- Requires an approved administrator in a private bot chat. User must declare a supported license/permission and an honest rights explanation. 10-minute, process-local session (lost on service restart). No publishing before explicit command.
- Rejects ZIP and other formats outside PDF, EPUB, DOCX and TXT for this particular workflow. Existing bulk upload remains separate.
- Only file metadata is changed in the catalog; the original Telegram document name and source-channel caption are not changed.

## Installation / checks (PowerShell)

Extract ZIP files to the root of your existing project (NOT a nested folder):

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 INSTALL_INDIVIDUAL_FORWARD_V11882.py --check
python -X utf8 INSTALL_INDIVIDUAL_FORWARD_V11882.py --apply
python -m py_compile library_individual_forward_v11882.py library_media_v117_bot.py
python -X utf8 -m unittest TEST_INDIVIDUAL_FORWARD_V11882 -q
python -X utf8 -m unittest TEST_INDIVIDUAL_FORWARD_V11882 TEST_SMART_BULK_V1188 TEST_PREVIOUS_CHANNEL_IMPORT_V11881 TEST_LIBRARY_LARGE_RELAY_V1187 TEST_LIBRARY_MEDIA_V117 TEST_GROUP_BOOK_ONLY_V116 -q
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

The installer previews a unified diff with `--check`, creates a timestamped backup before editing, checks exact anchors, and is safe to rerun. It modifies **one existing production source file**: `library_media_v117_bot.py`. Its new production module is `library_individual_forward_v11882.py`. Do not run `git add .`.

Only after all tests pass on Windows Python 3.14 and you have reviewed the diff:

```powershell
git add -- library_media_v117_bot.py library_individual_forward_v11882.py
# Optional versioned test source:
git add -- TEST_INDIVIDUAL_FORWARD_V11882.py
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "Add individual Telegram document forwarding V11.8.8.2"
git push origin main
```

Then confirm deployment and add the Render environment variable:

```
LIBRARY_INDIVIDUAL_FORWARD_V11882_ENABLED=true
```

## Telegram commands (private administrator chat)

1. `/mediaforward`
2. `/mediaforwardset Sahih al-Bukhari | Imam Muhammad al-Bukhari | English | Hadith / Islamic Studies | permission | Verified distribution permission for this edition`
3. Forward a single PDF message from an authorized source. This method does NOT depend on a source-caption match; it uses the exact details from Step 2.
4. Review the bot's preview. No publication has happened yet.
5. `/mediaforwardpublish` to publish, or `/mediaforwardcancel` to discard.

**Only use the `permission` example if you genuinely have that license/authorization for the PDF edition.** For other licenses use `public_domain`, `cc0`, `cc_by`, or `cc_by_sa` when accurate. File forwarding permissions and distribution rights are different.

`/mediacancel` also clears this new session. Existing `/mediaupload` and `/mediabulk` remain available and unchanged.

## Offline test scope

The new 16 focused tests cover rights validation, UTF-8 metadata, source-caption isolation, one-file-only review, cancellation, expiration, failures/retry, and an actual 4 GiB *simulated* Telegram-to-Telegram copy-and-catalog path. This is not a live 4 GiB transfer. Run full suite in your actual installed project before release.
