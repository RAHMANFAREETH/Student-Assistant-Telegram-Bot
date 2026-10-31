"""V11.7 media catalog storage. No public direct database access, only service-role DB.

The older book_library_items remains authoritative for existing PDFs. This
module stores NEW library media and approved user contributions independently.
"""
from __future__ import annotations
import difflib
import os
import re
import unicodedata
import uuid
from datetime import datetime, timezone, timedelta

TABLE = 'library_media_v117'
FAVORITES = 'library_media_v117_favorites'
READING = 'library_media_v117_reading'
AUDIT = 'library_media_v117_audit'
DL_EVENTS = 'library_media_v117_downloads'
PUBLIC = ('id,title,author,language,category,media_kind,file_name,file_size,'
          'preview_file_id,ocr_text,aliases,description,created_at,approved_at,download_count')
ALLOWED_TYPES = frozenset({'pdf','image','audio','video','zip','docx','pptx','epub','txt'})
BADGES = {'pdf':'📄','image':'🖼️','audio':'🎧','video':'🎥','zip':'📦',
          'docx':'📝','pptx':'📊','epub':'📚','txt':'📃'}
RIGHTS = frozenset({'public_domain','cc0','cc_by','cc_by_sa','permission','other'})
STATUS = frozenset({'pending','processing','approved','rejected','hidden'})


def enabled():
    return str(os.getenv('LIBRARY_MEDIA_V117_ENABLED','false')).lower().strip() in ('1','true','yes','on')


def _db():
    from db import supabase
    return supabase


def _rows(resp):
    return getattr(resp,'data',None) or []


def canonical(value):
    return str(uuid.UUID(str(value)))


def clean(value, maximum=180, *, minimum=2):
    value=' '.join(str(value or '').strip().split())
    if not minimum <= len(value) <= maximum or any(c in value for c in '<>\x00|'):
        raise ValueError('Use '+str(minimum)+'–'+str(maximum)+' plain-text characters.')
    return value


def normalize(value):
    value=unicodedata.normalize('NFKC',str(value or '')).casefold()
    value=''.join(c for c in value if not (
        unicodedata.category(c)=='Cf' or 0x0610<=ord(c)<=0x061A
        or 0x064B<=ord(c)<=0x065F or ord(c)==0x0670 or 0x06D6<=ord(c)<=0x06ED))
    return ' '.join(''.join(c if c.isspace() or unicodedata.category(c)[0] in ('L','M','N')
                            else ' ' for c in value).split())


# Opt-in aliases enable cross-script retrieval; don't claim universal transliteration.
_ALIASES = {'ibn kathir':['ابن كثير','இப்னு கஸீர்','ibnu kathir'],
            'arabic':['عربي','العربية','அரபு'],
            'quran':['قرآن','القرآن','குர்ஆன்'],
            'tamil':['தமிழ்','தமிழ் மொழி']}


def expanded_queries(value):
    key=normalize(value)
    expanded={key}
    for latin,alternates in _ALIASES.items():
        group=[latin,*alternates]
        if key in (normalize(x) for x in group):
            expanded.update(normalize(x) for x in group)
    return [x for x in expanded if x]


def detect_kind(message):
    """Accepted Telegram media only; do not trust a misleading extension blindly."""
    if getattr(message,'photo',None):
        photo=message.photo[-1]
        return dict(kind='image',telegram_file_id=photo.file_id,unique_id=photo.file_unique_id,
                    name='photo.jpg',size=int(getattr(photo,'file_size',0) or 0),source='photo')
    for attr,kind in (('video','video'),('audio','audio')):
        obj=getattr(message,attr,None)
        if obj:
            ext='.mp4' if kind=='video' else '.mp3'
            return dict(kind=kind,telegram_file_id=obj.file_id,unique_id=obj.file_unique_id,
                        name=str(getattr(obj,'file_name','') or 'media'+ext)[:255],
                        size=int(getattr(obj,'file_size',0) or 0),source=attr)
    doc=getattr(message,'document',None)
    if not doc:raise ValueError('Send a PDF, image, audio, video, ZIP, DOCX, PPTX, EPUB or TXT file.')
    name=str(getattr(doc,'file_name','') or '')[:255]
    ext=name.rsplit('.',1)[-1].lower() if '.' in name else ''
    kind={'jpg':'image','jpeg':'image','png':'image','webp':'image','gif':'image',
          'pdf':'pdf','mp3':'audio','m4a':'audio','ogg':'audio','wav':'audio',
          'mp4':'video','mov':'video','mkv':'video','webm':'video','zip':'zip',
          'docx':'docx','pptx':'pptx','epub':'epub','txt':'txt'}.get(ext)
    if kind not in ALLOWED_TYPES:raise ValueError('Unsupported file extension: '+ext[:20])
    return dict(kind=kind,telegram_file_id=doc.file_id,unique_id=doc.file_unique_id,
                name=name,size=int(getattr(doc,'file_size',0) or 0),source='document')


