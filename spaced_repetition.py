"""Student Assistant V5.4 — non-destructive spaced-repetition extension.

Uses existing flashcards read-only and stores review progress in a separate
Supabase table. Never modifies or deletes an existing flashcard.
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from threading import RLock

from telebot import types
from db import supabase


DUE_REVIEWS = "🧠 Due Reviews"
MAX_CARDS = 500
SESSION_MINUTES = 30

# Keep sessions short-lived. Ratings and due dates live in Supabase, not RAM.
_sessions = {}
_lock = RLock()


def utcnow():
    return datetime.now(timezone.utc)


def _first(row, names):
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return str(value)
    return None


def _field_names(env_name, defaults):
    preferred = os.getenv(env_name, "").strip()
    return ([preferred] if preferred else []) + [x for x in defaults if x != preferred]


def _parse_date(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _fetch_owned_cards(user_id):
    """Read only this student's cards; never fall back to unfiltered access."""
    candidates = _field_names("FLASHCARD_USER_FIELD", ["user_id", "telegram_id", "chat_id", "student_id"])
    last_error = None
    for field in candidates:
        try:
            result = (supabase.table("flashcards").select("*")
                      .eq(field, user_id).range(0, MAX_CARDS - 1).execute())
            return result.data or []
        except Exception as exc:
            last_error = exc
            # Try the next candidate only when the field is missing.
            message = str(exc).lower()
            if not any(term in message for term in ("column", "schema cache", "42703")):
                raise
    raise RuntimeError("No supported owner field found in flashcards") from last_error


def _normalize_cards(rows):
    cards = []
    for row in rows:
        card_id = _first(row, _field_names("FLASHCARD_ID_FIELD", ["id", "flashcard_id", "card_id"]))
        front = _first(row, _field_names("FLASHCARD_FRONT_FIELD", ["question", "front", "front_text", "question_text", "front_side", "term", "word", "title"]))
        back = _first(row, _field_names("FLASHCARD_BACK_FIELD", ["answer", "back", "back_text", "answer_text", "back_side", "definition", "meaning", "description"]))
        if not card_id or not front or not back:
            continue
        subject = _first(row, ["subject_name", "subject", "topic"])
        if not subject:
            subject_id = row.get("subject_id")
            subject = f"Subject #{subject_id}" if subject_id is not None else "Unassigned"
        cards.append({"id": card_id, "front": front, "back": back,
                      "subject": subject})
    return cards


def _fetch_reviews(user_id):
    response = (supabase.table("flashcard_reviews").select("*")
                .eq("user_id", user_id).range(0, MAX_CARDS - 1).execute())
    return {str(x["flashcard_id"]): x for x in (response.data or [])}


def choose_due(cards, reviews, now=None):
    now = now or utcnow()
    pending = []
    for card in cards:
        previous = reviews.get(card["id"])
        due = _parse_date(previous.get("due_at")) if previous else None
        if due is None or due <= now:
            pending.append((due or datetime.min.replace(tzinfo=timezone.utc), card))
    pending.sort(key=lambda pair: pair[0])
    return [card for _, card in pending]


def next_schedule(previous, rating, now=None):
    """Return a reproducible, SM-2-inspired (not identical to Anki) schedule."""
    now = now or utcnow()
    if rating not in ("again", "hard", "good", "easy"):
        raise ValueError("Unknown rating")
    reps = int(previous.get("repetitions") or 0) if previous else 0
    interval = int(previous.get("interval_days") or 0) if previous else 0
    ease = float(previous.get("ease_factor") or 2.5) if previous else 2.5
    if rating == "again":
        reps = 0
        interval = 0
        ease = max(1.3, ease - 0.2)
        due = now + timedelta(minutes=10)
    elif rating == "hard":
        interval = max(1, round(interval * 1.2))
        ease = max(1.3, ease - 0.15)
        due = now + timedelta(days=interval)
    elif rating == "good":
        reps += 1
        interval = 3 if interval == 0 else max(3, round(interval * ease))
        due = now + timedelta(days=interval)
    else:
        reps += 1
        interval = 7 if interval == 0 else max(7, round(interval * (ease + 0.5)))
        ease = min(3.0, ease + 0.15)
        due = now + timedelta(days=interval)
    return {"repetitions": reps, "interval_days": interval,
            "ease_factor": round(ease, 2), "due_at": due.isoformat(),
            "last_reviewed_at": now.isoformat(), "last_rating": rating,
            "review_count": int(previous.get("review_count") or 0) + 1 if previous else 1}


def _load_data(user_id):
    cards = _normalize_cards(_fetch_owned_cards(user_id))
    reviews = _fetch_reviews(user_id)
    return cards, reviews


def _reply_error(bot, chat_id, label, error):
    print(f"V5.4 {label}: {type(error).__name__}: {error}")
    bot.send_message(chat_id, "❌ Review data could not be loaded. Check your Supabase "
                              "flashcard_reviews table and flashcard field mappings. "
                              "See README_V5_4.txt.")


