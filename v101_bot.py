"""V10.1 all-12-feature Telegram addon. Register before legacy stateful handlers.

Each AI request requires one-shot consent. Voice/OCR/TTS use separate, explicit
provider consent. Disabling V101_ENABLED hides every new action without touching V10.
"""
from __future__ import annotations
import io, logging, os, threading, time
from uuid import uuid4
from collections import OrderedDict
from v10_engine import StudyError,MAX_UPLOAD_BYTES
from v10_store import find_evidence,coach,save_document
from v10_gemini import source_key
from v101_engine import (clean,topic,language,sources,roadmap,summary_from_evidence,
                         compare_passages,claim_support,validate_mock,validate_cards,grade_mock)
import v101_store as store
import v101_gemini as ai

LOG=logging.getLogger(__name__)
TRUTH=('true','yes','1')
LOCK=threading.RLock()
SESSIONS=OrderedDict()
TTL=600
VOICE_SLOTS=threading.BoundedSemaphore(1)
OCR_SLOTS=threading.BoundedSemaphore(1)


def enabled():return os.getenv('V101_ENABLED','').lower().strip() in TRUTH

def private(m):
    try:return m.chat.type=='private' and int(m.chat.id)==int(m.from_user.id)
    except (TypeError,ValueError,AttributeError):return False

def allowed(uid):
    if not enabled():return False
    from v10_bot import authorized
    from v10_gemini import adult_eligible
    # All V10.1 features (including rooms, OCR and audio) are independently verified adult-only.
    return bool(authorized(uid)) and bool(adult_eligible(uid))

def stage(uid,value):
    with LOCK:
        now=time.monotonic()
        for k,v in list(SESSIONS.items()):
            if now-v['ts']>TTL:SESSIONS.pop(k,None)
        SESSIONS[int(uid)]={**value,'ts':now}
        SESSIONS.move_to_end(int(uid))
        while len(SESSIONS)>40:SESSIONS.popitem(last=False)

def current(uid,kind=None,consume=False):
    with LOCK:
        v=SESSIONS.get(int(uid))
        if not v or time.monotonic()-v['ts']>TTL:
            SESSIONS.pop(int(uid),None);return None
        if kind and v.get('kind')!=kind:return None
        if consume:SESSIONS.pop(int(uid),None)
        return v

def cancel(uid):
    with LOCK:SESSIONS.pop(int(uid),None)

