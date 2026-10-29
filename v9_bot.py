"""V9.0 Academic Toolkit: 14 opt-in student tools under one V8-approved pilot.

No new Telegram bot or Render service. No automatic AI model invocation.
Temporary document/photo sessions are in-memory and expire. Persistent academic
records are student-scoped and stored in Supabase with server-only credentials.
"""
from __future__ import annotations
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from io import BytesIO
from threading import RLock
import os, re, secrets, time, uuid

from telebot import types
from telebot.handler_backends import ContinueHandling
from v8_engine import StudyInputError, MAX_FILE_BYTES
from v9_engine import (read_text, assignment_report, syllabus_lines, formula_lines,
    formula_docx, prepare_deck, document_diff, mindmap_topics, mindmap_png,
    presentation_pptx, math_solution, parse_timetable, diagram_labels)

HUB = '🧰 V9 Academic Toolkit'
OPTIONS = OrderedDict([
 ('📸 Math Solver', 'math'), ('🧠 Mind Map Generator', 'mindmap'),
 ('📊 Presentation Maker', 'ppt'), ('🔬 Diagram Label Reader', 'diagram'),
 ('📋 Assignment Checker', 'assignment'), ('📖 Syllabus Tracker', 'syllabus'),
 ('🧮 Formula Sheet', 'formula'), ('🖼 Timetable Photo Import', 'timetable'),
 ('🔎 Document Comparison', 'compare'), ('📓 Mistake Notebook', 'mistakes'),
 ('🍅 Focus Timer', 'focus'), ('📤 Anki Export', 'anki'),
 ('🔍 Citation Verifier', 'verify'), ('👥 Study Rooms', 'rooms'),
])
TOOLS = {v:k for k,v in OPTIONS.items()}
_states = OrderedDict()
_lock = RLock()
STATE_TTL = 12 * 60
MAX_STATES = 80


def enabled():
    return os.getenv('V9_ENABLED','').lower() in ('true','1','yes')


def allowed(uid):
    from v8_bot import allowed as v8_allowed
    return enabled() and v8_allowed(uid)


def _private(m): return getattr(m.chat,'type',None)=='private'


def _db():
    from db import supabase
    return supabase


def _set(uid, state):
    with _lock:
        _states[int(uid)] = {**state,'ts':time.monotonic()}
        _states.move_to_end(int(uid))
        while len(_states)>MAX_STATES:_states.popitem(last=False)


def _get(uid):
    with _lock:
        data=_states.get(int(uid))
        if data and time.monotonic()-data['ts']>STATE_TTL:
            _states.pop(int(uid),None);return None
        return data


def _clear(uid):
    with _lock:_states.pop(int(uid),None)


def _read_ocr(raw, filename):
    if len(raw)>950_000:
        raise StudyInputError('Image exceeds the 950 KB OCR limit. Send a smaller photo.')
    from translation_ocr import extract_text_with_ocr
    try: return extract_text_with_ocr(raw,filename=filename)[:10000]
    except Exception as exc: raise StudyInputError('OCR unavailable. Check OCR_SPACE_API_KEY and image size.') from exc


def _safe_send(bot,chat_id,message):
    bot.send_message(chat_id,str(message)[:3800])


def _send_file(bot,chat_id,data,caption):
    data.seek(0)
    bot.send_document(chat_id,data, caption=caption[:300])


