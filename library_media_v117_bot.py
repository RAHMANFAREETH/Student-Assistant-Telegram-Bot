"""V11.7 all-in-one Media Library and administrator panel.

All personal actions are private; group results are temporary public *links* only.
Existing V11.1–V11.6.1 handlers remain intact, with three small, opt-in hooks.
"""
from __future__ import annotations
import io
import logging
import os
import re
import threading
import time
import uuid
import zipfile
from pathlib import PurePosixPath
from urllib.parse import quote

import library_media_v117_store as st
import library_media_v117_processing as processing

LOG=logging.getLogger(__name__)
_LOCK=threading.RLock()
_STATES={}
_MAX_STATES=2000


def enabled():
    import book_library_bot as books
    return st.enabled() and books._enabled()


def private(m):
    return getattr(getattr(m,'chat',None),'type',None)=='private'


def admin(m):
    import book_library_bot as books
    return private(m) and bool(getattr(m,'from_user',None)) and books._admin(m.from_user.id)


def _message(bot,chat_id,text,**kwargs):
    return bot.send_message(chat_id,str(text)[:3990],**kwargs)


def _fail(bot,m,exc):
    if isinstance(exc,ValueError):
        _message(bot,m.chat.id,'⚠️ '+str(exc)[:500])
    else:
        LOG.exception('V11.7 library operation failed')
        _message(bot,m.chat.id,'⚠️ Could not complete the action. Check the bot service and library migration.')


def _username(bot):
    from book_library_bot import _bot_username
    return _bot_username(bot)


def _keyboard():
    from telebot import types
    return types.InlineKeyboardMarkup(row_width=1)


def _button(text,*,url=None,data=None):
    from telebot import types
    if url:return types.InlineKeyboardButton(text,url=url)
    return types.InlineKeyboardButton(text,callback_data=data)


def _book_rows(query,*,limit=8):
    from book_library_v113_store import smart_search
    if not query:
        from book_library_store import latest_books
        rows=latest_books(limit=limit)
    else:
        rows=smart_search(query,limit=limit)
    return [dict(r,source='book',media_kind='pdf',score=st.rank(r,query),
                 created_at=r.get('added_at')) for r in rows]


def _legacy_filtered(rows,filters):
    output=[]
    for row in rows:
        if filters.get('kind') and filters['kind']!='pdf':continue
        if any(st.normalize(val) not in st.normalize(row.get(key)) for key,val in
               (('author',filters.get('author')),('language',filters.get('language')),
                ('category',filters.get('category'))) if val):continue
        size=int(row.get('file_size') or 0)
        if size<filters.get('min_bytes',0):continue
        if filters.get('max_bytes') is not None and size>filters['max_bytes']:continue
        output.append(row)
    return output


def parse_search_query(raw):
    """In-group filters e.g. /book Arabic type:image lang:Tamil sort:newest."""
    tokens=str(raw or '').strip().split()
    filters={}
    terms=[]
    for word in tokens:
        if ':' not in word:
            terms.append(word);continue
        field,value=word.split(':',1)
        key={'type':'kind','lang':'language','author':'author','cat':'category',
             'sort':'sort','min_kb':'min_bytes','max_kb':'max_bytes'}.get(field.lower())
        if not key:terms.append(word);continue
        if key in ('min_bytes','max_bytes'):
            try:filters[key]=max(0,min(500000000,int(value)*1024))
            except ValueError:raise ValueError('Size filters use numbers, e.g. min_kb:100')
        else:filters[key]=value.lower() if key in ('kind','sort') else value
    if filters.get('kind') and filters['kind'] not in st.ALLOWED_TYPES:
        raise ValueError('Unknown file type')
    if filters.get('sort','relevance') not in ('relevance','newest','oldest','popular','smallest','largest'):
        raise ValueError('Unknown sort mode')
    query=' '.join(terms).strip()
    if query and not 2<=len(query)<=100:raise ValueError('Search must be 2–100 characters')
    return query,filters


def union_search(raw,*,limit=8):
    query,filt=parse_search_query(raw)
    try:
        current=st.search(query,**filt,limit=max(limit,12))
    except Exception:
        LOG.exception('Media catalog lookup unavailable')
        raise
    old=_legacy_filtered(_book_rows(query,limit=min(10,limit)),filt)
    rows=current+old
    sort=filt.get('sort','relevance')
    if sort=='relevance':rows.sort(key=lambda x:(-x.get('score',0),-int(x.get('download_count') or 0)))
    elif sort in ('newest','oldest'):
        rows.sort(key=lambda x:str(x.get('approved_at') or x.get('created_at') or ''),
                  reverse=sort=='newest')
    elif sort=='popular':rows.sort(key=lambda x:int(x.get('download_count') or 0),reverse=True)
    elif sort in ('smallest','largest'):
        rows.sort(key=lambda x:int(x.get('file_size') or 0),reverse=sort=='largest')
    return rows[:limit]


def _link(bot,row):
    bid=uuid.UUID(str(row['id'])).hex
    prefix='media' if row.get('source')=='media' or row.get('media_kind')!='pdf' and row.get('source')!='book' else 'book'
    return f'https://t.me/{quote(_username(bot))}?start={prefix}_{bid}'


def _result_label(row):
    """Show language and size without truncating either edition identifier."""
    from book_library_store import format_size
    badge=st.BADGES.get(row.get('media_kind','pdf'),'📦')
    language=' '.join(str(row.get('language') or 'Unknown').split())[:15]
    kind=str(row.get('media_kind') or 'pdf').upper()[:6]
    size=format_size(row['file_size']) if row.get('file_size') else ''
    prefix=f'{badge} {language} · '
    suffix=f' · {kind}' + (f' · {size}' if size else '')
    available=max(0,63-len(prefix)-len(suffix))
    title=' '.join(str(row.get('title') or 'Untitled').split())
    if len(title)>available:
        title=title[:max(1,available-1)]+'…' if available>1 else ''
    return (prefix+title+suffix)[:63]


