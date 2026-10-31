"""V10.0 Supabase operations. Every read/write is scoped to Telegram user_id."""
from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from v10_engine import (StudyError, MAX_DOCUMENTS, MAX_CHUNKS,split_pages,
                        rank_chunks,revise_plan,next_schedule,due)


def _db():
    from db import supabase
    return supabase


def list_documents(uid, db=None):
    db=db or _db()
    r=(db.table('v10_documents').select('id,title,filename,created_at')
       .eq('user_id',int(uid)).order('created_at',desc=True).limit(MAX_DOCUMENTS+2).execute())
    return r.data or []


def save_document(uid, filename, pages, db=None):
    uid=int(uid);db=db or _db()
    if len(list_documents(uid,db))>=MAX_DOCUMENTS:
        raise StudyError(f'Maximum {MAX_DOCUMENTS} saved documents. Delete an old one first.')
    name=str(filename or '').replace('\\','/').split('/')[-1][:120]
    if not name.lower().endswith(('.txt','.pdf','.docx')):
        raise StudyError('Supported files: PDF, DOCX, UTF-8 TXT.')
    chunks=split_pages(pages)
    doc_id=str(uuid4())
    title=name.rsplit('.',1)[0][:100] or 'Study document'
    db.table('v10_documents').insert({'id':doc_id,'user_id':uid,'title':title,'filename':name}).execute()
    try:
        records=[{'id':str(uuid4()),'document_id':doc_id,'user_id':uid,
                  'page_number':item['page_number'],'body':item['body']} for item in chunks]
        # bounded insert. Must never claim success if a chunk insert fails.
        for start in range(0,len(records),15):
            db.table('v10_document_chunks').insert(records[start:start+15]).execute()
    except Exception:
        try: db.table('v10_documents').delete().eq('user_id',uid).eq('id',doc_id).execute()
        except Exception: pass
        raise
    return {'id':doc_id,'title':title,'chunks':len(chunks)}


def remove_document(uid, doc_id, db=None):
    db=db or _db()
    r=(db.table('v10_documents').delete().eq('user_id',int(uid))
       .eq('id',str(doc_id)).select('id').execute())
    return bool(r.data)


def find_evidence(uid, question, db=None):
    db=db or _db()
    docs=list_documents(uid,db)
    if not docs:return []
    ids={str(x['id']):x for x in docs}
    response=(db.table('v10_document_chunks').select('document_id,page_number,body')
              .eq('user_id',int(uid)).limit(MAX_DOCUMENTS*MAX_CHUNKS).execute())
    rows=[]
    for x in response.data or []:
        if str(x.get('document_id')) in ids:
            rows.append({**x,'title':ids[str(x['document_id'])].get('title','Document')})
    return rank_chunks(rows,question)


def coach(uid, db=None):
    db=db or _db();uid=int(uid)
    mistakes=(db.table('v9_mistakes').select('topic,question,answer,mastered')
              .eq('user_id',uid).eq('mastered',False).limit(30).execute()).data or []
    topics=(db.table('v9_syllabus_topics').select('title,completed')
            .eq('user_id',uid).eq('completed',False).limit(30).execute()).data or []
    cards=(db.table('flashcards').select('id,question,correct_count,wrong_count')
           .eq('user_id',uid).limit(60).execute()).data or []
    return revise_plan(mistakes,topics,cards)


def mistakes_for_viva(uid, db=None):
    db=db or _db()
    return ((db.table('v9_mistakes').select('topic,question,answer,mastered')
             .eq('user_id',int(uid)).eq('mastered',False).limit(60).execute()).data or [])


def due_cards(uid, db=None, limit=10, now=None):
    db=db or _db();uid=int(uid);now=now or datetime.now(timezone.utc)
    cards=(db.table('flashcards').select('id,question,answer')
           .eq('user_id',uid).limit(200).execute()).data or []
    rows=(db.table('v10_card_schedule').select('flashcard_id,due_at,interval_days,repetitions')
          .eq('user_id',uid).limit(200).execute()).data or []
    schedules={str(r['flashcard_id']):r for r in rows}
    return [c for c in cards if due(now,schedules.get(str(c['id'])))][:limit]


def get_card(uid, card_id, db=None):
    db=db or _db()
    q=(db.table('flashcards').select('id,question,answer').eq('user_id',int(uid))
       .eq('id',int(card_id)).limit(1).execute())
    return (q.data or [None])[0]


def rate_card(uid,card_id,rating,db=None,now=None):
    db=db or _db();uid=int(uid);card_id=int(card_id)
    card=get_card(uid,card_id,db)
    if not card: raise StudyError('Flashcard not found in your account.')
    result=(db.table('v10_card_schedule').select('interval_days,repetitions')
            .eq('user_id',uid).eq('flashcard_id',card_id).limit(1).execute())
    payload={'user_id':uid,'flashcard_id':card_id,**next_schedule((result.data or [None])[0],rating,now)}
    db.table('v10_card_schedule').upsert(payload,on_conflict='user_id,flashcard_id').execute()
    return payload