def verify_reference(text):
    """User-requested metadata lookup. Fixed HTTPS endpoints; input never becomes a URL host."""
    import requests
    from urllib.parse import quote
    value=text.strip()
    if re.fullmatch(r'(?:10\.\d{4,9}/[-._;()/:A-Z0-9]+)', value, re.I):
        url='https://api.crossref.org/works/'+quote(value,safe='')
        try:
            result=requests.get(url,timeout=8,allow_redirects=False,headers={'User-Agent':'StudentAssistantBot-ReferenceChecker/1.0'});
            if result.status_code==404: return 'No DOI record found. Check the DOI manually.'
            result.raise_for_status()
            record=result.json()['message']
            title=(record.get('title') or [''])[0]
            return ('🔍 Crossref DOI record\nTitle: '+str(title)[:240]
                    +'\nAuthor(s): '+', '.join((a.get('family','') for a in record.get('author',[])[:5]))[:180]
                    +'\nYear: '+str((record.get('published') or {}).get('date-parts',[['?']])[0][0])
                    +'\nDOI: '+str(record.get('DOI',''))[:150]
                    +'\nVerify against the publisher record before citing.')
        except (requests.RequestException,KeyError,ValueError,IndexError,TypeError):
            return 'DOI metadata service unavailable. Try again later.'
    isbn=value.replace('-','').replace(' ','')
    if re.fullmatch(r'(?:\d{10}|\d{13}|\d{9}[xX])',isbn):
        try:
            result=requests.get('https://openlibrary.org/isbn/'+isbn+'.json',timeout=8,allow_redirects=False)
            if result.status_code==404:return 'ISBN record not found; check the publisher catalogue.'
            result.raise_for_status()
            item=result.json()
            return ('📚 Open Library ISBN record\nTitle: '+str(item.get('title','Unknown'))[:250]
                    +'\nPublication: '+str(item.get('publish_date','Unknown'))[:80]
                    +'\nPublisher: '+str(item.get('publishers',['Unknown'])[0])[:120]
                    +'\nCross-check against the actual book.')
        except (requests.RequestException,ValueError,IndexError,TypeError,KeyError):
            return 'ISBN metadata service unavailable. Try again later.'
    raise StudyInputError('Send a DOI (10.1234/abc) or ISBN-10/ISBN-13, not a URL.')


def _syllabus(uid, command):
    db=_db(); arg=command.strip()
    if arg.lower().startswith('done '):
        ident=arg[5:].strip()
        if not re.fullmatch(r'[0-9a-f-]{36}',ident,re.I):raise StudyInputError('Use done followed by the full topic ID.')
        db.table('v9_syllabus_topics').update({'completed':True}).eq('id',ident).eq('user_id',uid).execute()
    if arg.lower().startswith('add:'):
        topics=syllabus_lines(arg[4:].strip())
        for item in topics:
            db.table('v9_syllabus_topics').insert({'id':str(uuid.uuid4()),'user_id':uid,'title':item}).execute()
    rows=(db.table('v9_syllabus_topics').select('id,title,completed').eq('user_id',uid)
          .order('created_at').limit(70).execute()).data or []
    if not rows:return '📖 No syllabus topics. Send add: then one topic per line.'
    done=sum(bool(r['completed']) for r in rows)
    return ('📖 Syllabus progress: '+f'{done}/{len(rows)} completed\n'+
            '\n'.join(('✅ ' if r['completed'] else '⬜ ')+r['title'][:80]+' ['+r['id'][:8]+']' for r in rows[:35])+
            '\n\nTo complete one topic, send done FULL-UUID (use /v9syllabus_ids for IDs).')


def _mistakes(uid, command):
    db=_db(); value=command.strip()
    if value.lower().startswith('add:'):
        parts=[p.strip() for p in value[4:].split('|')]
        if len(parts)!=3 or any(not x for x in parts): raise StudyInputError('Use add: Topic | Question | Correct answer')
        if any(len(x)>350 for x in parts): raise StudyInputError('Each field must be under 350 characters.')
        db.table('v9_mistakes').insert({'id':str(uuid.uuid4()),'user_id':uid,'topic':parts[0],
                                       'question':parts[1],'answer':parts[2]}).execute()
    elif value.lower().startswith('mastered '):
        ident=value[9:].strip()
        if not re.fullmatch(r'[0-9a-f-]{36}',ident,re.I):raise StudyInputError('Use mastered FULL-UUID')
        db.table('v9_mistakes').update({'mastered':True}).eq('user_id',uid).eq('id',ident).execute()
    rows=(db.table('v9_mistakes').select('id,topic,question,answer,mastered').eq('user_id',uid)
          .eq('mastered',False).order('created_at',desc=True).limit(12).execute()).data or []
    if not rows:return '📓 No open mistakes. Send add: Topic | Wrong question | Correct answer.'
    return ('📓 Mistake Notebook\n'+'\n\n'.join(f'{r["topic"][:45]}: {r["question"][:110]}\n✓ {r["answer"][:150]}' for r in rows[:8])
           +'\n\nUse /v9mistake_ids for IDs, then mastered FULL-UUID.')


