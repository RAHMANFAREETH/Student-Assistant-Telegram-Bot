"""V11.3 Telegram Mini App. No Supabase credentials or Telegram bot token in client JS.
Every API request validates Telegram's signed initData using the bot token server-side.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import parse_qsl

from flask import jsonify, request, send_file, make_response, abort
from book_library_v113_store import (smart_search,my_progress,update_progress,my_collections,
    create_collection,add_to_collection,collection_books,public_reviews,related_books, SAFE_FIELDS, book_uuid)
from book_library_v112_store import (browse_books, list_favorites, toggle_favorite, facets, _db, _rows)

ASSETS=Path(__file__).resolve().parent


def validate_init_data(raw,token,now=None,max_age=86400):
    """Telegram WebAppData HMAC validation; never trust supplied user_id alone."""
    if not raw or len(raw)>8192 or not token: raise ValueError('Missing Telegram authentication.')
    parts=parse_qsl(raw,keep_blank_values=True,strict_parsing=True,max_num_fields=35)
    if len(parts)!=len({k for k,_ in parts}):raise ValueError('Duplicate Telegram auth keys.')
    data=dict(parts)
    signature=data.pop('hash','')
    if not re.fullmatch(r'[a-fA-F0-9]{64}',signature):raise ValueError('Invalid signature.')
    check='\n'.join(f'{k}={v}' for k,v in sorted(data.items()))
    secret=hmac.new(b'WebAppData',token.encode('utf-8'),hashlib.sha256).digest()
    expected=hmac.new(secret,check.encode('utf-8'),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,signature.lower()):raise ValueError('Signature mismatch.')
    now=int(time.time()) if now is None else int(now)
    signed_at=int(data.get('auth_date','0'))
    if signed_at<now-max_age or signed_at>now+60:raise ValueError('Telegram login expired.')
    user=json.loads(data.get('user','{}'))
    if not isinstance(user,dict):raise ValueError('User missing.')
    user_id=int(user.get('id',0))
    if user_id<=0:raise ValueError('User missing.')
    return user_id


def _public(row):
    """Ensure channel IDs, message IDs, upload admin IDs, private metadata never reach browser."""
    keys=set(SAFE_FIELDS.split(','))
    item={k:row.get(k) for k in keys if k in row}
    cover=str(item.get('cover_url') or '')
    if not re.fullmatch(r'https://covers\.openlibrary\.org/b/id/[0-9]+-[SML]\.jpg',cover):
        item['cover_url']=None
    return item


def register_book_library_web(app,bot):
    """Register routes once, from existing main.py immediately after Flask app creation."""
    def enabled():
        import book_library_v113_bot
        return book_library_v113_bot.enabled() and os.getenv('BOOK_LIBRARY_MINIAPP_ENABLED','false').lower() in ('true','1','yes')

    def access():
        if not enabled(): abort(404)
        if request.method == 'POST' and request.content_length is not None and request.content_length > 4096:
            abort(413)
        uid=validate_init_data(request.headers.get('X-Telegram-Init-Data',''),os.getenv('BOT_TOKEN',''))
        import book_library_bot as lib
        if not lib._verified(uid):abort(403)
        return uid

    @app.after_request
    def v113_headers(response):
        if request.path.startswith('/library'):
            response.headers['Cache-Control']='no-store'
            response.headers['X-Content-Type-Options']='nosniff'
            response.headers['Referrer-Policy']='no-referrer'
            response.headers['Content-Security-Policy']=(
                "default-src 'self'; script-src 'self' https://telegram.org; "
                "style-src 'self'; img-src 'self' https://covers.openlibrary.org data:; "
                "connect-src 'self'; frame-ancestors https://web.telegram.org https://*.telegram.org")
        return response

    @app.get('/library')
    def v113_home():
        if not enabled():abort(404)
        return send_file(ASSETS/'book_library_v113_miniapp.html',mimetype='text/html')

    @app.get('/library/assets/app.js')
    def v113_js():
        if not enabled():abort(404)
        return send_file(ASSETS/'book_library_v113_app.js',mimetype='application/javascript')

    @app.get('/library/assets/style.css')
    def v113_css():
        if not enabled():abort(404)
        return send_file(ASSETS/'book_library_v113_style.css',mimetype='text/css')

    @app.get('/library/api/catalog')
    def v113_catalog():
        access()
        q=str(request.args.get('q','')).strip()[:100]
        cat=str(request.args.get('category','')).strip()[:80]
        page=max(0,min(int(str(request.args.get('page','0'))[:4]),99))
        if q:
            books=smart_search(q,limit=8) if page==0 else []
            more=False
        else:
            books,more=browse_books(category=cat or None,page=page,page_size=5)
        from book_library_bot import _bot_username
        username=_bot_username(bot)
        public=[dict(_public(b),deep_link=f'https://t.me/{username}?start=book_{book_uuid(b["id"]).replace("-","")}') for b in books]
        return jsonify({'books':public,'more':more,'page':page})

    @app.get('/library/api/facets')
    def v113_facets():
        access()
        return jsonify({'categories':facets('category')[:30], 'languages':facets('language')[:30]})

    @app.get('/library/api/book/<bookid>')
    def v113_details(bookid):
        access()
        bid=book_uuid(bookid)
        rows=_rows(_db().table('book_library_items').select(SAFE_FIELDS)
                   .eq('id',bid).eq('active',True).limit(1).execute())
        if not rows:abort(404)
        return jsonify({'book':_public(rows[0]),'reviews':public_reviews(bid)})

    @app.get('/library/api/related/<bookid>')
    def v113_related(bookid):
        access()
        return jsonify({'books':[_public(x) for x in related_books(book_uuid(bookid),limit=5)]})

    @app.get('/library/api/favorites')
    def v113_favorites():
        uid=access()
        books,_=list_favorites(uid,page=0,page_size=5)
        return jsonify({'books':[_public(x) for x in books]})

    @app.post('/library/api/favorite')
    def v113_favorite_toggle():
        uid=access()
        obj=request.get_json(silent=True) or {}
        bid=book_uuid(obj.get('book_id'))
        return jsonify({'favorite':toggle_favorite(uid,bid)})

    @app.get('/library/api/reading')
    def v113_reading():
        uid=access()
        return jsonify({'progress':my_progress(uid)})

    @app.post('/library/api/reading')
    def v113_update_reading():
        uid=access(); obj=request.get_json(silent=True) or {}
        return jsonify(update_progress(uid,obj.get('book_id'),obj.get('status'),obj.get('percent',0)))

    @app.get('/library/api/collections')
    def v113_collections():
        uid=access();return jsonify({'collections':my_collections(uid)})

    @app.post('/library/api/collections')
    def v113_create_collection():
        uid=access();obj=request.get_json(silent=True) or {}
        return jsonify({'collection':create_collection(uid,obj.get('name'))})

    @app.errorhandler(ValueError)
    def v113_invalid(exc):
        if request.path.startswith('/library/api/'):
            return jsonify({'error':str(exc)[:160]}),400
        return 'Bad request',400

    @app.errorhandler(500)
    def v113_server_error(exc):
        if request.path.startswith('/library/api/'):
            return jsonify({'error':'Book Library service unavailable.'}),500
        return 'Server error',500
