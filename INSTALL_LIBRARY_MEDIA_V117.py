"""Idempotent, opt-in V11.7 installer. Preview first, backs up before changes.

This installer NEVER removes old feature modules or overwrites user content.
"""
from __future__ import annotations
import argparse
import difflib
import shutil
from datetime import datetime
from pathlib import Path

VERSION='# V11.7 Media Library + Admin Panel'
TARGETS=('book_library_bot.py','group_books_only_v116.py','group_ui_v115.py',
         'ui_v57.py','navigation.py')


def one(s,old,new,filename):
    if s.count(old)!=1:
        raise ValueError('Unexpected '+filename+' code layout; anchor missing or repeated: '+old[:75])
    return s.replace(old,new,1)


def transform(name,source):
    if VERSION in source:
        return source
    s=source
    if name=='book_library_bot.py':
        s=one(s, "def _search(bot, chat_id, query, group=False, requester_id=None):\n",
              "def _search(bot, chat_id, query, group=False, requester_id=None):\n"
              "    if _on('LIBRARY_MEDIA_V117_ENABLED', False):\n"
              "        from library_media_v117_bot import unified_search\n"
              "        return unified_search(bot, chat_id, query, group=group, requester_id=requester_id)\n",name)
        s=one(s,'def _latest(bot, chat_id):\n',
              "def _latest(bot, chat_id):\n"
              "    if _on('LIBRARY_MEDIA_V117_ENABLED', False):\n"
              "        from library_media_v117_bot import unified_latest\n"
              "        return unified_latest(bot, chat_id)\n",name)
        s=one(s, '    if _on(\'BOOK_LIBRARY_V112_ENABLED\', False):\n        from book_library_v112_bot import handle_preview_start',
              "    if _on('LIBRARY_MEDIA_V117_ENABLED', False):\n"
              "        from library_media_v117_bot import handle_media_start\n"
              "        if handle_media_start(bot, message):\n            return True\n"
              "    if _on('BOOK_LIBRARY_V112_ENABLED', False):\n        from book_library_v112_bot import handle_preview_start",name)
        needle='    """Register early, BEFORE old wildcard navigation and document handlers."""\n'
        s=one(s,needle,needle+
              "    if _on('LIBRARY_MEDIA_V117_ENABLED', False):\n"
              "        from library_media_v117_bot import register_v117_handlers\n"
              "        register_v117_handlers(bot)\n",name)
    elif name=='group_books_only_v116.py':
        needle='def _is_book_match(text):\n'
        s=one(s,needle,needle+
              "    if os.getenv('LIBRARY_MEDIA_V117_ENABLED','false').lower() in ('true','1','yes','on'):\n"
              "        from library_media_v117_bot import has_media_match\n"
              "        if has_media_match(text): return True\n",name)
        s=one(s, "BOOK_COMMANDS = frozenset({'book', 'booksearch', 'books', 'booklatest', 'latestbooks',\n"
              "                            'booksmart', 'bookbrowse'})",
              "BOOK_COMMANDS = frozenset({'book', 'booksearch', 'books', 'booklatest', 'latestbooks',\n"
              "                            'booksmart', 'bookbrowse', 'mediafind', 'medialatest', 'mediapopular'})",name)
        s=one(s,"LATEST_COMMANDS = frozenset({'books', 'booklatest', 'latestbooks'})",
              "LATEST_COMMANDS = frozenset({'books', 'booklatest', 'latestbooks', 'medialatest'})",name)
        needle="        if command in BOOK_COMMANDS:\n"
        needle="            if not _enabled() or not _allowed_group(m.chat.id) or not _verified(m.from_user.id):\n                _ephemeral(bot, m.chat.id, '📚 Book Library is unavailable in this group.')\n                return None\n"
        s=one(s,needle,needle+
              "            if command == 'mediapopular' and active():\n"
              "                if os.getenv('LIBRARY_MEDIA_V117_ENABLED','false').lower() in ('true','1','yes','on'):\n"
              "                    from library_media_v117_bot import show_popular\n"
              "                    show_popular(bot,m.chat.id,group=True)\n                    return None\n",name)
        s=one(s,
              "    def group_books_only_media(m):\n        if not active():\n            from telebot.handler_backends import ContinueHandling\n            return ContinueHandling()\n        return None\n",
              "    def group_books_only_media(m):\n        if not active():\n            from telebot.handler_backends import ContinueHandling\n            return ContinueHandling()\n"
              "        if os.getenv('LIBRARY_MEDIA_GROUP_DELETE','false').strip().lower() in ('true','1','yes','on'):\n"
              "            try: bot.delete_message(m.chat.id,m.message_id)\n"
              "            except Exception: LOG.warning('Cannot delete unauthorized group media',exc_info=True)\n"
              "        return None\n",name)
    elif name=='group_ui_v115.py':
        s=one(s,"r'(?:\\?|&)start=book_[0-9a-fA-F]{32}(?:&|$)'",
              "r'(?:\\?|&)start=(?:book|media)_[0-9a-fA-F]{32}(?:&|$)'",name)
    elif name=='ui_v57.py':
        needle='        _menu(bot, m.chat.id, caption,\n              CATEGORY_FEATURES[category] + [BACK_CATEGORIES, HELP_CENTER])'
        replacement=("        options = CATEGORY_FEATURES[category] + [BACK_CATEGORIES, HELP_CENTER]\n"
                     "        if category == CAT_MORE and getattr(m.chat, 'type', None) == 'private':\n"
                     "            import os\n"
                     "            if os.getenv('LIBRARY_MEDIA_V117_ENABLED', 'false').lower() in ('1','true','yes','on'):\n"
                     "                from book_library_bot import _admin\n"
                     "                if _admin(m.from_user.id):\n"
                     "                    options = CATEGORY_FEATURES[category] + ['🛡️ Library Admin Panel',\n"
                     "                               BACK_CATEGORIES, HELP_CENTER]\n"
                     "        _menu(bot, m.chat.id, caption, options)")
        s=one(s,needle,replacement,name)
    elif name=='navigation.py':
        s=one(s,'GLOBAL_BUTTONS.add("🔎 Find a Tool")',
              'GLOBAL_BUTTONS.add("🔎 Find a Tool")\nGLOBAL_BUTTONS.add("🛡️ Library Admin Panel")',name)
    else:raise ValueError('Not an allowed file '+name)
    s=s.rstrip('\n')+'\n\n'+VERSION+'\n'
    compile(s,name,'exec')
    return s


