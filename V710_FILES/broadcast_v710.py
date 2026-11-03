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


class AnnouncementService:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self._lock = threading.Lock()
        self._pending: dict[int, Preview] = {}
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
                "✅ You subscribed to occasional bot announcements. To stop them, send /unsubscribe.")
        else:
            self.bot.send_message(message.chat.id,
                "✅ You unsubscribed from announcements. To rejoin, send /subscribe.")

    def announcements(self, message):
        if not is_private(message):
            self.bot.send_message(message.chat.id, "📢 Use /announcements in a private chat with the bot.")
            return
        try:
            enabled = self._is_subscribed(int(message.from_user.id))
        except Exception:
            self.bot.send_message(message.chat.id,
                "⚠️ Announcement preferences are unavailable. Ask the admin to check Supabase setup.")
            return
        self.bot.send_message(message.chat.id,
            ("📢 Announcements are ON. Send /unsubscribe to stop them."
             if enabled else "📢 Announcements are OFF. Send /subscribe to receive updates."))

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
            preview = self._pending.pop(uid, None)
            if preview is None or time.monotonic() - preview.created > PREVIEW_TTL_SECONDS:
                self.bot.send_message(message.chat.id,
                                      "No valid preview. Start with /broadcast Your message.")
                return
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

    def _send_batch(self, admin_chat_id, text, destinations):
        sent, failed, stopped = 0, 0, 0
        try:
            for chat_id in destinations:
                try:
                    if not self._is_subscribed(chat_id):
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


def register_broadcast_handlers(bot, db=None):
    if db is None:
        from db import supabase
        db = supabase
    service = AnnouncementService(bot, db)

    @bot.message_handler(commands=["subscribe"])
    def subscribe(message):
        service.subscription(message, True)

    @bot.message_handler(commands=["unsubscribe"])
    def unsubscribe(message):
        service.subscription(message, False)

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
