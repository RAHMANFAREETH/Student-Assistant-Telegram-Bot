"""V11.9.2.1 local Telegram ZIP importer; keeps the existing <=20MB bot ZIP flow unchanged.

Run on an ADMINISTRATOR'S laptop using a locally authenticated Telegram USER
account. From a Telegram message URL, it downloads an accessible, unprotected
ZIP to local disk and delegates safe extraction and individual document sending
to IMPORT_LOCAL_BOOK_ZIPS_V1192. Large ZIP bytes NEVER touch Render.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import zipfile
from urllib.parse import urlparse

import IMPORT_LOCAL_BOOK_ZIPS_V1192 as local

MIN_FREE = 256 * 1024**2


def parse_message_link(url: str) -> tuple[str | int, int]:
    """Return channel username or -100... ID, message ID. Does not join chats."""
    u = urlparse(str(url).strip())
    if u.scheme not in ('http', 'https') or (u.hostname or '').lower() not in ('t.me', 'telegram.me', 'www.t.me'):
        raise ValueError('Use a Telegram message URL, such as https://t.me/c/123456789/15.')
    seg = [s for s in u.path.split('/') if s]
    if len(seg) == 3 and seg[0] == 's':
        seg = seg[1:]
    if len(seg) == 3 and seg[0] == 'c':
        raw, post = seg[1], seg[2]
        if (not raw.isdecimal() or int(raw) <= 0 or not post.isdecimal() or int(post) <= 0):
            raise ValueError('Invalid private channel message link.')
        return -int('100' + raw), int(post)
    if len(seg) == 2:
        name, post = seg
        if (not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{3,31}', name) or
                not post.isdecimal() or int(post) <= 0):
            raise ValueError('Unsupported Telegram public message link.')
        return name, int(post)
    raise ValueError('Specify a direct channel/group message link, not a channel invite or topic.')


def source_links(args) -> list[str]:
    out = list(args.link or [])
    if args.links_file:
        f = Path(args.links_file).expanduser()
        if not f.is_file():
            raise ValueError('The --links-file path does not exist.')
        out += [line.strip() for line in f.read_text(encoding='utf-8-sig').splitlines()
                if line.strip() and not line.lstrip().startswith('#')]
    dedup = list(dict.fromkeys(out))
    if not dedup:
        raise ValueError('Provide --link or --links-file with at least one Telegram message URL.')
    for link in dedup:
        parse_message_link(link)
    return dedup


def safe_name_and_size(msg) -> tuple[str, int]:
    doc = getattr(msg, 'document', None)
    if doc is None:
        raise ValueError('Selected Telegram message is not a document.')
    size = int(getattr(getattr(msg, 'file', None), 'size', 0) or getattr(doc, 'size', 0) or 0)
    name = str(getattr(getattr(msg, 'file', None), 'name', '') or '')
    if not name:
        for attr in getattr(doc, 'attributes', ()):
            if getattr(attr, 'file_name', None):
                name = str(attr.file_name)
                break
    if not name.lower().endswith('.zip') or size <= 0:
        raise ValueError('The selected message must contain a named .zip document with a valid size.')
    return name, size


def is_protected(chat, msg) -> bool:
    return bool(getattr(chat, 'noforwards', False) or getattr(msg, 'noforwards', False) or
                getattr(chat, 'has_protected_content', False))


async def get_source(client, link: str):
    peer, post = parse_message_link(link)
    if isinstance(peer, int):
        # Private /c/ links require existing membership. Do not attempt to join
        # channels or bypass membership / content-protection restrictions.
        entity = None
        async for dialog in client.iter_dialogs():
            if getattr(dialog.entity, 'id', None) == int(str(abs(peer))[3:]):
                entity = dialog.entity
                break
        if entity is None:
            raise ValueError('Private source channel/group not found among your accessible Telegram chats.')
    else:
        entity = await client.get_entity(peer)
    msg = await client.get_messages(entity, ids=post)
    if not msg:
        raise ValueError('Message unavailable to this Telegram account.')
    if is_protected(entity, msg):
        raise ValueError('Source protects message content. This importer will not bypass it.')
    name, size = safe_name_and_size(msg)
    return entity, msg, name, size


def local_zip_path(link: str, cache: Path) -> Path:
    digest = hashlib.sha256(link.encode('utf-8')).hexdigest()[:24]
    return cache / f'telegram-{digest}.zip'


def ensure_free_space(dest: Path, bytes_needed: int, reserve: int = MIN_FREE):
    local._ensure_private_dir(dest)
    available = shutil.disk_usage(dest).free
    if available < bytes_needed + reserve:
        raise ValueError(f'Not enough free disk space: need at least {(bytes_needed+reserve)/1024**3:.2f} GB.')


async def fetch_zip(client, msg, link: str, size: int, cache: Path) -> Path:
    """Save verified archive persistently so previous-file checkpoints remain valid."""
    path = local_zip_path(link, cache)
    local._ensure_private_dir(cache)
    if path.is_file() and path.stat().st_size == size and zipfile.is_zipfile(path):
        print(f'Reusing previously downloaded ZIP: {path}')
        return path
    if path.exists():
        path.unlink()
    ensure_free_space(cache, size)
    # Partial files are never passed to the extractor. A subsequent run retries.
    partial = path.with_suffix('.partial')
    if partial.exists():
        partial.unlink()
    try:
        result = await client.download_media(msg, file=str(partial))
        if not result or Path(result).resolve() != partial.resolve():
            raise RuntimeError('Telegram download returned a different path; refusing to process it.')
        if not partial.is_file() or partial.stat().st_size != size:
            raise ValueError('Downloaded size differs from Telegram metadata.')
        if not zipfile.is_zipfile(partial):
            raise ValueError('Downloaded file is not a valid ZIP archive.')
        os.replace(partial, path)
    finally:
        if partial.exists():
            partial.unlink()
    return path


def parser():
    p = argparse.ArgumentParser(description='Import accessible, unprotected Telegram ZIP messages into Smart Bulk via your Windows laptop. No changes to the old <=20MB bot ZIP handler.')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--dry-run', action='store_true', help='Inspect Telegram file names and sizes; no downloads or bot uploads.')
    g.add_argument('--apply', action='store_true', help='Automatically download ZIP locally, extract safe books, and upload to Smart Bulk.')
    p.add_argument('--link', action='append', help='Direct Telegram ZIP message link (repeatable).')
    p.add_argument('--links-file', help='Text file with one Telegram ZIP message link per line.')
    p.add_argument('--bot', default='@Student_Sl_Assistant_bot')
    p.add_argument('--language', default='Sinhala')
    p.add_argument('--category', default='Education')
    p.add_argument('--author', default='Unknown')
    p.add_argument('--rights', choices=sorted(local.RIGHTS))
    p.add_argument('--rights-note')
    p.add_argument('--delay', type=float, default=2.0)
    p.add_argument('--minimum-free-mb', type=int, default=256)
    p.add_argument('--reset-checkpoint', action='store_true', help='Resend every book; beware duplicates.')
    return p


async def run(args):
    from telethon import TelegramClient
    links = source_links(args)
    if args.minimum_free_mb < 256 or args.delay < 1:
        raise ValueError('--minimum-free-mb must be >=256 and --delay >=1.')
    if args.apply:
        local.validate_metadata(args)
    root = local.data_dir()  # OS-local; never in GitHub or Render
    local._ensure_private_dir(root)
    cache = root / 'telegram-zips'
    aid, ahash = local.read_credentials()
    client = TelegramClient(str(root / 'telegram-user'), aid, ahash)
    try:
        await client.start()
        me = await client.get_me()
        if not me or getattr(me, 'bot', False):
            raise ValueError('Login using your authorized Telegram ADMIN user account, not a bot.')
        docs = []
        for link in links:
            entity, msg, name, size = await get_source(client, link)
            print(f'ZIP: {name} — {size/1024**2:,.1f} MB | message #{msg.id} | source {getattr(entity, "title", getattr(entity, "username", "chat"))}')
            docs.append((link, msg, name, size))
        if args.dry_run:
            print('\nPREVIEW ONLY: No ZIP data was downloaded and nothing was sent to the bot.')
            print('Run --apply with verified redistribution rights to import the documents inside each ZIP.')
            return
        bot = await client.get_entity(args.bot)
        if not getattr(bot, 'bot', False):
            raise ValueError('Destination is not a Telegram bot.')
        print(f'\nDestination: @{bot.username}; ZIPs: {len(docs)}')
        print('Telegram ZIP files will be downloaded to your LAPTOP, not to Render.')
        print(f'Local downloads and resume checkpoints: {cache}')
        print('Confirm you have redistribution permission for ALL included editions.')
        if input('Type IMPORT to confirm source, bot, and rights: ').strip() != 'IMPORT':
            print('Canceled. No ZIP files downloaded or uploaded.')
            return
        started = await client.send_message(bot, '/mediabulk')
        if not await local._wait_ack(client, bot, started.id, 'SMART BULK UPLOAD'):
            raise RuntimeError('Bot did not acknowledge /mediabulk; check admin access and feature flag.')
        configured = await client.send_message(bot, f'/mediabulkset {args.language} | {args.category} | {args.rights} | {args.author} | {args.rights_note}')
        if not await local._wait_ack(client, bot, configured.id, 'Shared metadata saved'):
            raise RuntimeError('Bot did not save batch metadata. No ZIP downloaded.')
        total_sent = total_skip = 0
        for idx, (link, msg, name, size) in enumerate(docs, 1):
            print(f'\n[{idx}/{len(docs)}] Downloading {name} to laptop...')
            path = await fetch_zip(client, msg, link, size, cache)
            print(f'Local ZIP ready: {path} ({path.stat().st_size/1024**2:,.1f} MB)')
            local.preview_archive(path, after=(-1 if args.reset_checkpoint else local.read_checkpoint(local.checkpoint_file(path, root))), reserve_bytes=args.minimum_free_mb*1024**2)
            sent, skipped = await local._send_archive(client, bot, path, args, root)
            total_sent += sent
            total_skip += skipped
        await client.send_message(bot, '/mediabulkstatus')
        print(f'\nTelegram book documents SENT: {total_sent}; ZIP entries skipped/errors: {total_skip}.')
        print('SENT is not the same as PUBLISHED. Verify the bot counts and manually send /mediabulkdone.')
        print(f'ZIP downloads remain locally for resume: {cache}')
    finally:
        await client.disconnect()


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        asyncio.run(run(args))
        return 0
    except (ValueError, RuntimeError, OSError, zipfile.BadZipFile) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('Interrupted. Rerun with the same link to resume the previous archive checkpoint.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
