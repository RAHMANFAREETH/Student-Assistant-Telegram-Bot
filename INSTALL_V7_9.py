#!/usr/bin/env python3
"""Safe V7.9 update: strict source hash checks, existing .gitignore left untouched."""
from pathlib import Path
import argparse
import hashlib
import os
import shutil
import sys

FILES = {'main.py': ['cc20d1bcae25f33e63f0f61f6e8e320bab240e33af3ebd42d8f67f7aa4536d8e', 'de922f13ff0eebbb56ea0745c36f5a1e7d3409c0c5beead4c2cab657781fa66c'], 'ui_v57.py': ['a9199b37e5082856e2f0c8f9f63d7084cb6fbb792d98e26d458f298038bd177e', 'c2afd9a44e3abfba5ae66ba5fe8d96ec52e597ab6291569479a8f3e14cd8241a'], 'navigation.py': ['3b814efb14a692a3269aa1878b9877f8f9bd5454977a549d8b7943e48a3b3b94', 'b8b64694b11e5a3900503908411bf2456fcbb0b54b16eae38dd50f90248c9f6a'], 'system_health.py': ['e7081bf69941c07c166902c8fbf745df6bb55ad41a4162395a905df00da5dff1', 'c637ed7c1acb57b09da165f3d1282712601bcdae4cfe21c9f1d3ae97214f27d8'], 'study_materials.py': ['0e7cb4c8b65c020d420b61a3c3d0d6e846c36a377f482b5da304ce6f1bd8f1bb', 'cebbe486090dbe7740a378d9dc361e0fd0bb719554dca5ebce3731a3a5b0a3e3'], 'user_help_v79.py': [None, '4353d06b48f1b8fc0b46b85cc05ab9759a89d28e129041d2a81f80754fba036d'], 'TEST_V7_9_AUDIT.py': [None, '9623692c6d38deeb181cdfe0aec076df5a6afe75337e8387f93c9d5f93d61579'], 'README_V7_9.md': [None, 'b3ab98cca8b281568a37e66fa8448f805a68164711230c559b228f04c2605175']}
ROOT = Path(__file__).resolve().parent
UPDATED = ROOT / "V79_UPDATED"
BACKUP = ROOT / "v79_backups"


def digest(blob):
    return hashlib.sha256(blob.replace(b"\r\n", b"\n")).hexdigest()


def verify(rollback=False):
    if not UPDATED.is_dir():
        raise RuntimeError("V79_UPDATED folder is missing. Extract the complete patch ZIP first.")
    updates = []
    for name, (oldhash, newhash) in FILES.items():
        target = ROOT/name
        source = UPDATED/name
        if not source.is_file() or digest(source.read_bytes()) != newhash:
            raise RuntimeError("Patch files missing or changed: " + name)
        existing = digest(target.read_bytes()) if target.exists() else None
        if not rollback:
            if existing == newhash:
                continue
            if existing != oldhash:
                raise RuntimeError("Unexpected local edits in " + name + ". No files modified. Update requires the original V7.8 ZIP contents.")
        else:
            if existing == oldhash:
                continue
            if existing != newhash:
                raise RuntimeError("Cannot safely roll back: " + name + " has been modified since V7.9. No files modified.")
            if oldhash is not None:
                backup = BACKUP/(name+'.before_v79.bak')
                if not backup.is_file() or digest(backup.read_bytes()) != oldhash:
                    raise RuntimeError("Verified backup missing or changed for " + name)
        updates.append(name)
    return updates


def atomic_write(destination, content):
    temporary = destination.with_name(destination.name + '.v79_inprogress')
    try:
        with temporary.open('wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def install(dry_run=False, rollback=False):
    changes = verify(rollback=rollback)
    print('NOTE: existing .gitignore is preserved unchanged; review its secret-ignore rules.')
    action = 'ROLLBACK' if rollback else 'INSTALL'
    if not changes:
        print('V7.9: already in requested state; no files changed.')
        return 0
    print(action+':', ', '.join(changes))
    if dry_run:
        print('DRY RUN: verified; no changes made.')
        return 0
    BACKUP.mkdir(exist_ok=True)
    if not rollback:
        # A verified prior backup may be reused after a safe rollback.
        for name in changes:
            backup = BACKUP/(name+'.before_v79.bak')
            if FILES[name][0] is not None and backup.exists() and digest(backup.read_bytes()) != FILES[name][0]:
                raise RuntimeError('Existing V7.9 backup differs: '+name+'. Stop and inspect v79_backups manually.')
        for name in changes:
            backup = BACKUP/(name+'.before_v79.bak')
            if FILES[name][0] is not None and not backup.exists():
                atomic_write(backup, (ROOT/name).read_bytes())
    applied=[]
    try:
        for name in changes:
            target=ROOT/name
            oldhash,newhash=FILES[name]
            if rollback:
                if oldhash is None:
                    target.unlink()
                else:
                    atomic_write(target, (BACKUP/(name+'.before_v79.bak')).read_bytes())
            else:
                atomic_write(target, (UPDATED/name).read_bytes())
            applied.append(name)
    except Exception:
        # Restore changed files if a write or removal failed.
        for name in reversed(applied):
            oldhash,newhash=FILES[name]
            target=ROOT/name
            if rollback:
                atomic_write(target, (UPDATED/name).read_bytes())
            elif oldhash is None:
                if target.exists(): target.unlink()
            else:
                atomic_write(target, (BACKUP/(name+'.before_v79.bak')).read_bytes())
        raise
    print('V7.9 '+ ('rollback' if rollback else 'installation') +' completed.')
    if not rollback:
        print('Test: python -m unittest TEST_V7_9_AUDIT.py -v')
        print('Then: review .gitignore security exclusions, diff, commit, and push after reviewing.')
    return 0


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--dry-run',action='store_true')
    p.add_argument('--rollback',action='store_true')
    args=p.parse_args()
    try:
        raise SystemExit(install(dry_run=args.dry_run, rollback=args.rollback))
    except Exception as exc:
        print('V7.9 safely stopped:', str(exc), file=sys.stderr)
        raise SystemExit(1)