def _markup(bot,rows):
    kb=_keyboard()
    for r in rows:
        kb.add(_button(_result_label(r),url=_link(bot,r)))
    return kb


def _send_results(bot,chat_id,text,items,*,group=False):
    markup=_markup(bot,items)
    # Telegram has no native thumbnails alongside each inline button; show the
    # first item's thumbnail only. Each individual deep-link gets its own preview.
    if group and os.getenv('LIBRARY_MEDIA_GROUP_THUMBNAILS','true').lower() in ('1','true','yes','on'):
        cover=items[0].get('preview_file_id') or items[0].get('cover_file_id')
        if cover:
            try:
                sent=bot.send_photo(chat_id,cover,caption=text[:1000],reply_markup=markup)
                # V11.5 wraps send_message, not send_photo. Queue this explicitly.
                if getattr(sent,'message_id',None):
                    from group_ui_v115 import _remember
                    _remember(bot,chat_id,sent.message_id,kind='book_links')
                return sent
            except Exception:LOG.warning('Group thumbnail unavailable; falling back to text results')
    return _message(bot,chat_id,text,reply_markup=markup)


# V11.8.6 user-visible search progress and zero-results feedback.
def _remember_search_status(bot, chat_id, sent, *, group):
    if group and getattr(sent, 'message_id', None):
        try:
            from group_ui_v115 import _remember
            _remember(bot, chat_id, sent.message_id, kind='book_links')
        except Exception:
            LOG.warning('Cannot queue search message cleanup', exc_info=True)


def _searching_message(bot, chat_id, query, *, group):
    try:
        sent=_message(bot, chat_id,
            '🔎 SEARCHING FOR FILES\n'
            f'📚 {query[:100]}\n'
            '⏳ Checking the library catalog…'
            + ('\nThis message auto-deletes after 5 minutes.' if group else ''))
    except Exception:
        LOG.warning('Search progress message could not be sent', exc_info=True)
        return None
    _remember_search_status(bot, chat_id, sent, group=group)
    return sent


def _replace_search_status(bot, chat_id, status, text, *, group, markup=None):
    """Edit progress in place; if unsupported, send final and remove progress."""
    mid=getattr(status, 'message_id', None)
    editor=getattr(bot, "edit_message_text", None)  # V11.8.6.1
    if mid is not None and callable(editor):
        try:
            updated=editor(text, chat_id=chat_id, message_id=mid,
                           reply_markup=markup)
            if updated is not False:
                return status
        except Exception:
            LOG.warning('Cannot edit search status; using a new message', exc_info=True)
    try:
        sent=_message(bot, chat_id, text, reply_markup=markup)
    except Exception:
        LOG.exception('Could not send search feedback')
        return False
    _remember_search_status(bot, chat_id, sent, group=group)
    if mid is not None:
        try: bot.delete_message(chat_id, mid)
        except Exception: LOG.debug('Search progress cleanup unavailable')
    return sent


def _no_search_results_keyboard(query):
    from urllib.parse import quote_plus
    kb=_keyboard()
    # Spelling lookup only: no third-party downloading or file forwarding.
    kb.add(_button('🔎 Check spelling on Google',
                   url='https://www.google.com/search?q='+quote_plus(query[:100])))
    return kb


def unified_search(bot,chat_id,query,group=False,requester_id=None):
    if not enabled():return None
    q=str(query or '').strip()
    if not q or len(q)>180:
        return _message(bot,chat_id,'🔎 Example: /book Arabic grammar type:image lang:Tamil')
    try:
        parse_search_query(q)
    except ValueError as exc:
        return _message(bot,chat_id,'⚠️ '+str(exc)[:250])
    status=_searching_message(bot,chat_id,q,group=group)
    try:
        items=union_search(q,limit=30)
        if not items:
            note=('😕 NO FILES FOUND\n'
                  f'🔎 Search: {q[:100]}\n\n'
                  'Please check your spelling or try a shorter title, author, or another language.\n'
                  '📚 Example: /book Psychology\n'
                  '💌 You can request a missing book using /bookrequest TITLE in private.'
                  + ('\n⏳ This result auto-deletes after 5 minutes.' if group else ''))
            return _replace_search_status(bot,chat_id,status,note,group=group,
                                          markup=_no_search_results_keyboard(q))
        heading=('📚 Library results: '+q[:100]+'\n'
                 '📄 PDFs · 🖼️ Images · 🎧 Audio · 🎥 Video · 📦 ZIP\n'
                 '📩 Tap an item to preview it privately.'
                 + ('\n⏳ Auto-delete after 5 minutes.' if group else ''))
        if group and requester_id is None:
            # Preserve old URL-only keyboard when requester cannot be identified.
            result=_send_results(bot,chat_id,heading,items,group=group)
            if status is not None and getattr(status,'message_id',None):
                try: bot.delete_message(chat_id,status.message_id)
                except Exception: LOG.debug('Cannot remove search progress')
            return result
        from library_search_ui_v1183 import send_search_results
        return send_search_results(bot,chat_id,heading,items,group=group,
                                   requester_id=requester_id,status_message=status)
    except Exception:
        LOG.exception('V11.7 unified search failed')
        note=('⚠️ Library search is temporarily unavailable. Please try again later.'
              + ('\n⏳ This message auto-deletes after 5 minutes.' if group else ''))
        return _replace_search_status(bot,chat_id,status,note,group=group)


def unified_latest(bot,chat_id):
    try:
        old=_book_rows('',limit=5)
        fresh=[dict(r,source='media') for r in st.latest(limit=5)]
        items=sorted(old+fresh,key=lambda r:str(r.get('approved_at') or r.get('created_at') or ''),
                     reverse=True)[:5]
        if not items:return _message(bot,chat_id,'📚 Nothing has been added yet.')
        return _send_results(bot,chat_id,'📚 Latest 5 library files\n📩 Tap to preview privately.\n'
                             '⏳ Group results expire after 5 minutes.',items,group=bool(int(chat_id)<0))
    except Exception:
        LOG.exception('Latest media unavailable')
        return _message(bot,chat_id,'⚠️ Latest library files unavailable.')


