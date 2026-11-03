#!/usr/bin/env python3
"""V11.8.7 opt-in-policy file relay (default: no application cap).

Only source files for direct Telegram-to-Telegram file copying are modified.
The OCR, hashing, ZIP extraction, and file download safety caps remain intact.

Run --check first, then --apply; backup snapshots made before modification.
"""
from __future__ import annotations
import argparse
import difflib
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime

HERE = Path(__file__).resolve().parent

SPECS = {
 'book_library_bot.py': (
 '''        try:
            limit = max(1, min(int(os.getenv('BOOK_LIBRARY_MAX_BYTES', '52428800')), 2*1024**3))
        except ValueError:
            bot.send_message(m.chat.id, '⚠️ Library upload size limit is misconfigured.')
            return
        file_size = int(getattr(doc, 'file_size', 0) or 0)
        if file_size < 0 or file_size > limit:
            bot.send_message(m.chat.id, f'⚠️ File exceeds library upload limit ({format_size(limit)}).')
            return
''',
 '''        # V11.8.7: copying existing Telegram messages does not download the file.
        # A value of 0 (default) disables the *application* upload-size cap.
        # Positive BOOK_LIBRARY_MAX_BYTES values remain supported by administrators.
        try:
            limit = int(os.getenv('BOOK_LIBRARY_MAX_BYTES', '0'))
            if limit < 0:
                raise ValueError('negative size cap')
        except ValueError:
            bot.send_message(m.chat.id, '⚠️ Library upload size limit is misconfigured.')
            return
        file_size = int(getattr(doc, 'file_size', 0) or 0)
        if file_size < 0:
            bot.send_message(m.chat.id, '⚠️ Invalid document file size.')
            return
        if limit and file_size > limit:
            bot.send_message(m.chat.id, f'⚠️ File exceeds library upload limit ({format_size(limit)}).')
            return
'''),
 'book_library_v113_bot.py': (
 '''            size=int(getattr(doc,'file_size',0) or 0)
            if size<1 or size>int(os.getenv('BOOK_LIBRARY_SUBMISSION_MAX_BYTES','20971520')):
                raise ValueError('Submission too large; default maximum 20 MB.')
''',
 '''            size=int(getattr(doc,'file_size',0) or 0)
            # V11.8.7: approved Telegram-to-Telegram relay has no default app cap.
            # Setting a positive cap restores an administrator-chosen limit.
            maximum=int(os.getenv('BOOK_LIBRARY_SUBMISSION_MAX_BYTES','0'))
            if maximum<0:raise ValueError('Invalid submission size setting.')
            if size<1:raise ValueError('Invalid document file size.')
            if maximum and size>maximum:
                raise ValueError('Submission exceeds configured size limit.')
'''),
 'library_media_v117_bot.py': (
 '''    maximum=int(os.getenv('LIBRARY_MEDIA_SUBMISSION_MAX_BYTES','20971520') if contributor
                else os.getenv('LIBRARY_MEDIA_MAX_BYTES','52428800'))
    maximum=max(1024,min(maximum,100*1024*1024))
    if info['size']>maximum:raise ValueError('File is too large for this library upload.')
''',
 '''    # V11.8.7: media is copied inside Telegram, not downloaded by Render.
    # Zero/default means no *application* size limit; positive values opt in.
    maximum=int(os.getenv('LIBRARY_MEDIA_SUBMISSION_MAX_BYTES','0') if contributor
                else os.getenv('LIBRARY_MEDIA_MAX_BYTES','0'))
    if maximum<0:raise ValueError('Invalid library upload size setting.')
    if info['size']<0:raise ValueError('Invalid media file size.')
    if maximum and info['size']>maximum:
        raise ValueError('File is too large for this library upload.')
'''),
 'TEST_BOOK_LIBRARY.py': (
 '''    def test_admin_oversize(self):
        self.handlers['admin_book_upload'](fake_message(caption='Ihya | Ghazali | Arabic',file_size=90*1024*1024))
        self.assertIn('exceeds library upload limit',self.bot.sent[-1][1])
''',
 '''    def test_admin_oversize(self):
        # Legacy rejection scenario: administrators can explicitly enable a 50 MB cap.
        with patch.dict(os.environ,{'BOOK_LIBRARY_MAX_BYTES':'52428800'}):
            self.handlers['admin_book_upload'](fake_message(caption='Ihya | Ghazali | Arabic',file_size=90*1024*1024))
        self.assertIn('exceeds library upload limit',self.bot.sent[-1][1])
'''),
}


def plan():
    diffs = []
    replacements = {}
    issues = []
    for filename, (old, new) in SPECS.items():
        file = HERE/filename
        if not file.is_file():
            issues.append(f'MISSING {filename}')
            continue
        source = file.read_text(encoding='utf-8')
        if source.count(old) == 1:
            modified = source.replace(old, new, 1)
            replacements[file] = modified
            diff = ''.join(difflib.unified_diff(source.splitlines(True), modified.splitlines(True),
                                                 fromfile=filename+':current', tofile=filename+':planned'))
            diffs.append(diff)
        elif new in source:
            diffs.append(filename + ': already updated; no changes planned.\n')
        else:
            issues.append(f'UNEXPECTED SOURCE {filename}; STOP. No modification attempted.')
    return diffs, replacements, issues


def main():
    ap=argparse.ArgumentParser()
    opts=ap.add_mutually_exclusive_group(required=True)
    opts.add_argument('--check',action='store_true')
    opts.add_argument('--apply',action='store_true')
    args=ap.parse_args()
    diffs, changes, issues = plan()
    for diff in diffs:
        print(diff, end='' if diff.endswith('\n') else '\n')
    if issues:
        for issue in issues: print('STOP:',issue,file=sys.stderr)
        return 2
    if args.check:
        print(f'CHECK OK. {len(changes)} files would change. No files modified.')
        return 0
    if not changes:
        print('V11.8.7 already applied; no files modified.')
        return 0
    backup=HERE / ('V1187_LARGE_RELAY_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    for file in changes:
        shutil.copy2(file,backup/file.name)
    try:
        # Write temp files before replacing any source.
        prepared=[]
        for file, data in changes.items():
            temp=file.with_name(file.name+'.v1187_tmp')
            with temp.open('w',encoding='utf-8',newline='') as fp:fp.write(data)
            prepared.append((file,temp))
        for file,temp in prepared:os.replace(temp,file)
    except Exception as exc:
        print('INSTALL FAILED:',exc,file=sys.stderr)
        print('Your original files are in:',backup,file=sys.stderr)
        return 3
    print('V11.8.7 installed. Originals backed up in:',backup)
    print('No database, OCR processing caps, ZIP extraction limits, or adult access controls changed.')
    print('IMPORTANT: set BOOK_LIBRARY_MAX_BYTES=0 and LIBRARY_MEDIA_MAX_BYTES=0')
    print('and optionally both submission caps=0 on Render if existing values are nonzero.')
    return 0


if __name__=='__main__':raise SystemExit(main())
