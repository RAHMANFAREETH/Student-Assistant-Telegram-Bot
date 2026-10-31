"""V11.3 advanced library data layer. All user IDs derive from authenticated Telegram updates.
Only the existing server-side service-role Supabase client may call these methods.
"""
from __future__ import annotations
import difflib
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
import unicodedata
import uuid
import urllib.request
from collections import Counter
from functools import lru_cache

from book_library_v112_store import _db, _rows, uid, book_uuid, get_details, normalize_isbn, simple_text
from book_library_store import validate_metadata

BOOKS = 'book_library_items'
SAFE_FIELDS = 'id,title,author,language,category,isbn,file_size,cover_file_id,added_at,download_count,series_name,volume_number,edition,translator,publisher,published_year,description,preview_text,cover_url,license_type'
VALID_STATUS = ('want', 'reading', 'completed')
VALID_REPORTS = ('broken_file','metadata','inappropriate','copyright')
RIGHTS = ('public_domain','cc_by','cc_by_sa','cc0','permission','other')


def clean(value, limit=160, *, optional=False):
    val = ' '.join(str(value or '').split())
    if optional and not val:
        return ''
    if not 2 <= len(val) <= limit or any(c in val for c in '<>\x00|'):
        raise ValueError(f'Use 2–{limit} plain-text characters.')
    return val


def norm(value):
    text = unicodedata.normalize('NFKC', str(value or '')).casefold()
    # Arabic optional harakat can be ignored, but Tamil/Sinhala vowel signs MUST stay.
    text = ''.join(c for c in text if not (
        unicodedata.category(c) == 'Cf' or
        0x0610 <= ord(c) <= 0x061A or
        0x064B <= ord(c) <= 0x065F or
        ord(c) == 0x0670 or
        0x06D6 <= ord(c) <= 0x06ED))
    text = ''.join(c if (c.isspace() or unicodedata.category(c)[0] in ('L','M','N')) else ' ' for c in text)
    return ' '.join(text.split())


def fuzzy_rank(query, books, limit=5):
    """Unicode-aware bounded candidate reranker; query strings are never used in SQL templates."""
    q = norm(query)
    if len(q) < 2: return []
    scored=[]
    for row in books[:500]:
        if not row.get('active', True): continue
        title=norm(row.get('title'))
        alt=norm(row.get('author'))
        merged=title+' '+alt
        score=1.0 if q in merged else max(difflib.SequenceMatcher(None,q,title).ratio(),
                                          difflib.SequenceMatcher(None,q,alt).ratio()*0.82)
        if score >= 0.42:
            scored.append((score,row))
    scored.sort(key=lambda item: (-item[0], norm(item[1].get('title'))))
    return [item for _,item in scored[:max(1,min(limit,10))]]


def smart_search(query, *, limit=5, db=None):
    from book_library_v112_store import browse_books
    q=clean(query,100)
    d=db or _db()
    exact,_=browse_books(query=q,page_size=min(limit,8),db=d)
    if len(exact)>=limit: return exact[:limit]
    # Bounded candidate retrieval for spelling suggestions; avoids full table downloads.
    rows=_rows(d.table(BOOKS).select(SAFE_FIELDS+',active').eq('active',True)
               .order('added_at',desc=True).limit(500).execute())
    known={str(row.get('id')) for row in exact}
    return (exact + [r for r in fuzzy_rank(q,rows,limit=limit) if str(r.get('id')) not in known])[:limit]


def related_books(book_id, *, db=None, limit=5):
    d=db or _db()
    found=_rows(d.table(BOOKS).select(SAFE_FIELDS).eq('id',book_uuid(book_id))
                .eq('active',True).limit(1).execute())
    if not found: return []
    item=found[0]
    rows=_rows(d.table(BOOKS).select(SAFE_FIELDS+',active').eq('active',True)
               .limit(250).execute())
    ranked=[]
    for other in rows:
        if str(other['id'])==str(item['id']): continue
        score=(4 if norm(other.get('category'))==norm(item.get('category')) else 0)
        score+=(3 if norm(other.get('author'))==norm(item.get('author')) else 0)
        score+=(2 if item.get('series_name') and norm(other.get('series_name'))==norm(item.get('series_name')) else 0)
        score+=(1 if norm(other.get('language'))==norm(item.get('language')) else 0)
        if score: ranked.append((score,other))
    return [o for _,o in sorted(ranked,key=lambda x:-x[0])[:limit]]