def show_popular(bot,chat_id,*,group=False):
    try:
        news=[dict(row,source='media') for row in st.popular(limit=7)]
        if not news:
            return _message(bot,chat_id,'🔥 No popular media data yet.')
        return _send_results(bot,chat_id,'🔥 Most opened library media this week'+
                             ('\n⏳ Auto-delete after 5 minutes.' if group else ''),news,group=group)
    except Exception:
        return _message(bot,chat_id,'⚠️ Popular media is unavailable.')


def has_media_match(text):
    try:return bool(st.search(str(text or ''),limit=1))
    except Exception:
        LOG.warning('Group media matching unavailable',exc_info=True)
        return False


def _preview(bot,m,kind,identifier):
    import book_library_bot as books
    if kind=='m':
        record=st.get(identifier)
    else:
        record=__import__('book_library_store').get_book(identifier)
    if not record:
        return _message(bot,m.chat.id,'📚 This item is unavailable or has been removed.')
    badge=st.BADGES.get(record.get('media_kind','pdf'),'📄')
    title=record.get('title','Unknown')
    size=__import__('book_library_store').format_size(record.get('file_size'))
    caption=f'{badge} {title[:150]}\n✍️ {record.get("author","Unknown")[:80]}\n'+\
            f'🌐 {record.get("language","-")} · 🗂 {record.get("category","General")}\n📦 {size}'
    if kind=='m' and record.get('description'):
        caption+='\n📝 '+str(record['description'])[:250]
    kb=_keyboard()
    key=uuid.UUID(str(record['id'])).hex
    kb.add(_button('📥 Get File',data=f'v117:g:{kind}:{key}'))
    kb.add(_button('🔗 More Like This',data=f'v117:r:{kind}:{key}'))
    if kind=='m':kb.add(_button('❤️ Save Favorite',data=f'v117:f:m:{key}'))
    cover=record.get('preview_file_id') or record.get('cover_file_id')
    if cover:
        try:return bot.send_photo(m.chat.id,cover,caption=caption[:1000],reply_markup=kb)
        except Exception:LOG.warning('Cover unavailable, showing text preview')
    return _message(bot,m.chat.id,caption,reply_markup=kb)


def handle_media_start(bot,message):
    """Intercept /start media_* and book_* to preview before delivering."""
    if not enabled() or not private(message):return False
    text=str(getattr(message,'text','') or '')
    match=re.fullmatch(r'/start(?:@\w+)?\s+(media|book)_([0-9a-fA-F]{32})',text.strip())
    if not match:return False
    from book_library_bot import _verified,_adult_notice
    if not _verified(message.from_user.id):
        _adult_notice(bot,message.chat.id);return True
    try:_preview(bot,message,'m' if match[1]=='media' else 'b',str(uuid.UUID(hex=match[2])))
    except Exception as exc:_fail(bot,message,exc)
    return True


def _answer(bot,call,text='Done',alert=False):
    try:bot.answer_callback_query(call.id,text[:190],show_alert=alert)
    except Exception:pass


def _deliver(bot,call,kind,key):
    from book_library_bot import _verified
    if not _verified(call.from_user.id):return _answer(bot,call,'Access not permitted.',True)
    if kind=='m':item=st.get(key)
    else:item=__import__('book_library_store').get_book(key)
    if not item:return _answer(bot,call,'File unavailable.',True)
    cid=(item.get('storage_channel_id') if kind=='m' else item.get('channel_id'))
    mid=(item.get('storage_message_id') if kind=='m' else item.get('message_id'))
    if cid is None or mid is None:return _answer(bot,call,'File unavailable.',True)
    try:
        # Telegram-side copy: no exposed private-channel access or public file URL.
        bot.copy_message(chat_id=call.message.chat.id,from_chat_id=int(cid),message_id=int(mid))
    except Exception:
        LOG.exception('Private media delivery failed')
        _answer(bot,call,'Could not deliver. Report this file to admin.',True)
        return
    _answer(bot,call,'File delivered privately.')
    _message(bot,call.message.chat.id,'✅ Delivered: '+str(item.get('title',''))[:160])
    try:
        if kind=='m':st.record_delivery(key)
        else:
            from book_library_v112_store import record_delivery
            record_delivery(key)
    except Exception:LOG.warning('Delivery recorded unsuccessfully',exc_info=True)


def _related(bot,call,kind,key):
    if kind=='b':
        from book_library_v113_store import related_books
        items=[dict(r,source='book',media_kind='pdf') for r in related_books(key)]
    else:
        item=st.get(key)
        if not item:return _answer(bot,call,'File unavailable.',True)
        rows=st.search(category=item.get('category'),limit=8,sort='popular')
        items=[r for r in rows if r['id']!=key][:5]
    if not items:
        _answer(bot,call,'No related files yet.');return
    _answer(bot,call)
    _message(bot,call.message.chat.id,'📚 Similar library items',reply_markup=_markup(bot,items))


def _state_set(user_id,mode,*,seconds=300,remaining=1):
    with _LOCK:
        if len(_STATES)>_MAX_STATES:
            now=time.monotonic();_STATES.clear()  # bounded, no PII kept long term
        _STATES[int(user_id)]=(mode,time.monotonic()+seconds,remaining)


def _state_get(user_id):
    with _LOCK:
        state=_STATES.get(int(user_id))
        if state and state[1] > time.monotonic():return state
        _STATES.pop(int(user_id),None)
        return None


def _state_advance(user_id):
    with _LOCK:
        state=_STATES.get(int(user_id))
        if not state:return
        if state[2]>1:_STATES[int(user_id)]=(state[0],state[1],state[2]-1)
        else:_STATES.pop(int(user_id),None)


def _state_cancel(user_id):
    with _LOCK:_STATES.pop(int(user_id),None)


def _channel(var):
    val=int(os.getenv(var,'0'))
    if val>=0:raise ValueError('Configure '+var+' as your private Telegram channel ID.')
    return val


