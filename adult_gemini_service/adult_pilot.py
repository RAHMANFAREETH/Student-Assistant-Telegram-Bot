"""Access-controlled adult professional Gemini pilot logic (no student-bot imports).

Only enable for a manually vetted 18+ professional/developer audience.
An allowlist is access control, NOT age verification or legal compliance.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import RLock
from time import monotonic

from gemini_ai_studio_v59 import LANGUAGES, TASKS, GeminiClientError


class PilotDenied(Exception):
    pass


def allowed_ids(raw: str) -> frozenset[int]:
    """Fail closed on malformed allowlists, including empty comma segments."""
    if not raw.strip():
        return frozenset()
    values = [item.strip() for item in raw.split(",")]
    if any(not x.isascii() or not x.isdecimal() or int(x) < 1 for x in values):
        raise ValueError("Invalid GEMINI_ADULT_USER_IDS; use comma-separated numeric IDs.")
    return frozenset(int(v) for v in values)


def split_message(text: str, limit: int = 3500) -> list[str]:
    if limit < 100:
        raise ValueError("Message limit too small")
    if not text:
        return []
    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        boundary = text.rfind("\n", 0, limit)
        if boundary < limit // 2:
            boundary = text.rfind(" ", 0, limit)
        if boundary < limit // 2:
            boundary = limit
        part = text[:boundary].strip()
        if part:
            parts.append(part)
        text = text[boundary:].lstrip()
    return parts


class AdultPilot:
    """Small pilot guard; quotas are in-memory, per worker, not billing limits."""

    def __init__(self, *, client, adult_user_ids=frozenset(), enabled=False,
                 daily_limit=8, shared_daily_limit=60, minute_limit=5):
        if not 1 <= daily_limit <= 100:
            raise ValueError("daily_limit must be 1..100")
        if not 1 <= shared_daily_limit <= 10000:
            raise ValueError("shared_daily_limit must be 1..10000")
        if not 1 <= minute_limit <= 60:
            raise ValueError("minute_limit must be 1..60")
        self.client = client
        self.allowed = frozenset(adult_user_ids)
        self.enabled = bool(enabled)
        self.daily_limit = daily_limit
        self.shared_daily_limit = shared_daily_limit
        self.minute_limit = minute_limit
        self._day = None
        self._day_users = {}
        self._shared_day = 0
        self._minute = deque()
        self._settings = {}
        self._lock = RLock()

    def check(self, user_id: int, private: bool = True) -> None:
        if not private:
            raise PilotDenied("🔒 This pilot is available in private chats only.")
        if user_id not in self.allowed:
            raise PilotDenied("🔒 This is a restricted adult professional pilot. Access is not enabled for this account.")
        if not self.enabled:
            raise PilotDenied("⏸ Gemini pilot is currently disabled by the operator.")

    def settings(self, user_id: int):
        with self._lock:
            return dict(self._settings.get(user_id, {"task": "ask", "language": "english"}))

    def update_setting(self, user_id: int, name: str, value: str):
        options = {"task": TASKS, "language": LANGUAGES}
        if name not in options or value not in options[name]:
            raise PilotDenied(f"Invalid {name}. Options: " + ", ".join(options.get(name, {})))
        with self._lock:
            settings = self._settings.setdefault(user_id, {"task": "ask", "language": "english"})
            settings[name] = value

    def remaining(self, user_id: int) -> int:
        with self._lock:
            self._rollover()
            return max(0, self.daily_limit - self._day_users.get(user_id, 0))

    def _rollover(self):
        day = datetime.now(timezone.utc).date()
        if day != self._day:
            self._day = day
            self._day_users.clear()
            self._shared_day = 0
            self._minute.clear()

    def answer(self, user_id: int, question: str, *, private=True) -> str:
        self.check(user_id, private=private)
        if not isinstance(question, str) or not question.strip():
            raise PilotDenied("Please send a question.")
        question = question.strip()
        if len(question) > 5000:
            raise PilotDenied("Question too long (maximum 5,000 characters).")
        with self._lock:
            self._rollover()
            now = monotonic()
            while self._minute and now - self._minute[0] >= 60:
                self._minute.popleft()
            if self._day_users.get(user_id, 0) >= self.daily_limit:
                raise PilotDenied("Daily pilot request limit reached (resets at 00:00 UTC).")
            if self._shared_day >= self.shared_daily_limit:
                raise PilotDenied("Shared pilot daily request limit reached.")
            if len(self._minute) >= self.minute_limit:
                raise PilotDenied("Pilot is busy. Please try later.")
            self._day_users[user_id] = self._day_users.get(user_id, 0) + 1
            self._shared_day += 1
            self._minute.append(now)
            settings = dict(self._settings.get(user_id, {"task": "ask", "language": "english"}))
        try:
            return self.client.generate(question, task=settings["task"], language=settings["language"])
        except GeminiClientError as exc:
            raise PilotDenied(str(exc)) from None
        except Exception:
            # Do not expose Google response bodies, request texts, stack traces, or keys.
            raise PilotDenied("Gemini is temporarily unavailable. Please try later.") from None


def register_handlers(bot, pilot: AdultPilot):
    """Register only on the dedicated adult bot, never on the student bot."""
    def who(m):
        return int(m.from_user.id), getattr(m.chat, "type", "") == "private"

    def accept(m):
        uid, private = who(m)
        try:
            pilot.check(uid, private)
        except PilotDenied as exc:
            bot.send_message(m.chat.id, str(exc))
            return None
        return uid

    @bot.message_handler(commands=["myid"])
    def myid(m):
        uid, private = who(m)
        if private:
            bot.send_message(m.chat.id, f"Your Telegram numeric ID: {uid}\nOnly the operator can approve participation after eligibility verification.")

    @bot.message_handler(commands=["start", "help"])
    def start(m):
        uid = accept(m)
        if uid is None:
            return
        bot.send_message(m.chat.id,
            "🔒 Gemini — Restricted 18+ Professional Pilot\n"
            "For manually vetted adult professional/developer participants only.\n"
            "Ask a work/learning question as text or use /ask followed by your question.\n"
            "/language tamil|sinhala|english|arabic\n"
            "/mode ask|explain|maths|quiz|language\n"
            "/quota — remaining local pilot requests\n"
            "⚠️ Do not share confidential data or private student documents. Google processes prompts.")

    @bot.message_handler(commands=["quota"])
    def quota(m):
        uid = accept(m)
        if uid is not None:
            bot.send_message(m.chat.id, f"Pilot requests remaining today: {pilot.remaining(uid)} (UTC; local in-memory counter, not Google quota).")

    @bot.message_handler(commands=["language", "mode"])
    def options(m):
        uid = accept(m)
        if uid is None:
            return
        raw = (m.text or "").split(maxsplit=1)
        cmd = raw[0].split("@", 1)[0].lstrip("/").lower()
        setting = "language" if cmd == "language" else "task"
        option = raw[1].strip().lower() if len(raw) == 2 else ""
        if not option:
            available = LANGUAGES if setting == "language" else TASKS
            bot.send_message(m.chat.id, "Choose: " + ", ".join(available))
            return
        try:
            pilot.update_setting(uid, setting, option)
        except PilotDenied as exc:
            bot.send_message(m.chat.id, str(exc))
            return
        bot.send_message(m.chat.id, f"✅ {setting.capitalize()} set to {option}.")

    @bot.message_handler(commands=["ask"])
    def ask(m):
        uid = accept(m)
        if uid is None:
            return
        parts = (m.text or "").split(maxsplit=1)
        question = parts[1] if len(parts) == 2 else ""
        respond(m, uid, question)

    def respond(m, uid, question):
        try:
            answer = pilot.answer(uid, question)
        except PilotDenied as exc:
            bot.send_message(m.chat.id, str(exc))
            return
        for part in split_message(answer):
            bot.send_message(m.chat.id, part)

    @bot.message_handler(content_types=["text"], func=lambda m: bool(getattr(m, "text", None)))
    def plain_question(m):
        uid = accept(m)
        if uid is None:
            return
        if (m.text or "").startswith("/"):
            bot.send_message(m.chat.id, "Unknown command. Use /help.")
            return
        respond(m, uid, m.text)
