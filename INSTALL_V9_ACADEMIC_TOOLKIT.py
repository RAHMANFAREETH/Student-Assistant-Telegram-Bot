"""Idempotent V9 integration for the V8.0 project. --check never writes."""
from __future__ import annotations
import argparse, difflib, shutil
from pathlib import Path
from datetime import datetime

FILE_DEPENDENCIES = ('v9_engine.py','v9_bot.py','SQL_V9_ACADEMIC_TOOLKIT.sql','TEST_V9_ACADEMIC_TOOLKIT.py')
MENU_BLOCK = '''# V9.0 Academic Toolkit — independent pilot; uses the V8-approved allowlist.
import os as _v9_os
if _v9_os.getenv("V9_ENABLED", "").lower() in ("true", "1", "yes"):
    CATEGORY_FEATURES[CAT_MORE].insert(0, "🧰 V9 Academic Toolkit")

'''
NAV_BLOCK = '''# V9 toolkit navigation: prevent other stateful features from absorbing button taps.
import os as _v9_os
if _v9_os.getenv("V9_ENABLED", "").lower() in ("true", "1", "yes"):
    GLOBAL_BUTTONS.add("🧰 V9 Academic Toolkit")
    GLOBAL_BUTTONS.update(("📸 Math Solver", "🧠 Mind Map Generator", "📊 Presentation Maker",
       "🔬 Diagram Label Reader", "📋 Assignment Checker", "📖 Syllabus Tracker",
       "🧮 Formula Sheet", "🖼 Timetable Photo Import", "🔎 Document Comparison",
       "📓 Mistake Notebook", "🍅 Focus Timer", "📤 Anki Export",
       "🔍 Citation Verifier", "👥 Study Rooms"))

'''
MAIN_BLOCK = '''# V9.0 optional Academic Toolkit. Register before the older V8 state handlers.
from v9_bot import register_v9_handlers
register_v9_handlers(bot, show_main_menu)

'''
REQ_BLOCK = '\n# V9.0 safe symbolic math engine (BSD-3-Clause)\nsympy>=1.13,<2\n'


def patched(filename, body):
    if filename == 'main.py':
        before='# V8.0 Study Lab — opt-in and registered before stateful legacy workflows.'
        patch=MAIN_BLOCK
    elif filename == 'ui_v57.py':
        before='ALL_UI_BUTTONS = ('
        patch=MENU_BLOCK
    elif filename == 'navigation.py':
        before='GLOBAL_BUTTONS.add("📝 Text → PDF")'
        patch=NAV_BLOCK
    elif filename == 'requirements.txt':
        return body if 'sympy>=' in body.lower() else body.rstrip()+'\n'+REQ_BLOCK
    else:raise ValueError(filename)
    if patch in body:return body
    if body.count(before)!=1:raise ValueError(f'{filename}: V8 integration anchor not unique; stop and review manually.')
    return body.replace(before,patch+before,1)


def run(root, apply):
    missing=[f for f in FILE_DEPENDENCIES if not (root/f).is_file()]
    if missing: raise FileNotFoundError('Missing V9 package files: '+', '.join(missing))
    files=['main.py','ui_v57.py','navigation.py','requirements.txt']
    originals={f:(root/f).read_text(encoding='utf-8') for f in files}
    updates={f:patched(f, originals[f]) for f in files}
    for f in files:
        if originals[f]==updates[f]:print(f,': already integrated');continue
        print(''.join(difflib.unified_diff(originals[f].splitlines(True),updates[f].splitlines(True),
                                       fromfile=f+':current',tofile=f+':planned')))
    if not apply:
        print('CHECK OK. No files changed. Run --apply after reviewing the changes.');return
    backup=root/('V9_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    changed=[f for f in files if updates[f]!=originals[f]]
    if changed:
        backup.mkdir(exist_ok=False)
        for f in changed:shutil.copy2(root/f,backup/f)
    try:
        for f in changed:(root/f).write_text(updates[f],encoding='utf-8',newline='\n')
    except Exception:
        for f in changed:shutil.copy2(backup/f,root/f)
        raise
    print('Applied safely. Backups in:',backup if changed else '(already integrated)')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true');mode.add_argument('--apply',action='store_true')
    args=parser.parse_args();run(Path(__file__).resolve().parent,args.apply)
