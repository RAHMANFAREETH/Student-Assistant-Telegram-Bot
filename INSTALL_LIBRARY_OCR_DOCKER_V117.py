"""Optional offline Tesseract languages for V11.7; retains existing Dockerfile.

Use --check before --apply. No changes unless exact known Dockerfile layout.
"""
from __future__ import annotations
import argparse
import difflib
import shutil
from pathlib import Path
from datetime import datetime

PACKAGES=('tesseract-ocr','tesseract-ocr-eng','tesseract-ocr-tam',
          'tesseract-ocr-ara','tesseract-ocr-sin')


def transform(text):
    if 'tesseract-ocr' in text:
        return text
    if 'apt-get install -y --no-install-recommends' not in text:
        raise ValueError('Dockerfile does not use the expected apt package installation command.')
    anchor='    ca-certificates && rm -rf /var/lib/apt/lists/*'
    if text.count(anchor)!=1:
        raise ValueError('Dockerfile apt layout differs. Do not overwrite it automatically; edit manually instead.')
    new='    '+ ' '.join(PACKAGES) + ' \\\n' + anchor
    return text.replace(anchor,new,1)


def apply(root,*,write=False,output=print):
    file=Path(root)/'Dockerfile'
    raw=file.read_bytes()
    crlf=b'\r\n' in raw
    body=raw.decode('utf-8-sig').replace('\r\n','\n')
    new=transform(body)
    if new==body:
        output('Dockerfile already includes Tesseract packages. No changes.');return False
    if not write:
        output(''.join(difflib.unified_diff(body.splitlines(True),new.splitlines(True),
                 fromfile='Dockerfile:current',tofile='Dockerfile:planned')))
        output('CHECK OK. No changes.');return True
    backup=file.with_name('Dockerfile.V117_OCR_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    shutil.copy2(file,backup)
    prefix=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    data=prefix+(new.replace('\n','\r\n') if crlf else new).encode('utf-8')
    file.write_bytes(data)
    output('Dockerfile OCR packages enabled. Backup: '+str(backup))
    return True


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    actions=parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--check',action='store_true')
    actions.add_argument('--apply',action='store_true')
    opts=parser.parse_args()
    apply(Path(__file__).resolve().parent,write=opts.apply)
