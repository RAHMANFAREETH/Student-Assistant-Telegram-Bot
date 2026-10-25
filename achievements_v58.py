"""Student Assistant Bot V5.8 — read-only achievements and learning milestones.

Uses V4–V5.4 study records. No paid API and no extra Supabase SQL.
Student progress is queried using the Telegram user_id, not the chat_id.
Badges are *live milestones*, not permanent claims: deletion resets counts.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, time as dt_time
from zoneinfo import ZoneInfo

from telebot import types

BUTTON_ACHIEVEMENTS = "🏆 Achievements"
BUTTON_LEVEL = "⭐ My Level"
TZ = ZoneInfo("Asia/Colombo")


@dataclass(frozen=True)
class Milestone:
    key: str
    emoji: str
    label: str
    metric: str
    threshold: int


MILESTONES = (
    Milestone("first_note", "📝", "First Note", "notes", 1),
    Milestone("notes_10", "📘", "10 Notes", "notes", 10),
    Milestone("first_cards", "🧠", "5 Flashcards", "cards", 5),
    Milestone("cards_25", "📚", "25 Flashcards", "cards", 25),
    Milestone("reviewed_5", "🔁", "5 Cards Reviewed", "reviewed", 5),
    Milestone("reviewed_20", "🎯", "20 Cards Reviewed", "reviewed", 20),
    Milestone("first_quiz", "❓", "First Quiz", "quizzes", 1),
    Milestone("quizzes_5", "🏅", "5 Quizzes", "quizzes", 5),
    Milestone("perfect_quiz", "💯", "Perfect Quiz", "perfect_quizzes", 1),
    Milestone("first_assignment", "✅", "First Assignment Completed", "assignments", 1),
    Milestone("assignments_10", "📅", "10 Assignments Completed", "assignments", 10),
    Milestone("first_goal", "🎯", "First Goal Completed", "goals", 1),
    Milestone("goals_5", "🌟", "5 Goals Completed", "goals", 5),
    Milestone("first_session", "⏱", "First Focus Session", "sessions", 1),
    Milestone("sessions_10", "⏳", "10 Focus Sessions", "sessions", 10),
    Milestone("streak_3", "🔥", "3-Day Study Streak", "streak", 3),
    Milestone("streak_7", "🏆", "7-Day Study Streak", "streak", 7),
)

# XP is a friendly *current-record score*; it is not a cash reward or
# a permanent ledger. Reading /achievements repeatedly never earns XP.
XP_WEIGHTS = {
    "notes": 10,
    "cards": 5,
    "reviewed": 5,
    "quizzes": 20,
    "perfect_quizzes": 50,
    "assignments": 30,
    "goals": 40,
    "sessions": 15,
}
XP_PER_LEVEL = 250


class ProgressUnavailable(RuntimeError):
    """Some progress records could not be loaded; never report false zeroes."""


def count_records(client, table, user_id, *, equals=None, minimum=None):
    """Exact server-side count, not a capped select of returned rows."""
    query = client.table(table).select("id" if table != "flashcard_reviews" else "flashcard_id", count="exact")
    query = query.eq("user_id", int(user_id))
    for key, val in (equals or {}).items():
        query = query.eq(key, val)
    for key, val in (minimum or {}).items():
        query = query.gte(key, val)
    result = query.limit(1).execute()
    if result.count is None:
        raise ProgressUnavailable(f"Exact count unavailable for {table}")
    return max(0, int(result.count))


def session_minutes(row):
    value = row.get("actual_minutes")
    if value is None:
        value = row.get("planned_minutes")
    return max(0, int(value or 0))


def parse_timestamp(value):
    if not isinstance(value, str):
        raise ProgressUnavailable("Missing study-session timestamp")
    value = value.replace("Z", "+00:00")
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ProgressUnavailable("Invalid study-session timestamp") from exc
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(TZ)


def compute_streak(daily_minutes, target, *, today):
    """Current streak, allowing unfinished today to inherit yesterday."""
    goal = max(1, int(target))
    first_offset = 0 if daily_minutes.get(today, 0) >= goal else 1
    streak = 0
    for offset in range(first_offset, 8):
        day = today - timedelta(days=offset)
        if daily_minutes.get(day, 0) >= goal:
            streak += 1
        else:
            break
    return min(7, streak)


def recent_streak(client, user_id, *, now=None):
    now = now or datetime.now(TZ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=TZ)
    now = now.astimezone(TZ)
    today = now.date()
    start = datetime.combine(today - timedelta(days=7), dt_time.min, tzinfo=TZ)
    start_iso = start.astimezone(timezone.utc).isoformat()

    pref = (client.table("study_preferences").select("daily_target_minutes")
            .eq("user_id", int(user_id)).limit(1).execute())
    settings = pref.data or []
    target = int((settings[0].get("daily_target_minutes") if settings else None) or 60)
    daily = {}
    size = 300
    # Bounded pagination; fail clearly instead of incorrectly undercounting.
    for page in range(10):
        rows = (client.table("study_sessions")
                .select("started_at,actual_minutes,planned_minutes")
                .eq("user_id", int(user_id))
                .eq("status", "completed")
                .gte("started_at", start_iso)
                .order("started_at", desc=True)
                .range(page * size, (page + 1) * size - 1)
                .execute()).data or []
        for entry in rows:
            day = parse_timestamp(entry.get("started_at")).date()
            if day > today or day < today - timedelta(days=7):
                continue
            daily[day] = daily.get(day, 0) + session_minutes(entry)
        if len(rows) < size:
            return compute_streak(daily, target, today=today)
    raise ProgressUnavailable("Too many recent sessions to calculate accurate streak")


def collect_metrics(client, user_id, *, now=None):
    if int(user_id) <= 0:
        raise ValueError("Invalid Telegram user ID")
    metrics = {
        "notes": count_records(client, "notes", user_id),
        "cards": count_records(client, "flashcards", user_id),
        "reviewed": count_records(client, "flashcard_reviews", user_id,
                                  minimum={"review_count": 1}),
        "quizzes": count_records(client, "quiz_attempts", user_id),
        "perfect_quizzes": count_records(client, "quiz_attempts", user_id,
                                         minimum={"score_percent": 100}),
        "assignments": count_records(client, "assignments", user_id,
                                     equals={"status": "completed"}),
        "goals": count_records(client, "study_goals", user_id,
                               equals={"status": "completed"}),
        "sessions": count_records(client, "study_sessions", user_id,
                                  equals={"status": "completed"}),
        "streak": recent_streak(client, user_id, now=now),
    }
    return metrics


def evaluate(metrics):
    unlocked = [m for m in MILESTONES if metrics[m.metric] >= m.threshold]
    locked = [m for m in MILESTONES if metrics[m.metric] < m.threshold]
    xp = sum(min(100000, metrics[k]) * weight for k, weight in XP_WEIGHTS.items())
    level = 1 + xp // XP_PER_LEVEL
    return {
        "unlocked": unlocked,
        "locked": locked,
        "xp": xp,
        "level": level,
        "level_xp": xp % XP_PER_LEVEL,
        "remaining": XP_PER_LEVEL - xp % XP_PER_LEVEL,
    }


STRINGS = {
    "en": {"title": "🏆 Your Study Achievements", "level": "⭐ Your Learning Level",
           "unlocked": "Unlocked", "next": "Next milestones", "score": "Current learning score",
           "privacy": "🔒 Open a private chat with the bot to view your personal achievements.",
           "unavailable": "⚠️ Progress is temporarily unavailable. Please try again later.",
           "notice": "Calculated from your saved study records; deleting records or breaking a streak can change badges and XP.",
           "menu": "Select an option:", "remaining": "XP to next level"},
    "ta": {"title": "🏆 உங்கள் படிப்பு சாதனைகள்", "level": "⭐ உங்கள் கற்றல் நிலை",
           "unlocked": "கிடைத்த பதக்கங்கள்", "next": "அடுத்த இலக்குகள்", "score": "தற்போதைய கற்றல் புள்ளிகள்",
           "privacy": "🔒 தனிப்பட்ட சாதனைகளைப் பார்க்க bot உடன் private chat திறக்கவும்.",
           "unavailable": "⚠️ தற்போது முன்னேற்றத்தைக் காட்ட முடியவில்லை. பின்னர் முயற்சிக்கவும்.",
           "notice": "சேமித்த தரவுகளிலிருந்து கணக்கிடப்படுகிறது; தரவு நீக்கப்பட்டாலும் streak முறிந்தாலும் மதிப்பெண் மாறலாம்.",
           "menu": "ஒரு விருப்பத்தைத் தேர்ந்தெடுக்கவும்:", "remaining": "அடுத்த நிலைக்கு தேவையான XP"},
    "si": {"title": "🏆 ඔබේ අධ්‍යයන ජයග්‍රහණ", "level": "⭐ ඉගෙනුම් මට්ටම",
           "unlocked": "ලබාගත් පදක්කම්", "next": "මීළඟ ඉලක්ක", "score": "වත්මන් ඉගෙනුම් ලකුණු",
           "privacy": "🔒 පෞද්ගලික ජයග්‍රහණ බැලීමට bot සමඟ private chat එකක් විවෘත කරන්න.",
           "unavailable": "⚠️ මේ මොහොතේ ප්‍රගතිය ලබාගත නොහැක. නැවත උත්සාහ කරන්න.",
           "notice": "සුරැකි ඉගෙනුම් දත්ත මත ගණනය වේ; දත්ත ඉවත් කළහොත් හෝ streak බිඳුණහොත් වෙනස් විය හැක.",
           "menu": "විකල්පයක් තෝරන්න:", "remaining": "ඊළඟ මට්ටමට XP"},
    "ar": {"title": "🏆 إنجازاتك الدراسية", "level": "⭐ مستواك الدراسي",
           "unlocked": "الإنجازات المكتسبة", "next": "الأهداف التالية", "score": "نقاط التعلم الحالية",
           "privacy": "🔒 افتح محادثة خاصة مع البوت لعرض إنجازاتك الشخصية.",
           "unavailable": "⚠️ تعذر عرض التقدم حاليًا. حاول مرة أخرى لاحقًا.",
           "notice": "تُحسب من سجلات الدراسة المحفوظة؛ قد تتغير عند حذف السجلات أو انقطاع سلسلة الدراسة.",
           "menu": "اختر خيارًا:", "remaining": "نقاط XP للمستوى التالي"},
}


def format_achievements(metrics, language="en"):
    lang = STRINGS.get(language, STRINGS["en"])
    result = evaluate(metrics)
    lines = [lang["title"], "", f'{lang["unlocked"]}: {len(result["unlocked"])}/{len(MILESTONES)}', ""]
    lines += [f"{m.emoji} {m.label} ✅" for m in result["unlocked"]]
    lines.extend(["", lang["next"] + ":"])
    candidates = sorted(result["locked"], key=lambda m: (m.threshold-metrics[m.metric])/m.threshold)
    for badge in candidates[:4]:
        lines.append(f"▫️ {badge.emoji} {badge.label}: {metrics[badge.metric]}/{badge.threshold}")
    if not candidates:
        lines.append("🎉 All current milestones reached!")
    lines.extend(["", f'{lang["score"]}: {result["xp"]} XP', "", lang["notice"]])
    return "\n".join(lines)


def format_level(metrics, language="en"):
    lang = STRINGS.get(language, STRINGS["en"])
    result = evaluate(metrics)
    bars = result["level_xp"] * 10 // XP_PER_LEVEL
    return "\n".join([
        lang["level"], "", f'Level {result["level"]}',
        f'{result["xp"]} XP',
        "█" * bars + "░" * (10 - bars) + f'  {result["level_xp"]}/{XP_PER_LEVEL}',
        f'{result["remaining"]} {lang["remaining"]}', "", lang["notice"],
    ])


def register_achievements_v58_handlers(bot, show_main_menu):
    """Register before legacy stateful handlers, after V5.7 category handlers."""
    def on_action(message, level=False):
        try:
            from ui_v57 import get_language
            lang_code = get_language(message.from_user.id)
        except Exception:
            lang_code = "en"
        language = STRINGS.get(lang_code, STRINGS["en"])
        if getattr(message.chat, "type", "private") != "private":
            bot.send_message(message.chat.id, language["privacy"])
            return
        try:
            from db import supabase
            metrics = collect_metrics(supabase, message.from_user.id)
            output = format_level(metrics, lang_code) if level else format_achievements(metrics, lang_code)
        except Exception as exc:
            # No keys, database contents or student details in logs.
            print("V5.8 achievements unavailable:", type(exc).__name__, flush=True)
            bot.send_message(message.chat.id, language["unavailable"])
            return
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.row(types.KeyboardButton(BUTTON_ACHIEVEMENTS), types.KeyboardButton(BUTTON_LEVEL))
        markup.row(types.KeyboardButton("📊 My Progress"), types.KeyboardButton("🏠 Main Menu"))
        bot.send_message(message.chat.id, output, reply_markup=markup)

    @bot.message_handler(commands=["achievements", "badges"])
    def achievements_command(message):
        on_action(message)

    @bot.message_handler(commands=["level", "xp"])
    def level_command(message):
        on_action(message, level=True)

    @bot.message_handler(func=lambda m: getattr(m, "text", "") in {BUTTON_ACHIEVEMENTS, BUTTON_LEVEL})
    def achievements_buttons(message):
        on_action(message, level=message.text == BUTTON_LEVEL)

    return True
