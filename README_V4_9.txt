STUDENT ASSISTANT BOT V4.9
==========================

📚 REVISION PLANNER
-------------------
- Uses existing upcoming exams
- User enters one revision topic per line
- Topics are automatically distributed across
  the remaining days before the exam
- Today's revision list
- Complete revision tasks
- Revision-plan progress
- Plans automatically become completed when
  every task is completed
- Delete revision plans


🔥 STUDY STREAK
---------------
Uses completed Study Planner sessions.

A day counts toward the streak when:

completed study minutes >= daily target

Features:
- configurable daily target
- today's completed minutes
- current streak
- best streak from the last 60 days
- last 7 days activity


🎯 DAILY STUDY TARGET
---------------------
Default:
60 minutes per day

User can change it to:
30
45
60
90
120
etc.

Range:
1–1440 minutes


COST
----
No paid API.
No new external service.
No new pip package.


DATABASE
--------
New tables:
- study_preferences
- revision_plans
- revision_tasks

Existing data reused:
- exams
- subjects
- study_sessions
