"""Minimal, safe fix for Student Assistant: Translate handler swallowing documents.

Run from the StudentAssistantBot folder after copying this file into that folder:
    python FIX_DOCUMENT_ROUTING.py

Only translate.py is modified; the original is backed up.
"""
from __future__ import annotations
import ast
from datetime import datetime
from pathlib import Path
import shutil
import sys


def patch_source(source: bytes) -> bytes:
    nl = b'\r\n' if b'\r\n' in source else b'\n'
    before = nl.join([
        b'    @bot.message_handler(',
        b'        content_types=["document"]',
        b'    )',
        b'    def translation_document_handler(',
    ])
    after = nl.join([
        b'    @bot.message_handler(',
        b'        func=lambda m: (',
        b'            translation_state.get(m.chat.id, {}).get("step")',
        b'            in {"waiting_document", "waiting_ocr_image"}',
        b'        ),',
        b'        content_types=["document"],',
        b'    )',
        b'    def translation_document_handler(',
    ])
    if after in source:
        return source  # Already fixed.
    if source.count(before) != 1:
        raise ValueError("Expected translation document handler not found exactly once. File unchanged.")
    patched = source.replace(before, after, 1)
    ast.parse(patched.decode('utf-8-sig'), filename='translate.py')
    return patched


def main() -> int:
    target = Path(__file__).resolve().parent / 'translate.py'
    if not target.is_file():
        print('ERROR: translate.py not found next to FIX_DOCUMENT_ROUTING.py')
        return 1
    original = target.read_bytes()
    try:
        updated = patch_source(original)
    except (UnicodeError, SyntaxError, ValueError) as err:
        print(f'SAFE STOP: {err}')
        return 1
    if updated == original:
        print('Already fixed. No files changed.')
        return 0
    backup = target.with_name(f'translate.py.bak_document_fix_{datetime.now():%Y%m%d_%H%M%S}')
    shutil.copy2(target, backup)
    temp = target.with_name('translate.py.tmp_document_fix')
    try:
        temp.write_bytes(updated)
        temp.replace(target)
    except Exception:
        temp.unlink(missing_ok=True)
        shutil.copy2(backup, target)
        raise
    print('SUCCESS: Fixed document routing in translate.py')
    print(f'Backup: {backup.name}')
    print('Next: python -m py_compile translate.py study_materials.py main.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
