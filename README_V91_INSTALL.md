# Student Assistant Telegram Bot V9.1 — Automatic 18+ Eligibility (Yoti candidate)

**Status:** offline-tested integration candidate. Not a live Yoti-approved production release.

This update adds `/verify_adult` (opt-in hosted age check) and `/access_status` (server-side result check). It reuses the existing `STUDY_ACCESS_MODE=verified_adults` logic and `study_verified_adults` Supabase table. **It does not bypass age checks and does not make the bot public by itself.**

## Before starting

1. **Confirm Yoti is commercially and technically suitable** for your users, including Sri Lanka and their accepted age-verification methods, costs, consent handling and privacy/legal requirements. Register a business/service via https://hub.yoti.com/get-started, create an **Age checks → Age verification** service, obtain SDK ID and API key. These are not provided in this ZIP. See https://developers.yoti.com/age-verification/onboarding.
2. Save the deployed GitHub commit ID; back up your production Supabase database.
3. Keep existing `STUDY_ACCESS_MODE=pilot` and `V91_AGE_VERIFY_ENABLED=false` until an end-to-end Yoti test succeeds.
4. The latest V8, V9, and `study_access_v9.py` modules, verified-adult SQL, Flask, `requests`, `telebot` and server-only Supabase **secret key** are required. This does NOT replace the rest of your bot.

## Installation without overwriting unrelated features

Unzip and copy `age_verification_v91.py`, `SQL_V91_AGE_SESSIONS.sql`, `TEST_V91_AUTO_AGE.py`, and `INSTALL_V91_AUTO_AGE.py` into the root alongside `main.py`.

```powershell
python INSTALL_V91_AUTO_AGE.py --check
python -m unittest TEST_V91_AUTO_AGE -q
```

If checks pass and the planned diff adds the small V9.1 registration blocks only:

```powershell
python INSTALL_V91_AUTO_AGE.py --apply
python -m py_compile age_verification_v91.py main.py
python -m unittest TEST_V91_AUTO_AGE -q
```

Run your existing full V7–V9 regression suite too. Then open Supabase SQL Editor and run `SQL_V91_AGE_SESSIONS.sql` **once**, after backing up the database. This creates a new server-only `study_age_sessions` table and does not modify the existing `study_verified_adults` records.

## Render setup — disabled until provider onboarding

```dotenv
V8_ENABLED=true
V9_ENABLED=true
STUDY_ACCESS_MODE=pilot
V91_AGE_VERIFY_ENABLED=false
V8_PUBLIC_URL=https://your-existing-service.onrender.com
YOTI_AGE_SDK_ID=<SDK UUID from Yoti Hub>
YOTI_AGE_API_KEY=<API bearer token from Yoti Hub>
```

**Do not commit API keys to GitHub or paste them into chat.** Save Yoti credentials only as Render environment variables.

After provider onboarding, with a small known-adult test group, enable `V91_AGE_VERIFY_ENABLED=true` **while keeping `STUDY_ACCESS_MODE=pilot`**. Test `/verify_adult` and `/access_status` in private Telegram chat. A completed provider result should create a `verified` `trusted_provider` record; failures must not grant access.

When you have confirmed country availability, charges, provider result formats and consent, switch to `STUDY_ACCESS_MODE=verified_adults` on Render. At that point, unverified users will **not** have V8/V9 access until they complete the process; they should use `/verify_adult`. Keep a rollback path to `pilot` for the operator.

## Commands and privacy

- `/verify_adult`: only usable in a private chat; asks for opt-in and then creates a 15-minute Yoti-hosted verification link (maximum 3 starts per day per user).
- `/access_status`: checks the pending result **directly from the Yoti API** and, only if valid, stores an adult eligibility record for 90 days.
- `/v8`, `/v9`: still controlled by the existing `allowed()` checks. They require `STUDY_ACCESS_MODE=verified_adults` and an active record for broader access.
- Never send passports, selfies or identification photos directly to this bot. Those go only through the provider's hosted experience. The app stores a random provider session reference, account mapping, expiry and a yes/no eligibility record; it does not store birthdates, identity documents, or biometric files.
- A web/browser callback never grants access: users must request `/access_status` through their authenticated Telegram account.
- The link is a bearer session; don't forward it. Provider age verification cannot fully prevent a user from handing their link to someone else. More stringent account binding would be needed for higher-assurance use.
- The operator should publish a privacy notice, explain any Yoti collection/retention and user rights, and arrange appropriate removal of expired session references. For instance, review and run `DELETE FROM public.study_age_sessions WHERE expires_at < NOW() - INTERVAL '7 days';` as a service-role maintenance operation only after evaluating operational needs.

## Staging, optional after all tests pass

```powershell
git status -sb
git add -- main.py age_verification_v91.py SQL_V91_AGE_SESSIONS.sql TEST_V91_AUTO_AGE.py INSTALL_V91_AUTO_AGE.py
git diff --cached --check
git diff --cached --name-only
```

**Do not stage unrelated backup folders, `.env` or changes to existing V8/V9 files.** Check staged diff for secrets, then commit and push only when end-to-end testing and the provider agreement are ready.

## Known limits

- Tests mock Yoti and Supabase; **no live provider verification**, Render deploy, or local country's provider document acceptance has been proven.
- An age-check provider generally involves fees and organizational onboarding; do not assume free access.
- This is deliberately an **18+ self-service verification flow**, not unrestricted public access, and it does not substitute for validating eligibility under your AI providers' terms.
- The implementation polls when a student runs `/access_status`; it does not use webhook notifications. No automatic Telegram notification is sent upon completion.
- Cross-process request coalescing and stronger per-IP abuse controls should be reviewed before opening access at scale. Session attempts are bounded per-account in Supabase but concurrency could create multiple provider sessions.
- This update does not add a global age gate for pre-existing V7 tools; it only integrates with the existing V8/V9 authorization mode.
