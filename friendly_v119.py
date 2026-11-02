"""V11.9 Friendly Student Assistant: additive, opt-in UI and library engagement.

Public group commands are limited to allowlisted Book Library groups. Personal
commands, callbacks, ratings, telemetry, and notifications operate privately.
This module never downloads books or bypasses verified-adult delivery gates.
"""
from __future__ import annotations
import difflib
import hashlib
import logging
import os
import re
import secrets
import threading
import time
import uuid
from datetime import date, datetime, timezone, timedelta
from html import escape

LOG = logging.getLogger(__name__)
BOT = 'Student_Sl_Assistant_bot'
ARABIC_GREETING = '👋 السَّلَامُ عَلَيْكُمْ وَرَحْمَةُ اللَّهِ وَبَرَكَاتُهُ'
ENGLISH_GREETING = 'Welcome to Student Assistant! 🎓📚'
FLAG = 'FRIENDLY_V119_ENABLED'
USERS='friendly_v119_users'
SAVED='friendly_v119_saved'
EVENTS='friendly_v119_events'
REVIEWS='friendly_v119_reviews'
FEEDBACK='friendly_v119_feedback'
LANGUAGES={'en':'🇬🇧 English','ta':'🇱🇰 தமிழ்','si':'🇱🇰 සිංහල','ar':'🇸🇦 العربية'}
HOME_LABELS = {
 'en': ('📚 Find Books','🗂 Categories','❤️ My Books','🕘 Recent','🔥 Popular','🌟 Trending','📖 Daily Book','🆕 New Arrivals','🤖 AI & PDF Tools','🌐 Language','👤 My Profile','❓ All Commands','💬 Feedback','🤝 Invite Friends'),
 'ta': ('📚 புத்தகத் தேடல்','🗂 வகைகள்','❤️ எனது நூல்கள்','🕘 சமீபத்தில்','🔥 பிரபல நூல்கள்','🌟 Trending','📖 இன்றைய நூல்','🆕 புதிய நூல்கள்','🤖 AI & PDF கருவிகள்','🌐 மொழி','👤 எனது தகவல்','❓ Commands','💬 கருத்து','🤝 நண்பர்களை அழைக்க'),
 'si': ('📚 පොත් සොයන්න','🗂 වර්ග','❤️ මගේ පොත්','🕘 මෑත බැලූ','🔥 ජනප්‍රිය','🌟 Trending','📖 අද පොත','🆕 නව පොත්','🤖 AI සහ PDF','🌐 භාෂාව','👤 මගේ තොරතුරු','❓ විධාන','💬 ප්‍රතිචාර','🤝 ආරාධනා'),
 'ar': ('📚 البحث عن الكتب','🗂 التصنيفات','❤️ كتبي','🕘 شوهد مؤخراً','🔥 الأكثر شعبية','🌟 الرائج','📖 كتاب اليوم','🆕 كتب جديدة','🤖 أدوات AI و PDF','🌐 اللغة','👤 معلوماتي','❓ الأوامر','💬 الملاحظات','🤝 دعوة الأصدقاء')
}
CATEGORIES=('Islamic Studies','Hadith','Quran','Arabic','Education','Science','Mathematics','Finance','Novels','General')
PRIVATE_COMMANDS=frozenset({
 'home','friendly','commands','myid','myinfo','myprofile','botinfo','mystats',
 'privacy','forgetfriendly','mybooks','recentbooks','bookcategories','smartbook',
 'popular','trending','dailybook','sharebook','ratebook','reviewbook',
 'reportdetails','reportbookdetails','feedback','suggest','invite',
 'newarrivals','friendlanguage','v119language','friendhelp',
 'friendadmin','feedbackqueue','reviewqueue','reviewapprove','reviewreject',
 'feedbackresolve','notifynew',
})
GROUP_COMMANDS=frozenset({'chatid','groupinfo','grouphelp','userinfo'})
ALL_COMMANDS=sorted(PRIVATE_COMMANDS|GROUP_COMMANDS)
_LOCK=threading.RLock()
_PROMPTS={}
_LIMIT=1500


def enabled():
    return str(os.getenv(FLAG,'false')).strip().lower() in ('1','true','yes','on')


def _yes(name, default=False):
    return str(os.getenv(name,str(default))).strip().lower() in ('1','true','yes','on')


def _db():
    from db import supabase
    if supabase is None:raise RuntimeError('Database unavailable')
    return supabase


def _rows(response):
    return getattr(response,'data',None) or []


def _clean(value,maxlen=160):
    value = str(value or '').replace('\x00','').replace('\r',' ').replace('\n',' ')
    value = re.sub(r'[\u202a-\u202e\u2066-\u2069]','',value)
    return ' '.join(value.split())[:maxlen]


def _uid(m):
    return int(m.from_user.id)


def _private(m):
    return getattr(getattr(m,'chat',None),'type',None)=='private'


def _group(m):
    return getattr(getattr(m,'chat',None),'type',None) in ('group','supergroup')


def _adult(uid):
    # Never relax the pre-existing age/eligibility gate.
    from book_library_bot import _verified
    return bool(_verified(uid))


def _admin(uid):
    from book_library_bot import _admin
    return bool(_admin(uid))


def _allowed_group(cid):
    from book_library_bot import _enabled,_allowed_group
    import group_books_only_v116 as gate
    return bool(gate.active() and _enabled() and _allowed_group(cid))


def _msg(bot,cid,text,**kw):
    return bot.send_message(cid,text,**kw)


def _btn(label,data=None,url=None):
    from telebot import types
    if url:return types.InlineKeyboardButton(label,url=url)
    return types.InlineKeyboardButton(label,callback_data=data)


def _keyboard(rows):
    from telebot import types
    kb=types.InlineKeyboardMarkup(row_width=2)
    for row in rows:
        kb.row(*[_btn(*item) for item in row])
    return kb


