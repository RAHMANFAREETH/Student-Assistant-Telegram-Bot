"""V12.0 Super Mini App opt-in preview. Existing /library and bot handlers are untouched.

Production route exposure requires SUPER_MINIAPP_V120_ENABLED=true.
Personalized access is only available to signed Telegram accounts with current
server-side 18+ verification. The frontend sends no secrets or images to this API.
"""
from __future__ import annotations

import os
from pathlib import Path

from flask import abort, jsonify, make_response, request, send_file

ASSETS = Path(__file__).resolve().parent
_TRUE = {"1", "true", "yes", "on"}


def enabled():
    return os.getenv("SUPER_MINIAPP_V120_ENABLED", "false").strip().lower() in _TRUE


def verify_super_session(raw: str):
    """Re-use existing, HMAC-validated Telegram auth with short replay window.

    V8 validation does not grant access; current verified-adult record required.
    """
    from v8_miniapp import validate_init_data, MiniAppAuthError
    if not raw or len(raw) > 6000:
        raise MiniAppAuthError("Missing Telegram login.")
    uid = validate_init_data(raw, os.getenv("BOT_TOKEN", ""))
    from study_access_v9 import is_verified_adult
    if not is_verified_adult(uid):
        raise PermissionError("Verified adult access required.")
    return uid


def register_super_miniapp(app):
    """Called once after app creation. Does not modify old routes or bot handlers."""
    if "v120_super_home" in app.view_functions:
        return

    @app.after_request
    def v120_security_headers(response):
        if request.path == "/app" or request.path.startswith("/app/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; script-src 'self' https://telegram.org; "
                "style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; "
                "font-src 'self'; base-uri 'none'; form-action 'none'; "
                "object-src 'none'; frame-ancestors https://web.telegram.org https://*.telegram.org"
            )
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    @app.get("/app", endpoint="v120_super_home")
    def home():
        if not enabled():
            abort(404)
        return send_file(ASSETS / "super_miniapp_v120.html", mimetype="text/html; charset=utf-8")

    @app.get("/app/assets/style.css", endpoint="v120_super_css")
    def css():
        if not enabled():
            abort(404)
        return send_file(ASSETS / "super_miniapp_v120.css", mimetype="text/css; charset=utf-8")

    @app.get("/app/assets/app.js", endpoint="v120_super_js")
    def js():
        if not enabled():
            abort(404)
        return send_file(ASSETS / "super_miniapp_v120.js", mimetype="application/javascript")

    @app.get("/app/assets/tools.mjs", endpoint="v120_super_tools")
    def tools():
        if not enabled():
            abort(404)
        return send_file(ASSETS / "super_miniapp_v120_tools.mjs", mimetype="application/javascript")

    @app.get("/app/api/session", endpoint="v120_super_session")
    def session():
        if not enabled():
            abort(404)
        try:
            uid = verify_super_session(request.headers.get("X-Telegram-Init-Data", ""))
        except PermissionError:
            return jsonify({"error": "Verified 18+ access is required."}), 403
        except (ValueError, TypeError):
            return jsonify({"error": "Open the app from Telegram and sign in again."}), 401
        return jsonify({"ok": True, "user_id": uid, "version": "12.0-development-preview"})
