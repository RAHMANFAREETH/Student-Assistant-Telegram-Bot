# V11.8.8.4 — Unlimited Smart Bulk + Optional Group Welcome

## Scope
This package includes **two separate guarded patches**, to apply in this order:
1. `PATCH_UNLIMITED_BULK_V11883.py` — removes the 100-file and two-hour app session cutoffs. Changes `library_smart_bulk_v1188.py` and its test only. The session still lives in Render memory; restarts lose it. `/mediabulkdone` saves the summary and closes the session; `/mediacancel` also closes it. Large files still use Telegram-to-Telegram copying, subject to platform constraints. This patch is idempotent.
2. `PATCH_GROUP_WELCOME_V11884.py` — installs `group_welcome_v11884.py` immediately after the existing V11.6 group gate in `main.py`. Welcome is feature-flagged OFF by default. Original `main.py` is backed up. This installer is idempotent.

## Installation — Windows PowerShell
Extract the ZIP into the existing project folder. **Do not overwrite unrelated files.**

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 PATCH_UNLIMITED_BULK_V11883.py --check
python -X utf8 PATCH_UNLIMITED_BULK_V11883.py --apply
python -X utf8 PATCH_GROUP_WELCOME_V11884.py --check
python -X utf8 PATCH_GROUP_WELCOME_V11884.py --apply
python -m py_compile main.py group_welcome_v11884.py library_smart_bulk_v1188.py
python -X utf8 -m unittest TEST_GROUP_WELCOME_V11884 TEST_SMART_BULK_V1188 TEST_GROUP_BOOK_ONLY_V116 TEST_GROUP_UI_V115 -q
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

If any command fails, stop; do not deploy. Testing has to be repeated locally in Windows Python 3.14. Existing test-only negative-path tracebacks in stdout are acceptable only if unittest ends in OK.

## Enable after safe GitHub commit + Render deployment

Render environment:

```env
GROUP_WELCOME_V11884_ENABLED=true
GROUP_WELCOME_AUTO_DELETE_V11884=true
```

These **existing flags** are needed to allow Book Library group search and related welcome announcements:

```env
GROUP_BOOK_ONLY_V116_ENABLED=true
BOOK_LIBRARY_ENABLED=true
```

Your group must also be on the configured `BOOK_LIBRARY_GROUP_IDS` list, or `BOOK_LIBRARY_ALLOW_ALL_GROUPS=true` (only if deliberately chosen by admin). **Do not relax these settings merely to activate welcome messages.** In general, keep your existing adult eligibility checks enabled.

`GROUP_WELCOME_AUTO_DELETE_V11884=true` queues deletion via the **existing** V11.5 group cleanup system **only if `GROUP_UI_TIMER_ENABLED=true` and the bot has Delete Messages permission**. Cleanup is otherwise unavailable; the welcome remains until manually deleted. `GROUP_UI_DELETE_AFTER_SECONDS` controls the existing retention timer, normally 300s. There is no separate timer worker.

## Welcome examples

`👋 Welcome to our Digital Library, @reader_11! 📚`

`🔎 HOW TO SEARCH FOR BOOKS`

`1️⃣ Send /book Quran to search by title.`

`2️⃣ If plain-text search is enabled, you can also type Quran.`

`3️⃣ Another example: /book The Psychology of Money`

`4️⃣ Use /booklatest for recent books.`

`📩 Tap a result to open the bot and receive the file privately.`

`🤖 Bot: https://t.me/Student_Sl_Assistant_bot`

`🔞 Service is for eligible users aged 18+. Access rules apply.`

## Deployment
Only stage **production** files that are intended to change, after inspecting diff:

```powershell
git diff -- main.py library_smart_bulk_v1188.py
git add -- main.py library_smart_bulk_v1188.py group_welcome_v11884.py
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "Add unlimited smart bulk and group welcome V11.8.8.4"
git push origin main
```

Do **not** `git add .`. Do not push tests/installer or credentials unless needed and reviewed.

## Live checks
- Confirm the Render deployed commit and settings.
- Join an approved group with a test Telegram user (18+), confirm a single personalized welcome.
- Test `/book Quran`, `/booklatest`, and a book link delivering privately as before.
- Confirm group welcome ignores duplicate join events and unrelated groups.
- Check welcome cleanup if enabled.
- Start `/mediabulk`, select legitimate shared rights, forward >100 files in small Telegram batches, then explicitly finish with `/mediabulkdone` and verify final summary. Check upload and rights constraints.

### Limitations
This feature cannot know a person's age from their Telegram account and does not grant access to protected functions or files. Welcome messages are not private messages. Bot presence, permissions, Telegram service events, and Telegram's platform constraints still apply. Unlimited Smart Bulk sessions are not durable across Render restarts and metadata still must be accurate.
