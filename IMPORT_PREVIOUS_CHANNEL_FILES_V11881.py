"""V11.8.8.1: locally forward historical documents from your own Telegram channel.

Uses your Telegram *user* session and MTProto for history, not the Bot API.
Does not download, read, decrypt, extract, or bypass forwarding protection.
The bot's existing V11.8.8 smart bulk / Supabase workflow does cataloguing.

Credentials and session remain on the local computer, OUTSIDE the bot repo.
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import hashlib
import json
import os
import sys
import time
from pathlib import Path

SUPPORTED_EXTENSIONS = frozenset({'.pdf', '.epub', '.docx', '.txt'})
MAX_BULK_FILES = 100  # V11.8.8 server-side cap
RIGHTS = frozenset({'permission', 'public_domain', 'cc0', 'cc_by', 'cc_by_sa'})


def local_data_dir() -> Path:
    """Keep Telegram login session OUTSIDE source folders / cloud deployment."""
    base = os.environ.get('LOCALAPPDATA') if os.name == 'nt' else None
    root = Path(base) if base else Path.home() / '.local' / 'share'
    return root / 'StudentAssistantBot' / 'previous-channel-import'


def supported_name(message, extensions=SUPPORTED_EXTENSIONS) -> str | None:
    """Only original Telegram *documents* with known file names and extensions."""
    document = getattr(message, 'document', None)
    if not document:
        return None
    for attr in getattr(document, 'attributes', []) or []:
        name = getattr(attr, 'file_name', None)
        if name and Path(str(name)).suffix.lower() in extensions:
            return str(name)
    return None


def allowed_source(source) -> bool:
    """Require channel creator/admin status; never import arbitrary third-party feeds."""
    return bool(getattr(source, 'broadcast', False) and
                (getattr(source, 'creator', False) or getattr(source, 'admin_rights', None)))


def protected(source, message=None) -> bool:
    return bool(getattr(source, 'noforwards', False) or
                (message is not None and getattr(message, 'noforwards', False)))


def validate_metadata(language: str, category: str, author: str,
                      rights: str, rights_note: str) -> None:
    if rights not in RIGHTS:
        raise ValueError('Invalid rights code.')
    for label, value, maxlen in (
        ('Language', language, 40), ('Category', category, 70),
        ('Author', author, 120), ('Rights note', rights_note, 700),
    ):
        if not value or len(value.strip()) < 2 or len(value) > maxlen or '|' in value or '\n' in value or '\r' in value:
            raise ValueError(f'{label} must be 2-{maxlen} characters and cannot contain | or newlines.')


def checkpoint_path(source_id: int, bot_id: int, root: Path | None = None) -> Path:
    root = root or local_data_dir()
    digest = hashlib.sha256(f'{source_id}:{bot_id}'.encode()).hexdigest()[:16]
    return root / f'checkpoint-{digest}.json'


def read_checkpoint(path: Path, source_id: int, bot_id: int) -> int:
    if not path.is_file():
        return 0
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('source_id') != source_id or data.get('bot_id') != bot_id:
        raise ValueError('Checkpoint belongs to a different channel/bot. Refusing to use it.')
    last = data.get('last_scanned_id', 0)
    if type(last) is not int or last < 0:
        raise ValueError('Invalid checkpoint ID.')
    return last


def write_checkpoint(path: Path, source_id: int, bot_id: int, last_id: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name != 'nt':
        os.chmod(path.parent, 0o700)
    data = dict(source_id=source_id, bot_id=bot_id, last_scanned_id=last_id,
                note='Last Telegram message scanned/forwarded, NOT a guarantee of catalog approval')
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    if os.name != 'nt':
        os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def read_api_credentials() -> tuple[int, str]:
    """Never put API_HASH, phone code or local session in code or Git."""
    raw_id = os.environ.get('TG_API_ID', '').strip() or input('Telegram API ID (from my.telegram.org): ').strip()
    api_hash = os.environ.get('TG_API_HASH', '').strip() or getpass.getpass('Telegram API hash (hidden): ').strip()
    if not raw_id.isdecimal() or int(raw_id) <= 0 or len(api_hash) != 32 or any(x not in '0123456789abcdefABCDEF' for x in api_hash):
        raise ValueError('Invalid Telegram API ID/hash. Obtain them at my.telegram.org; do not share them in chat.')
    return int(raw_id), api_hash


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='Import OLD documents from your OWN channel into V11.8.8 smart bulk via Telegram forwards. No file downloads.')
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--list-channels', action='store_true', help='Show channels managed by your logged-in account')
    mode.add_argument('--dry-run', action='store_true', help='Preview candidate old files without forwarding or changing checkpoint')
    mode.add_argument('--apply', action='store_true', help='Actually forward into the bot after confirming destination')
    p.add_argument('--source', help='Channel @username or numeric channel ID (discover with --list-channels)')
    p.add_argument('--bot', help='Your exact Student Assistant Bot @username')
    p.add_argument('--max-files', type=int, default=50, help='Max documents forwarded in this run (1-100, default 50)')
    p.add_argument('--scan-limit', type=int, default=2000, help='Max history messages scanned this run (default 2000)')
    p.add_argument('--delay', type=float, default=2.0, help='Seconds between forwards, default 2; minimum 1')
    p.add_argument('--language', default='Tamil')
    p.add_argument('--category', default='Education')
    p.add_argument('--author', default='Unknown')
    p.add_argument('--rights', choices=sorted(RIGHTS))
    p.add_argument('--rights-note', help='Genuine distribution permission/license explanation for every document in this batch')
    p.add_argument('--reset-checkpoint', action='store_true', help='Start from earliest available message; safe duplicate handling is done by the bot')
    return p


async def _wait_for_reply(client, dest, since_id: int, phrase: str, timeout_seconds=35) -> bool:
    """Fail closed if the bot isn't actually ready. Avoid forwarding before setup."""
    until = time.monotonic() + timeout_seconds
    while time.monotonic() < until:
        messages = await client.get_messages(dest, limit=12)
        for m in messages:
            if m.id > since_id and not m.out and phrase.lower() in (getattr(m, 'message', '') or '').lower():
                return True
        await asyncio.sleep(1.5)
    return False


