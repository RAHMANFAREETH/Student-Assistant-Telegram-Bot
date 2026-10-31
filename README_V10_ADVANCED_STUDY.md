# V10.0 — Gemini AI Study Lab (Student Assistant Telegram Bot)

**Release status:** optional, offline-tested candidate. This ZIP does **not** install itself or modify the user's live Render/GitHub/Supabase environment. Target: existing Flask/pyTelegramBotAPI/Render service, existing Supabase project, and existing verified-adult V8/V9 access controls. Do **not** create a second bot, Render service, or API key.

## New features and scope

| Feature | Implemented | Limitation |
| --- | --- | --- |
| Multi-document study library | PDF/DOCX/TXT upload preview, explicit `/v10save`, keyword search across indexed passages with filename and page references; owner-scoped deletion with confirmation | At most 6 files/user, 5MB/file, 45k chars and 40 chunks/document; scanned PDF requires separate OCR; **keyword** retrieval is not vector/semantic search |
| Gemini source-grounded answers | `/v10askai QUESTION` → list snippets sent → `/v10confirm_ai`; uses existing `gemini_ai_studio_v59.py` with **gemini-3.1-flash-lite** | Provider output can hallucinate. A citation tag is not proof; check the document. No full file or permanent transcript sent. |
| Adaptive revision | `/v10coach` uses existing V9 mistakes/syllabus and flashcards; `/v10coachai` optionally asks Gemini to turn these priorities into a 3-step plan after consent | Rule-based ranking; Gemini suggestions aren't factual records or predictions |
| Viva practice | `/v10viva TOPIC` offline text practice; `/v10vivaai TOPIC` asks Gemini for one source-grounded oral-exam question after consent, then `/v10answer ...` gives keyword-based feedback | No microphone speech transcription, pronunciation grading or accurate automated scoring in this release |
| Spaced review | `/v10due`, `/v10card ID`, `/v10reveal`, `/v10rate again|hard|good|easy` | V10 schedule is kept **separate** from your existing V7 spaced-repetition schedule to avoid silently changing it |

All AI calls are **disabled by default**, private-chat only, and still require current independent adult eligibility. V7/V8/V9/V9.1/V9.2/V9.3 handlers remain untouched except for the three additive registration/menu changes.

## Gemini settings: use the existing key

The project already has `gemini_ai_studio_v59.py`; **keep that file**. It reads `GEMINI_API_KEY` (fallback `GOOGLE_API_KEY`). Never paste the API key in Telegram, chat, or Git, and do not add it to `.env.example`. The V10 adapter `v10_gemini.py` reuses this existing client, so **no new Python dependency** is required.

Google's Gemini API terms restrict API clients directed toward or likely accessed by under-18 users. **Do not enable V10 Gemini on a mixed-age or self-declaration-only bot.** It checks both `STUDY_ACCESS_MODE=verified_adults` and `study_access_v9.is_verified_adult(uid)` at the moment of each AI call. A developer pilot ID does not bypass the Gemini eligibility check. All V10 tools also enforce the existing `v8_bot.allowed()` gate.

**Privacy warning:** Google's Gemini API **Free tier** can use submitted content to improve its products; paid-tier treatment differs. The bot asks separately for each AI request and shows the passages or study priorities that will be sent. Advise users not to upload/send sensitive documents; avoid sending government IDs, medical records, bank information, student identifiers, or private third-party content. If your user content is confidential, review provider data-use settings and privacy requirements before allowing AI calls.

**Costs/limits:** V10 has its own Supabase-backed daily Gemini request counter (default **4 requests per user per UTC day**, maximum configurable 10), independent of the Cloudflare AI quota. Google may additionally enforce project/model rate limits or billing. Failed provider attempts after a quota claim still count. No auto retries; at most 2 concurrent outbound requests per Render process. Disable Gemini instantly via `V10_GEMINI_ENABLED=false` and redeploy.

## Package contents (9 files)

