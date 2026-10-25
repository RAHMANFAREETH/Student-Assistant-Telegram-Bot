"""V6.9 version-aware installer: wire private AI study note export into V6.8.

Edits revision_hub_v66.py only; additional module study_export_v69.py is copied
from the ZIP. Stops on unexpected code instead of overwriting custom changes.
"""
from __future__ import annotations

import ast
import os
import shutil
import tempfile
from pathlib import Path

TARGET = 'revision_hub_v66.py'
BACKUP = TARGET + '.before_v69.bak'
MARKER = '# V6.9 AI Study Notes Export registration'


class InstallationError(ValueError):
    pass


def _one(src, old, new, name):
    if src.count(old) != 1:
        raise InstallationError(f'Unexpected {name}; no changes made')
    return src.replace(old, new, 1)


def patch_module(src):
    ast.parse(src, filename=TARGET)
    if MARKER in src:
        if (src.count(MARKER) != 1
                or src.count('register_study_export_v69_handlers(bot, supabase)') != 1
                or src.count('from study_export_v69 import register_study_export_v69_handlers') != 1):
            raise InstallationError('Incomplete V6.9 patch detected')
        return src, False
    required = ('# V6.8 Full-Text Saved AI Note Search',
                'def revision_content_search(message):',
                'def revision_library_page(call):',
                'def register_revision_hub_v66_handlers(bot, show_main_menu):')
    if any(key not in src for key in required):
        raise InstallationError('V6.8 prerequisite missing. Install V6.8 before V6.9.')
    if 'study_export_v69' in src or 'v69:' in src:
        raise InstallationError('Unknown/custom V6.9 changes already present')
    src = _one(src,
               'from safe_utils import split_telegram_text\n',
               'from safe_utils import split_telegram_text\n'
               'from study_export_v69 import register_study_export_v69_handlers\n',
               'import location')
    src = _one(src,
               'Full text: /studysearch biology',
               'Full text: /studysearch biology\\nExport: /studyexport',
               'library hint')
    src = _one(src,
               '⏰ Revision Reminders — use existing planner and reminders",',
               '⏰ Revision Reminders — use existing planner and reminders\\n"\n'
               '                         "📤 Export AI Notes — /studyexport",',
               'hub hint')
    old = '    return True\n'
    # Use exact location of the final hub registration return, not other returns.
    if src.count(old) != 1:
        raise InstallationError('Unexpected revision registration ending')
    src = _one(src, old,
               '    # V6.9 AI Study Notes Export registration\n'
               '    register_study_export_v69_handlers(bot, supabase)\n'
               '    return True\n', 'registration end')
    ast.parse(src, filename=TARGET)
    return src, True


def install(root=Path('.')):
    root = Path(root)
    path = root / TARGET
    helper = root / 'study_export_v69.py'
    if not path.is_file() or not helper.is_file():
        raise InstallationError('Missing V6.8 revision hub or study_export_v69.py. Copy all ZIP files.')
    ast.parse(helper.read_text(encoding='utf-8'), filename=str(helper))
    if 'def register_study_export_v69_handlers(bot, db):' not in helper.read_text(encoding='utf-8'):
        raise InstallationError('Unexpected V6.9 helper version')
    with path.open('r', encoding='utf-8', newline='') as f:
        old = f.read()
    ending = '\r\n' if '\r\n' in old else '\n'
    new, changed = patch_module(old.replace('\r\n', '\n'))
    if not changed:
        return False
    backup = root / BACKUP
    if backup.exists():
        raise InstallationError('V6.9 backup already exists. Refusing to overwrite.')
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='',
                                         prefix='.v69_', suffix='.tmp', dir=root, delete=False) as f:
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
        print('V6.9 installation stopped:', exc)
        raise SystemExit(1)
    print('V6.9 ' + ('installed successfully' if changed else 'already installed; no files changed'))
