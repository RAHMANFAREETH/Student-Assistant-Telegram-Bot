"""Idempotent, targeted V8 integration. --check prints diffs without writes."""
from __future__ import annotations
import argparse
import difflib
from pathlib import Path
import shutil
from datetime import datetime


def patch_text(filename,text):
    if filename=='main.py':
        marker='register_study_context_handlers(bot, show_main_menu)'
        insertion='''# V8.0 Study Lab — opt-in and registered before stateful legacy workflows.\nfrom v8_bot import register_v8_handlers\nregister_v8_handlers(bot, show_main_menu)\n\n'''
        if insertion not in text:
            if text.count(marker)!=1: raise ValueError('main.py registration anchor mismatch')
            text=text.replace(marker,insertion+marker,1)
        route_anchor='@app.route(\n    "/",'
        route_add='''# V8.0 Mini App: read-only and Telegram-signature protected.\nfrom v8_miniapp import register_v8_miniapp\nregister_v8_miniapp(app)\n\n'''
        if route_add not in text:
            if text.count(route_anchor)!=1: raise ValueError('main.py Flask route anchor mismatch')
            text=text.replace(route_anchor,route_add+route_anchor,1)
        old='"version": "7.9",'
        new='"version": ("8.0-pilot" if os.getenv("V8_ENABLED", "").lower() in ("true", "1", "yes") else "7.9"),'
        if old in text:
            text=text.replace(old,new,1)
        return text
    if filename=='ui_v57.py':
        needle='ALL_UI_BUTTONS = ('
        add='''# V8.0 option only appears if an administrator enables the pilot.\nimport os as _v8_os\nif _v8_os.getenv("V8_ENABLED", "").lower() in ("true", "1", "yes"):\n    CATEGORY_FEATURES[CAT_MORE].insert(0, "🚀 V8 Study Lab")\n\n'''
        if add not in text:
            if text.count(needle)!=1: raise ValueError('ui_v57.py menu anchor mismatch')
            text=text.replace(needle,add+needle,1)
        label_anchor='CATEGORY_TEXT = {'
        label_add='# Keep the multilingual greeting accurate only when V8 is enabled.\nif _v8_os.getenv("V8_ENABLED", "").lower() in ("true", "1", "yes"):\n    for _lang_text in TEXT.values():\n        if "welcome" in _lang_text:\n            _lang_text["welcome"] = _lang_text["welcome"].replace("V7.9", "V8.0 Pilot")\n\n'
        if label_add not in text:
            if text.count(label_anchor)!=1: raise ValueError('ui_v57.py greeting anchor mismatch')
            text=text.replace(label_anchor,label_add+label_anchor,1)
        return text
    if filename=='navigation.py':
        needle='GLOBAL_BUTTONS.add("📝 Text → PDF")'
        add='''# V8 feature selection must not be swallowed by older stateful handlers.\nimport os as _v8_os\nif _v8_os.getenv("V8_ENABLED", "").lower() in ("true", "1", "yes"):\n    GLOBAL_BUTTONS.add("🚀 V8 Study Lab")\n    GLOBAL_BUTTONS.update(("📄 Document Chat", "📚 Past Paper Analyzer",\n        "🧠 Auto Flashcards & Quiz", "📅 Smart Exam Planner", "🎙 Lecture → Notes",\n        "📊 Advanced Progress", "📖 Citation Generator", "🏆 Group Quiz Battles",\n        "📱 Mini App", "☁️ Data Backup"))\n\n'''
        if add not in text:
            if text.count(needle)!=1: raise ValueError('navigation.py button anchor mismatch')
            text=text.replace(needle,add+needle,1)
        return text
    raise ValueError(filename)


def run(folder,apply):
    required=('v8_engine.py','v8_bot.py','v8_miniapp.py','SQL_V8_STUDY_LAB.sql','TEST_V8_STUDY_LAB.py')
    missing=[name for name in required if not (folder/name).is_file()]
    if missing:
        raise FileNotFoundError('Copy all V8 package files into the bot folder first: '+', '.join(missing))
    edits={}
    for name in ('main.py','ui_v57.py','navigation.py'):
        path=folder/name
        original=path.read_text(encoding='utf-8')
        updated=patch_text(name,original)
        edits[name]=(original,updated)
    for name,(original,updated) in edits.items():
        if original==updated:
            print(name,': already integrated'); continue
        print(''.join(difflib.unified_diff(original.splitlines(True),updated.splitlines(True),fromfile=name+':current',tofile=name+':V8')))
    if apply:
        backup=folder/('V8_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
        backup.mkdir(exist_ok=False)
        for name,(original,updated) in edits.items():
            if original!=updated:
                shutil.copy2(folder/name,backup/name)
        try:
            for name,(original,updated) in edits.items():
                if original!=updated:
                    (folder/name).write_text(updated,encoding='utf-8',newline='\n')
        except Exception:
            for name,(original,updated) in edits.items():
                if original!=updated:
                    shutil.copy2(backup/name,folder/name)
            raise
        print('Applied. Original files backed up in:',backup)
    else:
        print('CHECK OK. No files changed. Run --apply only after reviewing diffs.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(); mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true');mode.add_argument('--apply',action='store_true')
    args=parser.parse_args();run(Path(__file__).resolve().parent,args.apply)
