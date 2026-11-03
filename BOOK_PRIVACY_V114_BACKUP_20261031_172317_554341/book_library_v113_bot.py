"""V11.3: 18 public-library discovery, reading and admin workflows.
Additive handlers; all personal actions private and scoped to Telegram sender ID.
"""
from __future__ import annotations
import csv
import hashlib
import io
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from book_library_v113_store import (
    smart_search, related_books, find_duplicate, set_edition, set_description,
    series_books, update_progress, my_progress, submit_review, public_reviews,
    pending_reviews, moderate_review, challenge, my_challenges, create_collection,
    my_collections, add_to_collection, collection_books, subscribe, my_subscriptions,
    add_book_request, pending_requests, resolve_request, add_submission,
    pending_submissions, claim_submission, mark_submission, reset_submission,
    report_book, pending_reports, resolve_report, log_miss, analytics,
    isbn_metadata, queue_new_book, book_uuid, clean, VALID_REPORTS, record_metric, challenge_progress
)

log=logging.getLogger(__name__)
_lock=threading.RLock()
_pending_submissions={}
_pending_bulk={}
_recent_actions={}


def enabled():
    import book_library_bot as lib
    return lib._enabled() and lib._on('BOOK_LIBRARY_V112_ENABLED',False) and lib._on('BOOK_LIBRARY_V113_ENABLED',False)


def _lib():
    import book_library_bot as lib
    return lib


def _private(m):
    return _lib()._is_private(m)


def _admin(m):
    return _private(m) and _lib()._admin(m.from_user.id)


def _allowed(m):
    lib=_lib()
    return (enabled() and (lib._is_private(m) or (lib._is_group(m) and lib._allowed_group(m.chat.id)))
            and lib._verified(m.from_user.id))


def _limit(m, op, secs=3):
    key=(int(m.from_user.id),op)
    with _lock:
        now=time.monotonic()
        if len(_recent_actions)>1500:
            _recent_actions.clear()
        if now-_recent_actions.get(key,-1e9)<secs: return True
        _recent_actions[key]=now
        return False


def _txt(bot,m,text):
    bot.send_message(m.chat.id,str(text)[:3900])


def _arg(m):
    return _lib()._command_args(m)


def _list_books(bot,m,books,head):
    from book_library_bot import _results_markup, _short
    if not books:
        _txt(bot,m,'📚 No matching books found.')
        return
    bot.send_message(m.chat.id,head[:3500],reply_markup=_results_markup(bot,books[:10]))


def _is_private_cmd(bot,m):
    if not _allowed(m):
        _txt(bot,m,'📚 Library is not enabled here.'); return False
    if not _private(m):
        _txt(bot,m,'🔐 Open a private chat with the bot for personal reading features.');return False
    return True


def _admin_cmd(bot,m):
    if not enabled() or not _admin(m):
        _txt(bot,m,'🔒 Authorized library administrators only; use a private chat.');return False
    return True


def _mini_url():
    url=os.getenv('BOOK_LIBRARY_MINIAPP_URL','').strip()
    if not url:
        base=(os.getenv('RENDER_EXTERNAL_URL','') or os.getenv('BOOK_LIBRARY_PUBLIC_URL','')).rstrip('/')
        url=base+'/library' if base else ''
    parsed=urlparse(url)
    if parsed.scheme!='https' or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
        return None
    return url


def add_v113_menu_buttons(kb):
    if not enabled(): return
    from telebot import types
    kb.add(types.InlineKeyboardButton('🔎 Smart Search',callback_data='lib3:smart'),
           types.InlineKeyboardButton('📖 My Reading',callback_data='lib3:reading'))
    kb.add(types.InlineKeyboardButton('📋 My Collections',callback_data='lib3:collections'),
           types.InlineKeyboardButton('📩 Request a Book',callback_data='lib3:request'))
    url=_mini_url()
    if url:
        kb.add(types.InlineKeyboardButton('📚 Open Library Mini App',web_app=types.WebAppInfo(url=url)))


def _parse_parts(value,n):
    parts=[x.strip() for x in str(value).split('|')]
    if len(parts)!=n or not all(parts): raise ValueError(f'Expected {n} fields separated by |.')
    return parts


