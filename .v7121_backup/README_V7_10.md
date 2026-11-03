# Student Assistant Bot V7.10 — Admin Announcements

This is a small optional patch for the **existing V7.9** Telegram bot and the **same Render/Supabase** services. It does NOT activate Gemini, change AI routing, alter V7.9 navigation categories, or replace `main.py`. Its installer inserts just two lines into `main.py` and adds an optional Help command.

## What users can do

Open the bot privately and send:

- `/announcements` — check whether updates are on/off.
- `/subscribe` — opt in to useful announcements.
- `/unsubscribe` — stop announcements at any time.

**Important:** Existing bot users are **not silently enrolled**. Invite the 20–30 users to opt in by sending `/subscribe` to the bot. Telegram bots cannot initiate conversations with someone who never started the bot. Group chats do not subscribe anyone.

## What you, the admin, can do

Only a Telegram user ID in the existing `AI_OPS_ADMIN_IDS` Render environment variable can use the following commands, and only in a **private chat**:

- `/broadcastusers` — see subscriber count (no personal identifiers displayed).
- `/broadcast The exam reminder is tomorrow at 9:00 AM.` — preview text and recipient count; **does not send**.
- `/broadcastconfirm` — send the preview after a second confirmation step.
- `/broadcastcancel` — discard a preview.
- `/broadcaststatus` — progress/result for current Render process.
- `/messageuser 123456789 Your message` — one private message to a currently subscribed user by Telegram ID.

An administrator can also use `/subscribe` to receive announcements.

## Installation (Windows / VS Code PowerShell)

1. Extract the ZIP. Copy `INSTALL_V7_10.py` and the `V710_FILES` directory into the **existing** `StudentAssistantBot` Git project folder. Do not remove other files.
2. Open VS Code Terminal in that project folder.
3. Run `python INSTALL_V7_10.py --dry-run`. Read the planned changes; the dry run does not modify files.
4. Run `python INSTALL_V7_10.py`.
5. Run `python -m unittest TEST_V7_10_BROADCAST.py -v`.
6. Run `python -m py_compile main.py user_help_v79.py broadcast_v710.py`.
7. Supabase Dashboard → SQL Editor: execute `SQL_V7_10_BROADCAST.sql` from your project folder. This **adds one table**, without editing existing data.
8. In **existing Render service** → Environment, verify `AI_OPS_ADMIN_IDS` already contains your numeric Telegram ID; e.g. `123456789` (not a token and not a username). If it is already set for `/aiops`, reuse it. No other new environment variable or service is required.
9. Commit and push only the intended files. Example:

```powershell
git status
git add main.py user_help_v79.py broadcast_v710.py TEST_V7_10_BROADCAST.py SQL_V7_10_BROADCAST.sql README_V7_10.md .gitignore
git commit -m "V7.10 add consent based admin announcements"
git push origin main
```

10. Once Render says `Live`, privately test `/announcements`, `/subscribe`, `/broadcastusers`, `/broadcast test`, `/broadcastcancel`. Then broadcast to your opted-in users.

## Suggested message to share with your group

> 📢 Student Assistant Bot updates: Please open our existing Telegram bot and send `/subscribe` if you want to receive occasional exam reminders, study notices and important announcements. You can stop messages at any time using `/unsubscribe`.

## Safety and limitations

- Text-only messages in this initial version (up to 3,500 characters). No external AI requests or paid broadcast option.
- Subscriptions are stored in a new Supabase table with RLS enabled and no public policies. No message content is saved to the table.
- Sends at a conservative speed below Telegram's published default broadcast limits (100 recipients maximum). A Telegram `403` response automatically switches the user's announcements off. `429` errors are retried once with bounded delay.
- Preview lasts 10 minutes; newly subscribed users after the preview are excluded, and unsubscribers are excluded even after confirmation.
- Background sends avoid holding the Telegram webhook response open. The **current worker process** tracks progress. **If Render restarts mid-send, delivery may be incomplete and status is lost.** Do not blindly resend the whole message because some users may already have received it. For a production-grade guaranteed durable queue, a later upgrade should add delivery receipts and an atomic jobs table.
- Use **one gunicorn worker** with the current bot setup. Multiple workers can break preview state and allow overlapping broadcasts. This patch does not implement cross-worker job locking.
- Do not enable this for unsolicited bulk/spam messages. User opt-in and an easy opt-out are deliberate protections.
- To revert local code before deployment: `python INSTALL_V7_10.py --rollback`; this refuses to overwrite edits made since install. The Supabase subscriber table remains intact until you explicitly decide what to do with it.
- Neither installer nor unit tests reads `.env`, uses API keys, calls external services, or deploys anything.
