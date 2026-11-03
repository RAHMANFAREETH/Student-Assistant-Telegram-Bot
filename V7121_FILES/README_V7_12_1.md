# V7.12.1 — Remove `/unsubscribe` command

This is a **small maintenance patch** for your existing Student Assistant Telegram Bot. It makes no database changes, sends no messages, and requires no new bot, Render service, or API key.

- `/unsubscribe` is **no longer registered** as a Telegram command, or advertised in help/announcements messages.
- `/announcements` shows the current setting; `/announcements off` turns off nonessential bot announcements and `/announcements on` resumes. This protects previous user preferences instead of overriding them.
- `/broadcast` and `/broadcastall` still require admin preview + confirmation. `/broadcastall` continues to reach known active users without requiring `/subscribe`, **except** users who have opted out or blocked the bot.
- Existing `subscribed=false` rows in Supabase are preserved. We do not erase user choices or send to users who opted out.
- This patch works with a current V7.10 or V7.12 broadcast module. If `/broadcastall` is not installed yet, this patch does not install it. **Install V7.12 first** if you need `/broadcastall`.

## Installation

Extract ZIP; copy `INSTALL_V7_12_1.py` plus the complete `V7121_FILES` directory into your existing `StudentAssistantBot` folder.

In **Windows PowerShell**, run:

```powershell
python INSTALL_V7_12_1.py --dry-run
python INSTALL_V7_12_1.py
python -m unittest TEST_V7_10_BROADCAST.py TEST_V7_12_1_ANNOUNCEMENT_PREFS.py -v
```

If you have V7.12 installed, additionally run:

```powershell
python -m unittest TEST_V7_12_KNOWN_USERS.py -v
```

The installer updates the broadcast module and the user help and existing test files **only when present**, preserving other code. You should inspect `git diff --check` and `git status --short` before staging. No new SQL is necessary.

Use an explicit Git add list to avoid including `.env`, backups, installers or unnecessary files:

```powershell
git add broadcast_v710.py user_help_v79.py TEST_V7_10_BROADCAST.py TEST_V7_12_KNOWN_USERS.py TEST_V7_12_1_ANNOUNCEMENT_PREFS.py README_V7_12_1.md
```

If a named file is not present, omit it from `git add`. Review staged files and secret exclusions before commit/push.

Rollback before modifying the patched files:

```powershell
python INSTALL_V7_12_1.py --rollback
```

If you previously advertised `/unsubscribe` in **BotFather → /setcommands**, remove that entry manually. BotFather's public slash-command menu isn't changed by Python code.
