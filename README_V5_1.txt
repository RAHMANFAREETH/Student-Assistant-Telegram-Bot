STUDENT ASSISTANT BOT V5.1
SMART NOTIFICATIONS CENTER
==========================

🔔 SMART NOTIFICATIONS
----------------------
Students can configure automatic Telegram study updates.

No paid API is required.


☀️ DAILY BRIEF
--------------
Default:
07:00 local time

Includes:
- today's class count
- assignments due today
- overdue assignments
- exams in next 7 days
- active study goals

The student may:
- enable/disable it
- change the hour
- change timezone


📅 WEEKLY REVIEW
----------------
Default:
Sunday at 18:00 local time

Includes:
- study minutes in last 7 days
- assignments completed in last 7 days
- quiz average in last 7 days
- current overdue assignments
- exams in next 7 days

The student may:
- enable/disable it
- choose day
- choose hour
- choose timezone


🌍 TIMEZONE SUPPORT
-------------------
Uses IANA timezone names.

Examples:
Asia/Colombo
Asia/Dubai
Europe/London
America/New_York


☁️ WHY SUPABASE CRON?
----------------------
Render Free services may sleep.

The notification worker runs from Supabase Cron,
so daily/weekly notifications do not depend on
the Render app being awake.


🔐 SECURITY
-----------
Telegram token remains in Supabase Vault under:

telegram_bot_token

Do not place the token directly in SQL.


DATABASE
--------
New table:

notification_preferences


CRON
----
Job:

student-smart-notifications

Runs every 15 minutes and checks the user's
configured local timezone/hour.
