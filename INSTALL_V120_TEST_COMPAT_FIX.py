"""Fix two V12.0.1 outdated regression expectations without touching application code.

Usage: python INSTALL_V120_TEST_COMPAT_FIX.py --check
       python INSTALL_V120_TEST_COMPAT_FIX.py --apply
"""
from __future__ import annotations

import argparse
import difflib
from datetime import datetime
from pathlib import Path
import shutil
import sys

FILES = ('TEST_SUPER_MINIAPP_V120.py', 'TEST_V7_9_AUDIT.py')


def _once(text: str, old: str, label: str) -> None:
    count = text.count(old)
    if count != 1:
        raise ValueError(f'{label}: expected exactly one original test anchor, found {count}. Aborting safely.')


def update_super_test(source: str) -> str:
    # Re-run the legacy adult-verification assertion with adult mode explicitly ON.
    # The previous test implicitly depended on the developer's current environment.
    start = source.find('    def test_requires_signed_login_and_adult(self):')
    end = source.find('    def test_safe_security_headers(self):', start)
    if start < 0 or end < 0 or start >= end:
        raise ValueError('TEST_SUPER_MINIAPP_V120.py: expected test method layout not found.')
    block = source[start:end]
    if '# V120 TEST MODE COMPAT' in block:
        return source
    before = "with patch.dict(os.environ, {'BOT_TOKEN':'secret'}):"
    after = ("with patch.dict(os.environ, {'BOT_TOKEN':'secret', "
             "'SUPER_MINIAPP_V120_REQUIRE_ADULT':'true', "
             "'SUPER_MINIAPP_V120_LAUNCH_PUBLIC':'true', "
             "'SUPER_MINIAPP_V120_PILOT_IDS':''}):  # V120 TEST MODE COMPAT")
    _once(block, before, 'TEST_SUPER_MINIAPP_V120.py environment')
    block = block.replace(before, after, 1)
    check = "                with self.assertRaises(PermissionError):module.verify_super_session('valid')"
    extra = ("\n                # Public utility mode deliberately removes *manual* adult verification,\n"
             "                # but always requires valid Telegram HMAC for private user data.\n"
             "                with patch.dict(os.environ, {'SUPER_MINIAPP_V120_REQUIRE_ADULT':'false'}):\n"
             "                    self.assertEqual(module.verify_super_session('valid'), 44)\n"
             "                    with self.assertRaises(AuthError):module.verify_super_session('invalid')")
    _once(block, check, 'TEST_SUPER_MINIAPP_V120.py adult/security assertion')
    block = block.replace(check, check+extra, 1)
    return source[:start]+block+source[end:]


def update_audit_test(source: str) -> str:
    start = source.find('    def test_ui_categories_unchanged(self):')
    end = source.find('    def test_finder_covers_legacy_and_new_tools(self):', start)
    if start < 0 or end < 0 or start >= end:
        raise ValueError('TEST_V7_9_AUDIT.py: expected test method layout not found.')
    block = source[start:end]
    if '# V120 OPTIONAL MENU BUTTON' in block:
        return source
    old = '        self.assertEqual(sum(len(row) for row in MAIN_MENU_ROWS), 11)'
    new = '''        # V120 OPTIONAL MENU BUTTON: all eleven legacy entries must remain;
        # an enabled Super Mini App adds exactly one extra entry.
        super_label = '🎓 Super Mini App'
        occurrences = sum(button == super_label for row in MAIN_MENU_ROWS for button in row)
        self.assertIn(occurrences, (0, 1))
        self.assertEqual(sum(len(row) for row in MAIN_MENU_ROWS), 11 + occurrences)
        if occurrences:
            self.assertIn(super_label, GLOBAL_BUTTONS)
        self.assertIn('📚 Book Library', GLOBAL_BUTTONS)'''
    _once(block, old, 'TEST_V7_9_AUDIT.py menu count')
    block = block.replace(old, new, 1)
    return source[:start]+block+source[end:]


TRANSFORMS = {'TEST_SUPER_MINIAPP_V120.py': update_super_test,
              'TEST_V7_9_AUDIT.py': update_audit_test}


def process(root: Path, apply: bool) -> dict[str, str]:
    edits = {}
    for filename, transform in TRANSFORMS.items():
        file = root / filename
        if file.is_symlink() or not file.is_file():
            raise ValueError(f'{filename}: file is missing or a symbolic link; no files changed.')
        before = file.read_text(encoding='utf-8-sig')
        after = transform(before)
        compile(after, filename, 'exec')
        edits[filename] = (before, after)
    modes = {}
    for name, (before, after) in edits.items():
        mode = 'UPDATE' if before != after else 'UNCHANGED'
        modes[name] = mode
        print(f'{mode:9s} {name}')
        if before != after:
            print('\n'.join(difflib.unified_diff(before.splitlines(), after.splitlines(),
                  fromfile=name+' (existing)', tofile=name+' (proposed)', lineterm='')))
    if not apply:
        print('CHECK OK — no files written.')
        return modes
    changes = {name: value for name, value in edits.items() if value[0] != value[1]}
    if not changes:
        print('NO CHANGES — test fix already applied.')
        return modes
    backup = root / ('V120_TEST_COMPAT_BACKUP_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(mode=0o700)
    for name in changes:
        shutil.copy2(root/name, backup/name)
    written = []
    try:
        for name, (_, after) in changes.items():
            temp = root / (name+'.v120-testfix.tmp')
            temp.write_text(after, encoding='utf-8', newline='')
            temp.replace(root/name)
            written.append(name)
    except BaseException:
        for name in written:
            shutil.copy2(backup/name,root/name)
        raise
    print(f'APPLIED. Original test backup: {backup}')
    print('Only the two named TEST files were changed. Bot and Mini App code untouched.')
    return modes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    exclusive=parser.add_mutually_exclusive_group(required=True)
    exclusive.add_argument('--check',action='store_true')
    exclusive.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    try:process(Path(__file__).resolve().parent, args.apply)
    except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
        print(f'ABORTED SAFELY: {exc}', file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':
    raise SystemExit(main())
