# V11.8.2 — Distinguish Tamil / English PDFs in Library Search

Search-result buttons currently omit `language`, making distinct editions look identical. This optional display-only patch changes **only** `library_media_v117_bot.py`. It changes **no** Supabase records, file permissions, navigation, upload handlers, or storage messages. It does not add or index files that are missing from the database.

Example buttons after patch:

- `📄 English · The Psychology of Money · PDF · 2.8 MB`
- `📄 Tamil · The Psychology of Money · PDF · 37.9 MB`

These are **illustrations**, contingent on the English and Tamil catalog entries actually existing. If both search buttons refer to English catalog records, both will still say English.

## On Windows PowerShell

1. Copy `PATCH_LIBRARY_SEARCH_LABELS_V1182.py` and `TEST_LIBRARY_SEARCH_LABELS_V1182.py` into `C:\Users\Pros\Desktop\StudentAssistantBot`.
2. In the project folder, run:

```powershell
python -X utf8 PATCH_LIBRARY_SEARCH_LABELS_V1182.py --check
python -X utf8 PATCH_LIBRARY_SEARCH_LABELS_V1182.py --apply
python -m py_compile library_media_v117_bot.py
python -X utf8 -m unittest TEST_LIBRARY_SEARCH_LABELS_V1182 TEST_LIBRARY_MEDIA_V117 TEST_LIBRARY_MANAGE_V118 -q
```

3. Only after all tests pass, review `git diff -- library_media_v117_bot.py` and stage only the files you intend to ship. Production change requires deployment after your normal CI checks. A timestamped backup is created by `--apply`.

## To locate the Tamil edition now

In an allowed group, try `/book The Psychology of Money lang:Tamil`. For English try `lang:English`.

In your **private admin** chat, use `/librarymanage The Psychology of Money` (V11.8 flag must be enabled). Open each record and inspect its `Language`, original filename and file size. If no Tamil record exists in either catalog, the screenshot only proves the file exists in the Telegram channel—not that it was indexed in Supabase. You would need to add/register it through an existing authorized upload flow; don't delete or reupload anything until its catalog status has been checked. Please verify you hold sharing rights before republishing copyrighted books.
