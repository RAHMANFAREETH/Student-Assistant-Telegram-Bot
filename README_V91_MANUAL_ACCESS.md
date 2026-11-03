# Student Assistant Bot — V9.1 Manual Adult Access (release candidate)

**Status:** source integration and offline tests completed, **not** deployed. Protects current V7/V8/V9 features; does not replace any existing bot modules. The new request interface stays **off** until enabled.

## What this adds

- `/verify_adult` or **🔐 Verify Adult Access** in More Tools: submit one private access request. A request is **not** age verification. No birthdates, identity documents, selfies or evidence are accepted by this bot.
- `/access_status`: users see whether their request is pending, rejected, inactive/expired, or independently verified; active approvals show the expiry date (UTC).
- `/access_requests`: administrator-only pending queue, limited to 10 entries in a **private** bot chat.
- `/access_approve USER_ID verified_offline [DAYS]`: administrator attests they independently checked age 18+. Defaults to **180 days**, maximum **365**. The SQL RPC checks for a pending request and atomically updates verified eligibility, request status and audit log.
- `/access_reject USER_ID` and `/access_revoke USER_ID`: administrator-only actions, with an audit trail.
- A 24-hour cooldown before a declined/revoked/expired applicant can request another review; pending requests are idempotent.
- New V9.1 access button in **More Tools** when enabled. Previously denied users can reach onboarding without an existing V8/V9 allowlist entry.

This is **manual administrator review**. It does **not** perform age verification, open the bot to everyone, or store age-evidence. The administrator needs a legitimate, independent verification procedure appropriate for their jurisdiction and users. A Telegram ID, profile, typed date of birth or “I'm 18+” assertion is not sufficient on its own.

## Files in the ZIP

- `adult_requests_v91.py` — server-only request and approval service
- `v91_access_bot.py` — Telegram private-chat handlers
- `SQL_V91_MANUAL_ADULT_ACCESS.sql` — request and audit tables and atomic privileged RPCs
- `INSTALL_V91_MANUAL_ACCESS.py` — minimal idempotent project integration
- `TEST_V91_MANUAL_ACCESS.py` — 26 focused offline tests
- `README_V91_MANUAL_ACCESS.md` — this guide

## 1. Safely integrate locally

Back up your current working repository; **do not copy the ZIP over the whole project**. Extract and place all six files alongside `main.py` in `StudentAssistantBot`.

```powershell
python INSTALL_V91_MANUAL_ACCESS.py --check
python -m unittest TEST_V91_MANUAL_ACCESS -q
```

Review the diff; it should only add registration in `main.py`, one menu button in `ui_v57.py`, and navigation handling in `navigation.py`. Then:

```powershell
python INSTALL_V91_MANUAL_ACCESS.py --apply
python -m py_compile adult_requests_v91.py v91_access_bot.py main.py navigation.py ui_v57.py
python -m unittest TEST_V91_MANUAL_ACCESS TEST_V9_ADULT_ACCESS TEST_V9_ACADEMIC_TOOLKIT TEST_V8_STUDY_LAB -q
```

Test the full V7–V9 regression suite too. The package passed **125 V8/V9/V9.1 offline tests** in a reconstructed integration copy, but **no live Telegram or Supabase integration was run**.

## 2. Database setup

Back up your existing Supabase database. It must already have `public.study_verified_adults` from the earlier V9 access migration. Open Supabase → SQL Editor and **review then run** `SQL_V91_MANUAL_ADULT_ACCESS.sql` **once**.

This creates:

- `study_adult_access_requests`
- `study_adult_access_audit`
- `v91_review_adult_request(...)` and `v91_revoke_adult_access(...)` (server-role only RPCs)

They are server-only: RLS is enabled, and public API roles do not receive table access or RPC execution permissions. Atomic review and audit avoid partial approval writes. No existing student tables are dropped or altered.

Optional read-only verification:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema='public'
  AND table_name IN ('study_adult_access_requests','study_adult_access_audit');
