"""Install or roll back the V7.10 broadcast patch safely in an existing V7.9 bot.

No network calls, no database calls, no deployment. No keys or tokens are read.
"""
import argparse
import hashlib
import json
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()
PACKAGE = Path(__file__).resolve().parent / "V710_FILES"
BACKUP = ROOT / ".v710_backups" / "initial"
MANIFEST = BACKUP / "manifest.json"
ADDED = ["broadcast_v710.py", "SQL_V7_10_BROADCAST.sql", "TEST_V7_10_BROADCAST.py", "README_V7_10.md"]
MODIFIED = ["main.py", "user_help_v79.py", ".gitignore"]
IMPORT_TEXT = "from broadcast_v710 import register_broadcast_handlers\n"
REGISTER_TEXT = "register_broadcast_handlers(bot)\n"
ALIAS_TEXT = '    ("📦 More Tools", "📢 Announcements", "/announcements", "updates subscribe unsubscribe announcements broadcast messages"),\n'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_bytes(path):
    return path.read_bytes() if path.exists() else None


def patch_source(path, edit):
    original = path.read_bytes()
    newline = "\r\n" if b"\r\n" in original else "\n"
    content = original.decode("utf-8-sig").replace("\r\n", "\n")
    modified = edit(content)
    result = modified.replace("\n", newline).encode("utf-8")
    return result


def only_once(content, marker, name):
    if content.count(marker) != 1:
        raise ValueError(f"Expected exactly one {name} marker; found {content.count(marker)}")


def main_edit(text):
    if IMPORT_TEXT.strip() in text or REGISTER_TEXT.strip() in text:
        if IMPORT_TEXT.strip() not in text or REGISTER_TEXT.strip() not in text:
            raise ValueError("Partial V7.10 integration in main.py; inspect manually")
        return text
    anchor = "from ai_ops_v60 import register_ai_ops_v60_handlers\n"
    location = "register_ui_v57_handlers(bot, show_main_menu)\n"
    only_once(text, anchor, "admin integration")
    only_once(text, location, "handler registration")
    return text.replace(anchor, anchor + IMPORT_TEXT).replace(location, REGISTER_TEXT + location)


def help_edit(text):
    if "Bot announcements:" in text:
        if ALIAS_TEXT.strip() not in text:
            raise ValueError("Partial V7.10 integration in user_help_v79.py")
        return text
    alias = "EXTRA_COMMANDS = [\n"
    return_stmt = '    return QUICK_HELP.get(language, QUICK_HELP["en"])\n'
    only_once(text, alias, "feature finder")
    only_once(text, return_stmt, "quick help")
    # Announcements are optional, avoid changing the existing menu layout.
    text = text.replace(alias, alias + ALIAS_TEXT)
    text = text.replace(return_stmt,
        '    base = QUICK_HELP.get(language, QUICK_HELP["en"])\n'
        '    return base + "\\n\\n📢 Bot announcements: /announcements · /subscribe · /unsubscribe"\n')
    return text


def ignore_edit(text):
    if ".v710_backups/" in text:
        return text
    return text.rstrip("\n") + "\n.v710_backups/\n"


def plan():
    if not (ROOT / "main.py").exists() or not (ROOT / "user_help_v79.py").exists():
        raise ValueError("Run from your V7.9 StudentAssistantBot folder (with main.py and user_help_v79.py).")
    for name in ADDED:
        if not (PACKAGE / name).is_file():
            raise ValueError(f"Missing package file: {name}")
    targets = {}
    for name, editor in (("main.py", main_edit), ("user_help_v79.py", help_edit)):
        targets[name] = patch_source(ROOT / name, editor)
    gitignore = ROOT / ".gitignore"
    if gitignore.exists():
        targets[".gitignore"] = patch_source(gitignore, ignore_edit)
    else:
        targets[".gitignore"] = b".v710_backups/\n"
    for name in ADDED:
        source = (PACKAGE / name).read_bytes()
        current = read_bytes(ROOT / name)
        if current is not None and current != source:
            raise ValueError(f"Existing {name} differs from package. Refusing overwrite.")
        targets[name] = source
    return targets


def dry_run(targets):
    for name, updated in targets.items():
        old = read_bytes(ROOT / name)
        action = "ADD" if old is None else "UNCHANGED" if old == updated else "PATCH"
        print(f"{action:9} {name}")
    print("No production or Supabase changes were made.")


def install(targets):
    if MANIFEST.exists():
        if all(read_bytes(ROOT / name) == data for name, data in targets.items()):
            print("V7.10 already installed; no files changed.")
            return
        raise ValueError("An older V7.10 backup exists and files have changed. Inspect before re-install.")
    BACKUP.mkdir(parents=True, exist_ok=False)
    snapshot = {}
    for name, updated in targets.items():
        old = read_bytes(ROOT / name)
        snapshot[name] = {"before_hash": digest(old) if old is not None else None,
                          "after_hash": digest(updated)}
        if old is not None:
            (BACKUP / name).write_bytes(old)
    (BACKUP / "manifest.json").write_text(json.dumps({
        "created": datetime.now(timezone.utc).isoformat(), "files": snapshot
    }, indent=2), encoding="utf-8")
    try:
        for name, data in targets.items():
            (ROOT / name).write_bytes(data)
    except Exception:
        for name, details in snapshot.items():
            prior = details["before_hash"]
            if prior is None:
                (ROOT / name).unlink(missing_ok=True)
            else:
                (ROOT / name).write_bytes((BACKUP / name).read_bytes())
        raise
    print("V7.10 files installed locally. Run tests and then the Supabase SQL.")
    print("No Render or GitHub deployment has been performed.")


def rollback():
    if not MANIFEST.is_file():
        raise ValueError("No V7.10 backup found. Nothing to roll back.")
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    for name, entry in entries.items():
        current = read_bytes(ROOT / name)
        if current is None or digest(current) != entry["after_hash"]:
            raise ValueError(f"{name} changed after installation. Stopping to protect edits.")
    for name, entry in entries.items():
        if entry["before_hash"] is None:
            (ROOT / name).unlink()
        else:
            (ROOT / name).write_bytes((BACKUP / name).read_bytes())
    shutil.rmtree(BACKUP)
    print("V7.10 local code rolled back. Supabase table is intentionally retained for privacy/safety.")


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--rollback", action="store_true")
    args = parser.parse_args()
    try:
        if args.rollback:
            rollback()
        else:
            targets = plan()
            if args.dry_run:
                dry_run(targets)
            else:
                install(targets)
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"Install stopped safely: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
