"""Previewable, reversible install: one additive V11.7 integration file only."""
from __future__ import annotations
import argparse
import difflib
import shutil
from datetime import datetime
from pathlib import Path

MARK = '# V11.8: Manage Library Files for older PDFs and new media.'
TARGET = 'library_media_v117_bot.py'


def _one(text, anchor, replacement):
    if text.count(anchor) != 1:
        raise ValueError('Expected exactly one V11.7 anchor. Your file differs; do not force install: '+anchor[:80])
    return text.replace(anchor, replacement, 1)


def transform(original):
    """Add V11.8 hooks once; repair a missing menu entry in existing installs."""
    text = original
    manage = "('" + chr(0x1F4C1) + " Manage Library Files','manage'),"
    upload = "('" + chr(0x1F4E4) + " Upload Media','upload'),"

    # The former installer used an overly-specific moderation/stats anchor.
    # Use the single Upload Media entry to insert the new button before it.
    if manage not in text:
        text = _one(text, upload, manage + "\n                         " + upload)

    # Already-installed code must keep its existing handlers; never duplicate.
    if MARK in original:
        required = (
            "if action == 'manage'",
            "register_manage_handlers(bot)",
            "if action=='manage':",
        )
        missing = [part for part in required if part not in original]
        if missing:
            raise ValueError("Incomplete V11.8 hooks; refusing partial repair: " + repr(missing))
        return text

    old = "        kb.add(_button(label,data='v117:adm:'+action))\n"
    text = _one(text, old,
                "        if action == 'manage' and os.getenv('LIBRARY_MANAGE_V118_ENABLED','false').lower() not in ('true','yes','1','on'):\n"
                "            continue\n" + old)
    old = ("    from telebot.handler_backends import ContinueHandling\n\n"
           "    @bot.message_handler(commands=['libraryadmin','mediaadmin'])")
    text = _one(text, old,
                "    from telebot.handler_backends import ContinueHandling\n"
                f"    {MARK}\n"
                "    from library_manage_v118 import register_manage_handlers\n"
                "    register_manage_handlers(bot)\n\n"
                "    @bot.message_handler(commands=['libraryadmin','mediaadmin'])")
    old = "                if action=='pending':return _pending_panel(bot,c.message.chat.id)\n"
    text = _one(text, old, old +
                "                if action=='manage':\n"
                "                    from library_manage_v118 import list_panel,enabled as management_enabled\n"
                "                    if not management_enabled():return _message(bot,c.message.chat.id,'\\u26a0\\ufe0f File management is not enabled yet.')\n"
                "                    return list_panel(bot,c.from_user.id,c.message.chat.id)\n")
    return text


def integrate(root, apply=False, output=print):
    target = root / TARGET
    if not target.is_file():
        raise FileNotFoundError('V11.7 is required; missing '+str(target))
    src = target.read_bytes()
    bom = b'\xef\xbb\xbf' if src.startswith(b'\xef\xbb\xbf') else b''
    text = src.decode('utf-8-sig')
    dest = transform(text)
    if dest == text:
        output('V11.8 already installed; no modifications.')
        return False
    if not apply:
        output(''.join(difflib.unified_diff(text.splitlines(True), dest.splitlines(True),
                 fromfile='V11.7 current', tofile='V11.8 planned')))
        output('CHECK OK. Nothing modified.')
        return True
    backup = root / ('V118_MANAGEMENT_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    shutil.copy2(target, backup / TARGET)
    try:
        newbytes = bom + (dest.replace('\n', '\r\n') if '\r\n' in text else dest).encode('utf-8')
        temp = root / (TARGET+'.v118.tmp')
        temp.write_bytes(newbytes)
        temp.replace(target)
    except Exception:
        shutil.copy2(backup / TARGET, target)
        raise
    output('V11.8 installed. Backup: '+str(backup))
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    command = parser.add_mutually_exclusive_group(required=True)
    command.add_argument('--check', action='store_true')
    command.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    integrate(Path(__file__).resolve().parent, apply=args.apply)