def find_duplicate(file_unique_id=None,isbn=None,sha256=None, *, db=None):
    d=db or _db()
    for key,value in [('file_unique_id',file_unique_id),('sha256',sha256),('isbn',isbn)]:
        if value:
            rows=_rows(d.table(BOOKS).select('id,title').eq('active',True)
                       .eq(key,value).limit(1).execute())
            if rows: return dict(rows[0],matched_on=key)
    return None


def set_edition(book_id, *, series=None, volume=None, edition=None,
                translator=None, publisher=None, year=None, db=None):
    data={}
    if series is not None: data['series_name']=clean(series,100,optional=True) or None
    if volume is not None:
        value=int(volume)
        if not 1<=value<=500: raise ValueError('Volume must be 1–500.')
        data['volume_number']=value
    if edition is not None: data['edition']=clean(edition,100,optional=True) or None
    if translator is not None: data['translator']=clean(translator,100,optional=True) or None
    if publisher is not None: data['publisher']=clean(publisher,100,optional=True) or None
    if year is not None:
        val=int(year)
        if not 1400<=val<=2200: raise ValueError('Invalid publication year.')
        data['published_year']=val
    if not data: raise ValueError('No metadata supplied.')
    return bool(_rows((db or _db()).table(BOOKS).update(data).eq('id',book_uuid(book_id))
                      .eq('active',True).execute()))


def set_description(book_id, description, preview='', license_type=None, db=None):
    desc=clean(description,1600)
    if len(str(preview or ''))>1800: raise ValueError('Preview is too long.')
    data={'description':desc,'preview_text':str(preview or '').strip() or None}
    if license_type:
        if license_type not in RIGHTS: raise ValueError('Invalid rights type.')
        data['license_type']=license_type
    return bool(_rows((db or _db()).table(BOOKS).update(data).eq('id',book_uuid(book_id))
                      .eq('active',True).execute()))


def series_books(series, *, db=None):
    return _rows((db or _db()).table(BOOKS).select(SAFE_FIELDS).eq('active',True)
                 .ilike('series_name',str(series or '').replace('%','').replace('_','')[:80])
                 .order('volume_number').limit(50).execute())


def update_progress(user_id, book_id, status, percent=0, *, db=None):
    if status not in VALID_STATUS: raise ValueError('Use want, reading, or completed.')
    percent=int(percent)
    if not 0<=percent<=100: raise ValueError('Progress must be 0–100%.')
    if status=='completed': percent=100
    if not get_details(book_id,db=db): raise ValueError('Book is not available.')
    value={'user_id':uid(user_id),'book_id':book_uuid(book_id),'status':status,'percent':percent}
    (db or _db()).table('book_library_reading_progress').upsert(value,on_conflict='user_id,book_id').execute()
    return value


def my_progress(user_id, *, db=None, limit=20):
    return _rows((db or _db()).table('book_library_reading_progress').select('book_id,status,percent,updated_at')
                 .eq('user_id',uid(user_id)).order('updated_at',desc=True).limit(limit).execute())


def submit_review(user_id,book_id,rating,text, *, db=None):
    rating=int(rating)
    if not 1<=rating<=5: raise ValueError('Rating must be 1–5.')
    review=clean(text,500)
    if not get_details(book_id,db=db): raise ValueError('Book unavailable.')
    (db or _db()).table('book_library_reviews').upsert(dict(user_id=uid(user_id),
        book_id=book_uuid(book_id),rating=rating,review_text=review,status='pending'),
        on_conflict='user_id,book_id').execute()
    return True


def public_reviews(book_id, *, db=None):
    return _rows((db or _db()).table('book_library_reviews').select('rating,review_text,created_at')
                 .eq('book_id',book_uuid(book_id)).eq('status','approved')
                 .order('created_at',desc=True).limit(10).execute())


def pending_reviews(*, db=None, limit=10):
    return _rows((db or _db()).table('book_library_reviews').select('id,book_id,rating,review_text,created_at')
                 .eq('status','pending').order('created_at').limit(limit).execute())