def register_spaced_repetition_handlers(bot, show_main_menu):
    """Register BEFORE legacy modules that may have text catch-all handlers."""

    def send_next(chat_id, user_id):
        try:
            cards, reviews = _load_data(user_id)
            pending = choose_due(cards, reviews)
        except Exception as exc:
            _reply_error(bot, chat_id, "load", exc)
            return
        with _lock:
            _sessions.pop((chat_id, user_id), None)
        if not cards:
            bot.send_message(chat_id, "🧠 No compatible flashcards found in your account. "
                                      "Create cards using 🧠 Flashcards, then use /reviews. "
                                      "If cards exist, check field mappings in README_V5_4.txt.")
            return
        if not pending:
            bot.send_message(chat_id, "🎉 All caught up! No flashcards are due now.\n"
                                      "Use /reviewstats to see your progress.")
            return
        card = pending[0]
        token = secrets.token_hex(6)
        session = {"card": card, "token": token, "phase": "question", "created": utcnow()}
        with _lock:
            _sessions[(chat_id, user_id)] = session
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👁 Reveal Answer", callback_data=f"sr:s:{token}"))
        bot.send_message(chat_id, f"🧠 Due Review ({len(pending)} due)\n"
                                  f"📚 {card['subject']}\n\n❓ {card['front'][:2500]}",
                         reply_markup=markup)

    @bot.message_handler(commands=["reviews", "duereviews"])
    @bot.message_handler(func=lambda m: m.text == DUE_REVIEWS)
    def due_command(message):
        if message.chat.type != "private":
            bot.send_message(message.chat.id, "🔒 Please use /reviews in a private chat with this bot.")
            return
        send_next(message.chat.id, message.from_user.id)

    @bot.message_handler(commands=["reviewstats"])
    @bot.message_handler(func=lambda m: m.text == "📊 Review Stats")
    def review_stats(message):
        if message.chat.type != "private":
            bot.send_message(message.chat.id, "🔒 Please use /reviewstats in a private chat with this bot.")
            return
        try:
            cards, reviews = _load_data(message.from_user.id)
            due = len(choose_due(cards, reviews))
            reviewed = sum(1 for x in cards if x["id"] in reviews)
            mastered = sum(1 for x in cards if int(reviews.get(x["id"], {}).get("repetitions") or 0) >= 3)
            bot.send_message(message.chat.id,
                             f"📊 Flashcard Review Stats\n\n📚 Cards: {len(cards)}"
                             f"\n🧠 Reviewed: {reviewed}\n⏰ Due: {due}"
                             f"\n🏆 Strong recall (3+ good/easy repetitions): {mastered}"
                             "\n\nUse /reviews to study.")
        except Exception as exc:
            _reply_error(bot, message.chat.id, "stats", exc)

    @bot.callback_query_handler(func=lambda c: bool(c.data and c.data.startswith("sr:")))
    def review_callback(call):
        user_id = call.from_user.id
        chat_id = call.message.chat.id if call.message else None
        if chat_id is None:
            bot.answer_callback_query(call.id, "Open the bot chat to review.", show_alert=True)
            return
        parts = call.data.split(":")
        if len(parts) not in (3, 4):
            bot.answer_callback_query(call.id, "Invalid review action.")
            return
        action, token = parts[1], parts[2]
        with _lock:
            session = _sessions.get((chat_id, user_id))
            valid = (session is not None and session["token"] == token
                     and utcnow() - session["created"] <= timedelta(minutes=SESSION_MINUTES))
            if valid and action == "s" and session["phase"] == "question":
                session["phase"] = "answer"
                card = session["card"]
                phase = "show"
            elif valid and action == "r" and len(parts) == 4 and session["phase"] == "answer" and parts[3] in ("again", "hard", "good", "easy"):
                session["phase"] = "saving"
                card = session["card"]
                rating = parts[3]
                phase = "rate"
            else:
                phase = "stale"
        if phase == "stale":
            bot.answer_callback_query(call.id, "Review expired or already answered. Use /reviews.", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        if phase == "show":
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("🔴 Again", callback_data=f"sr:r:{token}:again"),
                types.InlineKeyboardButton("🟠 Hard", callback_data=f"sr:r:{token}:hard"),
                types.InlineKeyboardButton("🟢 Good", callback_data=f"sr:r:{token}:good"),
                types.InlineKeyboardButton("🔵 Easy", callback_data=f"sr:r:{token}:easy"),
            )
            bot.send_message(chat_id, f"✅ Answer:\n{card['back'][:2800]}\n\nHow well did you remember?",
                             reply_markup=markup)
            return
        try:
            existing = (supabase.table("flashcard_reviews").select("*")
                        .eq("user_id", user_id).eq("flashcard_id", card["id"]).limit(1).execute())
            previous = existing.data[0] if existing.data else None
            schedule = next_schedule(previous, rating)
            data = {"user_id": user_id, "flashcard_id": card["id"], **schedule}
            supabase.table("flashcard_reviews").upsert(
                data, on_conflict="user_id,flashcard_id").execute()
        except Exception as exc:
            with _lock:
                session = _sessions.get((chat_id, user_id))
                if session and session["token"] == token:
                    session["phase"] = "answer"
            _reply_error(bot, chat_id, "save", exc)
            return
        with _lock:
            _sessions.pop((chat_id, user_id), None)
        when = "in 10 minutes" if rating == "again" else f"in {schedule['interval_days']} day(s)"
        bot.send_message(chat_id, f"✅ Saved: {rating.title()} — next review {when}.")
        send_next(chat_id, user_id)


__all__ = ["DUE_REVIEWS", "register_spaced_repetition_handlers", "next_schedule", "choose_due"]