async def _run(args, client):
    from telethon.errors import RPCError, FloodWaitError

    me = await client.get_me()
    if not me or getattr(me, 'bot', False):
        raise RuntimeError('Log in with YOUR ADMIN USER account, not a bot account.')

    if args.list_channels:
        print('\nChannels you own/administer:')
        found = 0
        async for dialog in client.iter_dialogs():
            entity = getattr(dialog, 'entity', None)
            if entity is not None and allowed_source(entity):
                print(f'  {dialog.name} — ID: {entity.id}' +
                      (f' — @{entity.username}' if getattr(entity, 'username', None) else ' (private)'))
                found += 1
        print(f'Found: {found}. Use the ID or username as --source.')
        return

    if not args.source or not args.bot:
        raise ValueError('--source and --bot are required for --dry-run and --apply.')
    source_arg = int(args.source) if args.source.lstrip('-').isdigit() else args.source
    source = await client.get_entity(source_arg)
    dest = await client.get_entity(args.bot)
    if not allowed_source(source):
        raise ValueError('Source must be a channel you own or administer. Do not import third-party channels.')
    if protected(source):
        raise ValueError('Source channel has forwarding protection. Cannot import via forwarding.')
    if not getattr(dest, 'bot', False):
        raise ValueError('Destination is not a Telegram bot.')
    if int(source.id) == int(dest.id):
        raise ValueError('Source and destination must differ.')

    root = local_data_dir()
    path = checkpoint_path(int(source.id), int(dest.id), root)
    last_id = 0 if args.reset_checkpoint else read_checkpoint(path, int(source.id), int(dest.id))
    print(f'\nSource: {getattr(source,"title",None)} (ID {source.id})')
    print(f'Destination: @{getattr(dest,"username",None)} (ID {dest.id})')
    print(f'Mode: {"PREVIEW ONLY" if args.dry_run else "FORWARD DOCUMENTS"}')
    print(f'Resume after message: {last_id} | Max files: {args.max_files} | Scan limit: {args.scan_limit}')

    if args.apply:
        validate_metadata(args.language, args.category, args.author, args.rights, args.rights_note)
        print('The account logged into Telegram MUST be an existing authorized bot administrator.')
        print('You must have legal permission to distribute ALL selected documents.')
        confirm = input('To forward into this exact bot, type IMPORT: ').strip()
        if confirm != 'IMPORT':
            print('Canceled. No messages forwarded.')
            return
        started = await client.send_message(dest, '/mediabulk')
        if not await _wait_for_reply(client, dest, started.id, 'SMART BULK UPLOAD'):
            raise RuntimeError('Bot did not confirm V11.8.8 bulk session. Deploy/enable it and check admin access first.')
        config = f'/mediabulkset {args.language} | {args.category} | {args.rights} | {args.author} | {args.rights_note}'
        sent = await client.send_message(dest, config)
        if not await _wait_for_reply(client, dest, sent.id, 'Shared metadata saved'):
            raise RuntimeError('Bot did not confirm shared metadata. No documents forwarded.')
        print('Bot acknowledged batch setup. Forwarding historical documents...')

    scanned = 0
    eligible = 0
    forwarded = 0
    failures = 0
    last_committed = last_id
    try:
        async for message in client.iter_messages(source, reverse=True, min_id=last_id,
                                                 limit=args.scan_limit, wait_time=1):
            scanned += 1
            filename = supported_name(message)
            if filename and not protected(source, message):
                eligible += 1
                if args.dry_run:
                    if eligible <= 20:
                        print(f'  #{message.id}: {filename[:110]}')
                    if eligible >= args.max_files:
                        break
                else:
                    try:
                        # Tell Telegram not to forward the original channel caption.
                        # Shared batch metadata will name the book from its filename.
                        await client.forward_messages(dest, message, from_peer=source,
                                                      drop_media_captions=True)
                    except FloodWaitError as exc:
                        print(f'Rate limit: Telegram requested a pause of {exc.seconds} seconds. Stop and resume later.')
                        break
                    except RPCError as exc:
                        print(f'Forward failed on post #{message.id}: {type(exc).__name__}. Stop; review access/protection.')
                        failures += 1
                        break
                    forwarded += 1
                    print(f'  Forwarded {forwarded}/{args.max_files} — post #{message.id}: {filename[:90]}')
                    last_committed = message.id
                    write_checkpoint(path, int(source.id), int(dest.id), last_committed)
                    if forwarded >= args.max_files:
                        break
                    await asyncio.sleep(args.delay)
            elif filename and protected(source, message):
                failures += 1
                print(f'  Skipped protected post #{message.id}')
            if args.apply:
                last_committed = message.id
                write_checkpoint(path, int(source.id), int(dest.id), last_committed)
    except KeyboardInterrupt:
        print('Interrupted. Existing checkpoint preserved.')
    finally:
        print(f'\nScanned {scanned} history posts; matching documents {eligible}; forwarded {forwarded}; protected/errors {failures}.')
        if args.apply:
            try:
                await client.send_message(dest, '/mediabulkstatus')
                # Do not automatically finalize if a server-side backlog may still be processing.
                print('Check the bot response to /mediabulkstatus. When all files finish processing, send /mediabulkdone.')
            except RPCError:
                print('Could not ask for status. Check the bot chat manually.')
            print(f'Local resume checkpoint: {path}')
            print('A checkpoint means forwarded, NOT confirmed published; review failed files before the next run.')
        else:
            print('Dry run made no Telegram sends and did not modify the checkpoint.')


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    if args.max_files < 1 or args.max_files > MAX_BULK_FILES:
        raise SystemExit('--max-files must be between 1 and 100 (the bot session limit).')
    if args.scan_limit < 1 or args.scan_limit > 100000:
        raise SystemExit('--scan-limit must be 1-100000.')
    if args.delay < 1:
        raise SystemExit('--delay must be at least 1 second.')
    try:
        from telethon import TelegramClient
    except ImportError as exc:
        raise SystemExit('Telethon missing. Install locally: python -m pip install "telethon>=1.42,<2"') from exc
    try:
        api_id, api_hash = read_api_credentials()
    except (ValueError, KeyboardInterrupt, EOFError) as exc:
        raise SystemExit(str(exc)) from exc
    root = local_data_dir()
    root.mkdir(parents=True, exist_ok=True)
    if os.name != 'nt':
        os.chmod(root, 0o700)
    session = root / 'telegram-user'

    async def runner():
        client = TelegramClient(str(session), api_id, api_hash)
        try:
            await client.start()  # Local interactive login, never send codes to bot/ChatGPT.
            await _run(args, client)
        finally:
            await client.disconnect()

    try:
        asyncio.run(runner())
        return 0
    except (ValueError, RuntimeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
