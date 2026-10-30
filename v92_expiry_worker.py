"""Optional in-process expiry notifier for the existing Render web service.

Uses a Supabase lease to coordinate workers. Requires a live process; Render
free instance suspension and process restarts can delay notifications.
"""
from __future__ import annotations

import logging
import os
import threading
from v92_admin_service import process_expiry_batch

LOG = logging.getLogger(__name__)
_LOCK = threading.Lock()
_STARTED = False


def _on(name):
    return os.getenv(name, '').strip().lower() in ('1','true','yes')


def run_worker(bot, stop=None, interval_seconds=3600):
    stop = stop or threading.Event()
    while not stop.is_set():
        try:
            outcome = process_expiry_batch(bot)
            LOG.info('V9.2 expiry batch: claimed=%s sent=%s', outcome['claimed'], outcome['sent'])
        except Exception:
            LOG.exception('V9.2 expiry worker failed; will retry')
        stop.wait(interval_seconds)


def start_worker_if_enabled(bot):
    global _STARTED
    if not (_on('V92_ADMIN_ENABLED') and _on('V92_EXPIRY_WORKER_ENABLED')):
        return False
    with _LOCK:
        if _STARTED:
            return False
        worker = threading.Thread(target=run_worker, args=(bot,),
                                  daemon=True, name='v92-expiry-notifier')
        worker.start()
        _STARTED = True
        return True