def _link(kind,identifier):
    return f'https://t.me/{BOT}?start={"media" if kind=="m" else "book"}_{uuid.UUID(str(identifier)).hex}'


def _bookrow(row,kind='m'):
    return f'{_clean(row.get("title"),45)} — {_clean(row.get("author",""),20)}'


def _get_user(uid):
    try:
        result=_rows(_db().table(USERS).select('*').eq('user_id',int(uid)).limit(1).execute())
        return result[0] if result else None
    except Exception:
        LOG.warning('V11.9 user settings unavailable',exc_info=True)
        return None


def _ensure_user(uid, **updates):
    uid=int(uid)
    values={'user_id':uid,**updates}
    d=_db()
    try:
        # on_conflict updates only supplied columns. Does not erase existing preferences.
        return _rows(d.table(USERS).upsert(values,on_conflict='user_id').execute())
    except Exception:
        LOG.warning('V11.9 user settings write unavailable',exc_info=True)
        raise


def _event(uid,action,kind=None,item=None):
    if not _yes('FRIENDLY_V119_STATS_ENABLED',True):return
    try:
        _db().table(EVENTS).insert({'user_id':int(uid),'action':str(action)[:40],
              'item_kind':kind,'item_id':str(uuid.UUID(str(item))) if item else None}).execute()
    except Exception:
        LOG.debug('V11.9 optional analytics unavailable',exc_info=True)


def _lang(uid):
    try:
        from ui_v57 import get_language
        choice=get_language(int(uid))
        return choice if choice in LANGUAGES else 'en'
    except Exception:return 'en'


def _friendly_text(uid, key):
    translations={
     'en':{'search':'🔎 Find Books','my':'❤️ My Books','recent':'🕘 Recently Viewed','category':'🗂 Categories','help':'❓ Help & Commands','new':'🆕 New Arrivals'},
     'ta':{'search':'🔎 புத்தகங்களைத் தேடுங்கள்','my':'❤️ எனது புத்தகங்கள்','recent':'🕘 சமீபத்தில் பார்த்தவை','category':'🗂 வகைகள்','help':'❓ உதவி மற்றும் Commands','new':'🆕 புதிய நூல்கள்'},
     'si':{'search':'🔎 පොත් සොයන්න','my':'❤️ මගේ පොත්','recent':'🕘 මෑතකදී බැලූ','category':'🗂 වර්ග','help':'❓ උදව්','new':'🆕 නව පොත්'},
     'ar':{'search':'🔎 البحث عن الكتب','my':'❤️ كتبي','recent':'🕘 شوهد مؤخرًا','category':'🗂 التصنيفات','help':'❓ المساعدة','new':'🆕 الكتب الجديدة'}}
    return translations.get(_lang(uid),translations['en'])[key]


def welcome_text(name='Friend'):
    name=_clean(name,60) or 'Friend'
    return (f'{ARABIC_GREETING}\n{ENGLISH_GREETING}\n\n'
            f'👤 {name}\n'
            '📚 Books · 🤖 AI Study · 📄 PDF Tools · 🌍 Translation\n'
            'Choose a button below, or type /commands.\n'
            '🔞 Available to eligible users aged 18+.')


def home(bot,cid,name='Friend',*,send_welcome=True):
    if send_welcome:
        _msg(bot,cid,welcome_text(name))
    labels=HOME_LABELS.get(_lang(cid),HOME_LABELS['en'])
    actions=('find','categories','mybooks','recent','popular','trending','daily','new',
             'tools','language','myinfo','commands','feedback','invite')
    rows=[]
    for i in range(0,len(actions),2):
        rows.append([(labels[j],'v119:'+actions[j],None) for j in range(i,min(i+2,len(actions)))])
    return _msg(bot,cid,'🏠 Student Assistant — Friendly Home Menu',reply_markup=_keyboard(rows))


def _cmd(text):
    text=str(text or '').strip()
    parts=text.split(None,1)
    return (parts[0].lstrip('/').split('@')[0].lower(),parts[1].strip() if len(parts)>1 else '') if text.startswith('/') else ('','')


def _book_candidates(query='',category=None,limit=8):
    """Use existing catalog; keep searches bounded and public records only."""
    import library_media_v117_store as st
    result=[]
    if _yes('LIBRARY_MEDIA_V117_ENABLED'):
        try:
            for row in st.search(query,category=category,limit=min(limit,20)):
                result.append((row,'m'))
        except Exception:LOG.warning('Media search unavailable',exc_info=True)
    try:
        from book_library_v112_store import browse_books
        rows,_=browse_books(query=query or None,category=category, page=0,page_size=10)
        result.extend((row,'b') for row in rows)
    except Exception:
        try:
            from book_library_store import search_books,latest_books
            rows=search_books(query,limit=8) if query else latest_books(limit=8)
            result.extend((row,'b') for row in rows)
        except Exception: LOG.warning('Legacy catalog unavailable',exc_info=True)
    seen=set();out=[]
    for row,kind in result:
        identifier=str(row.get('id',''))
        if not identifier or (kind,identifier) in seen:continue
        seen.add((kind,identifier));out.append((row,kind))
    return out[:limit]


def _fuzzy(query,limit=7):
    candidates=_book_candidates('',limit=10)
    try:
        import library_media_v117_store as st
        rows=st.candidate_rows(limit=150)
        candidates.extend((row,'m') for row in rows if row.get('status','approved')=='approved')
    except Exception: pass
    seen=set();ranked=[]
    for row,kind in candidates:
        identifier=str(row.get('id',''))
        if (kind,identifier) in seen:continue
        seen.add((kind,identifier))
        r=max(difflib.SequenceMatcher(None,_clean(query).casefold(),_clean(row.get(col)).casefold()).ratio()
              for col in ('title','author'))
        if r>=.48:ranked.append((r,row,kind))
    return [(row,kind) for _,row,kind in sorted(ranked,key=lambda p:-p[0])[:limit]]