def parse_caption(text, *, user=False, default_name='Untitled'):
    """Title | Author | Language | Category | Rights code | Comment | Aliases.

    In admin mode, title can be inferred from filename when no caption exists.
    User submissions must provide a verifiable permission explanation.
    """
    fields=[x.strip() for x in str(text or '').split('|')]
    if user and not 6<=len(fields)<=7:
        raise ValueError('Caption: Title | Author | Language | Category | Permission explanation | Comment | Optional aliases')
    if not user and len(fields)==1 and not fields[0]: fields=[default_name,'Unknown','English','General','other','Admin upload']
    if not user and not 3<=len(fields)<=7:
        raise ValueError('Caption: Title | Author | Language | Category | Rights | Comment | Aliases (last four optional)')
    while len(fields)<7: fields.append('')
    title=clean(fields[0],180)
    author=clean(fields[1] or 'Unknown',120)
    language=clean(fields[2] or 'English',40)
    category=clean(fields[3] or 'General',70)
    rights=clean(fields[4] or 'other',300,minimum=2)
    comment=clean(fields[5] or ('Admin upload' if not user else ''),700,minimum=2)
    aliases=clean(fields[6],500,minimum=0)
    return dict(title=title,author=author,language=language,category=category,
                rights_statement=rights,comment=comment,aliases=aliases)


def duplicates(file_uid, sha=None, *, db=None):
    d=db or _db()
    if file_uid:
        result=_rows(d.table(TABLE).select('id,title').eq('file_unique_id',str(file_uid)).in_(
            'status',['pending','processing','approved']).limit(1).execute())
        if result:return dict(result[0],reason='file_unique_id')
        # Reuse older cross-version duplicate check for PDFs when available.
        try:
            from book_library_v113_store import find_duplicate
            old=find_duplicate(file_uid,None,sha,db=d)
            if old:return dict(old,reason='existing PDF')
        except (ImportError,AttributeError):pass
    if sha:
        result=_rows(d.table(TABLE).select('id,title').eq('sha256',str(sha)).in_(
            'status',['pending','processing','approved']).limit(1).execute())
        if result:return dict(result[0],reason='sha256')
    return None


def same_filename(file_name, *,db=None):
    """Soft warning only; same name does NOT prove identical content."""
    if not file_name:return []
    return _rows((db or _db()).table(TABLE).select('id,title').eq('file_name',str(file_name)[:255])
                 .eq('status','approved').limit(3).execute())


def create(item, *, db=None):
    values=dict(item)
    for key in ('title','author','language','category'):
        values[key]=clean(values[key], 180 if key=='title' else (120 if key=='author' else 70))
    if values['media_kind'] not in ALLOWED_TYPES:raise ValueError('Unsupported media type')
    if values['status'] not in STATUS:raise ValueError('Invalid media status')
    if values['status']=='approved':
        values.setdefault('approved_at',datetime.now(timezone.utc).isoformat())
    if int(values['uploader_id'])<=0:raise ValueError('Invalid contributor')
    if int(values['file_size'])<0:raise ValueError('Invalid media size')
    channel=values['storage_channel_id'] if values['status']=='approved' else values['review_channel_id']
    mid=values['storage_message_id'] if values['status']=='approved' else values['review_message_id']
    if channel is None or int(channel)>=0 or not mid or int(mid)<=0:
        raise ValueError('Storage/review channel message required')
    rows=_rows((db or _db()).table(TABLE).insert(values).execute())
    if not rows or not rows[0].get('id'): raise RuntimeError('Media save not confirmed')
    return rows[0]


def get(media_id, *, published=True,db=None):
    q=(db or _db()).table(TABLE).select('*').eq('id',canonical(media_id))
    if published:q=q.eq('status','approved')
    items=_rows(q.limit(1).execute())
    return items[0] if items else None


def pending(*,db=None,limit=15):
    return _rows((db or _db()).table(TABLE).select('*').eq('status','pending')
                 .order('created_at').limit(min(50,max(1,limit))).execute())


def my_submissions(uid,*,db=None):
    return _rows((db or _db()).table(TABLE).select('id,title,media_kind,status,created_at')
                 .eq('uploader_id',int(uid)).order('created_at',desc=True).limit(20).execute())


def claim(media_id, *, db=None):
    rows=_rows((db or _db()).rpc('library_v117_claim_media',{'p_id':canonical(media_id)}).execute())
    return rows[0] if rows else None


