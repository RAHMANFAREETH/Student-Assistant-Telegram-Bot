#!/usr/bin/env python3
"""Guarded V11.8.8.3 patch: unlimited admin smart-bulk attempts until done/cancel.
Run --check, then --apply. Does not touch the V11.8.1 caption fix or admin gates.
"""
from __future__ import annotations
import argparse, ast, difflib, os, shutil, sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
MODULE=ROOT/'library_smart_bulk_v1188.py'
TEST=ROOT/'TEST_SMART_BULK_V1188.py'
CHANGES = [
 ('MAX_ATTEMPTS = 100\nSESSION_SECONDS = 7200', '''# Unlimited number of files; no fixed session timeout for authenticated admins.
# Core V11.7 state accepts infinity as both seconds and remaining counter.
MAX_ATTEMPTS = float('inf')
SESSION_SECONDS = float('inf')'''),
 ("f'📁 Processed: {s.attempted}/{MAX_ATTEMPTS}\\n'", "f'📁 Processed: {s.attempted}\\n'"),
 ("f'Maximum {MAX_ATTEMPTS} files in one session · 2-hour session.\\n'", "'No per-session file limit or fixed timer. Finish with /mediabulkdone.\\n'"),
 ("""    with _LOCK:
        if s.attempted >= MAX_ATTEMPTS:
            _send(bot, m.chat.id, '⚠️ Batch full. Send /mediabulkdone and start a new batch.')
            return True
        s.attempted += 1""", """    with _LOCK:
        s.attempted += 1"""),
 ("""    if s.attempted >= MAX_ATTEMPTS:
        finish(bot, m, api=api)
    return True""", """    # Keep accepting files until /mediabulkdone or /mediacancel.
    return True"""),
]
TEST_CHANGES = [
 ("self.assertEqual(api._state_get(123)[2],100)", "self.assertEqual(api._state_get(123)[2],float('inf'))"),
 ("""    def test_full_session_closed_at_limit(self):
        self.configure();api._state_set(123,'bulk',seconds=120,remaining=100)
        smart._session(123).attempted=99
        with patch.object(api,'submit_media'):
            smart.accept_file(self.bot,msg(),api=api)
        self.assertIsNone(smart._session(123));self.assertIsNone(api._state_get(123))
        self.assertIn('UPLOAD FINISHED',self.bot.sent[-1][1])""", """    def test_over_100_files_remain_open_until_done(self):
        self.configure();api._state_set(123,'bulk',seconds=smart.SESSION_SECONDS,
                                        remaining=smart.MAX_ATTEMPTS)
        with patch.object(api,'submit_media'):
            for i in range(105):
                self.assertTrue(smart.accept_file(self.bot,msg(filename=f'file{i}.pdf'),api=api))
                api._state_advance(123)
        self.assertEqual(smart._session(123).attempted,105)
        self.assertEqual(api._state_get(123)[2],float('inf'))
        self.assertIn('Processed: 105',smart._report(smart._session(123)))
        smart.finish(self.bot,self.admin,api=api)
        self.assertIsNone(smart._session(123));self.assertIsNone(api._state_get(123))
        self.assertIn('UPLOAD FINISHED',self.bot.sent[-1][1])"""),
]
def patch_one(path, changes):
    orig=path.read_text(encoding='utf-8'); new=orig
    problems=[]
    for old,replacement in changes:
        if old in new:
            if new.count(old)!=1 and 'self.assertEqual(api._state_get(123)[2],100)' not in old:
                problems.append(f'Ambiguous matching text in {path.name}: {old[:48]}')
            else:new=new.replace(old,replacement)
        elif replacement in new:pass
        else:problems.append(f'Unrecognized version of {path.name} near: {old[:64]}')
    if not problems:ast.parse(new, filename=path.name)
    return orig,new,problems

def main():
    arg=argparse.ArgumentParser()
    g=arg.add_mutually_exclusive_group(required=True)
    g.add_argument('--check',action='store_true');g.add_argument('--apply',action='store_true')
    opts=arg.parse_args(); errors=[]; plans=[]
    for path,changes in ((MODULE,CHANGES),(TEST,TEST_CHANGES)):
        if not path.is_file():errors.append('Missing '+path.name);continue
        try:
            orig,new,issue=patch_one(path,changes)
            errors.extend(issue);plans.append((path,orig,new))
        except Exception as exc:errors.append(str(exc))
    if errors:
        for e in errors:print('STOP:',e,file=sys.stderr)
        return 2
    for path,old,new in plans:
        if opts.check and old!=new:
            print(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=path.name+':current',tofile=path.name+':planned')))
    if opts.check:
        print('CHECK OK. '+str(sum(o!=n for _,o,n in plans))+' files would change. Nothing modified.')
        return 0
    if all(o==n for _,o,n in plans):
        print('V11.8.8.3 already applied. Nothing modified.');return 0
    backup=ROOT/('V11883_UNLIMITED_BULK_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    for path,old,new in plans:
        if old != new:
            shutil.copy2(path,backup/path.name)
            tmp=path.with_suffix(path.suffix+'.v11883_tmp')
            tmp.write_text(new,encoding='utf-8')
            os.replace(tmp,path)
    print('V11.8.8.3 applied. Backups:',backup)
    print('Admin rights, duplicate detection, ZIP limits, group restrictions and large-file relay unchanged.')
    print('Note: sessions are RAM-only; Render redeploy or restart ends active sessions.')
    return 0
if __name__=='__main__':raise SystemExit(main())
