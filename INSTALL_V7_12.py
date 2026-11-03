"""V7.12 safe install: known users + broadcastall on existing V7.11 bot.

No network or Supabase calls. No changes unless installed after a successful dry-run.
To roll back locally: python INSTALL_V7_12.py --rollback
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone

ROOT = Path.cwd()
PACKAGE = Path(__file__).resolve().parent / "V712_FILES"
BACKUP = ROOT / ".v710_backups" / "v712_known_users"
MANIFEST = BACKUP / "manifest.json"
ADDED = ["SQL_V7_12_KNOWN_USERS.sql", "TEST_V7_12_KNOWN_USERS.py", "README_V7_12.md"]
# Exact baseline V7.10 module content. Check in normalized UTF-8 to support Windows CRLF.
OLD_BROADCAST_HASH = "4f4e85947d34fd5e458493076d5778d3ae296f972fa18d40ef89e24e62e54bda"

def norm(raw):
    return raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")

def digest(data):
    return hashlib.sha256(data).hexdigest()

def read_bytes(path):
    return path.read_bytes() if path.exists() else None

def patch_main(raw):
    newline = "\r\n" if b"\r\n" in raw else "\n"
    text = norm(raw)
    already = "track_known_private_user(update)" in text
    imp_old = "from broadcast_v710 import register_broadcast_handlers"
    imp_new = ("from broadcast_v710 import register_broadcast_handlers, "
               "register_known_broadcast_handlers, track_known_private_user")
    anchor = "        bot.process_new_updates(\n"
    reg_old = "register_broadcast_handlers(bot)\n"
    reg_new = ("broadcast_service = register_broadcast_handlers(bot)\n"
               "register_known_broadcast_handlers(bot, broadcast_service)\n")
    if already:
        if imp_new not in text or reg_new not in text:
            raise ValueError("Partial V7.12 main.py changes detected; inspect manually.")
        return raw
    if text.count(imp_old) != 1 or text.count(anchor) != 1 or text.count(reg_old) != 1:
        raise ValueError("Cannot find expected V7.10 import/registration/webhook anchors in main.py. No change made.")
    text = text.replace(imp_old, imp_new, 1)
    text = text.replace(reg_old, reg_new, 1)
    text = text.replace(anchor,
                        "        track_known_private_user(update)\n\n" + anchor, 1)
    return text.replace("\n", newline).encode("utf-8")

def plan():
    if not (ROOT / "main.py").is_file() or not (ROOT / "broadcast_v710.py").is_file():
        raise ValueError("Run from your existing V7.10/V7.11 StudentAssistantBot folder.")
    for name in ["broadcast_v710.py", *ADDED]:
        if not (PACKAGE / name).is_file():
            raise ValueError(f"Missing V712_FILES/{name}. Extract full ZIP first.")
    original = read_bytes(ROOT / "broadcast_v710.py")
    target = read_bytes(PACKAGE / "broadcast_v710.py")
    if norm(original) != norm(target) and digest(norm(original).encode()) != OLD_BROADCAST_HASH:
        raise ValueError("broadcast_v710.py has local edits or an unexpected version. Refusing to overwrite.")
    targets = {"main.py": patch_main(read_bytes(ROOT / "main.py")),
               "broadcast_v710.py": target}
    for name in ADDED:
        dest = read_bytes(ROOT / name)
        src = read_bytes(PACKAGE / name)
        if dest is not None and dest != src:
            raise ValueError(f"Existing {name} differs from V7.12 package. Refusing to overwrite.")
        targets[name] = src
    return targets

def install(targets, dry_run=False):
    for name, after in targets.items():
        before = read_bytes(ROOT / name)
        action = "ADD" if before is None else "UNCHANGED" if before == after else "UPDATE"
        print(f"{action:10} {name}")
    if dry_run:
        print("Dry run only — no files, Supabase or Render changes made.")
        return
    if MANIFEST.exists():
        if all(read_bytes(ROOT / name) == data for name, data in targets.items()):
            print("V7.12 already installed; no files changed.")
            return
        raise ValueError("V7.12 backup exists but files changed; inspect before reinstalling.")
    BACKUP.mkdir(parents=True, exist_ok=False)
    manifest = {}
    for name, data in targets.items():
        old = read_bytes(ROOT / name)
        manifest[name] = {"before_hash": digest(old) if old is not None else None,
                          "after_hash": digest(data)}
        if old is not None:
            (BACKUP / name).write_bytes(old)
    MANIFEST.write_text(json.dumps({"saved_at": datetime.now(timezone.utc).isoformat(),
                                    "files": manifest}, indent=2), encoding="utf-8")
    try:
        for name, data in targets.items():
            (ROOT / name).write_bytes(data)
    except Exception:
        for name, details in manifest.items():
            if details["before_hash"] is None:
                (ROOT / name).unlink(missing_ok=True)
            else:
                (ROOT / name).write_bytes((BACKUP / name).read_bytes())
        shutil.rmtree(BACKUP)
        raise
    print("V7.12 installed locally. Run tests, then Supabase SQL, then review Git changes.")

def rollback():
    if not MANIFEST.is_file():
        raise ValueError("No V7.12 installation backup found.")
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    for name, detail in entries.items():
        current = read_bytes(ROOT / name)
        if current is None or digest(current) != detail["after_hash"]:
            raise ValueError(f"{name} changed since V7.12; stopping to protect current edits.")
    for name, detail in entries.items():
        if detail["before_hash"] is None:
            (ROOT / name).unlink()
        else:
            (ROOT / name).write_bytes((BACKUP / name).read_bytes())
    shutil.rmtree(BACKUP)
    print("V7.12 source files rolled back. Any Supabase SQL data remains untouched.")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--rollback", action="store_true")
    args = parser.parse_args()
    try:
        if args.rollback:
            rollback()
        else:
            install(plan(), dry_run=args.dry_run)
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"Install stopped safely: {exc}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
