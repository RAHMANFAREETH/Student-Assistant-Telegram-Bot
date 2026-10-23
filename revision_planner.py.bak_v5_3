from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase
from subjects import (
    get_subject_by_id,
    subject_display,
)


SRI_LANKA_TZ = ZoneInfo("Asia/Colombo")
revision_state = {}


GLOBAL_BUTTONS = {
    "📄 PDF Tools",
    "📝 Notes",
    "🌐 Translate",
    "⏰ Study Reminder",
    "📚 Subjects",
    "📅 Assignments",
    "📚 Study Materials",
    "🗓 Timetable",
    "⏱ Study Planner",
    "🎙 Voice Notes",
    "🌍 Language Tools",
    "🧠 Flashcards",
    "❓ Quiz",
    "📝 Exams",
    "✅ Attendance",
    "🎯 Study Goals",
    "🎓 Semesters",
    "📊 Grades & GPA",
    "☀️ Today Hub",
    "🔎 Global Search",
    "📦 Export My Data",
    "📚 Revision Planner",
    "🔥 Study Streak",
    "📊 Dashboard",
    "📈 Progress",
    "ℹ️ Help",
}


def _local_exam_date(
    value,
):
    dt = datetime.fromisoformat(
        str(value).replace(
            "Z",
            "+00:00",
        )
    )

    return dt.astimezone(
        SRI_LANKA_TZ
    ).date()


def get_upcoming_exams(
    user_id,
    limit=30,
):
    result = (
        supabase
        .table("exams")
        .select(
            "id,user_id,subject_id,title,exam_at,location"
        )
        .eq(
            "user_id",
            int(user_id),
        )
        .gte(
            "exam_at",
            datetime.now(
                timezone.utc
            ).isoformat(),
        )
        .order(
            "exam_at"
        )
        .limit(limit)
        .execute()
    )

    return result.data or []