def _focus(uid,cmd):
    db=_db(); command=cmd.strip().lower()
    if command.startswith('start '):
        try:minutes=int(command[6:].strip())
        except ValueError:raise StudyInputError('Use start 25 (5–90 minutes).')
        if not 5<=minutes<=90:raise StudyInputError('Timer must be 5–90 minutes.')
        now=datetime.now(timezone.utc)
        db.table('v9_focus_sessions').insert({'id':str(uuid.uuid4()),'user_id':uid,'starts_at':now.isoformat(),
             'ends_at':(now+timedelta(minutes=minutes)).isoformat(),'minutes':minutes}).execute()
    rows=(db.table('v9_focus_sessions').select('id,starts_at,ends_at,minutes,completed')
          .eq('user_id',uid).eq('completed',False).order('starts_at',desc=True).limit(1).execute()).data or []
    if not rows:return '🍅 No active focus session. Send start 25.'
    item=rows[0]
    end=datetime.fromisoformat(item['ends_at'].replace('Z','+00:00'))
    remaining=int((end-datetime.now(timezone.utc)).total_seconds())
    if command == 'finish':
        if remaining>0:return f'⏳ {max(1,(remaining+59)//60)} min remaining. Continue studying; use status to check.'
        db.table('v9_focus_sessions').update({'completed':True}).eq('user_id',uid).eq('id',item['id']).execute()
        return f'✅ Focus session completed: {item["minutes"]} minutes.'
    return (f'🍅 Focus: {"Ready to finish" if remaining<=0 else str((remaining+59)//60)+" min remaining"}.\n'
            'Send finish when time is up. This is a checkable timer, not a scheduled Telegram notification.')


def _rooms(uid, command):
    db=_db(); val=command.strip()
    if val.lower().startswith('create:'):
        title=val[7:].strip()[:70]
        if len(title)<4:raise StudyInputError('Use create: Biology Revision')
        token=secrets.token_hex(8).upper()
        ident=str(uuid.uuid4())
        db.table('v9_study_rooms').insert({'id':ident,'creator_id':uid,'title':title,'join_code':token}).execute()
        db.table('v9_room_members').insert({'room_id':ident,'user_id':uid}).execute()
        return f'👥 Room: {title}\nInvite code: {token}\nShare it privately with approved adult testers. Send join: CODE to join.'
    if val.lower().startswith('join:'):
        token=val[5:].strip().upper()
        if not re.fullmatch('[0-9A-F]{16}', token):raise StudyInputError('Invalid join code.')
        found=(db.table('v9_study_rooms').select('id,title').eq('join_code',token).eq('active',True)
               .limit(1).execute()).data or []
        if not found:return 'Room not found or disabled.'
        db.table('v9_room_members').upsert({'room_id':found[0]['id'],'user_id':uid},on_conflict='room_id,user_id').execute()
        return '✅ Joined room: '+found[0]['title'][:70]
    if val.lower().startswith('post:'):
        parts=[x.strip() for x in val[5:].split('|',1)]
        if len(parts)!=2 or len(parts[1])>600 or not parts[1]:raise StudyInputError('Use post: ROOM-UUID | Study note')
        room=parts[0]
        allowed=(db.table('v9_room_members').select('room_id').eq('user_id',uid).eq('room_id',room).limit(1).execute()).data or []
        if not allowed:return '🔒 Join this room before posting.'
        db.table('v9_room_notes').insert({'id':str(uuid.uuid4()),'room_id':room,'user_id':uid,'body':parts[1]}).execute()
        return '✅ Note shared with room members.'
    memberships=(db.table('v9_room_members').select('room_id').eq('user_id',uid).limit(15).execute()).data or []
    if not memberships:return '👥 No rooms yet. Send create: Topic Name or join: INVITE_CODE.'
    lines=[]
    for m in memberships[:10]:
        rows=(db.table('v9_study_rooms').select('title,id').eq('id',m['room_id']).eq('active',True).limit(1).execute()).data or []
        if rows: lines.append(f'{rows[0]["title"][:60]} — {rows[0]["id"]}')
    return '👥 Your rooms:\n'+'\n'.join(lines)+'\nPost with: post: ROOM-UUID | Your note\nTo read: read: ROOM-UUID' if not val.lower().startswith('read:') else _read_room(uid,val[5:].strip())


