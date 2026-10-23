from datetime import datetime, timezone

from telebot import types
from telebot.handler_backends import ContinueHandling

from db import supabase
from subjects import (
    get_subjects,
    get_subject_by_id,
    subject_display,
)
from semesters import (
    get_semesters,
    get_semester,
    get_active_semester,
)


grade_state = {}


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
    "📊 Dashboard",
    "📈 Progress",
    "ℹ️ Help",
}


def get_results(
    user_id,
    semester_id=None,
    limit=100,
):
    query = (
        supabase
        .table("course_results")
        .select(
            "id,user_id,semester_id,subject_id,subject_name,"
            "credits,grade_label,grade_points,score_percent,"
            "created_at,updated_at"
        )
        .eq("user_id", int(user_id))
    )

    if semester_id is not None:
        query = query.eq(
            "semester_id",
            int(semester_id),
        )

    result = (
        query
        .order(
            "updated_at",
            desc=True,
        )
        .limit(limit)
        .execute()
    )

    return result.data or []


def get_result(
    user_id,
    result_id,
):
    result = (
        supabase
        .table("course_results")
        .select(
            "id,user_id,semester_id,subject_id,subject_name,"
            "credits,grade_label,grade_points,score_percent"
        )
        .eq("user_id", int(user_id))
        .eq("id", int(result_id))
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def save_result(
    user_id,
    semester_id,
    subject_id,
    subject_name,
    credits,
    grade_label,
    grade_points,
    score_percent=None,
):
    payload = {
        "user_id": int(user_id),
        "semester_id": int(
            semester_id
        ),
        "subject_id": int(
            subject_id
        ),
        "subject_name": subject_name,
        "credits": float(
            credits
        ),
        "grade_label": (
            grade_label.strip()
            if grade_label
            else None
        ),
        "grade_points": float(
            grade_points
        ),
        "score_percent": (
            float(
                score_percent
            )
            if score_percent is not None
            else None
        ),
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    return (
        supabase
        .table("course_results")
        .upsert(
            payload,
            on_conflict=(
                "user_id,"
                "semester_id,"
                "subject_id"
            ),
        )
        .execute()
    )


def delete_result(
    user_id,
    result_id,
):
    result = get_result(
        user_id,
        result_id,
    )

    if not result:
        return False

    (
        supabase
        .table("course_results")
        .delete()
        .eq("user_id", int(user_id))
        .eq("id", int(result_id))
        .execute()
    )

    return True


def weighted_gpa(
    results
):
    total_credits = 0.0
    quality_points = 0.0

    for result in results:
        credits = float(
            result.get(
                "credits"
            )
            or 0
        )

        grade_points = float(
            result.get(
                "grade_points"
            )
            or 0
        )

        total_credits += credits
        quality_points += (
            credits
            * grade_points
        )

    if total_credits <= 0:
        return (
            0.0,
            0.0,
            0.0,
        )

    return (
        quality_points
        / total_credits,
        total_credits,
        quality_points,
    )


def semester_label(
    semester
):
    if not semester:
        return "Unknown Semester"

    return (
        f"#{semester['id']} "
        f"{semester['name']}"
    )


def parse_semester_button(
    text
):
    if not text.startswith(
        "🎓 #"
    ):
        return None

    try:
        return int(
            text.split(
                " ",
                2,
            )[1].replace(
                "#",
                ""
            )
        )

    except Exception:
        return None


def parse_subject_button(
    text
):
    if not text.startswith(
        "📚 #"
    ):
        return None

    try:
        return int(
            text.split(
                " ",
                2,
            )[1].replace(
                "#",
                ""
            )
        )

    except Exception:
        return None


def register_grade_handlers(
    bot,
    show_main_menu,
):

    def show_grade_menu(
        chat_id
    ):
        grade_state.pop(
            chat_id,
            None,
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2,
        )

        markup.add(
            types.KeyboardButton(
                "➕ Add / Update Result"
            ),
            types.KeyboardButton(
                "📋 Semester Results"
            ),
            types.KeyboardButton(
                "📊 GPA Summary"
            ),
            types.KeyboardButton(
                "🧮 Target GPA"
            ),
            types.KeyboardButton(
                "🗑 Delete Result"
            ),
            types.KeyboardButton(
                "🎓 Semesters"
            ),
            types.KeyboardButton(
                "🏠 Main Menu"
            ),
        )

        bot.send_message(
            chat_id,
            (
                "📊 Grades & GPA\n\n"
                "Enter each course's credits and grade point.\n"
                "The bot calculates weighted GPA using the "
                "GPA scale saved for that semester."
            ),
            reply_markup=markup,
        )

    def semester_keyboard(
        user_id,
        back_text="🔙 GPA Menu",
    ):
        semesters = get_semesters(
            user_id
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=1,
        )

        for semester in semesters:
            status = (
                " ⭐"
                if semester[
                    "status"
                ] == "active"
                else ""
            )

            markup.add(
                types.KeyboardButton(
                    (
                        f"🎓 #{semester['id']} "
                        f"{semester['name']}"
                        f"{status}"
                    )
                )
            )

        markup.add(
            types.KeyboardButton(
                back_text
            )
        )

        return (
            semesters,
            markup,
        )

    def subject_keyboard(
        user_id,
    ):
        subjects = get_subjects(
            user_id
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=1,
        )

        for subject in subjects:
            markup.add(
                types.KeyboardButton(
                    (
                        f"📚 #{subject['id']} "
                        f"{subject_display(subject)}"
                    )
                )
            )

        markup.add(
            types.KeyboardButton(
                "🔙 GPA Menu"
            )
        )

        return (
            subjects,
            markup,
        )

    @bot.message_handler(
        commands=["gpa"]
    )
    def gpa_command(
        message
    ):
        show_grade_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📊 Grades & GPA"
    )
    def grade_button(
        message
    ):
        show_grade_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "➕ Add / Update Result"
    )
    def add_result(
        message
    ):
        semesters, markup = (
            semester_keyboard(
                message.from_user.id
            )
        )

        if not semesters:
            bot.send_message(
                message.chat.id,
                (
                    "🎓 Add a semester first."
                ),
            )
            return

        grade_state[
            message.chat.id
        ] = {
            "step": "semester"
        }

        bot.send_message(
            message.chat.id,
            "🎓 Choose the semester:",
            reply_markup=markup,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📋 Semester Results"
    )
    def semester_results_button(
        message
    ):
        semesters, markup = (
            semester_keyboard(
                message.from_user.id
            )
        )

        if not semesters:
            bot.send_message(
                message.chat.id,
                "🎓 Add a semester first.",
            )
            return

        grade_state[
            message.chat.id
        ] = {
            "step": "list_semester"
        }

        bot.send_message(
            message.chat.id,
            "🎓 Choose a semester:",
            reply_markup=markup,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "📊 GPA Summary"
    )
    def gpa_summary(
        message
    ):
        try:
            semesters = get_semesters(
                message.from_user.id
            )

            if not semesters:
                bot.send_message(
                    message.chat.id,
                    "🎓 No semesters found.",
                )
                return

            parts = [
                "📊 GPA SUMMARY\n"
                "━━━━━━━━━━━━━━━━━━"
            ]

            scale_values = set()
            all_results = []

            for semester in reversed(
                semesters
            ):
                results = get_results(
                    message.from_user.id,
                    semester_id=semester[
                        "id"
                    ],
                )

                if not results:
                    continue

                gpa, credits, _ = (
                    weighted_gpa(
                        results
                    )
                )

                scale = float(
                    semester[
                        "gpa_scale"
                    ]
                )

                scale_values.add(
                    round(
                        scale,
                        6,
                    )
                )

                all_results.extend(
                    results
                )

                parts.append(
                    (
                        f"\n\n🎓 {semester['name']}\n"
                        f"📊 GPA: {gpa:.3f} / {scale:g}\n"
                        f"🎯 Credits: {credits:g}\n"
                        f"📚 Courses: {len(results)}"
                    )
                )

            if not all_results:
                bot.send_message(
                    message.chat.id,
                    "📊 No course results saved yet.",
                )
                return

            if len(
                scale_values
            ) == 1:
                cumulative, total_credits, _ = (
                    weighted_gpa(
                        all_results
                    )
                )

                scale = next(
                    iter(
                        scale_values
                    )
                )

                parts.append(
                    (
                        "\n\n━━━━━━━━━━━━━━━━━━\n"
                        "🏆 CUMULATIVE\n"
                        f"📊 GPA: {cumulative:.3f} / {scale:g}\n"
                        f"🎯 Total Credits: {total_credits:g}"
                    )
                )

            else:
                parts.append(
                    (
                        "\n\n⚠️ Cumulative GPA not combined "
                        "because your semesters use different "
                        "GPA scales."
                    )
                )

            bot.send_message(
                message.chat.id,
                "\n".join(parts),
            )

        except Exception as error:
            print(
                "GPA summary error:",
                repr(error),
            )

            bot.send_message(
                message.chat.id,
                "❌ Could not calculate GPA.",
            )

    @bot.message_handler(
        func=lambda m:
        m.text == "🧮 Target GPA"
    )
    def target_gpa(
        message
    ):
        semesters, markup = (
            semester_keyboard(
                message.from_user.id
            )
        )

        if not semesters:
            bot.send_message(
                message.chat.id,
                "🎓 Add a semester first.",
            )
            return

        grade_state[
            message.chat.id
        ] = {
            "step": "target_semester"
        }

        bot.send_message(
            message.chat.id,
            (
                "🧮 Choose the semester for the "
                "Target GPA Calculator:"
            ),
            reply_markup=markup,
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🗑 Delete Result"
    )
    def delete_result_button(
        message
    ):
        grade_state[
            message.chat.id
        ] = {
            "step": "delete"
        }

        bot.send_message(
            message.chat.id,
            (
                "🗑 Send the result number.\n"
                "Example: 6"
            ),
        )

    @bot.message_handler(
        func=lambda m:
        m.text == "🔙 GPA Menu"
    )
    def back_gpa_menu(
        message
    ):
        show_grade_menu(
            message.chat.id
        )

    @bot.message_handler(
        func=lambda m:
        m.chat.id in grade_state,
        content_types=["text"],
    )
    def grade_state_handler(
        message
    ):
        chat_id = message.chat.id
        text = (
            message.text
            or ""
        ).strip()

        if text == "🏠 Main Menu":
            grade_state.pop(
                chat_id,
                None,
            )

            show_main_menu(
                chat_id,
                message.from_user.first_name
                or "Friend",
            )
            return

        if text == "🔙 GPA Menu":
            show_grade_menu(
                chat_id
            )
            return

        if (
            text.startswith("/")
            or text in GLOBAL_BUTTONS
        ):
            grade_state.pop(
                chat_id,
                None,
            )
            return ContinueHandling()

        state = grade_state.get(
            chat_id,
            {}
        )

        step = state.get(
            "step"
        )

        if step in {
            "semester",
            "list_semester",
            "target_semester",
        }:
            semester_id = parse_semester_button(
                text
            )

            semester = (
                get_semester(
                    message.from_user.id,
                    semester_id,
                )
                if semester_id
                else None
            )

            if not semester:
                bot.send_message(
                    chat_id,
                    "❌ Choose a semester using the buttons.",
                )
                return

            if step == "list_semester":
                grade_state.pop(
                    chat_id,
                    None,
                )

                results = get_results(
                    message.from_user.id,
                    semester_id=semester_id,
                )

                if not results:
                    bot.send_message(
                        chat_id,
                        (
                            f"📋 {semester['name']}\n\n"
                            "No results saved yet."
                        ),
                    )

                    show_grade_menu(
                        chat_id
                    )
                    return

                gpa, credits, _ = weighted_gpa(
                    results
                )

                parts = [
                    (
                        f"📋 {semester['name']}\n"
                        f"📊 GPA: {gpa:.3f} / "
                        f"{float(semester['gpa_scale']):g}\n"
                        f"🎯 Credits: {credits:g}\n"
                    )
                ]

                for result in results:
                    score = (
                        f"\n💯 {float(result['score_percent']):g}%"
                        if result.get(
                            "score_percent"
                        ) is not None
                        else ""
                    )

                    label = (
                        result.get(
                            "grade_label"
                        )
                        or "No label"
                    )

                    parts.append(
                        (
                            f"\n#{result['id']} "
                            f"{result['subject_name']}\n"
                            f"🎯 Credits: "
                            f"{float(result['credits']):g}\n"
                            f"🏷 Grade: {label}\n"
                            f"📊 Grade Point: "
                            f"{float(result['grade_points']):g}"
                            f"{score}\n"
                        )
                    )

                bot.send_message(
                    chat_id,
                    "\n".join(parts),
                )

                show_grade_menu(
                    chat_id
                )
                return

            if step == "target_semester":
                state[
                    "semester_id"
                ] = semester_id

                state[
                    "semester"
                ] = semester

                state[
                    "step"
                ] = "target_gpa_value"

                bot.send_message(
                    chat_id,
                    (
                        f"📊 GPA Scale: "
                        f"{float(semester['gpa_scale']):g}\n\n"
                        "🎯 What semester GPA do you want?\n\n"
                        "Example: 3.5"
                    ),
                )
                return

            state[
                "semester_id"
            ] = semester_id

            state[
                "semester"
            ] = semester

            subjects, markup = (
                subject_keyboard(
                    message.from_user.id
                )
            )

            if not subjects:
                grade_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    "📚 Add a subject first.",
                )
                return

            state[
                "step"
            ] = "subject"

            bot.send_message(
                chat_id,
                "📚 Choose the course/subject:",
                reply_markup=markup,
            )
            return

        if step == "subject":
            subject_id = parse_subject_button(
                text
            )

            subject = (
                get_subject_by_id(
                    message.from_user.id,
                    subject_id,
                )
                if subject_id
                else None
            )

            if not subject:
                bot.send_message(
                    chat_id,
                    "❌ Choose a subject using the buttons.",
                )
                return

            state[
                "subject_id"
            ] = subject_id

            state[
                "subject_name"
            ] = subject_display(
                subject
            )

            state[
                "step"
            ] = "credits"

            bot.send_message(
                chat_id,
                (
                    "🎯 Enter the course credit value.\n\n"
                    "Examples:\n"
                    "3\n"
                    "2.5"
                ),
            )
            return

        if step == "credits":
            try:
                credits = float(
                    text
                )

            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Enter credits as a number.",
                )
                return

            if not 0 < credits <= 100:
                bot.send_message(
                    chat_id,
                    "❌ Credits must be greater than 0.",
                )
                return

            state[
                "credits"
            ] = credits

            state[
                "step"
            ] = "grade_label"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
            )

            markup.add(
                types.KeyboardButton(
                    "⏭ Skip Grade Label"
                ),
                types.KeyboardButton(
                    "🔙 GPA Menu"
                ),
            )

            bot.send_message(
                chat_id,
                (
                    "🏷 Enter the grade label.\n\n"
                    "Examples:\n"
                    "A\n"
                    "A-\n"
                    "B+\n\n"
                    "Or choose ⏭ Skip Grade Label."
                ),
                reply_markup=markup,
            )
            return

        if step == "grade_label":
            state[
                "grade_label"
            ] = (
                None
                if text == "⏭ Skip Grade Label"
                else text
            )

            state[
                "step"
            ] = "grade_points"

            semester = state[
                "semester"
            ]

            bot.send_message(
                chat_id,
                (
                    "📊 Enter the grade point for this course.\n\n"
                    f"Your semester GPA scale is "
                    f"{float(semester['gpa_scale']):g}.\n\n"
                    "Example: 3.7"
                ),
            )
            return

        if step == "grade_points":
            try:
                points = float(
                    text
                )

            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Enter grade points as a number.",
                )
                return

            scale = float(
                state[
                    "semester"
                ][
                    "gpa_scale"
                ]
            )

            if not 0 <= points <= scale:
                bot.send_message(
                    chat_id,
                    (
                        f"❌ Grade point must be between "
                        f"0 and {scale:g}."
                    ),
                )
                return

            state[
                "grade_points"
            ] = points

            state[
                "step"
            ] = "score"

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
            )

            markup.add(
                types.KeyboardButton(
                    "⏭ Skip Score"
                ),
                types.KeyboardButton(
                    "🔙 GPA Menu"
                ),
            )

            bot.send_message(
                chat_id,
                (
                    "💯 Enter score percentage if you have it.\n\n"
                    "Example: 78.5\n\n"
                    "Or choose ⏭ Skip Score."
                ),
                reply_markup=markup,
            )
            return

        if step == "score":
            if text == "⏭ Skip Score":
                score = None
            else:
                try:
                    score = float(
                        text
                    )

                except ValueError:
                    bot.send_message(
                        chat_id,
                        "❌ Enter a percentage number.",
                    )
                    return

                if not 0 <= score <= 100:
                    bot.send_message(
                        chat_id,
                        "❌ Percentage must be 0–100.",
                    )
                    return

            try:
                save_result(
                    user_id=message.from_user.id,
                    semester_id=state[
                        "semester_id"
                    ],
                    subject_id=state[
                        "subject_id"
                    ],
                    subject_name=state[
                        "subject_name"
                    ],
                    credits=state[
                        "credits"
                    ],
                    grade_label=state.get(
                        "grade_label"
                    ),
                    grade_points=state[
                        "grade_points"
                    ],
                    score_percent=score,
                )

                semester_name = state[
                    "semester"
                ][
                    "name"
                ]

                subject_name = state[
                    "subject_name"
                ]

                grade_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    (
                        "✅ Course result saved!\n\n"
                        f"🎓 {semester_name}\n"
                        f"📚 {subject_name}\n"
                        f"🎯 Credits: "
                        f"{state['credits']:g}\n"
                        f"📊 Grade Point: "
                        f"{state['grade_points']:g}"
                    ),
                )

                show_grade_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Save course result error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not save course result.",
                )

            return

        if step == "target_gpa_value":
            try:
                target = float(
                    text
                )

            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Enter a number such as 3.5.",
                )
                return

            scale = float(
                state[
                    "semester"
                ][
                    "gpa_scale"
                ]
            )

            if not 0 <= target <= scale:
                bot.send_message(
                    chat_id,
                    (
                        f"❌ Target GPA must be between "
                        f"0 and {scale:g}."
                    ),
                )
                return

            state[
                "target_gpa"
            ] = target

            state[
                "step"
            ] = "remaining_credits"

            bot.send_message(
                chat_id,
                (
                    "🎯 Enter the number of credits "
                    "you still have remaining in this semester.\n\n"
                    "Example: 12"
                ),
            )
            return

        if step == "remaining_credits":
            try:
                remaining = float(
                    text
                )

            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Enter remaining credits as a number.",
                )
                return

            if remaining <= 0:
                bot.send_message(
                    chat_id,
                    "❌ Remaining credits must be greater than 0.",
                )
                return

            semester = state[
                "semester"
            ]

            results = get_results(
                message.from_user.id,
                semester_id=semester[
                    "id"
                ],
            )

            current_gpa, completed_credits, quality = (
                weighted_gpa(
                    results
                )
            )

            target = state[
                "target_gpa"
            ]

            required_quality = (
                target
                * (
                    completed_credits
                    + remaining
                )
                - quality
            )

            required_average = (
                required_quality
                / remaining
            )

            scale = float(
                semester[
                    "gpa_scale"
                ]
            )

            grade_state.pop(
                chat_id,
                None,
            )

            if not results:
                bot.send_message(
                    chat_id,
                    (
                        "🧮 TARGET GPA\n"
                        "━━━━━━━━━━━━━━━━━━\n\n"
                        f"🎓 {semester['name']}\n"
                        f"🎯 Target GPA: {target:.3f}\n"
                        f"📚 Remaining Credits: {remaining:g}\n\n"
                        f"📊 Required average grade point: "
                        f"{target:.3f} / {scale:g}\n\n"
                        "Because no completed course results are "
                        "saved yet, your required average equals "
                        "your target GPA."
                    ),
                )

                show_grade_menu(
                    chat_id
                )
                return

            if required_average <= 0:
                conclusion = (
                    "✅ Your current results are already strong "
                    "enough to remain at or above this target "
                    "even with a very low average on the "
                    "remaining credits."
                )

            elif required_average > scale:
                conclusion = (
                    "⚠️ This target is mathematically unreachable "
                    "with the remaining credits on your current "
                    "GPA scale."
                )

            else:
                conclusion = (
                    f"🎯 You need an average grade point of "
                    f"{required_average:.3f} / {scale:g} "
                    f"across the remaining {remaining:g} credits."
                )

            bot.send_message(
                chat_id,
                (
                    "🧮 TARGET GPA CALCULATOR\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    f"🎓 {semester['name']}\n"
                    f"📊 Current GPA: "
                    f"{current_gpa:.3f} / {scale:g}\n"
                    f"✅ Completed Credits: "
                    f"{completed_credits:g}\n"
                    f"📚 Remaining Credits: "
                    f"{remaining:g}\n"
                    f"🎯 Target GPA: {target:.3f}\n\n"
                    f"{conclusion}"
                ),
            )

            show_grade_menu(
                chat_id
            )
            return

        if step == "delete":
            try:
                result_id = int(
                    text.replace(
                        "#",
                        ""
                    )
                )

            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Send only the result number.",
                )
                return

            try:
                success = delete_result(
                    message.from_user.id,
                    result_id,
                )

                if not success:
                    bot.send_message(
                        chat_id,
                        "❌ Result not found.",
                    )
                    return

                grade_state.pop(
                    chat_id,
                    None,
                )

                bot.send_message(
                    chat_id,
                    "✅ Course result deleted.",
                )

                show_grade_menu(
                    chat_id
                )

            except Exception as error:
                print(
                    "Delete result error:",
                    repr(error),
                )

                bot.send_message(
                    chat_id,
                    "❌ Could not delete result.",
                )

            return
