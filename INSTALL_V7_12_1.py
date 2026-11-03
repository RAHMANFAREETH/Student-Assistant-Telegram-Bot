"""V7.12.1 safely removes the /unsubscribe Telegram command.

Preserves legacy opt-outs and offers /announcements off instead.
Supports installed V7.10 or V7.12; refuses unexpected source edits.
Usage: python INSTALL_V7_12_1.py --dry-run | --rollback
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
FILES = Path(__file__).resolve().parent / 'V7121_FILES'
BACKUP = ROOT / '.v7121_backup'
MANIFEST = BACKUP / 'manifest.json'


def normalized(raw: bytes) -> str:
    return raw.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def existing(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


def replace_once(s: str, old: str, new: str, label: str) -> str:
    if s.count(old) != 1:
        raise ValueError(f'Unexpected {label} structure. No source files changed.')
    return s.replace(old, new, 1)


def patch_broadcast(s: str) -> str:
    if '# V7.12.1 preference routing' in s:
        if '@bot.message_handler(commands=["unsubscribe"])' in s:
            raise ValueError('Partial V7.12.1 patch detected.')
        return s
    # Keep subscription(False) for preference choice and blocked accounts.
    s = replace_once(s,
        '    @bot.message_handler(commands=["unsubscribe"])\n'
        '    def unsubscribe(message):\n'
        '        service.subscription(message, False)\n\n',
        '', 'legacy /unsubscribe registration')
    old = '''    def announcements(self, message):
        if not is_private(message):
            self.bot.send_message(message.chat.id, "📢 Use /announcements in a private chat with the bot.")
            return
        try:
            enabled = self._is_subscribed(int(message.from_user.id))
        except Exception:
            self.bot.send_message(message.chat.id,
                "⚠️ Announcement preferences are unavailable. Ask the admin to check Supabase setup.")
            return
        self.bot.send_message(message.chat.id,
            ("📢 Announcements are ON. Send /unsubscribe to stop them."
             if enabled else "📢 Announcements are OFF. Send /subscribe to receive updates."))
'''
    new = '''    def announcements(self, message):
        # V7.12.1 preference routing: /announcements on|off, no /unsubscribe handler.
        if not is_private(message):
            self.bot.send_message(message.chat.id,
                "📢 Manage announcements in your private chat with the bot.")
            return
        parts = (getattr(message, "text", "") or "").strip().split(maxsplit=1)
        action = parts[1].strip().lower() if len(parts) > 1 else ""
        if action in ("on", "off"):
            self.subscription(message, action == "on")
            return
        if action:
            self.bot.send_message(message.chat.id,
                "📢 Use /announcements, /announcements on, or /announcements off.")
            return
        try:
            rows = (self.db.table(TABLE).select("subscribed")
                    .eq("user_id", int(message.from_user.id))
                    .limit(1).execute()).data or []
        except Exception:
            self.bot.send_message(message.chat.id,
                "⚠️ Announcement preferences are unavailable. Ask the admin to check Supabase setup.")
            return
        if rows and rows[0].get("subscribed") is False:
            response = "📢 Bot announcements are OFF. To resume: /announcements on."
        elif rows and rows[0].get("subscribed") is True:
            response = "📢 Bot announcements are ON. To stop: /announcements off."
        else:
            response = ("📢 No announcement preference set. Subscriber-only messages "
                        "require /subscribe. To stop other bot announcements: "
                        "/announcements off.")
        self.bot.send_message(message.chat.id, response)
'''
    s = replace_once(s, old, new, 'announcement preference method')
    s = replace_once(s,
        '"✅ You subscribed to occasional bot announcements. To stop them, send /unsubscribe."',
        '"✅ Announcements enabled. To stop: /announcements off."', 'subscribe success message')
    s = replace_once(s,
        '"✅ You unsubscribed from announcements. To rejoin, send /subscribe."',
        '"✅ Bot announcements disabled. To resume: /announcements on."', 'opt-out success message')
    # Only V7.12 contains known-user announcements.
    if 'def _make_all_preview(self, message, text):' in s:
        s = replace_once(s, '"\\n\\nTo stop future bot announcements: /unsubscribe"',
                         '"\\n\\nTo stop future bot announcements: /announcements off"', 'known-user footer')
        s = replace_once(s, 'payload = text if "/unsubscribe" in text else text + footer',
                         'payload = text if "/announcements off" in text else text + footer', 'footer duplicate check')
        s = s.replace('Announcement plus unsubscribe option', 'Announcement plus preference instructions')
        s = replace_once(s,
            '"For important bot updates only; recipients can /unsubscribe."',
            '"For important bot updates only; recipients can choose /announcements off."',
            'known-user preview instructions')
        s = s.replace('Explicit /unsubscribe, blocked users, and invalid IDs',
                      'Explicit opt-outs, blocked users, and invalid IDs')
    return s


def patch_other(filename: str, s: str) -> str:
    if filename == 'user_help_v79.py':
        return s.replace(' · /unsubscribe', ' · /announcements off')
    if filename == 'TEST_V7_10_BROADCAST.py':
        return s.replace("'subscribe', 'unsubscribe', 'announcements'",
                         "'subscribe', 'announcements'")
    if filename == 'TEST_V7_12_KNOWN_USERS.py':
        return s.replace("'broadcast','subscribe','unsubscribe','broadcastall'",
                         "'broadcast','subscribe','broadcastall'")
    if filename in ('README_V7_10.md', 'README_V7_12.md'):
        return s.replace('/unsubscribe', '/announcements off')
    raise ValueError(f'Unexpected target: {filename}')


def plan():
    base = ROOT / 'broadcast_v710.py'
    if not base.is_file():
        raise ValueError('Run from your StudentAssistantBot folder (broadcast_v710.py missing).')
    targets = {}
    names = ['broadcast_v710.py', 'user_help_v79.py', 'TEST_V7_10_BROADCAST.py',
             'TEST_V7_12_KNOWN_USERS.py', 'README_V7_10.md', 'README_V7_12.md']
    for name in names:
        path = ROOT / name
        data = existing(path)
        if data is None:
            if name == 'broadcast_v710.py':
                raise ValueError('Missing broadcast module')
            continue
        source = normalized(data)
        if name == 'broadcast_v710.py':
            changed = patch_broadcast(source)
        else:
            changed = patch_other(name, source)
        if changed == source:
            continue
        newline = '\r\n' if b'\r\n' in data else '\n'
        output = changed.replace('\n', newline).encode('utf-8')
        targets[name] = output
    for name in ('TEST_V7_12_1_ANNOUNCEMENT_PREFS.py', 'README_V7_12_1.md'):
        extra = FILES / name
        if not extra.is_file():
            raise ValueError(f'Missing V7121_FILES/{name}')
        present = existing(ROOT / name)
        if present is not None and present != extra.read_bytes():
            raise ValueError(f'Existing {name} differs: refusing overwrite.')
        if present is None:
            targets[name] = extra.read_bytes()
    return targets


def install(targets, dry_run=False):
    if not targets:
        print('V7.12.1 already present; nothing to update.')
        return
    if MANIFEST.exists():
        details = json.loads(MANIFEST.read_text(encoding='utf-8'))['files']
        if all(existing(ROOT / name) is not None and
               sha(existing(ROOT / name)) == detail['after']
               for name, detail in details.items()):
            print('V7.12.1 already installed; no files changed.')
            return
        raise ValueError('Previous V7.12.1 backup exists; current files differ. Inspect before reinstall.')
    for name in targets:
        print(('ADD ' if not (ROOT / name).exists() else 'UPDATE ') + name)
    if dry_run:
        print('Dry run passed. No files, SQL or Render modified.')
        return
    BACKUP.mkdir(parents=True, exist_ok=False)
    manifest = {}
    for name, after in targets.items():
        before = existing(ROOT / name)
        manifest[name] = {'before': sha(before) if before is not None else None,
                          'after': sha(after)}
        if before is not None:
            (BACKUP / name).write_bytes(before)
    MANIFEST.write_text(json.dumps({'date': datetime.now(timezone.utc).isoformat(),
                                    'files': manifest}, indent=2), encoding='utf-8')
    try:
        for name, after in targets.items():
            (ROOT / name).write_bytes(after)
    except Exception:
        for name, info in manifest.items():
            dest = ROOT / name
            if info['before'] is None:
                dest.unlink(missing_ok=True)
            else:
                dest.write_bytes((BACKUP / name).read_bytes())
        shutil.rmtree(BACKUP)
        raise
    print('V7.12.1 installed locally. Run tests, review Git changes, then deploy.')


def rollback():
    if not MANIFEST.exists():
        raise ValueError('No V7.12.1 backup found.')
    files = json.loads(MANIFEST.read_text(encoding='utf-8'))['files']
    for name, hashes in files.items():
        data = existing(ROOT / name)
        if data is None or sha(data) != hashes['after']:
            raise ValueError(f'{name} changed since patch. Refusing rollback.')
    for name, hashes in files.items():
        if hashes['before'] is None:
            (ROOT / name).unlink()
        else:
            (ROOT / name).write_bytes((BACKUP / name).read_bytes())
    shutil.rmtree(BACKUP)
    print('V7.12.1 source changes rolled back. Existing Supabase preferences untouched.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--dry-run', action='store_true')
    group.add_argument('--rollback', action='store_true')
    args = parser.parse_args()
    try:
        if args.rollback:
            rollback()
        else:
            install(plan(), dry_run=args.dry_run)
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        print('Stopped safely:', exc, file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
