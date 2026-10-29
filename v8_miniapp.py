"""Read-only V8 Telegram Mini App; server validates Telegram initData HMAC.

Do not expose Supabase secret or trust initDataUnsafe. No anonymous student data.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qsl

from flask import request, jsonify, Response


class MiniAppAuthError(ValueError):
    pass


def validate_init_data(raw: str, token: str, now: int | None = None) -> int:
    if not isinstance(raw,str) or len(raw)>6000 or not token:
        raise MiniAppAuthError("Missing or invalid Telegram credentials.")
    try:
        pairs=parse_qsl(raw,keep_blank_values=True,strict_parsing=True,max_num_fields=25)
        if len(pairs)!=len(dict(pairs)):
            raise MiniAppAuthError("Duplicate fields.")
        payload=dict(pairs)
        signature=payload.pop("hash", "")
        payload.pop("signature", None)  # Telegram may send third-party signature; not in HMAC input.
        if len(signature)!=64 or any(c not in '0123456789abcdefABCDEF' for c in signature):
            raise MiniAppAuthError("Invalid signature.")
        if not payload.get("auth_date") or not payload.get("user"):
            raise MiniAppAuthError("Missing user or timestamp.")
        stamp=int(payload['auth_date']); current=int(time.time() if now is None else now)
        if not current - 3600 <= stamp <= current + 60:
            raise MiniAppAuthError("Expired login, reopen the Mini App.")
        data_check="\n".join(f"{key}={payload[key]}" for key in sorted(payload))
        secret=hmac.new(b"WebAppData",token.encode(),hashlib.sha256).digest()
        expected=hmac.new(secret,data_check.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,signature.lower()):
            raise MiniAppAuthError("Invalid Telegram signature.")
        user=json.loads(payload['user'])
        uid=user.get('id')
        if type(uid) is not int or uid<=0:
            raise MiniAppAuthError("Invalid Telegram account.")
        return uid
    except (ValueError,TypeError,KeyError) as exc:
        if isinstance(exc,MiniAppAuthError): raise
        raise MiniAppAuthError("Invalid Telegram Mini App login.") from exc


PAGE=r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>Student Assistant — V8</title>
<script src="https://telegram.org/js/telegram-web-app.js?64"></script>
<style>
:root{color-scheme:light dark;font-family:system-ui,-apple-system,sans-serif}
body{max-width:720px;margin:0 auto;padding:22px;background:var(--tg-theme-bg-color,#f7f7f7);color:var(--tg-theme-text-color,#181818)}
h1{font-size:1.5rem}p{line-height:1.5;color:var(--tg-theme-hint-color,#555)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.box{border:1px solid var(--tg-theme-hint-color,#bbb);border-radius:12px;padding:16px;background:var(--tg-theme-secondary-bg-color,transparent)}
.num{font-size:1.7rem;font-weight:700}.label{font-size:.85rem}
#status{font-weight:600;margin-bottom:15px} .commands{line-height:1.9;word-break:break-word}
</style></head><body><h1>🎓 Student Assistant V8</h1>
<p>A private, read-only academic overview. Use your existing Telegram bot for editing, uploads and AI.</p>
<div id="status">Authenticating with Telegram…</div><div class="grid" id="cards"></div>
<h2>Study tools</h2><div class="box commands">/v8doc — Document Chat<br>/v8papers — Past Papers<br>/v8cards — Auto Flashcards<br>/v8planner — Study Planner<br>/v8lecture — Lecture Notes<br>/v8cite — Citations<br>/v8battle — Group Quizzes<br>/v8backup — Export Data</div>
<p>Close this dashboard and send a command in your private bot chat. Never share personal backup files.</p>
<script>
(async function(){const tg=window.Telegram&&window.Telegram.WebApp;const s=document.getElementById('status');
if(!tg||!tg.initData){s.textContent='Open this dashboard from inside the Telegram bot.';return;}
tg.ready();try{const r=await fetch('/v8/api/overview',{method:'POST',headers:{'Content-Type':'application/json','X-Telegram-Init-Data':tg.initData},body:'{}',cache:'no-store'});
if(!r.ok)throw Error('Session expired or access restricted; reopen from the bot.');
const data=await r.json();s.textContent='Your academic activity';
const grid=document.getElementById('cards');for(const [label,count] of Object.entries(data.counts||{})){
const box=document.createElement('div');box.className='box';const n=document.createElement('div');n.className='num';n.textContent=count===null?'—':String(count);
const l=document.createElement('div');l.className='label';l.textContent=label;box.append(n,l);grid.append(box);}
}catch(e){s.textContent=e.message||'Unable to load dashboard.';}})();</script></body></html>'''


def register_v8_miniapp(app):
    @app.get('/v8/app')
    def v8_app_page():
        from v8_bot import enabled
        if not enabled():
            return "Not found",404
        return Response(PAGE,status=200,content_type='text/html; charset=utf-8',headers={
            'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
            'Content-Security-Policy':"default-src 'none'; script-src 'unsafe-inline' https://telegram.org; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors https://web.telegram.org https://*.telegram.org"
        })

    @app.post('/v8/api/overview')
    def v8_app_overview():
        from v8_bot import allowed,student_progress
        try:
            uid=validate_init_data(request.headers.get('X-Telegram-Init-Data',''),os.getenv('BOT_TOKEN',''))
        except MiniAppAuthError:
            return jsonify({'error':'Unauthorized'}),401,{'Cache-Control':'no-store'}
        if not allowed(uid):
            return jsonify({'error':'Access denied'}),403,{'Cache-Control':'no-store'}
        return jsonify({'counts':student_progress(uid)}),200,{'Cache-Control':'no-store'}
