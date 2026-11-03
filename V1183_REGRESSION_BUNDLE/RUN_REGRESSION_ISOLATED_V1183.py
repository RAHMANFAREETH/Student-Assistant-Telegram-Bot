"""Run each Student Assistant Bot TEST_*.py module in a separate interpreter.

The old test suites frequently monkeypatch sys.modules, os.environ and imported
singletons. Running them together can produce false cross-suite failures.

This runner DOES NOT modify application code, databases, Telegram, or Render.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

RUN_RE = re.compile(r'Ran\s+(\d+)\s+tests?')
SKIP_RE = re.compile(r'skipped=(\d+)')


def summarize(output: str, rc: int, timed_out: bool):
    n = RUN_RE.findall(output)
    count = int(n[-1]) if n else 0
    m = SKIP_RE.findall(output)
    skipped = int(m[-1]) if m else 0
    if timed_out:
        status = 'TIMEOUT'
    elif rc == 0 and n:
        status = 'PASS'
    else:
        status = 'FAIL'
    return status, count, skipped


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--timeout', type=int, default=45, help='Seconds per module (default: 45)')
    p.add_argument('--match', default='TEST_*.py', help='Test module filename glob')
    p.add_argument('--include-lowercase', action='store_true', help='Also run test_*.py')
    p.add_argument('--output', help='Full report text path (default: system temp directory)')
    args = p.parse_args()
    root = Path(__file__).resolve().parent
    files = sorted(root.glob(args.match))
    if args.include_lowercase:
        files = sorted(set(files) | set(root.glob('test_*.py')))
    files = [x for x in files if x.is_file() and x.stem.isidentifier()]
    if not files:
        print('No tests found in', root, file=sys.stderr)
        return 2
    now = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    outfile = Path(args.output) if args.output else Path(tempfile.gettempdir()) / f'V1183_ISOLATED_TESTS_{now}.txt'
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    failures = []
    passed = 0
    total_tests = 0
    total_skipped = 0
    lines = [f'Isolated regression test report: {now}', f'Working directory: {root}',
             f'Python: {sys.executable}', 'Each module run in a fresh Python process.', '']
    for index, filename in enumerate(files, 1):
        command = [sys.executable, '-X', 'utf8', '-m', 'unittest', filename.stem, '-q']
        timed_out = False
        try:
            proc = subprocess.run(command, cwd=root, env=env, capture_output=True,
                                  text=True, errors='replace', timeout=args.timeout)
            raw = (proc.stdout or '') + '\n' + (proc.stderr or '')
            rc = proc.returncode
        except subprocess.TimeoutExpired as e:
            timed_out = True
            rc = 124
            def _s(x):
                return x.decode('utf-8', 'replace') if isinstance(x, bytes) else (x or '')
            raw = _s(e.stdout) + '\n' + _s(e.stderr) + f'\nTIMEOUT AFTER {args.timeout} seconds'
        status, count, skipped = summarize(raw, rc, timed_out)
        total_tests += count
        total_skipped += skipped
        if status == 'PASS':
            passed += 1
        else:
            failures.append(filename.stem)
        line = f'[{index:02}/{len(files):02}] {status:7} {filename.stem:48} {count:4} tests'
        print(line, flush=True)
        lines.extend(['=' * 76, line, 'Command: ' + ' '.join(command), 'Exit code: ' + str(rc), raw])
    summary = [f'Modules: {len(files)}', f'Passed modules: {passed}',
               f'Failed/timeout modules: {len(failures)}', f'Tests: {total_tests}',
               f'Skipped: {total_skipped}', 'Nonpassing modules: ' + ', '.join(failures)]
    print('\n' + '\n'.join(summary))
    outfile.parent.mkdir(parents=True, exist_ok=True)
    outfile.write_text('\n'.join(summary + ['\n'] + lines), encoding='utf-8')
    print('Full report saved:', outfile)
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
