"""Student Assistant Bot unit-test runner with per-module and environment isolation.

This is a TEST-ONLY tool. It does not patch any production Python module.
It does not print credentials and never changes the parent's environment.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import os
from pathlib import Path
import re
import subprocess
import sys

RUN_RE = re.compile(r'Ran\s+(\d+)\s+tests?')
SKIP_RE = re.compile(r'skipped=(\d+)')
APP_PREFIXES = (
    'BOOK_LIBRARY_', 'LIBRARY_MEDIA_', 'LIBRARY_MANAGE_',
    'LIBRARY_SEARCH_', 'V8_', 'V9_', 'V91_', 'V92_', 'V93_',
    'V10_', 'V101_', 'V11_',
)
APP_KEYS = ('AZURE_TRANSLATOR_KEY', 'AZURE_TRANSLATOR_REGION',
            'STUDY_ACCESS_MODE')  # V11.8.4.1: isolate study access mode in tests
AFFECTED = (
    'TEST_BOOK_LIBRARY', 'TEST_BOOK_LIBRARY_PRIVACY_V114',
    'TEST_BOOK_LIBRARY_V112', 'TEST_BOOK_PUBLIC_LATEST5',
    'TEST_TRANSLATOR_DIRECT_API', 'TEST_TRANSLATOR_FIX',
    'TEST_TRANSLATOR_LOCALES', 'TEST_V8_STUDY_LAB',
    'TEST_V91_MANUAL_ACCESS', 'TEST_V9_ACADEMIC_TOOLKIT',
)


def module_names(root: Path, *, include_lowercase: bool):
    """Use explicit case-sensitive matching, including on Windows."""
    names = []
    for path in root.iterdir():
        if not path.is_file() or path.suffix != '.py' or not path.stem.isidentifier():
            continue
        if fnmatch.fnmatchcase(path.name, 'TEST_*.py'):
            names.append(path.stem)
        elif include_lowercase and fnmatch.fnmatchcase(path.name, 'test_*.py'):
            names.append(path.stem)
    return sorted(names)


def subprocess_env(inherit_app_env: bool):
    env = os.environ.copy()
    removed = []
    if not inherit_app_env:
        for key in list(env):
            if key in APP_KEYS or any(key.startswith(prefix) for prefix in APP_PREFIXES):
                removed.append(key)
                del env[key]
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env, sorted(removed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--affected-only', action='store_true',
                        help='Recheck the 10 previously failing uppercase test modules')
    parser.add_argument('--include-lowercase', action='store_true',
                        help='Also run lowercase tests, including independent adult-service tests')
    parser.add_argument('--inherit-app-env', action='store_true',
                        help='Use existing application feature flags and Azure credentials (diagnostic only)')
    parser.add_argument('--timeout', type=int, default=45)
    parser.add_argument('--output', help='Save full test report at this path')
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error('--timeout must be positive')
    root = Path(__file__).resolve().parent
    names = module_names(root, include_lowercase=args.include_lowercase)
    if args.affected_only:
        missing = sorted(set(AFFECTED) - set(names))
        if missing:
            parser.error('Missing targeted test files: ' + ', '.join(missing))
        names = list(AFFECTED)
    if not names:
        parser.error('No tests found in ' + str(root))

    env, removed = subprocess_env(args.inherit_app_env)
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    output = (Path(args.output).expanduser().resolve() if args.output else
              root / ('V1184_REGRESSION_REPORT_' + stamp + '.txt'))
    report = [
        'Student Assistant Bot test-only regression',
        'Python: ' + sys.version.splitlines()[0],
        'Module isolation: each module uses a new Python process',
        'Application environment: ' + ('inherited' if args.inherit_app_env else 'feature flags isolated'),
        'Redacted count of inherited app keys excluded: ' + str(len(removed)),
        'Modules: ' + str(len(names)),
        '',
    ]
    failed = []
    total = skipped = passed = 0
    print(f'Testing {len(names)} modules; inherited feature settings removed: {len(removed)}')
    print('Production code and local environment variables are NOT modified.')
    for i, name in enumerate(names, 1):
        cmd = [sys.executable, '-X', 'utf8', '-m', 'unittest', name, '-q']
        timed_out = False
        try:
            result = subprocess.run(cmd, cwd=root, env=env, capture_output=True,
                                    text=True, errors='replace', timeout=args.timeout)
            raw = (result.stdout or '') + '\n' + (result.stderr or '')
            rc = result.returncode
        except subprocess.TimeoutExpired as exc:
            def string(x):
                if isinstance(x, bytes):
                    return x.decode('utf-8', 'replace')
                return x or ''
            raw = string(exc.stdout) + '\n' + string(exc.stderr) + '\nTIMEOUT'
            rc = 124
            timed_out = True
        match = RUN_RE.findall(raw)
        count = int(match[-1]) if match else 0
        skip = SKIP_RE.findall(raw)
        count_skipped = int(skip[-1]) if skip else 0
        status = 'TIMEOUT' if timed_out else ('PASS' if rc == 0 and match else 'FAIL')
        passed += (status == 'PASS')
        if status != 'PASS':
            failed.append(name)
        total += count
        skipped += count_skipped
        summary = f'[{i:02d}/{len(names):02d}] {status:7s} {name:45s} {count:4d} tests'
        print(summary, flush=True)
        report.extend(['=' * 74, summary, 'Exit code: ' + str(rc), raw])
    conclusion = [
        'Modules: ' + str(len(names)), 'Passed modules: ' + str(passed),
        'Failed/timeout modules: ' + str(len(failed)),
        'Tests run: ' + str(total), 'Skipped: ' + str(skipped),
        'Nonpassing modules: ' + (', '.join(failed) if failed else '(none)'),
    ]
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('\n'.join(conclusion + [''] + report), encoding='utf-8')
    except OSError as exc:
        print('Cannot save report:', str(exc), file=sys.stderr)
        return 2
    print('\n' + '\n'.join(conclusion))
    print('Detailed report:', output)
    print('Review report for credentials before sharing.')
    return int(bool(failed))


if __name__ == '__main__':
    raise SystemExit(main())
