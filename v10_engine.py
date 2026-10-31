"""V10.0 bounded, offline learning utilities. Not an AI model or an exam grader."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from collections import Counter
import math
import re
import unicodedata

MAX_DOCUMENTS = 6
MAX_CHUNKS = 40
MAX_CHARACTERS = 45000
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
WORD = re.compile(r"[^\W_]{2,}", re.UNICODE)
STOP = {'the','and','for','with','what','from','this','that','are','how','why','does','about','which','when','your','into','you','please','explain','describe','given'}

class StudyError(ValueError):
    pass


def words(value):
    # Preserve Unicode combining marks: Tamil, Sinhala and Arabic words often
    # contain vowel signs/harakat which a plain regex\w splits incorrectly.
    collected, current = [], []
    for ch in str(value or ''):
        if unicodedata.category(ch)[:1] in ('L', 'N', 'M'):
            current.append(ch)
        elif current:
            collected.append(''.join(current).lower()); current=[]
    if current: collected.append(''.join(current).lower())
    return [x for x in collected if x not in STOP and len(x)>=2]


def split_pages(pages, limit=1300):
    """Keep natural page references, hard-bound total storage and chunk size."""
    result, remaining = [], MAX_CHARACTERS
    for page, raw in pages:
        try: n = int(page)
        except (ValueError, TypeError): raise StudyError('Invalid page number.')
        if n < 1: raise StudyError('Invalid page number.')
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', str(raw or ''))
        text = re.sub(r'\s+', ' ', text).strip()
        text = text[:remaining]
        remaining -= len(text)
        while text and len(result) < MAX_CHUNKS:
            if len(text) <= limit: part, text = text, ''
            else:
                cut = text.rfind(' ', max(200,limit-180),limit+1)
                if cut < 200: cut = limit
                part, text = text[:cut], text[cut:].lstrip()
            if part.strip(): result.append({'page_number':n,'body':part.strip()})
        if remaining <= 0 or len(result) >= MAX_CHUNKS: break
    if sum(len(x['body']) for x in result) < 30:
        raise StudyError('Document needs at least 30 readable characters. Use the OCR tools for scanned PDFs.')
    return result


def rank_chunks(chunks, question, limit=4):
    question = str(question or '').strip()
    if not 3 <= len(question) <= 350: raise StudyError('Question must be 3–350 characters.')
    terms = set(words(question))
    if not terms: raise StudyError('Ask a question with specific study keywords.')
    result=[]
    for item in chunks:
        body=str(item.get('body') or '')
        frequency=Counter(words(body))
        hits=sum(min(frequency.get(t,0),3) for t in terms)
        if hits:
            coverage=len(terms & frequency.keys()) / len(terms)
            score=hits + coverage*5 - 0.00005*len(body)
            result.append({**item,'score':score})
    result.sort(key=lambda i:(-i['score'],str(i.get('document_id','')),int(i.get('page_number',1))))
    return result[:max(1,min(6,limit))]


def revise_plan(mistakes, topics, cards, limit=7):
    """Heuristic priority based on existing user-owned study records; not ML."""
    out=[]
    for m in mistakes:
        if m.get('mastered'): continue
        topic=' '.join(str(m.get('topic') or 'Mistake').split())[:70]
        out.append((100, f'🔴 Correct an earlier mistake: {topic}'))
    for card in cards:
        q=' '.join(str(card.get('question') or 'Flashcard').split())[:65]
        wrong=max(0,int(card.get('wrong_count') or 0))
        correct=max(0,int(card.get('correct_count') or 0))
        if wrong>0 or correct==0:
            out.append((80 + min(wrong,12)*2 - min(correct,5),f'🟠 Review flashcard: {q}'))
    for topic in topics:
        if topic.get('completed'): continue
        name=' '.join(str(topic.get('title') or 'Syllabus topic').split())[:70]
        out.append((60, f'🟡 Continue syllabus: {name}'))
    out.sort(key=lambda item:-item[0])
    result=[]; seen=set()
    for _,msg in out:
        if msg in seen: continue
        seen.add(msg); result.append(msg)
        if len(result)>=limit: break
    return result


def viva_prompt(topic, mistakes, excerpts):
    topic=' '.join(str(topic or '').split())[:90]
    if not 3<=len(topic)<=90: raise StudyError('Use /v10viva SUBJECT OR TOPIC (3–90 characters).')
    terms=set(words(topic))
    for m in mistakes:
        text=' '.join(str(m.get('topic') or '').split())
        if not m.get('mastered') and terms.intersection(words(text)) and m.get('question') and m.get('answer'):
            return {'question':str(m['question'])[:350], 'reference':str(m['answer'])[:1000], 'source':'Your Mistake Notebook'}
    if excerpts:
        e=excerpts[0]
        return {'question':f'Explain the main idea about {topic} from your study material.',
                'reference':str(e.get('body') or '')[:900],
                'source':f"{str(e.get('title') or 'Your document')[:60]} — page {e.get('page_number',1)}"}
    raise StudyError('No matching study material. Add a document or a V9 mistake on this topic first.')


def viva_feedback(answer, reference):
    answer=str(answer or '').strip()
    if not 8<=len(answer)<=1400: raise StudyError('Reply using /v10answer YOUR ANSWER (8–1400 characters).')
    expected=set(words(reference)); actual=set(words(answer))
    overlap=sorted(expected & actual)
    ratio=len(overlap)/max(1,min(20,len(expected)))
    if ratio>=0.55: label='Good keyword coverage'
    elif ratio>=0.25: label='Some relevant terminology'
    else: label='Limited keyword overlap'
    return {'label':label,'matched':overlap[:8], 'reference':str(reference)[:800],
            'disclaimer':'This is keyword-based practice feedback, not a reliable assessment of correctness or speaking skill.'}


def next_schedule(prior=None, rating='good', now=None):
    now=now or datetime.now(timezone.utc)
    rating=str(rating or '').lower().strip()
    if rating not in ('again','hard','good','easy'):
        raise StudyError('Rating must be again, hard, good or easy.')
    interval=max(0,int((prior or {}).get('interval_days') or 0))
    repetitions=max(0,int((prior or {}).get('repetitions') or 0))
    if rating=='again': interval,repetitions=1,0
    elif rating=='hard': interval,repetitions=max(1,math.ceil(interval*1.2)),repetitions+1
    elif rating=='good': interval,repetitions=(1 if not interval else max(2,math.ceil(interval*2.0))),repetitions+1
    else: interval,repetitions=(3 if not interval else max(4,math.ceil(interval*2.6))),repetitions+1
    interval=min(180,interval)
    return {'interval_days':interval,'repetitions':repetitions,
            'due_at':(now+timedelta(days=interval)).isoformat(), 'last_rating':rating,
            'reviewed_at':now.isoformat()}


def due(now, row):
    if not row: return True
    try:
        at=datetime.fromisoformat(str(row['due_at']).replace('Z','+00:00'))
        if at.tzinfo is None: return False
        return at <= now
    except (ValueError, TypeError, KeyError): return False
