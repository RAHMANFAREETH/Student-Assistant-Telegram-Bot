"""Safely switch the already installed V7.17 dependency to permissive alternatives."""
from __future__ import annotations
import argparse
from pathlib import Path
from datetime import datetime
import ast

OLD='PyMuPDF>=1.26,<1.27'
NEW='pypdf>=5,<7\npypdfium2>=4,<6\nreportlab>=4,<6'


def run() -> None:
    cli=argparse.ArgumentParser()
    cli.add_argument('--check',action='store_true')
    cli.add_argument('--apply',action='store_true')
    args=cli.parse_args()
    if args.check == args.apply:
        cli.error('Choose exactly one: --check or --apply')
    project=Path.cwd()
    req=project/'requirements.txt'
    engine=project/'advanced_pdf_v717.py'
    tests=project/'TEST_V7_17_ADVANCED_PDF.py'
    for f in (req,engine,tests):
        if not f.is_file():
            raise SystemExit(f'STOP: Missing {f.name}. Copy the replacement engine and test from ZIP into this folder.')
    code=engine.read_text(encoding='utf-8')
    ast.parse(code)
    if 'import pymupdf' in code or 'def _fitz' in code or 'from pypdf import' not in code:
        raise SystemExit('STOP: advanced_pdf_v717.py is still the old PyMuPDF version. Copy the replacement file first.')
    data=req.read_text(encoding='utf-8')
    count=data.count(OLD)
    if count==1:
        patched=data.replace(OLD,NEW)
    elif count==0 and all(x in data for x in NEW.splitlines()):
        patched=data
    else:
        raise SystemExit('STOP: Requirements file not in expected V7.17 state. No changes made.')
    if args.check:
        print('CHECK OK: replacement module and test are present.')
        print('Requirements:', 'already updated' if data == patched else 'will replace PyMuPDF with pypdf, pypdfium2, reportlab')
        print('No files changed.')
        return
    if patched==data:
        print('Already applied. No files changed.')
        return
    backup=req.with_suffix(req.suffix+'.pre_perm_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.bak')
    backup.write_bytes(req.read_bytes())
    req.write_text(patched,encoding='utf-8')
    print('Updated requirements.txt. Backup:', backup.name)


if __name__ == '__main__':
    run()