def _review_channel():
    review=_channel('BOOK_LIBRARY_REVIEW_CHANNEL_ID')
    storage=_channel('BOOK_LIBRARY_CHANNEL_ID')
    if review==storage:raise ValueError('Review channel must be different from storage channel.')
    return review


def _file_meta(bot,m,*,contributor=False):
    info=st.detect_kind(m)
    maximum=int(os.getenv('LIBRARY_MEDIA_SUBMISSION_MAX_BYTES','20971520') if contributor
                else os.getenv('LIBRARY_MEDIA_MAX_BYTES','52428800'))
    maximum=max(1024,min(maximum,100*1024*1024))
    if info['size']>maximum:raise ValueError('File is too large for this library upload.')
    default=info['name'].rsplit('.',1)[0].replace('_',' ')[:175]
    meta=st.parse_caption(getattr(m,'caption','') or '',user=contributor,default_name=default)
    if not contributor and meta['rights_statement']=='other':
        raise ValueError('Admin uploads must declare rights: add a fifth caption field such as permission or cc_by.')
    return info,meta


def _preview_file_id(bot,info,processed,channel):
    if info['source']=='photo':return info['telegram_file_id']
    pic=processed.get('preview_png')
    if not pic:return None
    memory=io.BytesIO(pic);memory.name='preview.jpg'
    try:
        output=bot.send_photo(channel,memory,caption='Library preview (not an original document)')
        photos=getattr(output,'photo',None) or []
        return photos[-1].file_id if photos else None
    except Exception:
        LOG.warning('Preview thumbnail upload unavailable',exc_info=True)
        return None


def submit_media(bot,m,*,contributor=False):
    info,meta=_file_meta(bot,m,contributor=contributor)
    if contributor and len([r for r in st.my_submissions(m.from_user.id) if r['status']=='pending'])>=3:
        raise ValueError('Maximum three pending submissions per contributor.')
    # Deterministic file fingerprints if optional processing is enabled.
    processed=processing.inspect_upload(bot,info)
    dupe=st.duplicates(info['unique_id'],processed.get('sha256'))
    if dupe:raise ValueError('Duplicate file already exists: '+str(dupe.get('title',''))[:70])
    try:
        names=st.same_filename(info['name'])
        if names:
            _message(bot,m.chat.id,'ℹ️ Another approved file has the same filename. '
                     'Please check whether this is a different edition.')
    except Exception:LOG.debug('Filename duplicate warning unavailable')
    channel=_review_channel() if contributor else _channel('BOOK_LIBRARY_CHANNEL_ID')
    copied=bot.copy_message(channel,m.chat.id,m.message_id)
    mid=int(copied.message_id)
    preview=None
    try:
        preview=_preview_file_id(bot,info,processed,channel)
        row={'title':meta['title'],'author':meta['author'],'language':meta['language'],
             'category':meta['category'],'rights_statement':meta['rights_statement'],
             'comment':meta['comment'],'aliases':meta['aliases'],'media_kind':info['kind'],
             'file_name':info['name'],'file_size':info['size'],'file_unique_id':info['unique_id'],
             'sha256':processed.get('sha256'),'uploader_id':m.from_user.id,
             'preview_file_id':preview,'ocr_text':processed.get('ocr_text','')[:10000],
             'description':'','status':'pending' if contributor else 'approved',
             'storage_channel_id':None if contributor else channel,
             'storage_message_id':None if contributor else mid,
             'review_channel_id':channel if contributor else None,
             'review_message_id':mid if contributor else None}
        saved=st.create(row)
    except Exception:
        try:bot.delete_message(channel,mid)
        except Exception:pass
        raise
    if not contributor:
        try:st.audit(m.from_user.id,'media uploaded',saved['id'],info['name'])
        except Exception:LOG.warning('Library audit write unavailable')
    suggestions=[]
    for key,label in [('suggested_title','Title'),('suggested_language','Language'),
                      ('suggested_category','Category')]:
        if processed.get(key):suggestions.append(label+': '+str(processed[key])[:110])
    if suggestions and not contributor:
        _message(bot,m.chat.id,'🔎 Automatic metadata suggestions (review manually):\n'+
                 '\n'.join(suggestions))
    return saved


def _zip_entries(raw):
    if len(raw)>20*1024*1024:raise ValueError('ZIP is too large for safe bulk import (20 MB maximum).')
    items=[];total=0
    with zipfile.ZipFile(io.BytesIO(raw),'r') as archive:
        entries=[f for f in archive.infolist() if not f.is_dir()]
        if len(entries)>20:raise ValueError('Bulk ZIP may contain at most 20 files.')
        for entry in entries:
            if entry.flag_bits & 1:raise ValueError('Encrypted ZIP entries are not supported.')
            if entry.file_size>8*1024*1024:raise ValueError('ZIP file entry exceeds 8 MB.')
            total+=entry.file_size
            if total>40*1024*1024:raise ValueError('ZIP expanded content exceeds 40 MB.')
            if entry.compress_size and entry.file_size/entry.compress_size>100:
                raise ValueError('Suspicious ZIP compression ratio.')
            p=PurePosixPath(entry.filename.replace('\\','/'))
            if p.is_absolute() or '..' in p.parts or len(p.parts)>4:raise ValueError('Unsafe ZIP path')
            name=p.name
            extension=name.rsplit('.',1)[-1].lower() if '.' in name else ''
            kind={'jpg':'image','jpeg':'image','png':'image','webp':'image',
                  'pdf':'pdf','mp3':'audio','mp4':'video','docx':'docx','pptx':'pptx',
                  'txt':'txt','epub':'epub'}.get(extension)
            if not kind:continue
            content=archive.read(entry)
            if kind=='pdf' and not content.startswith(b'%PDF'):
                raise ValueError('Invalid PDF signature in ZIP')
            items.append((name,kind,content))
    return items


