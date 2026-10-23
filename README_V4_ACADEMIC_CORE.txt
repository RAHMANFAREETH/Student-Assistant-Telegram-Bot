STUDENT ASSISTANT BOT V4 - ACADEMIC CORE

FEATURES
========

SUBJECTS
- Add subject
- Optional subject code
- View subjects
- Delete subjects
- Per-user Supabase storage
- Duplicate subject protection

ASSIGNMENTS
- Add assignment
- Description
- Deadline
- Priority: High / Medium / Low
- Link to a subject
- Upcoming assignments
- Due today
- Due in next 7 days
- Completed assignments
- Mark complete
- Delete assignment
- Sri Lanka timezone handling
- Per-user Supabase storage

ROUTING SAFETY
==============
State handlers use ContinueHandling() for commands and other major module buttons.
This helps avoid the handler conflicts previously seen between PDF Tools and Translation.

FILES
=====
v4_academic_core.sql
subjects.py
assignments.py
MAIN_INTEGRATION.txt

NEXT V4 PHASE
=============
After this is stable:
- Assignment reminder automation
- Dashboard
- Flashcards
- Quiz engine
- Study progress
