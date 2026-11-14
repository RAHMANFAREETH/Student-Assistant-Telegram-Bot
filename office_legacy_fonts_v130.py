"""Font compatibility guard for DOCX/PPTX -> PDF; does not transcode text.

A legacy font stores glyphs at non-Unicode codepoints. Replacing it with a
Unicode font does not recover the Tamil text. Runtime must have the exact
licensed family available, otherwise the conversion fails before LibreOffice.
"""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import os
import re
import subprocess
import zipfile
import xml.etree.ElementTree as ET

# Registered names are intentionally conservative: this is an indication of
# legacy layout, NOT a claim that two different fonts share the same encoding.
LEGACY_FAMILIES = (
    'Kalaham', 'Bamini', 'Baamini', 'SunTommy', 'Tharmini', 'Vanavil',
    'Senthamil', 'Amudham', 'TSCII', 'TAB', 'TAM', 'Shree Lipi', 'Anjal',
    'Suratha', 'Elango',
    # Sinhala non-Unicode font families: rendering requires matching fonts.
    'FM Abhaya', 'FM Malithi', 'FM Bindumathi', 'FM Derana',
    'DL Manel', 'DL Araliya', 'DL Champika', 'DL Divani',
    'Kaputa', 'kaputadotcom', 'Thibus29STru', 'ISI Font',
)
UNICODE_FAMILIES = (
    'Noto Sans Tamil', 'Noto Serif Tamil', 'Latha', 'Nirmala UI',
    'Vijaya', 'Arial Unicode MS',
)
# Generic font-name suffixes permitted for variant recognition.
_SUFFIX = re.compile(r'(?:plain|regular|medium|normal|bold|italic|light|semibold|demi|roman|mt|ttf|otf)+$', re.I)
_XML_NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

def normalize(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(value).casefold())

def recognized_legacy_font(value: str) -> bool:
    name = normalize(value)
    if not name:
        return False
    for family in LEGACY_FAMILIES:
        stem = normalize(family)
        if name == stem:
            return True
        if name.startswith(stem):
            suffix = name[len(stem):]
            # Permit known styling variants, but not arbitrary family prefixes.
            if suffix and _SUFFIX.fullmatch(suffix):
                return True
            # TAB/TAM and TSCII families legitimately include numeric variants.
            if stem in ('tab','tam','tscii') and suffix and re.fullmatch(r'[0-9]+',suffix):
                return True
    return False

def _doc_font_refs(node: ET.Element) -> list[str]:
    refs=[]
    for e in node.iter():
        if e.tag.endswith('}rFonts'):
            for k,v in e.attrib.items():
                if k.split('}')[-1] in ('ascii','hAnsi','eastAsia','cs'):
                    refs.append(v)
    return refs

def required_legacy_fonts(document: bytes, kind: str) -> tuple[str,...]:
    """Scan explicit run fonts and fonts inherited from used DOCX styles.

    Only Office text parts are parsed. Unused fontTable entries are deliberately
    ignored. Named theme fonts cannot be resolved here (document caution).
    """
    if kind not in ('docx','pptx'):
        return ()
    found={}
    try:
        with zipfile.ZipFile(BytesIO(document)) as z:
            names=set(z.namelist())
            if kind=='docx':
                # Parse style inheritance, but include only styles referenced by
                # document parts plus default styles. Unused definitions are ignored.
                styles={}; defaults=set()
                if 'word/styles.xml' in names:
                    root=ET.fromstring(z.read('word/styles.xml'))
                    for e in root.iter():
                        if e.tag == _XML_NS+'style':
                            sid=e.get(_XML_NS+'styleId')
                            if not sid:continue
                            based=e.find(_XML_NS+'basedOn')
                            parent=(based.get(_XML_NS+'val') if based is not None else None)
                            styles[sid]=(parent,_doc_font_refs(e))
                            if e.get(_XML_NS+'default') in ('1','true'):
                                defaults.add(sid)
                active=set(defaults)
                refs=[]
                for path in names:
                    if path=='word/document.xml' or re.fullmatch(r'word/(?:header|footer|footnotes|endnotes)[0-9]*\.xml',path):
                        root=ET.fromstring(z.read(path))
                        refs+=_doc_font_refs(root)
                        for e in root.iter():
                            if e.tag in (_XML_NS+'pStyle',_XML_NS+'rStyle'):
                                v=e.get(_XML_NS+'val')
                                if v:active.add(v)
                visited=set()
                while active:
                    sid=active.pop()
                    if sid in visited:continue
                    visited.add(sid)
                    parent, more=styles.get(sid,(None,[]))
                    refs+=more
                    if parent and parent not in visited:active.add(parent)
                for v in refs:
                    if recognized_legacy_font(v):found.setdefault(normalize(v),v)
            else:
                for path in names:
                    if re.fullmatch(r'ppt/slides/slide[0-9]+\.xml',path):
                        root=ET.fromstring(z.read(path))
                        for e in root.iter():
                            if e.tag.split('}')[-1] in ('latin','ea','cs'):
                                val=e.get('typeface')
                                if val and recognized_legacy_font(val):found.setdefault(normalize(val),val)
    except (zipfile.BadZipFile,ET.ParseError,KeyError,ValueError) as exc:
        # The calling converter's DOCX validation handles corrupt documents;
        # do not turn font detection failures into false 'font OK' reports.
        raise ValueError('Unable to inspect Office font declarations') from exc
    return tuple(sorted(found.values(),key=str.casefold))

def installed_font_families() -> set[str]|None:
    """Return normalized family names for the *current* OS, never a fixed list."""
    if os.name=='nt':
        try:
            import winreg
            values=set()
            keypath=r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'
            for hive in (winreg.HKEY_LOCAL_MACHINE,winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(hive,keypath) as key:
                        for i in range(winreg.QueryInfoKey(key)[1]):
                            label,_,_=winreg.EnumValue(key,i)
                            values.add(normalize(re.sub(r'\s*\((TrueType|OpenType).*', '',label,flags=re.I)))
                except OSError:pass
            return values or None
        except (OSError,ImportError):return None
    try:
        result=subprocess.run(['fc-list','-f','%{family}\n'],capture_output=True,
                              text=True,timeout=8,check=False)
        if result.returncode:return None
        return {normalize(name) for line in result.stdout.splitlines()
                for name in line.split(',') if normalize(name)} or None
    except (OSError,subprocess.TimeoutExpired):return None

def _has_font(wanted: str, actual: set[str]) -> bool:
    target=normalize(wanted)
    if target in actual:return True
    # Match a variant only inside the same font family (not Bamini <-> Baamini).
    for got in actual:
        if got.startswith(target) and _SUFFIX.fullmatch(got[len(target):] or '!'):
            return True
        if target.startswith(got) and _SUFFIX.fullmatch(target[len(got):] or '!'):
            return True
    return False

def missing_legacy_fonts(document: bytes, kind: str) -> tuple[str,...]:
    wanted=required_legacy_fonts(document,kind)
    if not wanted:return ()
    actual=installed_font_families()
    # Lack of enumeration is unknown, never proof of support.
    if actual is None:return wanted
    return tuple(w for w in wanted if not _has_font(w,actual))
