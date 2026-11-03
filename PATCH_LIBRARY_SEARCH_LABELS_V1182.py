"""V11.8.2 display-only improvement for V11.7 unified library results.

Usage:
  python -X utf8 PATCH_LIBRARY_SEARCH_LABELS_V1182.py --check
  python -X utf8 PATCH_LIBRARY_SEARCH_LABELS_V1182.py --apply
"""
from __future__ import annotations
import argparse
import difflib
import pathlib
import shutil
from datetime import datetime, timezone

OLD = "def _markup(bot,rows):\n    kb=_keyboard()\n    for r in rows:\n        name=' '.join(str(r.get('title','')).split())[:30]\n        badge=st.BADGES.get(r.get('media_kind','pdf'),'📦')\n        typ=str(r.get('media_kind','pdf')).upper()\n        kb.add(_button(f'{badge} {name} · {typ}'[:63],url=_link(bot,r)))\n    return kb\n"
NEW = 'def _result_label(row):\n    """Show language and size without truncating either edition identifier."""\n    from book_library_store import format_size\n    badge=st.BADGES.get(row.get(\'media_kind\',\'pdf\'),\'📦\')\n    language=\' \'.join(str(row.get(\'language\') or \'Unknown\').split())[:15]\n    kind=str(row.get(\'media_kind\') or \'pdf\').upper()[:6]\n    size=format_size(row[\'file_size\']) if row.get(\'file_size\') else \'\'\n    prefix=f\'{badge} {language} · \'\n    suffix=f\' · {kind}\' + (f\' · {size}\' if size else \'\')\n    available=max(0,63-len(prefix)-len(suffix))\n    title=\' \'.join(str(row.get(\'title\') or \'Untitled\').split())\n    if len(title)>available:\n        title=title[:max(1,available-1)]+\'…\' if available>1 else \'\'\n    return (prefix+title+suffix)[:63]\n\n\ndef _markup(bot,rows):\n    kb=_keyboard()\n    for r in rows:\n        kb.add(_button(_result_label(r),url=_link(bot,r)))\n    return kb\n'


def patch_text(source):
    if NEW in source:
        return source, 'Already installed'
    count = source.count(OLD)
    if count != 1:
        raise RuntimeError('Expected original _markup block not found exactly once. No changes made. Check your actual code before updating.')
    return source.replace(OLD, NEW, 1), 'Patch available'


def main():
    p=argparse.ArgumentParser()
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true')
    mode.add_argument('--apply',action='store_true')
    args=p.parse_args()
    path=pathlib.Path(__file__).resolve().parent/'library_media_v117_bot.py'
    if not path.is_file():
        p.error('Place this script inside your existing StudentAssistantBot directory.')
    before=path.read_text(encoding='utf-8')
    after,status=patch_text(before)
    print('V11.8.2:', status)
    if before==after:
        return
    if args.check:
        print(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='current',tofile='planned')))
        return
    backup=path.with_name(path.name+'.bak_search_labels_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S'))
    shutil.copy2(path,backup)
    try:
        path.write_text(after,encoding='utf-8')
        compile(after,str(path),'exec')
    except Exception:
        shutil.copy2(backup,path)
        raise
    print('Updated:',path.name)
    print('Backup:',backup.name)


if __name__=='__main__':
    main()
