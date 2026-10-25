"""Safe, idempotent V7.2 installer for the current V7.1 revision_hub_v66.py.

Does not modify main.py, navigation, AI providers, Supabase data or environment.
Run SQL separately in the existing Supabase SQL editor.
"""
from __future__ import annotations

import ast
import os
import tempfile
from pathlib import Path

TARGET = 'revision_hub_v66.py'
HELPER = 'study_organizer_v72.py'
SQL = 'SQL_V7_2_NOTE_ORGANIZER.sql'
BACKUP = 'revision_hub_v66.py.before_v72.bak'

MENU_MARKER = '    # V7.2 Study Notes Organizer menu\n'
MENU_BLOCK = MENU_MARKER + '    kb.row(types.KeyboardButton("🗂 Organize AI Notes"))\n'
MENU_ANCHOR = '    kb.row(types.KeyboardButton(REMINDERS), types.KeyboardButton("🏠 Main Menu"))\n'
ACTION_MARKER = '    # V7.2 Note Organizer shortcut\n'
ACTION_BLOCK = (ACTION_MARKER
                + '    from study_organizer_v72 import note_organizer_keyboard\n'
                + '    org_actions = note_organizer_keyboard(types, row.get("id"))\n'
                + '    if org_actions is not None:\n'
                + '        bot.send_message(chat_id, "🗂 Organize this saved AI note:", reply_markup=org_actions)\n')
ACTION_ANCHOR = '    # V7.1 Individual Note Quick Actions\n'
REGISTER_MARKER = '    # V7.2 Study Notes Organizer registration\n'
REGISTER_BLOCK = (REGISTER_MARKER
                  + '    from study_organizer_v72 import register_study_organizer_v72_handlers\n'
                  + '    register_study_organizer_v72_handlers(bot, supabase, load_note, load_ai_note_page, types)\n')
REGISTER_ANCHOR = '    # V7.1 Individual Note Quick Actions registration\n'


class InstallationError(ValueError):
    pass


def patch_module(source: str):
    ast.parse(source, filename=TARGET)
    normalized = source.replace('\r\n', '\n')
    marker_presence = tuple(marker in normalized for marker in
                            (MENU_MARKER, ACTION_MARKER, REGISTER_MARKER))
    if any(marker_presence):
        if not all(marker_presence):
            raise InstallationError('Partial V7.2 installation found; refusing changes')
        if any(normalized.count(block) != 1 for block in (MENU_BLOCK, ACTION_BLOCK, REGISTER_BLOCK)):
            raise InstallationError('Unexpected custom V7.2 code; refusing changes')
        if normalized.count('from study_organizer_v72 import') != 2:
            raise InstallationError('Unexpected V7.2 imports; refusing changes')
        return normalized, False
    required = (
        'def register_revision_hub_v66_handlers(bot, show_main_menu):',
        'def load_note(db, user_id: int, note_id: int):',
        'def load_ai_note_page(db, uid, page):',
        'register_study_note_actions_v71_handlers(bot, supabase, load_note, send_study_library)',
        'def _send_note(bot, chat_id, row):',
        '# V7.1 Individual Note Quick Actions registration',
    )
    if any(part not in normalized for part in required):
        raise InstallationError('V7.1 revision hub not found; install V7.1 first')
    for anchor in (MENU_ANCHOR, ACTION_ANCHOR, REGISTER_ANCHOR):
        if normalized.count(anchor) != 1:
            raise InstallationError('Unexpected V7.1 code layout near organizer insertion point')
    patched = normalized.replace(MENU_ANCHOR, MENU_BLOCK + MENU_ANCHOR, 1)
    patched = patched.replace(ACTION_ANCHOR, ACTION_BLOCK + ACTION_ANCHOR, 1)
    patched = patched.replace(REGISTER_ANCHOR, REGISTER_BLOCK + '\n' + REGISTER_ANCHOR, 1)
    ast.parse(patched, filename=TARGET)
    return patched, True


def install(root=Path('.')):
    root = Path(root)
    target = root / TARGET
    for path in (target, root / HELPER, root / SQL, root / 'study_note_actions_v71.py'):
        if not path.is_file():
            raise InstallationError(f'Missing required file: {path.name}')
    helper = (root / HELPER).read_text(encoding='utf-8')
    ast.parse(helper, filename=HELPER)
    if 'def register_study_organizer_v72_handlers(' not in helper:
        raise InstallationError('Unrecognized V7.2 helper file')
    script = (root / SQL).read_text(encoding='utf-8')
    if 'CREATE TABLE IF NOT EXISTS public.ai_note_organizer_v72' not in script:
        raise InstallationError('V7.2 SQL file is missing or unexpected')
    with target.open('r', encoding='utf-8', newline='') as stream:
        existing = stream.read()
    newline = '\r\n' if '\r\n' in existing else '\n'
    patched, changed = patch_module(existing)
    if not changed:
        return False
    backup = root / BACKUP
    if backup.exists():
        raise InstallationError('Existing V7.2 backup exists; refusing to overwrite')
    original_bytes = existing.encode('utf-8')
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.v72_', suffix='.tmp',
                                         dir=root, delete=False) as stream:
            temp_file = Path(stream.name)
            stream.write(patched.replace('\n', newline).encode('utf-8'))
        backup.write_bytes(original_bytes)
        os.replace(temp_file, target)
    except Exception:
        if temp_file:
            temp_file.unlink(missing_ok=True)
        if backup.exists() and target.read_bytes() == original_bytes:
            backup.unlink(missing_ok=True)
        raise
    return True


if __name__ == '__main__':
    try:
        changed = install()
        print('V7.2 installed: revision_hub_v66.py updated; backup created.' if changed
              else 'V7.2 already installed; no files changed.')
        print('Next: run SQL_V7_2_NOTE_ORGANIZER.sql in Supabase SQL Editor.')
        print('Then: python -m unittest TEST_V7_2_ORGANIZER.py -v')
    except (InstallationError, OSError, UnicodeError, SyntaxError) as exc:
        raise SystemExit('V7.2 installer stopped safely: ' + str(exc))
