#!/usr/bin/env python3
"""Guarded, idempotent V11.8.8.2 installer. Only patches library_media_v117_bot.py."""
from __future__ import annotations
import argparse,ast,difflib,os,shutil,sys
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parent
TARGET=ROOT/'library_media_v117_bot.py'
MARK='# V11.8.8.2: individual forward-and-review handler.'
BEFORE="    @bot.message_handler(commands=['mediaupload','mediabulk','mediauploadbulk'])\n"
INSERT="    # V11.8.8.2: individual forward-and-review handler.\n    @bot.message_handler(commands=['mediaforward','mediaforwardset','mediaforwardpublish','mediaforwardcancel'])\n    def individual_forward_commands_v11882(m):\n        if not enabled():return ContinueHandling()\n        if not admin(m):return _message(bot,m.chat.id,'🔒 Administrator-only private command.')\n        import library_individual_forward_v11882 as fw\n        if not fw.enabled():return _message(bot,m.chat.id,'⚠️ Individual forwarding is disabled.')\n        cmd=str(getattr(m,'text','') or '').split()[0].split('@')[0].lower()\n        if cmd=='/mediaforward':return fw.start(bot,m,api=__import__(__name__))\n        if cmd=='/mediaforwardset':return fw.configure(bot,m)\n        if cmd=='/mediaforwardcancel':\n            fw.cancel(m.from_user.id)\n            _state_cancel(m.from_user.id)\n            return _message(bot,m.chat.id,'✅ Individual forward session canceled.')\n        try:return fw.publish(bot,m,api=__import__(__name__))\n        except Exception as exc:return _fail(bot,m,exc)\n\n"

def plan():
    if not TARGET.is_file():return None,'Missing library_media_v117_bot.py'
    if not (ROOT/'library_individual_forward_v11882.py').is_file():return None,'Missing new forward module'
    old=TARGET.read_text(encoding='utf-8')
    if MARK in old:return old,None
    if old.count(BEFORE)!=1:return None,'Expected V11.8.8 uploader hook not found'
    # Guard additional compatibility anchors to avoid modifying an unexpected version.
    if 'smart_bulk_commands_v1188' not in old or 'smart.accept_file' not in old:
        return None,'V11.8.8 Smart Bulk not installed; install it first'
    new=old.replace(BEFORE,INSERT+BEFORE,1)
    anchor="""        try:
            if mode=='bulk':
"""
    replacement="""        try:
            if mode=='forward':
                import library_individual_forward_v11882 as fw
                return fw.receive(bot,m,api=__import__(__name__))
            if mode=='bulk':
"""
    if new.count(anchor)!=1:return None,'Expected V11.8.8 submission hook not found'
    new=new.replace(anchor,replacement,1)
    anchor_cancel="""        smart.cancel(m.from_user.id)
        _state_cancel(m.from_user.id)
"""
    repl_cancel="""        smart.cancel(m.from_user.id)
        import library_individual_forward_v11882 as fw
        fw.cancel(m.from_user.id)
        _state_cancel(m.from_user.id)
"""
    if new.count(anchor_cancel)!=1:return None,'Expected V11.8.8 cancel hook not found'
    new=new.replace(anchor_cancel,repl_cancel,1)
    ast.parse(new,filename=TARGET.name)
    return new,None

def main():
    p=argparse.ArgumentParser()
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--check',action='store_true');group.add_argument('--apply',action='store_true')
    args=p.parse_args()
    new,error=plan()
    if error:print('STOP:',error,file=sys.stderr);return 2
    old=TARGET.read_text(encoding='utf-8')
    if args.check:
        if new!=old:
            print(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='current',tofile='planned')))
        print('CHECK OK.', 'Already installed.' if new==old else 'One production file would change.', 'No files modified.')
        return 0
    if new==old:print('V11.8.8.2 already installed.');return 0
    backup=ROOT/('V11882_FORWARD_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir();shutil.copy2(TARGET,backup/TARGET.name)
    tmp=TARGET.with_name(TARGET.name+'.v11882_tmp')
    try:
        tmp.write_text(new,encoding='utf-8')
        os.replace(tmp,TARGET)
    finally:tmp.unlink(missing_ok=True)
    print('V11.8.8.2 installed. Backup:',backup)
    print('No database, OCR, ZIP, existing bulk workflows, or access policy modified.')
    return 0

if __name__=='__main__':raise SystemExit(main())
