"""V12.0 targeted repair: visible Mini App buttons and safe login diagnostics.

Run --check before --apply. No live API calls, no environment mutations.
Only four named Python files are patched. Never change Telegram signature verification.
"""
from __future__ import annotations
import argparse
import difflib
from datetime import datetime
from pathlib import Path
import shutil
import sys

MARK_NAV = '# >>> V12.0 SUPER MINI APP REPLY BUTTON >>>'
MARK_HOME = '# >>> V12.0 SUPER MINI APP FRIENDLY BUTTON >>>'
MARK_LAUNCH = '# >>> V12.0 SUPER MINI APP TEXT BUTTON >>>'
MARK_AUTH = '# >>> V12.0 SESSION FAILURE DIAGNOSTIC >>>'
BUTTON = '🎓 Super Mini App'


def only_once(source, needle, name):
    count = source.count(needle)
    if count != 1:
        raise ValueError(f'{name}: expected 1 matching anchor, found {count}; do not force the patch.')


def navigation(s):
    if MARK_NAV in s:
        return s
    anchor = '# V5.7 CATEGORY MENU END'
    only_once(s, anchor, 'navigation.py')
    addition = f'''{MARK_NAV}
# Add a text-trigger button; it will reply with a SIGNED inline WebApp button.
# ReplyKeyboardButton(web_app=...) does not provide signed initData.
import os as _v120_button_os
V120_SUPER_MINI_APP_BUTTON = "{BUTTON}"
if (_v120_button_os.getenv("SUPER_MINIAPP_V120_ENABLED", "").strip().lower() in ("true", "1", "yes", "on")
    and _v120_button_os.getenv("SUPER_MINIAPP_V120_LAUNCH_ENABLED", "").strip().lower() in ("true", "1", "yes", "on")):
    MAIN_MENU_ROWS.insert(-1, (V120_SUPER_MINI_APP_BUTTON,))
# <<< V12.0 SUPER MINI APP REPLY BUTTON <<<
'''
    return s.replace(anchor, anchor + '\n\n' + addition, 1)


def friendly(s):
    if MARK_HOME in s:
        return s
    anchor = "    return _msg(bot,cid,'🏠 Student Assistant — Friendly Home Menu',reply_markup=_keyboard(rows))"
    only_once(s, anchor, 'friendly_v119.py')
    replacement = f'''    {MARK_HOME}
    kb = _keyboard(rows)
    try:
        from super_miniapp_v120_launch import can_launch, mini_app_url
        url = mini_app_url()
        # Friendly Home is private; never show a personalized WebApp button
        # in a group or for an unverified user.
        if url and can_launch(int(cid)):
            from telebot import types
            kb.row(types.InlineKeyboardButton(
                "{BUTTON}", web_app=types.WebAppInfo(url=url)))
    except Exception:
        # Preserve the older Friendly Home if V12 is missing/unavailable.
        pass
    # <<< V12.0 SUPER MINI APP FRIENDLY BUTTON <<<
    return _msg(bot,cid,'🏠 Student Assistant — Friendly Home Menu',reply_markup=kb)'''
    return s.replace(anchor, replacement, 1)


def launch(s):
    if MARK_LAUNCH in s:
        return s
    anchor = "        bot.send_message(chat_id, 'Open your secure Student Assistant Super Mini App:',\n                         reply_markup=keyboard)"
    only_once(s, anchor, 'super_miniapp_v120_launch.py')
    addition = f'''

    {MARK_LAUNCH}
    @bot.message_handler(content_types=['text'],
                         func=lambda m: getattr(getattr(m, 'chat', None), 'type', None) == 'private' and
                         str(getattr(m, 'text', '') or '').strip() == '{BUTTON}')
    def v120_super_app_text_button(message):
        # The reply-keyboard button simply triggers the same verified
        # inline-WebApp launch as /superapp; do NOT use unsigned web_app reply buttons.
        return v120_super_app_command(message)
    # <<< V12.0 SUPER MINI APP TEXT BUTTON <<<'''
    return s.replace(anchor, anchor+addition, 1)


