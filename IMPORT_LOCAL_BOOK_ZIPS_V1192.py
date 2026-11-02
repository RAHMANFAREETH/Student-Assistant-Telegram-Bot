"""Local large-ZIP to Student Assistant Bot Smart Bulk importer.

Extracts each supported document on *your own computer* and uploads it as
an individual document using an authorized Telegram *user* account. It avoids
the hosted Bot API 20 MB getFile restriction and does not alter the production
bot, its server, or its safety checks.

This tool has NO total ZIP archive size cap and NO per-session file count cap;
Telegram, local disk, ZIP safety checks, and rights requirements still apply.
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import time
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path

ALLOWED = frozenset({'.pdf', '.epub', '.docx', '.txt'})
RIGHTS = frozenset({'permission', 'public_domain', 'cc0', 'cc_by', 'cc_by_sa'})
# The Telegram *user account* upload limit is 2 GB normally or 4 GB Premium.
# This is not a bot application restriction; larger members cannot be sent.
TELEGRAM_PREMIUM_MAX_BYTES = 4 * 1024**3
HIGH_RATIO = 1000  # refuse likely ZIP bombs; zero-byte members excluded
BUFFER = 1024 * 1024


def data_dir() -> Path:
    root = (Path(os.environ['LOCALAPPDATA']) if os.name == 'nt' and
            os.environ.get('LOCALAPPDATA') else Path.home() / '.local' / 'share')
    return root / 'StudentAssistantBot' / 'zip-bulk-import'


def _ensure_private_dir(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    if os.name != 'nt':
        os.chmod(d, 0o700)


def archives_from_source(source: str) -> list[Path]:
    path = Path(source).expanduser().resolve()
    if path.is_file() and path.suffix.lower() == '.zip':
        return [path]
    if path.is_dir():
        return sorted((x for x in path.iterdir() if x.is_file() and
                       x.suffix.lower() == '.zip'), key=lambda x: x.name.lower())
    raise ValueError('Provide an existing .zip file or folder containing ZIP files.')


def safe_member_name(info: zipfile.ZipInfo) -> str | None:
    """Never trust paths from archives. Always extract a single member to a private temp dir."""
    if info.is_dir() or (info.flag_bits & 1):
        return None
    raw = str(info.filename).replace('\\', '/')
    segments = raw.split('/')
    if not raw or raw.startswith('/') or any(x in ('..', '') for x in segments):
        return None
    if ':' in segments[0] or any(c in raw for c in '\x00\r\n'):
        return None
    mode = (info.external_attr >> 16) & 0xFFFF
    if stat.S_IFMT(mode) in (stat.S_IFLNK, stat.S_IFCHR, stat.S_IFBLK,
                             stat.S_IFIFO, stat.S_IFSOCK):
        return None
    name = unicodedata.normalize('NFC', segments[-1]).strip(' .')
    if not name or any(ord(c) < 32 for c in name):
        return None
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED:
        return None
    stem = Path(name).stem.strip()
    if not stem:
        return None
    # Keep Unicode, but limit filename component lengths for Windows/Telegram.
    stem = stem[:130].rstrip(' .')
    return stem + ext


def safety_reason(info: zipfile.ZipInfo, *, free_bytes: int | None = None,
                  reserve_bytes: int = 256 * 1024**2) -> str | None:
    if info.file_size < 0 or info.compress_size < 0:
        return 'invalid ZIP metadata'
    if info.file_size > TELEGRAM_PREMIUM_MAX_BYTES:
        return 'over Telegram Premium 4 GB single-file upload ceiling'
    if info.file_size and (info.file_size / max(info.compress_size, 1)) > HIGH_RATIO:
        return 'suspicious decompression ratio (ZIP-bomb protection)'
    if free_bytes is not None and free_bytes < info.file_size + reserve_bytes:
        return 'insufficient local free disk space'
    return None


@dataclass(frozen=True)
class Candidate:
    index: int
    info: zipfile.ZipInfo
    filename: str


def candidates(zip_obj: zipfile.ZipFile):
    for idx, info in enumerate(zip_obj.infolist()):
        name = safe_member_name(info)
        if name:
            yield Candidate(idx, info, name)


def extract_one(z: zipfile.ZipFile, cand: Candidate, temp: Path) -> Path:
    """Stream one member to disk; ZIP path is NEVER used as an extraction path."""
    dest = temp / cand.filename
    if dest.exists():
        raise FileExistsError('Destination exists in private temp directory.')
    count = 0
    with z.open(cand.info) as src, dest.open('xb') as out:
        while True:
            chunk = src.read(BUFFER)
            if not chunk:
                break
            count += len(chunk)
            if count > cand.info.file_size or count > TELEGRAM_PREMIUM_MAX_BYTES:
                raise ValueError('ZIP member expanded beyond declared size.')
            out.write(chunk)
    if count != cand.info.file_size:
        raise ValueError('ZIP size mismatch; archive may be corrupt.')
    return dest


def fingerprint(path: Path) -> str:
    st = path.stat()
    return hashlib.sha256(f'{str(path).casefold()}|{st.st_size}|{st.st_mtime_ns}'.encode()).hexdigest()[:24]


def checkpoint_file(path: Path, root: Path) -> Path:
    return root / f'archive-{fingerprint(path)}.json'


def read_checkpoint(path: Path) -> int:
    if not path.exists():
        return -1
    obj = json.loads(path.read_text(encoding='utf8'))
    idx = obj.get('last_sent_entry', -1)
    if type(idx) is not int or idx < -1:
        raise ValueError('Invalid checkpoint; do not continue automatically.')
    return idx


def write_checkpoint(path: Path, idx: int) -> None:
    _ensure_private_dir(path.parent)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps({'last_sent_entry': idx,
                                'note': 'Sent to Telegram, NOT guaranteed published by the bot.'}) + '\n', encoding='utf8')
    if os.name != 'nt':
        os.chmod(temp, 0o600)
    os.replace(temp, path)


def validate_metadata(args) -> None:
    if args.rights not in RIGHTS:
        raise ValueError('Choose a valid distribution rights code.')
    for label, value, max_len in [('Language', args.language, 40),
                                 ('Category', args.category, 70),
                                 ('Author', args.author, 120),
                                 ('Rights explanation', args.rights_note, 700)]:
        if (not value or len(value.strip()) < 2 or len(value) > max_len or
                any(c in value for c in '|\r\n')):
            raise ValueError(f'{label} must be 2-{max_len} characters without | or newlines.')


def read_credentials() -> tuple[int, str]:
    raw_id = os.getenv('TG_API_ID', '').strip() or input('Telegram API ID (my.telegram.org): ').strip()
    key = os.getenv('TG_API_HASH', '').strip() or getpass.getpass('Telegram API hash (hidden): ').strip()
    if (not raw_id.isdecimal() or int(raw_id) < 1 or len(key) != 32 or
            any(c not in 'abcdefABCDEF0123456789' for c in key)):
        raise ValueError('Invalid API ID or hash; obtain them at my.telegram.org.')
    return int(raw_id), key


def args_parser():
    p = argparse.ArgumentParser(description='Import any-sized LOCAL ZIP archive into Student Assistant Smart Bulk by uploading each book individually via your Telegram USER account.')
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true', help='Preview ZIP contents offline; no Telegram login.')
    mode.add_argument('--apply', action='store_true', help='Start /mediabulk and upload documents to the bot.')
    p.add_argument('--source', required=True, help='Path to a .zip file, or folder of ZIP files.')
    p.add_argument('--bot', default='@Student_Sl_Assistant_bot', help='Your exact bot username.')
    p.add_argument('--language', default='Sinhala')
    p.add_argument('--category', default='Education')
    p.add_argument('--author', default='Unknown')
    p.add_argument('--rights', choices=sorted(RIGHTS), help='Verified license or distribution permission for ALL books')
    p.add_argument('--rights-note', help='Accurate source/license statement for every document')
    p.add_argument('--delay', type=float, default=2.0, help='Seconds between uploads (minimum 1)')
    p.add_argument('--reset-checkpoint', action='store_true', help='Restart all entries; may cause duplicate uploads')
    p.add_argument('--minimum-free-mb', type=int, default=256, help='Reserve local disk space for safety')
    return p


def preview_archive(path: Path, *, after: int = -1, reserve_bytes: int = 256*1024**2):
    found = 0
    skipped = 0
    total_bytes = 0
    with zipfile.ZipFile(path) as z:
        for cand in candidates(z):
            if cand.index <= after:
                continue
            reason = safety_reason(cand.info, reserve_bytes=reserve_bytes)
            if reason:
                print(f'  SKIP: {cand.filename[:70]} ({reason})')
                skipped += 1
                continue
            if found < 25:
                print(f'  {cand.filename[:90]} — {cand.info.file_size / 1024**2:,.1f} MB')
            found += 1
            total_bytes += cand.info.file_size
    print(f'  Eligible documents: {found}; unsafe/oversize skipped: {skipped}; total expanded: {total_bytes / 1024**3:.2f} GB')
    if found > 25:
        print('  (Showing only first 25 document names)')
    return found


async def _wait_ack(client, bot, after_id: int, phrase: str, timeout=40):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        msgs = await client.get_messages(bot, limit=15)
        for m in msgs:
            if m.id > after_id and not m.out and phrase.casefold() in (getattr(m, 'message', '') or '').casefold():
                return True
        await asyncio.sleep(1.5)
    return False


async def _send_archive(client, dest, zippath: Path, args, root: Path) -> tuple[int, int]:
    from telethon.errors import FloodWaitError, RPCError
    cp = checkpoint_file(zippath, root)
    last = -1 if args.reset_checkpoint else read_checkpoint(cp)
    sent = 0
    skipped = 0
    with zipfile.ZipFile(zippath) as z:
        for cand in candidates(z):
            if cand.index <= last:
                continue
            reason = safety_reason(cand.info, reserve_bytes=args.minimum_free_mb * 1024**2)
            if reason:
                print(f'  SKIP {cand.filename[:65]}: {reason}')
                skipped += 1
                continue
            # A separate TemporaryDirectory per file minimizes disk use and
            # guarantees cleanup, including when extraction/Telegram fails.
            with tempfile.TemporaryDirectory(prefix='student-book-import-') as folder:
                target_dir = Path(folder)
                free = shutil.disk_usage(target_dir).free
                reason = safety_reason(cand.info, free_bytes=free,
                                       reserve_bytes=args.minimum_free_mb * 1024**2)
                if reason:
                    print(f'  STOP: {cand.filename[:65]}: {reason}. Retry after freeing disk space.')
                    return sent, skipped + 1
                try:
                    source = extract_one(z, cand, target_dir)
                except (OSError, zipfile.BadZipFile, RuntimeError, ValueError) as exc:
                    print(f'  STOP extraction #{cand.index} ({cand.filename[:65]}): {type(exc).__name__}.')
                    return sent, skipped + 1
                try:
                    # send_file uploads bytes as a document using the admin
                    # account's Telegram MTProto session. No ZIP is given to bot.
                    await client.send_file(dest, str(source), force_document=True)
                except FloodWaitError as exc:
                    print(f'  Telegram rate limit: pause {exc.seconds} s, then rerun to resume.')
                    return sent, skipped
                except (RPCError, OSError, ValueError) as exc:
                    print(f'  STOP sending #{cand.index} ({cand.filename[:65]}): {type(exc).__name__}.')
                    return sent, skipped + 1
            write_checkpoint(cp, cand.index)
            sent += 1
            print(f'  Sent {sent}: {cand.filename[:95]}')
            if args.delay:
                await asyncio.sleep(args.delay)
    return sent, skipped


async def run_apply(args, zips: list[Path]):
    from telethon import TelegramClient
    from telethon.errors import RPCError
    validate_metadata(args)
    if args.delay < 1:
        raise ValueError('--delay must be at least 1 second.')
    root = data_dir()
    _ensure_private_dir(root)
    ident, secret = read_credentials()
    session = root / 'telegram-user'
    client = TelegramClient(str(session), ident, secret)
    try:
        await client.start()
        me = await client.get_me()
        if not me or getattr(me, 'bot', False):
            raise ValueError('Use your authorized Telegram ADMIN user account, not a bot login.')
        dest = await client.get_entity(args.bot)
        if not getattr(dest, 'bot', False):
            raise ValueError('Destination is not a bot. Refusing to send.')
        print(f'\nDestination: @{dest.username} (ID {dest.id})')
        print(f'ZIP archives: {len(zips)}; each eligible book uploaded individually. No ZIP sent.')
        print('You must have legal permission to redistribute EVERY book in this batch.')
        if input('Type IMPORT to confirm bot and verified rights: ').strip() != 'IMPORT':
            print('Canceled: no files uploaded.')
            return
        start = await client.send_message(dest, '/mediabulk')
        if not await _wait_ack(client, dest, start.id, 'SMART BULK UPLOAD'):
            raise RuntimeError('Bot did not acknowledge /mediabulk. Check admin access and deployment.')
        setmsg = await client.send_message(dest,
                  f'/mediabulkset {args.language} | {args.category} | {args.rights} | {args.author} | {args.rights_note}')
        if not await _wait_ack(client, dest, setmsg.id, 'Shared metadata saved'):
            raise RuntimeError('Bot did not confirm shared metadata. No documents uploaded.')
        all_sent = all_skipped = 0
        for idx, zippath in enumerate(zips, 1):
            print(f'\n[{idx}/{len(zips)}] {zippath.name}')
            a,b = await _send_archive(client, dest, zippath, args, root)
            all_sent += a
            all_skipped += b
        try:
            await client.send_message(dest, '/mediabulkstatus')
        except RPCError:
            print('Could not request bot status automatically; check your bot chat.')
        print(f'\nTelegram uploads sent: {all_sent}; skipped/errors: {all_skipped}.')
        print('Review /mediabulkstatus. Sent ≠ Published. When finished, YOU send /mediabulkdone.')
        print(f'Checkpoints are stored privately at: {root}')
    finally:
        await client.disconnect()


def main(argv=None) -> int:
    args = args_parser().parse_args(argv)
    if args.minimum_free_mb < 256:
        print('ERROR: --minimum-free-mb must be >=256 for local disk safety.', file=sys.stderr)
        return 2
    try:
        zips = archives_from_source(args.source)
        if not zips:
            raise ValueError('No ZIP archives found in that folder.')
        if args.dry_run:
            print('PREVIEW ONLY — no Telegram login or uploads.')
            print('There is no fixed ZIP archive size cap. Telegram user upload/disk/security checks remain.')
            for idx, f in enumerate(zips, 1):
                print(f'\n[{idx}/{len(zips)}] {f.name} ({f.stat().st_size / 1024**2:,.1f} MB)')
                cp = checkpoint_file(f, data_dir())
                preview_archive(f, after=-1 if args.reset_checkpoint else read_checkpoint(cp),
                                reserve_bytes=args.minimum_free_mb * 1024**2)
        else:
            asyncio.run(run_apply(args, zips))
        return 0
    except (ValueError, RuntimeError, OSError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\nInterrupted. You can rerun to resume from the last Telegram send checkpoint.')
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
