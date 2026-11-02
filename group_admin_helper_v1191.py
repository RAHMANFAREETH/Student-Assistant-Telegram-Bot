"""V11.9.1 optional admin/group helper and bounded operational telemetry.

Reuses V11.9 feedback/review and V11.3 book requests; no second bot.
Alerts are best-effort only; Supabase is the durable source of truth.
"""
from __future__ import annotations
import collections
import logging
import os
import queue
import re
import threading
import time
from datetime import datetime, timezone

LOG=logging.getLogger(__name__)
FLAG='GROUP_HELPER_V1191_ENABLED'
_LOCK=threading.RLock()
_WARNINGS=collections.deque(maxlen=50)
_ERRORS=collections.deque(maxlen=40)
_FLOOD={}
_LAST_WARN={}
_STATS={'active':0,'peak':0,'requests':0,'errors':0,'last_ms':0.0}
_TIMES=collections.deque(maxlen=256)
_ALERTS=queue.Queue(maxsize=128)
_BOT=None
_STARTED=False
_LINK=re.compile(r'(?i)(?:https?://|t\.me/|telegram\.me/)')

def _on(name, default='false'):
    return str(os.getenv(name,default)).strip().lower() in ('true','1','yes','on')

def enabled():
    return _on(FLAG)

def _clean(value,limit=180):
    return ' '.join(str(value or '').replace('\n',' ').replace('\r',' ').split())[:limit]

def _uid(m):
    return int(m.from_user.id)

def _is_private(m):
    return getattr(getattr(m,'chat',None),'type',None)=='private'

def _group(m):
    return getattr(getattr(m,'chat',None),'type',None) in ('group','supergroup')

def _admin(uid):
    try:
        from book_library_bot import _admin as admin
        return bool(admin(uid))
    except Exception:
        return False

def _group_allowed(cid):
    try:
        from friendly_v119 import _allowed_group
        return bool(_allowed_group(cid))
    except Exception:
        return False

def _adult(uid):
    try:
        from friendly_v119 import _adult
        return bool(_adult(uid))
    except Exception:
        return False

def _reply(bot,m,text):
    return bot.send_message(m.chat.id,str(text)[:3900])

def _admin_chat():
    try:return int(os.getenv('GROUP_HELPER_ADMIN_CHAT_ID','0'))
    except (TypeError,ValueError):return 0

def _alert_worker():
    while True:
        text=_ALERTS.get()
        try:
            bot=_BOT;cid=_admin_chat()
            if bot is not None and cid and enabled():bot.send_message(cid,text[:3850])
        except Exception as exc:
            record_error('admin notification',exc,notify=False)
        finally:
            _ALERTS.task_done()
        time.sleep(0.6)  # Keep optional alert traffic modest.

def queue_alert(text):
    """No request is blocked on Telegram alert delivery. Does not replace DB queue."""
    if not enabled() or not _admin_chat():return False
    try:_ALERTS.put_nowait(str(text)[:3850]);return True
    except queue.Full:
        record_error('admin alert queue','Queue is full',notify=False)
        return False

def publish_feedback_event(rows):
    """Called only AFTER a successful V11.9 feedback insert."""
    if not rows:return False
    r=rows[0] if isinstance(rows,list) else rows
    text=(f'💬 New Student Assistant feedback\n'
          f'Type: {_clean(r.get("kind"),40)}\n'
          f'User ID: {r.get("user_id", "-")}\n'
          f'Feedback: {_clean(r.get("message"),450)}\n'
          'Review: /feedbackqueue (private admin command)')
    return queue_alert(text)

def publish_book_request(row):
    if not row:return False
    return queue_alert('📩 New Book Request\nTitle: '+_clean(row.get('title'),140)+
         '\nAuthor: '+_clean(row.get('author'),100)+
         '\nReview: /bookrequests (private admin command)')

def record_error(where,exc,notify=True):
    event=(datetime.now(timezone.utc).isoformat(timespec='seconds'),
           _clean(where,65),_clean(type(exc).__name__+': '+str(exc),150) if isinstance(exc,Exception) else _clean(exc,150))
    with _LOCK:_ERRORS.append(event)
    LOG.warning('V11.9.1 %s: %s',event[1],event[2])
    if notify and _on('GROUP_HELPER_ERROR_ALERTS_ENABLED'):
        queue_alert('⚠️ Bot error ('+event[1]+'): '+event[2])

def metrics_start():
    with _LOCK:
        _STATS['active']+=1
        _STATS['peak']=max(_STATS['peak'],_STATS['active'])
    return time.monotonic()

def metrics_finish(start,status=200):
    if start is None:return
    elapsed=max(0.0,(time.monotonic()-start)*1000)
    with _LOCK:
        _STATS['active']=max(0,_STATS['active']-1)
        _STATS['requests']+=1
        _STATS['errors']+=int(int(status)>=400)
        _STATS['last_ms']=round(elapsed,1)
        _TIMES.append(elapsed)

