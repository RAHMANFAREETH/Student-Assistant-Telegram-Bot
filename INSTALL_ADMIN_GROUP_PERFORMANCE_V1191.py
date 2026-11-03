"""Guarded one-command V11.9.1 integration; --check before --apply.
Copy this script and its sibling production module into StudentAssistantBot.
Only intended production files are patched; backups are created.
"""
from __future__ import annotations
import argparse
import datetime
import difflib
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parent
# Anchors are from the verified V11.9 deployment as shown by the user's installer.
MODS={
'main.py':[
('register_friendly_v119(bot)\n',
 'register_friendly_v119(bot)\n'
 '# V11.9.1: private admin hub, approved-group helper and lightweight moderation.\n'
 'from group_admin_helper_v1191 import install as install_group_admin_helper_v1191\n'
 'install_group_admin_helper_v1191(bot)\n'),
('app = Flask(__name__)\n',
 'app = Flask(__name__)\n'
 '# V11.9.1: process-local webhook timings; no change to Telegram acknowledgement.\n'
 'from group_admin_helper_v1191 import install_metrics as install_helper_metrics_v1191\n'
 'install_helper_metrics_v1191(app)\n'),
('    except Exception as error:\n        print(\n            "❌ Webhook processing error:"\n',
 '    except Exception as error:\n'
 '        from group_admin_helper_v1191 import record_error as record_helper_error_v1191\n'
 '        record_helper_error_v1191("webhook", error)\n'
 '        print(\n            "❌ Webhook processing error:"\n')
],
'friendly_v119.py':[
('    return _rows(_db().table(FEEDBACK).insert(entry).execute())\n',
 '    saved=_rows(_db().table(FEEDBACK).insert(entry).execute())\n'
 '    # Optional best-effort alert AFTER a successful database write.\n'
 '    try:\n'
 '        from group_admin_helper_v1191 import publish_feedback_event\n'
 '        publish_feedback_event(saved)\n'
 '    except Exception:LOG.debug("Optional admin feedback alert unavailable",exc_info=True)\n'
 '    return saved\n')
],
'book_library_v113_store.py':[
("    return _rows(d.table('book_library_requests').insert({'user_id':user_id,'title':title,\n"
 "        'author':author,'status':'pending'}).execute())[0]\n",
 "    saved=_rows(d.table('book_library_requests').insert({'user_id':user_id,'title':title,\n"
 "        'author':author,'status':'pending'}).execute())[0]\n"
 "    # Admin alert is optional; database save must not depend on Telegram delivery.\n"
 "    try:\n"
 "        from group_admin_helper_v1191 import publish_book_request\n"
 "        publish_book_request(saved)\n"
 "    except Exception:pass\n"
 "    return saved\n")
],
'Dockerfile':[
(' --workers 1 --threads 4 --timeout 180',
 ' --workers 1 --threads ${BOT_WEB_THREADS:-8} --timeout 180')
]
}

def patched(path):
    raw=path.read_text(encoding='utf-8')
    new=raw
    for old,replacement in MODS[path.name]:
        if replacement in new:
            continue
        if new.count(old)!=1:
            raise RuntimeError(f'{path.name}: expected exactly one anchor, found {new.count(old)}. No files modified.')
        new=new.replace(old,replacement,1)
    return raw,new

def main(argv=None):
    parser=argparse.ArgumentParser(description='V11.9.1 guarded patch')
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true')
    mode.add_argument('--apply',action='store_true')
    args=parser.parse_args(argv)
    required=ROOT/'group_admin_helper_v1191.py'
    if not required.is_file():raise RuntimeError('Missing group_admin_helper_v1191.py in project folder.')
    changes=[]
    for fn in MODS:
        path=ROOT/fn
        if not path.is_file():raise RuntimeError(f'Missing {fn}. Use your current V11.9 project folder.')
        raw,new=patched(path)
        changes.append((path,raw,new))
    modified=[(p,old,new) for p,old,new in changes if old!=new]
    if args.check:
        for p,old,new in modified:
            print(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=p.name+':current',tofile=p.name+':planned')))
        print(f'CHECK OK: {len(modified)} existing production files would change. No changes made.')
        return
    if not modified:
        print('V11.9.1 already integrated. No files changed.');return
    timestamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup=ROOT/('V1191_ADMIN_HELPER_BACKUP_'+timestamp)
    backup.mkdir()
    for p,old,new in modified:
        shutil.copy2(p,backup/p.name)
    for p,old,new in modified:
        # Explicitly write only after all paths and anchors validated.
        p.write_text(new,encoding='utf-8')
    print('V11.9.1 applied. Backups:',backup)
    print('Only enable flags after Windows tests, Supabase verification and GitHub/Render deployment.')
    print('Existing adult eligibility, book delivery, unlimited bulk sessions and group gates are unchanged.')

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('PATCH BLOCKED:',exc,file=sys.stderr)
        raise SystemExit(1)
