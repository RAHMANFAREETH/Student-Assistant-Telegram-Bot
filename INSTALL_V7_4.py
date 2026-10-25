"""V7.4 safe installer; adds Collection Tools to *existing* V7.3 module only.

Preflight, UTF-8, idempotent, atomic target replacement and lossless backup.
Does not alter main.py, revision hub, Notes or AI provider modules.
"""
from __future__ import annotations

import ast
import os
import tempfile
from pathlib import Path

TARGET = 'study_collections_v73.py'
HELPER = 'study_collection_tools_v74.py'
BACKUP = 'study_collections_v73.py.before_v74.bak'

MENU_ANCHOR = "    inventory = '\\n'.join("
MENU_MARKER = '    # V7.4 Collection Tools shortcut\n'
MENU_BLOCK = (MENU_MARKER
              + "    kb.add(types.InlineKeyboardButton('📊 Collection Tools',callback_data='v74:menu:0'))\n")
BUTTON_ANCHOR = "    kb.add(types.InlineKeyboardButton('🗑 Delete Collection',callback_data=f'v73:x:{cid}'))\n"
BUTTON_MARKER = '    # V7.4 Export current collection as Markdown\n'
BUTTON_BLOCK = (BUTTON_MARKER
                + "    kb.add(types.InlineKeyboardButton('📤 Export Collection (MD)',callback_data=f'v74:request:{cid}'))\n")
REG_ANCHOR = ("            bot.answer_callback_query(call.id,'Collections temporarily unavailable.',show_alert=True)\n"
              "    return True\n")
REG_MARKER = '    # V7.4 Collection Tools registration\n'
REG_BLOCK = (REG_MARKER
             + '    from study_collection_tools_v74 import register_study_collection_tools_v74_handlers\n'
             + '    register_study_collection_tools_v74_handlers(bot, db, types)\n')


class InstallationError(ValueError):
    pass


def patch_module(source):
    ast.parse(source, filename=TARGET)
    normalized = source.replace('\r\n', '\n')
    markers = (MENU_MARKER, BUTTON_MARKER, REG_MARKER)
    blocks = (MENU_BLOCK, BUTTON_BLOCK, REG_BLOCK)
    present = [marker in normalized for marker in markers]
    if any(present):
        if not all(present) or any(normalized.count(block) != 1 for block in blocks):
            raise InstallationError('Incomplete or customized V7.4 patch; no changes made')
        if normalized.count('from study_collection_tools_v74 import') != 1:
            raise InstallationError('Unexpected V7.4 import layout')
        return normalized, False
    prerequisites = (
        'def register_study_collections_v73_handlers(bot, db, load_note, types):',
        "    kb.add(types.InlineKeyboardButton('📁 '+name,callback_data=f'v73:c:{cid}'))",
        'def list_memberships(db, uid, cid, page=0):',
        'def get_collection(db, uid, collection_id):',
    )
    if any(s not in normalized for s in prerequisites):
        raise InstallationError('V7.3 collections module not recognized. Install V7.3 first.')
    for anchor in (MENU_ANCHOR, BUTTON_ANCHOR, REG_ANCHOR):
        if normalized.count(anchor) != 1:
            raise InstallationError('V7.3 module customized; refusing unsafe patch')
    patched = normalized.replace(MENU_ANCHOR, MENU_BLOCK + MENU_ANCHOR, 1)
    patched = patched.replace(BUTTON_ANCHOR, BUTTON_BLOCK + BUTTON_ANCHOR, 1)
    patched = patched.replace(REG_ANCHOR, REG_ANCHOR.replace('    return True\n',REG_BLOCK + '    return True\n'), 1)
    ast.parse(patched, filename=TARGET)
    return patched, True


def install(root=Path('.')):
    root = Path(root)
    for name in (TARGET, HELPER, 'study_markdown_v70.py'):
        if not (root/name).is_file():
            raise InstallationError(f'Missing required file: {name}')
    helper = (root/HELPER).read_text(encoding='utf-8')
    ast.parse(helper, filename=HELPER)
    if 'def register_study_collection_tools_v74_handlers(' not in helper:
        raise InstallationError('V7.4 helper not recognized')
    original = (root/TARGET).read_bytes()
    try:
        source = original.decode('utf-8')
    except UnicodeError:
        raise InstallationError(f'{TARGET} must be UTF-8') from None
    newline = '\r\n' if b'\r\n' in original else '\n'
    new_source, changed = patch_module(source)
    if not changed:
        return False
    backup = root/BACKUP
    if backup.exists():
        raise InstallationError(f'Backup conflict: {BACKUP}; no files changed')
    temp = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.v74_',suffix='.tmp',dir=root,delete=False) as stream:
            temp = Path(stream.name)
            stream.write(new_source.replace('\n', newline).encode('utf-8'))
        backup.write_bytes(original)
        os.replace(temp, root/TARGET)
        return True
    except Exception:
        if temp is not None:
            temp.unlink(missing_ok=True)
        if backup.exists() and (root/TARGET).read_bytes() == original:
            backup.unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    try:
        result = install()
        print('V7.4 installed; V7.3 collections module backed up.' if result
              else 'V7.4 already installed; no files changed.')
        print('Next: python -m unittest TEST_V7_4_COLLECTION_TOOLS.py -v')
    except (InstallationError, OSError, UnicodeError, SyntaxError) as exc:
        raise SystemExit('V7.4 installer stopped safely: ' + str(exc))