def show_smart_search(bot,chat_id,query,*,group=False):
    """Explicit /book searches use typo-tolerant matching; ordinary group text stays exact."""
    from book_library_bot import _results_markup, _short
    q=str(query or '').strip()
    if not 2<=len(q)<=100:
        if not group:bot.send_message(chat_id,'🔎 Use /book TITLE (2–100 characters).')
        return False
    try:
        books=smart_search(q,limit=5)
        try:
            record_metric('explicit_searches')
            if not books:
                log_miss(q)
                record_metric('not_found')
        except Exception: log.warning('Book search metrics unavailable')
        if not books:
            if not group:bot.send_message(chat_id,'📚 No matching books. Try /bookrequest TITLE.')
            return False
        bot.send_message(chat_id,'🔎 Books matching: '+_short(q,90),reply_markup=_results_markup(bot,books))
        return True
    except Exception:
        log.exception('Library smart search unavailable')
        if not group:bot.send_message(chat_id,'⚠️ Search currently unavailable.')
        return False


def _new_notice(bot,m,err):
    if isinstance(err,ValueError): _txt(bot,m,'⚠️ '+str(err)[:220])
    else:
        log.exception('V11.3 library action failed')
        _txt(bot,m,'⚠️ Library service is temporarily unavailable. Please try again later.')


def _safe_hash(bot,doc):
    """Optional, capped SHA-256. Can be expensive; never persist file contents."""
    if not _lib()._on('BOOK_LIBRARY_HASH_SMALL_FILES',False): return None
    maximum=max(1,min(int(os.getenv('BOOK_LIBRARY_HASH_MAX_BYTES','8388608')),8*1024*1024))
    size=int(getattr(doc,'file_size',0) or 0)
    if size<=0 or size>maximum: return None
    info=bot.get_file(doc.file_id)
    raw=bot.download_file(info.file_path)
    if len(raw)>maximum: raise ValueError('Hashing size limit exceeded.')
    return hashlib.sha256(raw).hexdigest()


def check_admin_upload(bot,m,*,isbn=None):
    """Run BEFORE copying to storage channel. Detect known duplicate without downloading file."""
    if not enabled(): return False,None,None
    doc=m.document
    identifier=str(getattr(doc,'file_unique_id','') or '') or None
    digest=_safe_hash(bot,doc)
    duplicate=find_duplicate(identifier,isbn,digest)
    if duplicate:
        _txt(bot,m,f'⚠️ Possible duplicate ({duplicate["matched_on"]}): {duplicate.get("title")}. Upload skipped. '
                'If this is a different edition, edit the existing catalog record or contact an admin.')
        return True,identifier,digest
    return False,identifier,digest


def post_admin_upload(bot,rec):
    if not enabled():return
    try:record_metric('uploads')
    except Exception:log.warning('Book upload metric unavailable')
    try:queue_new_book(rec,max_recipients=100)
    except Exception:log.exception('Library alert enqueue failed (book remains saved)')


def _read_csv(bot,m):
    doc=getattr(m,'document',None)
    if not doc or not str(getattr(doc,'file_name','')).lower().endswith('.csv'):
        raise ValueError('Upload a CSV file.')
    if int(getattr(doc,'file_size',0) or 0)>120000: raise ValueError('CSV must be 120 KB or less.')
    file=bot.get_file(doc.file_id)
    raw=bot.download_file(file.file_path)
    if len(raw)>120000: raise ValueError('CSV too large.')
    reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    required={'id','title','author','language','category','isbn'}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise ValueError('CSV requires: id,title,author,language,category,isbn')
    from book_library_v112_store import normalize_isbn
    from book_library_store import validate_metadata
    rows=[]
    for line,row in enumerate(reader,2):
        if len(rows)>=30: raise ValueError('Maximum 30 rows per import.')
        key=book_uuid(row['id'])
        title,author,language=validate_metadata(row['title'],row['author'],row['language'])
        category=clean(row['category'],60)
        isbn=normalize_isbn(row['isbn'])
        rows.append(dict(id=key,title=title,author=author,language=language,category=category,isbn=isbn))
    if not rows: raise ValueError('CSV contains no rows.')
    return rows


