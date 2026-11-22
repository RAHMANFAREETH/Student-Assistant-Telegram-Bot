# Student Assistant V13.4 — CloudBridge + all-ages student access

**Upgrade candidate; not a production deployment.** Base: owner-uploaded `StudentAssistantBot(9).zip`, V13.3 checkout (HEAD `2056552`). This release packages changed files only. It neither overwrites unrelated files nor includes database credentials, `.git`, local backups or compiled caches.

## What's included

- CloudBridge: signed Telegram `/cloud` Mini App with English/Tamil/Sinhala interface; per-user Google Drive, OneDrive and Dropbox OAuth connections; URL/cloud → cloud/Telegram; Telegram file reply → cloud with `/cloudpush`; `/cloudstatus`.
- Server-side encryption of OAuth tokens, per-user query scoping, one-time OAuth state, durable job queue, idempotent request IDs, owner-only cancel/retry/history deletion, Supabase row-level security, atomic job claims and fail-closed database behavior.
- All-ages access for ordinary V8/V9/V10/V10.1 study utilities, Book Library and the private Super Mini App; no `study_verified_adults` query needed to open these tools. Telegram HMAC, private-chat checks, admin permissions, quotas, explicit consent and standard safety rules remain.
- Legacy adult-registration commands become informative no-ops. Historical verification records and tables are retained; no destructive database migration.
- **Gemini API is NOT opened to minors.** Google Gemini API terms effective March 23, 2026 prohibit using it inside apps likely to be accessed by under-18s. The pre-existing `v10_gemini.validate` gate and independent adult pilot remain unchanged. Ordinary study features may run without Gemini. Review every other AI provider's suitability and terms before public enablement. See https://ai.google.dev/gemini-api/terms.

## Important technical limits

- Default per-job download/staging cap: 100 MiB (`CLOUDBRIDGE_MAX_MB`, hard cap 1024 MiB). Render temporary storage, provider quotas and API limits still apply. **This is not an unlimited/4GB Telegram download service.** Hosted Telegram Bot API file downloads are restricted to approximately 20 MB; current send path applies a 49 MB cap. Telegram-to-Telegram file-copy functions from existing releases are unaffected.
- Google Drive currently supports file uploads to the root folder (one filename), not nested folder paths; Google `drive.file` scope only grants access to files permitted for this app, not an arbitrary existing Drive library. Google Docs-native files require export first.
- OneDrive and Dropbox accept path-based uploads; Google/OneDrive sources are provider item IDs; Dropbox source is `/path/file`. OAuth scopes must be approved/configured per provider. Some provider features may require app verification.
- Website source is **HTTPS direct file download only**; no webpage crawling, credential bypass, pirate streaming, captchas, or conversion. DNS is pinned to a public IP with certificate verification and redirect validation.
- Workers require uptime. A sleeping Render web instance cannot guarantee a job starts immediately. `CLOUDBRIDGE_WORKER_ENABLED` is disabled by default; an always-on dedicated worker is recommended for reliable operation. Atomic database claims allow multiple workers, but jobs interrupted during remote upload must be manually reviewed before requeueing.
- Provider OAuth and real file transfers have not been tested with live accounts in the supplied workspace. They are implemented against documented API contracts but require provider-specific staging verification before public rollout.

## Safe installation on Windows

1. **Back up the current project** and confirm it matches the uploaded V13.3 snapshot. Do not unzip this package over your existing project. Extract the upgrade ZIP to a separate Downloads folder.
2. Open PowerShell in the extracted upgrade folder:

   ```powershell
   py -3 INSTALL_V134_CLOUDBRIDGE.py --check --target "C:\Users\Pros\Desktop\StudentAssistantBot"
   ```

   Every entry must show `READY` or `INSTALLED`. `CONFLICT` means the project has newer/local edits; review them instead of force-overwriting.
