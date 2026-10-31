"""V10.1 Supabase operations: owner-scoped by Telegram UID, no document sharing."""
from __future__ import annotations
import secrets
from uuid import uuid4
from datetime import datetime,timezone
from v10_engine import StudyError,rank_chunks,MAX_CHUNKS,MAX_DOCUMENTS
from v10_store import list_documents
from v101_engine import clean


def _db():
    from db import supabase
    return supabase

def chat_history(uid, db=None):
    db=db or _db()
    query=(db.table('v101_chat_turns').select('question,answer,created_at')
           .eq('user_id',int(uid)).gte('expires_at',datetime.now(timezone.utc).isoformat()).order('created_at',desc=True).limit(3).execute())
    return list(reversed(query.data or []))

def append_chat(uid, question, answer, db=None):
    db=db or _db()
    db.table('v101_chat_turns').insert({'id':str(uuid4()),'user_id':int(uid),
        'question':clean(question,350),'answer':clean(answer,2500)}).execute()
    return True

def forget_chat(uid,db=None):
    db=db or _db()
    db.table('v101_chat_turns').delete().eq('user_id',int(uid)).execute()
    return True

def create_plan(uid,subject,days,minutes,lines,db=None):
    db=db or _db()
    db.table('v101_plans').upsert({'user_id':int(uid),'subject':clean(subject,180),
        'days':int(days),'minutes_per_day':int(minutes),'plan':list(lines),
        'updated_at':datetime.now(timezone.utc).isoformat()},on_conflict='user_id').execute()
    return True

def get_plan(uid,db=None):
    db=db or _db()
    response=(db.table('v101_plans').select('subject,days,minutes_per_day,plan')
              .eq('user_id',int(uid)).limit(1).execute())
    return (response.data or [None])[0]

def save_mistakes(uid, mistakes, db=None):
    if not mistakes:return
    db=db or _db()
    items=[{'id':str(uuid4()),'user_id':int(uid),'question':clean(x['question'],320),
            'correct_answer':clean(x['correct_answer'],440)} for x in mistakes[:3]]
    db.table('v101_mock_mistakes').insert(items).execute()

def save_cards(uid,cards,db=None):
    db=db or _db()
    # Adds to the existing flashcards table, so /v10due shows them automatically.
    if not 1<=len(cards)<=5:raise StudyError('Only 1–5 flashcards at once.')
    payload=[{'user_id':int(uid),'subject_id':None,
              'question':clean(x['question'],280),'answer':clean(x['answer'],440)} for x in cards]
    result=db.table('flashcards').insert(payload).execute()
    return len(result.data or [])

def compare_rows(uid, query, db=None):
    db=db or _db();docs=list_documents(uid,db)
    allowed={str(x['id']):x for x in docs}
    if len(allowed)<2:raise StudyError('Save at least two documents before comparing them.')
    response=(db.table('v10_document_chunks').select('document_id,page_number,body')
        .eq('user_id',int(uid)).limit(MAX_DOCUMENTS*MAX_CHUNKS).execute())
    results=[]
    for row in response.data or []:
        doc=allowed.get(str(row.get('document_id')))
        if doc:results.append({**row,'title':doc.get('title','Document')})
    # Ranked per doc, so the top-ranked single file cannot dominate the result.
    selections=[]
    for doc_id in allowed:
        ranked=rank_chunks([r for r in results if str(r['document_id'])==doc_id],query,limit=1)
        if ranked:selections.append(ranked[0])
    return sorted(selections,key=lambda row:-float(row.get('score',0)))[:3]

# Room shares only opted-in goals/quiz results. Never document excerpts, chat or voice.

def create_room(uid,goal,db=None):
    db=db or _db()
    # Cryptographically unpredictable invitation. A room can be joined only with full code.
    for _ in range(3):
        code=secrets.token_urlsafe(12).replace('-','A').replace('_','B')[:16]
        try:
            db.table('v101_rooms').insert({'code':code,'owner_user_id':int(uid),'goal':clean(goal,140)}).execute()
            db.table('v101_room_members').insert({'room_code':code,'user_id':int(uid)}).execute()
            return code
        except Exception:
            # Never claim room creation succeeded on a partial write. Clean up just this room.
            try:db.table('v101_rooms').delete().eq('code',code).eq('owner_user_id',int(uid)).execute()
            except Exception:pass
            raise
    raise StudyError('Could not create study room.')