def bulk_import_zip(bot,m):
    doc=getattr(m,'document',None)
    if not doc or not str(getattr(doc,'file_name','')).lower().endswith('.zip'):
        raise ValueError('Send a ZIP archive containing at most 20 supported files.')
    info=st.detect_kind(m)
    raw=processing.get_bytes(bot,info['telegram_file_id'],info['size'],limit=20*1024*1024)
    if raw is None:raise ValueError('ZIP too large (maximum 20 MB).')
    entries=_zip_entries(raw)
    if not entries:raise ValueError('No supported files found in this archive.')
    channel=_channel('BOOK_LIBRARY_CHANNEL_ID')
    ok=[];failed=[]
    for name,kind,data in entries:
        try:
            import hashlib
            digest=hashlib.sha256(data).hexdigest()
            if st.duplicates(None,digest):raise ValueError('Duplicate')
            memory=io.BytesIO(data);memory.name=name
            sent=bot.send_document(channel,memory,caption='Admin bulk import: '+name[:150])
            file_obj=getattr(sent,'document',None)
            file_uid=getattr(file_obj,'file_unique_id',None)
            try:
                meta={'title':st.clean(name.rsplit('.',1)[0].replace('_',' ')[:160]),
                      'author':'Library Admin','language':'English','category':'Bulk Import',
                      'rights_statement':'permission','comment':'Imported by administrator',
                      'aliases':'','media_kind':kind,'file_name':name,'file_size':len(data),
                      'file_unique_id':file_uid,'sha256':digest,'uploader_id':m.from_user.id,
                      'status':'approved','storage_channel_id':channel,
                      'storage_message_id':sent.message_id,
                      'review_channel_id':None,'review_message_id':None,
                      'ocr_text':'','description':'','preview_file_id':None}
                added=st.create(meta)
                ok.append(added['id'])
                try:st.audit(m.from_user.id,'bulk imported',added['id'],name)
                except Exception:LOG.warning('Bulk audit write unavailable')
            except Exception:
                try:bot.delete_message(channel,sent.message_id)
                except Exception:pass
                raise
        except Exception as exc:
            failed.append((name,type(exc).__name__))
    return ok,failed


def _admin_panel(bot,m):
    if not admin(m):return _message(bot,m.chat.id,'🔒 Administrator panel is available only to authorized users in private chat.')
    kb=_keyboard()
    for label,action in [('📨 Pending Contributions','pending'),('📩 Requests & Status','requests'),
                         ('⭐ Reviews & Reports','moderation'),('📊 Library Analytics','stats'),
                         ('📁 Manage Library Files','manage'),
                         ('📤 Upload Media','upload'),('📦 Bulk Import','bulk'),
                         ('📚 Existing Book Submissions','legacy'),('🕵️ Audit Commands','audit')]:
        if action == 'manage' and os.getenv('LIBRARY_MANAGE_V118_ENABLED','false').lower() not in ('true','yes','1','on'):
            continue
        kb.add(_button(label,data='v117:adm:'+action))
    _message(bot,m.chat.id,'🛡️ Library Administrator Panel\n'
             'Review community files and requests, publish media, and manage rights.\n'
             'Only approved files appear in group searches.',reply_markup=kb)


def _pending_panel(bot,cid):
    items=st.pending(limit=10)
    if not items:return _message(bot,cid,'📨 No pending V11.7 community files.')
    kb=_keyboard()
    for item in items:
        label=f'{st.BADGES.get(item["media_kind"],"📦")} {item["title"][:37]}'
        kb.add(_button(label,data='v117:review:'+uuid.UUID(str(item['id'])).hex))
    _message(bot,cid,'📨 Pending media contributions\nReview original file and rights before approval.',reply_markup=kb)


def _review_panel(bot,cid,key):
    item=st.get(key,published=False)
    if not item or item['status']!='pending':return _message(bot,cid,'Submission already handled or unavailable.')
    text=(f'📨 Pending: {item["title"]}\n'
          f'✍️ {item["author"]} · {item["language"]} · {item["category"]}\n'
          f'📦 {item["media_kind"].upper()} / {item["file_name"][:100]}\n'
          f'👤 Contributor: {item["uploader_id"]}\n'
          f'📜 Claimed rights: {item["rights_statement"][:300]}\n'
          f'💬 Comment: {item.get("comment","")[:400]}\n'
          f'🔎 OCR excerpt: {item.get("ocr_text","")[:230]}\n'
          f'✏️ Rename: /libraryrename {key} | New Public Title\n'
          f'🗂 Edit other fields: /libraryedit {key} | category | Education\n'
          '⚠️ Review the original and permission evidence; a claim alone is not proof.')
    kb=_keyboard()
    kb.add(_button('📎 View Original in Review Channel',data=f'v117:view:{uuid.UUID(key).hex}'))
    kb.add(_button('✅ Approve & Publish',data=f'v117:approve:{uuid.UUID(key).hex}'))
    kb.add(_button('❌ Reject',data=f'v117:reject:{uuid.UUID(key).hex}'))
    return _message(bot,cid,text,reply_markup=kb)


def approve(bot,admin_id,key):
    item=st.claim(key)
    if not item:raise ValueError('Submission already processed or unavailable.')
    copied=None
    try:
        channel=_channel('BOOK_LIBRARY_CHANNEL_ID')
        if not str(item.get('rights_statement') or '').strip():
            raise ValueError('Review permission before publishing.')
        # Final cross-table duplicate check; exclude this submission's own record.
        from library_media_v117_store import duplicates
        duplicate=duplicates(item.get('file_unique_id'),item.get('sha256'))
        if duplicate and str(duplicate.get('id')) !=str(item['id']):
            raise ValueError('Duplicate of existing library item: '+str(duplicate.get('title'))[:70])
        copied=bot.copy_message(channel,int(item['review_channel_id']),int(item['review_message_id']))
        if not st.finalize(key,channel,copied.message_id):
            raise RuntimeError('Copy created but status update failed; reconcile the submission before retry.')
        try:st.audit(admin_id,'approved',key,item.get('title'))
        except Exception:LOG.warning('Approval audit write unavailable')
        try:bot.send_message(int(item['uploader_id']),'✅ Your library submission was approved: '+str(item['title'])[:150])
        except Exception:LOG.warning('Could not notify contributor')
        return item
    except Exception:
        # A DB timeout could happen AFTER a successful commit. Never delete
        # the stored Telegram file if the catalog already says approved.
        committed=False
        if copied:
            try:
                current=st.get(key,published=False)
                committed=bool(current and current.get('status')=='approved' and
                               int(current.get('storage_message_id') or 0)==int(copied.message_id))
            except Exception:
                # Unknown commit status: preserving the copy is safer than
                # breaking an approved public entry. Admin may reconcile it.
                committed=True
                LOG.error('Approval commit uncertain; kept Telegram copy for reconciliation')
        if not committed:
            if copied:
                try:bot.delete_message(channel,int(copied.message_id))
                except Exception:pass
            try:st.reset_processing(key)
            except Exception:LOG.warning('Processing state needs manual recovery')
        raise


