# V11.9.1 — Smart Admin & Group Helper + Concurrent Webhook Tuning

**Install on top of the working V11.9 release (`b2bc30d` or later), not an older version.** Reuses your current bot, Render service, Supabase feedback and book-request tables. No second bot is required. The patch does not grant access to unverified users.

## Features included

1. **Group moderation (optional):** per-user/group anti-flood and suspicious-link warning logic. Disabled by default; deletion disabled by default, even when moderation is enabled. Legitimate bot/library links allowed. Group administrators are excluded when membership can be checked. Telegram group privacy settings and bot permissions affect which messages are visible.
2. **Feedback notifications (optional):** after `friendly_v119.feedback` successfully saves to Supabase, a best-effort admin-chat notification can be queued. `/feedbackqueue` remains the durable review source.
3. **Book-request notifications (optional):** after `book_library_v113_store.add_book_request` saves, queue an admin alert. `/bookrequests` and `/bookrequestresolve` remain authoritative.
4. **New-member assistance:** reuse existing V11.8.8.4 personalized group welcome and V11.9 Arabic greeting. New `/groupguide` quickly explains how to search and receive files.
5. **Group help:** `/groupguide` (or existing `/grouphelp`) in approved library groups; no extra bot.
6. **User problem reports:** `/reportproblem DESCRIPTION` privately saves to the V11.9 feedback table (requires adult eligibility).
7. **Admin hub and monitoring:** `/adminhub`, `/adminrequests`, `/adminload`, `/adminwarnings`, `/adminalerts`, `/adminhubid`, `/admintestalert`; existing `/feedbackqueue`, `/reviewqueue`, `/friendadmin` and `/libraryadmin` are reused.
8. **Operational alerts:** optional best-effort admin-chat notifications for feedback, book requests and selected webhook failures. Render logs remain the primary error record.
9. **Multi-user capacity tuning:** Gunicorn retains **one worker**, with `BOT_WEB_THREADS` default 8 instead of hard-coded 4. Webhook handling remains synchronous within each Gunicorn request, preserving Telegram's retry behaviour for non-2xx responses. No unlimited throughput or guaranteed ordering is promised.

## Install — Windows PowerShell

Extract the ZIP into the **existing** `C:\Users\Pros\Desktop\StudentAssistantBot` folder. Only ZIP files from a trusted source should be extracted.

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 INSTALL_ADMIN_GROUP_PERFORMANCE_V1191.py --check
python -X utf8 INSTALL_ADMIN_GROUP_PERFORMANCE_V1191.py --apply
python -m py_compile main.py friendly_v119.py book_library_v113_store.py group_admin_helper_v1191.py
python -X utf8 -m unittest TEST_ADMIN_GROUP_PERFORMANCE_V1191 TEST_FRIENDLY_V119 TEST_GROUP_WELCOME_V11884 TEST_GROUP_BOOK_ONLY_V116 -q
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

**Stop on any error.** This patch is idempotent, backs up originals, and only modifies `main.py`, `friendly_v119.py`, `book_library_v113_store.py`, and `Dockerfile`. Adds `group_admin_helper_v1191.py`. Existing settings, access restrictions, file handling, and Supabase schema are unchanged.

## GitHub — commit only production files

```powershell
git status --short
git add -- main.py friendly_v119.py book_library_v113_store.py Dockerfile group_admin_helper_v1191.py
git diff --cached --check
git diff --cached --stat
git diff --cached --name-only
git diff --cached
# Only after reviewing all staged changes:
git commit -m "Add V11.9.1 Smart Admin Group Helper and webhook capacity"
git push origin main
```

Do not run `git add .`; do not commit credentials, local sessions, backups, or exported reports. Confirm Render actually deployed the new commit before enabling the helper.

## Render configuration (after deployment & tests)

Required for new helper:

```env
GROUP_HELPER_V1191_ENABLED=true
BOT_WEB_THREADS=8
```

Optional admin notifications and moderating **your approved library groups only**:

```env
GROUP_HELPER_ADMIN_CHAT_ID=-100YOUR_PRIVATE_ADMIN_GROUP_ID
GROUP_HELPER_MODERATION_ENABLED=false
GROUP_HELPER_FLOOD_THRESHOLD=9
GROUP_HELPER_LINK_WARNINGS_ENABLED=false
GROUP_HELPER_DELETE_ENABLED=false
GROUP_HELPER_WARN_IN_GROUP_ENABLED=false
GROUP_HELPER_ERROR_ALERTS_ENABLED=false
```

`GROUP_HELPER_ADMIN_CHAT_ID` must be a **numeric** Telegram chat ID (do not use literal `-100YOUR...`). Create a private admin group, add the **existing** Student Assistant Bot with permission to post, and as an authorized bot administrator send `/adminhubid` inside the group to get the ID. This is **not** your existing Student Assistant Book Reviews channel unless you specifically choose that destination; a dedicated private admin group avoids mixing unrelated content.

Configure the numeric ID on Render, redeploy, then send `/admintestalert` in the bot's private admin chat. The test message should appear in your chosen admin group. Access to the group should be limited to trusted administrators because notifications can contain a user ID and submitted feedback text.

Use `/adminhub` to see admin commands. `/adminload` is private and reports active requests, peak, total processed, HTTP errors and sample p95 latency **only for this process since restart**. `/adminalerts` and `/adminwarnings` are also process-local. The actual feedback and book-request queues remain in Supabase.

Enable moderation **only after** verifying group scope and behavior; with warning/deletion disabled it will record local flood events but not delete messages. Test first with `GROUP_HELPER_MODERATION_ENABLED=true`, then only turn on deletion if genuinely wanted and the bot has group admin Delete Messages permission. Admins and regular users should not be surprised by false positives. BotFather's group privacy mode and permissions determine what messages are visible to the bot.

## Performance guidance and safe concurrency

- **Current:** one Gunicorn worker, four threads, synchronous Flask Telegram webhook, stateful in-memory batch upload sessions. Four concurrent slow requests can exhaust the available request threads.
- **This patch:** one worker, eight configurable threads (`BOT_WEB_THREADS=8`) for more overlapping I/O requests; no new external services. Keep a single worker because existing bulk-upload state and callback sessions are process-local. Changes to threads don't make CPU-heavy PDFs faster, and more requests can increase Supabase/API pressure.
- **If memory rises, workers time out, or messages go out of order:** set `BOT_WEB_THREADS=4`, save and redeploy. Start by measuring from 4 to 6 to 8 during real traffic.
- **Telegram rate limits still apply**: avoid excessive messages per chat and retry `429 Too Many Requests` using Telegram's retry-after guidance where supported.
- **Do not add `--workers 2` or multiple Render replicas yet**: upload sessions and temporary callback state are not shared between processes. Doing so without Redis/Postgres-backed session state can break active sessions.
- **Future scale:** if peak load genuinely demands it, implement durable update-idempotency, distributed session state, an indexed database/search cache, and a dedicated queue/worker for CPU-heavy OCR/PDF/AI jobs before adding more instances. That architecture can incur additional hosting costs.
- **Alerts** run in a bounded memory queue, and are **best effort**, not reliable delivery. Admins must periodically check `/feedbackqueue` and `/bookrequests`. A Render restart can lose queued alerts, not the corresponding Supabase data.

## Live checks after enabling

1. Two adult-eligible users search books at the same time in an allowed group; each receives correct results, private delivery works.
2. In admin private chat, `/adminhub` and `/adminload` work. `/feedbackqueue` shows already-submitted feedback.
3. A member submits `/feedback This is very useful` and admin group receives one alert (if configured). Its record remains in Supabase.
4. A member requests a book through `/bookrequest TITLE`; verify `/bookrequests` and optional alert.
5. In allowed library group, `/groupguide` gives instructions. Existing personalized welcome works when someone joins.
6. Existing `/mediabulk`, `/mediabulkdone`, `/mediaforward` and 4 GB Telegram relay behaviour remain unchanged.
7. Inspect Render logs for errors. During 5–10 simultaneous users, compare `/adminload` and response time to old deployment. If worse, return to four threads.

This is a release candidate pending your Windows Python 3.14 complete regression, Supabase/live integration and your approval to deploy. No assertion is made that the project can handle an unlimited number of simultaneous users.
