# Student Assistant V13.6 — CloudBridge large files + Telegram copy

This is an **opt-in** upgrade to the live V13.4/V13.5 bot, preserving its Study
Lab, Book Library, PDF tools, languages, age policy, private Mini App auth,
existing storage accounts, and legacy small-file transfers.

## Included in the single V13.6 release

| Action | Implementation | Important limitation |
| --- | --- | --- |
| Google Drive file → same user's Google Drive | Google `files.copy` API (server-side, no 4 GiB download) | Only files accessible to the user's `drive.file` OAuth app; copies into Drive root |
| Public HTTPS URL → user's Google Drive | Validated TLS, public-IP-pinned 206 ranges, strong ETag; 5 MiB upload chunks; encrypted resumable session in Supabase | The source **must** support byte ranges and a stable strong ETag; the worker must be online |
| Telegram file → same private Telegram chat | Reply `/cloudcopy` (Telegram `copyMessage`, no media download) | Telegram may reject protected media or enforce its own copy restrictions |
| Telegram file → managed channel/supergroup | Reply `/cloudcopy @channel` or `/cloudcopy -100...`; both user and bot must be admins (bot must be allowed to post) | Send the command **in private bot chat**, replying to an existing file there |
| Telegram file → Google Drive | Existing `/cloudpush google /file.pdf` | Still subject to **hosted Telegram Bot API's 20 MB download cap** |
| Google Drive → Telegram attachment | Existing V13.4 transfer | Still subject to **49 MiB safety cap** for new bot uploads |
| Google Drive → Telegram private link | Successful new V13.6 Drive copy/upload sends the owner a private Drive URL | Link **does not** make the file public; access depends on Google permissions |

V13.6 **does not claim** that directly uploading a *new* 4 GiB file to Telegram
works through the hosted Bot API. The user's potential Premium account upgrade
does not by itself remove the Bot API limits. Existing Telegram-hosted files can
be server-side copied using the official Bot API where Telegram permits.

### Activation order (required)

1. Back up the Supabase database. Review and run `SQL_CLOUDBRIDGE_V136.sql`
   **before deploying code**. This extends the existing jobs table; it does not
   delete existing tables, accounts, tokens, or jobs. Run the SQL once in the
   correct production project.
2. Review the GitHub pull request's files and automated tests. Merge **only
   after review**; on Render manually deploy the latest merged `main` commit.
3. Keep the original environment variables unchanged and add:

   ```dotenv
   CLOUDBRIDGE_V134_ENABLED=true
   CLOUDBRIDGE_WORKER_ENABLED=true
   CLOUDBRIDGE_V136_ENABLED=true
   CLOUDBRIDGE_MAX_MB=4096
   ```

4. Retain the original `CLOUDBRIDGE_FERNET_KEY` and Google OAuth credentials:
   **do not rotate the encryption key during resumable transfers**. Do not put
   secrets in Git or screenshots.
5. Verify normal `/start`, `☁️ CloudBridge · Google Drive`, and existing small
   transfers before running a 4 GiB pilot. Test separate 100 MiB, 1 GiB, 2 GiB,
   and 4 GiB source files (with enough Google Drive storage available).

### Private commands

- Reply to a Telegram file in **your private bot chat**: `/cloudcopy`
- Copy that file to a channel/supergroup you administer: `/cloudcopy @mychannel`
- Upload a small Telegram file: `/cloudpush google /original_name.pdf`
- Check recent transfers: `/cloudstatus`
- Open Mini App: `/cloud`

For large transfers, choose `Cloud file` (Google Drive file ID) or `HTTPS website
URL` as the source and `Cloud account` → `Google Drive` as the destination.
Select a root destination path such as `/Large_Archive.zip` and set the file
name. The Mini App displays transfer progress and exposes Pause/Resume for
resumable HTTPS-to-Drive uploads, plus Cancel, Retry (when safe), and Delete
history. Google's server-side Drive copy is atomic and cannot be paused.

### Recovery and infrastructure

Resumable sessions are encrypted in Supabase, not exposed in `/cloud/api/jobs`.
Every progress write refreshes the job's lease. The SQL claim function can
reclaim a worker that has disappeared for 15 minutes **only** when the transfer
is still in the safe `preparing` phase or an encrypted remote state exists.
On resume, the server first queries Google's
confirmed offset or searches for the app-owned copy marker. It never silently
creates a second copy after an uncertain `files.copy` response. Pausing retains
that state; cancelling an uncertain remote upload marks `needs_review`.

**Render Free cannot guarantee uninterrupted multi-GB uploads**: free web
instances spin down after inactivity, have an ephemeral filesystem, and may
restart. V13.6 streaming does not stage a 4 GiB temporary file, but reliable
large HTTPS downloads still need an always-on worker with outbound network
access and periodic worker process restarts. If the worker goes away and the
Free instance stays asleep, jobs wait until the service starts again. A paused
Google upload session expires after about one week; expired sessions require
manual review, not blind retry. Never claim production-grade 4 GiB reliability
without a successful full-size live test and appropriate worker hosting.

Large Google-Drive-to-same-Google-Drive server-side copy is much less sensitive
to hosting duration than HTTPS-to-Drive relay.

### Offline verification

```powershell
py -3 -m unittest TEST_CLOUDBRIDGE_V136 TEST_CLOUDBRIDGE_V134 TEST_V135_CLOUDBRIDGE_HOME TEST_V134_TELEGRAM_SIGNATURE TEST_V8_STUDY_LAB TEST_STUDENT_ALL_AGES_V134 TEST_SUPER_MINIAPP_V120 TEST_V120_ACCESS_MENU_FIX -q
git diff --check
```

The V13.6 unit tests simulate a 4 GiB *offset* and final chunk without
allocating or uploading 4 GiB. **They do not replace an actual live Google
Drive/HTTPS/Telegram test.**
