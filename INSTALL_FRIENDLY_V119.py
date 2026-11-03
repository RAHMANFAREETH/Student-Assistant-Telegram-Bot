"""Guarded additive V11.9 installer. Run from your StudentAssistantBot project directory.

--check shows diffs; --apply backs up originals before writing. Never touches
Supabase, secrets, Render, .env, current handler registration or untracked backups.
"""
from __future__ import annotations
import argparse
import difflib
import datetime
from pathlib import Path
import shutil
import sys

ROOT=Path.cwd()
MODULE='friendly_v119.py'
SIGNATURE='# V11.9 Friendly Student Assistant — all-in-one, opt-in.'


def modify_main(raw):
    # Register BEFORE the group-only text gate so only explicit V11.9 commands
    # are handled, leaving all older group and private handlers as they were.
    anchor='from group_books_only_v116 import install_book_only_group_gate'
    if raw.count(anchor)!=1:raise RuntimeError('Unexpected main.py: group book gate anchor missing/ambiguous.')
    if SIGNATURE not in raw:
        raw=raw.replace(anchor,
            SIGNATURE+'\nfrom friendly_v119 import register as register_friendly_v119\n'
            'register_friendly_v119(bot)\n\n'+anchor,1)
    if 'if friendly_v119_enabled():' not in raw:
        intro='''    # V11.9 greeting and new inline home; retain original reply keyboard.
    from friendly_v119 import enabled as friendly_v119_enabled, home as v119_home, welcome_text as v119_welcome
    if friendly_v119_enabled():
        bot.send_message(chat_id, v119_welcome(first_name), reply_markup=build_main_menu_markup())
        v119_home(bot, chat_id, first_name, send_welcome=False)
        return
'''
        needle='''    """V5.7 compact menu; existing modules still receive original button text."""\n'''
        if raw.count(needle)!=1:raise RuntimeError('Unexpected main.py: original main menu anchor missing.')
        raw=raw.replace(needle,needle+intro,1)
    if 'if handle_v119_referral_start(bot, message):' not in raw:
        needle='''    if handle_library_start(bot, message):
        return
'''
        if raw.count(needle)!=1:raise RuntimeError('Unexpected main.py: /start deep-link guard anchor missing.')
        raw=raw.replace(needle,needle+
            '    # V11.9 opt-in referral deep-link, after existing Book Library deep-links.\n'
            '    from friendly_v119 import handle_start as handle_v119_referral_start\n'
            '    if handle_v119_referral_start(bot, message):\n'
            '        return\n',1)
    return raw


def modify_welcome(raw):
    marker='# V11.9 Arabic greeting (opt-in; older welcome preserved when disabled).'
    if marker in raw:return raw
    old=("def _text(name):\n"
         "    return (\n"
         "        f'👋 Welcome to our Digital Library, {name}! 📚\\n\\n'")
    new=("def _text(name):\n"
         "    "+marker+"\n"
         "    greeting = (f'👋 السَّلَامُ عَلَيْكُمْ وَرَحْمَةُ اللَّهِ وَبَرَكَاتُهُ\\n'\n"
         "                f'Welcome to Student Assistant! 📚\\n👤 {name}\\n\\n') if _on('FRIENDLY_V119_ENABLED') else (\n"
         "                f'👋 Welcome to our Digital Library, {name}! 📚\\n\\n')\n"
         "    return (\n"
         "        greeting +")
    if raw.count(old)!=1:raise RuntimeError('Unexpected group_welcome_v11884.py: greeting anchor missing.')
    return raw.replace(old,new,1)


def plan():
    for dep in ('book_library_bot.py','group_books_only_v116.py','ui_v57.py',
                'library_media_v117_store.py','group_ui_v115.py'):
        if not (ROOT/dep).exists():raise RuntimeError('Required existing module missing: '+dep)
    result={}
    for name,converter in [('main.py',modify_main),('group_welcome_v11884.py',modify_welcome)]:
        path=ROOT/name
        if not path.is_file():raise RuntimeError('File missing: '+name)
        before=path.read_text(encoding='utf-8')
        after=converter(before)
        compile(after,name,'exec')
        result[name]=(before,after)
    module=ROOT/MODULE
    if not module.is_file():raise RuntimeError('Extract '+MODULE+' alongside installer first.')
    compile(module.read_text(encoding='utf-8'),MODULE,'exec')
    return result


def run():
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check',action='store_true')
    modes.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    try:
        changes=plan()
        todo=[(name,before,after) for name,(before,after) in changes.items() if before!=after]
        if args.check:
            for name,before,after in todo:
                print(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
                       fromfile=name+':current',tofile=name+':V11.9')))
            print(f'CHECK OK. {len(todo)} existing production files would change; nothing modified.')
            print('Includes V11.9 new module; SQL migration must be run separately. Do NOT enable feature yet.')
            return 0
        if not todo:
            print('V11.9 already integrated. No changes needed.');return 0
        stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        backup=ROOT/('V119_FRIENDLY_BACKUP_'+stamp)
        backup.mkdir(exist_ok=False)
        try:
            for name,_,_ in todo:shutil.copy2(ROOT/name,backup/name)
            for name,_,after in todo:
                (ROOT/name).write_text(after,encoding='utf-8',newline='')
        except Exception:
            for name,_,_ in todo:
                original=backup/name
                if original.exists():shutil.copy2(original,ROOT/name)
            raise
        print('V11.9 integrated locally. Backup:',backup)
        print('Existing library, AI, PDF, group access and Render env unchanged.')
        print('IMPORTANT: Run SQL_FRIENDLY_V119.sql in Supabase BEFORE setting FRIENDLY_V119_ENABLED=true on Render.')
        return 0
    except Exception as exc:
        print('FAILED:',exc,file=sys.stderr)
        return 1

if __name__=='__main__':sys.exit(run())