def reject(bot,admin_id,key):
    item=st.get(key,published=False)
    if not item or item.get('status')!='pending' or not st.reject(key):
        raise ValueError('Submission is already processed.')
    try:st.audit(admin_id,'rejected',key,item.get('title'))
    except Exception:LOG.warning('Rejection audit unavailable')
    try:bot.send_message(int(item['uploader_id']),'❌ Your library submission was not approved: '+str(item['title'])[:150])
    except Exception:LOG.warning('Could not notify contributor')


def _requests_panel(bot,cid):
    items=st.pending_requests()
    if not items:return _message(bot,cid,'📩 No pending resource requests.')
    for item in items[:8]:
        key=uuid.UUID(str(item['id'])).hex
        kb=_keyboard()
        kb.add(_button('🔎 Found',data='v117:q:f:'+key),_button('✅ Uploaded',data='v117:q:u:'+key))
        kb.add(_button('❌ Reject',data='v117:q:r:'+key))
        _message(bot,cid,'📩 '+item['title'][:150]+'\nID: '+str(item['id']),reply_markup=kb)


def _request_decision(bot,admin_id,code,key):
    kind={'f':'found','u':'uploaded','r':'rejected'}.get(code)
    if not kind:raise ValueError('Invalid request status.')
    rows=st.resolve_request(key,kind)
    if not rows:raise ValueError('Request already resolved or unavailable.')
    rec=rows[0]
    try:st.audit(admin_id,'request '+kind,None,rec.get('title','')[:200])
    except Exception:LOG.warning('Request audit unavailable')
    try:
        bot.send_message(int(rec['user_id']),f'📩 Your request “{rec["title"][:120]}” status: {kind.upper()}.')
    except Exception:LOG.warning('Could not notify requester')
    return rec


def _moderation_panel(bot,cid):
    from book_library_v113_store import pending_reviews,pending_reports
    reviews=pending_reviews(limit=8)
    reports=pending_reports()
    if not reviews and not reports:return _message(bot,cid,'⭐ No pending reviews or book reports.')
    for r in reviews[:5]:
        key=uuid.UUID(str(r['id'])).hex
        kb=_keyboard();kb.add(_button('Approve Review',data='v117:mod:ra:'+key),
                              _button('Reject Review',data='v117:mod:rr:'+key))
        _message(bot,cid,f'⭐ {r["rating"]}/5 · {r["review_text"][:250]}',reply_markup=kb)
    for r in reports[:5]:
        key=uuid.UUID(str(r['id'])).hex
        kb=_keyboard();kb.add(_button('Resolve Report',data='v117:mod:br:'+key),
                              _button('Dismiss Report',data='v117:mod:bd:'+key))
        _message(bot,cid,f'🚩 {r["kind"]} · {r.get("description","")[:220]}',reply_markup=kb)


def _stats_panel(bot,cid):
    x=st.stats()
    _message(bot,cid,'📊 Media Library Dashboard\n'
             f'✅ Approved: {x["published"]}\n📨 Pending: {x["pending"]}\n'
             f'🙈 Hidden: {x["hidden"]}\n'
             '🔥 Weekly favorites:\n'+
             '\n'.join(str(item.get('title',''))[:45]+' — '+str(item.get('weekly_downloads',0))
                       for item in x['popular'][:5]))


