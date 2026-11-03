#!/usr/bin/env python3
"""Guarded V11.8.8 installer: --check previews, --apply backs up and patches.

Only library_media_v117_bot.py is edited; library_smart_bulk_v1188.py and
TEST_SMART_BULK_V1188.py are delivered alongside this installer in the ZIP.
"""
from __future__ import annotations
import argparse
import difflib
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parent
TARGET=ROOT/'library_media_v117_bot.py'
REQUIRED=('library_smart_bulk_v1188.py', 'TEST_SMART_BULK_V1188.py')

PATCHES=[
 ('''    @bot.message_handler(commands=['mediaupload','mediabulk','mediauploadbulk'])
    def admin_upload_start(m):
''', '''    # V11.8.8: explicit bulk metadata/status commands, only in admin private chat.
    @bot.message_handler(commands=['mediabulkset','mediabulkstatus','mediabulkdone'])
    def smart_bulk_commands_v1188(m):
        if not enabled():return ContinueHandling()
        if not admin(m):return _message(bot,m.chat.id,'🔒 Administrator-only private command.')
        import library_smart_bulk_v1188 as smart
        if not smart.enabled():return _message(bot,m.chat.id,'⚠️ Smart bulk upload is disabled.')
        command=str(getattr(m,'text','') or '').split()[0].split('@')[0].lower()
        if command=='/mediabulkstatus':return smart.status(bot,m)
        if command=='/mediabulkdone':return smart.finish(bot,m,api=__import__(__name__))
        session=_state_get(m.from_user.id)
        if not session or session[0]!='bulk':
            return _message(bot,m.chat.id,'⚠️ Start /mediabulk first.')
        return smart.configure(bot,m)

    @bot.message_handler(commands=['mediaupload','mediabulk','mediauploadbulk'])
    def admin_upload_start(m):
'''),
 ('''        bulk='bulk' in token
        _state_set(m.from_user.id,'bulk' if bulk else 'upload',seconds=600 if bulk else 300,
                   remaining=30 if bulk else 1)
''','''        bulk='bulk' in token
        if bulk:
            import library_smart_bulk_v1188 as smart
            if smart.enabled():
                _state_set(m.from_user.id,'bulk',seconds=smart.SESSION_SECONDS,
                           remaining=smart.MAX_ATTEMPTS)
                return smart.begin(bot,m)
        _state_set(m.from_user.id,'bulk' if bulk else 'upload',seconds=600 if bulk else 300,
                   remaining=30 if bulk else 1)
'''),
 ('''    def stop_upload(m):
        if not enabled():return ContinueHandling()
        _state_cancel(m.from_user.id)
        _message(bot,m.chat.id,'✅ Upload session closed.')
''','''    def stop_upload(m):
        if not enabled():return ContinueHandling()
        # Closing bulk uploads must not leave stale shared rights metadata.
        import library_smart_bulk_v1188 as smart
        smart.cancel(m.from_user.id)
        _state_cancel(m.from_user.id)
        _message(bot,m.chat.id,'✅ Upload session closed.')
'''),
 ('''        try:
            if mode=='bulk' and getattr(m,'document',None) and str(getattr(m.document,'file_name','')).lower().endswith('.zip'):
''','''        try:
            if mode=='bulk':
                import library_smart_bulk_v1188 as smart
                if smart.enabled() and smart.accept_file(bot,m,api=__import__(__name__)):
                    _state_advance(m.from_user.id)
                    return
            if mode=='bulk' and getattr(m,'document',None) and str(getattr(m.document,'file_name','')).lower().endswith('.zip'):
'''),
 ('''                if action=='bulk':
                    _state_set(c.from_user.id,'bulk',seconds=600,remaining=30)
                    return _message(bot,c.message.chat.id,'📦 Send files in sequence or ZIP (max 20 files / 20 MB). /mediacancel to stop.')
''','''                if action=='bulk':
                    import library_smart_bulk_v1188 as smart
                    if smart.enabled():
                        _state_set(c.from_user.id,'bulk',seconds=smart.SESSION_SECONDS,
                                   remaining=smart.MAX_ATTEMPTS)
                        from types import SimpleNamespace
                        return smart.begin(bot,SimpleNamespace(from_user=c.from_user,chat=c.message.chat))
                    _state_set(c.from_user.id,'bulk',seconds=600,remaining=30)
                    return _message(bot,c.message.chat.id,'📦 Send files in sequence or ZIP (max 20 files / 20 MB). /mediacancel to stop.')
'''),
]


def plan():
    issues=[];diff='';new_text=None
    for name in REQUIRED:
        if not (ROOT/name).is_file():issues.append('Missing '+name)
    if not TARGET.is_file():issues.append('Missing '+TARGET.name);return diff,None,issues
    old=TARGET.read_text(encoding='utf-8')
    new=old
    for before,after in PATCHES:
        if after in new:
            continue
        elif new.count(before)==1:
            new=new.replace(before,after,1)
        else:
            issues.append('Unexpected source near: '+before.splitlines()[0][:90])
    if issues:return diff,None,issues
    if new!=old:
        diff=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),
                    fromfile=TARGET.name+':current',tofile=TARGET.name+':planned'))
        new_text=new
    return diff,new_text,[]


def main():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check',action='store_true');group.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    diff,new,issues=plan()
    if issues:
        for issue in issues:print('STOP:',issue,file=sys.stderr)
        return 2
    if args.check:
        if new:print(diff)
        print('CHECK OK. '+('One production file would change.' if new else 'Already installed.')+' No files modified.')
        return 0
    if not new:
        print('V11.8.8 already installed. No changes.')
        return 0
    backup=ROOT/('V1188_SMART_BULK_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir();shutil.copy2(TARGET,backup/TARGET.name)
    temp=TARGET.with_name(TARGET.name+'.v1188_tmp')
    try:
        temp.write_text(new,encoding='utf-8')
        import ast
        ast.parse(new,filename=TARGET.name)
        os.replace(temp,TARGET)
    except Exception as exc:
        temp.unlink(missing_ok=True)
        print('INSTALL ERROR:',exc,'Backup:',backup,file=sys.stderr)
        return 3
    print('V11.8.8 installed. Original backed up in:',backup)
    print('No other production modules, databases, OCR/ZIP processing limits, or access rules changed.')
    print('Enable LIBRARY_SMART_BULK_V1188_ENABLED=true on Render ONLY after testing and deployment.')
    return 0

if __name__=='__main__':raise SystemExit(main())