def _cards(bot,cid,heading,items):
    if not items:
        return _msg(bot,cid,'📚 No matching books found. Try another spelling or use /bookrequest TITLE.')
    rows=[]
    for item,kind in items[:10]:
        try:
            identifier=uuid.UUID(str(item['id']))
            label='📖 '+_clean(item.get('title') or 'Book',37)
            rows.append([(label,f'v119:view:{kind}:{identifier.hex}',None)])
        except (ValueError,KeyError,TypeError):continue
    rows.append([('🏠 Home','v119:home',None)])
    return _msg(bot,cid,heading+'\n📩 Tap a title for its private preview and delivery.',reply_markup=_keyboard(rows))


def search_books(bot,cid,query):
    query=_clean(query,100)
    if len(query)<2:return _msg(bot,cid,'🔎 Send /smartbook TITLE — example: /smartbook Sahih al Bukhari')
    items=_book_candidates(query,limit=8)
    if not items:
        items=_fuzzy(query)
        header='🔎 Closest matches for: '+query
    else:header='📚 Books matching: '+query
    return _cards(bot,cid,header,items)


def _item(kind,identifier):
    try:
        identifier=str(uuid.UUID(str(identifier)))
        if kind=='m':
            import library_media_v117_store as st
            return st.get(identifier)
        if kind=='b':
            from book_library_store import get_book
            return get_book(identifier)
    except (TypeError,ValueError,AttributeError):pass
    return None


def _saved(uid,limit=15):
    rows=_rows(_db().table(SAVED).select('item_kind,item_id,created_at')
          .eq('user_id',int(uid)).order('created_at',desc=True).limit(limit).execute())
    return [(record, _item(record['item_kind'],record['item_id'])) for record in rows]


def _save(uid,kind,identifier):
    if not _item(kind,identifier):raise ValueError('This book is unavailable.')
    row={'user_id':int(uid),'item_kind':kind,'item_id':str(uuid.UUID(str(identifier)))}
    d=_db()
    existing=_rows(d.table(SAVED).select('item_id').eq('user_id',int(uid))
            .eq('item_kind',kind).eq('item_id',row['item_id']).limit(1).execute())
    if existing:
        d.table(SAVED).delete().eq('user_id',int(uid)).eq('item_kind',kind).eq('item_id',row['item_id']).execute()
        return False
    d.table(SAVED).insert(row).execute()
    return True


def favorites(bot,cid,uid):
    try:
        items=[(book,rec['item_kind']) for rec,book in _saved(uid) if book]
        # Reuse legacy favorites too; V11.9 does not hide an existing bookshelf.
        try:
            import library_media_v117_store as st
            items.extend((book,'m') for book in st.favorites(uid))
        except Exception:LOG.debug('Legacy media favorites unavailable',exc_info=True)
        try:
            from book_library_v112_store import list_favorites
            legacy,_=list_favorites(uid,page_size=8)
            items.extend((book,'b') for book in legacy)
        except Exception:LOG.debug('Legacy Book Library favorites unavailable',exc_info=True)
        unique=[];seen=set()
        for book,kind in items:
            key=(kind,str(book.get('id','')))
            if key not in seen and key[1]:seen.add(key);unique.append((book,kind))
    except Exception:return _msg(bot,cid,'⚠️ Bookshelf unavailable. Please try again later.')
    return _cards(bot,cid,'❤️ Your saved books',unique)


def recents(bot,cid,uid):
    try:
        raw=_rows(_db().table(EVENTS).select('item_kind,item_id').eq('user_id',int(uid))
                  .eq('action','view').order('created_at',desc=True).limit(35).execute())
        seen=set();items=[]
        for row in raw:
            key=(row.get('item_kind'),row.get('item_id'))
            if key in seen:continue
            seen.add(key)
            book=_item(*key)
            if book:items.append((book,key[0]))
            if len(items)>=10:break
        return _cards(bot,cid,'🕘 Recently viewed books',items)
    except Exception:return _msg(bot,cid,'⚠️ Recent books unavailable.')


def popular(bot,cid,days=7):
    items=[]
    try:
        import library_media_v117_store as st
        items.extend((r,'m') for r in st.popular(days=days,limit=7))
    except Exception: LOG.warning('Media popular unavailable',exc_info=True)
    try:
        from book_library_v112_store import top_downloaded
        items.extend((r,'b') for r in top_downloaded(limit=5))
    except Exception:pass
    return _cards(bot,cid,'🔥 Popular books' if days==7 else '🌟 Trending books (recent)',items)


def categories(bot,cid):
    rows=[]
    for i,cat in enumerate(CATEGORIES):
        rows.append([('📂 '+cat,f'v119:cat:{i}',None)])
    rows.append([('🏠 Home','v119:home',None)])
    return _msg(bot,cid,'🗂 Choose a category',reply_markup=_keyboard(rows))


def daily(bot,cid,uid):
    try:
        items=_book_candidates('',limit=10)
        if not items:return _msg(bot,cid,'📚 New recommendations will appear as books are added.')
        # Stable per user/day rather than unpredictable or incentive-driven ranking.
        salt=(str(uid)+':'+date.today().isoformat()).encode()
        chosen=items[int.from_bytes(hashlib.sha256(salt).digest()[:4],'big')%len(items)]
        return _cards(bot,cid,'📖 Today’s book recommendation', [chosen])
    except Exception:return _msg(bot,cid,'📚 Daily recommendation is unavailable right now.')


