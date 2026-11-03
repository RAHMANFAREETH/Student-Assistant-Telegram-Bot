#!/usr/bin/env python3
"""Test-only group-search option isolation for the V11.8.8 focused suite.

Safely updates TEST_GROUP_BOOK_ONLY_V116.py. No production or Render settings touched.
"""
from __future__ import annotations
import argparse
import difflib
from datetime import datetime
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / 'TEST_GROUP_BOOK_ONLY_V116.py'
BEFORE_ENV = "            'BOOK_LIBRARY_AUTO_GROUP_SEARCH':'true',\n            'BOOK_LIBRARY_ALLOW_ALL_GROUPS':'true',"
AFTER_ENV = "            'BOOK_LIBRARY_AUTO_GROUP_SEARCH':'true',\n            # Legacy group tests use match-only mode even if Render/local env opts in.\n            'LIBRARY_SEARCH_V1186_ALL_TEXT_ENABLED':'false',\n            'BOOK_LIBRARY_ALLOW_ALL_GROUPS':'true',"
BEFORE_TEST = '''    def test_plain_nonmatch_silent(self):
        with patch.object(gate,'_is_book_match',return_value=False):
            self.dispatch(msg('Hello my classmates'))
        self.assertEqual(self.bot.sent,[])
'''
AFTER_TEST = BEFORE_TEST + '''
    def test_all_text_mode_intentionally_routes_unmatched_text(self):
        # The optional V11.8.6 behavior is separate from legacy match-only mode.
        os.environ['LIBRARY_SEARCH_V1186_ALL_TEXT_ENABLED']='true'
        with patch.object(gate,'_is_book_match',side_effect=AssertionError('should not check catalog')), \\
                patch.object(gate,'_book_search',return_value=None) as search:
            self.dispatch(msg('Unfindable Book Title'))
        search.assert_called_once()
        args, kwargs = search.call_args
        self.assertIs(args[0], self.bot)
        self.assertEqual(args[2], 'Unfindable Book Title')
'''

def plan():
    if not TARGET.is_file():
        return None, 'STOP: TEST_GROUP_BOOK_ONLY_V116.py is missing.'
    original = TARGET.read_text(encoding='utf-8')
    new = original
    for before,after,label in ((BEFORE_ENV,AFTER_ENV,'test environment'),(BEFORE_TEST,AFTER_TEST,'group search test')):
        if after in new:
            continue
        if new.count(before) != 1:
            return None, f'STOP: unexpected {label} source; no changes were made.'
        new = new.replace(before,after,1)
    return (original,new),None

def main():
    p=argparse.ArgumentParser()
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true')
    mode.add_argument('--apply',action='store_true')
    args=p.parse_args()
    values,problem=plan()
    if problem:
        print(problem,file=sys.stderr)
        return 2
    original,new=values
    if original==new:
        print('Already installed. No changes needed.')
        return 0
    print(''.join(difflib.unified_diff(original.splitlines(keepends=True),new.splitlines(keepends=True),
            fromfile=TARGET.name+':current',tofile=TARGET.name+':planned')))
    if args.check:
        print('CHECK OK. Test-only change; no files changed.')
        return 0
    backup=ROOT/('V1188_GROUP_TEST_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(parents=False,exist_ok=False)
    shutil.copy2(TARGET,backup/TARGET.name)
    tmp=TARGET.with_name(TARGET.name+'.v1188tmp')
    tmp.write_text(new,encoding='utf-8',newline='')
    tmp.replace(TARGET)
    print('Test-only fix installed; backup:',backup)
    print('Production files and environment variables unchanged.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
