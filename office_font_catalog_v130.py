"""Exact-font preflight for critical Unicode Office typography.

DOCX/PPTX contents stay in RAM; no network or document-text logging. The
catalog is a selection guide, not a font renderer or licensing grant.
"""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import json
import os
import re
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CATALOG_FILE = ROOT/'font_catalog_v130.json'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
MAX_XML = 8*1024*1024


def catalog() -> dict:
    data=json.loads(CATALOG_FILE.read_text(encoding='utf-8'))
    if data.get('schema')!=1 or not isinstance(data.get('fonts'),list):
        raise ValueError('Unsupported font catalog schema')
    return data


def _xml(zf, member):
    info=zf.getinfo(member)
    if info.file_size>MAX_XML:
        raise ValueError('Office XML font section too large')
    return ET.fromstring(zf.read(info))


def _refs(node):
    result=[]
    for element in node.iter():
        if element.tag == W+'rFonts':
            for key,value in element.attrib.items():
                if key.rsplit('}',1)[-1] in ('ascii','hAnsi','eastAsia','cs') and value:
                    result.append(value)
    return result


def declared_font_names(blob:bytes,kind:str) -> tuple[str,...]:
    """Declared run/font styles used by document; not a rendered coverage test.

    Does not resolve theme font references or measure style substitution.
    """
    if kind not in ('docx','pptx'):raise ValueError('Requires DOCX or PPTX')
    found={}
    try:
        with zipfile.ZipFile(BytesIO(blob)) as z:
            names=set(z.namelist()); active=set(); styles={}; refs=[]
            if kind=='docx':
                if 'word/styles.xml' in names:
                    root=_xml(z,'word/styles.xml')
                    for element in root:
                        if element.tag==W+'docDefaults':refs.extend(_refs(element))
                        if element.tag!=W+'style':continue
                        sid=element.get(W+'styleId')
                        if not sid:continue
                        based=element.find(W+'basedOn')
                        parent=based.get(W+'val') if based is not None else None
                        styles[sid]=(parent,_refs(element))
                        if element.get(W+'default') in ('1','true'):active.add(sid)
                for path in sorted(names):
                    if path=='word/document.xml' or re.fullmatch(r'word/(?:header|footer|footnotes|endnotes)\d*\.xml',path):
                        root=_xml(z,path)
                        refs.extend(_refs(root))
                        for element in root.iter():
                            if element.tag in (W+'pStyle',W+'rStyle'):
                                sid=element.get(W+'val')
                                if sid:active.add(sid)
                seen=set()
                while active:
                    sid=active.pop()
                    if sid in seen:continue
                    seen.add(sid)
                    parent,more=styles.get(sid,(None,()))
                    refs.extend(more)
                    if parent and parent not in seen:active.add(parent)
            else:
                for path in sorted(names):
                    if not re.fullmatch(r'ppt/slides/slide\d+\.xml',path):continue
                    root=_xml(z,path)
                    for e in root.iter():
                        if e.tag.rsplit('}',1)[-1] in ('latin','ea','cs'):
                            v=e.get('typeface')
                            if v:refs.append(v)
            for name in refs:
                simple=normalize(name)
                if simple:found.setdefault(simple,name)
    except (zipfile.BadZipFile,KeyError,ET.ParseError,OSError,ValueError) as exc:
        raise ValueError('Could not inspect Office font declarations') from exc
    return tuple(sorted(found.values(),key=str.casefold))


def normalize(value):
    return re.sub(r'[^a-z0-9]+','',str(value).casefold())


def missing_exact_fonts(blob:bytes,kind:str,*,installed=None,policy=None)->tuple[str,...]:
    """Return important explicit fonts absent on conversion host.

    OFFICE_EXACT_FONT_POLICY: 'priority' (default), 'catalog', or 'off'.
    Every selected family requires an exact actual family, not an fc-match fallback.
    Unknown font enumeration is treated as unverified, not success.
    """
    level=str(policy if policy is not None else os.getenv('OFFICE_EXACT_FONT_POLICY','priority')).casefold().strip()
    if level=='off':return ()
    data=catalog()
    if level=='priority':
        required={normalize(x) for x in data['priority_exact_pdf']}
    elif level=='catalog':
        required={normalize(x['name']) for x in data['fonts']}
    else:raise ValueError('Invalid OFFICE_EXACT_FONT_POLICY')
    fonts=declared_font_names(blob,kind)
    wanted=[name for name in fonts if normalize(name) in required]
    if not wanted:return ()
    if installed is None:
        from office_legacy_fonts_v130 import installed_font_families
        installed=installed_font_families()
    if installed is None:return tuple(wanted)
    available={normalize(x) for x in installed}
    # Do not let fontconfig's suggested *fallback* count as actual installation.
    return tuple(name for name in wanted if normalize(name) not in available)


def installed_summary():
    from office_legacy_fonts_v130 import installed_font_families
    present=installed_font_families()
    data=catalog();out={}
    for language in ('ta','en','ar','si'):
        fonts=[f['name'] for f in data['fonts'] if f['language']==language]
        out[language]={'catalogued':len(fonts),'installed':None if present is None else [f for f in fonts if normalize(f) in present]}
    return out


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description='Read-only font audit; does not send document contents')
    p.add_argument('--file',type=Path)
    p.add_argument('--policy',choices=('off','priority','catalog'),default='priority')
    args=p.parse_args()
    print(json.dumps(installed_summary(),ensure_ascii=False,indent=2))
    if args.file:
        kind=args.file.suffix.lower().lstrip('.')
        blob=args.file.read_bytes()
        print('Font declarations:',declared_font_names(blob,kind))
        print('Missing selected exact fonts:',missing_exact_fonts(blob,kind,policy=args.policy))
