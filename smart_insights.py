from datetime import datetime, timedelta, time as dt_time, timezone
from zoneinfo import ZoneInfo

from telebot import types

from db import supabase
from subjects import (
    get_subjects,
    get_subject_by_id,
    subject_display,
)


SRI_LANKA_TZ = ZoneInfo("Asia/Colombo")


def _utc_iso(local_dt):
    if local_dt.tzinfo is None:
        local_dt = local_dt.replace(
            tzinfo=SRI_LANKA_TZ
        )

    return (
        local_dt
        .astimezone(timezone.utc)
        .isoformat()
    )


def _subject_name(
    user_id,
    subject_id,
):
    if not subject_id:
        return "No Subject"

    try:
        subject = get_subject_by_id(
            user_id,
            subject_id,
        )

        if subject:
            return subject_display(
                subject
            )

    except Exception:
        pass

    return "No Subject"


def _safe_rows(
    table_name,
    user_id,
    columns="*",
    limit=500,
):
    try:
        result = (
            supabase
            .table(table_name)
            .select(columns)
            .eq(
                "user_id",
                int(user_id),
            )
            .limit(limit)
            .execute()
        )

        return (
            result.data
            or []
        )

    except Exception as error:
        print(
            f"Smart insights table error ({table_name}):",
            repr(error),
        )

        return []


def _local_date_from_timestamp(
    value,
):
    if not value:
        return None

    try:
        dt = datetime.fromisoformat(
            str(value).replace(
                "Z",
                "+00:00",
            )
        )

        return (
            dt
            .astimezone(SRI_LANKA_TZ)
            .date()
        )

    except Exception:
        return None


def _local_datetime(
    value,
):
    if not value:
        return None

    try:
        dt = datetime.fromisoformat(
            str(value).replace(
                "Z",
                "+00:00",
            )
        )

        return dt.astimezone(
            SRI_LANKA_TZ
        )

    except Exception:
        return None


def _percentage(
    numerator,
    denominator,
):
    if not denominator:
        return None

    return (
        numerator
        / denominator
        * 100
    )