def register_v101_handlers(bot):
    def send(chat,message):
        text=str(message or 'No result.')
        for i in range(0,len(text),3400):bot.send_message(chat,text[i:i+3400])

    def gate(m):
        if not private(m):send(m.chat.id,'🔒 V10.1 personal study commands require a private chat.');return False
        if not allowed(m.from_user.id):
            send(m.chat.id,'🔒 V10.1 unavailable. Check /access_status, /v10 and your adult study access.');return False
        return True

    def error(m,exc):
        if isinstance(exc,StudyError):send(m.chat.id,'⚠️ '+str(exc))
        else:
            LOG.exception('V10.1 feature failed')
            send(m.chat.id,'⚠️ Study action temporarily unavailable. Your earlier bot features remain intact.')

    def args(m):return str(getattr(m,'text','') or '').partition(' ')[2].strip()

    def search(uid,question):
        # V10 owner-scoped keyword retrieval; not vector retrieval.
        return find_evidence(uid,topic(question))

    def queue_ai(m,action,payload):
        ai.validate(m.from_user.id)
        ai.build_prompt(action,payload) # no request yet
        stage(m.from_user.id,{'kind':'gemini','action':action,'payload':payload})
        evidence=payload.get('evidence') or []
        preview='\n'.join(sources(evidence,4,300)) if evidence else '(no saved document excerpts)'
        context=('Question: '+clean(payload.get('question'),330)+'\n'+
                 ('Your answer: '+clean(payload.get('answer'),500)+'\n' if payload.get('answer') else '')+
                 ('Criteria: '+clean(payload.get('criteria'),300)+'\n' if payload.get('criteria') else ''))
        memory='\n'.join('Prior Q: '+clean(x.get('question'),100)+' / A: '+clean(x.get('answer'),130)
                         for x in (payload.get('history') or [])[-3:])
        send(m.chat.id,
            '🔐 One-request Gemini consent. Review the following text to be sent to Google Gemini:\n'+
            (context+'\n'+memory+'\n'+preview)[:2200]+
            '\n\nOnly excerpts (not full files) are used. For chat, the last 3 study turns may also be sent. '
            'Free-tier content may be used to improve Google products. Avoid sensitive data. '
            'Uses one existing V10 Gemini daily quota request.\n'
            'Send /v101confirm to continue or /v101cancel to discard. Consent expires in 10 minutes.')

    @bot.message_handler(commands=['v101','v101help'])
    def home(m):
        if not gate(m):return
        send(m.chat.id,
            '🧠 V10.1 — Combined Learning Intelligence (12 features)\n'
            '1 /v101chat QUESTION — contextual Gemini tutor\n'
            '2 /v101viva TOPIC → /v101answer TEXT or /v101voice\n'
            '3 /v101explain LANGUAGE | QUESTION — multilingual teaching\n'
            '4 /v101ocr — scanned PDF/photo to V10 library\n'
            '5 /v101mock TOPIC → /v101submit A B C\n'
            '6 /v101rubric QUESTION | ANSWER | CRITERIA\n'
            '7 /v101plan 7|14|30 | TOPIC | MINUTES and /v101myplan\n'
            '8 /v101audio TOPIC — short audio lesson\n'
            '9 /v101cards TOPIC → /v101cardsave\n'
            '10 /v101compare TOPIC (/v101compareai TOPIC)\n'
            '11 /v101roomcreate GOAL → /v101roomjoin CODE, /v101roomquiz, /v101roomscore\n'
            '12 /v101check CLAIM — evidence overlap screening\n\n'
            'For Gemini: /v101confirm. For cancellation: /v101cancel. '
            'For chat deletion: /v101forget. External provider consent is required for AI, OCR, voice and audio.')

    @bot.message_handler(func=lambda m:getattr(m,'text',None)=='🧠 V10.1 All Features')
    def menu(m):home(m)

    @bot.message_handler(commands=['v101cancel'])
    def cmd_cancel(m):
        if gate(m):cancel(m.from_user.id);send(m.chat.id,'✅ Temporary V10.1 session discarded.')

    @bot.message_handler(commands=['v101forget'])
    def forget(m):
        if not gate(m):return
        try:store.forget_chat(m.from_user.id);cancel(m.from_user.id);send(m.chat.id,'✅ Stored V10.1 tutor conversation memory deleted.')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101chat'])
    def chat(m):
        if not gate(m):return
        try:
            q=topic(args(m));e=search(m.from_user.id,q)
            if not e:raise StudyError('No matching saved documents; add notes using /v10add.')
            h=store.chat_history(m.from_user.id)
            send(m.chat.id,'Tutor memory: this command opts in to storing your study turns for follow-ups. Recent turns expire from retrieval after 14 days; use /v101forget to delete stored turns.')
            queue_ai(m,'chat',{'question':q,'evidence':e,'history':h})
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101explain'])
    def explain(m):
        if not gate(m):return
        try:
            lang,question=[x.strip() for x in args(m).split('|',1)]
            q=topic(question);lang=language(lang)
            queue_ai(m,'explain',{'question':q,'language':lang,'evidence':search(m.from_user.id,q)})
        except ValueError:send(m.chat.id,'Usage: /v101explain Tamil | Explain photosynthesis')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101viva'])
    def viva(m):
        if not gate(m):return
        try:
            q=topic(args(m));queue_ai(m,'viva',{'question':q,'evidence':search(m.from_user.id,q)})
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101answer'])
    def viva_answer(m):
        if not gate(m):return
        state=current(m.from_user.id,'viva')
        if not state:send(m.chat.id,'No viva in progress. Use /v101viva TOPIC.');return
        ans=args(m)
        if not 8<=len(ans)<=1300:send(m.chat.id,'Answer must contain 8–1300 characters.');return
        try:
            payload={'question':state['question'],'evidence':state['evidence'],'answer':ans}
            queue_ai(m,'viva_feedback',payload)
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101mock'])
    def mock(m):
        if not gate(m):return
        try:
            q=topic(args(m));queue_ai(m,'mock',{'question':q,'evidence':search(m.from_user.id,q)})
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101submit'])
    def submit(m):
        if not gate(m):return
        st=current(m.from_user.id,'mock',consume=True)
        if not st:send(m.chat.id,'No current mock exam; use /v101mock TOPIC.');return
        try:
            score,lines,mistakes=grade_mock(st['questions'],args(m))
            store.save_mistakes(m.from_user.id,mistakes)
            send(m.chat.id,f'📝 Practice result: {score}/3\n'+'\n'.join(lines)+
                 '\n\n⚠️ Answers were AI-generated and are not an official exam or grading.')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101rubric'])
    def rubric(m):
        if not gate(m):return
        try:
            q,ans,criteria=[x.strip() for x in args(m).split('|',2)]
            if not 8<=len(ans)<=1300:raise StudyError('Answer should be 8–1300 characters.')
            if not 3<=len(criteria)<=500:raise StudyError('Add explicit marking criteria (3–500 characters).')
            # Rubric is formative. No source excerpts by default to avoid matching unrelated private notes.
            queue_ai(m,'rubric',{'question':topic(q),'answer':ans,'criteria':criteria})
        except ValueError:send(m.chat.id,'Usage: /v101rubric QUESTION | YOUR ANSWER | CRITERIA')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101plan'])
    def plan(m):
        if not gate(m):return
        try:
            ds,sub,mins=[x.strip() for x in args(m).split('|',2)]
            try:priorities=coach(m.from_user.id)
            except Exception:priorities=[]
            lines=roadmap(ds,sub,mins,priorities)
            store.create_plan(m.from_user.id,sub,int(ds),int(mins),lines)
            send(m.chat.id,'🗓 Your saved learning plan (heuristic, editable by replacing):\n'+'\n'.join(lines))
        except ValueError:send(m.chat.id,'Usage: /v101plan 7 | Biology | 60 (7, 14 or 30 days)')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101myplan'])
    def myplan(m):
        if not gate(m):return
        try:
            item=store.get_plan(m.from_user.id)
            if not item:send(m.chat.id,'No plan saved. Use /v101plan.');return
            send(m.chat.id,f'🗓 {item["subject"]}:\n'+'\n'.join(str(x) for x in item['plan'][:30]))
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101audio'])
    def audio(m):
        if not gate(m):return
        try:
            raw=args(m)
            if '|' in raw:
                raw_lang,raw_topic=[x.strip() for x in raw.split('|',1)]
                lang_name=language(raw_lang)
                lang_code={'English':'en','Tamil':'ta','Arabic':'ar','Sinhala':'si'}[lang_name]
            else:
                raw_topic,lang_code=raw,'en'
            q=topic(raw_topic);e=search(m.from_user.id,q)
            script=summary_from_evidence(e)
            stage(m.from_user.id,{'kind':'audio','text':script,'lang':lang_code})
            send(m.chat.id,'🔊 Extractive lesson preview (may not be comprehensive):\n'+script[:950]+
                 '\n\n/v101audioconfirm sends this text to Google TTS/gTTS, '
                 'which may process it externally. No original files are sent. '
                 'Send /v101audioconfirm to agree, or /v101cancel.')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101audioconfirm'])
    def audio_confirm(m):
        if not gate(m):return
        state=current(m.from_user.id,'audio',consume=True)
        if not state:send(m.chat.id,'No audio lesson pending. Use /v101audio TOPIC.');return
        try:
            from gtts import gTTS
            from gtts.lang import tts_langs
            if state['lang'] not in tts_langs():
                raise StudyError('This language is unavailable in the current speech engine. Try English.')
            stream=io.BytesIO()
            gTTS(text=state['text'],lang=state['lang']).write_to_fp(stream)
            stream.seek(0);stream.name='study_lesson.mp3'
            bot.send_audio(m.chat.id,stream,title='Study lesson (source excerpts)')
        except StudyError as exc:send(m.chat.id,'⚠️ '+str(exc))
        except Exception:
            LOG.exception('TTS failed')
            send(m.chat.id,'⚠️ Audio service unavailable. Try the text summary or your existing voice tools.')

    @bot.message_handler(commands=['v101cards'])
    def cards(m):
        if not gate(m):return
        try:
            q=topic(args(m));queue_ai(m,'cards',{'question':q,'evidence':search(m.from_user.id,q)})
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101cardsave'])
    def cards_save(m):
        if not gate(m):return
        state=current(m.from_user.id,'cards',consume=True)
        if not state:send(m.chat.id,'No cards prepared; use /v101cards TOPIC.');return
        try:
            count=store.save_cards(m.from_user.id,state['cards'])
            send(m.chat.id,f'✅ Saved {count} cards to your existing Flashcards table. Use /v10due for review.')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101compare'])
    def compare(m):
        if not gate(m):return
        try:send(m.chat.id,compare_passages(store.compare_rows(m.from_user.id,topic(args(m)))))
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101compareai'])
    def compare_ai(m):
        if not gate(m):return
        try:
            q=topic(args(m));rows=store.compare_rows(m.from_user.id,q)
            if len(rows)<2:raise StudyError('Two relevant saved documents are required.')
            queue_ai(m,'compare',{'question':q,'evidence':rows})
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101check'])
    def check(m):
        if not gate(m):return
        try:
            q=topic(args(m));send(m.chat.id,claim_support(q,search(m.from_user.id,q)))
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101roomcreate'])
    def roomcreate(m):
        if not gate(m):return
        try:
            if store.room_for_user(m.from_user.id):raise StudyError('Leave or close your current room first.')
            code=store.create_room(m.from_user.id,topic(args(m)))
            send(m.chat.id,'👥 Room created. Invite verified adults privately with code:\n'+code+
                 '\nThey join with /v101roomjoin CODE. Only goals, room quiz answers and scores are shared, never personal notes.')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101roomjoin'])
    def roomjoin(m):
        if not gate(m):return
        try:
            code=args(m)
            if not 12<=len(code)<=24:raise StudyError('Usage: /v101roomjoin ROOM_CODE')
            status=store.join_room(m.from_user.id,code)
            send(m.chat.id,{'joined':'✅ Joined the study room.', 'already_member':'You are already a member.',
                 'already_in_room':'Leave your old room first.','full':'The room is full (12 members).',
                 'missing':'No room found for this code.'}[status])
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101room'])
    def room(m):
        if not gate(m):return
        try:
            r=store.room_status(m.from_user.id)
            if not r:send(m.chat.id,'Not in a room. Use /v101roomcreate GOAL or /v101roomjoin CODE.');return
            quiz=store.active_quiz(r['code'])
            send(m.chat.id,f'👥 Goal: {r["goal"]}\nMembers: {r["members"]}/12\n'+
                 ('Latest quiz: '+str(quiz['question'])+'\nSend /v101roomanswer YOUR ANSWER' if quiz else 'No room quiz yet.'))
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101roomleave'])
    def roomleave(m):
        if not gate(m):return
        try:send(m.chat.id,store.leave_room(m.from_user.id))
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101roomquiz'])
    def roomquiz(m):
        if not gate(m):return
        try:
            q,a=[x.strip() for x in args(m).split('|',1)]
            if len(q)<3 or not a:raise StudyError('Question and answer required.')
            store.new_room_quiz(m.from_user.id,q,a)
            send(m.chat.id,'✅ Shared quiz created. Ask members to open /v101room and use /v101roomanswer ANSWER. The answer key is hidden.')
        except ValueError:send(m.chat.id,'Usage: /v101roomquiz QUESTION | CORRECT ANSWER')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101roomanswer'])
    def roomanswer(m):
        if not gate(m):return
        try:
            if not args(m):raise StudyError('Usage: /v101roomanswer ANSWER')
            correct=store.submit_room_answer(m.from_user.id,args(m))
            send(m.chat.id,'✅ Answer recorded. '+('Exact-match correct.' if correct else 'Not an exact answer match.'))
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101roomscore'])
    def roomscore(m):
        if not gate(m):return
        try:
            r=store.room_score(m.from_user.id)
            send(m.chat.id,f'👥 Room progress: {r["questions"]} quizzes, {r["answers"]} submissions, '
                 f'{r["correct"]} exact matches. Anonymous totals; no member names or private study content.')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101confirm'])
    def confirm_ai(m):
        if not gate(m):return
        st=current(m.from_user.id,'gemini',consume=True)
        if not st:send(m.chat.id,'No pending Gemini consent.');return
        try:
            action,payload=st['action'],st['payload']
            output=ai.generate(m.from_user.id,action,payload)
            if action=='mock':
                questions=validate_mock(output)
                stage(m.from_user.id,{'kind':'mock','questions':questions})
                lines=['📝 3-question practice exam (AI-generated; verify facts):']
                for i,q in enumerate(questions,1):
                    lines.append(f'{i}. {q["question"]}\n'+'\n'.join(f'{"ABCD"[n]}. {v}' for n,v in enumerate(q['options'])))
                send(m.chat.id,'\n\n'.join(lines)+'\n\nReply /v101submit A B C (your selected letters).')
            elif action=='cards':
                cards=validate_cards(output)
                stage(m.from_user.id,{'kind':'cards','cards':cards})
                send(m.chat.id,'📚 Gemini flashcard preview (check citations):\n'+
                     '\n'.join(f'{i}. {c["question"]} → {c["answer"]}' for i,c in enumerate(cards,1))+
                     '\n\nSend /v101cardsave to save or /v101cancel to discard.')
            elif action=='viva':
                stage(m.from_user.id,{'kind':'viva','question':clean(output,700),'evidence':payload['evidence']})
                send(m.chat.id,'🎤 Viva question:\n'+clean(output,700)+'\n\nAnswer via /v101answer TEXT, or /v101voice for a voice reply.')
            else:
                if action=='chat':store.append_chat(m.from_user.id,payload['question'],output)
                if action=='viva_feedback':
                    stage(m.from_user.id,{'kind':'viva','question':payload['question'],'evidence':payload['evidence']})
                send(m.chat.id,output+'\n\nSource key:\n'+source_key(payload.get('evidence') or [])+
                     '\n⚠️ Gemini answers, suggested marks and source claims need human verification.')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101voice'])
    def voice_request(m):
        if not gate(m):return
        st=current(m.from_user.id,'viva')
        if not st:send(m.chat.id,'Start a viva using /v101viva TOPIC first.');return
        stage(m.from_user.id,{'kind':'voice_wait','question':st['question'],'evidence':st['evidence']})
        send(m.chat.id,'🎙 Send a short Telegram voice note (max 60 seconds / 2MB). '
             'By sending it now you consent to transcription by AssemblyAI, an external provider. '
             'No audio is stored in V10.1. Transcript will be returned for review before Gemini feedback. '
             'Use /v101cancel to decline.')

    @bot.message_handler(content_types=['voice'],func=lambda m:private(m) and bool(current(m.from_user.id,'voice_wait')))
    def voice_received(m):
        if not gate(m):return
        st=current(m.from_user.id,'voice_wait',consume=True)
        if not st:return
        if int(getattr(m.voice,'duration',0) or 0)>60 or int(getattr(m.voice,'file_size',0) or 0)>2*1024*1024:
            send(m.chat.id,'Voice message must be at most 60 seconds and 2MB.');return
        if not VOICE_SLOTS.acquire(blocking=False):send(m.chat.id,'Voice transcription is busy. Try again later.');return
        chat=m.chat.id;uid=m.from_user.id;fid=m.voice.file_id
        nonce=str(uuid4());stage(uid,{'kind':'voice_processing','nonce':nonce})
        def still_current():
            item=current(uid,'voice_processing')
            return bool(item and item.get('nonce')==nonce)
        def transcribe():
            try:
                from speech_to_text import stt_is_configured,transcribe_audio
                if not stt_is_configured():raise StudyError('AssemblyAI speech-to-text is not configured.')
                info=bot.get_file(fid);audio=bot.download_file(info.file_path)
                if len(audio)>2*1024*1024:raise StudyError('Voice note too large.')
                result=transcribe_audio(audio,poll_timeout_seconds=65)
                text=clean(result.get('text'),1300)
                if len(text)<8:raise StudyError('No clear answer transcribed.')
                if not still_current():return
                stage(uid,{'kind':'transcribed','question':st['question'],'evidence':st['evidence'],'answer':text})
                send(chat,'📝 Transcript preview:\n'+text+'\n\nSend /v101voicefeedback to request Gemini feedback with separate consent, or /v101cancel.')
            except StudyError as exc:
                if still_current():send(chat,'⚠️ '+str(exc))
            except Exception:
                LOG.exception('V10.1 transcription failed')
                if still_current():send(chat,'⚠️ Transcription unavailable; use /v101viva and a typed answer instead.')
            finally:VOICE_SLOTS.release()
        threading.Thread(target=transcribe,daemon=True,name='v101-voice').start()
        send(chat,'🎙 Received. Transcription has started; delivery is best-effort while this Render worker remains running.')

    @bot.message_handler(commands=['v101voicefeedback'])
    def voice_feedback(m):
        if not gate(m):return
        state=current(m.from_user.id,'transcribed',consume=True)
        if not state:send(m.chat.id,'No transcript pending. Start /v101viva then /v101voice.');return
        try:queue_ai(m,'viva_feedback',{k:state[k] for k in ('question','evidence','answer')})
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101ocr'])
    def ocr(m):
        if not gate(m):return
        stage(m.from_user.id,{'kind':'ocr_upload'})
        send(m.chat.id,'📷 Send a small scanned PDF (max 5MB) or JPG/PNG (max 1MB). '
             'Then /v101ocrconfirm will request explicit consent before sending the document to OCR.space. '
             'No external upload occurs yet. Use /v101cancel to discard.')

    @bot.message_handler(content_types=['document','photo'],func=lambda m:private(m) and bool(current(m.from_user.id,'ocr_upload')))
    def ocr_file(m):
        if not gate(m):return
        try:
            if getattr(m,'document',None):
                obj=m.document;name=clean(obj.file_name,100);fid=obj.file_id;size=obj.file_size or 0
            elif getattr(m,'photo',None):
                obj=m.photo[-1];name='study_photo.jpg';fid=obj.file_id;size=obj.file_size or 0
            else:raise StudyError('Send a JPG, PNG or PDF.')
            if not name.lower().endswith(('.pdf','.jpg','.jpeg','.png')):raise StudyError('OCR supports PDF/JPG/PNG.')
            limit=MAX_UPLOAD_BYTES if name.lower().endswith('.pdf') else 1_000_000
            if size and size>limit:raise StudyError('File exceeds OCR upload limit.')
            info=bot.get_file(fid);raw=bot.download_file(info.file_path)
            if not raw or len(raw)>limit:raise StudyError('File exceeds OCR upload limit.')
            stage(m.from_user.id,{'kind':'ocr_consent','filename':name,'data':raw})
            send(m.chat.id,f'📷 {name} received. Send /v101ocrconfirm to send it to OCR.space for text recognition. '
                 'OCR.space receives your document and may have its own processing terms; avoid sensitive records. '
                 'Or /v101cancel to discard.')
        except Exception as exc:error(m,exc)

    @bot.message_handler(commands=['v101ocrconfirm'])
    def ocr_confirm(m):
        if not gate(m):return
        st=current(m.from_user.id,'ocr_consent',consume=True)
        if not st:send(m.chat.id,'No OCR document pending. Use /v101ocr.');return
        if not OCR_SLOTS.acquire(blocking=False):
            send(m.chat.id,'OCR provider queue is busy. Restart with /v101ocr.');return
        uid,chat=m.from_user.id,m.chat.id
        nonce=str(uuid4());stage(uid,{'kind':'ocr_processing','nonce':nonce})
        def still_current():
            item=current(uid,'ocr_processing')
            return bool(item and item.get('nonce')==nonce)
        def perform_ocr():
            try:
                from translation_ocr import extract_text_with_ocr
                recognized=extract_text_with_ocr(st['data'],st['filename'])
                text=str(recognized or '')[:45000]
                if len(text)<30:raise StudyError('OCR found too little readable text.')
                if not still_current():return
                fname=st['filename'] if st['filename'].lower().endswith('.pdf') else st['filename'].rsplit('.',1)[0]+'.txt'
                stage(uid,{'kind':'ocr_save','filename':fname,'pages':[(1,text)]})
                send(chat,'📄 OCR text preview:\n'+clean(text,900)+
                     '\n\nOCR page references are merged, NOT guaranteed original page numbers. '
                     'Send /v101ocrsave to store text in your private V10 library or /v101cancel.')
            except StudyError as exc:
                if still_current():send(chat,'⚠️ '+str(exc))
            except Exception:
                LOG.exception('V10.1 OCR failed')
                if still_current():send(chat,'⚠️ OCR provider unavailable or could not read this document. Try the existing OCR tool.')
            finally:OCR_SLOTS.release()
        threading.Thread(target=perform_ocr,daemon=True,name='v101-ocr').start()
        send(chat,'📷 OCR request started. The preview will arrive if this Render worker remains running.')

    @bot.message_handler(commands=['v101ocrsave'])
    def ocr_save(m):
        if not gate(m):return
        st=current(m.from_user.id,'ocr_save',consume=True)
        if not st:send(m.chat.id,'No OCR text prepared. Start /v101ocr.');return
        try:
            result=save_document(m.from_user.id,st['filename'],st['pages'])
            send(m.chat.id,f'✅ OCR-derived text saved: {result["title"]}, {result["chunks"]} chunks. Use /v10ask or /v101chat.')
        except Exception as exc:error(m,exc)
