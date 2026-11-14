"""V13.3 standalone *offline* DOCX review/strict font-specific Unicode conversion.

Requires python-docx (already used by the bot). Never modifies the original file;
requires explicit exact-font reviewed profile. Not wired into production PDF Tools.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import unicodedata
from zipfile import ZipFile, BadZipFile

from docx import Document
from docx.oxml.ns import qn

SCRIPT={'ta':re.compile('[\u0b80-\u0bff]'),'si':re.compile('[\u0d80-\u0dff]')}
LEGACY={'bamini','baamini','suntommy','kalaham','vanavil','tharmini','senthamil','amudham','tab','tam','tscii','fm abhaya','fm malithi','fm derana','fm bindumathi','dl manel','dl champika','dl divani','kaputa','amalee','thibus'}

def validate_profile(raw):
    if not isinstance(raw,dict) or raw.get('schema')!='student-legacy-profile-v1':
        raise ValueError('Not a V13.3 reviewed profile')
    language=raw.get('language');font=raw.get('font');maps=raw.get('mappings');samples=raw.get('samples')
    if language not in SCRIPT or not isinstance(font,str) or not font.strip():raise ValueError('Invalid profile language/font')
    if raw.get('provenanceStatus')!='reviewed' or raw.get('direction') not in ('decode','both'):raise ValueError('Profile not independently reviewed')
    if not isinstance(maps,dict) or not 2<=len(maps)<=6000:raise ValueError('Mapping missing or too large')
    if not isinstance(raw.get('source'),str) or not (raw['source'].startswith('https://') or raw['source'].startswith('local-reviewed:')):raise ValueError('Missing source attribution')
    if not isinstance(raw.get('license'),str) or not raw['license']:raise ValueError('Missing mapping license')
    for k,v in maps.items():
        if not isinstance(k,str) or not k or len(k)>40 or not isinstance(v,str) or len(v)>80 or not SCRIPT[language].search(v):
            raise ValueError('Invalid glyph mapping')
        if any(ord(c)<32 and c not in '\t\n\r' for c in k+v):raise ValueError('Control character in mapping')
    if not isinstance(samples,list) or not 2<=len(samples)<=100:raise ValueError('At least two reviewed samples required')
    for s in samples:
        if not isinstance(s,dict) or decode(str(s.get('legacy','')),raw)!=s.get('unicode'):
            raise ValueError('Mapping does not match reviewed examples')
    return raw

def decode(value,raw):
    if not isinstance(value,str) or len(value)>120000:raise ValueError('Input text too large')
    for k,v in (raw.get('preprocess') or {}).items():
        if not isinstance(k,str) or not k or len(k)>20 or not isinstance(v,str) or len(v)>30:raise ValueError('Bad preprocessing rule')
        value=value.replace(k,v)
    pairs=sorted(raw['mappings'].items(),key=lambda p:-len(p[0]))
    output=[];i=0
    while i<len(value):
        p=next(((a,b) for a,b in pairs if value.startswith(a,i)),None)
        if p:output.append(p[1]);i+=len(p[0]);continue
        if value[i].isspace():output.append(value[i]);i+=1;continue
        raise ValueError('Unmapped legacy glyph at position '+str(i+1))
    return unicodedata.normalize('NFC',''.join(output))

def review_zip(path):
    if not path.is_file() or path.suffix.lower()!='.docx' or path.stat().st_size>15*1024*1024:raise ValueError('Choose a DOCX file under 15 MB')
    try:
        with ZipFile(path) as z:
            if len(z.infolist())>1500 or sum(f.file_size for f in z.infolist())>75*1024*1024:raise ValueError('DOCX archive too large after expansion')
            if any(n.endswith('vbaProject.bin') for n in z.namelist()):raise ValueError('Macro-containing DOCX is not accepted')
    except BadZipFile:raise ValueError('Not a valid DOCX archive') from None

def all_paragraphs(doc):
    # Body + nested tables; conservative: do not claim headers, text boxes, etc.
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    def scan(element,parent):
        for child in element.iterchildren():
            if child.tag==qn('w:p'):yield Paragraph(child,parent)
            elif child.tag==qn('w:tbl'):
                tbl=Table(child,parent)
                for row in tbl.rows:
                    for cell in row.cells:
                        yield from scan(cell._tc,cell)
    yield from scan(doc._body._element,doc._body)

def explicit_font(run):
    rpr=run._r.rPr
    if rpr is None:return None
    fonts=rpr.rFonts
    if fonts is None:return None
    return fonts.get(qn('w:ascii')) or fonts.get(qn('w:hAnsi')) or fonts.get(qn('w:cs')) or fonts.get(qn('w:eastAsia'))

def audit(path):
    review_zip(path);doc=Document(str(path));matches=[];pars=list(all_paragraphs(doc))
    for pidx,p in enumerate(pars,1):
        for ridx,run in enumerate(p.runs,1):
            font=explicit_font(run)
            if font and run.text:
                matches.append({'paragraph':pidx,'run':ridx,'font':font,'chars':len(run.text),'legacy_candidate':font.strip().lower() in LEGACY})
    return doc,pars,matches

def convert(path,profile,out):
    reviewed=validate_profile(profile);name=reviewed['font'].casefold();doc,paragraphs,runs=audit(path)
    if out.resolve()==path.resolve():raise ValueError('Output must be a different file')
    total=0;parts=[]
    for p in paragraphs:
        for n,r in enumerate(p.runs):
            font=explicit_font(r)
            if not font or font.casefold()!=name or not r.text:continue
            # Adjacent same-font runs can split a legacy glyph sequence.
            if (n>0 and explicit_font(p.runs[n-1])==font and p.runs[n-1].text) or (n+1<len(p.runs) and explicit_font(p.runs[n+1])==font and p.runs[n+1].text):
                raise ValueError('Adjacent same-font runs: conversion could split a glyph sequence. Review in Word first.')
            for child in r._r.iterchildren():
                if child.tag not in (qn('w:rPr'),qn('w:t')):
                    raise ValueError('Run includes fields/tabs/drawings; no conversion performed')
            parts.append((r,decode(r.text,reviewed)))
    if not parts:raise ValueError('No explicitly declared runs in selected font; cannot safely infer inherited fonts')
    # Conversion was fully validated before any mutation.
    for r,new in parts:
        r.text=new
        r.font.name='Noto Sans Tamil' if reviewed['language']=='ta' else 'Noto Sans Sinhala'
        total+=1
    out.parent.mkdir(parents=True,exist_ok=True)
    doc.save(str(out))
    return {'converted_runs':total,'output':str(out),'original_untouched':True}

def main():
    pa=argparse.ArgumentParser(description='Offline DOCX legacy-font audit and strict Unicode copy')
    pa.add_argument('docx',type=Path);pa.add_argument('--profile',type=Path);pa.add_argument('--output',type=Path);pa.add_argument('--audit-json',type=Path)
    args=pa.parse_args();_,_,runs=audit(args.docx)
    report={'run_count':len(runs),'legacy_candidates':sum(x['legacy_candidate'] for x in runs),'runs':runs[:1000], 'caveat':'Explicit run fonts in body and tables only; headers/footers/text boxes and inherited font styles not audited.'}
    if args.audit_json:args.audit_json.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if args.output:
        if not args.profile:pa.error('--output requires --profile')
        p=json.loads(args.profile.read_text(encoding='utf-8'));print(json.dumps(convert(args.docx,p,args.output),ensure_ascii=False))

if __name__=='__main__':main()
