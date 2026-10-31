"""Opt-in V10 Learning Lab; command-first to avoid existing V7/V8/V9 state collisions."""
from __future__ import annotations
import logging, os, threading, time, uuid
from collections import OrderedDict
from v10_engine import (StudyError,MAX_UPLOAD_BYTES,split_pages,viva_prompt,viva_feedback)
from v10_gemini import GeminiStudyError, validate as gemini_validate, generate as gemini_generate, source_key
from v10_store import (list_documents,save_document,remove_document,find_evidence,coach,
                       mistakes_for_viva,due_cards,get_card,rate_card)

LOG=logging.getLogger(__name__)
TTL=600
LOCK=threading.RLock()
STATE=OrderedDict()
TRUTH=('true','yes','1')
BUTTON='🧠 V10 Learning Lab'


def enabled():return os.getenv('V10_ENABLED','').strip().lower() in TRUTH


def authorized(uid):
    if not enabled():return False
    # V8's current authorization is source of truth: pilot or verified_adults.
    from v8_bot import allowed
    return bool(allowed(uid))


def _private(m):
    try:return m.chat.type=='private' and int(m.chat.id)==int(m.from_user.id)
    except (AttributeError,ValueError,TypeError):return False


def _set(uid,data):
    with LOCK:
        now=time.monotonic()
        for k,v in list(STATE.items()):
            if now-v['ts']>TTL:STATE.pop(k,None)
        STATE[int(uid)]={**data,'ts':now}
        STATE.move_to_end(int(uid))
        while len(STATE)>80:STATE.popitem(last=False)


def _get(uid):
    with LOCK:
        val=STATE.get(int(uid))
        if val and time.monotonic()-val['ts']>TTL:
            STATE.pop(int(uid),None);return None
        return val


def _clear(uid):
    with LOCK:STATE.pop(int(uid),None)


def _consume(uid, kind):
    """Atomically consume one-shot confirmation to prevent double sends."""
    with LOCK:
        value=STATE.get(int(uid))
        if value and value.get("kind")==kind and time.monotonic()-value["ts"]<=TTL:
            STATE.pop(int(uid),None)
            return value
        STATE.pop(int(uid),None)
        return None


