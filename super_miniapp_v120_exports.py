"""V12.0.2 optional Telegram-native image export.

Files exist only in this worker's RAM for at most 300 seconds, no database or disk.
The browser must explicitly select 'Save via Telegram' to upload. Bearer URLs are
unguessable but anyone holding one can fetch its file until expiry.
"""
from __future__ import annotations

import io
import os
import re
import secrets
import threading
import time
from collections import OrderedDict, defaultdict, deque

from flask import abort, jsonify, request, send_file

_MAX_FILE = 8 * 1024 * 1024
_MAX_RAM = 32 * 1024 * 1024
_TTL = 300
_LOCK = threading.RLock()
_ITEMS: OrderedDict[str, tuple] = OrderedDict()
_RATE: dict[str, deque] = defaultdict(deque)
_VALID = {"image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
          "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
          "image/webp": (b"RIFF", ".webp")}


def _enabled():
    yes = {"true", "1", "yes", "on"}
    return (os.getenv("SUPER_MINIAPP_V120_ENABLED", "false").lower() in yes
            and os.getenv("SUPER_MINIAPP_V120_PUBLIC_TOOLS", "false").lower() in yes)


def _valid_image(mime: str, content: bytes) -> bool:
    if mime not in _VALID or len(content) < 20:
        return False
    prefix, _ = _VALID[mime]
    if not content.startswith(prefix):
        return False
    if mime == "image/webp" and content[8:12] != b"WEBP":
        return False
    return True


def _clear_expired(now: float) -> None:
    for token in list(_ITEMS):
        if _ITEMS[token][0] <= now:
            del _ITEMS[token]
    for key in list(_RATE):
        while _RATE[key] and _RATE[key][0] <= now-60:
            _RATE[key].popleft()
        if not _RATE[key]:
            del _RATE[key]


def _store(content: bytes, mime: str, fname: str, client: str = "") -> str:
    now=time.monotonic()
    with _LOCK:
        _clear_expired(now)
        recent=_RATE[client]
        if len(recent) >= 12:
            raise ValueError("Too many requests; try again in one minute.")
        recent.append(now)
        while _ITEMS and (len(_ITEMS)>=20 or sum(len(entry[1]) for entry in _ITEMS.values()) + len(content) > _MAX_RAM):
            _ITEMS.popitem(last=False)
        token=secrets.token_urlsafe(24)
        _ITEMS[token]=(now+_TTL,content,mime,fname)
        return token


def _fetch(token: str):
    with _LOCK:
        _clear_expired(time.monotonic())
        return _ITEMS.get(token)


def register_v120_exports(app):
    """Called by the existing register_super_miniapp; doesn't affect /library."""
    if "v120_export_create" in app.view_functions:
        return

    @app.post("/app/api/export", endpoint="v120_export_create")
    def create_export():
        if not _enabled():
            abort(404)
        if request.headers.get("X-V120-Export-Intent") != "1":
            return jsonify(error="Explicit export consent required."), 400
        if request.content_length is not None and request.content_length > _MAX_FILE:
            return jsonify(error="Export exceeds 8 MB; use local Share/Save."), 413
        mime=request.mimetype
        if mime not in _VALID:
            return jsonify(error="Only PNG, JPEG, and WebP exports supported."), 415
        content=request.stream.read(_MAX_FILE+1)
        if len(content)>_MAX_FILE:
            return jsonify(error="Export exceeds 8 MB; use local Share/Save."), 413
        if not _valid_image(mime,content):
            return jsonify(error="Invalid image file."), 400
        ext=_VALID[mime][1]
        fname=request.headers.get("X-V120-Export-Name","student-export")
        fname=re.sub(r"[^A-Za-z0-9_-]", "-",fname.rsplit(".",1)[0])[:48].strip("-") or "student-export"
        try:
            token=_store(content,mime,fname+ext,request.remote_addr or "unknown")
        except ValueError as exc:
            return jsonify(error=str(exc)), 429
        return jsonify(ok=True, path=f"/app/exports/{token}", expires_in=_TTL),201

    @app.get("/app/exports/<token>", endpoint="v120_export_fetch")
    def fetch_export(token):
        if not _enabled():
            abort(404)
        if not re.fullmatch(r"[A-Za-z0-9_-]{32}",token):
            abort(404)
        item=_fetch(token)
        if item is None:
            abort(404)
        _,content,mime,fname=item
        response=send_file(io.BytesIO(content),mimetype=mime,as_attachment=True,
                           download_name=fname,max_age=0,conditional=True)
        response.headers["Cache-Control"]="private, no-store, max-age=0"
        response.headers["Access-Control-Allow-Origin"]="https://web.telegram.org"
        response.headers["X-Content-Type-Options"]="nosniff"
        response.headers["Referrer-Policy"]="no-referrer"
        return response