def register_v113_handlers(bot):
    """Called once from register_book_library_handlers; existing commands remain registered."""
    from telebot import types

    @bot.message_handler(commands=['booksmart','bookrelated','bookseries','bookinfo'])
    def discovery(m):
        if not _allowed(m): return _txt(bot,m,'📚 Library unavailable in this chat.')
        if _limit(m,'discover',2): return
        command=str(m.text or '').split()[0].split('@')[0].lower()
        val=_arg(m)
        if not val: return _txt(bot,m,'Usage: /booksmart TITLE, /bookrelated UUID, /bookseries NAME, /bookinfo UUID')
        try:
            if command=='/bookinfo':
                return _book_info(bot,m,val)
            if command=='/bookrelated':
                items=related_books(book_uuid(val)); head='📚 Related books'
            elif command=='/bookseries':
                items=series_books(clean(val,100));head='📚 Series: '+val[:80]
            else:
                items=smart_search(val,limit=5);head='🔎 Smart search: '+val[:80]
                if not items and str(m.text).startswith('/booksmart'):
                    try:log_miss(val)
                    except Exception:log.warning('Book search-miss analytics unavailable')
            _list_books(bot,m,items,head)
        except Exception as exc:_new_notice(bot,m,exc)

    @bot.message_handler(commands=['bookreading','bookprogress','bookchallenge','bookchallengecheck','bookcollections','bookcollection','bookcollectionadd','bookcollectionview'])
    def reading(m):
        if not _is_private_cmd(bot,m):return
        if _limit(m,'reading',2):return
        cmd=str(m.text).split()[0].split('@')[0].lower();raw=_arg(m)
        try:
            if cmd=='/bookreading':
                rows=my_progress(m.from_user.id)
                return _txt(bot,m,'📖 Your Reading\n'+'\n'.join(f"{r['book_id']} — {r['status']} ({r['percent']}%)" for r in rows) if rows else '📖 No reading records. Use /bookprogress UUID | reading | 20')
            if cmd=='/bookprogress':
                parts=_parse_parts(raw,3)
                value=update_progress(m.from_user.id,parts[0],parts[1].lower(),parts[2])
                return _txt(bot,m,f"✅ {value['status']} — {value['percent']}%")
            if cmd=='/bookchallenge':
                args=raw.split()
                if len(args)!=2:raise ValueError('Usage: /bookchallenge 5 30 (five books in 30 days)')
                row=challenge(m.from_user.id,*args)
                return _txt(bot,m,f"🎯 Challenge created: {row['target_books']} books in {row['days']} days.")
            if cmd=='/bookchallengecheck':
                records=my_challenges(m.from_user.id)
                lines=[f"🎯 {challenge_progress(m.from_user.id,c)}/{c['target_books']} completed · by {str(c.get('ends_at'))[:10]}" for c in records]
                return _txt(bot,m,'\n'.join(lines) if lines else 'No challenges. Start: /bookchallenge 5 30')
            if cmd=='/bookcollections':
                rows=my_collections(m.from_user.id)
                return _txt(bot,m,'📋 My collections\n'+'\n'.join(f"{r['name']} — {r['id']}" for r in rows) if rows else 'No collections. /bookcollection My Books')
            if cmd=='/bookcollection':
                row=create_collection(m.from_user.id,raw)
                return _txt(bot,m,f"✅ Collection created: {row['name']}\nID: {row['id']}")
            if cmd=='/bookcollectionadd':
                cid,bid=_parse_parts(raw,2)
                add_to_collection(m.from_user.id,cid,bid)
                return _txt(bot,m,'✅ Added to your personal collection.')
            if cmd=='/bookcollectionview':
                books=collection_books(m.from_user.id,raw)
                return _list_books(bot,m,books,'📋 My collection')
        except Exception as exc:_new_notice(bot,m,exc)

    @bot.message_handler(commands=['bookreview','bookreviews','bookalert','bookalerts','bookrequest','bookreport'])
    def community(m):
        if not _is_private_cmd(bot,m):return
        if _limit(m,'community',2):return
        cmd=str(m.text).split()[0].split('@')[0].lower();raw=_arg(m)
        try:
            if cmd=='/bookreview':
                bid,rating,text=_parse_parts(raw,3)
                submit_review(m.from_user.id,bid,rating,text)
                return _txt(bot,m,'⭐ Review submitted for administrator moderation. It is not public yet.')
            if cmd=='/bookreviews':
                items=public_reviews(raw)
                return _txt(bot,m,'⭐ Approved reviews\n'+'\n'.join(f"{r['rating']}/5 — {r['review_text'][:200]}" for r in items) if items else 'No approved reviews yet.')
            if cmd=='/bookalert':
                bits=raw.split('|')
                if len(bits)!=2:raise ValueError('Usage: /bookalert category | Psychology OR /bookalert off category | Psychology')
                kind=bits[0].strip().lower();enabled=True
                if kind.startswith('off '):enabled=False;kind=kind[4:].strip()
                subscribe(m.from_user.id,kind,bits[1].strip(),enabled=enabled)
                return _txt(bot,m,'🔔 Subscription saved.' if enabled else '🔕 Subscription removed.')
            if cmd=='/bookalerts':
                rows=my_subscriptions(m.from_user.id)
                return _txt(bot,m,'🔔 Your subscriptions\n'+'\n'.join(f"{r['kind']}: {r['term']}" for r in rows) if rows else 'No alerts. /bookalert category | Psychology')
            if cmd=='/bookrequest':
                bits=[x.strip() for x in raw.split('|',1)]
                if not bits or not bits[0]:raise ValueError('Usage: /bookrequest Title | Optional Author')
                row=add_book_request(m.from_user.id,bits[0],bits[1] if len(bits)==2 else '')
                return _txt(bot,m,'📩 Book request added for admin review. ID: '+str(row['id']))
            if cmd=='/bookreport':
                bid,kind,info=_parse_parts(raw,3)
                record=report_book(m.from_user.id,bid,kind,info)
                return _txt(bot,m,'🚩 Report received. Admin review ID: '+str(record['id']))
        except Exception as exc:_new_notice(bot,m,exc)

    @bot.message_handler(commands=['booksubmit'])
    def ask_submission(m):
        if not _is_private_cmd(bot,m):return
        with _lock:
            _pending_submissions[m.from_user.id]=time.monotonic()+180
        _txt(bot,m,'📨 Send one legally shareable PDF/EPUB/DOCX/TXT within 3 minutes with caption:\n'
             'Title | Author | Language | Permission or open-license explanation\n'
             'Files remain in a separate private review channel until an admin approves them.')

    @bot.message_handler(content_types=['document'],func=lambda m: enabled() and _private(m)
                         and _pending_submissions.get(m.from_user.id,0)>time.monotonic()
                         and not _lib()._admin(m.from_user.id))
    def student_submission(m):
        with _lock:_pending_submissions.pop(m.from_user.id,None)
        try:
            from book_library_store import format_size
            from book_library_store import validate_metadata
            parts=_parse_parts(getattr(m,'caption',''),4)
            title,author,language=validate_metadata(*parts[:3])
            rights=clean(parts[3],300)
            doc=m.document
            filename=str(getattr(doc,'file_name','') or '')
            if not filename.lower().endswith(('.pdf','.epub','.docx','.txt')):raise ValueError('Unsupported file type.')
            size=int(getattr(doc,'file_size',0) or 0)
            if size<1 or size>int(os.getenv('BOOK_LIBRARY_SUBMISSION_MAX_BYTES','20971520')):
                raise ValueError('Submission too large; default maximum 20 MB.')
            channel=int(os.getenv('BOOK_LIBRARY_REVIEW_CHANNEL_ID','0'))
            if channel>=0 or channel==int(os.getenv('BOOK_LIBRARY_CHANNEL_ID','0')):
                raise ValueError('Separate private review channel is required.')
            copied=bot.copy_message(chat_id=channel,from_chat_id=m.chat.id,message_id=m.message_id)
            try:
                row=add_submission(m.from_user.id,title=title,author=author,language=language,
                    rights=rights,channel_id=channel,message_id=copied.message_id,
                    file_name=filename,file_size=size,file_unique_id=getattr(doc,'file_unique_id',None))
            except Exception:
                try:bot.delete_message(channel,copied.message_id)
                except Exception:pass
                raise
            _txt(bot,m,'✅ Submitted for rights and content review. Not publicly available. ID: '+str(row['id']))
        except Exception as exc:_new_notice(bot,m,exc)

    @bot.message_handler(commands=['bookmeta','bookmetafill','bookedition','bookdescription','booklicense',
                                  'bookrequests','bookrequestresolve','bookreviewsadmin','bookreviewmoderate',
                                  'booksubmissions','booksubmitapprove','booksubmitreject','bookreports',
                                  'bookreportresolve','bookanalytics','bookbulk','bookbulkapply'])
    def admin(m):
        if not _admin_cmd(bot,m):return
        if _limit(m,'admin',1):return
        cmd=str(m.text).split()[0].split('@')[0].lower();raw=_arg(m)
        try:
            if cmd=='/bookmeta':
                obj=isbn_metadata(raw)
                return _txt(bot,m,'📘 Open Library metadata (review before editing):\n'+str(obj)[:2900])
            if cmd=='/bookmetafill':
                from book_library_v113_store import _db, _rows
                bid,isbn=_parse_parts(raw,2); obj=isbn_metadata(isbn)
                data={}
                if obj.get('publishers') and isinstance(obj['publishers'],list):
                    data['publisher']=str(obj['publishers'][0])[:100]
                if obj.get('cover_url'):data['cover_url']=obj['cover_url']
                if obj.get('description'):data['description']=str(obj['description'])[:1200]
                if obj.get('publish_date'):
                    years=re.findall(r'\b(?:1[4-9]\d{2}|20\d{2}|21\d{2})\b',str(obj['publish_date']))
                    if years:data['published_year']=int(years[0])
                if not data:raise ValueError('No supported metadata returned.')
                _rows(_db().table('book_library_items').update(data).eq('id',book_uuid(bid))
                      .eq('active',True).execute())
                return _txt(bot,m,'✅ Metadata imported for this existing catalog book. Check /bookpreview.')
            if cmd=='/bookedition':
                parts=_parse_parts(raw,7)
                ok=set_edition(parts[0],series=parts[1],volume=parts[2],edition=parts[3],
                               translator=parts[4],publisher=parts[5],year=parts[6])
                return _txt(bot,m,'✅ Series/edition saved.' if ok else 'Book not found.')
            if cmd=='/bookdescription':
                args=_parse_parts(raw,3)
                ok=set_description(args[0],args[1],args[2])
                return _txt(bot,m,'✅ Description/preview saved.' if ok else 'Book not found.')
            if cmd=='/booklicense':
                from book_library_v113_store import _db, _rows, RIGHTS
                key,license_type=_parse_parts(raw,2)
                if license_type not in RIGHTS:raise ValueError('Invalid license type: '+', '.join(RIGHTS))
                ok=_rows(_db().table('book_library_items').update({'license_type':license_type})
                         .eq('id',book_uuid(key)).eq('active',True).execute())
                return _txt(bot,m,'✅ Rights classification saved after admin review.' if ok else 'Book not found.')
            if cmd=='/bookrequests':
                rows=pending_requests()
                return _txt(bot,m,'📩 Book requests\n'+'\n'.join(f"{x['id']}: {x['title']} — {x.get('author') or '-'}" for x in rows) if rows else 'No pending requests.')
            if cmd=='/bookrequestresolve':
                rid,status=_parse_parts(raw,2)
                ok=resolve_request(rid,status)
                return _txt(bot,m,'✅ Request updated.' if ok else 'Request not found.')
            if cmd=='/bookreviewsadmin':
                rows=pending_reviews()
                return _txt(bot,m,'⭐ Reviews pending\n'+'\n'.join(f"{x['id']}: {x['rating']}/5 — {x['review_text'][:80]}" for x in rows) if rows else 'No pending reviews.')
            if cmd=='/bookreviewmoderate':
                rid,status=_parse_parts(raw,2)
                ok=moderate_review(rid,status)
                return _txt(bot,m,'✅ Review updated.' if ok else 'Review not found.')
            if cmd=='/booksubmissions':
                rows=pending_submissions()
                return _txt(bot,m,'📨 Submissions pending rights review\n'+'\n'.join(
                    f"{x['id']}: {x['title']}\nClaimed rights: {x['rights_statement'][:120]}" for x in rows) if rows else 'No pending submissions.')
            if cmd=='/booksubmitapprove':
                return _approve_submission(bot,m,raw)
            if cmd=='/booksubmitreject':
                ok=mark_submission(raw,'rejected')
                return _txt(bot,m,'❌ Submission rejected.' if ok else 'Submission not found.')
            if cmd=='/bookreports':
                rows=pending_reports()
                return _txt(bot,m,'🚩 Pending reports\n'+'\n'.join(f"{x['id']}: {x['kind']} — book {x['book_id']}" for x in rows) if rows else 'No pending reports.')
            if cmd=='/bookreportresolve':
                rid,status=_parse_parts(raw,2)
                ok=resolve_report(rid,status)
                return _txt(bot,m,'✅ Report updated.' if ok else 'Report not found.')
            if cmd=='/bookanalytics':
                result=analytics()
                lines=['📊 Library Analytics', 'Most downloaded:']
                lines.extend(f"{x.get('title')}: {x.get('download_count',0)}" for x in result['downloads'][:6])
                lines.append('Popular categories:')
                lines.extend(f"{x['value']}: {x['book_count']}" for x in result['categories'][:6])
                lines.append('Recent daily totals:')
                lines.extend(f"{x['stat_day']}: {x['metric']} {x['total']}" for x in result['daily'][:8])
                lines.append('Missing-search terms (explicit queries only):')
                lines.extend(f"{x['query']}: {x['occurrences']}" for x in result['misses'][:6])
                return _txt(bot,m,'\n'.join(lines))
            if cmd=='/bookbulk':
                with _lock:_pending_bulk[m.from_user.id]={'expires':time.monotonic()+180,'rows':None}
                return _txt(bot,m,'📄 Send a CSV file within 3 minutes with columns id,title,author,language,category,isbn.\n'
                            'Maximum 30 rows. The bot will preview before applying.')
            if cmd=='/bookbulkapply':
                with _lock:state=_pending_bulk.pop(m.from_user.id,None)
                if not state or state['expires']<time.monotonic() or not state['rows']:
                    raise ValueError('No valid CSV preview; restart /bookbulk.')
                from book_library_v112_store import update_metadata
                failures=[];count=0
                for row in state['rows']:
                    try:
                        if update_metadata(row['id'],title=row['title'],author=row['author'],language=row['language'],
                                           category=row['category'],isbn=row['isbn']):count+=1
                        else:failures.append(row['id'])
                    except Exception:failures.append(row['id'])
                return _txt(bot,m,f'✅ Updated {count} of {len(state["rows"])} books. Failed: '+', '.join(failures[:5]))
        except Exception as exc:_new_notice(bot,m,exc)

    @bot.message_handler(content_types=['document'],func=lambda m:enabled() and _admin(m)
                         and _pending_bulk.get(m.from_user.id,{}).get('expires',0)>time.monotonic())
    def bulk_csv(m):
        try:
            rows=_read_csv(bot,m)
            with _lock:_pending_bulk[m.from_user.id]={'expires':time.monotonic()+180,'rows':rows}
            _txt(bot,m,f'📄 CSV preview: {len(rows)} metadata updates. Sample titles:\n'+
                 '\n'.join(x['title'] for x in rows[:5])+ '\nApply with /bookbulkapply within 3 minutes.')
        except Exception as exc:_new_notice(bot,m,exc)

    @bot.callback_query_handler(func=lambda c:str(getattr(c,'data','')).startswith('lib3:'))
    def menu_callbacks(c):
        m=getattr(c,'message',None)
        if not m or not _allowed(_callback_message(m,c.from_user)) or not _private(m) or m.chat.id!=c.from_user.id:
            bot.answer_callback_query(c.id,'Open the library privately.',show_alert=True);return
        action=str(c.data).split(':',1)[-1]
        bot.answer_callback_query(c.id)
        info={'smart':'🔎 Use /booksmart BOOK TITLE to search with spelling tolerance.',
              'reading':'📖 /bookreading lists progress; /bookprogress UUID | reading | 30 updates it.',
              'collections':'📋 /bookcollections to view, /bookcollection NAME to create.',
              'request':'📩 /bookrequest BOOK TITLE | Author to request a missing book.'}
        bot.send_message(m.chat.id,info.get(action,'📚 Open /bookbrowse'))

    @bot.inline_handler(func=lambda q:enabled() and len(str(getattr(q,'query','')).strip())>=2)
    def library_inline(q):
        try:
            lib=_lib()
            if not lib._verified(q.from_user.id):return bot.answer_inline_query(q.id,[],cache_time=5,is_personal=True)
            books=smart_search(q.query,limit=8)
            username=lib._bot_username(bot)
            results=[]
            for item in books:
                identifier=uuid.UUID(str(item['id'])).hex
                text=(f"📚 {item.get('title')}\n✍️ {item.get('author')}\n"
                      f"Get book privately: https://t.me/{username}?start=book_{identifier}")
                results.append(types.InlineQueryResultArticle(
                    id=identifier,title=str(item.get('title',''))[:100],
                    description=(str(item.get('author',''))+' · '+str(item.get('language','')))[:120],
                    input_message_content=types.InputTextMessageContent(text)))
            bot.answer_inline_query(q.id,results,cache_time=10,is_personal=True)
        except Exception:
            log.exception('Book inline query failed')
            try:bot.answer_inline_query(q.id,[],cache_time=5,is_personal=True)
            except Exception:pass