def language(bot,cid,uid):
    return _msg(bot,cid,'🌐 Choose your preferred language / மொழியைத் தேர்ந்தெடுக்கவும்',
          reply_markup=_keyboard([[ (label,f'v119:lang:{code}',None)] for code,label in LANGUAGES.items()]))


def set_language(uid,code):
    if code not in LANGUAGES:raise ValueError('Unsupported language.')
    from ui_v57 import set_language as existing
    # Same preference as the existing V5.7 interface; no competing storage.
    return existing(uid,code)


def profile(bot,m):
    u=m.from_user
    name=_clean(' '.join(filter(None,[getattr(u,'first_name',''),getattr(u,'last_name','')])),100)
    username=getattr(u,'username',None)
    info=(f'👤 My Telegram Profile\nName: {name or "Not provided"}\n'
         f'Username: @{_clean(username,32)}\n' if username else
         f'👤 My Telegram Profile\nName: {name or "Not provided"}\nUsername: Not set\n')
    info+=f'User ID: {u.id}\nLanguage: {LANGUAGES.get(_lang(u.id),"English")}\n'
    info+='📱 Phone number: Not available to the bot without your explicit sharing.\n'
    info+='🔒 Your activity and saved books are private. Use /privacy to learn more.'
    return _msg(bot,m.chat.id,info)


def stats(bot,cid,uid):
    try:
        d=_db(); actions=('view','search','favorite','rate','feedback')
        counts={}
        for action in actions:
            result=d.table(EVENTS).select('id',count='exact').eq('user_id',int(uid)).eq('action',action).limit(1).execute()
            counts[action]=getattr(result,'count',None) or 0
        saved=d.table(SAVED).select('item_id',count='exact').eq('user_id',int(uid)).limit(1).execute()
        return _msg(bot,cid,'📊 Your Friendly Bot Activity\n'+ '\n'.join(f'{key.title()}: {count}' for key,count in counts.items())+ f'\nSaved: {getattr(saved,"count",0) or 0}')
    except Exception:return _msg(bot,cid,'⚠️ Personal activity is unavailable. Check the V11.9 database migration.')


def privacy_text():
    return ('🔒 V11.9 Privacy\n'
       'Telegram provides your public name, username and numeric User ID. We cannot see your phone number unless you explicitly share it.\n'
       'Friendly features store your language preference, saved books, optional reviews and feedback, referral choices, and limited activity events.\n'
       'These records are for your features and private admin statistics, not public leaderboards.\n'
       'New-arrivals alerts are opt-in. /forgetfriendly deletes the V11.9 profile, activity, saves, ratings and feedback, but not your original Telegram messages or records held by other older bot features.\n'
       'Access remains limited to eligible adults, and Telegram group messages are not used as a personal activity feed.')


def forget(uid):
    d=_db()
    for table in (EVENTS,SAVED,REVIEWS,FEEDBACK):
        d.table(table).delete().eq('user_id',int(uid)).execute()
    # Don't leave referral records attributing this user.
    d.table(USERS).update({'referrer_id':None}).eq('referrer_id',int(uid)).execute()
    d.table(USERS).delete().eq('user_id',int(uid)).execute()


def command_guide(bot,cid):
    return _msg(bot,cid,(
      '❓ Commands — V11.9\n'
      '🏠 /home /commands /friendlanguage\n'
      '📚 /smartbook TITLE /book TITLE /booklatest /bookcategories\n'
      '❤️ /mybooks /recentbooks /dailybook\n'
      '🔥 /popular /trending /sharebook UUID\n'
      '⭐ /ratebook m|b UUID 1-5 [review] /reviewbook m|b UUID 1-5 REVIEW\n'
      '💬 /reportdetails KIND UUID ISSUE /feedback MESSAGE\n'
      '👤 /myid /myinfo /chatid /groupinfo /userinfo /mystats /botinfo\n'
      '🤝 /invite /newarrivals on|off\n'
      '📄 /mediaupload /mediabulk /mediaforward (admin permissions required)\n'
      '🔐 /privacy /forgetfriendly\n'
      '📩 Need a missing book? /bookrequest TITLE\n'
      'ℹ️ KIND is m (Media) or b (Book); UUID appears in book share links.\n'
      '🔒 Personal commands only work in your bot private chat.'))


def _prompt_set(uid,action,kind=None,identifier=None):
    with _LOCK:
        if len(_PROMPTS)>=_LIMIT:
            for k,v in list(_PROMPTS.items()):
                if v[3]<time.monotonic():_PROMPTS.pop(k,None)
            if len(_PROMPTS)>=_LIMIT:_PROMPTS.clear()
        _PROMPTS[int(uid)]=(action,kind,identifier,time.monotonic()+300)


def _prompt_take(uid):
    with _LOCK:
        value=_PROMPTS.pop(int(uid),None)
    return value if value and value[3]>time.monotonic() else None


def _prompt_has(uid):
    with _LOCK:
        data=_PROMPTS.get(int(uid))
        return bool(data and data[3]>time.monotonic())


def feedback(uid,text,kind='suggestion',item_kind=None,item_id=None):
    text=_clean(text,650)
    if len(text)<8:raise ValueError('Please describe the issue in at least 8 characters.')
    if item_id and not _item(item_kind,item_id):raise ValueError('Book is unavailable.')
    entry={'user_id':int(uid),'kind':kind,'message':text,'item_kind':item_kind,
           'item_id':str(uuid.UUID(str(item_id))) if item_id else None,'status':'pending'}
    return _rows(_db().table(FEEDBACK).insert(entry).execute())


