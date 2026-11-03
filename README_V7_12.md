# Student Assistant Bot V7.12 — Announcements to existing users

## What changed

V7.10 `/broadcast` sends only to users who opted in with `/subscribe`. This upgrade adds **`/broadcastall`**, a separate admin-only, private-chat-only announcement mode for **known users who have previously used your bot**, whether or not they subscribed. Existing `/broadcast`, `/subscribe`, `/announcements off`, and `/messageuser` remain unchanged.

Users who explicitly sent `/announcements off` (or blocked the bot and were marked unsubscribed) are excluded. Every known-users announcement includes an opt-out instruction. Only admin IDs in `AI_OPS_ADMIN_IDS` can use `/broadcastall`.

## Important limitation

Telegram cannot provide a historical list of everyone who ever started your bot. The SQL migration imports IDs from **existing Supabase study tables** when available. Users who only sent `/start` long ago and never saved anything may not be in Supabase and cannot be recovered automatically. After this upgrade, private messages and private callback interactions are tracked in `bot_known_users_v712` (numeric user/chat ID + timestamp only). Group chat participants are not added. Messages and names are never stored in the new table.

Telegram can send a message only to a user with whom the bot can currently open a private conversation; delivery to users who never started it or who blocked it fails. Failed users with Telegram 403 are marked excluded for the future. Keep announcements occasional and relevant to the bot, not spam.

## Step 1 — Install the SAFE PATCH locally

Extract the ZIP. Copy **`INSTALL_V7_12.py`** and the entire **`V712_FILES`** folder into your existing `StudentAssistantBot` folder. Do not replace `main.py` manually.

Run in **VS Code Windows PowerShell**:

```powershell
python INSTALL_V7_12.py --dry-run
```

If it says `Install stopped safely`, STOP and share the output; it intentionally refuses to overwrite a locally edited or unexpected V7.10 broadcast module. If dry-run succeeds:

```powershell
python INSTALL_V7_12.py
python -m unittest TEST_V7_10_BROADCAST.py TEST_V7_12_KNOWN_USERS.py -v
python -m py_compile main.py broadcast_v710.py
```

Expected: **47 tests pass** if your existing V7.10 test file is present (21 old + 26 new). The installer keeps backups under `.v710_backups/v712_known_users/` and can safely roll back **local files only** via `python INSTALL_V7_12.py --rollback` if they have not been edited since installation.

## Step 2 — Supabase: import known users

In the **same Supabase project** → **SQL Editor**, execute `SQL_V7_12_KNOWN_USERS.sql` once. Re-running it is harmless: existing records are retained, and only missing user IDs are added.

The SQL creates **`bot_known_users_v712`** and imports distinct user IDs from existing study tables if those tables exist. It does **not** edit your Notes, Materials, Collections, AI settings, or existing broadcast preferences. It outputs one number: `known_user_ids`.

If SQL fails, do not send announcements. Share the SQL error and we can adjust the migration to your actual database schema. You must already have run the V7.10 `SQL_V7_10_BROADCAST.sql` migration.

## Step 3 — Review and deploy

```powershell
git diff --check
git status --short
git check-ignore .env
git ls-files .env
```

Check that `.env` is ignored and **not tracked** by Git. Stage **only** the V7.12 files:

```powershell
git add main.py broadcast_v710.py SQL_V7_12_KNOWN_USERS.sql TEST_V7_12_KNOWN_USERS.py README_V7_12.md
git diff --cached --check
git --no-pager diff --cached --stat
git commit -m "V7.12 add admin announcements to known users"
git push origin main
```

Existing Render Build/Start Commands and environment variables stay unchanged. Wait until Render shows **Live** before Telegram testing. This upgrade does not require a new Telegram bot, Render service, third-party API, or additional API key.

## Step 4 — In your existing Telegram bot (private chat)

1. `/broadcastallusers` — show how many known eligible users are in Supabase. Check if count resembles your 20–30 participants; if unexpectedly high, STOP and review the audience before sending.
2. `/broadcastall` — bot asks for announcement. Send the announcement in the **next plain-text message** (more user-friendly).
   - Or send a single message: `/broadcastall 📢 Bot update: new Text → PDF tool is available!`
3. Read the preview, which includes the exact message and recipient count.
4. `/broadcastallconfirm` — sends once to **known eligible users** in preview, re-checking opt-outs.
5. `/broadcastallcancel` — discard preview or compose mode. `/broadcaststatus` — view delivery summary.

**Examples**

```
/broadcastall
```

Bot: `Send your announcement as the NEXT text message.`

You: `📢 Hello friends! Thanks for using our Student Assistant Bot. Text → PDF is now available under PDF Tools!`

Bot shows the preview including `To stop future bot announcements: /announcements off`.

You: `/broadcastallconfirm`

### Existing commands remain unchanged

- `/broadcast Your message` → ONLY subscribers, confirmed via `/broadcastconfirm`.
- `/subscribe` → opt in to normal announcements.
- `/announcements off` → stop **both** kinds of broadcast, including `/broadcastall`.
- `/messageuser ID Your message` → subscribed recipients only (no change).

### Operational safeguards

- Max **100 known recipients** per broadcast. Exceeding this fails without delivery.
- Max 3,500 characters **including** the appended unsubscribe instructions.
- Admin-only, private-only, preview + explicit confirmation, 10-minute preview expiry.
- Single process-wide broadcast lock shared with V7.10.
- Re-checks eligibility at preview, confirmation, and immediately before each send.
- Respect `/announcements off` and Telegram block (403); handle rate limits (429).
- No messages are sent by installing the code or running SQL. Only a manual `/broadcastallconfirm` sends.
- Render restarts can interrupt in-memory delivery. Status isn't durable; don't resend blindly.

## Troubleshooting

- `0 known users`: Ensure Supabase migration ran; existing user IDs may not have been stored. Ask users to open the bot and send `/start` once after deployment to register them (no `/subscribe` needed).
- `Cannot load known users/preferences`: SQL migration missing, wrong Supabase key, or table grants.
- `Install stopped safely`: Local code differs from expected V7.10 base. Do **not** force-merge; get a targeted compatibility patch.
- Private updates via Telegram webhook must have passed secret validation before the tracking call; tracking error does not crash the bot.
- You can view a count of recorded IDs in Supabase: `select count(*) from public.bot_known_users_v712;`.
