# Student Assistant Telegram Bot V9.3 — Reliability & Access Security

**Release candidate.** Complements V9.1 manual age verification and V9.2 admin buttons. Does not replace V7, V8, V9, V9.1 or V9.2 handlers. No changes to existing verified records.

## What changes

- `/access_help`: private, plain-language onboarding instructions for users. No identity documents requested.
- `/access_health`: administrator-only private health overview: safe Render flag summaries and minimal read-only Supabase table reachability checks. It never displays credentials, table rows, Telegram IDs or student records. Requires `V93_ENABLED=true` and existing `V91_ADMIN_USER_IDS` allowlist.
- Atomic `/verify_adult` requests: optional `v93_submit_adult_request` Supabase RPC prevents simultaneous identical requests across separate Render processes, observes verified status and enforces the existing 24-hour retry cooldown. Enabled separately **only after** applying SQL.
- `/access_approve` invalid-request messages now distinguish known client errors, including blocked self-approval. Independent human age verification remains mandatory.
- Existing V9.1 and V9.2 approval, expiry, audit, and Telegram callbacks remain unchanged.

## Files (five new files, three targeted edits)

New:

1. `v93_reliability_bot.py`
2. `INSTALL_V93_RELIABILITY.py`
3. `TEST_V93_RELIABILITY.py`
4. `SQL_V93_ATOMIC_REQUESTS.sql`
5. `README_V93_RELIABILITY.md`

Installer changes **only** `main.py`, `adult_requests_v91.py`, and `v91_access_bot.py`. It refuses unexpected anchors and creates backups in a new `V93_BACKUP_*` directory.

## Safe Windows installation

In PowerShell, from `C:\Users\Pros\Desktop\StudentAssistantBot`:

1. Copy all five new files from the ZIP into this folder. **Do not overwrite** any other bot files.
2. Preview:

   ```powershell
   python INSTALL_V93_RELIABILITY.py --check
   ```

   Examine the diff. It must show only the three intended edits.

3. Apply:

   ```powershell
   python INSTALL_V93_RELIABILITY.py --apply
   ```

4. Compile and test:

   ```powershell
   python -m py_compile main.py adult_requests_v91.py v91_access_bot.py v93_reliability_bot.py
   python -m unittest TEST_V93_RELIABILITY -q
   python -m unittest TEST_V91_MANUAL_ACCESS TEST_V92_SMART_ADMIN -q
   python -m unittest TEST_V9_ADULT_ACCESS -q
   ```

   Run any other existing V8/V9 regression suites in your repository as well. If an old fixture-style test fails because it assumes an older `main.py` integration pattern, diagnose it before editing production code.

5. Review SQL in Supabase SQL Editor and run `SQL_V93_ATOMIC_REQUESTS.sql` **before** activating `V93_REQUEST_RPC_ENABLED`. It grants RPC execution only to `service_role`. It does not grant the Telegram user self-approval rights.

6. In Render, keep all existing working environment values and add:

   ```env
   V93_ENABLED=false
   V93_REQUEST_RPC_ENABLED=false
   ```

   Commit and push only the intended V9.3 changes; confirm your Render deployment is Live.

7. Enable `V93_ENABLED=true` first, Save and deploy. Test `/access_help` from a regular private user chat, and `/access_health` from an authorized admin chat. Verify three required tables are `reachable` (and the reminder table if the V9.2 worker is enabled).

8. **Only after SQL migration and live tests pass**, set `V93_REQUEST_RPC_ENABLED=true`, Save and deploy. Test two `/verify_adult` requests from a new unverified test account: first should say submitted, second pending; `/access_status` should be pending. Approval still requires a separate authorized admin and independent age verification.

## Safe deployment / Git hygiene

Your repository has older backup directories and unrelated untracked files. **Never run `git add .` or `git add -A`.** Review and stage only:

- New: `v93_reliability_bot.py`, `INSTALL_V93_RELIABILITY.py`, `TEST_V93_RELIABILITY.py`, `SQL_V93_ATOMIC_REQUESTS.sql`, `README_V93_RELIABILITY.md`.
- Selective hunks: `main.py`, `adult_requests_v91.py`, `v91_access_bot.py` using `git add -p`.

Then run `git diff --cached --check`, `git diff --cached --name-only`, inspect actual diff, commit and push.

## Troubleshooting

- `/access_health` silent: check that the V9.3 registration is in `origin/main:main.py`, Render deployed that commit, and its handler runs *before* V8/V9 stateful handlers.
- Health says table unavailable: check Render logs and the service-role Supabase configuration; do not paste secrets in chat.
- `/verify_adult` stops working after enabling atomic requests: **turn `V93_REQUEST_RPC_ENABLED=false`** to restore the previous V9.1 code path, then check that the SQL RPC exists and the Supabase schema cache has refreshed. Never retry approvals blindly.
- The expiry worker and the V9.2 dashboard are independent. Keep their flags as previously working.
- Disabling V9.3 does not override the V9.1 verified-adult permission checks. It disables the new admin diagnostic; the atomic RPC flag controls the new request path separately.

## Boundaries

- No legal identity or age verification is performed by this bot. An administrator must verify 18+ independently.
- This release does not automatically approve requests or relax the 18+ restriction.
- Health checks do not verify the whole Render deployment or guarantee notification delivery. V9.2 notifications remain best-effort while the Render service is running.
- Offline tests do not substitute for Telegram, Supabase and Render live testing.
