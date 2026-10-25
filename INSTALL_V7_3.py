"""Safe V7.3 installer: patch ONLY the existing V7.2 revision_hub_v66.py.

Idempotent, preflights the expected code layout, preserves Windows CRLF,
creates a byte-for-byte backup, refuses existing backup conflicts.
"""
from __future__ import annotations

import ast
import os
import tempfile
from pathlib import Path

TARGET = 'revision_hub_v66.py'
HELPER = 'study_collections_v73.py'
SQL = 'SQL_V7_3_COLLECTIONS.sql'
BACKUP = 'revision_hub_v66.py.before_v73.bak'

MENU_MARKER = '    # V7.3 Collections menu\n'
MENU_BLOCK = MENU_MARKER + '    kb.row(types.KeyboardButton("📁 My Collections"))\n'
MENU_ANCHOR = '    # V7.2 Study Notes Organizer menu\n'
NOTE_MARKER = '    # V7.3 Add saved AI note to a collection\n'
NOTE_BLOCK = (NOTE_MARKER
              + '    from study_collections_v73 import note_collection_keyboard\n'
              + '    collections_action = note_collection_keyboard(types, row.get("id"))\n'
              + '    if collections_action is not None:\n'
              + '        bot.send_message(chat_id, "📁 Add this AI note to a collection:", reply_markup=collections_action)\n')
NOTE_ANCHOR = '    # V7.2 Note Organizer shortcut\n'
REG_MARKER = '    # V7.3 Collections registration\n'
REG_BLOCK = (REG_MARKER
             + '    from study_collections_v73 import register_study_collections_v73_handlers\n'
             + '    register_study_collections_v73_handlers(bot, supabase, load_note, types)\n')
REG_ANCHOR = '    # V7.2 Study Notes Organizer registration\n'

class InstallationError(ValueError):
    pass


def patch_module(source: str):
    ast.parse(source, filename=TARGET)
    normalized = source.replace('\r\n', '\n')
    markers = (MENU_MARKER,NOTE_MARKER,REG_MARKER)
    blocks = (MENU_BLOCK,NOTE_BLOCK,REG_BLOCK)
    presence = [marker in normalized for marker in markers]
    if any(presence):
        if not all(presence) or any(normalized.count(block) != 1 for block in blocks):
            raise InstallationError('Partial or customized V7.3 patch detected; no files changed')
        if normalized.count('from study_collections_v73 import') != 2:
            raise InstallationError('Unexpected V7.3 imports; no files changed')
        return normalized, False
    checks = (
        'def register_revision_hub_v66_handlers(bot, show_main_menu):',
        'def load_note(db, user_id: int, note_id: int):',
        'register_study_organizer_v72_handlers(bot, supabase, load_note, load_ai_note_page, types)',
        'register_study_note_actions_v71_handlers(bot, supabase, load_note, send_study_library)',
    )
    if any(c not in normalized for c in checks):
        raise InstallationError('V7.2 code not recognized. Install V7.2 before V7.3.')
    for anchor in (MENU_ANCHOR, NOTE_ANCHOR, REG_ANCHOR):
        if normalized.count(anchor) != 1:
            raise InstallationError('V7.2 code layout is customized; refusing unsafe patch')
    result = normalized.replace(MENU_ANCHOR, MENU_BLOCK+MENU_ANCHOR, 1)
    result = result.replace(NOTE_ANCHOR, NOTE_BLOCK+NOTE_ANCHOR,1)
    result = result.replace(REG_ANCHOR, REG_BLOCK+'\n'+REG_ANCHOR,1)
    ast.parse(result,filename=TARGET)
    return result, True


def install(root=Path('.')):
    root=Path(root)
    target=root/TARGET
    for f in (TARGET,HELPER,SQL,'study_organizer_v72.py'):
        if not (root/f).is_file():
            raise InstallationError(f'Missing required file: {f}')
    helper=(root/HELPER).read_text(encoding='utf-8')
    ast.parse(helper,filename=HELPER)
    if 'def register_study_collections_v73_handlers(' not in helper:
        raise InstallationError('V7.3 helper not recognized')
    sql=(root/SQL).read_text(encoding='utf-8')
    for table in ('public.ai_study_collections_v73','public.ai_study_collection_notes_v73'):
        if f'CREATE TABLE IF NOT EXISTS {table}' not in sql:
            raise InstallationError('V7.3 SQL file not recognized')
    original=target.read_bytes()
    try:
        source=original.decode('utf-8')
    except UnicodeError:
        raise InstallationError('Expected UTF-8 encoded revision_hub_v66.py') from None
    newline='\r\n' if b'\r\n' in original else '\n'
    patched,changed=patch_module(source)
    if not changed:
        return False
    backup=root/BACKUP
    if backup.exists():
        raise InstallationError(f'Backup conflict: {BACKUP} exists, refusing overwrite')
    temp=None
    try:
        with tempfile.NamedTemporaryFile(prefix='.v73_',suffix='.tmp',dir=root,delete=False) as stream:
            temp=Path(stream.name)
            stream.write(patched.replace('\n',newline).encode('utf-8'))
        backup.write_bytes(original)
        os.replace(temp,target)
        return True
    except Exception:
        if temp is not None:
            temp.unlink(missing_ok=True)
        if backup.exists() and target.read_bytes()==original:
            backup.unlink(missing_ok=True)
        raise

if __name__=='__main__':
    try:
        changed=install()
        print('V7.3 installed; original revision_hub_v66.py backed up.' if changed
              else 'V7.3 already installed; no files changed.')
        print('Next: run SQL_V7_3_COLLECTIONS.sql in the same Supabase project.')
        print('Then: python -m unittest TEST_V7_3_COLLECTIONS.py -v')
    except (InstallationError,OSError,UnicodeError,SyntaxError) as exc:
        raise SystemExit('V7.3 installer stopped safely: '+str(exc))
