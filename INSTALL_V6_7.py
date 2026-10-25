"""V6.7 pagination and title search for the existing V6.6 revision hub.

Only patches revision_hub_v66.py with a backup and atomic replacement.
Refuses incompatible/partial code; no other bot modules or data are touched.
"""
from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

TARGET = "revision_hub_v66.py"
BACKUP = TARGET + ".before_v67.bak"
MARKER = "# V6.7 AI Library Browse and Search"
EXPECTED_NOTES_SHA256 = "6a9079c425ed2f91a5a5d70e8e2fa11f32a1c1339c3dd1cd759c906edebc670e"


class InstallationError(ValueError):
    pass


def replace_once(src, old, new, label):
    if src.count(old) != 1:
        raise InstallationError(f"Unexpected {label} code; stopping without changes")
    return src.replace(old, new, 1)


NEW_HELPERS = '''# V6.7 AI Library Browse and Search
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
        name = str(row.get("title") or "AI Study Note").replace("\\n", " ")[:50]
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
            bot.send_message(chat_id, "📭 No saved AI study notes yet.\\n"
                             "Use /ai, then 💾 Save AI Answer and ✅ Confirm Save.",
                             reply_markup=_reply_markup())
        return
    _note_choices(bot, chat_id, rows,
                  f"📚 Saved AI Notes • Page {page + 1}\\n"
                  "Tap any note to revise. Search titles: /studyfind photosynthesis",
                  prev_page=page-1 if page else None,
                  next_page=page+1 if has_more and page < 999 else None)


'''

NEW_MESSAGES = '''    @bot.message_handler(commands=["studylibrary", "reviseagain"])
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
            bot.send_message(message.chat.id, "🔎 Search saved AI note titles:\\n"
                             "/studyfind biology\\n"
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
        warning = "\\nSearch checked only the 200 most recent AI notes." if capped else ""
        _note_choices(bot, message.chat.id, rows,
                      f"🔎 Found {count} title matches; showing up to 8.{warning}")

'''

NEW_CALLBACK = '''    @bot.callback_query_handler(func=lambda c: bool(LIBRARY_PAGE_PATTERN.fullmatch(
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

'''


def patch_module(src):
    ast.parse(src, filename=TARGET)
    if MARKER in src:
        if (src.count(MARKER) != 1 or src.count('def revision_find(message):') != 1
                or src.count('def revision_library_page(call):') != 1):
            raise InstallationError("Incomplete V6.7 patch found")
        return src, False
    required = (
        '"""V6.6: Private, read-only revision hub',
        'def register_revision_hub_v66_handlers(bot, show_main_menu):',
        'def revision_notes(message):',
        'def revision_callback(call):',
        'return True',
    )
    if any(x not in src for x in required) or 'v67:' in src:
        raise InstallationError("This is not the expected V6.6 revision hub")
    src = replace_once(src, 'def load_note(db, user_id: int, note_id: int):',
                       NEW_HELPERS + 'def load_note(db, user_id: int, note_id: int):', "helpers")
    oldstart = '    @bot.message_handler(commands=["studylibrary", "reviseagain"])'
    oldend = '    @bot.message_handler(commands=["studypractice", "practicecards"])'
    if src.count(oldstart) != 1 or src.count(oldend) != 1:
        raise InstallationError("Unexpected study library handlers")
    a = src.index(oldstart)
    b = src.index(oldend)
    if hashlib.sha256(src[a:b].encode("utf-8")).hexdigest() != EXPECTED_NOTES_SHA256:
        raise InstallationError("Customized V6.6 notes handler detected; nothing changed")
    src = src[:a] + NEW_MESSAGES + src[b:]
    src = replace_once(src, '    return True\n', NEW_CALLBACK + '    return True\n', 'callback registration')
    ast.parse(src, filename=TARGET)
    return src, True


def install(root=Path('.')):
    root = Path(root)
    target = root / TARGET
    if not target.is_file():
        raise InstallationError("Missing revision_hub_v66.py. Install V6.6 first.")
    with target.open('r', encoding='utf-8', newline='') as stream:
        old = stream.read()
    ending = '\r\n' if '\r\n' in old else '\n'
    new, changed = patch_module(old.replace('\r\n', '\n'))
    if not changed:
        return False
    backup = root / BACKUP
    if backup.exists():
        raise InstallationError("V6.7 backup already exists; refusing overwrite")
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='',
                                         dir=root, prefix='.v67_', suffix='.tmp', delete=False) as f:
            tmp = Path(f.name)
            f.write(new.replace('\n', ending))
        shutil.copy2(target, backup)
        os.replace(tmp, target)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
    return True


if __name__ == '__main__':
    try:
        changed = install()
    except (ValueError, OSError, UnicodeError, SyntaxError) as exc:
        print("V6.7 install stopped safely:", exc)
        raise SystemExit(1)
    print("V6.7 " + ("installed" if changed else "already installed; no files changed"))
