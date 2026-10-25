"""V7.0 safe installer — adds private Markdown export to existing V6.9.

Only patches study_export_v69.py.  Does not change Cloudflare/Gemini,
Supabase writes, legacy menus, or the existing TXT export flow.
"""
from __future__ import annotations

import ast
import os
import shutil
import tempfile
from pathlib import Path

TARGET = 'study_export_v69.py'
HELPER = 'study_markdown_v70.py'
BACKUP = 'study_export_v69.py.before_v70.bak'
MARKER = '    # V7.0 Private Markdown Export registration\n'
REGISTRATION = (MARKER
                + '    from study_markdown_v70 import register_study_markdown_v70_handlers\n'
                + '    register_study_markdown_v70_handlers(bot, db, types, load_export_notes,\n'
                + '                                         _private_sender, _private_callback)\n'
                + '    return True\n')


class InstallationError(ValueError):
    pass


def patch_module(src):
    ast.parse(src, filename=TARGET)
    if MARKER in src:
        if (src.count(MARKER) != 1
                or src.count(REGISTRATION) != 1
                or src.count('register_study_markdown_v70_handlers(') != 1
                or src.count('from study_markdown_v70 import register_study_markdown_v70_handlers') != 1):
            raise InstallationError('Incomplete V7.0 patch; refused')
        return src, False
    required = ('def register_study_export_v69_handlers(bot, db):',
                'def v69_export_request(message):',
                'def v69_export_callback(call):',
                'def load_export_notes(db, user_id):',
                "CONFIRM = \"v69:e:confirm\"")
    if any(s not in src for s in required):
        raise InstallationError('Expected V6.9 TXT export code not found. Install V6.9 first.')
    if 'study_markdown_v70' in src or 'v70:' in src:
        raise InstallationError('Unknown/custom Markdown integration exists; refused')
    anchor = '    return True\n'
    if src.count(anchor) != 1:
        raise InstallationError('Expected single registration endpoint not found')
    patch = REGISTRATION
    dst = src.replace(anchor, patch, 1)
    ast.parse(dst, filename=TARGET)
    return dst, True


def install(root=Path('.')):
    root = Path(root)
    target = root / TARGET
    helper = root / HELPER
    if not target.is_file() or not helper.is_file():
        raise InstallationError('Missing V6.9 module or V7.0 helper. Copy files into bot root.')
    ast.parse(helper.read_text(encoding='utf-8'), filename=str(helper))
    if 'def register_study_markdown_v70_handlers(' not in helper.read_text(encoding='utf-8'):
        raise InstallationError('Unexpected V7.0 helper version')
    with target.open('r', encoding='utf-8', newline='') as f:
        before = f.read()
    line_ending = '\r\n' if '\r\n' in before else '\n'
    after, changed = patch_module(before.replace('\r\n', '\n'))
    if not changed:
        return False
    backup = root / BACKUP
    if backup.exists():
        raise InstallationError('Existing V7.0 backup: refusing to overwrite it')
    tmp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='',
                                         prefix='.v70_', suffix='.tmp', dir=root, delete=False) as f:
            tmp = Path(f.name)
            f.write(after.replace('\n', line_ending))
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
        print('V7.0 installation stopped:', exc)
        raise SystemExit(1)
    print('V7.0 ' + ('installed: private Markdown export' if changed else 'already installed; no changes made'))