3. After inspection, apply:

   ```powershell
   py -3 INSTALL_V134_CLOUDBRIDGE.py --apply --target "C:\Users\Pros\Desktop\StudentAssistantBot"
   ```

   Installer copies originals into `V134_BACKUP_*` and changes only the exact files in the package. It is idempotent on a matching snapshot. A `--rollback --backup "C:\...\V134_BACKUP_..."` restores those exact originals if nothing changed since installation. **Do not delete the backup before verifying.**
4. In the project environment install dependencies, run tests and check the existing bot's unrelated functions:

   ```powershell
   cd "C:\Users\Pros\Desktop\StudentAssistantBot"
   py -3 -m pip install -r requirements.txt
   py -3 -m unittest TEST_CLOUDBRIDGE_V134 TEST_STUDENT_ALL_AGES_V134 -v
   node --check cloudbridge_v134.js
   ```

   Existing legacy test cases asserting adult-only behavior must be rebaselined to the newly approved all-ages behavior. Do not misrepresent those as new application regressions.

## Supabase staging migration (review before production)

Back up Supabase first. Run `SQL_CLOUDBRIDGE_V134.sql` in a **staging** project. It creates three private tables, two privileged RPC functions and queue triggers. Ensure the bot uses a server-side service-role key (`SUPABASE_SECRET_KEY` in the existing project); never embed it in JavaScript or Telegram messages.

### Render environment (values are illustrative, never commit credentials)

```text
CLOUDBRIDGE_V134_ENABLED=false
CLOUDBRIDGE_WORKER_ENABLED=false
CLOUDBRIDGE_PUBLIC_URL=https://YOUR-RENDER-SERVICE.onrender.com
CLOUDBRIDGE_MAX_MB=100
CLOUDBRIDGE_FERNET_KEY=YOUR_GENERATED_FERNET_KEY
CLOUDBRIDGE_GOOGLE_CLIENT_ID=
CLOUDBRIDGE_GOOGLE_CLIENT_SECRET=
CLOUDBRIDGE_ONEDRIVE_CLIENT_ID=
CLOUDBRIDGE_ONEDRIVE_CLIENT_SECRET=
CLOUDBRIDGE_DROPBOX_CLIENT_ID=
CLOUDBRIDGE_DROPBOX_CLIENT_SECRET=
```

Generate the Fernet key **once, privately** and store in Render Environment:

```powershell
py -3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Do not rotate the key without first re-encrypting existing account tokens, or linked accounts will require reconnection. For each OAuth app register this exact redirect URI:

```text
https://YOUR-RENDER-SERVICE.onrender.com/cloud/oauth/callback
```

Google: Drive `drive.file` scope. Microsoft: delegated `offline_access`, `Files.ReadWrite`, `User.Read` permissions. Dropbox: files content read/write and offline refresh tokens. Consult each provider's current console permission requirements.

Enable features only after staging tests. For the existing Super Mini App also configure its existing feature/launch switches as appropriate. The new all-ages access code does not silently turn on disabled features or silently publish a service.

## Telegram steps after authorized staging deployment

1. Start a private chat with `@Student_Sl_Assistant_bot` and send `/cloud`.
2. Connect each provider through the official consent page, return to the Mini App and press Refresh.
3. Submit a small public HTTPS test file to your own Telegram chat, inspect exact bytes.
4. Test provider → Telegram, URL → provider and cloud → cloud; confirm both endpoints are owned by the same Telegram user.
5. Reply to your own 1 MB PDF with `/cloudpush dropbox /test/test.pdf`; verify destination and cancel/retry behavior.
6. Use a second Telegram test account to confirm linked accounts and job history are not visible or controllable across accounts.
7. Simulate database outage, OAuth expiry, cancellation during upload, slow connections and worker restart. Review unknown-state jobs before any retry.
8. Only then consider enabling `CLOUDBRIDGE_V134_ENABLED=true` and a worker in production, with owner approval and a rollback window.

### Verified locally in this candidate

`TEST_CLOUDBRIDGE_V134`: 18 tests; `TEST_STUDENT_ALL_AGES_V134`: 6 tests; legacy JavaScript suite: 168 tests; Python compile and JavaScript syntax checks. Real third-party OAuth, production database migration and end-to-end Telegram file sending remain unverified.
