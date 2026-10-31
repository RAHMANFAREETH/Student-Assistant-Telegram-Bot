"""Best-effort queue notifier in existing Render worker. Disabled by default.
Database leases prevent most overlapping sends; exactly-once delivery cannot be guaranteed.
"""
from __future__ import annotations
import logging
import os
import threading
import time
from book_library_v113_store import (claim_notifications,finish_notification,queue_challenge_reminders)

log=logging.getLogger(__name__)
_started=False
_guard=threading.Lock()


def tick(bot):
    queue_challenge_reminders(max_users=100)
    events=claim_notifications(limit=10)
    sent=0
    for item in events:
        ok=False
        try:
            bot.send_message(int(item['user_id']),str(item['body'])[:350])
            ok=True;sent+=1
        except Exception:
            log.warning('Library reminder could not be sent to one subscriber')
        try:finish_notification(item['id'],ok)
        except Exception:log.exception('Library notification completion unavailable')
        time.sleep(.2)
    return sent


def start_worker_if_enabled(bot):
    global _started
    enabled=(os.getenv('BOOK_LIBRARY_ENABLED','false').lower() in ('true','1','yes')
             and os.getenv('BOOK_LIBRARY_V112_ENABLED','false').lower() in ('true','1','yes')
             and os.getenv('BOOK_LIBRARY_V113_ENABLED','false').lower() in ('true','1','yes')
             and os.getenv('BOOK_LIBRARY_NOTIFIER_ENABLED','false').lower() in ('true','1','yes'))
    if not enabled:return False
    with _guard:
        if _started:return False
        _started=True
    def run():
        while True:
            try:tick(bot)
            except Exception:log.exception('Library notification batch failed; will retry')
            time.sleep(max(60,min(int(os.getenv('BOOK_LIBRARY_NOTIFY_INTERVAL_SECONDS','300')),3600)))
    threading.Thread(target=run,daemon=True,name='book-library-v113-notifier').start()
    return True
