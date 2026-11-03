"""Separate 18+ Gemini Telegram bot. Not part of the public StudentAssistantBot."""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import telebot
from telebot.apihelper import ApiTelegramException
from flask import Flask, request

from gemini_engine import GeminiError, authorized, generate, clear_session, quota_status

TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip()

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False) if TOKEN else None
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="gemini-adult")
_busy = set()
_busy_lock = Lock()


def safe_send(chat_id, text):
    if not bot:
        return
    # Telegram text messages cannot exceed 4096 characters.
    for offset in range(0, len(text), 3500):
        try:
            bot.send_message(chat_id, text[offset:offset+3500])
        except ApiTelegramException as exc:
            if exc.error_code == 403:
                print("Telegram recipient unavailable (403)", flush=True)
                return
            print("Telegram send failed:", exc.error_code, flush=True)
            return


def private_and_allowed(message):
    if message.chat.type != "private":
        safe_send(message.chat.id, "🔒 Please use this bot in a private chat.")
        return False
    if not authorized(message.from_user.id):
        safe_send(message.chat.id,
                  "🔒 This is a separate, restricted Gemini pilot for verified adults aged 18+. "
                  "Access must be approved by the administrator.")
        return False
    return True


def answer_job(chat_id, user_id, question):
    try:
        safe_send(chat_id, generate(question, user_id))
    except GeminiError as exc:
        print("Gemini issue:", exc.code, flush=True)
        safe_send(chat_id, str(exc))
    except Exception as exc:
        print("Gemini unexpected error type:", type(exc).__name__, flush=True)
        safe_send(chat_id, "⚠️ Something went wrong. Please try again later.")
    finally:
        with _busy_lock:
            _busy.discard(user_id)


if bot:
    @bot.message_handler(commands=["start", "help"])
    def start(message):
        if not private_and_allowed(message):
            return
        safe_send(message.chat.id,
                  "🤖 Gemini Adult Study Assistant\n\n"
                  "Ask a study question in Tamil, Sinhala, English or Arabic.\n"
                  "Send /clear to erase temporary conversation memory, or /quota for your remaining test requests.\n\n"
                  "⚠️ AI can be mistaken. Don't submit personal, sensitive, or confidential data. "
                  "Gemini free-tier content may be used by Google to improve its services.")

    @bot.message_handler(commands=["clear"])
    def clear(message):
        if private_and_allowed(message):
            clear_session(message.from_user.id)
            safe_send(message.chat.id, "🧹 Temporary chat cleared.")

    @bot.message_handler(commands=["quota"])
    def quota(message):
        if private_and_allowed(message):
            used, limit = quota_status(message.from_user.id)
            safe_send(message.chat.id, f"📊 Today: {used}/{limit} questions (UTC reset; pilot counter resets on restart).")

    @bot.message_handler(content_types=["text"])
    def ask(message):
        if not private_and_allowed(message):
            return
        question = (message.text or "").strip()
        if not question or question.startswith("/"):
            safe_send(message.chat.id, "Please send a study question.")
            return
        uid = int(message.from_user.id)
        with _busy_lock:
            if uid in _busy:
                safe_send(message.chat.id, "⏳ Your previous question is still being answered.")
                return
            if len(_busy) >= 2:
                safe_send(message.chat.id, "⏳ All pilot AI slots are busy. Please try shortly.")
                return
            _busy.add(uid)
        try:
            _pool.submit(answer_job, message.chat.id, uid, question)
        except RuntimeError:
            with _busy_lock:
                _busy.discard(uid)
            safe_send(message.chat.id, "⚠️ AI worker is unavailable.")
            return
        safe_send(message.chat.id, "🤖 Thinking...")


@app.get("/")
def health():
    return {"status": "ok", "bot": "Gemini adult-only companion", "enabled": bool(bot)}, 200


@app.post("/telegram-webhook")
def webhook():
    # Fail closed if secret is missing or invalid.
    if (not bot or not WEBHOOK_SECRET or
            request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET):
        return "Forbidden", 403
    try:
        update = telebot.types.Update.de_json(request.get_data(as_text=True))
        bot.process_new_updates([update])
    except ApiTelegramException as exc:
        if exc.error_code == 403:
            print("Telegram blocked-user update acknowledged", flush=True)
            return "OK", 200
        print("Telegram API error:", exc.error_code, flush=True)
        return "Error", 500
    except Exception as exc:
        print("Webhook exception type:", type(exc).__name__, flush=True)
        return "Error", 500
    return "OK", 200


def register_webhook():
    if not bot or not RENDER_URL or not WEBHOOK_SECRET:
        print("Webhook not configured; set BOT_TOKEN, RENDER_EXTERNAL_URL and WEBHOOK_SECRET", flush=True)
        return
    try:
        result = bot.set_webhook(
            url=RENDER_URL.rstrip("/") + "/telegram-webhook",
            secret_token=WEBHOOK_SECRET,
            allowed_updates=["message"],
        )
        print("Gemini companion webhook registered:", bool(result), flush=True)
    except Exception as exc:
        print("Webhook registration error type:", type(exc).__name__, flush=True)


# Render with one worker: gunicorn main:app --workers 1 --threads 4 ...
if RENDER_URL:
    register_webhook()

if __name__ == "__main__":
    if bot and not RENDER_URL:
        bot.remove_webhook()
        bot.infinity_polling(skip_pending=True)
    else:
        app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