def moderate_review(review_id, status, *, db=None):
    if status not in ('approved','rejected'): raise ValueError('Invalid action.')
    return bool(_rows((db or _db()).table('book_library_reviews').update({'status':status})
                      .eq('id',book_uuid(review_id)).eq('status','pending').execute()))


def challenge(user_id,target=5,days=30,*,db=None):
    target=int(target); days=int(days)
    if not 1<=target<=100 or not 1<=days<=365: raise ValueError('Challenge range: 1–100 books, 1–365 days.')
    d=db or _db()
    ends=(datetime.now(timezone.utc)+timedelta(days=days)).isoformat()
    return _rows(d.table('book_library_challenges').insert(dict(user_id=uid(user_id),
                 target_books=target,days=days,ends_at=ends)).execute())[0]


def my_challenges(user_id,*,db=None):
    return _rows((db or _db()).table('book_library_challenges').select('*').eq('user_id',uid(user_id))
                 .order('created_at',desc=True).limit(5).execute())


def challenge_progress(user_id, record, *, db=None):
    d=db or _db()
    rows=_rows(d.table('book_library_reading_progress').select('book_id').eq('user_id',uid(user_id))
               .eq('status','completed').gte('updated_at',record['created_at'])
               .lte('updated_at',record['ends_at']).limit(100).execute())
    return len(rows)


def create_collection(user_id,name,*,db=None):
    name=clean(name,80)
    return _rows((db or _db()).table('book_library_collections').insert(
        {'user_id':uid(user_id),'name':name}).execute())[0]


def my_collections(user_id, *, db=None):
    return _rows((db or _db()).table('book_library_collections').select('id,name,created_at')
                 .eq('user_id',uid(user_id)).order('created_at',desc=True).limit(20).execute())


def add_to_collection(user_id,collection_id,book_id, *, db=None):
    d=db or _db(); user_id=uid(user_id)
    found=_rows(d.table('book_library_collections').select('id').eq('id',book_uuid(collection_id))
               .eq('user_id',user_id).limit(1).execute())
    if not found: raise ValueError('Collection not found.')
    if not get_details(book_id,db=d): raise ValueError('Book not found.')
    d.table('book_library_collection_items').upsert({'collection_id':book_uuid(collection_id),
       'book_id':book_uuid(book_id)},on_conflict='collection_id,book_id').execute()
    return True


def collection_books(user_id,collection_id,*,db=None):
    d=db or _db()
    found=_rows(d.table('book_library_collections').select('id').eq('id',book_uuid(collection_id))
               .eq('user_id',uid(user_id)).limit(1).execute())
    if not found: raise ValueError('Collection not found.')
    items=_rows(d.table('book_library_collection_items').select('book_id')
                .eq('collection_id',book_uuid(collection_id)).limit(100).execute())
    return [row for x in items if (row:=get_details(x['book_id'],db=d))]


def subscribe(user_id,kind,term,enabled=True,*,db=None):
    if kind not in ('category','author','challenge'): raise ValueError('Invalid subscription type.')
    term=clean(term,100)
    d=db or _db(); user_id=uid(user_id)
    if enabled:
        d.table('book_library_subscriptions').upsert({'user_id':user_id,'kind':kind,
            'term':term,'enabled':True},on_conflict='user_id,kind,term').execute()
    else:
        (d.table('book_library_subscriptions').delete().eq('user_id',user_id)
         .eq('kind',kind).eq('term',term).execute())
    return enabled


def my_subscriptions(user_id,*,db=None):
    return _rows((db or _db()).table('book_library_subscriptions').select('kind,term,enabled')
                 .eq('user_id',uid(user_id)).eq('enabled',True).limit(25).execute())


def add_book_request(user_id,title,author='', *, db=None):
    d=db or _db(); user_id=uid(user_id)
    title=clean(title,160); author=clean(author,120,optional=True)
    # Server-side count, plus SQL unique constraint by active request per title/user.
    items=_rows(d.table('book_library_requests').select('id').eq('user_id',user_id)
                .eq('status','pending').limit(6).execute())
    if len(items)>=5: raise ValueError('Limit: five open requests per person.')
    return _rows(d.table('book_library_requests').insert({'user_id':user_id,'title':title,
        'author':author,'status':'pending'}).execute())[0]