def rate(uid,kind,identifier,stars,text=''):
    if kind not in ('m','b'):raise ValueError('Book type must be m or b.')
    if not _item(kind,identifier):raise ValueError('Book is unavailable.')
    stars=int(stars)
    if not 1<=stars<=5:raise ValueError('Rating must be 1–5.')
    text=_clean(text,550)
    values={'user_id':int(uid),'item_kind':kind,'item_id':str(uuid.UUID(str(identifier))),
            'stars':stars,'review_text':text,'status':'pending' if text else 'approved',
            'updated_at':datetime.now(timezone.utc).isoformat()}
    _db().table(REVIEWS).upsert(values,on_conflict='user_id,item_kind,item_id').execute()
    return values


def rate_summary(kind,identifier):
    rows=_rows(_db().table(REVIEWS).select('stars,review_text')
          .eq('item_kind',kind).eq('item_id',str(uuid.UUID(str(identifier))))
          .eq('status','approved').limit(500).execute())
    if not rows:return '⭐ No ratings yet.'
    avg=sum(int(r['stars']) for r in rows)/len(rows)
    comments=[_clean(r.get('review_text'),150) for r in rows if r.get('review_text')]
    return f'⭐ {avg:.1f}/5 from {len(rows)} ratings.\n'+ '\n'.join('💬 '+c for c in comments[:3])


def referral_link(uid):
    d=_db(); profile=_get_user(uid)
    code=(profile or {}).get('ref_code')
    if not code:
        code=secrets.token_urlsafe(9).replace('-','').replace('_','')[:12]
        d.table(USERS).upsert({'user_id':int(uid),'ref_code':code},on_conflict='user_id').execute()
    return f'https://t.me/{BOT}?start=ref_{code}'


def handle_start(bot,m):
    """Only consumes referral deep links; normal /start remains unchanged."""
    if not enabled() or not _private(m):return False
    match=re.fullmatch(r'/start(?:@\w+)?\s+ref_([A-Za-z0-9]{8,24})',str(getattr(m,'text','') or '').strip())
    if not match:return False
    uid=_uid(m)
    if not _adult(uid):
        _msg(bot,m.chat.id,'🔒 This service is for eligible adults. Please complete the existing access verification.');return True
    try:
        profile=_get_user(uid)
        if not profile:
            inviter=_rows(_db().table(USERS).select('user_id').eq('ref_code',match[1]).limit(1).execute())
            if inviter and int(inviter[0]['user_id'])!=uid:
                _ensure_user(uid,referrer_id=int(inviter[0]['user_id']))
            else:_ensure_user(uid)
        _event(uid,'start')
    except Exception:LOG.warning('Referral recording unavailable',exc_info=True)
    home(bot,m.chat.id,getattr(m.from_user,'first_name','Friend'))
    return True


def _sub(uid,enabled_value):
    _ensure_user(uid,notify_new=bool(enabled_value))


def notify_admin(bot,m):
    """Opt-in announcements, manual admin batches, safe retries and no background worker."""
    if not _admin(_uid(m)):return _msg(bot,m.chat.id,'🔒 Admin only.')
    items=_book_candidates('',limit=1)
    if not items:return _msg(bot,m.chat.id,'📚 No new books to announce.')
    rec,kind=items[0]
    key=f'{kind}:{uuid.UUID(str(rec["id"]))}'
    d=_db();pending=[];cursor=0
    for _ in range(100):  # bounded paging, up to 10,000 subscribers per invocation
        page=_rows(d.table(USERS).select('user_id,last_notified_key')
                   .eq('notify_new',True).gt('user_id',cursor)
                   .order('user_id').limit(100).execute())
        if not page:break
        cursor=int(page[-1]['user_id'])
        pending.extend(x for x in page if x.get('last_notified_key')!=key)
        if len(pending)>=15:break
    pending=pending[:15]
    sent=failed=0
    for item in pending:
        uid=int(item['user_id'])
        if not _adult(uid):continue
        try:
            bot.send_message(uid,'🆕 New Library Book\n📚 '+_clean(rec.get('title'),125)+'\n'+_link(kind,rec['id']))
            d.table(USERS).update({'last_notified_key':key}).eq('user_id',uid).execute()
            sent+=1
        except Exception:
            failed+=1
            LOG.warning('Could not notify subscriber',exc_info=True)
    return _msg(bot,m.chat.id,f'📢 Notification batch: {sent} sent, {failed} failed. Run /notifynew again for the next batch.\nOnly opted-in adults are contacted.')


def admin_report(bot,m,table):
    if not _admin(_uid(m)):return _msg(bot,m.chat.id,'🔒 Admin only.')
    name=FEEDBACK if table=='feedback' else REVIEWS
    rows=_rows(_db().table(name).select('*').eq('status','pending').order('created_at',desc=False).limit(8).execute())
    if not rows:return _msg(bot,m.chat.id,'✅ No pending items.')
    content='\n'.join(f'{x["id"]} — '+_clean(x.get('message') or x.get('review_text'),85) for x in rows)
    return _msg(bot,m.chat.id,'🛡️ Pending '+table+'\n'+content+'\n\nUse the appropriate approve/reject/resolve command.')


def admin_stats(bot,m):
    if not _admin(_uid(m)):return _msg(bot,m.chat.id,'🔒 Admin only.')
    d=_db();after=(datetime.now(timezone.utc)-timedelta(days=7)).isoformat()
    recent=_rows(d.table(EVENTS).select('user_id,action').gte('created_at',after).limit(3000).execute())
    users=set(x['user_id'] for x in recent)
    counts={}
    for x in recent:counts[x['action']]=counts.get(x['action'],0)+1
    return _msg(bot,m.chat.id, f'📊 V11.9 Admin Popularity (last 7 days)\nActive unique users: {len(users)}\nEvents in sample: {len(recent)}\n'+'\n'.join(f'{k}: {v}' for k,v in sorted(counts.items(),key=lambda i:-i[1])[:10])+'\nStats cover only enabled V11.9 activity; capped at the newest 3,000 events.')