def load_summary():
    with _LOCK:
        data=dict(_STATS);times=sorted(_TIMES)
    p95=round(times[min(len(times)-1,int(0.95*(len(times)-1)))],1) if times else 0
    return ('⚡ Webhook load (this process, since restart)\n'
      'Active requests: {active}\nPeak concurrent: {peak}\n'
      'Completed requests: {requests}\nHTTP errors: {errors}\n'
      'Last webhook: {last_ms} ms\nSample p95: '+str(p95)+' ms\n'
      'Process-local; not all Telegram users or full infrastructure metrics.').format(**data)

def install_metrics(app):
    if getattr(app,'_helper_v1191_metrics',False):return app
    from flask import g,request
    @app.before_request
    def _v1191_before():
        if enabled() and request.path=='/telegram-webhook':g._v1191_time=metrics_start()
    @app.after_request
    def _v1191_after(response):
        start=getattr(g,'_v1191_time',None)
        if start is not None:metrics_finish(start,response.status_code);g._v1191_time=None
        return response
    app._helper_v1191_metrics=True
    return app

def _flood_check(m):
    """Lightweight per-user/group anti-flood; never globally throttle others."""
    cid=int(m.chat.id);uid=_uid(m)
    if getattr(m.from_user,'is_bot',False) or _admin(uid):return False
    now=time.monotonic();window=12.0
    try:threshold=max(4,min(30,int(os.getenv('GROUP_HELPER_FLOOD_THRESHOLD','9'))))
    except ValueError:threshold=9
    key=(cid,uid)
    with _LOCK:
        # Bounded memory under high load; stale entries are discarded.
        if len(_FLOOD)>=5000:
            for k,(stamps,last) in list(_FLOOD.items()):
                if now-last>60:_FLOOD.pop(k,None)
            if len(_FLOOD)>=5000:_FLOOD.clear()
        recent,last=_FLOOD.get(key,(collections.deque(maxlen=32),now))
        while recent and now-recent[0]>window:recent.popleft()
        recent.append(now)
        _FLOOD[key]=(recent,now)
        bad=len(recent)>threshold
        if bad:_WARNINGS.append((cid,uid,round(now,0),'flood'))
    return bad

def _link_check(m):
    if not _on('GROUP_HELPER_LINK_WARNINGS_ENABLED'):return False
    text=str(getattr(m,'text',None) or getattr(m,'caption',None) or '')
    if not _LINK.search(text):return False
    # Whitelist legitimate library/bot links. This is only a heuristic.
    cleaned=text.lower()
    if 't.me/student_sl_assistant_bot' in cleaned or 't.me/library_for_all' in cleaned:return False
    return True

def _act_on_group_event(bot,m,reason):
    cid=int(m.chat.id);uid=_uid(m);now=time.monotonic()
    if _on('GROUP_HELPER_DELETE_ENABLED'):
        try:bot.delete_message(cid,int(m.message_id))
        except Exception as exc:record_error('group delete',exc,notify=False)
    with _LOCK:
        last=_LAST_WARN.get((cid,uid),0)
        warn=now-last>=45
        if warn:_LAST_WARN[(cid,uid)]=now
    if warn and _on('GROUP_HELPER_WARN_IN_GROUP_ENABLED'):
        try:bot.send_message(cid,'⚠️ Please avoid repeated messages or suspicious links. Use /grouphelp for book-search instructions.')
        except Exception as exc:record_error('group warning',exc,notify=False)
    return None

