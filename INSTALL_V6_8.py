"""V6.8 installer: add private full-text search for saved AI study notes.

Installs on top of existing V6.7 only; changes revision_hub_v66.py only.
Refuses any partial/incompatible code. Atomic UTF-8 replace with pre-existing backup guard.
"""
from __future__ import annotations

import ast
from pathlib import Path
import os
import shutil
import tempfile

TARGET = 'revision_hub_v66.py'
BACKUP = TARGET + '.before_v68.bak'
MARKER = '# V6.8 Full-Text Saved AI Note Search'

class InstallationError(ValueError):
    pass


def _one(src: str, old: str, new: str, label: str) -> str:
    if src.count(old) != 1:
        raise InstallationError('Unexpected V6.7 ' + label + '; no changes made')
    return src.replace(old, new, 1)


HELPERS = '''# V6.8 Full-Text Saved AI Note Search
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
    bot.send_message(chat_id, "\\n".join(lines)[:3500], reply_markup=kb)


'''

NEW_HANDLER = '''    @bot.message_handler(commands=["studysearch"])
    def revision_content_search(message):
        if not _private(message):
            bot.send_message(message.chat.id, "🔒 Use this in a private chat.")
            return
        text = str(getattr(message, "text", "") or "")
        term = text.partition(" ")[2].strip()
        if not 2 <= len(term) <= 60 or any(ord(c) < 32 for c in term):
            bot.send_message(message.chat.id,
                             "🔎 Search saved AI note titles AND content:\\n"
                             "/studysearch photosynthesis\\n"
                             "/studysearch ஒளிச்சேர்க்கை\\n"
                             "Type 2–60 characters after the command.")
            return
        try:
            show_saved_ai_search(bot, supabase, message.chat.id,
                                 message.from_user.id, term)
        except Exception as exc:
            print("V6.8 private content search failed:", type(exc).__name__)
            bot.send_message(message.chat.id,
                             "⚠️ Note search is unavailable. Try again later.")

'''


def patch_module(src: str):
    ast.parse(src, filename=TARGET)
    if MARKER in src:
        if (src.count(MARKER) != 1
                or src.count('def revision_content_search(message):') != 1
                or src.count('def search_saved_ai_content(db, uid, term):') != 1
                or src.count('def show_saved_ai_search(bot, db, chat_id, uid, term):') != 1):
            raise InstallationError('Incomplete V6.8 installation detected')
        return src, False
    required = ('# V6.7 AI Library Browse and Search',
                'def find_ai_study_titles(db, uid, term):',
                'def send_study_library(bot, db, chat_id, uid, page=0):',
                'def revision_find(message):',
                'def revision_library_page(call):',
                'def register_revision_hub_v66_handlers(bot, show_main_menu):')
    if any(x not in src for x in required) or 'v68:' in src:
        raise InstallationError('V6.7 prerequisite missing or unsupported source')
    src = _one(src, '\ndef load_note(db, user_id: int, note_id: int):',
               '\n' + HELPERS + 'def load_note(db, user_id: int, note_id: int):', 'search helpers')
    src = _one(src, '    @bot.message_handler(commands=["studypractice", "practicecards"])',
               NEW_HANDLER + '    @bot.message_handler(commands=["studypractice", "practicecards"])',
               'handler location')
    src = _one(src, 'Tap any note to revise. Search titles: /studyfind photosynthesis',
               'Tap a note to revise. Titles: /studyfind biology\\nFull text: /studysearch biology',
               'library guidance')
    ast.parse(src, filename=TARGET)
    return src, True


def install(root=Path('.')):
    root = Path(root)
    path = root / TARGET
    if not path.is_file():
        raise InstallationError('Missing revision_hub_v66.py. Install V6.6 and V6.7 first.')
    with path.open('r', encoding='utf-8', newline='') as f:
        old = f.read()
    ending = '\r\n' if '\r\n' in old else '\n'
    new, changed = patch_module(old.replace('\r\n', '\n'))
    if not changed:
        return False
    backup = root / BACKUP
    if backup.exists():
        raise InstallationError('V6.8 backup exists; refusing overwrite')
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='',
                dir=root, prefix='.v68_', suffix='.tmp', delete=False) as f:
            tmp = Path(f.name)
            f.write(new.replace('\n', ending))
        shutil.copy2(path, backup)
        os.replace(tmp, path)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
    return True


if __name__ == '__main__':
    try:
        changed = install()
    except (ValueError, OSError, UnicodeError, SyntaxError) as exc:
        print('V6.8 installation stopped:', exc)
        raise SystemExit(1)
    print('V6.8 ' + ('installed successfully' if changed else 'already installed; no changes made'))