1. `v10_bot.py` — V10 private Telegram handlers and confirmation flow.
2. `v10_engine.py` — bounded text processing, search ranking, offline study logic.
3. `v10_store.py` — user-scoped Supabase storage operations.
4. `v10_gemini.py` — existing Gemini client adapter, adult revalidation, rate limit and safe prompts.
5. `SQL_V10_ADVANCED_STUDY.sql` — four tables and the `v10_claim_gemini_quota` function.
6. `INSTALL_V10_ADVANCED_STUDY.py` — dry-run and idempotent, backup-on-apply integration.
7. `TEST_V10_ADVANCED_STUDY.py` — offline unit and Telegram-flow tests.
8. `TEST_V10_GEMINI.py` — adult-gating, quota, prompts, provider-mock tests.
9. `README_V10_ADVANCED_STUDY.md` — this guide.

### 1. Copy and validate on Windows

Back up your working `StudentAssistantBot` directory. Extract this ZIP and **copy only these nine V10 files** into:

`C:\Users\Pros\Desktop\StudentAssistantBot`

Verify your original `gemini_ai_studio_v59.py` and `study_access_v9.py` are still present. Do not overwrite `main.py`, `navigation.py`, `ui_v57.py`, `v8_bot.py`, or other existing components with files from any older source zip.

In PowerShell:

```powershell
python INSTALL_V10_ADVANCED_STUDY.py --check
python -m unittest TEST_V10_ADVANCED_STUDY TEST_V10_GEMINI -q
```

`--check` should show **only additive** changes in `main.py`, `ui_v57.py`, and `navigation.py` and then `CHECK OK. No files changed.` The focused test suites should report **90 tests passed** for this candidate. Windows Python 3.14 Unicode tests use UTF-8 file writes; if your console ever fails to encode Unicode, try `python -X utf8 -m unittest ...`.

When you've reviewed the diff:

```powershell
python INSTALL_V10_ADVANCED_STUDY.py --apply
python INSTALL_V10_ADVANCED_STUDY.py --check
python -m py_compile main.py ui_v57.py navigation.py v10_bot.py v10_engine.py v10_store.py v10_gemini.py
python -m unittest TEST_V10_ADVANCED_STUDY TEST_V10_GEMINI -q
```

Installer backups are written to `V10_BACKUP_...` in your project; **do not commit backups**. Run previously passing V8/V9/V9.1/V9.2/V9.3 and PDF/scanner regressions separately; those tests must pass locally before deployment. The tests here do **not** send real Gemini requests, and they cannot establish your account's API quota or billing eligibility.

### 2. Supabase migration (before enabling)

Back up your database. In Supabase SQL Editor, **review** and execute the entire `SQL_V10_ADVANCED_STUDY.sql`. It adds the four tables:

- `v10_documents`
- `v10_document_chunks`
- `v10_card_schedule`
- `v10_gemini_daily_quota`

and the protected, service-role-only `v10_claim_gemini_quota(bigint, integer)` RPC. It **does not alter or drop** the V7–V9.3 tables, including `study_verified_adults`.

Verify tables and Row Level Security:

```sql
select tablename, rowsecurity
from pg_tables
where schemaname='public' and tablename in
  ('v10_documents','v10_document_chunks','v10_card_schedule','v10_gemini_daily_quota')
order by tablename;
```

All rows should show `rowsecurity = true`. The bot must use a backend Supabase service-role credential, not an `anon` key. **Never** add permissive RLS policies or expose the service-role key. On the same project, check that the quota function exists:

```sql
select proname from pg_proc
where pronamespace='public'::regnamespace
  and proname='v10_claim_gemini_quota';
```

Do not manually claim quota in SQL for production users just as a diagnostic; it changes the quota count.

### 3. Stage only V10 changes (avoid unrelated backups)

```powershell
git diff --cached --name-only
git add -- v10_bot.py v10_engine.py v10_store.py v10_gemini.py INSTALL_V10_ADVANCED_STUDY.py TEST_V10_ADVANCED_STUDY.py TEST_V10_GEMINI.py SQL_V10_ADVANCED_STUDY.sql README_V10_ADVANCED_STUDY.md
git add -p -- main.py ui_v57.py navigation.py
git diff --cached --check
git diff --cached --name-only
git diff --cached --stat
```

