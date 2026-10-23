STUDENT ASSISTANT BOT V4.7
SEMESTERS + GRADES + GPA
========================

🎓 SEMESTER MANAGER
-------------------
- Add semester
- Optional start/end dates
- Set the university GPA scale
- One active semester at a time
- View semester history
- Change active semester
- Delete semester

When a new semester is created:
- any old active semester becomes completed
- the new semester becomes active


📊 COURSE RESULTS
-----------------
- Choose semester
- Choose subject
- Enter credits
- Optional grade label
- Enter grade points
- Optional percentage score
- Add/update one result per subject per semester
- Delete results


📊 GPA CALCULATOR
-----------------
Weighted GPA formula:

sum(credits × grade_points)
---------------------------
sum(credits)

The bot does NOT guess your university's grade mapping.
You enter:
- GPA scale
- grade point for each result

This makes the tracker compatible with different universities.


🏆 CUMULATIVE GPA
-----------------
Cumulative GPA is shown only when the included semesters
use the same GPA scale.

If semester scales differ, the bot does not combine them,
because that could produce a misleading result.


🧮 TARGET GPA
-------------
The bot can calculate the average grade point required
over your remaining credits to reach a target semester GPA.

It also tells you when:
- the target is already safely exceeded
- the target is mathematically unreachable


DEPENDENCIES
------------
No new Python packages required.
Uses your existing Supabase setup.
