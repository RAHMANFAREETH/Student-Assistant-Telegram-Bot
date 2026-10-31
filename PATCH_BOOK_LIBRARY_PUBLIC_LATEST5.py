"""V11.1 Book Library: public private/group access and latest-five catalog patch.

No database migration, no Gemini changes, and no modifications to main.py/navigation.py.
Usage:
  python PATCH_BOOK_LIBRARY_PUBLIC_LATEST5.py --check
  python PATCH_BOOK_LIBRARY_PUBLIC_LATEST5.py --apply
"""
from __future__ import annotations

import argparse
import difflib
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BOT = 'book_library_bot.py'
STORE = 'book_library_store.py'


def _replace(text: str, old: str, new: str, description: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise ValueError(f'Cannot safely patch {description}: expected one exact anchor, got {count}. No files changed.')
    return text.replace(old, new, 1)


def transform(name: str, text: str) -> str:
    if name == STORE:
        return _replace(
            text,
            'def latest_books(*, limit=8, db=None):',
            'def latest_books(*, limit=5, db=None):',
            'latest_books default limit',
        )
    if name != BOT:
        raise ValueError(f'Unsupported file: {name}')

    text = _replace(
        text,
        "def _allowed_group(chat_id):\n    # Never search all groups indiscriminately; specify the approved group IDs.\n    ids = _ids('BOOK_LIBRARY_GROUP_IDS')\n    return bool(ids) and int(chat_id) in ids",
        "def _allowed_group(chat_id):\n"
        "    # Explicit opt-in: permit /book and /booklatest in any group containing the bot.\n"
        "    # Automatic free-text group search remains OFF unless separately enabled.\n"
        "    if _on('BOOK_LIBRARY_ALLOW_ALL_GROUPS', False):\n"
        "        return True\n"
        "    ids = _ids('BOOK_LIBRARY_GROUP_IDS')\n"
        "    return bool(ids) and int(chat_id) in ids",
        'group access rule',
    )
    text = _replace(
        text,
        "if not _on('BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT', True):",
        "if not _on('BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT', False):",
        'public-library default',
    )
    text = _replace(
        text,
        "        books = latest_books()\n",
        "        books = latest_books(limit=5)\n",
        'latest-five query',
    )
    text = _replace(
        text,
        "bot.send_message(chat_id, '📚 Recently added books:',",
        "bot.send_message(chat_id, f'📚 Latest Books ({len(books)} most recent uploads):',",
        'latest-five heading',
    )
    text = _replace(
        text,
        "bot.send_message(m.chat.id, '📚 Search here with /book TITLE. Results link to private delivery.')",
        "bot.send_message(m.chat.id, '📚 Search here with /book TITLE or show the newest five with /booklatest. Results link to private delivery.')",
        'group menu help',
    )
    # Register the new command BEFORE existing document/text wildcard handlers.
    text = _replace(
        text,
        "    @bot.message_handler(commands=['bookremove'])",
        "    @bot.message_handler(commands=['booklatest', 'latestbooks'])\n"
        "    def library_latest_command(m):\n"
        "        if not _enabled():\n"
        "            bot.send_message(m.chat.id, '📚 Book Library is not enabled yet.')\n"
        "            return\n"
        "        if _is_group(m) and not _allowed_group(m.chat.id):\n"
        "            bot.send_message(m.chat.id, '🔒 Book search is not enabled in this group.')\n"
        "            return\n"
        "        if not (_is_private(m) or _is_group(m)):\n"
        "            return\n"
        "        if not _verified(m.from_user.id):\n"
        "            if _is_private(m):\n"
        "                _adult_notice(bot, m.chat.id)\n"
        "            else:\n"
        "                bot.send_message(m.chat.id, '🔒 Book Library access is restricted.')\n"
        "            return\n"
        "        if _cooldown(m.chat.id, m.from_user.id, 3):\n"
        "            return\n"
        "        _latest(bot, m.chat.id)\n\n"
        "    @bot.message_handler(commands=['bookremove'])",
        'latest-books command registration',
    )
    # Helpful /books in groups: show latest five rather than only usage.
    text = _replace(
        text,
        "            else:\n                bot.send_message(m.chat.id, 'Usage: /book Book Title or Author')\n"
        "        else:\n            if _cooldown(m.chat.id, m.from_user.id, 3):",
        "            else:\n                if _cooldown(m.chat.id, m.from_user.id, 3):\n                    return\n                _latest(bot, m.chat.id)\n"
        "        else:\n            if _cooldown(m.chat.id, m.from_user.id, 3):",
        'group no-query behavior',
    )
    # Group auto-search may be enabled explicitly, but use the same opt-in all-group rule.
    return text


def integrate(root: Path, *, apply: bool, output=print):
    originals, changes, transformed = {}, {}, {}
    for name in (BOT, STORE):
        path = root / name
        if not path.is_file():
            raise FileNotFoundError(f'Missing {name}; copy this patch into your existing bot folder.')
        content = path.read_bytes()
        try:
            decoded = content.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise ValueError(f'{name} must be UTF-8 source') from exc
        new_text = transform(name, decoded.replace('\r\n', '\n'))
        if '\r\n' in decoded:
            new_text = new_text.replace('\n', '\r\n')
        new_bytes = new_text.encode('utf-8')
        originals[name] = content
        if new_bytes != content:
            changes[name] = new_bytes
            transformed[name] = new_text
    if not changes:
        output('Public Library + Latest 5 already installed. No files changed.')
        return []
    for name in changes:
        before = originals[name].decode('utf-8').splitlines(keepends=True)
        after = transformed[name].splitlines(keepends=True)
        output(''.join(difflib.unified_diff(before, after, fromfile=name+':current', tofile=name+':planned')))
    if not apply:
        output('CHECK OK. No files changed.')
        return list(changes)
    # Verify both sources compile BEFORE writing anything.
    for name, content in changes.items():
        compile(content, name, 'exec')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
    backup = root / f'BOOK_PUBLIC_LATEST5_BACKUP_{stamp}'
    backup.mkdir()
    for name in changes:
        (backup / name).write_bytes(originals[name])
    try:
        for name, content in changes.items():
            with tempfile.NamedTemporaryFile(prefix='.bookpatch_', dir=root, delete=False) as tmp:
                tmp.write(content)
                tmppath = Path(tmp.name)
            tmppath.replace(root / name)
    except Exception:
        for name in changes:
            (root / name).write_bytes(originals[name])
        raise
    output(f'Public Book Library + Latest Five applied. Backup: {backup}')
    return list(changes)


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--check', action='store_true')
    g.add_argument('--apply', action='store_true')
    a = p.parse_args()
    integrate(Path(__file__).resolve().parent, apply=a.apply)

if __name__ == '__main__':
    main()
