"""V6.6: Private, read-only revision hub for existing Supabase Notes/Flashcards.

No AI calls, no database writes, no new tables or credentials.
Flashcard *practice* here is view/reveal only; /reviews remains the existing
tracked spaced-repetition workflow.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from telebot import types
from db import supabase
from safe_utils import split_telegram_text

LIBRARY = "📚 My AI Study Library"
REVISE = "🔄 Revise AI Note"
PRACTICE = "🧠 Practice Saved Cards"
PROGRESS = "📊 Revision Progress"
REMINDERS = "⏰ Revision Reminders"
HUB = "📖 Revision Hub"
BUTTONS = frozenset((LIBRARY, REVISE, PRACTICE, PROGRESS, REMINDERS, HUB))
NOTE_LIMIT = 8
CARD_LIMIT = 500
_CALLBACK = re.compile(r"^v66:([npa]):([1-9][0-9]{0,17})$")


def _private(message):
    """Private chat only; ownership is always Telegram *sender* ID."""
    chat = getattr(message, "chat", None)
    user = getattr(message, "from_user", None)
    return (getattr(chat, "type", None) == "private"
            and isinstance(getattr(user, "id", None), int)
            and getattr(user, "id", 0) > 0)


def _rows(response):
    data = getattr(response, "data", None)
    if data is None or not isinstance(data, list):
        raise RuntimeError("Unexpected database response")
    return data


def load_ai_notes(db, user_id: int, limit=NOTE_LIMIT):
    """Only notes created by V6.5's AI save workflow and owned by this user."""
    return _rows(db.table("notes").select("id,title,created_at")
                 .eq("user_id", int(user_id)).ilike("title", "AI Study:%")
                 .order("id", desc=True).limit(limit).execute())


def load_note(db, user_id: int, note_id: int):
    data = _rows(db.table("notes").select("id,title,content")
                 .eq("user_id", int(user_id)).eq("id", int(note_id))
                 .limit(1).execute())
    if not data or not str(data[0].get("title") or "").startswith("AI Study:"):
        return None
    return data[0]


def load_card(db, user_id: int, card_id: int):
    data = _rows(db.table("flashcards").select("id,question,answer")
                 .eq("user_id", int(user_id)).eq("id", int(card_id))
                 .limit(1).execute())
    return data[0] if data else None


def latest_card(db, user_id: int, before=None):
    query = (db.table("flashcards").select("id,question")
             .eq("user_id", int(user_id)))
    if before is not None:
        query = query.lt("id", int(before))
    rows = _rows(query.order("id", desc=True).limit(1).execute())
    return rows[0] if rows else None


def revision_summary(db, user_id: int, now=None):
    """Counts recent 500 cards. Never substitute empty data on a DB error."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must include timezone")
    rows = _rows(db.table("flashcards")
                 .select("id").eq("user_id", int(user_id))
                 .order("id", desc=True).range(0, CARD_LIMIT - 1).execute())
    revs = _rows(db.table("flashcard_reviews")
                 .select("flashcard_id,repetitions,due_at,review_count")
                 .eq("user_id", int(user_id)).range(0, CARD_LIMIT - 1).execute())
    review_map = {str(row["flashcard_id"]): row for row in revs}
    due = reviewed = strong = 0
    for card in rows:
        rev = review_map.get(str(card["id"]))
        if rev:
            reviewed += 1
            if int(rev.get("repetitions") or 0) >= 3:
                strong += 1
        due_at = (rev or {}).get("due_at")
        if not due_at:
            due += 1
            continue
        try:
            parsed = datetime.fromisoformat(str(due_at).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed <= now:
                due += 1
        except (ValueError, TypeError):
            due += 1
    return {"cards": len(rows), "reviewed": reviewed, "due": due,
            "strong": strong, "capped": len(rows) >= CARD_LIMIT}


def _reply_markup():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.row(types.KeyboardButton(LIBRARY), types.KeyboardButton(REVISE))
    kb.row(types.KeyboardButton(PRACTICE), types.KeyboardButton(PROGRESS))
    kb.row(types.KeyboardButton(REMINDERS), types.KeyboardButton("🏠 Main Menu"))
    return kb


def _send_note(bot, chat_id, row):
    """Split content to remain safely under Telegram's text limit."""
    title = str(row.get("title") or "AI Study Note")[:140]
    content = str(row.get("content") or "").strip()
    if not content:
        bot.send_message(chat_id, "⚠️ This saved note is empty.")
        return
    bot.send_message(chat_id, "📚 Revision: " + title)
    for section in split_telegram_text(content, limit=3500):
        bot.send_message(chat_id, section)
    bot.send_message(chat_id, "✅ Finished reviewing this note.\n"
                     "Try 🧠 Practice Saved Cards or /reviews to study with flashcards.",
                     reply_markup=_reply_markup())