def register_v117_handlers(bot):
    """Called before all previous book handlers, but only active under flag."""
    if getattr(bot,'_library_media_v117_installed',False):return
    bot._library_media_v117_installed=True
    from telebot.handler_backends import ContinueHandling
    # V11.8: Manage Library Files for older PDFs and new media.
    from library_manage_v118 import register_manage_handlers
    register_manage_handlers(bot)
    from library_search_ui_v1183 import register_private_handlers
    register_private_handlers(bot)

    @bot.message_handler(commands=['libraryadmin','mediaadmin'])
    def admin_command(m):
        if not enabled():return ContinueHandling()
        return _admin_panel(bot,m)

    @bot.message_handler(content_types=['text'],func=lambda m:str(getattr(m,'text',''))=='🛡️ Library Admin Panel')
    def admin_button(m):
        if not enabled():return ContinueHandling()
        return _admin_panel(bot,m)

    @bot.message_handler(commands=['mediasubmit','booksubmit','mediacontribute'])
    def submit_start(m):
        if not enabled():return ContinueHandling()
        if not private(m):return _message(bot,m.chat.id,'📩 Submit files privately to the bot, not in the group.')
        _state_set(m.from_user.id,'submit',seconds=300)
        return _message(bot,m.chat.id,'📤 Send ONE PDF, image, audio, video, ZIP, DOCX, PPTX or EPUB within 5 minutes.\n'
                        'Caption:\nTitle | Author | Language | Category | Permission explanation | Comment | Optional search aliases\n'
                        'The file remains private until admin reviews rights and content.')

    @bot.message_handler(commands=['mediaupload','mediabulk','mediauploadbulk'])
    def admin_upload_start(m):
        if not enabled():return ContinueHandling()
        if not admin(m):return _message(bot,m.chat.id,'🔒 Administrators only, in private chat.')
        token=str(m.text).split()[0].split('@')[0].lower()
        bulk='bulk' in token
        _state_set(m.from_user.id,'bulk' if bulk else 'upload',seconds=600 if bulk else 300,
                   remaining=30 if bulk else 1)
        _message(bot,m.chat.id,'📦 Bulk upload: send up to 30 separate files or a ZIP (max 20 files / 20 MB).'
                 if bulk else '📤 Send ONE supported file within 5 minutes.')
        return _message(bot,m.chat.id,
                        'Use caption: Title | Author | Language | Category | Rights | Comment | Aliases\n'
                        'Example rights: permission / public_domain / cc_by.\n'
                        '⛔ Admin must verify distribution rights before publishing.\n'
                        'Send /mediacancel when finished.')


    @bot.message_handler(commands=['mediacancel'])
    def stop_upload(m):
        if not enabled():return ContinueHandling()
        _state_cancel(m.from_user.id)
        _message(bot,m.chat.id,'✅ Upload session closed.')

    @bot.message_handler(commands=['mediafind','medialatest','mediapopular','mediafavorites',
                                   'mediareading','mediaprogress','mediarequests','mediamyuploads','mediahelp'])
    def user_commands(m):
        if not enabled():return ContinueHandling()
        if not private(m):return _message(bot,m.chat.id,'📚 Search public media here with /book TITLE. Personal tools open privately.')
        cmd=str(m.text).split()[0].split('@')[0].lower()
        arg=str(m.text).split(' ',1)[1].strip() if ' ' in str(m.text) else ''
        try:
            if cmd=='/mediahelp':
                return _message(bot,m.chat.id,'📚 /book TITLE type:image lang:Tamil sort:newest\n'
                          '🔎 /mediafind TITLE type:image cat:Education sort:popular\n'
                          '🆕 /medialatest · 🔥 /mediapopular · ❤️ /mediafavorites\n'
                          '📖 /mediaprogress UUID | reading | 40 · /mediareading\n'
                          '📩 /mediarequests · 📨 /mediamyuploads · /booksubmit\n'
                          '🛡️ /libraryadmin (authorized administrators only)')
            if cmd=='/mediafind':return unified_search(bot,m.chat.id,arg)
            if cmd=='/medialatest':return unified_latest(bot,m.chat.id)
            if cmd=='/mediapopular':return show_popular(bot,m.chat.id)
            if cmd=='/mediafavorites':
                rows=[dict(r,source='media') for r in st.favorites(m.from_user.id)]
                if not rows:return _message(bot,m.chat.id,'❤️ No saved media. Use Favorite on an item preview.')
                return _message(bot,m.chat.id,'❤️ Your saved media',reply_markup=_markup(bot,rows))
            if cmd=='/mediareading':
                rows=st.my_reading(m.from_user.id)
                return _message(bot,m.chat.id,'📖 Your media reading list\n'+
                          ('\n'.join(f'{r["media_id"]} — {r["status"]} {r["percent"]}%'
                                     for r in rows) if rows else 'No reading entries.'))
            if cmd=='/mediaprogress':
                bits=[b.strip() for b in arg.split('|')]
                if len(bits)!=3:raise ValueError('Use /mediaprogress UUID | reading | 40')
                rec=st.reading(m.from_user.id,*bits)
                return _message(bot,m.chat.id,f'✅ {rec["status"]} ({rec["percent"]}%)')
            if cmd=='/mediarequests':
                rows=st.my_requests(m.from_user.id)
                return _message(bot,m.chat.id,'📩 Your library requests\n'+
                        ('\n'.join(f'{r["title"][:55]}: {r["status"]}' for r in rows) if rows else 'No requests yet. Try /bookrequest TITLE.'))
            if cmd=='/mediamyuploads':
                rows=st.my_submissions(m.from_user.id)
                return _message(bot,m.chat.id,'📨 Your media submissions\n'+
                        ('\n'.join(f'{st.BADGES.get(r["media_kind"],"📦")} {r["title"][:50]}: {r["status"]}' for r in rows)
                         if rows else 'No submissions yet. /booksubmit'))
        except Exception as exc:return _fail(bot,m,exc)

    @bot.message_handler(commands=['libraryrename','libraryedit','libraryhide','libraryrestore','libraryaudit'])
    def editing(m):
        if not enabled():return ContinueHandling()
        if not admin(m):return _message(bot,m.chat.id,'🔒 Authorized administrators only in private chat.')
        command=str(m.text).split()[0].split('@')[0].lower()
        arg=str(m.text).split(' ',1)[1].strip() if ' ' in str(m.text) else ''
        try:
            if command=='/libraryaudit':
                rows=st._rows(st._db().table(st.AUDIT).select('admin_id,action,details,created_at')
                              .order('created_at',desc=True).limit(15).execute())
                return _message(bot,m.chat.id,'🕵️ Library administration log\n'+
                                ('\n'.join(f'{r["created_at"][:16]}: {r["action"]} ({r["admin_id"]})' for r in rows)
                                 if rows else 'No actions yet.'))
            if command in ('/libraryhide','/libraryrestore'):
                target='hidden' if command=='/libraryhide' else 'approved'
                if not st.set_visibility(arg,target):raise ValueError('Item not found in expected status.')
                st.audit(m.from_user.id,'hidden' if target=='hidden' else 'restored',arg)
                return _message(bot,m.chat.id,'✅ Media status changed: '+target)
            if command=='/libraryrename':
                fields=[v.strip() for v in arg.split('|',1)]
                if len(fields)!=2:raise ValueError('Use /libraryrename UUID | New Catalog Title')
                record_id,title=fields;changes={'title':title}
            else:
                fields=[v.strip() for v in arg.split('|',2)]
                if len(fields)!=3 or fields[1] not in ('title','author','language','category','aliases','description','rights_statement'):
                    raise ValueError('Use /libraryedit UUID | category | Education')
                record_id,field,value=fields;changes={field:value}
            if not st.edit(record_id,changes):raise ValueError('Media not found.')
            st.audit(m.from_user.id,'metadata edited',record_id,str(changes)[:150])
            return _message(bot,m.chat.id,'✅ Catalog metadata updated. Original Telegram filename is unchanged.')
        except Exception as exc:return _fail(bot,m,exc)

    @bot.message_handler(content_types=['document','photo','audio','video'],
         func=lambda m:enabled() and private(m) and _state_get(m.from_user.id) is not None)
    def file_submission(m):
        state=_state_get(m.from_user.id)
        if not state:return ContinueHandling()
        mode=state[0]
        if mode!='submit' and not admin(m):
            _state_cancel(m.from_user.id)
            return _message(bot,m.chat.id,'🔒 Administrator upload permission lost.')
        try:
            if mode=='bulk' and getattr(m,'document',None) and str(getattr(m.document,'file_name','')).lower().endswith('.zip'):
                added,failed=bulk_import_zip(bot,m)
                _message(bot,m.chat.id,f'✅ ZIP imported: {len(added)} files. Failed: {len(failed)}.\n'+
                         '\n'.join(f'{name}: {why}' for name,why in failed[:8]))
            else:
                new=submit_media(bot,m,contributor=(mode=='submit'))
                _message(bot,m.chat.id,'📨 Submission received for admin review.' if mode=='submit'
                         else '✅ Published in Library: '+new['title']+'\nID: '+new['id'])
            _state_advance(m.from_user.id)
        except Exception as exc:
            _fail(bot,m,exc)
            if mode!='bulk':_state_cancel(m.from_user.id)

    @bot.callback_query_handler(func=lambda c:str(getattr(c,'data','') or '').startswith('v117:'))
    def actions(c):
        if not enabled():return ContinueHandling()
        if not private(getattr(c,'message',None)) or c.from_user.id!=c.message.chat.id:
            return _answer(bot,c,'This button works in your private chat only.',True)
        parts=str(c.data).split(':')
        try:
            if len(parts)==4 and parts[1] in ('g','r','f') and parts[2] in ('m','b'):
                action,kind,key=parts[1],parts[2],str(uuid.UUID(hex=parts[3]))
                if action=='g':return _deliver(bot,c,kind,key)
                if action=='r':return _related(bot,c,kind,key)
                if action=='f':
                    if kind!='m':raise ValueError('Use existing book favorites for PDFs.')
                    st.favorite(c.from_user.id,key)
                    return _answer(bot,c,'Saved to your private favorites.')
            # Telegram callback.message.from_user is the bot, NOT the clicking admin.
            # Authorization must use callback.from_user, never message.from_user.
            import book_library_bot as lib
            if not lib._admin(c.from_user.id):return _answer(bot,c,'Admin only.',True)
            if len(parts)==3 and parts[1]=='adm':
                action=parts[2]
                _answer(bot,c)
                if action=='pending':return _pending_panel(bot,c.message.chat.id)
                if action=='manage':
                    from library_manage_v118 import list_panel,enabled as management_enabled
                    if not management_enabled():return _message(bot,c.message.chat.id,'⚠️ File management is not enabled yet.')
                    return list_panel(bot,c.from_user.id,c.message.chat.id)
                if action=='requests':return _requests_panel(bot,c.message.chat.id)
                if action=='moderation':return _moderation_panel(bot,c.message.chat.id)
                if action=='stats':return _stats_panel(bot,c.message.chat.id)
                if action=='legacy':
                    from book_library_v113_store import pending_submissions
                    recs=pending_submissions()
                    return _message(bot,c.message.chat.id,'📚 Existing V11.3 submissions\n'+
                        ('\n'.join(x['title'][:60]+' — '+str(x['id']) for x in recs) if recs else 'None')+
                        '\nApprove: /booksubmitapprove UUID\nReject: /booksubmitreject UUID')
                if action=='audit':return _message(bot,c.message.chat.id,'🕵️ /libraryaudit — Last 15 admin actions.')
                if action=='upload':
                    _state_set(c.from_user.id,'upload',seconds=300)
                    return _message(bot,c.message.chat.id,'📤 Send one file with: Title | Author | Language | Category | Rights | Comment | Aliases')
                if action=='bulk':
                    _state_set(c.from_user.id,'bulk',seconds=600,remaining=30)
                    return _message(bot,c.message.chat.id,'📦 Send files in sequence or ZIP (max 20 files / 20 MB). /mediacancel to stop.')
            if len(parts)==3 and parts[1] in ('review','view','approve','reject'):
                action,key=parts[1],str(uuid.UUID(hex=parts[2]))
                if action=='review':_answer(bot,c);return _review_panel(bot,c.message.chat.id,key)
                if action=='view':
                    item=st.get(key,published=False)
                    if not item or item['status']!='pending':raise ValueError('Submission unavailable.')
                    bot.copy_message(c.message.chat.id,int(item['review_channel_id']),int(item['review_message_id']))
                    return _answer(bot,c,'Original sent privately.')
                if action=='approve':
                    result=approve(bot,c.from_user.id,key)
                    _answer(bot,c,'Approved and published!')
                    return _message(bot,c.message.chat.id,'✅ Published: '+result['title'])
                if action=='reject':
                    reject(bot,c.from_user.id,key)
                    return _answer(bot,c,'Rejected. Contributor notified.')
            if len(parts)==4 and parts[1]=='q':
                row=_request_decision(bot,c.from_user.id,parts[2],str(uuid.UUID(hex=parts[3])))
                return _answer(bot,c,'Request status: '+row['status'])
            if len(parts)==4 and parts[1]=='mod':
                from book_library_v113_store import moderate_review,resolve_report
                key=str(uuid.UUID(hex=parts[3]));flag=parts[2]
                if flag in ('ra','rr'):
                    ok=moderate_review(key,'approved' if flag=='ra' else 'rejected')
                elif flag in ('br','bd'):
                    ok=resolve_report(key,'resolved' if flag=='br' else 'dismissed')
                else:raise ValueError('Unknown moderation action.')
                return _answer(bot,c,'Updated.' if ok else 'Already handled.',not ok)
            return _answer(bot,c,'Unknown action.',True)
        except Exception as exc:
            LOG.warning('Library callback failed',exc_info=True)
            return _answer(bot,c,str(exc)[:170] if isinstance(exc,ValueError) else 'Could not perform action.',True)