def _msg_in_group(bot,m,text,reply_markup=None):
    if not _allowed_group(m.chat.id):return None
    if reply_markup is not None:
        sent=_msg(bot,m.chat.id,text,reply_markup=reply_markup)
        try:
            from group_ui_v115 import _remember
            if getattr(sent,'message_id',None):_remember(bot,m.chat.id,sent.message_id,kind='menu')
        except Exception:LOG.debug('Optional group cleanup queue unavailable',exc_info=True)
        return sent
    try:
        from group_books_only_v116 import _ephemeral
        return _ephemeral(bot,m.chat.id,text)
    except Exception:
        return _msg(bot,m.chat.id,text)


def _reply_user(bot,m):
    # Only group admins can inspect information that Telegram already supplies
    # in a replied-to message; never reveal private contact information.
    if not _group(m) or not _allowed_group(m.chat.id):return None
    try:
        actor=bot.get_chat_member(m.chat.id,_uid(m))
        if getattr(actor,'status','') not in ('administrator','creator'):return _msg_in_group(bot,m,'🔒 Group administrators only.')
    except Exception:return _msg_in_group(bot,m,'🔒 Administrator permission could not be checked.')
    target=getattr(getattr(m,'reply_to_message',None),'from_user',None)
    if target is None:return _msg_in_group(bot,m,'↩️ Reply to a member message with /userinfo.')
    name=_clean(' '.join(filter(None,[getattr(target,'first_name',''),getattr(target,'last_name','')])),80)
    username=getattr(target,'username',None)
    return _msg_in_group(bot,m,'👤 Telegram public user fields\nName: '+(name or '-')+'\nUsername: '+('@'+_clean(username,32) if username else 'Not set')+'\nID: '+str(target.id))


def _perform(bot,m,cmd,args):
    uid=_uid(m);cid=m.chat.id
    if cmd in GROUP_COMMANDS and _group(m):
        if cmd=='grouphelp':
            kb=_keyboard([[('🤖 Open Student Assistant',None,'https://t.me/'+BOT)],
                          [('📚 Open Book Library',None,'https://t.me/'+BOT+'?start=study')]])
            return _msg_in_group(bot,m,'📚 Search in this group: /book Quran or /booklatest.\n📩 Tap below to use the bot privately.',reply_markup=kb)
        if cmd=='chatid':return _msg_in_group(bot,m,'💬 Group Chat ID: '+str(cid))
        if cmd=='groupinfo':
            try:cnt=bot.get_chat_member_count(cid)
            except Exception:cnt='Unknown'
            return _msg_in_group(bot,m,f'📚 Group: {_clean(getattr(m.chat,"title",""),90)}\nID: {cid}\nMembers: {cnt}\n🔎 /book TITLE')
        return _reply_user(bot,m)
    if not _private(m):return _msg_in_group(bot,m,'🔒 Personal features work in a private chat: https://t.me/'+BOT)
    _prompt_take(uid)  # A slash command cancels any unfinished free-text form.
    if cmd in ('myid','chatid'):return _msg(bot,cid,f'👤 Your User ID: {uid}\n💬 Chat ID: {cid}')
    if cmd in ('myinfo','myprofile'):return profile(bot,m)
    if cmd=='privacy':return _msg(bot,cid,privacy_text())
    if cmd=='forgetfriendly':
        if args!='CONFIRM':return _msg(bot,cid,'⚠️ This deletes your V11.9 settings, saved books and feedback. To confirm, send /forgetfriendly CONFIRM. Original library records and Telegram messages remain.')
        forget(uid);return _msg(bot,cid,'✅ V11.9 personal records deleted. Original records managed by older bot features remain.')
    if cmd in ('friendlanguage','v119language'):return language(bot,cid,uid)
    if not _adult(uid):return _msg(bot,cid,'🔒 Please complete the existing adult-access verification before using library features.')
    if cmd in ('home','friendly'):return home(bot,cid,getattr(m.from_user,'first_name','Friend'))
    if cmd=='botinfo':return _msg(bot,cid,'🤖 Student Assistant Bot\nVersion: V11.9 Friendly Experience (feature enabled)\nBot: https://t.me/'+BOT+'\n📚 /book · 🤖 AI · 📄 PDF · 🌍 Translation\n🔞 18+ eligibility applies.')
    if cmd=='mystats':return stats(bot,cid,uid)
    if cmd in ('commands','friendhelp'):return command_guide(bot,cid)
    if cmd=='smartbook':_event(uid,'search');return search_books(bot,cid,args)
    if cmd=='bookcategories':return categories(bot,cid)
    if cmd=='mybooks':return favorites(bot,cid,uid)
    if cmd=='recentbooks':return recents(bot,cid,uid)
    if cmd=='popular':return popular(bot,cid)
    if cmd=='trending':return popular(bot,cid,days=3)
    if cmd=='dailybook':return daily(bot,cid,uid)
    if cmd=='sharebook':
        parts=args.split()
        if len(parts)!=2 or parts[0] not in ('m','b'):return _msg(bot,cid,'🔗 Usage: /sharebook m|b UUID')
        item=_item(*parts)
        return _msg(bot,cid,'🔗 Share this book:\n'+_link(*parts)) if item else _msg(bot,cid,'File unavailable.')
    if cmd in ('ratebook','reviewbook'):
        parts=args.split(None,3)
        if len(parts)<3:return _msg(bot,cid,'⭐ Usage: /ratebook m|b UUID 1-5 [optional review]')
        stars=int(parts[2]);review=parts[3] if len(parts)>3 else ''
        rate(uid,parts[0],parts[1],stars,review);_event(uid,'rate')
        return _msg(bot,cid,'✅ Rating saved. Written reviews remain pending until admin approval.' if review else '✅ Rating saved.')
    if cmd in ('reportdetails','reportbookdetails'):
        parts=args.split(None,2)
        if len(parts)<3:return _msg(bot,cid,'📝 Usage: /reportdetails m|b UUID DESCRIPTION')
        feedback(uid,parts[2],kind='book_report',item_kind=parts[0],item_id=parts[1]);_event(uid,'feedback')
        return _msg(bot,cid,'✅ Book metadata report sent for administrator review.')
    if cmd in ('feedback','suggest'):
        if not args:_prompt_set(uid,'feedback');return _msg(bot,cid,'💬 Send your suggestion or feedback now. /home cancels the form.')
        feedback(uid,args);_event(uid,'feedback');return _msg(bot,cid,'✅ Thank you! Admins can review your feedback.')
    if cmd=='invite':
        link=referral_link(uid)
        profile=_get_user(uid)
        count=_db().table(USERS).select('user_id',count='exact').eq('referrer_id',uid).limit(1).execute()
        return _msg(bot,cid,f'🤝 Invite your friends (18+)\n{link}\nInvited users who started: {getattr(count,"count",0) or 0}\nNo forced invitations or leaderboard.')
    if cmd=='newarrivals':
        if args.lower() not in ('on','off'):
            p=_get_user(uid) or {}
            return _msg(bot,cid, '🆕 New-arrivals notifications are '+('ON' if p.get('notify_new') else 'OFF')+'.\nUse /newarrivals on or /newarrivals off.')
        _sub(uid,args.lower()=='on');return _msg(bot,cid,'✅ New arrivals notifications '+args.upper()+'. You can change this anytime.')
    if cmd=='friendadmin':return admin_stats(bot,m)
    if cmd=='feedbackqueue':return admin_report(bot,m,'feedback')
    if cmd=='reviewqueue':return admin_report(bot,m,'review')
    if cmd in ('reviewapprove','reviewreject','feedbackresolve'):
        if not _admin(uid):return _msg(bot,cid,'🔒 Admin only.')
        key=str(uuid.UUID(args))
        table=FEEDBACK if cmd=='feedbackresolve' else REVIEWS
        status='resolved' if cmd=='feedbackresolve' else ('approved' if cmd=='reviewapprove' else 'rejected')
        rows=_rows(_db().table(table).update({'status':status}).eq('id',key).eq('status','pending').execute())
        return _msg(bot,cid,'✅ Updated.' if rows else '⚠️ Item not found or already processed.')
    if cmd=='notifynew':return notify_admin(bot,m)
    return command_guide(bot,cid)