def collect_subject_metrics(
    user_id,
):
    subjects = get_subjects(
        user_id
    )

    metrics = {}

    for subject in subjects:
        subject_id = subject[
            "id"
        ]

        metrics[
            subject_id
        ] = {
            "subject_id": subject_id,
            "subject_name": subject_display(
                subject
            ),

            "assignment_pending": 0,
            "assignment_completed": 0,
            "assignment_overdue": 0,
            "assignment_due_7d": 0,

            "quiz_attempts": 0,
            "quiz_average": None,

            "flashcards_total": 0,
            "flashcards_mastered": 0,
            "flashcard_mastery": None,

            "attendance_total": 0,
            "attendance_present": 0,
            "attendance_late": 0,
            "attendance_absent": 0,
            "attendance_excused": 0,
            "attendance_percent": None,

            "study_minutes_7d": 0,

            "revision_pending": 0,
            "revision_completed": 0,

            "grade_results": 0,
            "grade_point_average": None,

            "exam_within_14d": False,
            "next_exam_at": None,

            "health_score": None,
            "risk_level": None,
            "reasons": [],
            "recommendations": [],
        }

    now_utc = datetime.now(
        timezone.utc
    )

    now_local = datetime.now(
        SRI_LANKA_TZ
    )

    week_start_local = (
        now_local
        - timedelta(days=7)
    )

    two_weeks_utc = (
        now_utc
        + timedelta(days=14)
    )

    # ==================================================
    # ASSIGNMENTS
    # ==================================================

    assignments = _safe_rows(
        "assignments",
        user_id,
        (
            "id,subject_id,title,due_at,"
            "priority,status,completed_at"
        ),
        1000,
    )

    for item in assignments:
        subject_id = item.get(
            "subject_id"
        )

        if subject_id not in metrics:
            continue

        status = (
            item.get(
                "status"
            )
            or "pending"
        )

        due_at = _local_datetime(
            item.get(
                "due_at"
            )
        )

        if status == "completed":
            metrics[
                subject_id
            ][
                "assignment_completed"
            ] += 1

        else:
            metrics[
                subject_id
            ][
                "assignment_pending"
            ] += 1

            if due_at:
                if due_at < now_local:
                    metrics[
                        subject_id
                    ][
                        "assignment_overdue"
                    ] += 1

                elif (
                    due_at
                    <= now_local
                    + timedelta(days=7)
                ):
                    metrics[
                        subject_id
                    ][
                        "assignment_due_7d"
                    ] += 1

    # ==================================================
    # QUIZZES
    # ==================================================

    quiz_attempts = _safe_rows(
        "quiz_attempts",
        user_id,
        (
            "id,subject_id,total_questions,"
            "correct_answers,wrong_answers,"
            "score_percent,created_at"
        ),
        1000,
    )

    quiz_scores = {}

    for item in quiz_attempts:
        subject_id = item.get(
            "subject_id"
        )

        if subject_id not in metrics:
            continue

        score = item.get(
            "score_percent"
        )

        if score is None:
            continue

        try:
            score = float(
                score
            )
        except Exception:
            continue

        quiz_scores.setdefault(
            subject_id,
            [],
        ).append(
            score
        )

    for subject_id, values in quiz_scores.items():
        metrics[
            subject_id
        ][
            "quiz_attempts"
        ] = len(
            values
        )

        metrics[
            subject_id
        ][
            "quiz_average"
        ] = (
            sum(values)
            / len(values)
        )

    # ==================================================
    # FLASHCARDS
    # ==================================================

    flashcards = _safe_rows(
        "flashcards",
        user_id,
        (
            "id,subject_id,mastered,"
            "times_seen,correct_count,wrong_count"
        ),
        2000,
    )

    for item in flashcards:
        subject_id = item.get(
            "subject_id"
        )

        if subject_id not in metrics:
            continue

        metrics[
            subject_id
        ][
            "flashcards_total"
        ] += 1

        if item.get(
            "mastered"
        ):
            metrics[
                subject_id
            ][
                "flashcards_mastered"
            ] += 1

    for subject_id, item in metrics.items():
        item[
            "flashcard_mastery"
        ] = _percentage(
            item[
                "flashcards_mastered"
            ],
            item[
                "flashcards_total"
            ],
        )

    # ==================================================
    # ATTENDANCE
    # ==================================================

    attendance = _safe_rows(
        "attendance_records",
        user_id,
        (
            "id,subject_id,class_date,"
            "status"
        ),
        3000,
    )

    for item in attendance:
        subject_id = item.get(
            "subject_id"
        )

        if subject_id not in metrics:
            continue

        status = item.get(
            "status"
        )

        metrics[
            subject_id
        ][
            "attendance_total"
        ] += 1

        if status == "present":
            metrics[
                subject_id
            ][
                "attendance_present"
            ] += 1

        elif status == "late":
            metrics[
                subject_id
            ][
                "attendance_late"
            ] += 1

        elif status == "absent":
            metrics[
                subject_id
            ][
                "attendance_absent"
            ] += 1

        elif status == "excused":
            metrics[
                subject_id
            ][
                "attendance_excused"
            ] += 1

    for subject_id, item in metrics.items():
        item[
            "attendance_percent"
        ] = _percentage(
            (
                item[
                    "attendance_present"
                ]
                + item[
                    "attendance_late"
                ]
            ),
            item[
                "attendance_total"
            ],
        )

    # ==================================================
    # STUDY MINUTES — LAST 7 DAYS
    # ==================================================

    sessions = _safe_rows(
        "study_sessions",
        user_id,
        (
            "id,subject_id,planned_minutes,"
            "actual_minutes,status,started_at"
        ),
        2000,
    )

    for item in sessions:
        if item.get(
            "status"
        ) != "completed":
            continue

        subject_id = item.get(
            "subject_id"
        )

        if subject_id not in metrics:
            continue

        started_at = _local_datetime(
            item.get(
                "started_at"
            )
        )

        if not started_at:
            continue

        if started_at < week_start_local:
            continue

        minutes = int(
            item.get(
                "actual_minutes"
            )
            or item.get(
                "planned_minutes"
            )
            or 0
        )

        metrics[
            subject_id
        ][
            "study_minutes_7d"
        ] += minutes

    # ==================================================
    # REVISION TASKS
    # ==================================================

    revision_plans = _safe_rows(
        "revision_plans",
        user_id,
        (
            "id,subject_id,status"
        ),
        500,
    )

    plan_subject = {
        plan[
            "id"
        ]: plan.get(
            "subject_id"
        )
        for plan in revision_plans
    }

    revision_tasks = _safe_rows(
        "revision_tasks",
        user_id,
        (
            "id,plan_id,status,"
            "task_date"
        ),
        3000,
    )

    for task in revision_tasks:
        subject_id = plan_subject.get(
            task.get(
                "plan_id"
            )
        )

        if subject_id not in metrics:
            continue

        if task.get(
            "status"
        ) == "completed":
            metrics[
                subject_id
            ][
                "revision_completed"
            ] += 1

        else:
            metrics[
                subject_id
            ][
                "revision_pending"
            ] += 1

    # ==================================================
    # GRADES
    # ==================================================

    grade_rows = _safe_rows(
        "course_results",
        user_id,
        (
            "id,subject_id,credits,"
            "grade_points,semester_id"
        ),
        1000,
    )

    weighted = {}

    for item in grade_rows:
        subject_id = item.get(
            "subject_id"
        )

        if subject_id not in metrics:
            continue

        try:
            credits = float(
                item.get(
                    "credits"
                )
                or 0
            )

            grade_points = float(
                item.get(
                    "grade_points"
                )
                or 0
            )

        except Exception:
            continue

        if credits <= 0:
            continue

        weighted.setdefault(
            subject_id,
            {
                "quality": 0.0,
                "credits": 0.0,
                "count": 0,
            },
        )

        weighted[
            subject_id
        ][
            "quality"
        ] += (
            credits
            * grade_points
        )

        weighted[
            subject_id
        ][
            "credits"
        ] += credits

        weighted[
            subject_id
        ][
            "count"
        ] += 1

    for subject_id, values in weighted.items():
        metrics[
            subject_id
        ][
            "grade_results"
        ] = values[
            "count"
        ]

        if values[
            "credits"
        ] > 0:
            metrics[
                subject_id
            ][
                "grade_point_average"
            ] = (
                values[
                    "quality"
                ]
                / values[
                    "credits"
                ]
            )

    # ==================================================
    # UPCOMING EXAMS
    # ==================================================

    exams = _safe_rows(
        "exams",
        user_id,
        (
            "id,subject_id,title,"
            "exam_at"
        ),
        500,
    )

    for item in exams:
        subject_id = item.get(
            "subject_id"
        )

        if subject_id not in metrics:
            continue

        exam_dt = _local_datetime(
            item.get(
                "exam_at"
            )
        )

        if not exam_dt:
            continue

        if exam_dt < now_local:
            continue

        current = metrics[
            subject_id
        ][
            "next_exam_at"
        ]

        if (
            current is None
            or exam_dt < current
        ):
            metrics[
                subject_id
            ][
                "next_exam_at"
            ] = exam_dt

        if (
            exam_dt.astimezone(
                timezone.utc
            )
            <= two_weeks_utc
        ):
            metrics[
                subject_id
            ][
                "exam_within_14d"
            ] = True

    return metrics


