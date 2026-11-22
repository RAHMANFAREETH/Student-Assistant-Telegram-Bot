"""V13.4 opt-in CloudBridge routes + private Telegram commands.

Signed Telegram identity on EVERY private API. No admin-only shortcuts and no
changes to the existing AI, Library, age verification or navigation policies.
"""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from cloudbridge_v134_core import (BridgeError, account_id, create_job, database,
                                   enabled, encrypt_token, job_id, list_jobs,
                                   new_oauth_state, provider, safe_filename,
                                   update_job)
from cloudbridge_v134_providers import authorization_url, exchange_code

ASSETS = Path(__file__).resolve().parent


def public_url():
    value = os.getenv("CLOUDBRIDGE_PUBLIC_URL", "").rstrip("/")
    try:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            return None
        if parsed.port not in (None, 443) or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            return None
        return value
    except ValueError:
        return None


def signed_user(raw):
    from v8_miniapp import validate_init_data
    # Public, non-AI file utility for ALL bot users, including minors.
    # Deliberately does not grant Study Lab / restricted adult access.
    return account_id(validate_init_data(raw, os.getenv("BOT_TOKEN", "")))


def register_cloudbridge(app, bot):
    from flask import abort, jsonify, make_response, redirect, request, send_file

    if "cloudbridge_v134_home" in app.view_functions:
        return

    @app.after_request
    def cloudbridge_headers(resp):
        if request.path == "/cloud" or request.path.startswith("/cloud/"):
            resp.headers["Cache-Control"] = "no-store"
            resp.headers["X-Content-Type-Options"] = "nosniff"
            resp.headers["Referrer-Policy"] = "no-referrer"
            resp.headers["X-Frame-Options"] = "DENY" if request.path.startswith("/cloud/oauth/") else "SAMEORIGIN"
            if request.path == "/cloud" or request.path.startswith("/cloud/assets/"):
                resp.headers["Content-Security-Policy"] = (
                    "default-src 'none'; script-src 'self' https://telegram.org; "
                    "style-src 'self'; connect-src 'self'; img-src 'self'; "
                    "base-uri 'none'; form-action 'none'; object-src 'none'; "
                    "frame-ancestors https://web.telegram.org https://*.telegram.org"
                )
        return resp

    def gated():
        if not enabled():
            abort(404)

    def auth():
        from v8_miniapp import MiniAppAuthError
        try:
            return signed_user(request.headers.get("X-Telegram-Init-Data", ""))
        except (MiniAppAuthError, BridgeError):
            abort(401, description="Open CloudBridge from Telegram and sign in again.")

    def json_body(max_size=4096):
        if request.content_length is None or request.content_length > max_size:
            abort(413)
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            abort(400)
        return body

    @app.get("/cloud", endpoint="cloudbridge_v134_home")
    def cloud_home():
        gated()
        return send_file(ASSETS / "cloudbridge_v134.html", mimetype="text/html; charset=utf-8")

    @app.get("/cloud/assets/app.js", endpoint="cloudbridge_v134_js")
    def cloud_js():
        gated()
        return send_file(ASSETS / "cloudbridge_v134.js", mimetype="application/javascript")

    @app.get("/cloud/assets/style.css", endpoint="cloudbridge_v134_css")
    def cloud_css():
        gated()
        return send_file(ASSETS / "cloudbridge_v134.css", mimetype="text/css; charset=utf-8")

    @app.get("/cloud/api/session", endpoint="cloudbridge_v134_session")
    def session():
        gated()
        return jsonify({"ok": True, "user_id": auth(), "version": "13.4",
                        "providers": ["google", "onedrive", "dropbox"]})

    @app.route("/cloud/api/jobs", methods=["GET", "POST"], endpoint="cloudbridge_v134_jobs")
    def jobs():
        gated()
        uid = auth()
        try:
            if request.method == "GET":
                return jsonify({"ok": True, "jobs": list_jobs(uid)})
            body = json_body()
            result, fresh = create_job(uid, body)
            return jsonify({"ok": True, "job": result}), 201 if fresh else 200
        except BridgeError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception:
            app.logger.warning("CloudBridge queue database unavailable")
            return jsonify({"error": "Transfer queue temporarily unavailable."}), 503

    @app.post("/cloud/api/jobs/<jid>/<action>", endpoint="cloudbridge_v134_job_action")
    def job_action(jid, action):
        gated()
        uid = auth()
        if action not in {"cancel", "retry", "delete"}:
            abort(404)
        try:
            body = json_body()
            if body:
                raise BridgeError("Action body must be empty JSON.")
            result = update_job(uid, jid, action)
            return (jsonify({"ok": True, "job": result}) if result else
                    (jsonify({"error": "Job not found or state changed."}), 404))
        except BridgeError as exc:
            return jsonify({"error": str(exc)}), 409
        except Exception:
            return jsonify({"error": "Queue temporarily unavailable."}), 503

    @app.get("/cloud/api/accounts", endpoint="cloudbridge_v134_accounts")
    def accounts():
        gated()
        uid = auth()
        try:
            rows = (database().table("cloudbridge_accounts_v134").select("provider,created_at")
                    .eq("user_id", uid).execute()).data or []
            # Never return tokens, ciphertext, emails or linked account IDs.
            return jsonify({"ok": True, "accounts": rows})
        except Exception:
            return jsonify({"error": "Account service unavailable."}), 503

    @app.post("/cloud/api/accounts/<name>/disconnect", endpoint="cloudbridge_v134_disconnect")
    def disconnect(name):
        gated()
        uid = auth()
        try:
            provider(name)
            if json_body():
                raise BridgeError("Request body must be empty JSON.")
            database().table("cloudbridge_accounts_v134").delete().eq("user_id", uid).eq("provider", name).execute()
            return jsonify({"ok": True})
        except BridgeError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception:
            return jsonify({"error": "Account service unavailable."}), 503

    @app.post("/cloud/api/oauth/<name>/start", endpoint="cloudbridge_v134_oauth_start")
    def oauth_start(name):
        gated()
        uid = auth()
        try:
            provider(name)
            if json_body():
                raise BridgeError("Request body must be empty JSON.")
            token, digest = new_oauth_state()
            # The database handles expiration and one-time consumption.
            database().table("cloudbridge_oauth_states_v134").insert({
                "state_hash": digest, "user_id": uid, "provider": name}).execute()
            return jsonify({"ok": True, "url": authorization_url(name, token)})
        except BridgeError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception:
            return jsonify({"error": "Provider connection is not configured."}), 503

    @app.get("/cloud/oauth/callback", endpoint="cloudbridge_v134_callback")
    def callback():
        import hashlib
        gated()
        state = request.args.get("state", "")
        code = request.args.get("code", "")
        if len(state) < 30 or len(state) > 150 or not 1 <= len(code) <= 4096:
            return "Cloud authorization failed. Return to the Mini App.", 400
        try:
            digest = hashlib.sha256(state.encode()).hexdigest()
            rows = database().rpc("cloudbridge_consume_oauth_v134", {"p_hash": digest}).execute().data or []
            if not rows:
                return "Cloud authorization expired or already used.", 400
            record = rows[0]
            uid, name = account_id(int(record["user_id"])), provider(record["provider"])
            tokens = exchange_code(name, code)
            database().table("cloudbridge_accounts_v134").upsert({
                "user_id": uid, "provider": name, "tokens_ciphertext": encrypt_token(tokens)},
                on_conflict="user_id,provider").execute()
            return redirect("/cloud/connected", code=303)
        except Exception:
            app.logger.warning("CloudBridge OAuth callback unsuccessful (no credentials logged)")
            return "Cloud account connection failed. Reopen CloudBridge and try again.", 503

    @app.get("/cloud/connected", endpoint="cloudbridge_v134_connected")
    def connected():
        gated()
        response = make_response("Cloud account connected. Return to the Telegram Mini App and tap Refresh.")
        response.headers["Content-Type"] = "text/plain; charset=utf-8"
        return response

    @bot.message_handler(commands=["cloud", "cloudbridge"])
    def cloud_launcher(message):
        chat = getattr(message, "chat", None)
        if getattr(chat, "type", None) != "private":
            return
        uid = getattr(getattr(message, "from_user", None), "id", None)
        if not enabled() or type(uid) is not int or uid != getattr(chat, "id", None):
            return
        url = public_url()
        if not url:
            bot.send_message(uid, "CloudBridge is not configured yet.")
            return
        from telebot import types
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("☁️ Open CloudBridge", web_app=types.WebAppInfo(url=url + "/cloud")))
        bot.send_message(uid, "Securely connect cloud storage and manage your transfers.", reply_markup=markup)

    @bot.message_handler(commands=["cloudpush"])
    def cloud_push(message):
        """Reply to your Telegram document with: /cloudpush dropbox /folder/name.pdf"""
        chat = getattr(message, "chat", None)
        if not enabled() or getattr(chat, "type", None) != "private":
            return
        uid = getattr(getattr(message, "from_user", None), "id", None)
        if type(uid) is not int or uid != getattr(chat, "id", None):
            return
        try:
            parts = (message.text or "").strip().split(maxsplit=2)
            if len(parts) != 3:
                raise BridgeError("Reply: /cloudpush dropbox /folder/file.pdf")
            name, path = provider(parts[1].lower()), parts[2]
            original = getattr(message, "reply_to_message", None)
            media = getattr(original, "document", None) or getattr(original, "video", None) or getattr(original, "audio", None)
            if media is None:
                raise BridgeError("Reply to a document, video or audio file.")
            filename = safe_filename(getattr(media, "file_name", None) or path.rsplit("/", 1)[-1])
            result, fresh = create_job(uid, {"id": str(uuid4()),
                "filename": filename,
                "source": {"kind": "telegram", "ref": media.file_id},
                "destination": {"kind": "provider", "provider": name, "path": path}})
            bot.send_message(uid, "☁️ Transfer " + ("queued" if fresh else "already queued") + ": " + result["id"])
        except BridgeError as exc:
            bot.send_message(uid, str(exc))
        except Exception:
            bot.send_message(uid, "CloudBridge queue is unavailable. Please try again later.")

    @bot.message_handler(commands=["cloudstatus"])
    def cloud_status(message):
        chat = getattr(message, "chat", None)
        if not enabled() or getattr(chat, "type", None) != "private":
            return
        uid = getattr(getattr(message, "from_user", None), "id", None)
        if type(uid) is not int or uid != getattr(chat, "id", None):
            return
        try:
            jobs = list_jobs(uid)[:5]
            message_text = "\n".join(f"{job['status']} — {job['filename']}" for job in jobs)
            bot.send_message(uid, message_text or "No CloudBridge transfers yet.")
        except Exception:
            bot.send_message(uid, "CloudBridge status is temporarily unavailable.")

    from cloudbridge_v134_worker import start_worker
    start_worker(bot)
