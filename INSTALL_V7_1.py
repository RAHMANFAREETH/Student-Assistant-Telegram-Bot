"""Idempotent V7.1 installer. Only changes revision_hub_v66.py.

No main.py, AI integrations, Supabase data, or v6.9/v7.0 export code changed.
"""
from __future__ import annotations

import ast
import os
import tempfile
from pathlib import Path

TARGET = 'revision_hub_v66.py'
HELPER = 'study_note_actions_v71.py'
BACKUP = 'revision_hub_v66.py.before_v71.bak'

ACTIONS_MARKER = '    # V7.1 Individual Note Quick Actions\n'
ACTIONS_BLOCK = (ACTIONS_MARKER
                 + '    from study_note_actions_v71 import note_actions_keyboard\n'
                 + '    actions = note_actions_keyboard(types, row.get("id"))\n'
                 + '    if actions is not None:\n'
                 + '        bot.send_message(chat_id, "📎 Quick actions for this note:", reply_markup=actions)\n')
REGISTER_MARKER = '    # V7.1 Individual Note Quick Actions registration\n'
REGISTER_BLOCK = (REGISTER_MARKER
                  + '    from study_note_actions_v71 import register_study_note_actions_v71_handlers\n'
                  + '    register_study_note_actions_v71_handlers(bot, supabase, load_note, send_study_library)\n')
ANCHOR_ACTION = ('    bot.send_message(chat_id, "✅ Finished reviewing this note.\\n"\n'
                 '                     "Try 🧠 Practice Saved Cards or /reviews to study with flashcards.",\n'
                 '                     reply_markup=_reply_markup())\n')
ANCHOR_REGISTER = '    # V6.9 AI Study Notes Export registration\n'


class InstallationError(ValueError):
    pass


def patch_module(source):
    ast.parse(source, filename=TARGET)
    if ACTIONS_MARKER in source or REGISTER_MARKER in source or 'study_note_actions_v71' in source:
        if (source.count(ACTIONS_MARKER) != 1
                or source.count(REGISTER_MARKER) != 1
                or source.count(ACTIONS_BLOCK) != 1
                or source.count(REGISTER_BLOCK) != 1
                or source.count('from study_note_actions_v71 import') != 2):
            raise InstallationError('Incomplete/custom V7.1 patch detected; refusing modification')
        return source, False
    prerequisites = [
        'def register_revision_hub_v66_handlers(bot, show_main_menu):',
        'def load_note(db, user_id: int, note_id: int):',
        'def send_study_library(bot, db, chat_id, uid, page=0):',
        'def _send_note(bot, chat_id, row):',
        'register_study_export_v69_handlers(bot, supabase)',
        '# V6.8 Full-Text Saved AI Note Search',
    ]
    if any(token not in source for token in prerequisites):
        raise InstallationError('Expected V6.9+ revision hub missing. Install prior upgrades first.')
    if source.count(ANCHOR_ACTION) != 1 or source.count(ANCHOR_REGISTER) != 1:
        raise InstallationError('Expected note and registration anchors not found; refusing modification')
    patched = source.replace(ANCHOR_ACTION, ANCHOR_ACTION + ACTIONS_BLOCK, 1)
    patched = patched.replace(ANCHOR_REGISTER, REGISTER_BLOCK + '\n' + ANCHOR_REGISTER, 1)
    ast.parse(patched, filename=TARGET)
    return patched, True


def install(root=Path('.')):
    root = Path(root)
    target, helper = root / TARGET, root / HELPER
    if not target.is_file() or not helper.is_file():
        raise InstallationError('Copy INSTALL_V7_1.py and study_note_actions_v71.py into project root.')
    helper_source = helper.read_text(encoding='utf-8')
    ast.parse(helper_source, filename=HELPER)
    if 'def register_study_note_actions_v71_handlers(' not in helper_source:
        raise InstallationError('Unknown V7.1 helper version')
    # Ensure V7.0 is in place, but do not modify its files.
    md = root / 'study_markdown_v70.py'
    exp = root / 'study_export_v69.py'
    if not md.is_file() or not exp.is_file() or 'V7.0 Private Markdown Export registration' not in exp.read_text(encoding='utf-8'):
        raise InstallationError('Expected V7.0 Markdown export not found. Install V7.0 first.')
    with target.open('r', encoding='utf-8', newline='') as handle:
        before = handle.read()
    ending = '\r\n' if '\r\n' in before else '\n'
    patched, changed = patch_module(before.replace('\r\n', '\n'))
    if not changed:
        return False
    backup = root / BACKUP
    if backup.exists():
        raise InstallationError('Existing V7.1 backup found; refusing to overwrite: ' + str(backup))
    contents = patched.replace('\n', ending).encode('utf-8')
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.v71_', suffix='.tmp', dir=root, delete=False) as stream:
            tmp = Path(stream.name)
            stream.write(contents)
        backup.write_bytes(before.encode('utf-8'))
        os.replace(tmp, target)
    except Exception:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        if backup.exists() and target.read_bytes() == before.encode('utf-8'):
            backup.unlink(missing_ok=True)
        raise
    return True


if __name__ == '__main__':
    try:
        if install():
            print('V7.1 installed: revision_hub_v66.py updated; backup created.')
        else:
            print('V7.1 already installed; no files changed.')
        print('Now run: python -m py_compile revision_hub_v66.py study_note_actions_v71.py')
        print('Then: python -m unittest TEST_V7_1_NOTE_ACTIONS.py -v')
    except (InstallationError, SyntaxError, UnicodeError, OSError) as exc:
        raise SystemExit('V7.1 installer stopped safely: ' + str(exc))
