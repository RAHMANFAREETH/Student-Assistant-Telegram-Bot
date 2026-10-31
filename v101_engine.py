"""Bounded, offline V10.1 study functions; no network or user data sharing."""
from __future__ import annotations
import json, re, unicodedata
from datetime import datetime, timezone
from v10_engine import StudyError, words

LANGS={'en':'English','ta':'Tamil','si':'Sinhala','ar':'Arabic',
       'english':'English','tamil':'Tamil','sinhala':'Sinhala','arabic':'Arabic'}

def clean(value, cap=300):
    return ' '.join(str(value or '').split())[:cap]

def language(value):
    key=clean(value,20).lower()
    if key not in LANGS:raise StudyError('Choose English, Tamil, Sinhala, or Arabic.')
    return LANGS[key]

def topic(value):
    result=clean(value,180)
    if not 3<=len(result)<=180:raise StudyError('Provide a topic/question of 3–180 characters.')
    return result

def sources(evidence, limit=4, body_cap=550):
    out=[]
    for index, item in enumerate(list(evidence or [])[:limit],1):
        body=clean(item.get('body'),body_cap)
        if body:
            out.append(f'[S{index}] {clean(item.get("title","Document"),65)}, page {item.get("page_number",1)}: {body}')
    return out

def citations(evidence):
    return '\n'.join(s.split(': ',1)[0] for s in sources(evidence))

def extract_json(raw):
    text=str(raw or '').strip()
    if text.startswith('```'):
        text=re.sub(r'^```(?:json)?\s*','',text,flags=re.I).rsplit('```',1)[0].strip()
    if not text.startswith('{'):
        a,b=text.find('{'),text.rfind('}')
        if a<0 or b<a:raise StudyError('Gemini did not return structured study questions. Try again.')
        text=text[a:b+1]
    try:return json.loads(text)
    except (ValueError,TypeError):raise StudyError('Gemini did not return valid study JSON. Try again.') from None

def validate_mock(raw):
    obj=extract_json(raw)
    questions=obj.get('questions',[]) if isinstance(obj,dict) else []
    if not isinstance(questions,list) or len(questions)!=3:raise StudyError('Gemini must return exactly three questions.')
    output=[]
    for row in questions:
        if not isinstance(row,dict):raise StudyError('Invalid quiz question format.')
        question=clean(row.get('question'),320)
        options=row.get('options')
        answer=str(row.get('answer','')).strip().upper()
        if not 8<=len(question)<=320 or not isinstance(options,list) or len(options)!=4 or answer not in 'ABCD' or len(answer)!=1:
            raise StudyError('Invalid quiz question or answer.')
        options=[clean(x,140) for x in options]
        if any(not x for x in options):raise StudyError('Missing quiz option.')
        output.append({'question':question,'options':options,'answer':answer,'explanation':clean(row.get('explanation'),220)})
    return output

def validate_cards(raw):
    obj=extract_json(raw)
    cards=obj.get('cards',[]) if isinstance(obj,dict) else []
    if not isinstance(cards,list) or not 1<=len(cards)<=5:raise StudyError('Gemini must return one to five cards.')
    result=[]; seen=set()
    for c in cards:
        if not isinstance(c,dict):raise StudyError('Invalid card data.')
        q,a=clean(c.get('question'),280),clean(c.get('answer'),440)
        if len(q)<8 or len(a)<3 or q.lower() in seen:raise StudyError('Invalid or duplicate card.')
        seen.add(q.lower());result.append({'question':q,'answer':a})
    return result

def grade_mock(questions, answer_string):
    answers=re.findall(r'[ABCD]',str(answer_string).upper())
    if len(answers)!=len(questions):raise StudyError('Reply with exactly three letters, e.g., /v101submit A B C.')
    score=0;mistakes=[];lines=[]
    for i,(q,chosen) in enumerate(zip(questions,answers),1):
        correct=chosen==q['answer'];score+=correct
        lines.append(f'{i}. {"✅" if correct else "❌"} {chosen} (correct: {q["answer"]}). {q["explanation"]}')
        if not correct:mistakes.append({'question':q['question'],'correct_answer':q['options']['ABCD'.index(q['answer'])]})
    return score,lines,mistakes

def roadmap(days, subject, minutes, priorities=()):
    try: days,minutes=int(days),int(minutes)
    except (ValueError,TypeError):raise StudyError('Days and minutes must be numbers.') from None
    if days not in (7,14,30) or not 15<=minutes<=240:raise StudyError('Choose 7, 14 or 30 days, and 15–240 minutes daily.')
    subject=topic(subject)
    items=[clean(x,95) for x in list(priorities or [])[:12] if clean(x)]
    if not items:items=[f'Learn fundamentals of {subject}',f'Practise {subject} examples',f'Self-test {subject}']
    plan=[]
    for d in range(1,days+1):
        exercise=items[(d-1)%len(items)]
        stage='Review and self-test' if d%7==0 else 'Learn / practise'
        plan.append(f'Day {d}: {stage} — {exercise} ({minutes} min)')
    return plan

def summary_from_evidence(rows, max_chars=950):
    snippets=[]
    for row in rows[:3]:
        body=clean(row.get('body'),550)
        if body: snippets.append(body)
    text=' '.join(snippets)
    if not text:raise StudyError('No matching saved notes. Upload and save study material first.')
    # Extractive summary, not generated or guaranteed comprehensive.
    sentences=re.split(r'(?<=[.!?])\s+',text)
    return ' '.join(sentences[:6])[:max_chars]

def compare_passages(rows):
    by_doc={}
    for row in rows:
        ident=str(row.get('document_id',''))
        if ident not in by_doc and clean(row.get('body')):by_doc[ident]=row
    if len(by_doc)<2:raise StudyError('Comparison needs relevant excerpts from two different saved documents.')
    chosen=list(by_doc.values())[:3]
    tokens=[set(words(x.get('body',''))) for x in chosen]
    shared=set.intersection(*tokens) if tokens else set()
    lines=['📚 Source comparison (keyword overlap, not fact-checking):']
    for index,item in enumerate(chosen,1):
        lines.append(f'[{index}] {clean(item.get("title"),65)}, p.{item.get("page_number",1)}: {clean(item.get("body"),420)}')
    lines.append('Shared terms: '+(', '.join(sorted(shared)[:14]) or 'No strong lexical overlap.'))
    lines.append('Different wording does not prove a contradiction. Inspect the original sources.')
    return '\n\n'.join(lines)

def claim_support(claim, rows):
    claim=topic(claim)
    terms=set(words(claim))
    if not rows:return 'No matching saved-document excerpts. This claim is NOT verified.'
    results=[]
    for i,row in enumerate(rows[:4],1):
        body=set(words(row.get('body','')))
        common=terms & body
        coverage=len(common)/max(1,len(terms))
        results.append(f'[S{i}] {clean(row.get("title"),65)} p.{row.get("page_number",1)}: '+
                       f'{len(common)}/{len(terms)} claim terms overlap ({coverage:.0%}).')
    return ('🔎 Source support screening (lexical only):\n'+'\n'.join(results)+
            '\n⚠️ Word overlap is NOT proof of factual accuracy, entailment, or correct citations. ' +
            'Inspect the cited pages for full context and contradictions.')