def score_subject_health(
    metrics,
):
    score = 100.0
    reasons = []
    recommendations = []

    # ==================================================
    # ASSIGNMENT RISK
    # ==================================================

    overdue = metrics[
        "assignment_overdue"
    ]

    due_7d = metrics[
        "assignment_due_7d"
    ]

    if overdue:
        penalty = min(
            30,
            overdue
            * 12,
        )

        score -= penalty

        reasons.append(
            (
                f"{overdue} overdue assignment"
                f"{'s' if overdue != 1 else ''}"
            )
        )

        recommendations.append(
            "Finish overdue assignments first."
        )

    elif due_7d:
        score -= min(
            10,
            due_7d
            * 3,
        )

        reasons.append(
            (
                f"{due_7d} assignment"
                f"{'s' if due_7d != 1 else ''} "
                "due within 7 days"
            )
        )

        recommendations.append(
            "Schedule time for upcoming assignments."
        )

    # ==================================================
    # QUIZ RISK
    # ==================================================

    quiz_average = metrics[
        "quiz_average"
    ]

    if quiz_average is not None:
        if quiz_average < 50:
            score -= 20

            reasons.append(
                (
                    f"quiz average is "
                    f"{quiz_average:.1f}%"
                )
            )

            recommendations.append(
                "Review weak quiz topics and retest."
            )

        elif quiz_average < 70:
            score -= 10

            reasons.append(
                (
                    f"quiz average is "
                    f"{quiz_average:.1f}%"
                )
            )

            recommendations.append(
                "Do another quiz after revising key topics."
            )

    # ==================================================
    # FLASHCARD MASTERY
    # ==================================================

    mastery = metrics[
        "flashcard_mastery"
    ]

    if (
        mastery is not None
        and metrics[
            "flashcards_total"
        ] >= 4
    ):
        if mastery < 30:
            score -= 15

            reasons.append(
                (
                    f"flashcard mastery is "
                    f"{mastery:.0f}%"
                )
            )

            recommendations.append(
                "Spend 15–20 minutes reviewing flashcards."
            )

        elif mastery < 60:
            score -= 7

    # ==================================================
    # ATTENDANCE
    # ==================================================

    attendance = metrics[
        "attendance_percent"
    ]

    if (
        attendance is not None
        and metrics[
            "attendance_total"
        ] >= 3
    ):
        if attendance < 75:
            score -= 25

            reasons.append(
                (
                    f"attendance is "
                    f"{attendance:.1f}%"
                )
            )

            recommendations.append(
                "Prioritize attendance and catch up missed classes."
            )

        elif attendance < 85:
            score -= 10

            reasons.append(
                (
                    f"attendance is "
                    f"{attendance:.1f}%"
                )
            )

    # ==================================================
    # STUDY TIME
    # ==================================================

    minutes = metrics[
        "study_minutes_7d"
    ]

    if minutes == 0:
        score -= 12

        reasons.append(
            "no completed study sessions in the last 7 days"
        )

        recommendations.append(
            "Start a focused study session for this subject."
        )

    elif minutes < 60:
        score -= 6

    # ==================================================
    # EXAM + REVISION PRESSURE
    # ==================================================

    if metrics[
        "exam_within_14d"
    ]:
        score -= 5

        reasons.append(
            "exam is within 14 days"
        )

        if metrics[
            "revision_pending"
        ] > 0:
            recommendations.append(
                "Complete pending revision tasks before the exam."
            )

        elif metrics[
            "revision_completed"
        ] == 0:
            recommendations.append(
                "Create a revision plan for the upcoming exam."
            )

    # ==================================================
    # FINAL
    # ==================================================

    score = max(
        0.0,
        min(
            100.0,
            score,
        ),
    )

    if score >= 80:
        risk = "🟢 Strong"

    elif score >= 60:
        risk = "🟡 Watch"

    elif score >= 40:
        risk = "🟠 At Risk"

    else:
        risk = "🔴 High Risk"

    metrics[
        "health_score"
    ] = round(
        score
    )

    metrics[
        "risk_level"
    ] = risk

    metrics[
        "reasons"
    ] = reasons

    metrics[
        "recommendations"
    ] = recommendations

    return metrics