def _callback_message(m,user):
    from types import SimpleNamespace
    return SimpleNamespace(chat=m.chat,from_user=user)


def _approve_submission(bot,m,raw):
    """Only admin may call after independently reviewing redistribution rights."""
    from book_library_store import add_book
    if not raw.endswith(' RIGHTS_CHECKED'):
        raise ValueError('Usage: /booksubmitapprove UUID RIGHTS_CHECKED — only after reviewing legal permission.')
    key=book_uuid(raw[:-15].strip())
    item=claim_submission(key)
    if not item:
        raise ValueError('Submission already reviewed or unavailable.')
    storage_mid=None
    published=False
    try:
        if find_duplicate(item.get('file_unique_id')):
            raise ValueError('Duplicate file already exists. Reject or resolve manually.')
        channel=int(os.getenv('BOOK_LIBRARY_CHANNEL_ID','0'))
        if channel>=0:raise ValueError('Storage channel not configured.')
        copied=bot.copy_message(chat_id=channel,from_chat_id=int(item['review_channel_id']),
                                message_id=int(item['review_message_id']))
        storage_mid=int(copied.message_id)
        record=add_book(title=item['title'],author=item['author'],language=item['language'],
                        channel_id=channel,message_id=storage_mid,file_name=item['file_name'],
                        file_size=item['file_size'],uploaded_by=m.from_user.id,
                        category='Community Submissions',
                        file_unique_id=item.get('file_unique_id'))
        published=True
        if not mark_submission(key,'approved'):
            raise RuntimeError('Published, but review status did not update; reconcile manually.')
        post_admin_upload(bot,record)
        _txt(bot,m,'✅ Approved and published in library: '+str(record['id']))
    except Exception:
        if not published:
            if storage_mid:
                try:bot.delete_message(int(os.getenv('BOOK_LIBRARY_CHANNEL_ID')),storage_mid)
                except Exception:pass
            reset_submission(key)
        else:
            log.error('Submission published, review status needs manual reconciliation')
        raise