def integrate(root:Path, *, apply=False, output=print):
    root=Path(root)
    plan={}
    for name in TARGETS:
        path=root/name
        raw=path.read_bytes()
        bom=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
        dos=b'\r\n' in raw
        old=raw.decode('utf-8-sig').replace('\r\n','\n')
        new=transform(name,old)
        if dos:new=new.replace('\n','\r\n')
        plan[name]=(raw,bom+new.encode('utf-8'))
    diff=[name for name,(old,new) in plan.items() if old!=new]
    if not diff:
        output('V11.7 already installed. No modifications.');return []
    if not apply:
        for name in diff:
            a,b=plan[name]
            output(''.join(difflib.unified_diff(a.decode('utf-8-sig').splitlines(True),
                 b.decode('utf-8-sig').splitlines(True),
                 fromfile=name+':current',tofile=name+':planned')))
        output('CHECK OK. No files modified.');return diff
    backup=root/('V117_LIBRARY_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(exist_ok=False)
    for name in diff:shutil.copy2(root/name,backup/name)
    try:
        for name in diff:
            tmp=root/(name+'.v117.tmp')
            tmp.write_bytes(plan[name][1]);tmp.replace(root/name)
    except Exception:
        for name in diff:shutil.copy2(backup/name,root/name)
        raise
    output('Installed V11.7. Backups: '+str(backup))
    output('Modified existing files: '+', '.join(diff))
    return diff


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check',action='store_true')
    group.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    integrate(Path(__file__).resolve().parent,apply=args.apply)
