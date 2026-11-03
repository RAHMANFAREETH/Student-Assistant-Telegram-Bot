"""V11.8.4.1: isolate pilot-mode unit tests from production study-access settings.

Only changes TEST_V8_STUDY_LAB.py, TEST_V9_ACADEMIC_TOOLKIT.py and
RUN_REGRESSION_SAFE_V1184.py. No production modules or environment variables.

Usage: python -X utf8 PATCH_STUDY_ACCESS_TEST_ISOLATION_V11841.py --check
       python -X utf8 PATCH_STUDY_ACCESS_TEST_ISOLATION_V11841.py --apply
"""
from __future__ import annotations

import argparse
import difflib
from datetime import datetime
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent


def _replace_once(text: str, old: str, new: str, context: str) -> str:
    if new in text:
        return text
    found = text.count(old)
    if found != 1:
        raise RuntimeError(f"{context}: expected one source anchor, found {found}; refusing to change anything")
    return text.replace(old, new, 1)


def updated(name: str, content: str) -> str:
    if name == 'TEST_V8_STUDY_LAB.py':
        # Two independent TestCase classes use test-only pilot users.
        workflow_old = """        self.old=(os.getenv('V8_ENABLED'),os.getenv('V8_ALLOWED_USER_IDS'))
        os.environ['V8_ENABLED']='true';os.environ['V8_ALLOWED_USER_IDS']='2468'
"""
        workflow_new = """        self.old=(os.getenv('V8_ENABLED'),os.getenv('V8_ALLOWED_USER_IDS'),os.getenv('STUDY_ACCESS_MODE'))
        os.environ['STUDY_ACCESS_MODE']='pilot'  # V11.8.4.1: isolate pilot fixture
        os.environ['V8_ENABLED']='true';os.environ['V8_ALLOWED_USER_IDS']='2468'
"""
        content = _replace_once(content, workflow_old, workflow_new, 'V8 workflow setup')
        workflow_teardown_old = """        for key,val in zip(('V8_ENABLED','V8_ALLOWED_USER_IDS'),self.old):
            if val is None:os.environ.pop(key,None)
            else:os.environ[key]=val
"""
        workflow_teardown_new = """        for key,val in zip(('V8_ENABLED','V8_ALLOWED_USER_IDS','STUDY_ACCESS_MODE'),self.old):
            if val is None:os.environ.pop(key,None)
            else:os.environ[key]=val
"""
        content = _replace_once(content, workflow_teardown_old, workflow_teardown_new,
                                'V8 workflow teardown')
        gate_teardown_old = """        for name,val in zip(('V8_ENABLED','V8_ALLOWED_USER_IDS'),self.old):
            if val is None:os.environ.pop(name,None)
            else:os.environ[name]=val
"""
        gate_teardown_new = """        for name,val in zip(('V8_ENABLED','V8_ALLOWED_USER_IDS','STUDY_ACCESS_MODE'),self.old):
            if val is None:os.environ.pop(name,None)
            else:os.environ[name]=val
"""
        content = _replace_once(content, gate_teardown_old, gate_teardown_new,
                                'V8 gate teardown')
        gate_old = """        self.old=(os.getenv('V8_ENABLED'),os.getenv('V8_ALLOWED_USER_IDS'))
    def tearDown(self):
"""
        gate_new = """        self.old=(os.getenv('V8_ENABLED'),os.getenv('V8_ALLOWED_USER_IDS'),os.getenv('STUDY_ACCESS_MODE'))
        os.environ['STUDY_ACCESS_MODE']='pilot'  # V11.8.4.1: isolate pilot fixture
    def tearDown(self):
"""
        content = _replace_once(content, gate_old, gate_new, 'V8 allowlist gate setup')
        return content
    if name == 'TEST_V9_ACADEMIC_TOOLKIT.py':
        old = """        self.env=patch.dict(os.environ,{'V8_ENABLED':'true','V8_ALLOWED_USER_IDS':'123','V9_ENABLED':'true'})
"""
        new = """        self.env=patch.dict(os.environ,{'V8_ENABLED':'true','V8_ALLOWED_USER_IDS':'123','V9_ENABLED':'true',
                                        'STUDY_ACCESS_MODE':'pilot'})  # V11.8.4.1 test-only
"""
        return _replace_once(content, old, new, 'V9 workflow setup')
    if name == 'RUN_REGRESSION_SAFE_V1184.py':
        old = """APP_KEYS = ('AZURE_TRANSLATOR_KEY', 'AZURE_TRANSLATOR_REGION')
"""
        new = """APP_KEYS = ('AZURE_TRANSLATOR_KEY', 'AZURE_TRANSLATOR_REGION',
            'STUDY_ACCESS_MODE')  # V11.8.4.1: isolate study access mode in tests
"""
        return _replace_once(content, old, new, 'V11.8.4 diagnostic runner')
    raise RuntimeError(f'Unexpected filename: {name}')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--apply', action='store_true')
    args = p.parse_args()

    names = ('TEST_V8_STUDY_LAB.py', 'TEST_V9_ACADEMIC_TOOLKIT.py',
             'RUN_REGRESSION_SAFE_V1184.py')
    proposed = []
    # Validate ALL source files and exact anchors before ANY write.
    for name in names:
        src = ROOT / name
        if not src.is_file():
            p.error(f'Missing file: {src}')
        prior = src.read_text(encoding='utf-8')
        after = updated(name, prior)
        compile(after, name, 'exec')
        if prior != after:
            proposed.append((src, prior, after))

    if args.check:
        if not proposed:
            print('CHECK OK: already installed. No files changed.')
        else:
            for src, before, after in proposed:
                print(''.join(difflib.unified_diff(
                    before.splitlines(keepends=True), after.splitlines(keepends=True),
                    fromfile=src.name+':current', tofile=src.name+':planned')))
            print('CHECK OK. No files changed.')
        return 0

    if not proposed:
        print('V11.8.4.1 already installed; no changes made.')
        return 0
    backup = ROOT / ('V11841_TEST_BACKUP_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    for src, _prior, _after in proposed:
        shutil.copy2(src, backup / src.name)
    written = []
    try:
        for src, _prior, after in proposed:
            src.write_text(after, encoding='utf-8')
            written.append(src)
    except Exception:
        for src in written:
            shutil.copy2(backup / src.name, src)
        raise
    print('V11.8.4.1 test isolation installed. Backup:', backup)
    print('Changed only:', ', '.join(x[0].name for x in proposed))
    print('No production modules, feature flags or runtime environment variables changed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
