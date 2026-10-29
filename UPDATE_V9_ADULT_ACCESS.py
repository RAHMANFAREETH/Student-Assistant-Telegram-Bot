"""Add verified-adult access mode without changing existing pilot behavior.

--check prints a diff and changes nothing. --apply backs up modified files.
Requires V8 and V9 source files present in the StudentAssistantBot directory.
"""
from __future__ import annotations
import argparse
import difflib
import shutil
from datetime import datetime
from pathlib import Path

V8_OLD = '''def allowed(uid):
    # Fail closed: enabling V8 alone does not expose private data or AI to strangers.
    ids = {s.strip() for s in os.getenv("V8_ALLOWED_USER_IDS", "").split(",") if s.strip().isdigit()}
    return enabled() and str(uid) in ids
'''
V8_NEW = '''def allowed(uid):
    # Pilot remains the default. Verified-adults mode requires independently
    # established age eligibility stored in server-only Supabase records.
    if not enabled():
        return False
    mode = os.getenv("STUDY_ACCESS_MODE", "pilot").strip().lower()
    if mode == "pilot":
        ids = {s.strip() for s in os.getenv("V8_ALLOWED_USER_IDS", "").split(",") if s.strip().isdigit()}
        return str(uid) in ids
    if mode == "verified_adults":
        from study_access_v9 import is_verified_adult
        return is_verified_adult(uid)
    return False  # Unknown or misconfigured mode: deny, don't accidentally open access.
'''
V9_OLD = "if not allowed(m.from_user.id):send(m,'🔒 V9 is available only to approved adult pilot testers.');return False"
V9_NEW = "if not allowed(m.from_user.id):send(m,'🔒 V9 access requires approved pilot access or verified adult eligibility.');return False"


def edited(name: str, source: str) -> str:
    if name == 'v8_bot.py':
        old, new = V8_OLD, V8_NEW
    elif name == 'v9_bot.py':
        old, new = V9_OLD, V9_NEW
    else:
        raise ValueError(name)
    if new in source:
        return source
    if source.count(old) != 1:
        raise ValueError(f'{name}: expected authorization code not found exactly once. STOP; do not overwrite.')
    return source.replace(old, new, 1)


def run(root: Path, apply: bool) -> None:
    for name in ('study_access_v9.py', 'SQL_V9_ADULT_ACCESS.sql', 'TEST_V9_ADULT_ACCESS.py'):
        if not (root / name).is_file():
            raise FileNotFoundError(f'Missing package file: {name}')
    sources = {name: (root / name).read_text(encoding='utf-8') for name in ('v8_bot.py', 'v9_bot.py')}
    changed = {name: edited(name, source) for name, source in sources.items()}
    for name in sources:
        if sources[name] == changed[name]:
            print(f'{name}: already updated')
        else:
            print(''.join(difflib.unified_diff(sources[name].splitlines(True),
                    changed[name].splitlines(True), fromfile=name+':current', tofile=name+':planned')))
    if not apply:
        print('CHECK OK. No files changed.')
        return
    diff = [name for name in sources if sources[name] != changed[name]]
    if not diff:
        print('Already installed. No changes.')
        return
    backup = root / ('V9_ACCESS_BACKUP_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    backup.mkdir(exist_ok=False)
    for name in diff:
        shutil.copy2(root / name, backup / name)
    try:
        for name in diff:
            (root / name).write_text(changed[name], encoding='utf-8', newline='\n')
    except Exception:
        for name in diff:
            shutil.copy2(backup / name, root / name)
        raise
    print('Updated access checks. Backups:', backup)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--apply', action='store_true')
    a = parser.parse_args()
    run(Path(__file__).resolve().parent, a.apply)