def _callback(bot,c):
    if not enabled():return False
    data=str(getattr(c,'data','') or '')
    if not data.startswith('v119:'):return False
    try:bot.answer_callback_query(c.id)
    except Exception:pass
    m=getattr(c,'message',None)
    if m is None:return True
    if not _private(m):
        try:bot.answer_callback_query(c.id,'Open the bot privately to use this feature.',show_alert=True)
        except Exception:pass
        return True
    uid=int(c.from_user.id);cid=m.chat.id
    if not _adult(uid):_msg(bot,cid,'🔒 Adult verification required.');return True
    parts=data.split(':')
    action=parts[1] if len(parts)>1 else ''
    if action=='home':home(bot,cid,getattr(c.from_user,'first_name','Friend'),send_welcome=False)
    elif action=='find':_msg(bot,cid,'🔎 Search by title or author:\n/smartbook Sahih al Bukhari\n/book Quran')
    elif action=='mybooks':favorites(bot,cid,uid)
    elif action=='recent':recents(bot,cid,uid)
    elif action=='popular':popular(bot,cid)
    elif action=='trending':popular(bot,cid,days=3)
    elif action=='daily':daily(bot,cid,uid)
    elif action=='new':_msg(bot,cid,'🆕 Latest books: /booklatest\nSubscribe for new-arrivals notices with /newarrivals on.')
    elif action=='categories':categories(bot,cid)
    elif action=='cat' and len(parts)==3 and parts[2].isdigit():
        index=int(parts[2]);
        if 0<=index<len(CATEGORIES):_cards(bot,cid,'📂 '+CATEGORIES[index],_book_candidates(category=CATEGORIES[index]))
    elif action=='language':language(bot,cid,uid)
    elif action=='lang' and len(parts)==3:
        saved=set_language(uid,parts[2]);_msg(bot,cid,'✅ Language saved.' if saved else '⚠️ Language changed for this session, database storage needs checking.')
        home(bot,cid,getattr(c.from_user,'first_name','Friend'),send_welcome=False)
    elif action=='tools':_msg(bot,cid,'🤖 AI: use the existing AI & Questions menu.\n📄 PDF Tools: select PDF Tools in your main menu.\n🔎 Tool Finder: /findtool library\n🚀 /home to return.')
    elif action=='myinfo':profile(bot,type('M',(),{'chat':m.chat,'from_user':c.from_user})())
    elif action=='commands':command_guide(bot,cid)
    elif action=='feedback':_prompt_set(uid,'feedback');_msg(bot,cid,'💬 Send your suggestion or problem in one message.')
    elif action=='invite':_msg(bot,cid,'🤝 Send /invite to get your personal link.')
    elif action=='save' and len(parts)==4:
        try:
            saved=_save(uid,parts[2],uuid.UUID(hex=parts[3]))
            _event(uid,'favorite',parts[2],uuid.UUID(hex=parts[3]))
            _msg(bot,cid,'❤️ Added to My Books.' if saved else '💔 Removed from My Books.')
        except Exception:_msg(bot,cid,'⚠️ Could not update My Books.')
    elif action=='view' and len(parts)==4:
        kind=parts[2]; identifier=str(uuid.UUID(hex=parts[3]))
        item=_item(kind,identifier)
        if item:
            _event(uid,'view',kind,identifier)
            detail=(f'📚 {_clean(item.get("title"),140)}\n✍️ {_clean(item.get("author","Unknown"),85)}\n'
                    f'🌐 {_clean(item.get("language",""),40)} · 🗂 {_clean(item.get("category","General"),50)}\n'
                    f'📦 {__import__("book_library_store").format_size(item.get("file_size"))}\n')
            try:detail+='\n'+rate_summary(kind,identifier)
            except Exception:pass
            markup=_keyboard([[('📥 Open File',None,_link(kind,identifier))],
                             [('❤️ Save/Unsave',f'v119:save:{kind}:{uuid.UUID(identifier).hex}',None)],
                             [('⭐ Rate This Book',f'v119:rating:{kind}:{uuid.UUID(identifier).hex}',None)],
                             [('🔗 Share Book',f'v119:share:{kind}:{uuid.UUID(identifier).hex}',None)],
                             [('🚩 Report Details',f'v119:report:{kind}:{uuid.UUID(identifier).hex}',None)]])
            _msg(bot,cid,detail,reply_markup=markup)
        else:_msg(bot,cid,'📚 File unavailable.')
    elif action=='rating' and len(parts)==4:
        k,ident=parts[2:]; _msg(bot,cid,'⭐ Rate the book using a button:',reply_markup=_keyboard(
            [[(str(x)+'⭐',f'v119:star:{k}:{ident}:{x}',None) for x in range(1,4)],
             [(str(x)+'⭐',f'v119:star:{k}:{ident}:{x}',None) for x in (4,5)]]))
    elif action=='star' and len(parts)==5:
        try:rate(uid,parts[2],uuid.UUID(hex=parts[3]),int(parts[4]));_event(uid,'rate');_msg(bot,cid,'✅ Thank you for rating!')
        except Exception:_msg(bot,cid,'⚠️ Could not save this rating.')
    elif action=='share' and len(parts)==4:
        try:
            if _item(parts[2],uuid.UUID(hex=parts[3])):
                _msg(bot,cid,'🔗 Share this book with an eligible student:\n'+_link(parts[2],uuid.UUID(hex=parts[3])))
            else:_msg(bot,cid,'📚 Book is unavailable.')
        except Exception:_msg(bot,cid,'⚠️ Could not create share link.')
    elif action=='report' and len(parts)==4:
        _prompt_set(uid,'book_report',parts[2],str(uuid.UUID(hex=parts[3])))
        _msg(bot,cid,'🚩 Please type the incorrect book detail and the correct value. Your report goes to admin review.')
    return True