def finalize(media_id, channel_id, message_id, *, db=None):
    data={'storage_channel_id':int(channel_id),'storage_message_id':int(message_id),
          'status':'approved','approved_at':datetime.now(timezone.utc).isoformat()}
    rows=_rows((db or _db()).table(TABLE).update(data).eq('id',canonical(media_id))
               .eq('status','processing').execute())
    return bool(rows)


def reset_processing(media_id,*,db=None):
    return bool(_rows((db or _db()).table(TABLE).update({'status':'pending'})
                .eq('id',canonical(media_id)).eq('status','processing').execute()))


def reject(media_id,*,db=None):
    return bool(_rows((db or _db()).table(TABLE).update({'status':'rejected'})
                .eq('id',canonical(media_id)).eq('status','pending').execute()))


def edit(media_id, values, *,db=None):
    permitted={'title','author','language','category','description','aliases','rights_statement'}
    if not values or set(values)-permitted:raise ValueError('Unsupported metadata edit')
    cleaned={k:clean(v,700 if k=='description' else 500 if k=='aliases' else
                     300 if k=='rights_statement' else 180 if k=='title' else
                     120 if k=='author' else 70,minimum=0 if k in ('aliases','description') else 2)
             for k,v in values.items()}
    return bool(_rows((db or _db()).table(TABLE).update(cleaned).eq('id',canonical(media_id))
                .in_('status',['pending','approved','hidden']).execute()))


def set_visibility(media_id,status,*,db=None):
    if status not in ('hidden','approved'):raise ValueError('Invalid visibility')
    old='approved' if status=='hidden' else 'hidden'
    return bool(_rows((db or _db()).table(TABLE).update({'status':status})
                      .eq('id',canonical(media_id)).eq('status',old).execute()))


def audit(admin_id,operation,media_id=None,details=None, *,db=None):
    data={'admin_id':int(admin_id),'action':clean(operation,65),
          'media_id':canonical(media_id) if media_id else None,
          'details':str(details or '')[:500]}
    return _rows((db or _db()).table(AUDIT).insert(data).execute())


def candidate_rows(*,db=None,limit=350,query=None,kind=None,language=None,
                   author=None,category=None,min_bytes=0,max_bytes=None):
    """Server-matched historical results plus a bounded typo-tolerant recent set.

    The fixed SQL RPC uses bind parameters, not interpolated SQL. Returning rows
    remain on the trusted bot server; storage-channel fields never reach the UI.
    """
    d=db or _db()
    matched=[]
    if query:
        args=dict(p_query=query,p_kind=kind,p_language=language,p_author=author,
                  p_category=category,p_min_bytes=int(min_bytes or 0),
                  p_max_bytes=int(max_bytes) if max_bytes is not None else None,
                  p_limit=250)
        matched=_rows(d.rpc('library_v117_search_candidates',args).execute())
    recent=_rows(d.table(TABLE).select(PUBLIC).eq('status','approved')
                 .order('created_at',desc=True).limit(min(500,max(1,limit))).execute())
    seen=set();result=[]
    for r in matched+recent:
        key=str(r.get('id'))
        if key not in seen:
            result.append(r);seen.add(key)
    return result


def rank(item,q):
    if not q:return 1
    title=normalize(item.get('title')); author=normalize(item.get('author'))
    strings=[title,author,normalize(item.get('aliases')),
             normalize(item.get('category')),normalize(item.get('description')),
             normalize(item.get('ocr_text'))]
    candidates=expanded_queries(q)
    if any(k in s for k in candidates for s in strings if s):
        return max((10 if k in title else 8 if k in strings[2] else 6 if k in strings[3] else 3)
                   for k in candidates for s in strings if s and k in s)
    return max((difflib.SequenceMatcher(None,k,title).ratio()*2 for k in candidates),default=0)


