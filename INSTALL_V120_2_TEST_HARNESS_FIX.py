"""V12.0.2 test-harness compatibility patch (tests only).

V12.0.2 adds two Flask endpoints, including an @app.post export endpoint.
Older FakeApp test doubles cannot register POST routes and expected only 9
endpoints, whereas the new route count is 11.

Usage:
    python INSTALL_V120_2_TEST_HARNESS_FIX.py --check
    python INSTALL_V120_2_TEST_HARNESS_FIX.py --apply

Never touches production app code, Render configuration, Supabase, or Library.
"""
from __future__ import annotations

import argparse
import difflib
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = ('TEST_SUPER_MINIAPP_V120.py', 'TEST_V120_PUBLIC_ACCESS.py')


def update_super(src: str) -> str:
    marker = "class FakeApp:\n"
    if src.count(marker) != 1:
        raise ValueError('TEST_SUPER_MINIAPP_V120.py: FakeApp not unique')
    before, cls = src.split(marker, 1)
    end = cls.find('\nclass TestSuperMiniApp(')
    if end < 0:
        raise ValueError('TEST_SUPER_MINIAPP_V120.py: test class not found')
    code, rest = cls[:end], cls[end:]
    anchor = '    def route(self, path, methods=None, endpoint=None):\n'
    postdef = ('    def post(self, path, endpoint=None):\n'
               '        return self.route(path, methods=["POST"], endpoint=endpoint)\n')
    if '    def post(self, ' not in code:
        if code.count(anchor) != 1:
            raise ValueError('TEST_SUPER_MINIAPP_V120.py: FakeApp.route layout changed')
        code = code.replace(anchor, postdef + anchor, 1)
    elif code.count(postdef) != 1:
        raise ValueError('TEST_SUPER_MINIAPP_V120.py: unexpected FakeApp.post implementation')
    src = before + marker + code + rest

    old = '        self.assertEqual(len(self.app.view_functions),9)'
    new = ('        # V12.0.2: nine existing endpoints plus POST export and GET download.\n'
           '        self.assertEqual(len(self.app.view_functions),11)\n'
           "        self.assertIn('v120_export_create', self.app.view_functions)\n"
           "        self.assertIn('v120_export_fetch', self.app.view_functions)")
    if old in src:
        if src.count(old) != 1:
            raise ValueError('TEST_SUPER_MINIAPP_V120.py: duplicate route-count assertions')
        src = src.replace(old, new, 1)
    elif new not in src:
        raise ValueError('TEST_SUPER_MINIAPP_V120.py: unexpected route-count assertion')
    return src


def update_public(src: str) -> str:
    marker = 'class FakeApp:\n'
    if src.count(marker) != 1:
        raise ValueError('TEST_V120_PUBLIC_ACCESS.py: FakeApp not unique')
    before, cls = src.split(marker, 1)
    end = cls.find('\nclass Tests(')
    if end < 0:
        raise ValueError('TEST_V120_PUBLIC_ACCESS.py: Tests class not found')
    code, rest = cls[:end], cls[end:]
    anchor = '    def route(self,path,methods=None,endpoint=None):\n'
    postdef = ('    def post(self,path,endpoint=None):\n'
               '        return self.route(path,methods=["POST"],endpoint=endpoint)\n')
    if '    def post(self,' not in code:
        if code.count(anchor) != 1:
            raise ValueError('TEST_V120_PUBLIC_ACCESS.py: FakeApp.route layout changed')
        code = code.replace(anchor, postdef + anchor, 1)
    elif postdef not in code:
        raise ValueError('TEST_V120_PUBLIC_ACCESS.py: unexpected FakeApp.post implementation')
    return before + marker + code + rest


TRANSFORMS = {'TEST_SUPER_MINIAPP_V120.py': update_super,
              'TEST_V120_PUBLIC_ACCESS.py': update_public}


def plan(root: Path):
    changes = {}
    for filename in FILES:
        p = root / filename
        if not p.is_file() or p.is_symlink():
            raise ValueError(f'{filename}: missing or unsafe file; no changes written')
        src = p.read_text(encoding='utf-8-sig')
        dest = TRANSFORMS[filename](src)
        compile(dest, filename, 'exec')
        changes[filename] = (src, dest)
    return changes


def execute(root: Path, apply: bool) -> None:
    changes = plan(root)
    for name, (before, after) in changes.items():
        print(('UPDATE' if before != after else 'UNCHANGED') + ' ' + name)
        if before != after:
            print('\n'.join(difflib.unified_diff(before.splitlines(), after.splitlines(),
                fromfile=name+' (current)',tofile=name+' (proposed)', lineterm='')))
    if not apply:
        print('CHECK OK (no files written)')
        return
    todo = {name:(before,after) for name,(before,after) in changes.items() if before!=after}
    if not todo:
        print('NO CHANGES (already applied)')
        return
    backup = root/('V120_2_TEST_HARNESS_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    for name in todo:
        shutil.copy2(root/name, backup/name)
    written = []
    try:
        for name,(_,after) in todo.items():
            temp = root/(name+'.v1202tmp')
            if temp.exists() or temp.is_symlink():
                raise RuntimeError('Unexpected temporary file: '+str(temp))
            with temp.open('x', encoding='utf-8', newline='\n') as f:
                f.write(after)
            temp.replace(root/name)
            written.append(name)
    except BaseException:
        for name in written:
            shutil.copy2(backup/name,root/name)
        raise
    print('APPLIED. Backup: '+str(backup))
    print('Only TEST files modified; production code untouched.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--apply', action='store_true')
    args=p.parse_args()
    try:
        execute(ROOT, args.apply)
    except (OSError, ValueError, RuntimeError, SyntaxError) as exc:
        print('ABORTED SAFELY:', exc, file=sys.stderr)
        raise SystemExit(2)


if __name__=='__main__':
    main()