def build_smart_insights(
    user_id,
):
    metrics_map = collect_subject_metrics(
        user_id
    )

    results = []

    for item in metrics_map.values():
        results.append(
            score_subject_health(
                item
            )
        )

    results.sort(
        key=lambda item: (
            item[
                "health_score"
            ],
            item[
                "subject_name"
            ].casefold(),
        )
    )

    return results


def build_priority_list(
    user_id,
):
    results = build_smart_insights(
        user_id
    )

    priorities = []

    for item in results:
        if (
            item[
                "health_score"
            ] >= 80
            and not item[
                "assignment_due_7d"
            ]
            and not item[
                "exam_within_14d"
            ]
        ):
            continue

        actions = item[
            "recommendations"
        ][
            :3
        ]

        if not actions:
            actions = [
                "Keep your study routine consistent."
            ]

        priorities.append(
            {
                "subject_name": item[
                    "subject_name"
                ],
                "health_score": item[
                    "health_score"
                ],
                "risk_level": item[
                    "risk_level"
                ],
                "actions": actions,
            }
        )

    return priorities


def register_smart_insight_handlers(
    bot,
    show_main_menu,
):

    def show_insight_menu(
        chat_id
    ):
        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "🧠 Smart Study Insights"
            ),
            types.KeyboardButton(
                "🚦 Subject Health"
            ),
            types.KeyboardButton(
                "🎯 What Should I Study?"
            ),
            types.KeyboardButton(
                "📅 Weekly Review"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "🧠 Smart Study Insights V5.0\n\n"
                "The bot analyzes your own academic data "
                "and highlights subjects that need attention.\n\n"
                "This is rule-based analysis, not paid AI."
            ),
            reply_markup=markup,
        )

    @bot.message_handler(
        commands=["insights"]
    )
    def insights_command(
        message
    ):
        show_insight_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🧠 Smart Insights"
    )
    def insights_button(
        message
    ):
        show_insight_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🧠 Smart Study Insights"
    )
    def run_insights(
        message
    ):
        status = bot.send_message(
            message.chat.id,
            "🧠 Analyzing your study data..."
        )

        try:
            results = build_smart_insights(
                message.from_user.id
            )

            try:
                bot.delete_message(
                    message.chat.id,
                    status.message_id,
                )
            except Exception:
                pass

            if not results:
                bot.send_message(
                    message.chat.id,
                    (
                        "📚 No subjects found yet.\n\n"
                        "Add subjects first."
                    ),
                )
                return

            parts = [
                (
                    "🧠 SMART STUDY INSIGHTS\n"
                    "━━━━━━━━━━━━━━━━━━"
                )
            ]

            for item in results:
                parts.append(
                    (
                        f"\n\n📚 {item['subject_name']}\n"
                        f"{item['risk_level']} "
                        f"— Health {item['health_score']}/100"
                    )
                )

                if item[
                    "reasons"
                ]:
                    parts.append(
                        "\n⚠️ "
                        + "; ".join(
                            item[
                                "reasons"
                            ][
                                :3
                            ]
                        )
                    )

                if item[
                    "recommendations"
                ]:
                    parts.append(
                        "\n✅ "
                        + " ".join(
                            item[
                                "recommendations"
                            ][
                                :2
                            ]
                        )
                    )

            text = "".join(
                parts
            )

            for start in range(
                0,
                len(text),
                3800,
            ):
                bot.send_message(
                    message.chat.id,
                    text[
                        start:
                        start + 3800
                    ],
                )

        except Exception as error:
            print(
                "Smart insights error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not build smart insights.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "🚦 Subject Health"
    )
    def subject_health(
        message
    ):
        try:
            results = build_smart_insights(
                message.from_user.id
            )

            if not results:
                bot.send_message(
                    message.chat.id,
                    "📚 No subjects found.",
                )
                return

            parts = [
                "🚦 SUBJECT HEALTH\n"
                "━━━━━━━━━━━━━━━━━━\n"
            ]

            for item in results:
                assignment_total = (
                    item[
                        "assignment_pending"
                    ]
                    + item[
                        "assignment_completed"
                    ]
                )

                quiz = (
                    f"{item['quiz_average']:.1f}%"
                    if item[
                        "quiz_average"
                    ] is not None
                    else "No data"
                )

                attendance = (
                    f"{item['attendance_percent']:.1f}%"
                    if item[
                        "attendance_percent"
                    ] is not None
                    else "No data"
                )

                flashcards = (
                    f"{item['flashcard_mastery']:.0f}%"
                    if item[
                        "flashcard_mastery"
                    ] is not None
                    else "No data"
                )

                parts.append(
                    (
                        f"\n📚 {item['subject_name']}\n"
                        f"{item['risk_level']} "
                        f"{item['health_score']}/100\n"
                        f"📅 Assignments: "
                        f"{item['assignment_completed']}/"
                        f"{assignment_total} completed\n"
                        f"❓ Quiz Avg: {quiz}\n"
                        f"🧠 Flashcards: {flashcards}\n"
                        f"✅ Attendance: {attendance}\n"
                        f"⏱ Study 7d: "
                        f"{item['study_minutes_7d']} min\n"
                    )
                )

            text = "\n".join(
                parts
            )

            for start in range(
                0,
                len(text),
                3800,
            ):
                bot.send_message(
                    message.chat.id,
                    text[
                        start:
                        start + 3800
                    ],
                )

        except Exception as error:
            print(
                "Subject health error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not calculate subject health.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "🎯 What Should I Study?"
    )
    def what_should_i_study(
        message
    ):
        try:
            priorities = build_priority_list(
                message.from_user.id
            )

            if not priorities:
                bot.send_message(
                    message.chat.id,
                    (
                        "✅ No urgent study risks detected.\n\n"
                        "Continue your normal study plan."
                    ),
                )
                return

            parts = [
                (
                    "🎯 WHAT SHOULD I STUDY NEXT?\n"
                    "━━━━━━━━━━━━━━━━━━"
                )
            ]

            for index, item in enumerate(
                priorities[
                    :5
                ],
                start=1,
            ):
                parts.append(
                    (
                        f"\n\n{index}. 📚 "
                        f"{item['subject_name']}\n"
                        f"{item['risk_level']} "
                        f"— {item['health_score']}/100"
                    )
                )

                for action in item[
                    "actions"
                ]:
                    parts.append(
                        f"\n   • {action}"
                    )

            bot.send_message(
                message.chat.id,
                "".join(
                    parts
                ),
            )

        except Exception as error:
            print(
                "Study priority error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not build study priorities.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "📅 Weekly Review"
    )
    def weekly_review(
        message
    ):
        try:
            results = build_smart_insights(
                message.from_user.id
            )

            if not results:
                bot.send_message(
                    message.chat.id,
                    "📚 No subjects found.",
                )
                return

            total_minutes = sum(
                item[
                    "study_minutes_7d"
                ]
                for item in results
            )

            overdue = sum(
                item[
                    "assignment_overdue"
                ]
                for item in results
            )

            due_7d = sum(
                item[
                    "assignment_due_7d"
                ]
                for item in results
            )

            strong = sum(
                1
                for item in results
                if item[
                    "health_score"
                ] >= 80
            )

            at_risk = [
                item
                for item in results
                if item[
                    "health_score"
                ] < 60
            ]

            parts = [
                (
                    "📅 WEEKLY STUDY REVIEW\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    f"⏱ Study time: {total_minutes} minutes\n"
                    f"⚠️ Overdue assignments: {overdue}\n"
                    f"📅 Assignments due in 7 days: {due_7d}\n"
                    f"🟢 Strong subjects: {strong}/{len(results)}\n"
                    f"🟠/🔴 At-risk subjects: {len(at_risk)}"
                )
            ]

            if at_risk:
                parts.append(
                    "\n\n🎯 PRIORITY SUBJECTS"
                )

                for item in at_risk[
                    :5
                ]:
                    parts.append(
                        (
                            f"\n• {item['subject_name']} "
                            f"— {item['health_score']}/100"
                        )
                    )

            strongest = max(
                results,
                key=lambda item:
                item[
                    "health_score"
                ],
            )

            weakest = min(
                results,
                key=lambda item:
                item[
                    "health_score"
                ],
            )

            parts.append(
                (
                    "\n\n🏆 Strongest: "
                    f"{strongest['subject_name']} "
                    f"({strongest['health_score']}/100)"
                    "\n📌 Needs most attention: "
                    f"{weakest['subject_name']} "
                    f"({weakest['health_score']}/100)"
                )
            )

            bot.send_message(
                message.chat.id,
                "".join(
                    parts
                ),
            )

        except Exception as error:
            print(
                "Weekly review error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not create weekly review.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "🏠 Main Menu"
    )
    def insights_main_menu(
        message
    ):
        show_main_menu(
            message.chat.id,
            message.from_user.first_name
            or "Friend",
        )