def room_for_user(uid,db=None):
    db=db or _db()
    rows=(db.table('v101_room_members').select('room_code').eq('user_id',int(uid))
          .order('joined_at',desc=True).limit(1).execute()).data or []
    if not rows:return None
    code=rows[0]['room_code']
    rr=(db.table('v101_rooms').select('code,goal,owner_user_id')
        .eq('code',code).limit(1).execute()).data or []
    return rr[0] if rr else None

def join_room(uid,code,db=None):
    db=db or _db()
    result=db.rpc('v101_join_study_room', {'p_user_id':int(uid),'p_code':code}).execute().data
    if isinstance(result,list):result=result[0] if result else None
    if isinstance(result,dict):result=result.get('v101_join_study_room')
    if result not in ('joined','already_member','full','missing','already_in_room'):
        raise StudyError('Study room temporarily unavailable.')
    return result

def leave_room(uid,db=None):
    db=db or _db();r=room_for_user(uid,db)
    if not r:raise StudyError('You are not in a study room.')
    if int(r['owner_user_id'])==int(uid):
        db.table('v101_rooms').delete().eq('code',r['code']).eq('owner_user_id',int(uid)).execute()
        return 'Room closed by its owner.'
    db.table('v101_room_members').delete().eq('user_id',int(uid)).eq('room_code',r['code']).execute()
    return 'You left the room.'

def room_status(uid,db=None):
    db=db or _db();r=room_for_user(uid,db)
    if not r:return None
    members=(db.table('v101_room_members').select('user_id',count='exact')
             .eq('room_code',r['code']).execute())
    return {**r,'members':members.count if members.count is not None else len(members.data or [])}

def new_room_quiz(uid,question,answer,db=None):
    db=db or _db();room=room_for_user(uid,db)
    if not room or int(room['owner_user_id'])!=int(uid):raise StudyError('Only the room owner may create a shared quiz.')
    quiz_id=str(uuid4())
    db.table('v101_room_quizzes').insert({'id':quiz_id,'room_code':room['code'],
        'question':clean(question,320),'answer':clean(answer,160)}).execute()
    return quiz_id

def active_quiz(room_code,db=None):
    db=db or _db()
    rows=(db.table('v101_room_quizzes').select('id,question,answer').eq('room_code',room_code)
          .order('created_at',desc=True).limit(1).execute()).data or []
    return rows[0] if rows else None

def submit_room_answer(uid,reply,db=None):
    db=db or _db();room=room_for_user(uid,db)
    if not room:raise StudyError('Join a room first.')
    quiz=active_quiz(room['code'],db)
    if not quiz:raise StudyError('No room quiz is available.')
    is_correct=clean(reply,160).casefold()==clean(quiz['answer'],160).casefold()
    # First answer counts; unique key prevents retry score inflation.
    existing=(db.table('v101_room_answers').select('user_id').eq('quiz_id',quiz['id'])
              .eq('user_id',int(uid)).limit(1).execute()).data or []
    if existing:raise StudyError('Your answer for this quiz is already recorded.')
    db.table('v101_room_answers').insert({'quiz_id':quiz['id'],'user_id':int(uid),
        'is_correct':is_correct}).execute()
    return is_correct

def room_score(uid,db=None):
    db=db or _db();room=room_for_user(uid,db)
    if not room:raise StudyError('Join a room first.')
    quizzes=(db.table('v101_room_quizzes').select('id').eq('room_code',room['code']).limit(30).execute()).data or []
    if not quizzes:return {'questions':0,'answers':0,'correct':0}
    quiz_ids=[x['id'] for x in quizzes]
    answers=(db.table('v101_room_answers').select('quiz_id,is_correct')
             .in_('quiz_id',quiz_ids).limit(360).execute()).data or []
    return {'questions':len(quizzes),'answers':len(answers),'correct':sum(x.get('is_correct') is True for x in answers)}
