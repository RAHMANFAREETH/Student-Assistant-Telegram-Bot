"""Safe, test-only V11.8.3 regression harness refresh.

Usage:
    python -X utf8 PATCH_TEST_REGRESSION_V1183.py --check
    python -X utf8 PATCH_TEST_REGRESSION_V1183.py --apply

Changes only three obsolete TEST_*.py files and adds the isolated runner.
No production code, environment, Supabase, Telegram, or deployment changes.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime
import hashlib
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent / 'V1183_REGRESSION_BUNDLE'
ROOT = Path.cwd()
OLD_EXPECTED = {
    'TEST_OFFICE_MENU_FIX.py': '6c4db7cb2f6eb06eecddeb6fecb04f09eee690b81c467f6e3078acda57e90bbd',
    'TEST_V7_9_AUDIT.py': '9623692c6d38deeb181cdfe0aec076df5a6afe75337e8387f93c9d5f93d61579',
    'TEST_V7_13_INSTALLER.py': 'a8e0d4325de44fe8636c22a40606dffba8eccf2c21107c21e231cec638730e44',
}
ADD = 'RUN_REGRESSION_ISOLATED_V1183.py'


def normalized_sha(blob: bytes) -> str:
    return hashlib.sha256(blob.replace(b'\r\n', b'\n').replace(b'\r', b'\n').removeprefix(b'\xef\xbb\xbf')).hexdigest()


def run(apply: bool):
    edits = {}
    for name, expected in OLD_EXPECTED.items():
        src = ROOT / name
        proposed = HERE / name
        if not src.is_file() or not proposed.is_file():
            raise RuntimeError(f'Missing {name}. Place patch files in the project root.')
        current = src.read_bytes()
        planned = proposed.read_bytes()
        ast.parse(planned.decode('utf-8'), filename=name)
        if normalized_sha(current) == normalized_sha(planned):
            print('ALREADY UPDATED:', name)
            continue
        if normalized_sha(current) != expected:
            raise RuntimeError(f'{name} differs from the reviewed source. No changes made; share this file for a safe adjustment.')
        edits[name] = planned
    proposed = HERE / ADD
    if not proposed.is_file():
        raise RuntimeError(f'Missing {ADD}')
    planned = proposed.read_bytes()
    ast.parse(planned.decode('utf-8'), filename=ADD)
    if (ROOT / ADD).exists():
        if normalized_sha((ROOT / ADD).read_bytes()) != normalized_sha(planned):
            raise RuntimeError(f'Existing {ADD} differs; no changes made.')
        print('ALREADY UPDATED:', ADD)
    else:
        edits[ADD] = planned
    if not edits:
        print('CHECK OK. All test-only updates already installed. No changes.')
        return
    print('Planned test-only changes:', ', '.join(edits))
    if not apply:
        print('CHECK OK. No changes made.')
        return
    backup = ROOT / ('V1183_TEST_REGRESSION_BACKUP_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    try:
        for name in edits:
            if (ROOT / name).exists():
                shutil.copy2(ROOT / name, backup / name)
        for name, content in edits.items():
            temp = ROOT / (name + '.v1183_tmp')
            temp.write_bytes(content)
            temp.replace(ROOT / name)
    except Exception:
        for name in edits:
            if (backup / name).exists():
                shutil.copy2(backup / name, ROOT / name)
            elif name == ADD:
                (ROOT / name).unlink(missing_ok=True)
            (ROOT / (name + '.v1183_tmp')).unlink(missing_ok=True)
        raise
    print('Test-only changes installed. Originals backed up in:', backup)
    print('Production modules were not modified.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--check', action='store_true')
    actions.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        run(args.apply)
    except Exception as exc:
        print('PATCH STOPPED:', str(exc), file=sys.stderr)
        raise SystemExit(1)