Review **exactly 12 V10 files**: 9 new and 3 integration edits. Do not stage older untracked files and backup folders. If the three integration files contain unrelated diffs, use patch staging and verify each hunk; **do not** use `git add .`.

After local tests and migration review:

```powershell
git commit -m "V10: Add verified-adult Gemini Study Lab"
git push origin main
```

### 4. Safe two-phase Render rollout

Before pushing, set the following on your **existing** Render service:

```dotenv
V10_ENABLED=false
V10_GEMINI_ENABLED=false
V10_GEMINI_DAILY_LIMIT=4
```

Keep all working V8/V9/V9.1–V9.3 env vars unchanged, including `STUDY_ACCESS_MODE=verified_adults`, `V91_*`, `V92_*`, `V93_*`, and `GEMINI_API_KEY`.

When Render is **Live** on the new commit and the Supabase migration is verified, enable offline V10 first:

```dotenv
V10_ENABLED=true
V10_GEMINI_ENABLED=false
```

Test `/v10`, `/v10add`, `/v10docs`, `/v10ask`, `/v10coach`, `/v10viva`, `/v10due`. Test with two separately verified adult accounts and one unapproved account to confirm data isolation. Confirm `/v8`, `/v9`, `/adult_admin`, `/access_status`, `/access_health` and legacy tools still work.

Only after verifying your Gemini key and reviewing Free-tier data-use terms, enable Gemini for a **small verified-adult pilot**:

```dotenv
V10_ENABLED=true
V10_GEMINI_ENABLED=true
V10_GEMINI_DAILY_LIMIT=4
STUDY_ACCESS_MODE=verified_adults
```

**No separate key**, `V8_AI_ASSISTED`, or Cloudflare quota is needed for V10 Gemini. The older Ask AI and V8 AI paths remain as they were; V10 `/v10askai` specifically uses Gemini. Keep the old `V10_AI_ENABLED` unset/false: it is not used in this Gemini edition.

### 5. Telegram test steps

From an independently verified adult account **in a private chat**:

| Command | Expected result |
| --- | --- |
| `/v10` | V10 study menu |
| `/v10add` → upload → `/v10save` | Explicit save; indexed excerpts now stored in Supabase |
| `/v10docs` | Your own documents only |
| `/v10ask photosynthesis` | Relevant, page-labelled excerpts (offline) |
| `/v10askai photosynthesis` | Lists short excerpts and asks for **one-time consent** |
| `/v10confirm_ai` | Gemini answer with `[S1]`/page key if enabled; consent consumed once |
| `/v10coach` / `/v10coachai` | Offline priorities / opt-in Gemini revision suggestions |
| `/v10viva gravity` / `/v10vivaai gravity` | Text question / opt-in Gemini oral-exam question |
| `/v10answer ...` | Keyword-based practice feedback |
| `/v10due` → `/v10card ID` → `/v10reveal` → `/v10rate good` | Separate due schedule saved |
| `/v10delete UUID` → `/v10confirmdelete` | Owner-scoped permanent removal |
| `/v10cancel` | Clears temporary V10 upload, consent or practice session |

Run `/v10confirm_ai` twice: the second call must say there's no pending consent and must **not** make another AI call. Test that a user in `pilot` mode (not verified) is denied Gemini, even if V10 AI toggle is on. Test invalid/expired verified records and a temporary Supabase outage. Protect all API keys and student records when sharing logs.

### Known limitations and rollback

- Offline search is lexical; source references refer to indexed text, not automatic verification of AI factual accuracy.
- Gemini model is fixed by your existing `gemini_ai_studio_v59.py` client (`gemini-3.1-flash-lite`). Test key/model availability in the Render environment; no live API test has been performed by this package.
- File storage retains excerpts until deleted; live DB/RLS and Telegram behavior must be tested.
- The V10 flashcard schedule is separate from the legacy one; don't claim synchronization.
- The Render process may be suspended; no guarantee for session continuity or schedules.
- Rapid concurrent saves or requests from two workers need live validation. V10 stores upload previews in process memory, so they can expire after a restart.
- Roll back safely by setting `V10_ENABLED=false` and `V10_GEMINI_ENABLED=false` and redeploying. Older features stay installed. Do not drop V10 tables without a reviewed data-retention plan.
