"""Independent Telegram webhook app for vetted 18+ professional participants.

This file lives in adult_gemini_service/ and must NEVER replace the public bot's main.py.
"""
from __future__ import annotations

import hmac
import os
import re

from flask import Flask, jsonify, request
import telebot

from adult_pilot import AdultPilot, allowed_ids, register_handlers
from gemini_ai_studio_v59 import GeminiClient, read_api_key


def checked_secret(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,256}", value or ""):
        raise ValueError("ADULT_GEMINI_WEBHOOK_SECRET must be 16-256 characters, A-Z a-z 0-9 _ - only")
    return value


def create_app(*, bot_override=None, pilot_override=None, register_webhook=True):
    app = Flask(__name__)
    secret = checked_secret(os.environ.get("ADULT_GEMINI_WEBHOOK_SECRET", ""))
    token = os.environ.get("ADULT_GEMINI_BOT_TOKEN", "").strip()
    if not token and bot_override is None:
        raise ValueError("ADULT_GEMINI_BOT_TOKEN is required for separate bot")
    if token and os.environ.get("BOT_TOKEN", "") == token:
        raise ValueError("Do not reuse public BOT_TOKEN in adult pilot")
    enabled = os.environ.get("GEMINI_ENABLED", "false").lower() == "true"
    ids = allowed_ids(os.environ.get("GEMINI_ADULT_USER_IDS", ""))
    if enabled and not ids:
        raise ValueError("Refusing to enable Gemini with empty adult allowlist")
    api_key = read_api_key()
    if enabled and not api_key and pilot_override is None:
        raise ValueError("GEMINI_API_KEY required when GEMINI_ENABLED=true")
    bot = bot_override or telebot.TeleBot(token, threaded=False)
    pilot = pilot_override or AdultPilot(
        client=GeminiClient(api_key or "disabled-placeholder"),
        adult_user_ids=ids,
        enabled=enabled,
        daily_limit=int(os.environ.get("GEMINI_DAILY_LIMIT", "8")),
        shared_daily_limit=int(os.environ.get("GEMINI_SHARED_DAILY_LIMIT", "60")),
        minute_limit=int(os.environ.get("GEMINI_SHARED_MINUTE_LIMIT", "5")),
    )
    register_handlers(bot, pilot)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "restricted-gemini-pilot"})

    @app.post("/telegram-gemini-webhook")
    def telegram_webhook():
        supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not hmac.compare_digest(supplied, secret):
            return ("Forbidden", 403)
        if request.content_length is not None and request.content_length > 100_000:
            return ("Too large", 413)
        try:
            raw = request.get_data(cache=False)
            if len(raw) > 100_000:
                return ("Too large", 413)
            update = telebot.types.Update.de_json(raw.decode("utf-8"))
            if update:
                bot.process_new_updates([update])
        except Exception as exc:
            # No secret, user prompt, or Telegram update dumps in logs.
            app.logger.error("Adult pilot update error type: %s", type(exc).__name__)
            return ("Update error", 500)
        return ("OK", 200)

    if register_webhook:
        base = os.environ.get("ADULT_GEMINI_PUBLIC_URL", "").strip().rstrip("/")
        if not base.startswith("https://") or not base[8:] or "/" in base[8:]:
            raise ValueError("Set ADULT_GEMINI_PUBLIC_URL to exact public https://your-service.onrender.com")
        if not bot.set_webhook(url=base + "/telegram-gemini-webhook", secret_token=secret):
            raise RuntimeError("Could not register adult pilot Telegram webhook")
    return app


# Gunicorn imports app:app; real service config is validated at import.
if __name__ == "app" or __name__ == "__main__":
    app = create_app()
