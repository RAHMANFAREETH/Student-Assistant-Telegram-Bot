# Student Assistant Telegram Bot — V9.2 Smart Admin Dashboard & Security

**Release candidate — local/offline tested; NOT deployed to GitHub, Render or Supabase by this package.**

This is an **additive** update for the bot's existing V9.1 administrator-reviewed adult access. It deliberately does not replace `v91_access_bot.py`, `adult_requests_v91.py`, `study_access_v9.py`, `v8_bot.py`, `v9_bot.py`, or older student tools.

## Features

- **`/adult_admin` or `/access_admin`**: private, admin-only inline Telegram dashboard.
- **Pending requests**: browse users (8 per page), see request dates, select a request, and navigate back.
- **Approve**: requires administrator to confirm they **independently checked 18+ eligibility outside Telegram**, choose 30/90/180/365-day expiry, and press a separate **final confirmation** button. V9.1 atomic RPC saves both verification and audit. No self-approval.
- **Reject/revoke**: final confirmation, reuses audited V9.1 RPC. Self-review is prevented in dashboard.
- **Active verified users**: browse active records, expiry, verification method; revoke access.
- **Audit history**: see approvals/rejections/revocations, admin ID and timestamps from existing V9.1 table.
- **Expiry reminders**: optional hourly worker using a new leased database queue; send reminders at ~7 days, ~1 day, or shortly after expiration. Admin can also manually trigger a batch with confirmation.
- **Security**: admin allowlist verified on each command and callback; private chats only; 10-minute single-use callback tokens tied to the specific admin; database change actions remain server-side. No identity documents or birthdays requested/stored through Telegram.

**Limitations:** The bot **does not independently verify age**. Approval buttons record an administrator's attestation that an independent process has already occurred. Legacy V9.1 admin commands remain available and must be used responsibly. The optional in-process reminder worker runs only while Render's web service is awake, so **expiry alerts are best-effort, not guaranteed to arrive at exact times**. A Telegram send might be duplicated if successful delivery is followed by failed database acknowledgement; the lease prevents most duplicates. Admin buttons issued before a process restart expire safely. If you need guaranteed reminders, a reliable external scheduler/always-on worker is required.

## Contents

| File | Purpose |
| --- | --- |
| `v92_admin_bot.py` | Telegram buttons and confirmation flow |
| `v92_admin_service.py` | Protected Supabase reads and reminder handling |
| `v92_expiry_worker.py` | Optional in-process reminder loop |
| `SQL_V92_SMART_ADMIN.sql` | Additive reminders table and two protected RPCs |
| `INSTALL_V92_SMART_ADMIN.py` | Idempotent `--check`/`--apply` for main.py only |
| `TEST_V92_SMART_ADMIN.py` | Focused offline tests |
| `README_V92_SMART_ADMIN.md` | This guide |

## 1. Copy, check and test locally

1. Download ZIP and extract its 7 files to `C:\Users\Pros\Desktop\StudentAssistantBot`, alongside `main.py`. Do **not** overwrite your existing V9.1 files.
2. Open PowerShell in the project directory:

```powershell
python INSTALL_V92_SMART_ADMIN.py --check
python -m unittest TEST_V92_SMART_ADMIN -q
python -m unittest TEST_V91_MANUAL_ACCESS -q
```

`--check` should show **only one** intended addition to `main.py` immediately after `register_v91_access_handlers(bot)`. It does not change files. The V9.2 tests passed **32** focused offline tests, and the V9.1+V9.2 combined tests passed **58** in a reconstructed project. Neither is a substitute for testing your local repository.

3. If the check is exactly as expected:

```powershell
python INSTALL_V92_SMART_ADMIN.py --apply
python -m py_compile v92_admin_bot.py v92_admin_service.py v92_expiry_worker.py main.py
python -m unittest TEST_V92_SMART_ADMIN -q
python -m unittest TEST_V91_MANUAL_ACCESS -q
python -m unittest TEST_V9_ADULT_ACCESS -q
python -m unittest TEST_V9_ACADEMIC_TOOLKIT -q
python -m unittest TEST_V8_STUDY_LAB -q
```

Run legacy suites **in separate invocations** because older mock Telegram test fixtures can interfere when their suites are run together in one Python process.

The installer backs up `main.py` in a `V92_BACKUP_<timestamp>` folder, which you must **not** commit. It refuses missing/duplicate V9.1 insertion anchors. You can run the installer repeatedly.

