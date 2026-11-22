"""Durable CloudBridge queue runner, with atomic Supabase RPC claims.

The DB is the source of truth; no in-memory queue or automatic unsafe retry.
For reliably prompt execution use a dedicated always-on worker. Render web
instances may sleep, in which case queued transfers wait until a worker runs.
"""
from __future__ import annotations

import logging
import os
import tempfile
import threading
import time
import uuid

from cloudbridge_v134_core import BridgeError, database
from cloudbridge_v134_providers import download_provider, download_https, upload_provider

LOGGER = logging.getLogger(__name__)
_worker_started = False


class Cancelled(Exception):
    pass


def max_bytes():
    # V13.6 Google Drive streaming supports up to 4096 MiB; legacy transfers
    # still use temporary disk and keep their original <=1024 MiB safety cap.
    try:
        value = int(os.getenv("CLOUDBRIDGE_MAX_MB", "100"))
    except ValueError:
        value = 100
    return max(1, min(value, 4096)) * 1024 * 1024


def _cancel_check(row, db):
    result = (db.table("cloudbridge_jobs_v134").select("cancel_requested")
              .eq("user_id", row["user_id"]).eq("id", row["id"]).limit(1).execute()).data or []
    if not result or result[0].get("cancel_requested"):
        raise Cancelled()


def _set_state(row, db, **values):
    (db.table("cloudbridge_jobs_v134").update(values)
     .eq("user_id", row["user_id"]).eq("id", row["id"]).execute())


def _download_telegram(file_id, handle, limit, bot, cancel):
    import requests
    from urllib.parse import quote
    # Telegram's hosted Bot API has its own size cap; no fake "unlimited" claim.
    file = bot.get_file(file_id)
    size = int(getattr(file, "file_size", 0) or 0)
    if size and size > min(limit, 20 * 1024 * 1024):
        raise BridgeError("Telegram Bot API download limit reached (20 MB).")
    path = getattr(file, "file_path", "")
    if not path or path.startswith("/") or ".." in path.split("/") or "?" in path:
        raise BridgeError("Unexpected Telegram file path.")
    token = os.getenv("BOT_TOKEN", "")
    if not token:
        raise RuntimeError("Telegram Bot API is not configured.")
    url = "https://api.telegram.org/file/bot" + token + "/" + quote(path, safe="/")
    response = requests.get(url, stream=True, timeout=(8, 60), allow_redirects=False)
    try:
        if response.status_code != 200:
            raise BridgeError("Telegram file download failed.")
        total = 0
        for block in response.iter_content(1024 * 1024):
            cancel()
            if not block:
                continue
            total += len(block)
            if total > min(limit, 20 * 1024 * 1024):
                raise BridgeError("Telegram file exceeds Bot API limit.")
            handle.write(block)
        return total
    finally:
        response.close()


def execute_job(row, bot, db=None):
    db = db or database()
    from cloudbridge_v136_large import enabled as large_enabled, transfer as large_transfer
    if (large_enabled() and row.get("destination_kind") == "provider"
            and row.get("destination_provider") == "google"
            and (row.get("source_kind") == "url" or
                 (row.get("source_kind") == "provider" and row.get("source_provider") == "google"))):
        large_transfer(row, bot, db, maximum=max_bytes())
        return
    stage = "download"
    try:
        uid = int(row["user_id"])
        if uid <= 0:
            raise BridgeError("Invalid account.")
        cancel = lambda: _cancel_check(row, db)
        cancel()
        # Old transport needs disk; never let the V13.6 4-GiB setting make
        # legacy Telegram/other-provider staging allocate a 4-GiB file.
        legacy_limit = min(max_bytes(), 1024 * 1024 * 1024)
        if row.get("destination_kind") == "telegram":
            # Reject large Telegram deliveries during download, rather than
            # filling temporary storage and rejecting only at upload.
            legacy_limit = min(legacy_limit, 49 * 1024 * 1024)
        with tempfile.TemporaryFile() as handle:
            kind = row["source_kind"]
            if kind == "telegram":
                length = _download_telegram(row["source_ref"], handle, legacy_limit, bot, cancel)
            elif kind == "provider":
                length = download_provider(uid, row["source_provider"], row["source_ref"],
                                           handle, legacy_limit, db, cancel)
            elif kind == "url":
                length = download_https(row["source_ref"], handle, legacy_limit, cancel)
            else:
                raise BridgeError("Unsupported source.")
            if length <= 0:
                raise BridgeError("Empty file was not transferred.")
            _set_state(row, db, bytes_done=length)
            cancel()
            stage = "upload"
            handle.seek(0)
            if row["destination_kind"] == "provider":
                upload_provider(uid, row["destination_provider"], row["destination_path"],
                                row["filename"], handle, length, db, cancel)
            elif row["destination_kind"] == "telegram":
                if length > 49 * 1024 * 1024:
                    raise BridgeError("Telegram Bot API send limit exceeded (49 MB safety cap).")
                bot.send_document(uid, handle, visible_file_name=row["filename"],
                                  caption="✅ File delivered by Student Assistant CloudBridge")
            else:
                raise BridgeError("Unsupported destination.")
            # Never remove a successful file after a late cancellation: record
            # completion honestly and let user manage the remote copy.
            _set_state(row, db, status="completed", error_code=None, bytes_done=length)
    except Cancelled:
        _set_state(row, db, status="cancelled" if stage == "download" else "needs_review",
                   error_code="cancelled_during_" + stage)
    except BridgeError as exc:
        # Download stage has no remote side effects, so retry is safe.
        _set_state(row, db, status="failed" if stage == "download" else "needs_review",
                   error_code=str(exc)[:180])
    except Exception:
        # Never write exception repr: it may include access tokens / URLs.
        LOGGER.warning("CloudBridge transfer failed, stage=%s", stage)
        _set_state(row, db, status="failed" if stage == "download" else "needs_review",
                   error_code="transfer_error_" + stage)


def run_once(bot, db=None):
    db = db or database()
    claim = db.rpc("cloudbridge_claim_job_v134", {"p_worker": str(uuid.uuid4())}).execute().data
    row = claim[0] if isinstance(claim, list) and claim else claim if isinstance(claim, dict) else None
    if not row:
        return False
    execute_job(row, bot, db=db)
    return True


def worker_loop(bot, stop=None, db_factory=database):
    while stop is None or not stop.is_set():
        try:
            if run_once(bot, db=db_factory()):
                continue
        except Exception:
            LOGGER.warning("CloudBridge worker unavailable; waiting for database/connection recovery")
        if stop is None:
            time.sleep(5)
        else:
            stop.wait(5)


def start_worker(bot):
    global _worker_started
    if os.getenv("CLOUDBRIDGE_WORKER_ENABLED", "false").lower() not in {"true", "yes", "1"}:
        return False
    if _worker_started:
        return True
    _worker_started = True
    threading.Thread(target=worker_loop, args=(bot,), daemon=True,
                     name="CloudBridge-V134").start()
    return True
