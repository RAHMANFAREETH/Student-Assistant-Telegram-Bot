STUDENT ASSISTANT BOT V4.8
==========================

☀️ TODAY HUB
------------
One daily academic overview:

- today's classes
- assignments due today
- exams in the next 7 days
- active study goals
- overdue study goals
- study minutes completed today

This is an on-demand dashboard.
No paid API is used.


🔎 GLOBAL SEARCH
----------------
Search one phrase across:

- notes
- study materials
- assignments
- exams
- study goals
- voice-note transcripts
- multilingual vocabulary
- flashcards

Results show:
- source type
- record ID
- title/question/term
- nearby matching text


📦 DATA EXPORT / BACKUP
-----------------------
Exports the signed-in Telegram user's academic rows only.

Included:
- subjects
- notes
- reminders
- assignments
- study materials
- timetable
- study sessions
- flashcards
- quiz attempts
- voice-note metadata/transcripts
- language vocabulary
- exams
- attendance
- study goals
- semesters
- course results

Format:
JSON compressed with GZIP

Example filename:
student_assistant_backup_20261023_183000.json.gz

SECURITY:
The export does NOT include:
- BOT_TOKEN
- SUPABASE_SECRET_KEY
- WEBHOOK_SECRET
- OCR_SPACE_API_KEY
- ASSEMBLYAI_API_KEY
- environment variables

The backup itself may contain private academic information,
so students should keep the file private.


DEPENDENCIES
------------
No new pip package.
No new Supabase table.
Uses Python standard library + existing Supabase client.