def pending_requests(*,db=None):
    return _rows((db or _db()).table('book_library_requests').select('id,title,author,created_at')
                 .eq('status','pending').order('created_at').limit(20).execute())


def resolve_request(request_id,status, *, db=None):
    if status not in ('fulfilled','rejected'): raise ValueError('Invalid status.')
    return bool(_rows((db or _db()).table('book_library_requests').update({'status':status})
                      .eq('id',book_uuid(request_id)).eq('status','pending').execute()))


def add_submission(user_id, *, title,author,language,rights,channel_id,message_id,
                   file_name,file_size,file_unique_id=None, db=None):
    title,author,language=validate_metadata(title,author,language)
    rights=clean(rights,300)
    d=db or _db(); user_id=uid(user_id)
    pending=_rows(d.table('book_library_submissions').select('id').eq('user_id',user_id)
                  .eq('status','pending').limit(4).execute())
    if len(pending)>=3: raise ValueError('Maximum three pending submissions.')
    return _rows(d.table('book_library_submissions').insert(dict(user_id=user_id,title=title,
        author=author,language=language,rights_statement=rights,review_channel_id=int(channel_id),
        review_message_id=int(message_id),file_name=str(file_name)[:255],
        file_size=int(file_size),file_unique_id=str(file_unique_id or '')[:200],
        status='pending')).execute())[0]


def pending_submissions(*,db=None):
    return _rows((db or _db()).table('book_library_submissions').select('*')
                 .eq('status','pending').order('created_at').limit(20).execute())


def mark_submission(submission_id,status, *, db=None):
    if status not in ('approved','rejected'): raise ValueError('Invalid review decision.')
    return bool(_rows((db or _db()).table('book_library_submissions').update({'status':status})
                      .eq('id',book_uuid(submission_id)).eq('status', 'processing' if status=='approved' else 'pending').execute()))


def report_book(user_id,book_id,kind,description='', *, db=None):
    if kind not in VALID_REPORTS: raise ValueError('Report type must be broken_file, metadata, inappropriate or copyright.')
    if not get_details(book_id,db=db): raise ValueError('Book unavailable.')
    return _rows((db or _db()).table('book_library_reports').insert({
       'user_id':uid(user_id),'book_id':book_uuid(book_id),'kind':kind,
       'description':clean(description,300,optional=True),'status':'pending'}).execute())[0]


def pending_reports(*,db=None):
    return _rows((db or _db()).table('book_library_reports').select('id,book_id,kind,description,created_at')
                 .eq('status','pending').order('created_at').limit(20).execute())


def resolve_report(report_id,status,*,db=None):
    if status not in ('resolved','dismissed'): raise ValueError('Invalid status.')
    return bool(_rows((db or _db()).table('book_library_reports').update({'status':status})
                      .eq('id',book_uuid(report_id)).eq('status','pending').execute()))


def log_miss(query, *,db=None):
    # Only explicit /book command queries (never ordinary group conversations) are aggregated.
    q=clean(query,100)
    (db or _db()).rpc('book_library_v113_search_miss',{'p_query':norm(q)[:100]}).execute()


def analytics(*,db=None):
    d=db or _db()
    by_category=_rows(d.rpc('book_library_v112_facets',{'p_kind':'category'}).execute())
    misses=_rows(d.table('book_library_search_misses').select('query,occurrences')
                 .order('occurrences',desc=True).limit(10).execute())
    top=_rows(d.table(BOOKS).select('title,download_count').eq('active',True)
              .order('download_count',desc=True).limit(10).execute())
    daily=_rows(d.table('book_library_daily_stats').select('stat_day,metric,total')
                .order('stat_day',desc=True).limit(30).execute())
    return dict(categories=by_category[:10],misses=misses,downloads=top,daily=daily)


