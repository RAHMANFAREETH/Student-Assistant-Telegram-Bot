STUDENT ASSISTANT BOT V5.4 — SMART SPACED REPETITION
====================================================

CONTENTS
--------
main.py                      Updated from your main_v5_3_fixed.py
navigation.py                Adds 🧠 Due Reviews to central menu
spaced_repetition.py         Review feature; existing flashcards.py unchanged
SQL_V5_4.sql                 New Supabase review progress table
system_health.py             Adds flashcard_reviews to expected tables
MAIN_V5_4_INTEGRATION.txt    Installation steps
TEST_V5_4.py                 Lightweight algorithm tests
Plus V5.3 core-stability support files.

IMPORTANT LIMITATION
--------------------
Your V5.3 ZIP contains only core-stability utilities, not flashcards.py,
db.py, config.py, or the rest of the project. Install the V5.4 files into
your FULL EXISTING bot directory and keep all other existing modules.

This add-on reads the existing flashcards table and never edits it. It
stores new review progress in flashcard_reviews. Because flashcards.py was
not supplied, the old table schema cannot yet be confirmed.

DEFAULT FLASHCARD DATABASE FIELDS
---------------------------------
Student owner: user_id (alternates: telegram_id, chat_id, student_id)
Card ID: id (alternates: flashcard_id, card_id)
Front: question (alternates: front, front_text, term, word, title)
Back: answer (alternates: back, back_text, definition, meaning, description)

For nonstandard field names set optional environment variables:
FLASHCARD_USER_FIELD, FLASHCARD_ID_FIELD,
FLASHCARD_FRONT_FIELD, FLASHCARD_BACK_FIELD

No unfiltered card retrieval occurs; only the current Telegram user's
records are queried. The user's from_user.id is used, rather than any
untrusted chat text. If older flashcards were stored by chat ID, private
chat use usually gives identical IDs; group chats may not.

COMMANDS
--------
/reviews      Start due-review session
/reviewstats  View totals and mastery

A new 🧠 Due Reviews button is on the main menu.
The old 🧠 Flashcards button continues to use flashcards.py as before.

REVIEW SCHEDULING
-----------------
Again = 10 minutes; Hard = 1 day for new card;
Good = 3 days for new card; Easy = 7 days for new card.
Later intervals adapt using the previous interval and ease factor.
This is a simple SM-2-inspired scheduler, not Anki's exact algorithm.

RELIABILITY NOTES
-----------------
Schedules are persisted in Supabase. The current unanswered card is held
in memory for up to 30 minutes; deployment restarts invalidate its buttons.
Run /reviews again after a restart. A rating is saved once per session.

Maximum 500 cards per user are considered per session. If students have
more, the bot needs pagination. Your existing flashcards and legacy
features are not touched by this change.

Security: bot should access Supabase via server-side service-role secret;
never include secrets in ZIP or Git commits. The review table has RLS
and revokes anon/authenticated access by default.

VALIDATION
----------
python -m py_compile main.py navigation.py spaced_repetition.py system_health.py
python -m unittest TEST_V5_4.py

Integration with your specific flashcards table requires deployment-time
validation. Tests in this package do not claim successful Telegram/Supabase
integration on your live bot.