## 2. Apply the SQL migration (Supabase)

1. Make a database backup. You must already have installed V9.1 SQL (including `study_adult_access_requests`, `study_adult_access_audit` and `study_verified_adults`).
2. Supabase Dashboard > SQL Editor > New query: review and run `SQL_V92_SMART_ADMIN.sql`.
3. It adds **only** `study_adult_expiry_notifications`, an index on the existing verified table, and two service-role-only functions: `v92_claim_expiry_notifications` and `v92_mark_expiry_notification_sent`. RLS is enabled and anonymous/authenticated clients are not granted access.
4. Check:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema='public'
  AND table_name='study_adult_expiry_notifications';

SELECT proname FROM pg_proc
WHERE proname IN ('v92_claim_expiry_notifications',
                  'v92_mark_expiry_notification_sent');
```

**Do not paste Supabase API keys into SQL Editor, chat, or GitHub.** Existing server service-role credentials are needed to call these RPCs.

## 3. Safe Git commit (your repository has many unrelated backups)

Review local changes:

```powershell
git diff -- main.py
git status -sb
```

Stage the 7 V9.2 files explicitly:

```powershell
git add -- v92_admin_bot.py v92_admin_service.py v92_expiry_worker.py
git add -- INSTALL_V92_SMART_ADMIN.py TEST_V92_SMART_ADMIN.py SQL_V92_SMART_ADMIN.sql README_V92_SMART_ADMIN.md
```

Stage **only the V9.2 hunk** in existing `main.py`:

```powershell
git add -p -- main.py
```

Answer `y` for the new V9.2 lines, `n` for unrelated edits. Verify the staged file list includes exactly the 7 new files and `main.py`:

```powershell
git diff --cached --check
git diff --cached --name-only
git diff --cached --stat
```

Only if every staged hunk is intended and tests pass:

```powershell
git commit -m "V9.2: Add secure admin dashboard and expiry reminders"
git push origin main
```

**Never `git add .`**. Avoid committing backup folders, local env files, or any credentials. GitHub auto-deploy to Render may begin after push.

## 4. Render staged rollout (same bot and existing web service)

Before the new code deploys, keep existing working V8, V9, V9.1 variables unchanged, and add:

```dotenv
V92_ADMIN_ENABLED=false
V92_EXPIRY_WORKER_ENABLED=false
```

Do not replace `V91_ADMIN_USER_IDS` or change `STUDY_ACCESS_MODE=verified_adults`. Once Render reports the new commit Live, and V7/V8/V9 and `/access_status` still work:

1. Set `V92_ADMIN_ENABLED=true`, save/deploy. Leave `V92_EXPIRY_WORKER_ENABLED=false` initially.
2. As a designated administrator, open a private bot chat and send `/adult_admin`.
3. Check **Pending requests**, **Active verified**, **Audit history**. Test a real review ONLY after independently confirming age outside Telegram; do not approve a fabricated or unverified account just to test.
4. Verify a **non-admin** user cannot open dashboard or use forwarded/old buttons.
5. Test **Run expiry reminders** after database SQL is installed. If no user is due for notification the batch should return `claimed 0`.
6. After validating reminder behavior and database permissions, optionally set `V92_EXPIRY_WORKER_ENABLED=true` and deploy. It will scan about once per hour as long as the Render service remains awake.

For a quick rollback, set both `V92_ADMIN_ENABLED=false` and `V92_EXPIRY_WORKER_ENABLED=false` and redeploy. This disables the new dashboard/reminder behavior without changing V9.1 access approvals or removing any older study tools.

## Privacy and safety

- Admin users must be explicitly trusted and independently check eligibility through an appropriate secure offline or external process. Telegram messages, IDs, self-reported birthdates, or account profiles are **not** age proof.
- Audit records contain administrator and user **Telegram numeric IDs**, timestamps, action names and expiry, not source evidence.
- Only the existing backend may read the request/audit tables; use a secure server-side Supabase service-role key. Never expose these APIs or allow public client table access.
- Expiry notices are sent only to the linked Telegram IDs, but cannot be delivered to a user who blocked the bot. They do **not** create or extend approval.
- V9.2 manages the existing V8/V9 adult access, not all older V7 functions and not any third-party AI provider's separate eligibility rules.

**Production readiness:** Offline tests and compilation must pass on *your current repository*; live Supabase RPC, Telegram callbacks, Render worker behavior and legacy feature regression still require final end-to-end validation.
