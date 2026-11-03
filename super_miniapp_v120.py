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

# >>> V12 PUBLIC UTILITY ACCESS >>>
def public_tools_enabled():
    """Public, browser-only calculators; never a replacement for signed identity."""
    return os.getenv('SUPER_MINIAPP_V120_PUBLIC_TOOLS', 'false').strip().lower() in _TRUE


def adult_verification_required():
    """Opt out ONLY for the V12 benign Mini App, not for other bot/AI features."""
    return os.getenv('SUPER_MINIAPP_V120_REQUIRE_ADULT', 'true').strip().lower() not in ('0', 'false', 'no', 'off')


def _guest_session():
    return jsonify({'ok': True, 'guest': True, 'user_id': None,
                    'private_features': False, 'version': '12.0-development-preview'})

# <<< V12 PUBLIC UTILITY ACCESS <<<


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
    if adult_verification_required():
        from study_access_v9 import is_verified_adult
        if not is_verified_adult(uid):
            raise PermissionError("Verified adult access required.")
    # V12.0 optional server-side pilot gate; HMAC and adult checks run first.
    from super_miniapp_v120_launch import pilot_access_allowed
    if not pilot_access_allowed(uid):
        raise PermissionError("V12 pilot access is restricted.")
    return uid


def register_super_miniapp(app):
    """Called once after app creation. Does not modify old routes or bot handlers."""
    if "v120_super_home" in app.view_functions:
        return

    # >>> V12.0.2 optional temporary exports >>>
    from super_miniapp_v120_exports import register_v120_exports
    register_v120_exports(app)
    from super_miniapp_v121 import register_v121_arcade
    register_v121_arcade(app)
    from super_miniapp_v122_fonts import register_v122_fontstudio
    register_v122_fontstudio(app)
    # <<< V12.0.2 optional temporary exports <<<

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

    @app.get("/app/assets/results.mjs", endpoint="v120_super_results")
    def results_module():
        if not enabled():
            abort(404)
        return send_file(ASSETS / "super_miniapp_v120_results.mjs", mimetype="application/javascript")

    @app.get("/app/api/session", endpoint="v120_super_session")
    def session():
        if not enabled():
            abort(404)
        raw = request.headers.get('X-Telegram-Init-Data', '')
        if public_tools_enabled() and not raw:
            return _guest_session()
        try:
            uid = verify_super_session(raw)
        except PermissionError:
            # Anonymous utilities are safe; private endpoints still check HMAC.
            if public_tools_enabled():
                return _guest_session()
            return jsonify({'error': 'Verified 18+ access is required.'}), 403
        # >>> V12.0 SESSION FAILURE DIAGNOSTIC >>>
        except (ValueError, TypeError) as exc:
            # Do not log initData, user ID or the bot token.
            detail = str(exc).lower()
            if 'expired' in detail:
                reason = 'expired_telegram_login'
            elif 'signature' in detail:
                reason = 'invalid_telegram_signature'
            else:
                reason = 'invalid_telegram_login'
            app.logger.warning('V12 login denied: %s (no sensitive data logged)', reason)
            if public_tools_enabled():
                return _guest_session()
            return jsonify({'error':'Open the app from Telegram and sign in again.', 'code': reason}), 401
        # <<< V12.0 SESSION FAILURE DIAGNOSTIC <<<
        return jsonify({'ok': True, 'user_id': uid,
                        'private_features': True, 'version': '12.0-development-preview'})

    @app.route("/app/api/tasks", methods=["GET", "POST"], endpoint="v120_super_tasks")
    def tasks():
        if not enabled():
            abort(404)
        try:
            uid = verify_super_session(request.headers.get("X-Telegram-Init-Data", ""))
        except PermissionError:
            return jsonify({"error": "Verified 18+ access is required."}), 403
        except (ValueError, TypeError):
            return jsonify({"error": "Open the app from Telegram and sign in again."}), 401
        from super_miniapp_v120_tasks import (list_tasks, create_task, TaskInputError, TaskLimitError)
        try:
            if request.method == "GET":
                return jsonify({"ok": True, "tasks": list_tasks(uid)})
            if request.content_length is not None and request.content_length > 4096:
                return jsonify({"error": "Request too large."}), 413
            body = request.get_json(silent=True)
            if not isinstance(body, dict):
                return jsonify({"error": "Expected JSON object."}), 400
            task, created = create_task(uid, body)
            return jsonify({"ok": True, "task": task}), 201 if created else 200
        except TaskLimitError:
            return jsonify({"error": "Maximum of 100 synchronized tasks."}), 409
        except TaskInputError:
            return jsonify({"error": "Invalid task data."}), 400
        except Exception:
            app.logger.warning("V12 private task API unavailable")
            return jsonify({"error": "Task synchronization unavailable."}), 503

    @app.route("/app/api/tasks/<task_id>", methods=["PATCH", "DELETE"], endpoint="v120_super_task_item")
    def task_item(task_id):
        if not enabled():
            abort(404)
        try:
            uid = verify_super_session(request.headers.get("X-Telegram-Init-Data", ""))
        except PermissionError:
            return jsonify({"error": "Verified 18+ access is required."}), 403
        except (ValueError, TypeError):
            return jsonify({"error": "Open the app from Telegram and sign in again."}), 401
        from super_miniapp_v120_tasks import update_task, delete_task, TaskInputError
        try:
            if request.method == "DELETE":
                delete_task(uid, task_id)
                return jsonify({"ok": True})
            if request.content_length is not None and request.content_length > 4096:
                return jsonify({"error": "Request too large."}), 413
            body = request.get_json(silent=True)
            record = update_task(uid, task_id, body)
            return (jsonify({"ok": True, "task": record}) if record else
                    (jsonify({"error": "Task not found."}), 404))
        except TaskInputError:
            return jsonify({"error": "Invalid task data."}), 400
        except Exception:
            app.logger.warning("V12 private task mutation unavailable")
            return jsonify({"error": "Task synchronization unavailable."}), 503

    @app.get("/app/api/planner", endpoint="v120_super_planner")
    def planner():
        if not enabled():
            abort(404)
        try:
            uid = verify_super_session(request.headers.get("X-Telegram-Init-Data", ""))
        except PermissionError:
            return jsonify({"error": "Verified 18+ access is required."}), 403
        except (ValueError, TypeError):
            return jsonify({"error": "Open the app from Telegram and sign in again."}), 401
        try:
            return jsonify({"ok": True, **read_planner_overview(uid)})
        except Exception:
            # Never leak database exceptions or connection strings to the browser.
            app.logger.warning("V12 planner overview unavailable")
            return jsonify({"error": "Planner data is temporarily unavailable."}), 503


# User-specific academic overview. All reads use the verified Telegram user ID.
# No writes, schema changes, reminders, or access to other users' data.
def read_planner_overview(user_id):
    from assignments import get_assignments
    from exam_planner import get_exams
    assignments = get_assignments(int(user_id), status="pending", limit=30)
    exams = get_exams(int(user_id), upcoming_only=True, limit=30)
    return {
        "assignments": [
            {
                "title": str(a.get("title") or "")[:160],
                "due_at": a.get("due_at"),
                "priority": str(a.get("priority") or "")[:32],
                "status": str(a.get("status") or "")[:32],
            }
            for a in (assignments or []) if isinstance(a, dict)
        ],
        "exams": [
            {
                "title": str(e.get("title") or "")[:160],
                "exam_at": e.get("exam_at"),
                "location": str(e.get("location") or "")[:120],
            }
            for e in (exams or []) if isinstance(e, dict)
        ],
        "read_only": True,
    }