def register_revision_hub_v66_handlers(bot, show_main_menu):
    """Register after V5.7 UI and before legacy wildcard handlers."""

    @bot.message_handler(commands=["studyhub", "revisionhub"])
    @bot.message_handler(func=lambda m: getattr(m, "text", None) == HUB)
    def revision_hub_menu(message):
        if not _private(message):
            bot.send_message(message.chat.id, "🔒 Open a private chat with the bot to view your study records.")
            return
        bot.send_message(message.chat.id,
                         "📖 Smart Study Revision V6.6\n\n"
                         "📚 My AI Study Library — browse saved AI notes\n"
                         "🔄 Revise AI Note — open a saved note\n"
                         "🧠 Practice Saved Cards — reveal saved flashcard answers\n"
                         "📊 Revision Progress — tracked /reviews statistics\n"
                         "⏰ Revision Reminders — use existing planner and reminders",
                         reply_markup=_reply_markup())

    @bot.message_handler(commands=["studylibrary", "reviseagain"])
    @bot.message_handler(func=lambda m: getattr(m, "text", None) in (LIBRARY, REVISE))
    def revision_notes(message):
        if not _private(message):
            bot.send_message(message.chat.id, "🔒 Use this in a private chat.")
            return
        try:
            notes = load_ai_notes(supabase, message.from_user.id)
        except Exception as exc:
            print("V6.6 note query failed:", type(exc).__name__)
            bot.send_message(message.chat.id, "⚠️ Cannot load saved AI notes right now. Please try again later.")
            return
        if not notes:
            bot.send_message(message.chat.id,
                             "📭 No saved AI study notes yet.\n\n"
                             "Ask /ai a question, then use 💾 Save AI Answer and ✅ Confirm Save.",
                             reply_markup=_reply_markup())
            return
        kb = types.InlineKeyboardMarkup(row_width=1)
        for row in notes:
            try:
                note_id = int(row["id"])
                if note_id <= 0:
                    continue
            except (ValueError, TypeError, KeyError):
                continue
            title = str(row.get("title") or "AI Study Note").replace("\n", " ")[:50]
            kb.add(types.InlineKeyboardButton("📖 " + title, callback_data=f"v66:n:{note_id}"))
        bot.send_message(message.chat.id,
                         "📚 Your latest saved AI answers (up to 8)\n"
                         "Select a note to revise. Only your notes are shown.", reply_markup=kb)

    @bot.message_handler(commands=["studypractice", "practicecards"])
    @bot.message_handler(func=lambda m: getattr(m, "text", None) == PRACTICE)
    def revision_cards(message):
        if not _private(message):
            bot.send_message(message.chat.id, "🔒 Use this in a private chat.")
            return
        try:
            card = latest_card(supabase, message.from_user.id)
        except Exception as exc:
            print("V6.6 card query failed:", type(exc).__name__)
            bot.send_message(message.chat.id, "⚠️ Cannot load saved cards right now.")
            return
        if not card:
            bot.send_message(message.chat.id,
                             "📭 No flashcards yet. Save an AI quiz using 🗂 Save AI Quiz,"
                             " or add a flashcard manually.")
            return
        _send_question(bot, message.chat.id, card)

    def _send_question(bot_, chat_id, card):
        try:
            ident = int(card["id"])
            if ident <= 0:
                raise ValueError
        except (KeyError, ValueError, TypeError):
            bot_.send_message(chat_id, "⚠️ Invalid flashcard. Please try another.")
            return
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton("👁 Reveal Answer", callback_data=f"v66:a:{ident}"))
        question = str(card.get("question") or "").strip()[:3000]
        bot_.send_message(chat_id, "🧠 Practice a Saved Flashcard\n\n❓ " + question,
                          reply_markup=kb)

    @bot.message_handler(commands=["revisionprogress"])
    @bot.message_handler(func=lambda m: getattr(m, "text", None) == PROGRESS)
    def revision_progress(message):
        if not _private(message):
            bot.send_message(message.chat.id, "🔒 Use this in a private chat.")
            return
        try:
            summary = revision_summary(supabase, message.from_user.id)
        except Exception as exc:
            print("V6.6 progress failed:", type(exc).__name__)
            bot.send_message(message.chat.id,
                             "⚠️ Revision progress is unavailable. Check Supabase flashcard_reviews setup.")
            return
        extra = "\n⚠️ Recent 500 cards only." if summary["capped"] else ""
        bot.send_message(message.chat.id,
                         "📊 Flashcard Revision Progress\n\n"
                         f"🧠 Cards counted: {summary['cards']}\n"
                         f"✅ Reviewed: {summary['reviewed']}\n"
                         f"⏰ Due: {summary['due']}\n"
                         f"🏆 Strong recall: {summary['strong']}"
                         + extra + "\n\nUse /reviews for graded, tracked practice."
                         " Read-only practice here does not change these statistics.")

    @bot.message_handler(commands=["revisionreminders"])
    @bot.message_handler(func=lambda m: getattr(m, "text", None) == REMINDERS)
    def revision_reminders(message):
        if not _private(message):
            bot.send_message(message.chat.id, "🔒 Use this in a private chat.")
            return
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        kb.row(types.KeyboardButton("⏰ Study Reminder"),
               types.KeyboardButton("📚 Revision Planner"))
        kb.row(types.KeyboardButton("🏠 Main Menu"), types.KeyboardButton(HUB))
        bot.send_message(message.chat.id,
                         "⏰ Revision Reminders\n\n"
                         "Use ⏰ Study Reminder to schedule an existing reminder, or"
                         " 📚 Revision Planner to plan study sessions.\n"
                         "This V6.6 shortcut does not create a reminder automatically.",
                         reply_markup=kb)

    @bot.callback_query_handler(func=lambda c: bool(re.fullmatch(r"v66:(?:[npa]:[1-9][0-9]{0,17})", str(getattr(c, "data", "")))))
    def revision_callback(call):
        """Server-side owner queries, not a trusted callback_data user ID."""
        if (getattr(call.message.chat, "type", None) != "private"
                or getattr(call.from_user, "id", None) != call.message.chat.id):
            bot.answer_callback_query(call.id, "Open the bot's private chat.", show_alert=True)
            return
        match = _CALLBACK.fullmatch(call.data)
        if not match:
            return
        action, ident_text = match.groups()
        ident = int(ident_text)
        uid = int(call.from_user.id)
        chat_id = call.message.chat.id
        try:
            if action == "n":
                note = load_note(supabase, uid, ident)
                if not note:
                    bot.answer_callback_query(call.id, "Note unavailable.", show_alert=True)
                    return
                bot.answer_callback_query(call.id)
                _send_note(bot, chat_id, note)
                return
            card = load_card(supabase, uid, ident)
            if not card:
                bot.answer_callback_query(call.id, "Card unavailable.", show_alert=True)
                return
            bot.answer_callback_query(call.id)
            if action == "p":
                _send_question(bot, chat_id, card)
            else:
                next_card = latest_card(supabase, uid, before=ident)
                kb = types.InlineKeyboardMarkup(row_width=1)
                if next_card:
                    kb.add(types.InlineKeyboardButton("⏭ Next Card",
                           callback_data=f"v66:p:{int(next_card['id'])}"))
                bot.send_message(chat_id,
                                 "✅ Answer:\n" + str(card.get("answer") or "(empty)")[:3000]
                                 + "\n\nUse /reviews to grade recall and update due dates."
                                 + ("\nEnd of saved cards. /studypractice starts again." if not next_card else ""),
                                 reply_markup=kb if next_card else None)
        except Exception as exc:
            print("V6.6 callback failed:", type(exc).__name__)
            bot.answer_callback_query(call.id, "Sorry, revision could not be loaded.", show_alert=True)

    return True
