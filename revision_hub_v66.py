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


# V6.7 AI Library Browse and Search
LIBRARY_PAGE_SIZE = NOTE_LIMIT
SEARCH_MAX_RECENT = 200
LIBRARY_PAGE_PATTERN = re.compile(r"^v67:l:([0-9]{1,3})$")


def load_ai_note_page(db, uid, page):
    """Return (records, has_more) from an owner-filtered page of 8 saved AI notes."""
    if not isinstance(page, int) or not 0 <= page <= 999:
        raise ValueError("Invalid library page")
    offset = page * LIBRARY_PAGE_SIZE
    data = _rows(db.table("notes").select("id,title,created_at")
                 .eq("user_id", int(uid)).ilike("title", "AI Study:%")
                 .order("id", desc=True)
                 .range(offset, offset + LIBRARY_PAGE_SIZE).execute())
    return data[:LIBRARY_PAGE_SIZE], len(data) > LIBRARY_PAGE_SIZE


def find_ai_study_titles(db, uid, term):
    """Literal title search in recent 200 notes, with no user-supplied DB wildcard."""
    term = str(term or "").strip()
    if not 2 <= len(term) <= 60:
        raise ValueError("Search must be 2–60 characters")
    data = _rows(db.table("notes").select("id,title,created_at")
                 .eq("user_id", int(uid)).ilike("title", "AI Study:%")
                 .order("id", desc=True).limit(SEARCH_MAX_RECENT).execute())
    matching = [row for row in data if term.casefold() in str(row.get("title") or "").casefold()]
    return matching[:LIBRARY_PAGE_SIZE], len(matching), len(data) == SEARCH_MAX_RECENT


def _note_choices(bot, chat_id, rows, heading, prev_page=None, next_page=None):
    kb = types.InlineKeyboardMarkup(row_width=1)
    valid = 0
    for row in rows:
        try:
            note_id = int(row["id"])
            if note_id <= 0 or note_id >= 10**18:
                continue
        except (ValueError, TypeError, KeyError):
            continue
        name = str(row.get("title") or "AI Study Note").replace("\n", " ")[:50]
        kb.add(types.InlineKeyboardButton("📖 " + name, callback_data=f"v66:n:{note_id}"))
        valid += 1
    nav = []
    if prev_page is not None:
        nav.append(types.InlineKeyboardButton("⬅️ Newer notes", callback_data=f"v67:l:{prev_page}"))
    if next_page is not None:
        nav.append(types.InlineKeyboardButton("Older notes ➡️", callback_data=f"v67:l:{next_page}"))
    if nav:
        kb.row(*nav)
    if not valid and not nav:
        bot.send_message(chat_id, "📭 No matching saved AI study notes.")
    else:
        bot.send_message(chat_id, heading, reply_markup=kb)


def send_study_library(bot, db, chat_id, uid, page=0):
    rows, has_more = load_ai_note_page(db, uid, page)
    if not rows:
        if page:
            bot.send_message(chat_id, "📭 No more older AI notes. Use /studylibrary to start again.")
        else:
            bot.send_message(chat_id, "📭 No saved AI study notes yet.\n"
                             "Use /ai, then 💾 Save AI Answer and ✅ Confirm Save.",
                             reply_markup=_reply_markup())
        return
    _note_choices(bot, chat_id, rows,
                  f"📚 Saved AI Notes • Page {page + 1}\n"
                  "Tap a note to revise. Titles: /studyfind biology\nFull text: /studysearch biology",
                  prev_page=page-1 if page else None,
                  next_page=page+1 if has_more and page < 999 else None)


# V6.8 Full-Text Saved AI Note Search
STUDYSEARCH_MAX_RECENT = SEARCH_MAX_RECENT  # search only latest 200 saved AI notes
STUDYSEARCH_PREVIEW_CHARS = 125


def _v68_excerpt(text, term, max_chars=STUDYSEARCH_PREVIEW_CHARS):
    """A short, unformatted snippet near the first occurrence of the literal search term."""
    content = str(text or "")
    index = content.casefold().find(term.casefold())
    if index < 0:
        return ""
    start = max(0, index - 40)
    end = min(len(content), start + max_chars)
    piece = " ".join(content[start:end].split())
    # Control chars should not break the private Telegram preview.
    piece = "".join(c for c in piece if c.isprintable())
    return ("…" if start else "") + piece[:max_chars] + ("…" if end < len(content) else "")


def search_saved_ai_content(db, uid, term):
    """Read-only, user-filtered literal search in title or content, newest 200 notes.

    Returns (at most 8 result dictionaries, total matches, scan_capped).
    Title matches are listed first, then body-only matches; both retain newest order.
    """
    term = str(term or "").strip()
    if not 2 <= len(term) <= 60 or any(ord(c) < 32 for c in term):
        raise ValueError("Search term must be 2–60 printable characters")
    data = _rows(db.table("notes").select("id,title,content")
                 .eq("user_id", int(uid)).ilike("title", "AI Study:%")
                 .order("id", desc=True).limit(STUDYSEARCH_MAX_RECENT).execute())
    needle = term.casefold()
    titles, bodies = [], []
    for row in data:
        title = str(row.get("title") or "")
        content = str(row.get("content") or "")
        if not title.startswith("AI Study:"):
            continue
        if needle in title.casefold():
            titles.append({"id": row.get("id"), "title": title,
                           "excerpt": "Title match", "kind": "title"})
        elif needle in content.casefold():
            bodies.append({"id": row.get("id"), "title": title,
                           "excerpt": _v68_excerpt(content, term), "kind": "content"})
    ranked = titles + bodies
    return ranked[:LIBRARY_PAGE_SIZE], len(ranked), len(data) >= STUDYSEARCH_MAX_RECENT