_metadata_cache={}
def isbn_metadata(isbn,*,opener=None,now=None):
    """Admin-triggered metadata lookup only; strictly fixed HTTPS host, bounded response."""
    isbn=normalize_isbn(isbn)
    if not isbn: raise ValueError('Provide a valid ISBN.')
    now=time.monotonic() if now is None else now
    if isbn in _metadata_cache and _metadata_cache[isbn][0]>now:
        return _metadata_cache[isbn][1]
    url='https://openlibrary.org/isbn/'+isbn+'.json'
    req=urllib.request.Request(url,headers={'User-Agent':'StudentAssistantLibrary/11.3 (educational metadata lookup)'})
    fetch=opener or urllib.request.urlopen
    with fetch(req,timeout=6) as response:
        raw=response.read(100001)
    if len(raw)>100000: raise ValueError('Metadata response too large.')
    data=json.loads(raw.decode('utf-8'))
    if not isinstance(data,dict): raise ValueError('Unexpected metadata response.')
    result={k:data.get(k) for k in ('title','publish_date','number_of_pages','publishers','covers','description')}
    if isinstance(result.get('description'),dict): result['description']=result['description'].get('value','')
    cover=result.get('covers')
    if isinstance(cover,list) and cover and isinstance(cover[0],int):
        result['cover_url']=f'https://covers.openlibrary.org/b/id/{cover[0]}-M.jpg'
    _metadata_cache[isbn]=(now+3600,result)
    if len(_metadata_cache)>200: _metadata_cache.clear()
    return result


def claim_submission(submission_id,*,db=None):
    rows=_rows((db or _db()).rpc('book_library_v113_claim_submission',
                               {'p_id':book_uuid(submission_id)}).execute())
    return rows[0] if rows else None


def reset_submission(submission_id,*,db=None):
    (db or _db()).table('book_library_submissions').update({'status':'pending'}).eq(
       'id',book_uuid(submission_id)).eq('status','processing').execute()


def queue_new_book(book,*,db=None,max_recipients=100):
    """Enqueue opt-in notifications only; never send while handling document upload."""
    d=db or _db(); bid=book_uuid(book['id']); count=0
    for kind,value in (('category',book.get('category')),('author',book.get('author'))):
        if not value: continue
        subs=_rows(d.table('book_library_subscriptions').select('user_id').eq('enabled',True)
                   .eq('kind',kind).ilike('term',str(value).replace('%','').replace('_',''))
                   .limit(max_recipients).execute())
        for sub in subs:
            if count>=max_recipients: return count
            user=uid(sub['user_id'])
            body='📚 New library book: '+str(book.get('title',''))[:120]+'\nOpen the bot and search for the title.'
            try:
                d.table('book_library_notifications').upsert({
                    'user_id':user,'body':body,'kind':'new_book',
                    'dedupe_key':f'newbook:{user}:{bid}'},on_conflict='dedupe_key').execute()
                count+=1
            except Exception:
                continue
    return count


def queue_challenge_reminders(*,db=None,max_users=100,now=None):
    d=db or _db();now=now or datetime.now(timezone.utc)
    rows=_rows(d.table('book_library_subscriptions').select('user_id').eq('enabled',True)
               .eq('kind','challenge').limit(max_users).execute())
    count=0
    for sub in rows:
        user=uid(sub['user_id'])
        active=_rows(d.table('book_library_challenges').select('id').eq('user_id',user)
                     .gte('ends_at',now.isoformat()).limit(1).execute())
        if not active: continue
        try:
            d.table('book_library_notifications').upsert({
                'user_id':user,'body':'📖 Reading challenge reminder: open /bookchallengecheck for your progress.',
                'kind':'challenge','dedupe_key':f'challenge:{user}:{now.date().isoformat()}'},
                on_conflict='dedupe_key').execute()
            count+=1
        except Exception:
            continue
    return count


def claim_notifications(*,db=None,limit=10):
    return _rows((db or _db()).rpc('book_library_v113_claim_notifications',
                                 {'p_limit':max(1,min(int(limit),20))}).execute())


def finish_notification(notice_id,ok,*,db=None):
    data={'status':'sent' if ok else 'failed'}
    if ok: data['sent_at']=datetime.now(timezone.utc).isoformat()
    (db or _db()).table('book_library_notifications').update(data).eq('id',book_uuid(notice_id)).execute()


def record_metric(metric,*,db=None):
    if metric not in ('deliveries','uploads','explicit_searches','not_found'):
        raise ValueError('Invalid metric.')
    (db or _db()).rpc('book_library_v113_metric',{'p_metric':metric}).execute()
