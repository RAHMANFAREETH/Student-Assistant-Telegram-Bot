"""V7.10 optional, consent-based Telegram broadcast for a small private bot.

Users opt in explicitly. Admins must be listed in AI_OPS_ADMIN_IDS.
No new bot, Render service or API provider is required.
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass

TABLE = "bot_broadcast_subscribers"
MAX_RECIPIENTS = 100
MAX_TEXT = 3500
PREVIEW_TTL_SECONDS = 600
MIN_SEND_INTERVAL_SECONDS = 0.15


def admin_ids() -> frozenset[int]:
    # Reuse the existing explicitly admin-only configuration; not AI_ALLOWED_USER_IDS.
    values = os.getenv("AI_OPS_ADMIN_IDS", "")
    return frozenset(
        int(s) for part in values.split(",")
        if (s := part.strip()).isascii() and s.isdecimal() and int(s) > 0
    )


def is_private(message) -> bool:
    chat = getattr(message, "chat", None)
    user = getattr(message, "from_user", None)
    return bool(chat and user and getattr(chat, "type", None) == "private"
                and int(chat.id) == int(user.id))


def code_and_wait(exc):
    """Extract only safe structured Telegram error info, not exception bodies."""
    code = getattr(exc, "error_code", None)
    result = getattr(exc, "result_json", None)
    parameters = result.get("parameters", {}) if isinstance(result, dict) else {}
    if not isinstance(parameters, dict):
        parameters = {}
    try:
        wait = max(1, min(15, int(parameters.get("retry_after", 2))))
    except (TypeError, ValueError):
        wait = 2
    return code, wait


@dataclass(frozen=True)
class Preview:
    text: str
    user_ids: frozenset[int]
    created: float
    audience: str = "subscribers"


class AnnouncementService:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self._lock = threading.Lock()
        self._pending: dict[int, Preview] = {}
        self._pending_all_draft: dict[int, float] = {}
        self._active = False
        self._last = "No broadcast has been started in this process."

    def _admin(self, message) -> bool:
        if not is_private(message):
            self.bot.send_message(message.chat.id, "🔒 Admin broadcasts work only in your private bot chat.")
            return False
        if int(message.from_user.id) not in admin_ids():
            self.bot.send_message(message.chat.id, "🔒 This command is for bot administrators only.")
            return False
        return True

    def _subscriber_rows(self):
        response = (self.db.table(TABLE).select("user_id,chat_id")
                    .eq("subscribed", True).limit(MAX_RECIPIENTS + 1).execute())
        rows = response.data or []
        if len(rows) > MAX_RECIPIENTS:
            raise ValueError("recipient_limit")
        result = {}
        for row in rows:
            user_id, chat_id = int(row["user_id"]), int(row["chat_id"])
            if user_id > 0 and user_id == chat_id:
                result[user_id] = chat_id
        return result

    def _is_subscribed(self, user_id):
        response = (self.db.table(TABLE).select("user_id")
                    .eq("user_id", user_id).eq("subscribed", True).limit(1).execute())
        return bool(response.data)

    def _known_user_rows(self):
        """Known private-chat IDs; does not require /subscribe.

        Explicit opt-outs, blocked users, and invalid IDs are always excluded.
        If preferences cannot be checked, abort rather than accidentally sending.
        """
        response = (self.db.table("bot_known_users_v712")
                    .select("user_id,chat_id")
                    .order("user_id").limit(MAX_RECIPIENTS + 1).execute())
        rows = response.data or []
        if len(rows) > MAX_RECIPIENTS:
            raise ValueError("recipient_limit")
        result = {}
        for row in rows:
            uid, chat_id = int(row["user_id"]), int(row["chat_id"])
            if uid > 0 and uid == chat_id:
                result[uid] = chat_id
        if not result:
            return result
        preferences = (self.db.table(TABLE).select("user_id,subscribed")
                       .in_("user_id", list(result)).execute()).data or []
        for pref in preferences:
            if pref.get("subscribed") is False:
                result.pop(int(pref["user_id"]), None)
        return result

    def _known_user_eligible(self, user_id):
        """Fail closed if either the known-user table or preference lookup fails."""
        known = (self.db.table("bot_known_users_v712").select("user_id")
                 .eq("user_id", int(user_id)).limit(1).execute()).data or []
        if not known:
            return False
        pref = (self.db.table(TABLE).select("subscribed")
                .eq("user_id", int(user_id)).limit(1).execute()).data or []
        return not any(row.get("subscribed") is False for row in pref)

    def subscription(self, message, enabled: bool):
        if not is_private(message):
            self.bot.send_message(message.chat.id,
                                  "📢 Open the bot in a private chat to manage announcements.")
            return
        uid = int(message.from_user.id)
        try:
            self.db.table(TABLE).upsert({
                "user_id": uid, "chat_id": uid, "subscribed": bool(enabled)
            }, on_conflict="user_id").execute()
        except Exception:
            self.bot.send_message(message.chat.id,
                                  "⚠️ Announcement preferences are unavailable. Ask the admin to check Supabase setup.")
            return
        if enabled:
            self.bot.send_message(message.chat.id,
                "✅ Announcements enabled. To stop: /announcements off.")
        else:
            self.bot.send_message(message.chat.id,
                "✅ Bot announcements disabled. To resume: /announcements on.")

    def announcements(self, message):
        # V7.12.1 preference routing: /announcements on|off, no /unsubscribe handler.
        if not is_private(message):
            self.bot.send_message(message.chat.id,
                "📢 Manage announcements in your private chat with the bot.")
            return
        parts = (getattr(message, "text", "") or "").strip().split(maxsplit=1)
        action = parts[1].strip().lower() if len(parts) > 1 else ""
        if action in ("on", "off"):
            self.subscription(message, action == "on")
            return
        if action:
            self.bot.send_message(message.chat.id,
                "📢 Use /announcements, /announcements on, or /announcements off.")
            return
        try:
            rows = (self.db.table(TABLE).select("subscribed")
                    .eq("user_id", int(message.from_user.id))
                    .limit(1).execute()).data or []
        except Exception:
            self.bot.send_message(message.chat.id,
                "⚠️ Announcement preferences are unavailable. Ask the admin to check Supabase setup.")
            return
        if rows and rows[0].get("subscribed") is False:
            response = "📢 Bot announcements are OFF. To resume: /announcements on."
        elif rows and rows[0].get("subscribed") is True:
            response = "📢 Bot announcements are ON. To stop: /announcements off."
        else:
            response = ("📢 No announcement preference set. Subscriber-only messages "
                        "require /subscribe. To stop other bot announcements: "
                        "/announcements off.")
        self.bot.send_message(message.chat.id, response)

    def recipients(self, message):
        if not self._admin(message):
            return
        try:
            n = len(self._subscriber_rows())
        except ValueError:
            self.bot.send_message(message.chat.id,
                                  "⚠️ More than 100 subscribers. Upgrade the broadcast limit before sending.")
            return
        except Exception:
            self.bot.send_message(message.chat.id,
                                  "⚠️ Cannot read subscribers. Run SQL_V7_10_BROADCAST.sql in Supabase.")
            return
        self.bot.send_message(message.chat.id,
                              f"📢 {n} users currently subscribed to announcements.")

    def preview(self, message):
        if not self._admin(message):
            return
        text = (getattr(message, "text", "") or "").partition(" ")[2].strip()
        if not text or len(text) > MAX_TEXT:
            self.bot.send_message(message.chat.id,
                f"Usage: /broadcast Your announcement here\nMaximum: {MAX_TEXT} characters.")
            return
        try:
            users = self._subscriber_rows()
        except ValueError:
            self.bot.send_message(message.chat.id, "⚠️ Recipient limit exceeded. Nothing was sent.")
            return
        except Exception:
            self.bot.send_message(message.chat.id,
                "⚠️ Cannot load subscribers. Run SQL_V7_10_BROADCAST.sql in Supabase. Nothing was sent.")
            return
        if not users:
            self.bot.send_message(message.chat.id,
                "📭 No subscribers yet. Ask users to send /subscribe in a private chat with the bot.")
            return
        with self._lock:
            if self._active:
                self.bot.send_message(message.chat.id,
                    "⏳ Another broadcast is still running. Check /broadcaststatus.")
                return
            self._pending[int(message.from_user.id)] = Preview(
                text, frozenset(users), time.monotonic())
        self.bot.send_message(message.chat.id,
            f"📢 BROADCAST PREVIEW\n\n{text}\n\n"
            f"Recipients: {len(users)} opted-in users\n\n"
            "✅ Send: /broadcastconfirm\n❌ Cancel: /broadcastcancel\n"
            "Preview expires in 10 minutes. New subscribers after this preview will not receive it.")

    def preview_all(self, message):
        """Admin-only service announcement to known existing bot users."""
        if not self._admin(message):
            return
        uid = int(message.from_user.id)
        text = (getattr(message, "text", "") or "").partition(" ")[2].strip()
        if not text:
            with self._lock:
                self._pending_all_draft[uid] = time.monotonic()
            self.bot.send_message(message.chat.id,
                "📢 Send your announcement as the NEXT text message.\n"
                "Nothing is sent until /broadcastallconfirm.\n"
                "Cancel: /broadcastallcancel")
            return
        self._make_all_preview(message, text)

    def pending_all_text(self, message):
        """Catch the next plain-text admin message after /broadcastall."""
        if not is_private(message) or int(message.from_user.id) not in admin_ids():
            return False
        text = (getattr(message, "text", "") or "").strip()
        if not text or text.startswith("/") or text in (
            "🏠 Main Menu", "⬅️ Back", "❌ Cancel", "📦 More Tools"):
            return False
        with self._lock:
            start = self._pending_all_draft.get(int(message.from_user.id))
            return start is not None and (time.monotonic() - start <= PREVIEW_TTL_SECONDS)

    def accept_all_text(self, message):
        with self._lock:
            self._pending_all_draft.pop(int(message.from_user.id), None)
        self._make_all_preview(message, (message.text or "").strip())

    def _make_all_preview(self, message, text):
        uid = int(message.from_user.id)
        footer = "\n\nTo stop future bot announcements: /announcements off"
        payload = text if "/announcements off" in text else text + footer
        if not text or len(payload) > MAX_TEXT:
            self.bot.send_message(message.chat.id,
                f"⚠️ Announcement plus preference instructions must fit {MAX_TEXT} characters. Nothing was sent.")
            return
        try:
            users = self._known_user_rows()
        except ValueError:
            self.bot.send_message(message.chat.id,
                "⚠️ More than 100 known users. Nothing was sent. Contact the developer.")
            return
        except Exception:
            self.bot.send_message(message.chat.id,
                "⚠️ Could not load known users/preferences. Run SQL_V7_12_KNOWN_USERS.sql. Nothing was sent.")
            return
        if not users:
            self.bot.send_message(message.chat.id,
                "📭 No known eligible users yet. Run the V7.12 SQL migration. Nothing was sent.")
            return
        with self._lock:
            if self._active:
                self.bot.send_message(message.chat.id,
                    "⏳ Another broadcast is still running. Check /broadcaststatus.")
                return
            self._pending[uid] = Preview(payload, frozenset(users), time.monotonic(), "all")
            self._pending_all_draft.pop(uid, None)
        self.bot.send_message(message.chat.id,
            f"📢 KNOWN USERS ANNOUNCEMENT PREVIEW\n\n{payload}\n\n"
            f"Recipients: {len(users)} known users (explicit opt-outs excluded).\n\n"
            "✅ Send: /broadcastallconfirm\n❌ Cancel: /broadcastallcancel\n"
            "Preview expires in 10 minutes. New users after preview are excluded.\n"
            "For important bot updates only; recipients can choose /announcements off.")

    def known_count(self, message):
        if not self._admin(message):
            return
        try:
            n = len(self._known_user_rows())
        except ValueError:
            self.bot.send_message(message.chat.id, "⚠️ More than 100 known users; sending is disabled.")
            return
        except Exception:
            self.bot.send_message(message.chat.id,
                                  "⚠️ Cannot read known users. Run SQL_V7_12_KNOWN_USERS.sql.")
            return
        self.bot.send_message(message.chat.id,
            f"📢 Known eligible private-chat users: {n}. No /subscribe required.")

    def cancel_all(self, message):
        if not self._admin(message):
            return
        uid = int(message.from_user.id)
        with self._lock:
            self._pending_all_draft.pop(uid, None)
            pending = self._pending.get(uid)
            removed = self._pending.pop(uid, None) if pending and pending.audience == "all" else None
        self.bot.send_message(message.chat.id,
            "✅ Known-user draft canceled. Nothing was sent." if removed else
            "✅ Compose mode canceled. Nothing was sent.")

    def confirm_all(self, message):
        if not self._admin(message):
            return
        uid = int(message.from_user.id)
        with self._lock:
            if self._active:
                self.bot.send_message(message.chat.id, "⏳ A broadcast is already running.")
                return
            preview = self._pending.get(uid)
            if not preview or preview.audience != "all" or time.monotonic() - preview.created > PREVIEW_TTL_SECONDS:
                if preview and preview.audience == "all":
                    self._pending.pop(uid, None)
                self.bot.send_message(message.chat.id,
                    "No valid known-users preview. Start with /broadcastall Your message.")
                return
            self._pending.pop(uid, None)
            try:
                current = self._known_user_rows()
            except Exception:
                self.bot.send_message(message.chat.id,
                    "⚠️ Cannot verify known users and opt-outs. Nothing was sent.")
                return
            destinations = [current[uid] for uid in sorted(preview.user_ids) if uid in current]
            if not destinations:
                self.bot.send_message(message.chat.id, "📭 No eligible users remain. Nothing was sent.")
                return
            self._active = True
            self._last = f"⏳ Sending bot update to {len(destinations)} known users."
        try:
            worker = threading.Thread(target=self._send_batch,
                args=(message.chat.id, preview.text, destinations, "all"),
                daemon=True, name="known-user-announcement-sender")
            worker.start()
        except Exception:
            with self._lock:
                self._active = False
                self._last = "⚠️ Broadcast worker failed to start. Nothing was sent."
            self.bot.send_message(message.chat.id, self._last)
            return
        self.bot.send_message(message.chat.id,
            f"📤 Sending to {len(destinations)} known users. Check /broadcaststatus.\n"
            "If Render restarts, delivery may be incomplete. Do not resend blindly.")

    def cancel(self, message):
        if not self._admin(message):
            return
        with self._lock:
            removed = self._pending.pop(int(message.from_user.id), None)
        self.bot.send_message(message.chat.id,
                              "✅ Draft discarded. No message was sent." if removed
                              else "No pending draft to cancel.")

    def confirm(self, message):
        if not self._admin(message):
            return
        uid = int(message.from_user.id)
        with self._lock:
            if self._active:
                self.bot.send_message(message.chat.id, "⏳ A broadcast is already running.")
                return
            preview = self._pending.get(uid)
            if preview is None or preview.audience != "subscribers" or time.monotonic() - preview.created > PREVIEW_TTL_SECONDS:
                self.bot.send_message(message.chat.id,
                                      "No valid preview. Start with /broadcast Your message.")
                return
            self._pending.pop(uid, None)
            try:
                current = self._subscriber_rows()
            except Exception:
                self.bot.send_message(message.chat.id,
                                      "⚠️ Cannot verify subscriptions. Nothing was sent.")
                return
            # Re-check opt-out; never include people who subscribed only after preview.
            destinations = [current[user_id] for user_id in sorted(preview.user_ids)
                            if user_id in current]
            if not destinations:
                self.bot.send_message(message.chat.id,
                                      "📭 No eligible subscribers remain. Nothing was sent.")
                return
            self._active = True
            self._last = f"⏳ Broadcast sending to {len(destinations)} subscribers."
        try:
            worker = threading.Thread(
                target=self._send_batch,
                args=(message.chat.id, preview.text, destinations),
                daemon=True, name="announcement-sender",
            )
            worker.start()
        except Exception:
            with self._lock:
                self._active = False
                self._last = "⚠️ Broadcast worker could not start. Nothing was sent."
            self.bot.send_message(message.chat.id, self._last)
            return
        self.bot.send_message(message.chat.id,
            f"📤 Broadcast started for {len(destinations)} subscribers. Check /broadcaststatus shortly."
            "\nIf the Render process restarts mid-send, delivery may be incomplete; do not resend blindly.")

    def _send_batch(self, admin_chat_id, text, destinations, audience="subscribers"):
        sent, failed, stopped = 0, 0, 0
        try:
            for chat_id in destinations:
                try:
                    eligible = (self._known_user_eligible(chat_id) if audience == "all"
                                else self._is_subscribed(chat_id))
                    if not eligible:
                        stopped += 1
                        continue
                except Exception:
                    failed += 1
                    continue
                for attempt in range(2):
                    try:
                        self.bot.send_message(chat_id, text, parse_mode=None)
                        sent += 1
                        break
                    except Exception as exc:
                        code, wait = code_and_wait(exc)
                        if code == 429 and attempt == 0:
                            time.sleep(wait)
                            continue
                        if code == 403:
                            try:
                                self.db.table(TABLE).upsert({
                                    "user_id": chat_id, "chat_id": chat_id,
                                    "subscribed": False,
                                }, on_conflict="user_id").execute()
                            except Exception:
                                pass
                        failed += 1
                        break
                time.sleep(MIN_SEND_INTERVAL_SECONDS)
        finally:
            status = (f"✅ Broadcast finished. Sent: {sent}, failed: {failed}, "
                      f"opted out before sending: {stopped}.")
            with self._lock:
                self._active = False
                self._last = status
            try:
                self.bot.send_message(admin_chat_id, status)
            except Exception:
                pass

    def status(self, message):
        if not self._admin(message):
            return
        with self._lock:
            current = self._last
        self.bot.send_message(message.chat.id, current)

    def direct(self, message):
        if not self._admin(message):
            return
        rest = (getattr(message, "text", "") or "").partition(" ")[2].strip()
        uid, _, text = rest.partition(" ")
        if not uid.isascii() or not uid.isdecimal() or not text.strip() or len(text) > MAX_TEXT:
            self.bot.send_message(message.chat.id,
                                  "Usage: /messageuser 123456789 Your message")
            return
        target = int(uid)
        try:
            allowed = self._is_subscribed(target)
        except Exception:
            self.bot.send_message(message.chat.id,
                                  "⚠️ Cannot verify recipient subscription. Nothing was sent.")
            return
        if not allowed:
            self.bot.send_message(message.chat.id,
                                  "📭 This user has not opted in to bot announcements. Nothing was sent.")
            return
        try:
            self.bot.send_message(target, text.strip(), parse_mode=None)
        except Exception as exc:
            code, _ = code_and_wait(exc)
            if code == 403:
                try:
                    self.db.table(TABLE).upsert({
                        "user_id": target, "chat_id": target, "subscribed": False
                    }, on_conflict="user_id").execute()
                except Exception:
                    pass
            self.bot.send_message(message.chat.id,
                                  "⚠️ Message could not be delivered. The user may have blocked the bot.")
            return
        self.bot.send_message(message.chat.id, "✅ Private message sent to the subscribed user.")


def track_known_private_user(update, db=None):
    """Register a known private-chat user. Metadata only; never log message text.

    Called from authenticated Telegram webhook before handlers. Database errors
    must not stop processing an otherwise valid Telegram update.
    """
    try:
        message = getattr(update, "message", None)
        callback = getattr(update, "callback_query", None)
        if message is not None:
            chat, user = getattr(message, "chat", None), getattr(message, "from_user", None)
        elif callback is not None:
            chat = getattr(getattr(callback, "message", None), "chat", None)
            user = getattr(callback, "from_user", None)
        else:
            return False
        if not chat or not user or getattr(chat, "type", None) != "private":
            return False
        uid, cid = int(user.id), int(chat.id)
        if uid <= 0 or cid != uid or getattr(user, "is_bot", False):
            return False
        if db is None:
            from db import supabase
            db = supabase
        from datetime import datetime, timezone
        db.table("bot_known_users_v712").upsert({
            "user_id": uid, "chat_id": cid,
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            "source": "private_chat",
        }, on_conflict="user_id").execute()
        return True
    except Exception:
        # Tracking is supplementary; never break /start or the Telegram webhook.
        return False


def register_broadcast_handlers(bot, db=None):
    if db is None:
        from db import supabase
        db = supabase
    service = AnnouncementService(bot, db)

    @bot.message_handler(commands=["subscribe"])
    def subscribe(message):
        service.subscription(message, True)

    @bot.message_handler(commands=["announcements"])
    def announcements(message):
        service.announcements(message)

    @bot.message_handler(commands=["broadcastusers"])
    def broadcastusers(message):
        service.recipients(message)

    @bot.message_handler(commands=["broadcast"])
    def broadcast(message):
        service.preview(message)

    @bot.message_handler(commands=["broadcastconfirm"])
    def broadcastconfirm(message):
        service.confirm(message)

    @bot.message_handler(commands=["broadcastcancel"])
    def broadcastcancel(message):
        service.cancel(message)

    @bot.message_handler(commands=["broadcaststatus"])
    def broadcaststatus(message):
        service.status(message)

    @bot.message_handler(commands=["messageuser"])
    def messageuser(message):
        service.direct(message)

    return service


def register_known_broadcast_handlers(bot, service):
    """Install V7.12 commands alongside existing V7.10 commands."""

    @bot.message_handler(commands=["broadcastallusers"])
    def broadcastallusers(message):
        service.known_count(message)

    @bot.message_handler(commands=["broadcastall"])
    def broadcastall(message):
        service.preview_all(message)

    @bot.message_handler(commands=["broadcastallconfirm"])
    def broadcastallconfirm(message):
        service.confirm_all(message)

    @bot.message_handler(commands=["broadcastallcancel"])
    def broadcastallcancel(message):
        service.cancel_all(message)

    # Registered after the command handlers but before the other bot modules.
    # Only intercepts the next plain-text admin message in compose mode.
    # Older V7.10 unit-test bots implement command-only message_handler;
    # skip this optional text handler only for those limited test doubles.
    try:
        next_text_handler = bot.message_handler(
            func=lambda m: service.pending_all_text(m), content_types=["text"])
    except TypeError:
        next_text_handler = None
    if next_text_handler is not None:
        next_text_handler(service.accept_all_text)

    return service