def get_exam(
    user_id,
    exam_id,
):
    result = (
        supabase
        .table("exams")
        .select(
            "id,user_id,subject_id,title,exam_at,location"
        )
        .eq(
            "user_id",
            int(user_id),
        )
        .eq(
            "id",
            int(exam_id),
        )
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def get_plans(
    user_id,
    status="active",
    limit=30,
):
    query = (
        supabase
        .table("revision_plans")
        .select(
            "id,user_id,exam_id,subject_id,title,"
            "start_date,end_date,status,created_at"
        )
        .eq(
            "user_id",
            int(user_id),
        )
    )

    if status:
        query = query.eq(
            "status",
            status,
        )

    result = (
        query
        .order(
            "end_date"
        )
        .limit(limit)
        .execute()
    )

    return result.data or []


def get_plan(
    user_id,
    plan_id,
):
    result = (
        supabase
        .table("revision_plans")
        .select(
            "id,user_id,exam_id,subject_id,title,"
            "start_date,end_date,status,created_at"
        )
        .eq(
            "user_id",
            int(user_id),
        )
        .eq(
            "id",
            int(plan_id),
        )
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def get_tasks(
    user_id,
    plan_id=None,
    task_date=None,
    status=None,
    limit=200,
):
    query = (
        supabase
        .table("revision_tasks")
        .select(
            "id,user_id,plan_id,task_date,topic,"
            "status,completed_at,created_at"
        )
        .eq(
            "user_id",
            int(user_id),
        )
    )

    if plan_id is not None:
        query = query.eq(
            "plan_id",
            int(plan_id),
        )

    if task_date is not None:
        query = query.eq(
            "task_date",
            str(task_date),
        )

    if status:
        query = query.eq(
            "status",
            status,
        )

    result = (
        query
        .order(
            "task_date"
        )
        .limit(limit)
        .execute()
    )

    return result.data or []


def create_revision_plan(
    user_id,
    exam,
    topics,
):
    today = datetime.now(
        SRI_LANKA_TZ
    ).date()

    exam_date = _local_exam_date(
        exam[
            "exam_at"
        ]
    )

    end_date = (
        exam_date
        - timedelta(days=1)
    )

    if end_date < today:
        end_date = today

    plan_result = (
        supabase
        .table("revision_plans")
        .insert(
            {
                "user_id": int(user_id),
                "exam_id": exam[
                    "id"
                ],
                "subject_id": exam.get(
                    "subject_id"
                ),
                "title": (
                    f"Revision — {exam['title']}"
                ),
                "start_date": today.isoformat(),
                "end_date": end_date.isoformat(),
                "status": "active",
            }
        )
        .execute()
    )

    if not plan_result.data:
        return None

    plan = plan_result.data[0]

    total_days = (
        end_date
        - today
    ).days + 1

    total_days = max(
        total_days,
        1,
    )

    task_rows = []

    for index, topic in enumerate(
        topics
    ):
        offset = (
            index
            % total_days
        )

        task_date = (
            today
            + timedelta(
                days=offset
            )
        )

        task_rows.append(
            {
                "user_id": int(
                    user_id
                ),
                "plan_id": plan[
                    "id"
                ],
                "task_date": (
                    task_date.isoformat()
                ),
                "topic": topic,
                "status": "pending",
            }
        )

    if task_rows:
        (
            supabase
            .table("revision_tasks")
            .insert(
                task_rows
            )
            .execute()
        )

    return plan


def complete_task(
    user_id,
    task_id,
):
    result = (
        supabase
        .table("revision_tasks")
        .select(
            "id,plan_id,status"
        )
        .eq(
            "user_id",
            int(user_id),
        )
        .eq(
            "id",
            int(task_id),
        )
        .limit(1)
        .execute()
    )

    if not result.data:
        return False

    plan_id = result.data[0][
        "plan_id"
    ]

    (
        supabase
        .table("revision_tasks")
        .update(
            {
                "status": "completed",
                "completed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
        )
        .eq(
            "user_id",
            int(user_id),
        )
        .eq(
            "id",
            int(task_id),
        )
        .execute()
    )

    remaining = get_tasks(
        user_id,
        plan_id=plan_id,
        status="pending",
        limit=1,
    )

    if not remaining:
        (
            supabase
            .table("revision_plans")
            .update(
                {
                    "status": "completed",
                }
            )
            .eq(
                "user_id",
                int(user_id),
            )
            .eq(
                "id",
                int(plan_id),
            )
            .execute()
        )

    return True


def delete_plan(
    user_id,
    plan_id,
):
    plan = get_plan(
        user_id,
        plan_id,
    )

    if not plan:
        return False

    (
        supabase
        .table("revision_plans")
        .delete()
        .eq(
            "user_id",
            int(user_id),
        )
        .eq(
            "id",
            int(plan_id),
        )
        .execute()
    )

    return True


def _subject_name(
    user_id,
    subject_id,
):
    if not subject_id:
        return "No Subject"

    subject = get_subject_by_id(
        user_id,
        subject_id,
    )

    return (
        subject_display(
            subject
        )
        if subject
        else "No Subject"
    )


def register_revision_planner_handlers(
    bot,
    show_main_menu,
):

    def show_revision_menu(
        chat_id
    ):
        revision_state.pop(
            chat_id,
            None,
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "➕ Create Revision Plan"
            ),
            types.KeyboardButton(
                "📚 My Revision Plans"
            ),
            types.KeyboardButton(
                "📅 Today's Revision"
            ),
            types.KeyboardButton(
                "✅ Complete Revision Task"
            ),
            types.KeyboardButton(
                "🗑 Delete Revision Plan"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "📚 Revision Planner\n\n"
                "Create a day-by-day revision plan from "
                "an upcoming exam and your topic list."
            ),
            reply_markup=markup,
        )

    @bot.message_handler(
        commands=["revision"]
    )
    def revision_command(
        message
    ):
        show_revision_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📚 Revision Planner"
    )
    def revision_button(
        message
    ):
        show_revision_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "➕ Create Revision Plan"
    )
    def create_plan_button(
        message
    ):
        exams = get_upcoming_exams(
            message.from_user.id
        )

        if not exams:
            bot.send_message(
                message.chat.id,
                (
                    "📝 No upcoming exams found.\n\n"
                    "Add an exam first using 📝 Exams."
                ),
            )
            return

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=1,
        )

        for exam in exams:
            exam_date = _local_exam_date(
                exam[
                    "exam_at"
                ]
            )

            markup.add(
                types.KeyboardButton(
                    (
                        f"📝 #{exam['id']} "
                        f"{exam['title']} "
                        f"({exam_date.strftime('%d-%m-%Y')})"
                    )
                )
            )

        markup.add(
            types.KeyboardButton(
                "🔙 Revision Menu"
            )
        )

        revision_state[
            message.chat.id
        ] = {
            "step": "exam"
        }

        bot.send_message(
            message.chat.id,
            "📝 Choose the exam:",
            reply_markup=markup,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📚 My Revision Plans"
    )
    def my_plans(
        message
    ):
        try:
            plans = get_plans(
                message.from_user.id,
                status=None,
            )

            if not plans:
                bot.send_message(
                    message.chat.id,
                    "📚 No revision plans yet.",
                )
                return

            parts = [
                "📚 MY REVISION PLANS\n"
            ]

            for plan in plans:
                tasks = get_tasks(
                    message.from_user.id,
                    plan_id=plan[
                        "id"
                    ],
                )

                completed = sum(
                    1
                    for task in tasks
                    if task[
                        "status"
                    ] == "completed"
                )

                total = len(
                    tasks
                )

                percent = (
                    round(
                        completed
                        / total
                        * 100
                    )
                    if total
                    else 0
                )

                status = (
                    "✅ Completed"
                    if plan[
                        "status"
                    ] == "completed"
                    else "📖 Active"
                )

                parts.append(
                    (
                        f"\n#{plan['id']} "
                        f"{plan['title']}\n"
                        f"{status}\n"
                        f"📚 "
                        f"{_subject_name(message.from_user.id, plan.get('subject_id'))}\n"
                        f"📅 {plan['start_date']} → {plan['end_date']}\n"
                        f"📊 {completed}/{total} tasks "
                        f"({percent}%)\n"
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
                "List revision plans error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not load revision plans.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "📅 Today's Revision"
    )
    def today_revision(
        message
    ):
        try:
            today = datetime.now(
                SRI_LANKA_TZ
            ).date()

            tasks = get_tasks(
                message.from_user.id,
                task_date=today,
                limit=100,
            )

            pending = [
                task
                for task in tasks
                if task[
                    "status"
                ] == "pending"
            ]

            completed = [
                task
                for task in tasks
                if task[
                    "status"
                ] == "completed"
            ]

            parts = [
                (
                    "📅 TODAY'S REVISION\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    f"📆 {today.strftime('%d-%m-%Y')}"
                )
            ]

            if pending:
                parts.append(
                    "\n\n📖 TO DO"
                )

                for task in pending:
                    parts.append(
                        (
                            f"\n• #{task['id']} "
                            f"{task['topic']}"
                        )
                    )

            if completed:
                parts.append(
                    "\n\n✅ COMPLETED"
                )

                for task in completed:
                    parts.append(
                        (
                            f"\n• #{task['id']} "
                            f"{task['topic']}"
                        )
                    )

            if not tasks:
                parts.append(
                    "\n\n✅ No revision tasks scheduled today."
                )

            bot.send_message(
                message.chat.id,
                "".join(parts),
            )

        except Exception as error:
            print(
                "Today's revision error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not load today's revision.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "✅ Complete Revision Task"
    )
    def complete_task_button(
        message
    ):
        revision_state[
            message.chat.id
        ] = {
            "step": "complete"
        }

        bot.send_message(
            message.chat.id,
            (
                "✅ Send the revision task number.\n"
                "Example: 12"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🗑 Delete Revision Plan"
    )
    def delete_plan_button(
        message
    ):
        revision_state[
            message.chat.id
        ] = {
            "step": "delete"
        }

        bot.send_message(
            message.chat.id,
            (
                "🗑 Send the revision plan number.\n"
                "Example: 3"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔙 Revision Menu"
    )
    def back_revision_menu(
        message
    ):
        show_revision_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.chat.id in revision_state,
        content_types=["text"],
    )
    def revision_state_handler(
        message
    ):
        chat_id = message.chat.id
        text = (
            message.text
            or ""
        ).strip()

        if text == "🏠 Main Menu":
            revision_state.pop(
                chat_id,
                None,
            )

            show_main_menu(
                chat_id,
                message.from_user.first_name
                or "Friend",
            )
            return

        if text == "🔙 Revision Menu":
            show_revision_menu(
                chat_id
            )
            return

        if (
            text.startswith("/")
            or text in GLOBAL_BUTTONS
        ):
            revision_state.pop(
                chat_id,
                None,
            )
            return ContinueHandling()

        state = revision_state.get(
            chat_id,
            {}
        )

        step = state.get(
            "step"
        )

        if step == "exam":
            if not text.startswith(
                "📝 #"
            ):
                bot.send_message(
                    chat_id,
                    "❌ Choose an exam using the buttons.",
                )
                return

            try:
                exam_id = int(
                    text.split(
                        " ",
                        2,
                    )[1].replace(
                        "#",
                        ""
                    )
                )

            except Exception:
                bot.send_message(
                    chat_id,
                    "❌ Invalid exam selection.",
                )
                return

            exam = get_exam(
                message.from_user.id,
                exam_id,
            )

            if not exam:
                bot.send_message(
                    chat_id,
                    "❌ Exam not found.",
                )
                return

            state[
                "exam"
            ] = exam

            state[
                "step"
            ] = "topics"

            bot.send_message(
                chat_id,
                (
                    "📚 Send the topics you need to revise.\n\n"
                    "Put ONE topic per line.\n\n"
                    "Example:\n"
                    "Introduction\n"
                    "Chapter 1\n"
                    "Chapter 2\n"
                    "Past paper questions"
                ),
            )
            return

        if step == "topics":
            topics = [
                line.strip()
                for line in text.splitlines()
                if line.strip()
            ]

            if not topics:
                bot.send_message(
                    chat_id,
                    "❌ Add at least one topic.",
                )
                return

            if len(
                topics
            ) > 100:
                bot.send_message(
                    chat_id,
                    "❌ Maximum 100 topics per revision plan.",
                )
                return

            try:
                plan = create_revision_plan(
                    user_id=message.from_user.id,
                    exam=state[
                        "exam"
                    ],
                    topics=topics,
                )

                revision_state.pop(
                    chat_id,
                    None,
                )

                if not plan:
                    raise RuntimeError(
                        "Revision plan was not saved."
                    )

                bot.send_message(
                    chat_id,
                    (
                        "✅ Revision plan created!\n\n"
                        f"📚 {plan['title']}\n"
                        f"📅 {plan['start_date']} → "
                        f"{plan['end_date']}\n"
                        f"📖 Topics: {len(topics)}\n\n"
                        "Topics were distributed across "
                        "the available revision days."
                    ),
                )

                show_revision_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Create revision plan error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not create revision plan.",
                )

            return

        if step == "complete":
            try:
                task_id = int(
                    text.replace(
                        "#",
                        ""
                    )
                )

            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Send only the task number.",
                )
                return

            try:
                success = complete_task(
                    message.from_user.id,
                    task_id,
                )

                if not success:
                    bot.send_message(
                        chat_id,
                        "❌ Revision task not found.",
                    )
                    return

                revision_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    "✅ Revision task completed!",
                )

                show_revision_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Complete revision task error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not complete revision task.",
                )

            return

        if step == "delete":
            try:
                plan_id = int(
                    text.replace(
                        "#",
                        ""
                    )
                )

            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Send only the plan number.",
                )
                return

            try:
                success = delete_plan(
                    message.from_user.id,
                    plan_id,
                )

                if not success:
                    bot.send_message(
                        chat_id,
                        "❌ Revision plan not found.",
                    )
                    return

                revision_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    "✅ Revision plan deleted.",
                )

                show_revision_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Delete revision plan error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not delete revision plan.",
                )

            return