def search(query='',*,kind=None,language=None,author=None,category=None,min_bytes=0,
           max_bytes=None,sort='relevance',limit=10,db=None):
    if query and not 2<=len(query.strip())<=100:raise ValueError('Search must be 2–100 characters.')
    if kind and kind not in ALLOWED_TYPES:raise ValueError('Unsupported type filter')
    if sort not in ('relevance','newest','oldest','popular','smallest','largest'):
        raise ValueError('Invalid sort')
    data=candidate_rows(db=db,query=query,kind=kind,language=language,
                        author=author,category=category,min_bytes=min_bytes,max_bytes=max_bytes)
    matches=[]
    for row in data:
        if kind and row.get('media_kind')!=kind:continue
        if any(normalize(val) not in normalize(row.get(key)) for key,val in
               (('language',language),('author',author),('category',category)) if val):continue
        size=int(row.get('file_size') or 0)
        if size<int(min_bytes or 0) or max_bytes is not None and size>int(max_bytes):continue
        score=rank(row,query)
        if query and score<1.08:continue
        row=dict(row,source='media',score=score)
        matches.append(row)
    if sort=='relevance':matches.sort(key=lambda r:(-r['score'],str(r.get('title','')).casefold()))
    elif sort in ('newest','oldest'):
        matches.sort(key=lambda r:str(r.get('approved_at') or r.get('created_at') or ''),
                     reverse=sort=='newest')
    elif sort=='popular':matches.sort(key=lambda r:int(r.get('download_count') or 0),reverse=True)
    elif sort in ('smallest','largest'):
        matches.sort(key=lambda r:int(r.get('file_size') or 0),reverse=sort=='largest')
    return matches[:max(1,min(int(limit),50))]


def latest(*,limit=5,db=None):
    return _rows((db or _db()).table(TABLE).select(PUBLIC).eq('status','approved')
                 .order('approved_at',desc=True).limit(max(1,min(int(limit),20))).execute())


def record_delivery(media_id, *,db=None):
    # No user identity in the downloads event table.
    d=db or _db()
    d.rpc('library_v117_record_delivery',{'p_id':canonical(media_id)}).execute()


def popular(*,days=7,db=None,limit=10):
    d=db or _db()
    after=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
    ids=_rows(d.table(DL_EVENTS).select('media_id').gte('created_at',after).limit(3000).execute())
    counts={}
    for rec in ids:
        k=rec.get('media_id');counts[k]=counts.get(k,0)+1
    if not counts:return []
    rows=candidate_rows(db=d)
    rows.sort(key=lambda r:counts.get(r['id'],0),reverse=True)
    return [dict(r,weekly_downloads=counts.get(r['id'],0)) for r in rows if counts.get(r['id'],0)][:limit]


def favorite(uid,media_id,*,db=None):
    if not get(media_id,db=db):raise ValueError('This item is unavailable')
    (db or _db()).table(FAVORITES).upsert({'user_id':int(uid),'media_id':canonical(media_id)},
                 on_conflict='user_id,media_id').execute()
    return True


def favorites(uid,*,db=None):
    d=db or _db()
    refs=_rows(d.table(FAVORITES).select('media_id').eq('user_id',int(uid))
               .order('created_at',desc=True).limit(20).execute())
    all_rows=candidate_rows(db=d,limit=500)
    by_id={r['id']:r for r in all_rows}
    return [by_id[r['media_id']] for r in refs if r.get('media_id') in by_id]


def reading(uid,media_id,status,percent=0,*,db=None):
    if status not in ('want','reading','completed'):raise ValueError('Use want, reading, completed')
    percent=int(percent)
    if not 0<=percent<=100:raise ValueError('Percent must be 0–100')
    if status=='completed':percent=100
    if not get(media_id,db=db):raise ValueError('Media unavailable')
    data={'user_id':int(uid),'media_id':canonical(media_id),'status':status,'percent':percent,
          'updated_at':datetime.now(timezone.utc).isoformat()}
    (db or _db()).table(READING).upsert(data,on_conflict='user_id,media_id').execute()
    return data


def my_reading(uid,*,db=None):
    return _rows((db or _db()).table(READING).select('media_id,status,percent,updated_at')
                 .eq('user_id',int(uid)).order('updated_at',desc=True).limit(20).execute())


def my_requests(uid,*,db=None):
    return _rows((db or _db()).table('book_library_requests').select('id,title,status,created_at')
                 .eq('user_id',int(uid)).order('created_at',desc=True).limit(20).execute())


def pending_requests(*,db=None):
    return _rows((db or _db()).table('book_library_requests').select('id,user_id,title,author,status')
                 .eq('status','pending').order('created_at').limit(15).execute())


def resolve_request(req_id,status,*,db=None):
    if status not in ('found','uploaded','rejected'):raise ValueError('Invalid request status')
    return _rows((db or _db()).table('book_library_requests').update({'status':status})
                 .eq('id',canonical(req_id)).eq('status','pending').execute())


def stats(*,db=None):
    d=db or _db()
    results={}
    for label,op in [('published',('status','approved')),('pending',('status','pending')),
                     ('hidden',('status','hidden'))]:
        response=d.table(TABLE).select('id',count='exact').eq(*op).limit(1).execute()
        results[label]=getattr(response,'count',None)
        if results[label] is None:
            results[label]=len(_rows(response))
    results['recent']=latest(limit=5,db=d)
    results['popular']=popular(db=d,limit=5)
    return results
