"""Privacy-preserving four-script Office document inspection.

Scans Unicode text runs in the Office XML; reports character counts, not content.
Does not claim font availability or change the document's character encoding.
"""
from __future__ import annotations
from collections import Counter
from io import BytesIO
from pathlib import Path
import argparse
import json
import re
import zipfile
import xml.etree.ElementTree as ET

LABELS = {'ta':'Tamil', 'en':'English/Latin', 'ar':'Arabic', 'si':'Sinhala'}
ARABIC_RANGES = ((0x0600,0x06ff),(0x0750,0x077f),(0x08a0,0x08ff),(0xfb50,0xfdff),(0xfe70,0xfeff))

def classify(character: str) -> str | None:
    cp=ord(character)
    if 0x0b80<=cp<=0x0bff:return 'ta'
    if 0x0d80<=cp<=0x0dff:return 'si'
    if any(a<=cp<=b for a,b in ARABIC_RANGES):return 'ar'
    if (65<=cp<=90 or 97<=cp<=122 or 0x00c0<=cp<=0x024f):return 'en'
    return None


def report(blob: bytes, kind: str) -> dict:
    if kind not in ('docx','pptx'):raise ValueError('Expected DOCX or PPTX')
    if len(blob)>12*1024*1024:raise ValueError('Input exceeds supported document size')
    counts=Counter()
    replacements=0
    ntext=0
    scanned=0
    with zipfile.ZipFile(BytesIO(blob)) as z:
        for info in z.infolist():
            path=info.filename
            if kind=='docx':
                valid=(path=='word/document.xml' or bool(re.fullmatch(r'word/(?:header|footer|footnotes|endnotes)[0-9]*\.xml',path)))
            else:
                valid=bool(re.fullmatch(r'ppt/slides/slide\d+\.xml',path))
            if not valid:continue
            if info.file_size>16*1024*1024:raise ValueError('Office XML part too large for preview')
            scanned+=1
            if scanned>100:raise ValueError('Too many Office text parts')
            root=ET.fromstring(z.read(info))
            for el in root.iter():
                if el.tag.split('}')[-1] not in ('t','delText','instrText'):continue
                if not el.text:continue
                ntext+=len(el.text)
                if ntext>600000:raise ValueError('Office text too large to inspect')
                for ch in el.text:
                    code=classify(ch)
                    if code:counts[code]+=1
                    if ch=='\ufffd':replacements+=1
    return {'language_counts':{key:counts[key] for key in ('ta','en','ar','si')},
            'languages':[LABELS[k] for k in ('ta','en','ar','si') if counts[k]],
            'replacement_characters':replacements,'text_characters_scanned':ntext,
            'notes':['Font availability and complex-script shaping must be checked in the rendered PDF.',
                     'Latin-coded legacy Tamil/Sinhala text cannot be recognized by Unicode range alone.']}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description='Read-only language report; never uploads document text')
    ap.add_argument('file',type=Path)
    args=ap.parse_args()
    kind=args.file.suffix.lower().lstrip('.')
    print(json.dumps(report(args.file.read_bytes(),kind),ensure_ascii=False,indent=2))
