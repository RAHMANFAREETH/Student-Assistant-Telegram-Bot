"""Gemini 3.1 Flash-Lite client for a separately restricted 18+ Telegram bot.

Never call this module from the existing mixed-age StudentAssistantBot.
"""
import os
import re
import time
from collections import OrderedDict, deque
from datetime import datetime, timezone
from threading import RLock

import requests

MODEL = "gemini-3.1-flash-lite"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
MAX_QUESTION = 1500
MAX_ANSWER_TOKENS = 900
SYSTEM_PROMPT = (
    "You are an educational study assistant for verified adult students aged 18+. "
    "Support Tamil, Sinhala, Arabic, and English. Answer in the user's language. "
    "Explain topics carefully, show mathematics steps, offer practice quizzes when requested. "
    "Be clear about uncertainty and avoid inventing facts or sources. "
    "Never request credentials, personal contact details, or sensitive student information. "
    "You cannot access the user's uploaded notes or documents unless included in the prompt. "
    "Give study support, not assistance with academic dishonesty."
)

_lock = RLock()
# Pilot quotas are memory-only and reset when a service restarts.
_daily = {}
_global_daily = {}
_minute = deque()
_sessions = OrderedDict()


class GeminiError(Exception):
    def __init__(self, message, code="unavailable"):
        super().__init__(message)
        self.code = code


def enabled():
    return os.getenv("GEMINI_ENABLED", "false").strip().lower() in {"true", "1", "yes"}


def adult_ids():
    return {int(s.strip()) for s in os.getenv("GEMINI_ADULT_USER_IDS", "").split(",")
            if s.strip().isdigit()}


def authorized(user_id):
    """Fail closed. A public-use flag never grants Gemini access.

    IDs must be manually approved as verified adults; an ID is not proof of age.
    """
    return bool(enabled() and os.getenv("GEMINI_API_KEY", "").strip() and
                int(user_id) in adult_ids())


def _limit(name, default, maximum):
    try:
        return min(max(1, int(os.getenv(name, str(default)))), maximum)
    except ValueError:
        return default


def reserve_quota(user_id, now=None):
    """In-memory quotas for ONE Render instance. Not suitable for open public usage."""
    now = time.time() if now is None else now
    day = datetime.fromtimestamp(now, tz=timezone.utc).date().isoformat()
    individual_limit = _limit("GEMINI_DAILY_LIMIT", 8, 20)
    shared_limit = _limit("GEMINI_SHARED_DAILY_LIMIT", 100, 350)
    minute_limit = _limit("GEMINI_SHARED_MINUTE_LIMIT", 8, 12)
    with _lock:
        while _minute and _minute[0] <= now - 60:
            _minute.popleft()
        person = (day, int(user_id))
        if _daily.get(person, 0) >= individual_limit:
            raise GeminiError("⏳ You've reached today's Gemini question limit.", "user_quota")
        if _global_daily.get(day, 0) >= shared_limit or len(_minute) >= minute_limit:
            raise GeminiError("⏳ Gemini's shared limit is busy. Please try later.", "shared_quota")
        _daily[person] = _daily.get(person, 0) + 1
        _global_daily[day] = _global_daily.get(day, 0) + 1
        _minute.append(now)
        # Old days need not remain in memory.
        if len(_global_daily) > 3:
            for previous in sorted(_global_daily)[:-2]:
                _global_daily.pop(previous, None)
            for key in list(_daily):
                if key[0] not in _global_daily:
                    _daily.pop(key, None)
        return _daily[person], individual_limit


def quota_status(user_id):
    day = datetime.now(timezone.utc).date().isoformat()
    with _lock:
        return _daily.get((day, int(user_id)), 0), _limit("GEMINI_DAILY_LIMIT", 8, 20)


def clear_session(user_id):
    with _lock:
        _sessions.pop(int(user_id), None)


def _history(user_id):
    with _lock:
        saved = _sessions.get(int(user_id))
        if not saved or saved["time"] + 1800 < time.monotonic():
            _sessions.pop(int(user_id), None)
            return []
        return list(saved["turns"])


def _remember(user_id, question, answer):
    with _lock:
        uid = int(user_id)
        saved = _sessions.get(uid)
        previous = (saved or {}).get("turns", [])
        turns = (previous + [("user", question), ("model", answer[:1600])])[-6:]
        _sessions[uid] = {"time": time.monotonic(), "turns": turns}
        _sessions.move_to_end(uid)
        while len(_sessions) > 100:
            _sessions.popitem(last=False)


def make_payload(question, history=None):
    contents = [{"role": role, "parts": [{"text": text}]}
                for role, text in (history or []) if role in {"user", "model"}]
    contents.append({"role": "user", "parts": [{"text": question}]})
    return {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": MAX_ANSWER_TOKENS},
    }


def generate(question, user_id, http_post=None):
    """Call Gemini, logging status only; prompts and credentials never logged."""
    if not authorized(user_id):
        raise GeminiError("🔒 Gemini is available only to approved adult testers.", "unauthorized")
    question = (question or "").strip()
    if not question or len(question) > MAX_QUESTION:
        raise GeminiError(f"✂️ Ask a question of 1–{MAX_QUESTION} characters.", "input")
    reserve_quota(user_id)
    request = http_post or requests.post
    try:
        response = request(
            API_URL,
            headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"],
                     "Content-Type": "application/json"},
            json=make_payload(question, _history(user_id)),
            timeout=(5, 35),
        )
    except requests.exceptions.Timeout as exc:
        raise GeminiError("⌛ Gemini timed out. Try again shortly.", "timeout") from exc
    except requests.exceptions.RequestException as exc:
        raise GeminiError("🌐 Could not reach Gemini. Try again later.", "network") from exc
    # No API key, response body, or prompt in logs.
    print("Gemini API HTTP:", response.status_code, flush=True)
    if response.status_code in (401, 403):
        raise GeminiError("🔑 Gemini authorization failed. Ask the admin to check the key.", "auth")
    if response.status_code == 429:
        raise GeminiError("⏳ Gemini rate limit reached. Try again later.", "rate_limit")
    if response.status_code == 404:
        raise GeminiError("⚠️ Gemini model isn't available in this project.", "model")
    if response.status_code >= 400:
        raise GeminiError("⚠️ Gemini request failed. Ask the admin to check Render logs.",
                          f"http_{response.status_code}")
    try:
        result = response.json()
        if (result.get("promptFeedback") or {}).get("blockReason"):
            raise GeminiError("⚠️ Gemini cannot answer this question safely.", "safety")
        candidates = result.get("candidates") or []
        if not candidates:
            raise GeminiError("⚠️ Gemini returned no response.", "empty")
        candidate = candidates[0]
        if candidate.get("finishReason") in {"SAFETY", "PROHIBITED_CONTENT", "SPII", "BLOCKLIST"}:
            raise GeminiError("⚠️ Gemini blocked this answer for safety.", "safety")
        answer = "".join(p.get("text", "") for p in
                         (candidate.get("content") or {}).get("parts", [])
                         if isinstance(p, dict)).strip()
        if not answer:
            raise GeminiError("⚠️ Gemini returned an empty answer.", "empty")
        _remember(user_id, question, answer)
        return answer
    except GeminiError:
        raise
    except (KeyError, ValueError, TypeError, IndexError, AttributeError) as exc:
        raise GeminiError("⚠️ Invalid Gemini response.", "response") from exc
