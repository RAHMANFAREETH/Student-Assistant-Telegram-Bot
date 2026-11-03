"""V7.16 safe installer: add Scan Document without overwriting existing tools.

Run in the existing StudentAssistantBot project folder:
 python INSTALL_V7_16.py --dry-run
 python INSTALL_V7_16.py
 python INSTALL_V7_16.py --rollback

Modifies only pdf_tools.py, requirements.txt; adds scan_document_v716.py and its tests.
No network, database, Telegram, Render or Git actions.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path.cwd().resolve()
SOURCE = Path(__file__).resolve().parent / 'V716_FILES'
BACKUP = ROOT / '.v716_backup'
MANIFEST = BACKUP / 'manifest.json'
MODIFIED = ('pdf_tools.py', 'requirements.txt')
ADDED = ('scan_document_v716.py', 'TEST_V7_16_SCAN_DOCUMENT.py')
REQUIREMENT = 'opencv-python-headless>=4.10,<5'


def hash_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def atomic(path: Path, raw: bytes):
    fd, tmp = tempfile.mkstemp(prefix='.v716_', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(raw)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def encode_like(original: bytes, text: str) -> bytes:
    return text.replace('\n', '\r\n').encode('utf-8') if b'\r\n' in original else text.encode('utf-8')


def prereqs():
    for file in MODIFIED:
        if not (ROOT / file).is_file():
            raise RuntimeError(f'Missing {file}; run this installer inside your StudentAssistantBot project.')
    for file in ADDED + ('PATCH_V7_16_CORE.py', 'SCAN_HANDLERS_V716.txt'):
        if not (SOURCE / file).is_file():
            raise RuntimeError(f'Missing installer component V716_FILES/{file}.')


def plan():
    prereqs()
    sys.path.insert(0, str(SOURCE))
    from PATCH_V7_16_CORE import patch_pdf_tools
    src = (ROOT / 'pdf_tools.py').read_bytes()
    old = src.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')
    fragment = (SOURCE / 'SCAN_HANDLERS_V716.txt').read_text(encoding='utf-8')
    patched = patch_pdf_tools(old, fragment)
    ast.parse(patched, 'pdf_tools.py')
    for filename in ADDED:
        ast.parse((SOURCE / filename).read_text(encoding='utf-8'), filename)
    req_raw = (ROOT / 'requirements.txt').read_bytes()
    req = req_raw.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')
    if 'opencv-python-headless' in req:
        patched_req = req
    elif req.endswith('\n'):
        patched_req = req + '\n# V7.16 offline scanner (OpenCV)\n' + REQUIREMENT + '\n'
    else:
        patched_req = req + '\n\n# V7.16 offline scanner (OpenCV)\n' + REQUIREMENT + '\n'
    after = {'pdf_tools.py': encode_like(src, patched),
             'requirements.txt': encode_like(req_raw, patched_req)}
    installed = patched == old and patched_req == req
    preexisting = set()
    for name in ADDED:
        target = ROOT / name
        if target.exists():
            # Existing files must match the source we are about to install.
            # Ignore Windows CRLF differences, but do not overwrite custom edits.
            if not target.is_file():
                raise RuntimeError(f'{name} exists but is not a regular file. No files changed.')
            source_contents = (SOURCE / name).read_bytes().replace(b'\r\n', b'\n')
            target_contents = target.read_bytes().replace(b'\r\n', b'\n')
            if target_contents != source_contents:
                raise RuntimeError(
                    f'{name} already exists and differs from V7.16 package. '
                    'Back up/review it; no files changed.'
                )
            preexisting.add(name)
    if installed:
        if len(preexisting) != len(ADDED):
            raise RuntimeError('V7.16 marker present but scanner module/test is missing. No files changed.')
    elif BACKUP.exists() and any(BACKUP.iterdir()):
        raise RuntimeError('Existing .v716_backup present. Review before installing again.')
    return after, installed, preexisting


def install(dry: bool):
    after, installed, preexisting = plan()
    if installed:
        print('V7.16 already installed; no files changed.')
        return
    print('V7.16 will update: pdf_tools.py, requirements.txt')
    print('V7.16 scanner files already present and matching:', ', '.join(sorted(preexisting)) or 'none')
    print('V7.16 will add missing:', ', '.join(n for n in ADDED if n not in preexisting) or 'none')
    print('Preserved: main.py, broadcast, Gemini, Cloudflare, Supabase, current PDF/crop modules.')
    if dry:
        print('Dry-run OK. No files changed.')
        return
    before = {name: (ROOT / name).read_bytes() for name in MODIFIED}
    newfiles = {name: (SOURCE / name).read_bytes() for name in ADDED if name not in preexisting}
    # Pre-create backup before changing project files.
    BACKUP.mkdir(exist_ok=False)
    manifest = {'modified': {}, 'added': {}}
    for name, raw in before.items():
        (BACKUP / name).write_bytes(raw)
        manifest['modified'][name] = {'before': hash_bytes(raw), 'after': hash_bytes(after[name])}
    for name, raw in newfiles.items():
        manifest['added'][name] = hash_bytes(raw)
    (BACKUP / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    written = []
    try:
        for name, raw in after.items():
            atomic(ROOT / name, raw)
            written.append(name)
        for name, raw in newfiles.items():
            atomic(ROOT / name, raw)
            written.append(name)
    except Exception:
        for name in written:
            if name in before:
                atomic(ROOT / name, before[name])
            else:
                (ROOT / name).unlink(missing_ok=True)
        shutil.rmtree(BACKUP)
        raise
    print('V7.16 installed. Backups: .v716_backup/')
    print('Next: python -m pip install -r requirements.txt')
    print('Then: python -m unittest TEST_V7_16_SCAN_DOCUMENT.py -v')


def rollback():
    if not MANIFEST.is_file():
        raise RuntimeError('V7.16 backup manifest is missing; cannot automatically rollback.')
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for name, info in manifest['modified'].items():
        p = ROOT / name
        if not p.is_file() or hash_bytes(p.read_bytes()) != info['after']:
            raise RuntimeError(f'{name} edited after install; rollback stopped safely.')
    for name, digest in manifest['added'].items():
        p = ROOT / name
        if not p.is_file() or hash_bytes(p.read_bytes()) != digest:
            raise RuntimeError(f'{name} edited after install; rollback stopped safely.')
    for name, info in manifest['modified'].items():
        raw = (BACKUP / name).read_bytes()
        if hash_bytes(raw) != info['before']:
            raise RuntimeError('Backup hash mismatch; rollback stopped.')
    for name in manifest['modified']:
        atomic(ROOT / name, (BACKUP / name).read_bytes())
    for name in manifest['added']:
        (ROOT / name).unlink()
    shutil.rmtree(BACKUP)
    print('V7.16 rollback complete. Original files restored.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--rollback', action='store_true')
    args = parser.parse_args()
    try:
        if args.rollback:
            rollback()
        else:
            install(args.dry_run)
    except (OSError, RuntimeError, ValueError, SyntaxError, UnicodeError) as error:
        print('V7.16 safely stopped:', error, file=sys.stderr)
        sys.exit(1)
