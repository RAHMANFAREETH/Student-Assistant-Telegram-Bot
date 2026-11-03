#!/usr/bin/env python3
"""V11.8.3: isolate contributor review-channel test from optional OCR.

This script patches only TEST_LIBRARY_MEDIA_V117.py, never production bot code.
Usage: python -X utf8 PATCH_V1183_TEST_OCR_ISOLATION.py --check|--apply
"""
from __future__ import annotations
import argparse
from datetime import datetime
import difflib
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / 'TEST_LIBRARY_MEDIA_V117.py'
OLD = (b"        with patch.dict(os.environ,{'BOOK_LIBRARY_CHANNEL_ID':'-10011',"
       b"'BOOK_LIBRARY_REVIEW_CHANNEL_ID':'-10012'}):")
NEW = (b"        with patch.dict(os.environ,{'BOOK_LIBRARY_CHANNEL_ID':'-10011',"
       b"'BOOK_LIBRARY_REVIEW_CHANNEL_ID':'-10012',"
       b"'LIBRARY_MEDIA_OCR_ENABLED':'false'}):")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true',help='Show proposed change without writing')
    mode.add_argument('--apply',action='store_true',help='Back up and fix only the test')
    args=parser.parse_args()
    if not TARGET.is_file():
        parser.error(f'Missing expected test file: {TARGET}')
    original=TARGET.read_bytes()
    if NEW in original:
        print('OCR test isolation already installed; no changes needed.')
        return
    if original.count(OLD)!=1:
        parser.error('Safe patch anchor missing or not unique. No files changed.')
    updated=original.replace(OLD,NEW,1)
    if args.check:
        print('--- TEST_LIBRARY_MEDIA_V117.py:current')
        print('+++ TEST_LIBRARY_MEDIA_V117.py:planned')
        print(''.join(difflib.unified_diff(original.decode('utf-8').splitlines(keepends=True),
                updated.decode('utf-8').splitlines(keepends=True),fromfile='current',tofile='planned')))
        print('CHECK OK. No files changed.')
        return
    backup=ROOT / ('V1183_TEST_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    shutil.copy2(TARGET, backup/TARGET.name)
    TARGET.write_bytes(updated)
    print(f'Test isolation fix installed. Original backed up in: {backup}')
    print('Only TEST_LIBRARY_MEDIA_V117.py changed; production code untouched.')

if __name__=='__main__':
    main()
