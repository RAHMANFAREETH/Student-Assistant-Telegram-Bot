STUDENT ASSISTANT BOT V5.3
CORE STABILITY
==========================

WHY V5.3?
---------
The bot now has many modules.

Older modules each maintained their own copy of
GLOBAL_BUTTONS.

That creates a common bug:

1. A module is waiting for text input.
2. A new main-menu button is pressed.
3. The old module thinks that button text is the answer.
4. The new menu does not open correctly.

V5.3 fixes the architecture by creating one central
navigation source.


navigation.py
-------------
Contains:
- all main-menu button labels
- MAIN_MENU_ROWS
- GLOBAL_BUTTONS
- universal navigation labels
- build_main_menu_markup()
- should_yield_to_navigation()


navigation_handlers.py
----------------------
Handles universal:

🏠 Main Menu
❌ Cancel


safe_utils.py
-------------
Reusable safe helpers:
- Telegram long-message splitting
- safe message deletion
- state cleanup
- integer validation


system_health.py
----------------
Commands:

/healthcheck
/systemhealth

Checks:
- required environment variables
- optional integration keys
- availability of expected Supabase tables

It never prints secret values.


migrate_global_buttons.py
-------------------------
Migration helper.

It finds top-level GLOBAL_BUTTONS assignments in known
stateful modules and replaces them with:

from navigation import GLOBAL_BUTTONS

A .bak_v5_3 backup is created before each modification.


SECURITY
--------
System Health only reports whether a secret exists.

It does NOT display:
- BOT_TOKEN
- SUPABASE_SECRET_KEY
- WEBHOOK_SECRET
- OCR key
- speech-to-text API key


COST
----
No paid API.
No new database table.
No new pip package.
