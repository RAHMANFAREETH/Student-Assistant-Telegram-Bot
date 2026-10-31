"""Optional, capped, offline OCR and PDF thumbnail extraction for V11.7.

No external AI or paid API. All downloads limited; the review bot continues to
work if OCR/preview dependencies aren't installed.
"""
from __future__ import annotations
import io
import hashlib
import logging
import os
import re
import shutil
import subprocess

LOG = logging.getLogger(__name__)
MAX_DOWNLOAD = 12 * 1024 * 1024


def get_bytes(bot,file_id,size,*,limit=MAX_DOWNLOAD):
    if size and size > limit: return None
    info = bot.get_file(file_id)
    raw = bot.download_file(info.file_path)
    if not isinstance(raw,bytes):raw=bytes(raw)
    if len(raw)>limit:raise ValueError('Media exceeded processing limit.')
    return raw


def language_hint(text):
    text=str(text or '')
    samples={'Tamil':sum('\u0b80'<=c<='\u0bff' for c in text),
             'Arabic':sum('\u0600'<=c<='\u06ff' for c in text),
             'Sinhala':sum('\u0d80'<=c<='\u0dff' for c in text)}
    top=max(samples,key=samples.get)
    return top if samples[top]>=5 else 'English'


def category_hint(text):
    low=str(text or '').lower()
    for words,cat in [(('grammar','نحو','இலக்கணம்'),'Grammar'),
                      (('math','algebra','கணிதம்'),'Mathematics'),
                      (('biology','anatomy','உயிரியல்'),'Biology'),
                      (('history','வரலாறு','تاريخ'),'History'),
                      (('quran','قرآن','குர்ஆன்'),'Islamic Studies')]:
        if any(w in low for w in words):return cat
    return 'General'


def _tesseract(data,lang='eng+tam+ara+sin'):
    if not shutil.which('tesseract'):return ''
    try:
        run=subprocess.run(['tesseract','stdin','stdout','-l',lang],input=data,
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                           timeout=12,check=False)
        if run.returncode:return ''
        return run.stdout.decode('utf-8','replace')[:10000]
    except (OSError,subprocess.TimeoutExpired):
        LOG.warning('Image OCR timed out or is unavailable')
        return ''


def extract(kind,raw,*,filename=''):
    """Return extracted text and png preview; no change to original source."""
    output={'ocr_text':'','preview_png':None,'sha256':None,
            'suggested_language':None,'suggested_category':None,'suggested_title':None}
    if not raw:return output
    output['sha256']=hashlib.sha256(raw).hexdigest()
    text='';thumb=None
    if kind=='image':
        try:
            from PIL import Image,ImageOps
            with Image.open(io.BytesIO(raw)) as src:
                src.verify()
            with Image.open(io.BytesIO(raw)) as src:
                im=ImageOps.exif_transpose(src).convert('RGB')
                if im.width*im.height>24_000_000: raise ValueError('Image too large for OCR')
                im.thumbnail((640,640))
                tmp=io.BytesIO(); im.save(tmp,format='JPEG',quality=80)
                thumb=tmp.getvalue()
            text=_tesseract(raw)
        except (OSError,ValueError):
            LOG.debug('Cannot build safe image preview')
    elif kind=='pdf':
        try:
            from pypdf import PdfReader
            reader=PdfReader(io.BytesIO(raw),strict=False)
            if reader.is_encrypted:raise ValueError('Encrypted document cannot be previewed')
            if reader.pages:
                text=str(reader.pages[0].extract_text() or '')[:10000]
        except Exception:LOG.debug('PDF text preview not available',exc_info=True)
        try:
            import pypdfium2 as pdfium
            pdf=pdfium.PdfDocument(raw)
            try:
                if len(pdf)>0:
                    page=pdf[0]
                    try:
                        width,height=page.get_size();scale=min(1.4,1000/max(1,width,height))
                        rendered=page.render(scale=scale)
                        image=rendered.to_pil().convert('RGB')
                        image.thumbnail((800,1000))
                        tmp=io.BytesIO();image.save(tmp,format='JPEG',quality=79)
                        thumb=tmp.getvalue()
                    finally:page.close()
            finally:pdf.close()
        except Exception:LOG.debug('PDF first-page preview unavailable',exc_info=True)
        if not text and thumb:
            text=_tesseract(thumb)
    elif kind=='txt':
        text=raw.decode('utf-8','replace')[:10000]
    first_line=next((x.strip() for x in text.splitlines() if 8<=len(x.strip())<=110),None)
    output.update(ocr_text=text,preview_png=thumb,
                  suggested_language=language_hint(text) if text else None,
                  suggested_category=category_hint(text) if text else None,
                  suggested_title=first_line or os.path.splitext(os.path.basename(filename))[0].replace('_',' ').strip()[:150] or None)
    return output


def inspect_upload(bot,info):
    limit=max(0,min(int(os.getenv('LIBRARY_MEDIA_PROCESS_LIMIT_BYTES',str(MAX_DOWNLOAD))),MAX_DOWNLOAD))
    if os.getenv('LIBRARY_MEDIA_OCR_ENABLED','false').lower() not in ('true','1','yes','on'):
        return {'ocr_text':'','sha256':None,'preview_png':None,'suggested_language':None,
                'suggested_category':None,'suggested_title':None}
    if info['kind'] not in ('image','pdf','txt'):
        return {'ocr_text':'','sha256':None,'preview_png':None,'suggested_language':None,
                'suggested_category':None,'suggested_title':None}
    raw=get_bytes(bot,info['telegram_file_id'],info['size'],limit=limit)
    return extract(info['kind'],raw,filename=info['name'])
