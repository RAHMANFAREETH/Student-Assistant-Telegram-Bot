"""Small, idempotent V9.1 integration installer. --check prints diff, --apply backs up main.py."""
from pathlib import Path
import argparse
import difflib
from datetime import datetime

MARKER = '# V9.1 automatic adult verification (opt-in).'
OLD = '# V9.0 optional Academic Toolkit. Register before the older V8 state handlers.'
INSERT = '''# V9.1 automatic adult verification (opt-in).
from age_verification_v91 import register_v91_age_handlers
register_v91_age_handlers(bot)

'''
APP_OLD = 'register_v8_miniapp(app)'
APP_INSERT = '''register_v8_miniapp(app)

# V9.1 provider return landing page; never grants access from a browser redirect.
from age_verification_v91 import register_v91_age_return
register_v91_age_return(app)'''


def edited(text):
    if MARKER not in text:
        if text.count(OLD) != 1:
            raise ValueError('V9 integration point missing or changed in main.py. No files changed.')
        text = text.replace(OLD, INSERT+OLD, 1)
    if 'register_v91_age_return(app)' not in text:
        if text.count(APP_OLD) != 1:
            raise ValueError('V8 Mini App integration point missing or changed in main.py. No files changed.')
        text = text.replace(APP_OLD, APP_INSERT, 1)
    return text


def main():
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--check', action='store_true')
    g.add_argument('--apply', action='store_true')
    a=p.parse_args()
    path=Path('main.py')
    old=path.read_text(encoding='utf-8')
    new=edited(old)
    if a.check:
        if new==old:
            print('CHECK OK. V9.1 already installed. No files changed.')
        else:
            print(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='main.py:current',tofile='main.py:V9.1')))
            print('CHECK OK. No files changed.')
        return
    if new==old:
        print('Already installed. No files changed.');return
    backup=path.with_suffix(path.suffix+'.pre_v91_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.bak')
    backup.write_text(old,encoding='utf-8')
    path.write_text(new,encoding='utf-8')
    print('APPLIED: main.py. Backup: '+str(backup))

if __name__=='__main__':main()