def register_v10_handlers(bot):
    """Register immediately after V9.3 and before V9/V8 session handlers."""
    from telebot import types

    def send(chat,text,markup=None):
        text=str(text or 'No result.')
        for start in range(0,len(text),3500):
            bot.send_message(chat,text[start:start+3500],reply_markup=markup if start==0 else None)

    def gate(m):
        if not _private(m):
            send(m.chat.id,'🔒 V10 personal study tools are available only in a private chat.');return False
        if not authorized(m.from_user.id):
            send(m.chat.id,'🔒 V10 is disabled or your adult study access is not active. Check /access_status.');return False
        return True

    def error(m,exc):
        if isinstance(exc,StudyError):send(m.chat.id,'⚠️ '+str(exc))
        else:
            LOG.exception('V10 study tool unavailable')
            send(m.chat.id,'⚠️ Study service unavailable. Your existing bot tools are unaffected; try later.')

    def dashboard(m):
        if not gate(m):return
        kb=types.InlineKeyboardMarkup(row_width=2)
        for pair in [('📤 Add document','upload'),('📚 My documents','docs'),
                     ('🔎 Search notes','search'),('🎯 Revision coach','coach'),
                     ('🎤 Viva practice','viva'),('🧠 Due flashcards','due')]:
            kb.add(types.InlineKeyboardButton(pair[0],callback_data='v10:'+pair[1]))
        send(m.chat.id,'🧠 V10 Learning Lab\n\nPersonal study tools with page-referenced search, adaptive revision, text-based viva practice and review scheduling.\n\nFiles are stored in Supabase only after /v10save. Use /v10help for commands.',kb)

    @bot.message_handler(commands=['v10'])
    def cmd_home(m): dashboard(m)

    @bot.message_handler(func=lambda m:getattr(m,'text',None)==BUTTON)
    def menu_home(m): dashboard(m)

    @bot.message_handler(commands=['v10help'])
    def cmd_help(m):
        if not gate(m):return
        send(m.chat.id,'🧠 V10 commands\n/v10add — upload PDF, DOCX or TXT then /v10save\n/v10docs — list saved documents\n/v10ask QUESTION — source-grounded search\n/v10askai QUESTION — optional AI answer; asks for confirmation\n/v10coach — personalized revision tips\n/v10coachai — Gemini study plan after consent\n/v10vivaai TOPIC — Gemini viva question after consent\n/v10viva TOPIC — text viva practice\n/v10answer ANSWER — practice reply\n/v10due — flashcards due today\n/v10card ID — start card review\n/v10reveal — reveal answer\n/v10rate good|hard|easy|again — schedule next review\n/v10delete ID — request deletion\n/v10cancel — clear current V10 session.\nOnly your own study data is queried.')

    @bot.message_handler(commands=['v10cancel'])
    def cmd_cancel(m):
        if not gate(m):return
        _clear(m.from_user.id)
        send(m.chat.id,'✅ V10 temporary session cleared.')

    @bot.message_handler(commands=['v10add'])
    def cmd_add(m):
        if not gate(m):return
        _set(m.from_user.id,{'kind':'upload'})
        send(m.chat.id,'📄 Send a readable PDF, DOCX or UTF-8 TXT (max 5 MB). It will NOT be saved until you send /v10save. Only the first 45,000 readable characters and up to 40 text chunks are indexed; scanned pages need the existing OCR tool. Use /v10cancel to stop.')

    @bot.message_handler(func=lambda m:_private(m) and bool(_get(m.from_user.id)) and _get(m.from_user.id).get('kind')=='upload',content_types=['document'])
    def document(m):
        if not gate(m):return
        uid=m.from_user.id
        try:
            f=m.document
            name=str(f.file_name or 'file')[:120]
            if not name.lower().endswith(('.pdf','.docx','.txt')):
                raise StudyError('Only PDF, DOCX and TXT are supported.')
            if f.file_size and f.file_size>MAX_UPLOAD_BYTES:
                raise StudyError('File too large (max 5 MB).')
            info=bot.get_file(f.file_id)
            raw=bot.download_file(info.file_path)
            if len(raw)>MAX_UPLOAD_BYTES:raise StudyError('File too large (max 5 MB).')
            from v8_engine import extract_document
            pages=extract_document(name,raw)
            chunks=split_pages(pages)
            # Only prepared plaintext is kept in volatile memory before explicit save.
            _set(uid,{'kind':'save','filename':name,'pages':pages})
            send(m.chat.id,f'📖 Preview: {name}\n{len(chunks)} text chunks across {len(set(c["page_number"] for c in chunks))} readable pages.\n\nSend /v10save to store searchable excerpts in your private Supabase collection, or /v10cancel to discard. Index is capped at 45,000 characters / 40 chunks. Files are never uploaded to an AI provider by this action.')
        except Exception as exc:error(m, exc)

    @bot.message_handler(commands=['v10save'])
    def cmd_save(m):
        if not gate(m):return
        st=_get(m.from_user.id)
        if not st or st.get('kind')!='save':
            send(m.chat.id,'No prepared upload. Start with /v10add.');return
        try:
            saved=save_document(m.from_user.id,st['filename'],st['pages'])
            _clear(m.from_user.id)
            send(m.chat.id,f'✅ Saved {saved["title"]} ({saved["chunks"]} chunks). Use /v10ask YOUR QUESTION.\nID: {saved["id"]}')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v10docs'])
    def cmd_docs(m):
        if not gate(m):return
        try:
            items=list_documents(m.from_user.id)
            if not items:send(m.chat.id,'📚 No saved documents. Use /v10add.');return
            send(m.chat.id,'📚 Your saved documents:\n'+'\n'.join(f'• {x["title"][:70]}\n  ID: {x["id"]}' for x in items)+'\n\nUse /v10delete ID to request deletion.')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v10delete'])
    def cmd_delete(m):
        if not gate(m):return
        args=m.text.split(maxsplit=1)
        if len(args)<2:
            send(m.chat.id,'Usage: /v10delete DOCUMENT_UUID');return
        try:doc_id=str(uuid.UUID(args[1].strip()))
        except ValueError:
            send(m.chat.id,'Invalid document ID. Use /v10docs to copy it.');return
        try:
            matches=[x for x in list_documents(m.from_user.id) if str(x['id'])==doc_id]
            if not matches:send(m.chat.id,'Document not found in your account.');return
            _set(m.from_user.id,{'kind':'delete','id':doc_id})
            send(m.chat.id,f'⚠️ Permanently delete {matches[0]["title"]}?\nSend /v10confirmdelete to confirm or /v10cancel to stop.')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v10confirmdelete'])
    def cmd_confirm_delete(m):
        if not gate(m):return
        st=_get(m.from_user.id)
        if not st or st.get('kind')!='delete':
            send(m.chat.id,'No document deletion pending.');return
        _clear(m.from_user.id)  # one-time confirmation, even if DB fails
        try:
            ok=remove_document(m.from_user.id,st['id'])
            send(m.chat.id,'✅ Document and its chunks deleted.' if ok else 'Document not found.')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v10ask'])
    def cmd_search(m):
        if not gate(m):return
        question=m.text.partition(' ')[2].strip()
        try:
            results=find_evidence(m.from_user.id,question)
            if not results:
                send(m.chat.id,'🔎 No matching evidence in your saved documents. Try another keyword or /v10add.');return
            lines=['🔎 Matching passages (not an AI-generated conclusion):']
            for idx,r in enumerate(results,1):
                lines.append(f'\n[{idx}] {r["title"][:55]}, page {r["page_number"]}\n{r["body"][:460]}')
            send(m.chat.id,'\n'.join(lines)+'\n\nCheck the original document for full context.')
        except Exception as exc:error(m,exc)

    def _start_gemini(m, mode, question='', excerpts=None, priorities=None):
        if not os.getenv('V10_GEMINI_ENABLED','').strip().lower() in TRUTH:
            send(m.chat.id,'V10 Gemini is disabled. All offline study tools remain available.');return
        try:
            gemini_validate(m.from_user.id)
            from v10_gemini import build_prompt
            # Check context validity before asking for consent. No external call yet.
            build_prompt(mode,question,excerpts,priorities)
            _set(m.from_user.id,{'kind':'ai','mode':mode,'question':question,
                                 'excerpts':list(excerpts or [])[:4], 'priorities':list(priorities or [])[:8]})
            if mode in ('answer','viva'):
                content=source_key(excerpts)
            else:
                content='\n'.join('• '+str(x)[:110] for x in (priorities or [])[:8])
            send(m.chat.id,
                '⚠️ Consent required: this action sends the following short study excerpts or '
                'revision priorities to Google Gemini 3.1 Flash-Lite:\n'+content+
                '\n\nNo full files are sent; the API key stays server-side and is used only for authentication. Google may use Free-tier content to improve '
                'its products; do not send sensitive/private records. This costs one of your '
                'V10 Gemini daily requests.\n\nSend /v10confirm_ai for THIS request only, '
                'or /v10cancel to discard.')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v10askai'])
    def cmd_ask_ai(m):
        if not gate(m):return
        if not os.getenv('V10_GEMINI_ENABLED','').strip().lower() in TRUTH:
            send(m.chat.id,'V10 Gemini is disabled. Use /v10ask for offline search.');return
        question=m.text.partition(' ')[2].strip()
        try:
            excerpts=find_evidence(m.from_user.id,question)
            if not excerpts:
                send(m.chat.id,'No matching excerpts found. Use /v10ask or add documents first.');return
            _start_gemini(m,'answer',question=question,excerpts=excerpts)
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v10coachai'])
    def cmd_coach_ai(m):
        if not gate(m):return
        if not os.getenv('V10_GEMINI_ENABLED','').strip().lower() in TRUTH:
            send(m.chat.id,'V10 Gemini is disabled. Use /v10coach for offline revision priorities.');return
        try:
            priorities=coach(m.from_user.id)
            _start_gemini(m,'coach',priorities=priorities)
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v10vivaai'])
    def cmd_viva_ai(m):
        if not gate(m):return
        if not os.getenv('V10_GEMINI_ENABLED','').strip().lower() in TRUTH:
            send(m.chat.id,'V10 Gemini is disabled. Use /v10viva TOPIC for offline practice.');return
        question=m.text.partition(' ')[2].strip()
        if not question:
            send(m.chat.id,'Usage: /v10vivaai TOPIC');return
        try:
            excerpts=find_evidence(m.from_user.id,question)
            if not excerpts:
                send(m.chat.id,'No matching excerpts found for this topic. Add study documents first.');return
            _start_gemini(m,'viva',question=question,excerpts=excerpts)
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v10confirm_ai'])
    def cmd_confirm_ai(m):
        if not gate(m):return
        st=_consume(m.from_user.id,'ai')
        if not st:
            send(m.chat.id,'No pending Gemini consent. Start with /v10askai, /v10coachai or /v10vivaai.');return
        try:
            mode=st['mode']
            answer=gemini_generate(m.from_user.id,mode,st.get('question',''),
                                   st.get('excerpts'),st.get('priorities'))
            if mode=='viva':
                from v10_gemini import _clean
                refs=st['excerpts']
                _set(m.from_user.id,{'kind':'viva','prompt':{
                    'question':answer[:800],
                    'reference':'\n'.join(_clean(e.get('body',''),500) for e in refs),
                    'source':source_key(refs)}})
                send(m.chat.id,'🎤 Gemini viva question (check against your source):\n'+answer[:800]+
                     '\n\nReply using /v10answer YOUR EXPLANATION. Feedback is keyword-based, not AI grading.')
            elif mode=='coach':
                send(m.chat.id,'🎯 Gemini revision suggestions (verify before using):\n'+answer)
            else:
                send(m.chat.id,answer+'\n\nSource key:\n'+source_key(st['excerpts'])+
                     '\n\n⚠️ AI can be wrong. Check original page references.')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v10coach'])
    def cmd_coach(m):
        if not gate(m):return
        try:
            items=coach(m.from_user.id)
            if not items:
                send(m.chat.id,'🎯 No outstanding V9 mistakes, unfinished syllabus topics or weak flashcards found. Add learning records in V9 or Flashcards first.');return
            send(m.chat.id,'🎯 Suggested revision priorities:\n\n'+'\n'.join(f'{i}. {s}' for i,s in enumerate(items,1))+'\n\nThese are rule-based study suggestions, not a model prediction.')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v10viva'])
    def cmd_viva(m):
        if not gate(m):return
        topic=m.text.partition(' ')[2].strip()
        try:
            mistakes=mistakes_for_viva(m.from_user.id)
            evidence=find_evidence(m.from_user.id,topic) if topic else []
            p=viva_prompt(topic,mistakes,evidence)
            _set(m.from_user.id,{'kind':'viva','prompt':p})
            send(m.chat.id,'🎤 Text-based viva practice\nQuestion: '+p['question']+'\n\nType /v10answer YOUR EXPLANATION. Voice recognition is not included in this version.')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v10answer'])
    def cmd_viva_answer(m):
        if not gate(m):return
        st=_get(m.from_user.id)
        if not st or st.get('kind')!='viva':
            send(m.chat.id,'No active viva question. Start with /v10viva TOPIC.');return
        answer=m.text.partition(' ')[2].strip()
        try:
            feedback=viva_feedback(answer,st['prompt']['reference'])
            _clear(m.from_user.id)
            send(m.chat.id,f'🎤 Practice feedback: {feedback["label"]}\nRelevant keywords: {", ".join(feedback["matched"]) or "none found"}\n\nReference ({st["prompt"]["source"]}):\n{feedback["reference"]}\n\n{feedback["disclaimer"]}')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v10due'])
    def cmd_due(m):
        if not gate(m):return
        try:
            cards=due_cards(m.from_user.id)
            if not cards:send(m.chat.id,'🧠 No flashcards due right now. Add flashcards using the existing Flashcards tool.');return
            send(m.chat.id,'🧠 Due flashcards:\n'+'\n'.join(f'• {c["id"]}: {str(c["question"])[:100]}' for c in cards)+'\n\nSend /v10card ID to begin. Reviews here do not overwrite existing V7 review statistics.')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v10card'])
    def cmd_card(m):
        if not gate(m):return
        try:
            card_id=int(m.text.partition(' ')[2].strip())
            card=get_card(m.from_user.id,card_id)
            if not card:raise StudyError('No flashcard with this ID in your account.')
            _set(m.from_user.id,{'kind':'card','card':card,'revealed':False})
            send(m.chat.id,f'🧠 Question: {str(card["question"])[:500]}\n\nRecall the answer, then send /v10reveal.')
        except (ValueError,TypeError):send(m.chat.id,'Usage: /v10card NUMERIC_ID')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v10reveal'])
    def cmd_reveal(m):
        if not gate(m):return
        st=_get(m.from_user.id)
        if not st or st.get('kind')!='card':
            send(m.chat.id,'Start with /v10card ID.');return
        st['revealed']=True
        _set(m.from_user.id,st)
        send(m.chat.id,f'✅ Answer: {str(st["card"]["answer"])[:800]}\n\nRate your recall: /v10rate again | hard | good | easy')

    @bot.message_handler(commands=['v10rate'])
    def cmd_rate(m):
        if not gate(m):return
        st=_get(m.from_user.id)
        if not st or st.get('kind')!='card' or not st.get('revealed'):
            send(m.chat.id,'Reveal the flashcard answer with /v10reveal before rating.');return
        rating=m.text.partition(' ')[2].strip().lower()
        try:
            result=rate_card(m.from_user.id,st['card']['id'],rating)
            _clear(m.from_user.id)
            send(m.chat.id,f'✅ Next review in {result["interval_days"]} day(s). Use /v10due for more.')
        except Exception as exc:error(m,exc)

    @bot.callback_query_handler(func=lambda c:str(getattr(c,'data','')).startswith('v10:'))
    def callback(c):
        try:
            if not c.message or c.message.chat.type!='private' or int(c.message.chat.id)!=int(c.from_user.id):
                bot.answer_callback_query(c.id,'Private chat only.');return
            if not authorized(c.from_user.id):
                bot.answer_callback_query(c.id,'V10 unavailable for your account.');return
            bot.answer_callback_query(c.id)
            action=c.data[4:]
            # Menu callbacks do not perform write operations.
            if action=='upload':
                _set(c.from_user.id,{'kind':'upload'})
                send(c.message.chat.id,'📄 Send PDF/DOCX/TXT (max 5MB), then /v10save to save or /v10cancel to discard.')
            elif action=='docs':
                items=list_documents(c.from_user.id)
                send(c.message.chat.id,'📚 Your documents:\n'+('\n'.join(f'{x["title"][:55]} — {x["id"]}' for x in items) or 'None saved.'))
            elif action=='search':send(c.message.chat.id,'🔎 Send /v10ask YOUR QUESTION')
            elif action=='coach':
                items=coach(c.from_user.id)
                send(c.message.chat.id,'🎯 Priorities:\n'+('\n'.join(items) or 'No pending review suggestions.'))
            elif action=='viva':send(c.message.chat.id,'🎤 Send /v10viva TOPIC for a text-based oral exam practice question.')
            elif action=='due':
                cards=due_cards(c.from_user.id)
                send(c.message.chat.id,'🧠 Due:\n'+('\n'.join(f'{x["id"]}: {x["question"][:90]}' for x in cards) or 'No cards due.')+'\nUse /v10card ID.')
        except Exception:
            LOG.exception('V10 menu action failed')
            send(c.message.chat.id,'⚠️ This study action is temporarily unavailable.')
