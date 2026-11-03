"""Guarded V11.8.8.1 compatibility patch; changes one function in smart bulk.

Prevents channel-forward captions (including pipe-separated promotional text)
from overriding the shared authorized batch metadata and filename-derived title.
"""
from __future__ import annotations
import argparse
import difflib
import shutil
from datetime import datetime
from pathlib import Path

TARGET = Path('library_smart_bulk_v1188.py')
OLD = """    original = str(getattr(m, 'caption', '') or '').strip()
    if '|' in original:
"""
NEW = """    # V11.8.8.1: channel-forward text is not a library rights declaration.
    # Trust admin-confirmed shared metadata and the actual document filename.
    # Individually authored admin uploads keep existing caption overrides.
    forwarded = bool(getattr(m, 'forward_origin', None) or
                     getattr(m, 'forward_from_chat', None) or
                     getattr(m, 'forward_date', None))
    original = '' if forwarded else str(getattr(m, 'caption', '') or '').strip()
    if '|' in original:
"""


def run(*, apply: bool) -> int:
    if not TARGET.exists():
        print('STOP: library_smart_bulk_v1188.py not found. Extract/install V11.8.8 first.')
        return 2
    text = TARGET.read_text(encoding='utf-8')
    if NEW in text:
        print('V11.8.8.1 forwarded-caption compatibility is already installed.')
        return 0
    if text.count(OLD) != 1:
        print('STOP: expected V11.8.8 caption function is missing/changed. No files modified.')
        return 2
    revised = text.replace(OLD, NEW, 1)
    diff = list(difflib.unified_diff(text.splitlines(keepends=True),
                                     revised.splitlines(keepends=True),
                                     fromfile=f'{TARGET}:current',tofile=f'{TARGET}:planned'))
    print(''.join(diff))
    if not apply:
        print('CHECK OK. One production file would change; nothing modified.')
        return 0
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup = Path(f'V11881_PREVIOUS_CHANNEL_BACKUP_{stamp}')
    backup.mkdir(parents=True, exist_ok=False)
    shutil.copy2(TARGET, backup / TARGET.name)
    try:
        TARGET.write_text(revised, encoding='utf-8')
        compile(revised, TARGET.name, 'exec')
    except Exception:
        shutil.copy2(backup / TARGET.name, TARGET)
        print('STOP: update failed; original restored.')
        return 2
    print(f'V11.8.8.1 installed. Original backed up in: {backup}')
    print('No database, OCR, ZIP, adult-access, or group-routing code changed.')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--check', action='store_true')
    g.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    raise SystemExit(run(apply=args.apply))