def show_saved_ai_search(bot, db, chat_id, uid, term):
    matches, count, scan_capped = search_saved_ai_content(db, uid, term)
    if not matches:
        bot.send_message(chat_id, "🔎 No matches in recent saved AI notes. Try /studysearch with another word.")
        return
    kb = types.InlineKeyboardMarkup(row_width=1)
    lines = [f"🔎 Saved AI Notes: {count} matching note(s).",
             f"Search: {term[:60]}", "Tap a title to open the complete note."]
    for row in matches:
        try:
            ident = int(row["id"])
            if ident < 1 or ident >= 10**18:
                continue
        except (TypeError, ValueError, KeyError):
            continue
        title = " ".join(str(row["title"]).split())[:48]
        kb.add(types.InlineKeyboardButton("📖 " + title,
                   callback_data=f"v66:n:{ident}"))
        if row["kind"] == "content":
            lines.append("• " + title[:44] + ": " + row["excerpt"])
    if count > LIBRARY_PAGE_SIZE:
        lines.append(f"Showing first {LIBRARY_PAGE_SIZE} results (title matches first).")
    if scan_capped:
        lines.append("⚠️ Only the 200 most recent AI notes were searched.")
    bot.send_message(chat_id, "\n".join(lines)[:3500], reply_markup=kb)


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
            send_study_library(bot, supabase, message.chat.id, message.from_user.id)
        except Exception as exc:
            print("V6.7 library query failed:", type(exc).__name__)
            bot.send_message(message.chat.id, "⚠️ Cannot load saved AI notes right now. Please try later.")

    @bot.message_handler(commands=["studyfind"])
    def revision_find(message):
        if not _private(message):
            bot.send_message(message.chat.id, "🔒 Use this in a private chat.")
            return
        text = str(getattr(message, "text", "") or "")
        term = text.partition(" ")[2].strip()
        if not 2 <= len(term) <= 60:
            bot.send_message(message.chat.id, "🔎 Search saved AI note titles:\n"
                             "/studyfind biology\n"
                             "Enter 2–60 characters after the command.")
            return
        try:
            rows, count, capped = find_ai_study_titles(supabase, message.from_user.id, term)
        except Exception as exc:
            print("V6.7 study search failed:", type(exc).__name__)
            bot.send_message(message.chat.id, "⚠️ Search is unavailable. Please try again later.")
            return
        if not rows:
            bot.send_message(message.chat.id, "🔎 No matching AI note titles among the recent saved notes.")
            return
        warning = "\nSearch checked only the 200 most recent AI notes." if capped else ""
        _note_choices(bot, message.chat.id, rows,
                      f"🔎 Found {count} title matches; showing up to 8.{warning}")

    @bot.message_handler(commands=["studysearch"])
    def revision_content_search(message):
        if not _private(message):
            bot.send_message(message.chat.id, "🔒 Use this in a private chat.")
            return
        text = str(getattr(message, "text", "") or "")
        term = text.partition(" ")[2].strip()
        if not 2 <= len(term) <= 60 or any(ord(c) < 32 for c in term):
            bot.send_message(message.chat.id,
                             "🔎 Search saved AI note titles AND content:\n"
                             "/studysearch photosynthesis\n"
                             "/studysearch ஒளிச்சேர்க்கை\n"
                             "Type 2–60 characters after the command.")
            return
        try:
            show_saved_ai_search(bot, supabase, message.chat.id,
                                 message.from_user.id, term)
        except Exception as exc:
            print("V6.8 private content search failed:", type(exc).__name__)
            bot.send_message(message.chat.id,
                             "⚠️ Note search is unavailable. Try again later.")

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

    @bot.callback_query_handler(func=lambda c: bool(LIBRARY_PAGE_PATTERN.fullmatch(
        str(getattr(c, "data", "")))))
    def revision_library_page(call):
        if (getattr(getattr(call.message, "chat", None), "type", None) != "private"
                or getattr(getattr(call, "from_user", None), "id", None) !=
                   getattr(call.message.chat, "id", None)):
            bot.answer_callback_query(call.id, "Open a private chat.", show_alert=True)
            return
        match = LIBRARY_PAGE_PATTERN.fullmatch(call.data)
        if not match:
            return
        try:
            bot.answer_callback_query(call.id)
            send_study_library(bot, supabase, call.message.chat.id,
                               call.from_user.id, int(match.group(1)))
        except Exception as exc:
            print("V6.7 page load failed:", type(exc).__name__)
            bot.send_message(call.message.chat.id, "⚠️ Could not load that page. Try /studylibrary.")

    return True