def _book_info(bot,m,value):
    """Descriptions, licensed previews, series metadata and moderated reviews."""
    from book_library_v113_store import _db, _rows, SAFE_FIELDS
    key=book_uuid(value)
    rows=_rows(_db().table('book_library_items').select(SAFE_FIELDS)
               .eq('id',key).eq('active',True).limit(1).execute())
    if not rows:return _txt(bot,m,'📚 Book unavailable.')
    b=rows[0]
    info=[f"📖 {b.get('title')}",f"✍️ {b.get('author')}",
          f"🌐 {b.get('language')} · {b.get('category')}"]
    if b.get('series_name'):info.append(f"📚 {b['series_name']} · Volume {b.get('volume_number') or '?'}")
    if b.get('edition'):info.append('Edition: '+str(b['edition']))
    if b.get('publisher'):info.append('Publisher: '+str(b['publisher']))
    if b.get('description'):info.append('About: '+str(b['description'])[:700])
    if b.get('preview_text'):info.append('📄 Authorized sample:\n'+str(b['preview_text'])[:700])
    reviews=public_reviews(key)
    if reviews:info.append('⭐ Approved reviews:\n'+'\n'.join(
        f"{r['rating']}/5 · {r['review_text'][:100]}" for r in reviews[:3]))
    _txt(bot,m,'\n'.join(info))
