# V8 / V9 optional Verified-Adult Access — security-gated update

**This is not a turnkey public rollout or an age-verification service.** It adds an opt-in `verified_adults` mode, but a trusted provider or an authorized operator must verify eligibility and write unexpired records. The Telegram Bot API does not supply reliable adult age eligibility in normal bot updates. Self-declaration does not qualify as verification. Until you have a trustworthy onboarding/verification workflow, retain the original pilot mode.

## What changes

- Two exact-string, backup-protected edits: `v8_bot.py` (adds `STUDY_ACCESS_MODE`); `v9_bot.py` (updates denial text).
- One new `study_access_v9.py` server-side eligibility check, denying access unless an active non-expired verified record exists in Supabase; short 15-second cache, possible revocation delay.
- A SQL table `study_verified_adults` with RLS and revoked anon/authenticated privileges; **no personal identity documents stored**. Trusted verification must happen separately. Access is fail-closed when DB is unreachable.
- By default `STUDY_ACCESS_MODE=pilot` (or missing) uses `V8_ALLOWED_USER_IDS` exactly as today. `V9_ENABLED` still separately controls V9 visibility; V8 and V9 must both be enabled for V9 access.
- Applies to existing V8 Mini App API because it calls `v8_bot.allowed()`.

## Safe workflow

1. First, apply the original `INSTALL_V9_ACADEMIC_TOOLKIT.py --apply` **locally** after reviewing its existing `--check` output. Do NOT deploy until integration tests and DB migration pass.
2. Copy all five files from this archive into the same project folder.
3. Run: `python UPDATE_V9_ADULT_ACCESS.py --check` — must show `CHECK OK`.
4. Run: `python UPDATE_V9_ADULT_ACCESS.py --apply`.
5. Run: `python -m unittest TEST_V9_ADULT_ACCESS TEST_V9_ACADEMIC_TOOLKIT TEST_V8_STUDY_LAB -q`.
6. Run the complete existing PDF, OCR, Office, scanner, V7/V8 regression suite.
7. Back up Supabase first; inspect/run `SQL_V9_ACADEMIC_TOOLKIT.sql`, then `SQL_V9_ADULT_ACCESS.sql`. Do not manually grant access just because a user clicked an 18+ button.
8. Stage ONLY reviewed production files + tests, SQL migrations, installer scripts. Keep `.env`, backups, and secrets untracked. Initially deploy with `V9_ENABLED=false` and `STUDY_ACCESS_MODE=pilot` to protect your current V8 pilot.
9. Only AFTER deploying a **trusted age-verification integration**, setting verified records, testing with eligible and ineligible accounts, and checking quotas/role privileges, change `STUDY_ACCESS_MODE=verified_adults`, while keeping `V8_ENABLED=true` and `V9_ENABLED=true`.

This package does **not** enable V8/V9 access to every Telegram account. It enables access to every account whose adult eligibility has been **independently verified**, without requiring additions to `V8_ALLOWED_USER_IDS`. It also does not automatically age-restrict the legacy V7 and older features.

Current V9 features call OCR.space after explicit consent. Group quizzes and study rooms require dedicated authorization and cross-user privacy tests before broad rollout. Under the current architecture, each verified-user lookup adds a backend database call when the cache expires.
