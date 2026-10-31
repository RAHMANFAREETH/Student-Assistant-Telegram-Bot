"""Idempotent, narrowly scoped V9.3 installer. --check previews changes.

Patches only known anchors in main.py, adult_requests_v91.py and
v91_access_bot.py; refuses unexpected variants instead of guessing.
"""
from __future__ import annotations
import argparse
import difflib
import shutil
from datetime import datetime
from pathlib import Path

REGISTRATION_ANCHOR = 'register_v92_admin_handlers(bot)'
REGISTRATION = '''\n\n# V9.3 reliability diagnostics, before legacy stateful handlers.\nfrom v93_reliability_bot import register_v93_reliability_handlers\nregister_v93_reliability_handlers(bot)'''
RPC_ANCHOR = '    uid = _id(uid)\n    from study_access_v9 import is_verified_adult\n'
RPC_INSERTION = '''    uid = _id(uid)
    # V9.3: use a single atomic database operation only after its SQL is installed.
    if os.getenv('V93_REQUEST_RPC_ENABLED', '').strip().lower() in ('true', '1', 'yes'):
        result = (db or _db()).rpc('v93_submit_adult_request', {'p_user_id': uid}).execute().data
        if result not in ('created', 'pending', 'verified', 'cooldown'):
            raise AccessError('Unexpected adult access request result.')
        return result
    from study_access_v9 import is_verified_adult
'''
OLD_APPROVAL_ERROR = '''        except (AccessError, ValueError):
            send(m.chat.id, '❌ Invalid request, review confirmation, or expiry (1–365 days).')
'''
NEW_APPROVAL_ERROR = '''        except AccessError as exc:
            send(m.chat.id, '❌ Invalid request: ' + str(exc)[:200])
        except ValueError:
            send(m.chat.id, '❌ Invalid Telegram ID or expiry days (1–365).')
'''
FILES = ('main.py', 'adult_requests_v91.py', 'v91_access_bot.py')
DEPENDENCIES = ('v92_admin_bot.py', 'v93_reliability_bot.py',
                'SQL_V93_ATOMIC_REQUESTS.sql', 'TEST_V93_RELIABILITY.py')


def replace_once(text, old, new, filename):
    if new in text:
        return text
    if text.count(old) != 1:
        raise ValueError(f'{filename}: missing or ambiguous integration anchor; stop and inspect manually')
    return text.replace(old, new, 1)


def edit_main(text):
    return replace_once(text, REGISTRATION_ANCHOR,
                        REGISTRATION_ANCHOR + REGISTRATION, 'main.py')


def edit_requests(text):
    # Anchor uniquely identifies create_request, not request_status.
    start = text.index('def create_request(') if 'def create_request(' in text else -1
    if start < 0:
        raise ValueError('adult_requests_v91.py: create_request() not found')
    end = text.find('\ndef ', start + 4)
    if end < 0:
        end = len(text)
    section = text[start:end]
    changed = replace_once(section, RPC_ANCHOR, RPC_INSERTION, 'adult_requests_v91.py')
    return text[:start] + changed + text[end:]


def edit_v91_bot(text):
    return replace_once(text, OLD_APPROVAL_ERROR, NEW_APPROVAL_ERROR, 'v91_access_bot.py')


def changes(root):
    for name in FILES + DEPENDENCIES:
        if not (root / name).is_file():
            raise FileNotFoundError('Missing required file: ' + name)
    edits = {}
    for name, fn in zip(FILES, (edit_main, edit_requests, edit_v91_bot)):
        original = (root / name).read_text(encoding='utf-8')
        result = fn(original)
        if original != result:
            edits[name] = (original, result)
    return edits


def run(root: Path, apply=False):
    edits = changes(root)
    if not edits:
        print('V9.3 already integrated; no files changed.')
        return
    for name, (before, after) in edits.items():
        print(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                         fromfile=name + ':current', tofile=name + ':planned')))
    if not apply:
        print('CHECK OK. No files changed.')
        return
    backup = root / ('V93_BACKUP_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    for name in edits:
        shutil.copy2(root / name, backup / name)
    try:
        for name, (_, after) in edits.items():
            (root / name).write_text(after, encoding='utf-8', newline='\n')
    except Exception:
        for name in edits:
            shutil.copy2(backup / name, root / name)
        raise
    print('V9.3 integrated. Original files backed up to:', backup)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check', action='store_true')
    modes.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    run(Path(__file__).resolve().parent, apply=args.apply)
