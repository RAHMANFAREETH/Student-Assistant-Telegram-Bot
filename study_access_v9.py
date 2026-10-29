"""Server-only authorization for V8/V9 general adult access.

This module does NOT verify age. An approved operator or trusted age-verification
integration must write a verified + unexpired record to Supabase. Database access
must use the backend service key and must never expose that key to Telegram users.
"""
from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
import time

_lock = RLock()
_cache: dict[int, tuple[float, bool]] = {}
_CACHE_TTL_SECONDS = 15.0  # Short delay for revocations; do not use this as age proof.
_CACHE_MAX = 1500


def _is_future(value: str, now: datetime) -> bool:
    if not isinstance(value, str):
        return False
    try:
        expiry = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if expiry.tzinfo is None:
            return False
        return expiry.astimezone(timezone.utc) > now
    except ValueError:
        return False


def is_verified_adult(uid: int) -> bool:
    """True only for an active, unexpired record from a trusted verification flow.

    Fail closed on invalid IDs, missing schema, network errors, expired statuses.
    Uses server-side credentials via the existing db.supabase connection.
    """
    try:
        uid = int(uid)
    except (ValueError, TypeError, OverflowError):
        return False
    if uid <= 0:
        return False
    now_mono = time.monotonic()
    with _lock:
        cached = _cache.get(uid)
        if cached and cached[0] > now_mono:
            return cached[1]
    result = False
    try:
        from db import supabase
        data = (supabase.table('study_verified_adults')
                .select('user_id,status,verification_method,valid_until')
                .eq('user_id', uid)
                .eq('status', 'verified')
                .limit(1).execute()).data or []
        if (data and data[0].get('status') == 'verified'
                and data[0].get('verification_method') in ('trusted_provider', 'manual_review')
                and str(data[0].get('user_id')) == str(uid)):
            result = _is_future(data[0].get('valid_until'), datetime.now(timezone.utc))
    except Exception:
        result = False
    with _lock:
        if len(_cache) >= _CACHE_MAX:
            _cache.clear()
        _cache[uid] = (time.monotonic() + _CACHE_TTL_SECONDS, result)
    return result