def _command(bot,m):
    from telebot.handler_backends import ContinueHandling
    if not enabled():return ContinueHandling()
    text=str(getattr(m,'text','') or '')
    command=text.split(maxsplit=1)[0].lstrip('/').split('@')[0].lower()
    arguments=text.split(maxsplit=1)[1] if len(text.split(maxsplit=1))>1 else ''
    if command=='adminhubid':
        # Private admin group chat ID discovery, without weakening book-group allowlists.
        if _group(m) and _admin(_uid(m)):
            return _reply(bot,m,'🛡️ Admin group ID: '+str(m.chat.id)+
              '\nUse this as GROUP_HELPER_ADMIN_CHAT_ID on Render. Keep this group private.')
        return ContinueHandling()
    if command=='groupguide':
        if not _group(m) or not _group_allowed(m.chat.id):return ContinueHandling()
        return _reply(bot,m,'👋 أَلسَّلَامُ عَلَيْكُمْ وَرَحْمَةُ اللَّهِ وَبَرَكَاتُهُ\n📚 Book Library Help\n'
              'Search: /book Quran\nLatest: /booklatest\nOpen any result privately to get the file.\n'
              '🤖 https://t.me/Student_Sl_Assistant_bot\n🔞 18+ eligibility applies.')
    if command=='reportproblem':
        if not _is_private(m):return ContinueHandling()
        if not _adult(_uid(m)):return _reply(bot,m,'🔒 Adult eligibility verification required.')
        if not arguments.strip():return _reply(bot,m,'💬 Usage: /reportproblem Describe the issue (at least 8 characters).')
        try:
            from friendly_v119 import feedback
            feedback(_uid(m),arguments,'suggestion')
            return _reply(bot,m,'✅ Report saved. Administrators can review it privately.')
        except ValueError as exc:return _reply(bot,m,'⚠️ '+_clean(exc,220))
        except Exception as exc:
            record_error('report problem',exc)
            return _reply(bot,m,'⚠️ Unable to save this report. Try /feedback later.')
    if not _is_private(m):return ContinueHandling()
    if not _admin(_uid(m)):return _reply(bot,m,'🔒 Private bot administrator command.')
    if command=='adminhub':
        return _reply(bot,m,'🛡️ Student Assistant — Admin Hub\n'
          '💬 /feedbackqueue — pending feedback\n'
          '⭐ /reviewqueue — book reviews\n'
          '📩 /adminrequests — new book requests\n'
          '📚 /libraryadmin — library controls\n'
          '📊 /friendadmin — V11.9 activity overview\n'
          '⚡ /adminload — current process latency/load\n'
          '⚠️ /adminalerts — recent service events\n'
          '👥 /adminwarnings — recorded anti-flood warnings\n'
          '🔎 /groupguide — group search instructions\n'
          '🆔 In your private admin group: /adminhubid\n'
          '📣 /admintestalert — test alert delivery\n'
          'Private notifications require GROUP_HELPER_ADMIN_CHAT_ID.')
    if command=='adminrequests':
        try:
            from book_library_v113_store import pending_requests
            rows=pending_requests()
            if not rows:return _reply(bot,m,'✅ No pending book requests.')
            return _reply(bot,m,'📩 Pending book requests\n'+'\n'.join(
              _clean(r.get('title'),80)+' — '+_clean(r.get('author') or 'Unknown',35) for r in rows[:15])+\
              '\nResolve using /bookrequestresolve UUID fulfilled|rejected')
        except Exception as exc:
            record_error('book requests',exc)
            return _reply(bot,m,'⚠️ Book request queue unavailable.')
    if command=='admintestalert':
        if not _admin_chat():return _reply(bot,m,'⚠️ Set GROUP_HELPER_ADMIN_CHAT_ID in Render first.')
        return _reply(bot,m,'✅ Alert queued for the configured private admin chat.' if
            queue_alert('🛡️ Student Assistant Admin Hub test alert (no user information).')
            else '⚠️ Alert queue unavailable. See /adminalerts and Render logs.')
    if command=='adminload':return _reply(bot,m,load_summary())
    if command=='adminwarnings':
        with _LOCK:events=list(_WARNINGS)[-12:]
        return _reply(bot,m,'👥 Recent moderation warnings (process-local)\n'+
          ('\n'.join(f'Group {cid}, user {uid}: {reason}' for cid,uid,_,reason in events) if events else 'None.'))
    if command=='adminalerts':
        with _LOCK:events=list(_ERRORS)[-8:]
        return _reply(bot,m,'⚠️ Recent bot errors (process-local)\n'+
          ('\n'.join(f'{t}: {where} — {desc}' for t,where,desc in events) if events else 'None recorded.')+
          '\nNote: Render logs are the authoritative service log.')
    return ContinueHandling()

def install(bot):
    """Register BEFORE the restrictive V11.6 group-message gate."""
    global _BOT,_STARTED
    if getattr(bot,'_helper_v1191_installed',False):return bot
    from telebot.handler_backends import ContinueHandling
    _BOT=bot
    with _LOCK:
        if not _STARTED:
            thread=threading.Thread(target=_alert_worker,name='admin-hub-alerts',daemon=True)
            thread.start();_STARTED=True
    @bot.message_handler(commands=['adminhub','adminrequests','adminload','adminwarnings','adminalerts','admintestalert','adminhubid','reportproblem','groupguide'])
    def helper_commands(m):
        return _command(bot,m)
    @bot.message_handler(content_types=['text','document','photo','video','audio','animation'],func=_group)
    def helper_group_monitor(m):
        if not enabled() or not _group_allowed(m.chat.id) or not _on('GROUP_HELPER_MODERATION_ENABLED'):
            return ContinueHandling()
        if not getattr(m,'from_user',None):return ContinueHandling()
        if getattr(m.from_user,'is_bot',False) or _admin(_uid(m)):
            return ContinueHandling()
        bad=_flood_check(m) or _link_check(m)
        if bad:
            # Group administrators must not be moderated by this helper.
            # Check membership only on a suspicious event to avoid one API call per message.
            try:
                member=bot.get_chat_member(m.chat.id,m.from_user.id)
                if getattr(member,'status','') in ('administrator','creator','owner'):
                    return ContinueHandling()
            except Exception:
                # Never auto-delete when the bot cannot check group permissions.
                if _on('GROUP_HELPER_DELETE_ENABLED'):return ContinueHandling()
            return _act_on_group_event(bot,m,'flood_or_link')
        return ContinueHandling()
    bot._helper_v1191_installed=True
    return bot
