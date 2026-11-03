# Student Assistant Bot — V5.4 Full Project (clean copy)

This is a full Python project sourced from your uploaded StudentAssistantBot.zip, with
all application modules preserved. This archive does **not** contain `.env`, local
student database files, `.git` history, `__pycache__`, or V5.3 backup copies.

## Already integrated

- Flask + Render Telegram webhook entry point in `main.py`
- Central navigation including `🧠 Due Reviews`
- Legacy `🧠 Flashcards` features plus new Due Reviews / Review Stats submenu buttons
- `spaced_repetition.py` review sessions, ratings, and statistics
- `SQL_V5_4.sql` separate `flashcard_reviews` table
- Original `flashcards.py` database model unchanged (`id`, `user_id`, `subject_id`, `question`, `answer`)

## Safe installation / deployment

1. **Back up** your current working folder and Supabase before replacing code.
2. Run `SQL_V5_4.sql` once in **Supabase → SQL Editor**, if you have not done it already.
   The script creates only the review table and its index; it does not alter your existing cards.
3. For an existing V5.4 installation, update just these files: `flashcards.py`,
   `spaced_repetition.py`, `navigation.py`. The other application files in this archive
   come from your uploaded project and are included for convenience.
4. For a fresh checkout, keep your existing **private** `.env` locally. Never commit it.
   See `.env.example` for variable names; Render should already store them under
   Environment. Do not replace a working token/key with placeholder values.
5. Install dependencies from `requirements.txt` inside your existing virtualenv.
6. Run the checks: `python -m compileall -q .` and
   `python -m unittest TEST_V5_4.py TEST_V5_4_INTEGRATION.py -v`.
7. Test against your **actual** Supabase environment, then deploy via your existing
   Git → Render flow. Do not run local polling while the Render webhook is active
   unless intentionally switching environments.

## Telegram smoke test

- Send `/start`, tap `🧠 Flashcards`.
- Add a flashcard if necessary; open `🧠 Due Reviews`.
- Reveal Answer → rate Again/Hard/Good/Easy.
- Tap `📊 Review Stats` and check that due count changes.
- Send `/healthcheck` and confirm `flashcard_reviews` is present.
- Try `/reviews` and `/reviewstats` directly.
- Check that the **legacy** `🎯 Study Flashcards` still works and that Main Menu / Cancel work.

## Limitations

- A user's first 500 existing flashcards are considered per review command.
- Sessions are stored in RAM; old review buttons expire after 30 minutes or restart.
  Completed review schedules remain stored in Supabase.
- Interval scheduling is SM-2-inspired, not the exact Anki algorithm.
- Unit and mocked integration tests cannot establish actual live database/webhook compatibility.

## Security

This project was uploaded with a `.env` and `.git` directory. Both are **excluded**
from this distribution. If the archive has been shared beyond your trusted account,
rotate Telegram/Supabase/webhook credentials and check repository history.

## Rollback

Restore your previously working Git commit or backups and redeploy. The new
`flashcard_reviews` table is separate; leave it untouched for later recovery.