```

Check access from the **existing backend secret Supabase connection**. If the backend uses an anonymous key rather than `SUPABASE_SECRET_KEY` with appropriate privileges, requests and approvals will fail closed. Do not put keys in Git or chat.

## 3. Render environment (same existing service)

Start with your existing working V8/V9 setup and add:

```dotenv
V91_ACCESS_REQUESTS_ENABLED=false
V91_ADMIN_USER_IDS=YOUR_NUMERIC_TELEGRAM_ID
STUDY_ACCESS_MODE=pilot
```

Only use your own ID for `V91_ADMIN_USER_IDS`, or comma-separated IDs of **trusted administrators**. This grants *review powers*, not age-verification proof. No administrator can approve their own request using the bot; a second authorized reviewer must independently check the account, or a separately authorized verified registry enrollment process must be used. Do not bypass this by self-inserting an unverified record.

Continue to keep the existing `V8_ENABLED=true`, `V9_ENABLED=true`, existing `V8_ALLOWED_USER_IDS` (pilot IDs), and other current settings as appropriate. Save variables but don't enable V9.1 until the new Git commit is live.

## 4. Git review and staged deploy

Your project has many historical backups and unrelated local edits. **Never run `git add .`**. Review before staging:

```powershell
git status -sb
git diff --check
```

If your V9.1 tests pass, stage **only** these intended changes:

```powershell
git add -- main.py navigation.py ui_v57.py
  # (PowerShell: run the next command on its own line)
git add -- adult_requests_v91.py v91_access_bot.py SQL_V91_MANUAL_ADULT_ACCESS.sql TEST_V91_MANUAL_ACCESS.py INSTALL_V91_MANUAL_ACCESS.py

git diff --cached --name-only
git diff --cached --check
git diff --cached --stat
```

Confirm there are no secrets, backup folders, unrelated changes, or unexpected staged files. The README itself may be committed if desired. After review and complete tests, commit/push to your existing GitHub `main` branch, and confirm Render deploys that commit with `V91_ACCESS_REQUESTS_ENABLED=false`.

## 5. Test the workflow, then enable enrollment

1. Verify existing `/start`, `/v8`, `/v9`, PDF Tools and AI features with onboarding disabled.
2. Set `V91_ACCESS_REQUESTS_ENABLED=true` in Render and deploy **without changing `STUDY_ACCESS_MODE=pilot`**.
3. Test from a separate account in the bot's **private chat**: `/verify_adult` then `/access_status` → pending. Do **not** send identity documents via Telegram.
4. From an admin's private bot chat: `/access_requests`. Arrange an **independent verification** outside the Telegram bot using appropriate safeguards. Only after evidence is verified: `/access_approve USER_ID verified_offline 180`. Otherwise `/access_reject USER_ID`.
5. Check `/access_status`, expiry and audited records; test revocation with `/access_revoke USER_ID`. Verification checks are cached for up to ~15 seconds.
6. Once your own account has a genuinely verified record, other intended adult testers are approved, and integration tests pass, switch `STUDY_ACCESS_MODE=verified_adults` while retaining a tested rollback to `pilot`.

**Important:** `verified_adults` denies access to anyone without an active record, including the owner. Don't switch without an approved record and a confirmed way to administer verification. This update is for **V8/V9 gates only**, not a global age gate for older V7 tools or unrestricted use of Gemini/other AI providers.

## Security & operational notes

- Administrator actions must be in private chat and require `V91_ADMIN_USER_IDS`. Requests never grant access automatically.
- Database writes and reviews use your server-only Supabase credentials; SQL RPCs are not executable by anonymous/authenticated public clients.
- The review command uses `verified_offline` as explicit administrative attestation; **that phrase is not evidence**. Establish and document a genuine independent verification policy and a user appeal/revocation process.
- Never ask for government IDs, selfies, dates of birth or age-evidence through Telegram chat. Ensure your actual review channel is safe, and publish an appropriate privacy notice.
- Apply a backup and test rollback; change `V91_ACCESS_REQUESTS_ENABLED=false` to disable new requests without affecting V7/V8/V9.
- This is a candidate, not a production age assurance guarantee. Supabase privileges and all live Telegram workflows still require end-to-end validation.