def _read_room(uid,room):
    db=_db()
    member=(db.table('v9_room_members').select('room_id').eq('room_id',room).eq('user_id',uid).limit(1).execute()).data or []
    if not member:return '🔒 Join the room first.'
    active=(db.table('v9_study_rooms').select('id').eq('id',room).eq('active',True).limit(1).execute()).data or []
    if not active:return 'Room is no longer active.'
    rows=(db.table('v9_room_notes').select('body,created_at').eq('room_id',room)
          .order('created_at',desc=True).limit(8).execute()).data or []
    return '👥 Recent room notes:\n'+'\n'.join('• '+r['body'][:300] for r in rows) if rows else 'No notes in this room.'


def register_v9_handlers(bot, show_main_menu):
    if not enabled(): return
    def send(m,s):_safe_send(bot,m.chat.id,s)
    def require(m):
        if not _private(m):send(m,'🔒 V9 personal tools work only in private chat.');return False
        if not allowed(m.from_user.id):send(m,'🔒 V9 access requires approved pilot access or verified adult eligibility.');return False
        return True
    def hub(m):
        if not require(m):return
        _clear(m.from_user.id)
        kb=types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=2)
        labels=list(OPTIONS)
        for i in range(0,len(labels),2):kb.row(*(types.KeyboardButton(label) for label in labels[i:i+2]))
        kb.row(types.KeyboardButton('🏠 Main Menu'))
        bot.send_message(m.chat.id,'🧰 V9 Academic Toolkit — 14 student tools.\n'
            'OCR photos are shared with OCR.space ONLY after explicit consent. '
            'Photo math/diagram functions read labels, not full visual reasoning.\n'
            'Type /v9cancel to clear a session.',reply_markup=kb)
    @bot.message_handler(commands=['v9'])
    def command_hub(m):hub(m)
    @bot.message_handler(func=lambda m:getattr(m,'text','')==HUB)
    def button_hub(m):hub(m)

    def choose(m,kind):
        if not require(m):return
        uid=m.from_user.id;_clear(uid)
        if kind in ('math','syllabus','mistakes','focus','verify','rooms'):
            _set(uid,{'kind':kind,'stage':'text'})
            help_text={
              'math':'📸 Math Solver: send an equation like 2*x+3=11, or send a JPG photo. Photo OCR needs your consent.',
              'syllabus':'📖 Syllabus: send add: followed by one topic per line. Send list or done FULL-UUID.',
              'mistakes':'📓 Mistakes: send add: Topic | Question | Correct answer. Send list or mastered FULL-UUID.',
              'focus':'🍅 Focus Timer: send start 25, status or finish. Timer checks when you ask; no automatic alerts.',
              'verify':'🔍 Citation Verifier: send a DOI (10.1234/example) or ISBN (978...). Looks up public metadata.',
              'rooms':'👥 Study Rooms: send create: Topic, join: CODE, list, post: ROOM-UUID | Note or read: ROOM-UUID.'}[kind]
            send(m,help_text)
        elif kind in ('diagram','timetable'):
            _set(uid,{'kind':kind,'stage':'photo'})
            send(m,'🖼 Send a clear JPG/PNG photo (under 950 KB). OCR is optional and requires explicit consent. '
                   +('Diagram tool reads text labels only; visual relationships are not interpreted.' if kind=='diagram'
                     else 'Recognized timetable entries will be shown for confirmation before saving.'))
        elif kind=='anki':
            try:
                from flashcards import get_flashcards
                data=get_flashcards(uid,limit=200)
                if not data:send(m,'No flashcards found. Create cards with 🧠 Flashcards first.');return
                buff=prepare_deck([(r.get('question',''),r.get('answer','')) for r in data])
                _send_file(bot,m.chat.id,buff,'📤 Anki TSV import. Anki → Import → select file. Columns: Front, Back.')
            except Exception:send(m,'⚠️ Could not export flashcards. Check the existing flashcards database.')
        else:
            _set(uid,{'kind':kind,'stage':'upload1'})
            desc={
                'mindmap':'🧠 Upload lecture notes (PDF/DOCX/TXT) for a simple PNG topic map.',
                'ppt':'📊 Upload lecture notes for an editable PPTX slide deck (up to 11 slides).',
                'assignment':'📋 Upload your assignment to check basic structure and approximate word count.',
                'formula':'🧮 Upload lecture notes to extract possible formulas into DOCX.',
                'compare':'🔎 Upload the FIRST PDF/DOCX/TXT; then send the SECOND document.'}[kind]
            send(m,desc+' Max 8 MB; readable text required.')

    @bot.message_handler(func=lambda m:getattr(m,'text',None) in OPTIONS)
    def menu_feature(m):choose(m,OPTIONS[m.text])

    @bot.message_handler(commands=['v9cancel'])
    def cancel(m):
        _clear(m.from_user.id);send(m,'✅ V9 temporary upload/session cleared.')

    @bot.message_handler(commands=['v9syllabus_ids','v9mistake_ids'])
    def ids(m):
        if not require(m):return
        uid=m.from_user.id; is_syllabus=m.text.split()[0].startswith('/v9syllabus')
        table='v9_syllabus_topics' if is_syllabus else 'v9_mistakes'
        try:
            rows=(_db().table(table).select('id,title' if is_syllabus else 'id,topic')
                  .eq('user_id',uid).limit(30).execute()).data or []
            send(m,'\n'.join(f'{r["id"]} — {r.get("title") or r.get("topic")}' for r in rows) or 'No records.')
        except Exception:send(m,'⚠️ Could not retrieve IDs.')

    @bot.message_handler(func=lambda m:_private(m) and bool(_get(m.from_user.id)),content_types=['document'])
    def file_handler(m):
        if not require(m):return
        uid=m.from_user.id;st=_get(uid)
        if not st or st.get('stage') not in ('upload1','upload2'):return ContinueHandling()
        doc=m.document
        if not doc or not str(doc.file_name or '').lower().endswith(('.pdf','.docx','.txt')):
            send(m,'Send PDF, DOCX or UTF-8 TXT.');return
        if not doc.file_size or doc.file_size>MAX_FILE_BYTES:
            send(m,'File must be 1 byte–8 MB.');return
        try:
            info=bot.get_file(doc.file_id)
            if info.file_size and info.file_size>MAX_FILE_BYTES:raise StudyInputError('File too large.')
            data=bot.download_file(info.file_path)
            text=read_text(doc.file_name,data)
            kind=st['kind']
            if kind=='compare':
                if st['stage']=='upload1':
                    _set(uid,{'kind':kind,'stage':'upload2','first':text})
                    send(m,'✅ First document read. Send the SECOND PDF, DOCX or TXT.');return
                send(m,document_diff(st['first'],text));_clear(uid);return
            _clear(uid)
            if kind=='mindmap':
                out=mindmap_png('Study Topic Map',mindmap_topics(text))
                bot.send_photo(m.chat.id,out,caption='🧠 Heuristic topic map. Verify the topics against your notes.')
            elif kind=='ppt':
                out,count=presentation_pptx(text)
                _send_file(bot,m.chat.id,out,f'📊 Editable presentation: {count} slides. Review all contents.')
            elif kind=='formula':
                lines=formula_lines(text)
                if not lines:send(m,'No candidate formula lines found.');return
                _send_file(bot,m.chat.id,formula_docx(lines),f'🧮 Found {len(lines)} candidate formulas. Check the originals.')
            elif kind=='assignment':
                send(m,assignment_report(doc.file_name,data))
        except StudyInputError as exc:send(m,'⚠️ '+str(exc))
        except Exception:send(m,'⚠️ Unable to process that document. Existing tools are unaffected.')

    @bot.message_handler(func=lambda m:_private(m) and bool(_get(m.from_user.id)),content_types=['photo'])
    def photo_handler(m):
        if not require(m):return
        st=_get(m.from_user.id)
        if not st or st.get('kind') not in ('math','diagram','timetable') or st.get('stage') not in ('text','photo'):
            return ContinueHandling()
        try:
            image=m.photo[-1]
            if image.file_size and image.file_size>950_000:raise StudyInputError('Send a JPG under 950 KB.')
            info=bot.get_file(image.file_id)
            data=bot.download_file(info.file_path)
            if len(data)>950_000:raise StudyInputError('Send a smaller photo.')
            _set(m.from_user.id,{'kind':st['kind'],'stage':'ocr_consent','data':data})
            send(m,'🔒 OCR consent: This photo will be transmitted to OCR.space (an external service) '
                   'to extract text. Reply exactly I AGREE OCR to proceed, or /v9cancel.')
        except StudyInputError as exc:send(m,'⚠️ '+str(exc))
        except Exception:send(m,'⚠️ Could not read the image.')

    @bot.message_handler(func=lambda m:_private(m) and bool(_get(m.from_user.id)) and bool(getattr(m,'text',None)))
    def text_handler(m):
        if not require(m):return
        uid=m.from_user.id;st=_get(uid)
        if not st:return ContinueHandling()
        value=(m.text or '').strip()
        if value.startswith('/') or value=='🏠 Main Menu' or value in OPTIONS or value==HUB:
            _clear(uid);return ContinueHandling()
        kind=st['kind']
        try:
            if st['stage']=='ocr_consent':
                if value != 'I AGREE OCR':
                    _clear(uid);send(m,'OCR cancelled. Your photo was not sent.');return
                _clear(uid)
                text=_read_ocr(st['data'],'photo.jpg')
                if kind=='math':send(m,'🧾 OCR extracted: '+text[:170]+'\n\n'+math_solution(text.splitlines()[0][:105]));return
                if kind=='diagram':send(m,diagram_labels(text));return
                matches=parse_timetable(text)
                if not matches:
                    send(m,'No timetable rows detected. Expected: Mon 09:00-10:30 Biology. '
                            'Try better contrast or use Timetable to enter manually.');return
                preview='\n'.join(f'{row[0]} {row[1]}–{row[2]} {row[3]}' for row in matches)
                _set(uid,{'kind':'timetable','stage':'confirm','entries':matches})
                send(m,'🖼 Proposed timetable entries (day numbers 0=Mon):\n'+preview[:2300]
                        +'\n\nReply exactly SAVE TIMETABLE to add these entries to your timetable; or anything else to cancel.')
                return
            if st['stage']=='confirm' and kind=='timetable':
                _clear(uid)
                if value!='SAVE TIMETABLE':send(m,'No entries saved.');return
                from timetable import create_timetable_entry
                saved=0
                for day,a,b,title in st['entries']:
                    create_timetable_entry(uid,None,title,day,a,b);saved+=1
                send(m,f'✅ Added {saved} timetable entries. Review under 📅 Timetable.');return
            if st['stage']!='text':send(m,'Send the requested document/photo first or use /v9cancel.');return
            if kind=='math':send(m,math_solution(value))
            elif kind=='verify':send(m,verify_reference(value));_clear(uid)
            elif kind=='syllabus':send(m,_syllabus(uid,value))
            elif kind=='mistakes':send(m,_mistakes(uid,value))
            elif kind=='focus':send(m,_focus(uid,value))
            elif kind=='rooms':send(m,_rooms(uid,value))
        except StudyInputError as exc:send(m,'⚠️ '+str(exc))
        except Exception:send(m,'⚠️ The operation could not complete. Check database setup, connectivity or input.')
