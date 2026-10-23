STUDENT ASSISTANT BOT V4.1

NEW FEATURES
============

📊 STUDENT DASHBOARD
- Subject count
- Note count
- Active reminder count
- Pending assignment count
- Due today
- Due in next 7 days
- Completed assignment count
- Assignment completion percentage
- Next upcoming assignment

🔔 AUTOMATIC ASSIGNMENT ALERTS
- Due within 24 hours
- Due within 3 hours
- Deadline reached

ARCHITECTURE
============

Telegram
  ↓
Student adds assignment
  ↓
Supabase assignments table
  ↓
Supabase Cron every 5 minutes
  ↓
Database function
  ↓
pg_net
  ↓
Telegram Bot API
  ↓
Student receives alert

IMPORTANT
=========

New assignments store chat_id.
Existing assignments created before V4.1 may have chat_id = NULL
and therefore cannot receive automatic assignment alerts.
They can still appear normally in the bot/dashboard.

The Telegram token remains securely read from Supabase Vault.