def auth(s):
    if MARK_AUTH in s:
        return s
    # Leave validation and adult checks intact. Provide only a safe log code.
    anchor = '''        except (ValueError, TypeError):
            return jsonify({"error": "Open the app from Telegram and sign in again."}), 401'''
    only_once(s, anchor, 'super_miniapp_v120.py') if s.count(anchor) == 1 else None
    if s.count(anchor) < 1:
        raise ValueError('super_miniapp_v120.py: session authentication handler not found')
    # Only replace first occurrence; the same generic catch is reused in other API handlers.
    replacement = f'''        {MARK_AUTH}
        except (ValueError, TypeError) as exc:
            # Log a category only; never log raw initData, tokens or user IDs.
            detail = str(exc).lower()
            if 'expired' in detail:
                reason = 'expired_telegram_login'
            elif 'signature' in detail:
                reason = 'invalid_telegram_signature'
            elif 'missing user' in detail or 'timestamp' in detail:
                reason = 'missing_signed_user_or_timestamp'
            elif not request.headers.get('X-Telegram-Init-Data', ''):
                reason = 'missing_telegram_initdata'
            else:
                reason = 'invalid_telegram_login'
            app.logger.warning('V12 login denied: %s (no sensitive data logged)', reason)
            return jsonify({{"error": "Open the app from Telegram and sign in again.", "code": reason}}), 401
        # <<< V12.0 SESSION FAILURE DIAGNOSTIC <<<'''
    return s.replace(anchor, replacement, 1)

PATCHES = {
    'navigation.py': navigation,
    'friendly_v119.py': friendly,
    'super_miniapp_v120_launch.py': launch,
    'super_miniapp_v120.py': auth,
}


def process(root: Path, apply: bool):
    edits = {}
    for fname, fn in PATCHES.items():
        path = root / fname
        if not path.is_file() or path.is_symlink():
            raise ValueError(f'{fname}: missing file or unsafe symbolic link')
        before = path.read_text(encoding='utf-8')
        after = fn(before)
        compile(after, fname, 'exec')
        edits[fname] = (before, after)
    for fname, (old,new) in edits.items():
        print(f'{"UPDATE" if old!=new else "UNCHANGED"} {fname}')
        if old != new:
            patch = list(difflib.unified_diff(old.splitlines(),new.splitlines(),fromfile=fname+' (original)',tofile=fname+' (proposed)',lineterm=''))
            print('\n'.join(patch[:110]))
            if len(patch)>110: print('... diff truncated; inspect source before deploy')
    if not apply:
        print('CHECK OK (no files written)')
        return
    changed = [(name,old,new) for name,(old,new) in edits.items() if old!=new]
    if not changed:
        print('NO CHANGES (already installed)')
        return
    backup_dir = root / ('V120_ACCESS_MENU_BACKUP_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup_dir.mkdir(mode=0o700)
    for name,old,new in changed:
        shutil.copy2(root/name, backup_dir/name)
    written = []
    try:
        for name,old,new in changed:
            tmp = root/(name+'.v120-new')
            tmp.write_text(new,encoding='utf-8',newline='')
            tmp.replace(root/name)
            written.append(name)
    except Exception:
        for name in written:
            shutil.copy2(backup_dir/name,root/name)
        raise
    print(f'APPLIED. Backup: {backup_dir}')
    print('This does not configure the Telegram chat Menu Button; use BotFather /setmenubutton.')
    print('Do NOT bypass signed Telegram auth or 18+ checks.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--check',action='store_true')
    action.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    try: process(Path(__file__).resolve().parent,apply=args.apply)
    except (ValueError,OSError,SyntaxError) as exc:
        print(f'ABORT: {exc}',file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':
    raise SystemExit(main())