def register(bot):
    if getattr(bot,'_friendly_v119_registered',False):return bot
    from telebot.handler_backends import ContinueHandling

    @bot.message_handler(commands=ALL_COMMANDS)
    def v119_commands(m):
        if not enabled():return ContinueHandling()
        cmd,args=_cmd(m.text)
        try:return _perform(bot,m,cmd,args)
        except (ValueError,TypeError) as e:return _msg(bot,m.chat.id,'⚠️ '+_clean(str(e),240))
        except Exception:
            LOG.exception('V11.9 command unavailable: %s',cmd)
            return _msg(bot,m.chat.id,'⚠️ This feature is temporarily unavailable. Please try again later.')

    @bot.callback_query_handler(func=lambda c:str(getattr(c,'data','') or '').startswith('v119:'))
    def v119_callbacks(c):
        if not enabled():return ContinueHandling()
        try:return _callback(bot,c)
        except Exception:
            LOG.exception('V11.9 callback failure')
            return True

    @bot.message_handler(content_types=['text'],func=lambda m: enabled() and _private(m) and
                         getattr(getattr(m,'from_user',None),'id',None) is not None and
                         _prompt_has(m.from_user.id) and not str(getattr(m,'text','') or '').startswith('/'))
    def v119_user_input(m):
        if not _adult(_uid(m)):return _msg(bot,m.chat.id,'🔒 Adult verification required.')
        state=_prompt_take(_uid(m))
        if not state:return ContinueHandling()
        try:
            if state[0]=='feedback':feedback(_uid(m),m.text);_event(_uid(m),'feedback');return _msg(bot,m.chat.id,'✅ Feedback received. Thank you!')
            if state[0]=='book_report':feedback(_uid(m),m.text,'book_report',state[1],state[2]);_event(_uid(m),'feedback');return _msg(bot,m.chat.id,'✅ Book report sent for admin review.')
        except (ValueError,TypeError) as e:return _msg(bot,m.chat.id,'⚠️ '+_clean(str(e),200))
        except Exception:return _msg(bot,m.chat.id,'⚠️ Could not save feedback. Please try again later.')
        return ContinueHandling()

    @bot.inline_handler(func=lambda q:enabled())
    def v119_inline(q):
        # Telegram Inline Mode must separately be enabled in @BotFather.
        from telebot import types
        if not _adult(q.from_user.id):
            try:bot.answer_inline_query(q.id,[],cache_time=1,is_personal=True)
            except Exception:pass
            return
        query=_clean(getattr(q,'query',''),100)
        matches=_book_candidates(query,limit=6) if len(query)>=2 else []
        results=[]
        for item,kind in matches:
            try:
                link=_link(kind,item['id']); title=_clean(item.get('title','Book'),100)
                results.append(types.InlineQueryResultArticle(
                    id=uuid.uuid4().hex,title=title,
                    description=_clean(item.get('author'),70),
                    input_message_content=types.InputTextMessageContent('📚 '+title+'\n'+link)))
            except Exception:continue
        try:bot.answer_inline_query(q.id,results,cache_time=30,is_personal=True)
        except Exception:LOG.warning('Inline query failed',exc_info=True)

    bot._friendly_v119_registered=True
    return bot
