# V12.0.2 — Export Reliability, Worldwide Clocks & 68 Tools (Development Patch)

Target: your existing StudentAssistantBot (Python/Flask, Telegram, Render).
Requires the V12.0.1 **62-tool** QA rebuild already applied locally.
**Do not push or deploy if any check fails.**

## What this changes

- **Six new real browser tools**: JSON Formatter, Base64 Text, Text Difference, Attendance Planner, Weighted Grades, CSV Inspector.
- **World Clock:** 247 ISO-coded countries/territories and 418 named IANA time-zone entries. Search by country, city or time-zone ID, add up to 30 clocks, remove or reset, switch 12/24 h. Time and DST computed using device Intl, not an external API. Time-zone rules depend on the device's updated browser. Saved choices stay on the device (session-only for guests).
- **PNG/JPEG export:** replaces the one-click `blob:` download assumption. After preparing an image or signature, users see a preview and three choices:
  - **Download to device:** direct local browser request (may be blocked by Telegram).
  - **Share / Save to Files:** native device share sheet if supported (no upload).
  - **Save via Telegram (temporary upload):** **explicitly transfers** the exported file to this bot's Render server via HTTPS, makes a 5-minute capability URL, and calls `Telegram.WebApp.downloadFile`. A temporary HTTPS link is displayed as a fallback.
- The temporary export endpoint permits only PNG/JPEG/WebP, checks file signatures, limits each to **8 MiB**, caps RAM use at **32 MiB**, and rate-limits uploads. File links expire after 5 minutes; memory is lazily cleared on subsequent cache activity or server restart. Anonymous URL holders with the link can download until expiry. Files are not persisted to Supabase or disk.
- Existing `/library`, admin tools, private task APIs and signed Telegram authentication are not deliberately changed. Requires your existing `SUPER_MINIAPP_V120_PUBLIC_TOOLS=true`.
- Adds a **single backend registration line** to `super_miniapp_v120.py` rather than replacing your current security/authentication code.
- No new API key, dependency, Supabase SQL or Render environment variable.

## Installation: VS Code PowerShell

1. Finish any in-progress Smart Bulk session using `/mediabulkdone` before a production restart.
2. Extract this ZIP **into** `C:\Users\Pros\Desktop\StudentAssistantBot`, preserving the `V120_2_PAYLOAD` folder.
3. Run:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python INSTALL_V120_2_EXPORT_CLOCK.py --check
```

`CHECK OK` must show only V12.0.2 frontend, four existing JS tests, the new export module, two new test files, and one registration in `super_miniapp_v120.py`.

The installer checks SHA-256 of existing V12.0.1 assets and **refuses unknown changes**. If you receive a hash/source error, **do not force it**; share the message and the relevant diff first.

4. If check passes:

```powershell
python INSTALL_V120_2_EXPORT_CLOCK.py --apply
python -m py_compile super_miniapp_v120.py super_miniapp_v120_exports.py
node --test TEST_SUPER_TOOLS_V120.mjs TEST_SUPER_TOOLS_EXPANSION_V120.mjs TEST_SUPER_LOCALE_PLANNER_V120.mjs TEST_SUPER_TASK_SYNC_V120.mjs TEST_V120_REBUILT_TOOLS.mjs TEST_V120_2_EXPORT_WORLD.mjs
python -X utf8 -m unittest TEST_V120_2_EXPORT_CLOCK -q
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

Expected JS tests: **81/81**. Python and full regression must also pass on your Windows installation before a commit.

## Security and operational limitations

- The **local/Share** buttons do **not** send files anywhere. The Telegram-native option **does upload** a file to the bot's own server in response to a direct button tap. Make this clear to users for sensitive photos/signatures.
- Telegram's native `downloadFile` requires a public HTTPS file URL and `Content-Disposition: attachment` (plus `Access-Control-Allow-Origin` for Telegram Web). Source: https://core.telegram.org/bots/webapps
- The download cache is **in memory in a single Flask/Gunicorn worker**. Your current one-worker Gunicorn setting is appropriate. More than one worker, service restarts or RAM pressure may cause short-lived links to stop working. For multi-worker scale use durable object storage with automatic expiry.
- A returned download prompt acceptance is **not proof the file saved**. Users must check their Downloads folder or chosen Files destination.
- Without mobile Telegram test, native download compatibility and local storage behavior are not guaranteed.
- The World Clock directory uses IANA `zone.tab`, and the browser's own `Intl.DateTimeFormat` supplies time and daylight-saving offsets. Country names/zone mapping may change over time.
- Existing personal task sync still requires a valid signed Telegram session; guest calculations require none.
- The installer creates timestamped copies of modified files in `V120_2_EXPORT_CLOCK_BACKUP_*` (do not commit these).

## Deployment after tests

Use **selective staging only**, never `git add .`:

```powershell
git add -- super_miniapp_v120.py super_miniapp_v120_exports.py super_miniapp_v120.js super_miniapp_v120_tools.mjs super_miniapp_v120.css TEST_SUPER_TOOLS_V120.mjs TEST_SUPER_TOOLS_EXPANSION_V120.mjs TEST_SUPER_LOCALE_PLANNER_V120.mjs TEST_V120_REBUILT_TOOLS.mjs TEST_V120_2_EXPORT_WORLD.mjs TEST_V120_2_EXPORT_CLOCK.py
git diff --cached --check
git diff --cached --stat
git diff --cached -- super_miniapp_v120.py
```

Verify the diff before `git commit` and `git push origin main`. If Render auto deploys, it will restart the current process; finish Smart Bulk first.

## Live Telegram acceptance tests

1. Open `/superapp` with public tools configured.
2. **World Clock**: search `Maldives` and `United States`, add/remove clocks; verify date/day changes.
3. **Signature Pad**: draw → Prepare PNG → **Save via Telegram** → accept download → check actual Downloads/Files. Try **Share / Save to Files** as well.
4. **Image Watermark**: select a non-sensitive sample photo → Process image → Save via Telegram → check actual exported PNG contains watermark.
5. **Image Compression**: choose image and quality → process → save JPEG; inspect quality and dimensions.
6. Test all six new tools with realistic inputs. Check the 50+ older tools and existing Library still work.
7. Test public guest calculator access and ensure `/app/api/tasks` still blocks requests with missing/invalid Telegram signatures.
8. Check Render logs for errors. Never share raw `initData`, bot tokens, or private images.

No changes are deployed by this ZIP itself. Do not announce production completion until the phone tests pass.
