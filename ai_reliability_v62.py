"""Student Assistant V6.2: privacy-preserving, passive Cloudflare health signals.

Purely an observer: no extra requests, retries, Telegram handlers, model switching,
student identifiers, prompts or response contents. Data live only in this process.
The Gemini key and Google API are never used here.
"""
from __future__ import annotations

from collections import Counter, deque
from datetime import datetime, timezone
from functools import wraps
import os
import threading
import time
from typing import Callable

_WINDOW_SECONDS = 15 * 60
_MAX_EVENTS = 300
_LOCK = threading.RLock()
# Each tuple: monotonic timestamp, kind, outcome, category, duration milliseconds, brief answer
_EVENTS: deque[tuple[float, str, str, str, int, bool]] = deque(maxlen=_MAX_EVENTS)
_ALLOWED_KINDS = {"generation", "safety", "other_cloudflare"}
_ALLOWED_ERRORS = {"auth", "config", "rate_limit", "timeout", "network",
                   "invalid_response", "empty_response", "safety_context_missing",
                   "safety_unknown", "unavailable", "http_400", "http_401",
                   "http_403", "http_404", "http_429", "http_500",
                   "http_502", "http_503", "http_504"}


def _kind(model: object) -> str:
    if model == "@cf/qwen/qwen3-30b-a3b-fp8":
        return "generation"
    if model == "@cf/meta/llama-guard-3-8b":
        return "safety"
    return "other_cloudflare"


def _category(error: BaseException) -> str:
    # Error text is never inspected, retained, logged, or presented.
    code = getattr(error, "code", "unavailable")
    return code if isinstance(code, str) and code in _ALLOWED_ERRORS else "other_error"


def _purge(now: float) -> None:
    while _EVENTS and now - _EVENTS[0][0] > _WINDOW_SECONDS:
        _EVENTS.popleft()


def record_event(kind: str, outcome: str, category: str = "none",
                 duration_ms: int = 0, brief: bool = False, *, at: float | None = None) -> None:
    """Record only bounded aggregate metadata. at= aids deterministic offline tests."""
    now = time.monotonic() if at is None else float(at)
    safe_kind = kind if kind in _ALLOWED_KINDS else "other_cloudflare"
    safe_outcome = outcome if outcome in {"ok", "error"} else "error"
    safe_code = (category if category in _ALLOWED_ERRORS else "other_error") if safe_outcome == "error" else "none"
    try:
        safe_duration = max(0, min(300_000, int(duration_ms)))
    except (ValueError, TypeError, OverflowError):
        safe_duration = 0
    with _LOCK:
        _purge(now)
        _EVENTS.append((now, safe_kind, safe_outcome, safe_code, safe_duration, bool(brief)))


def observe_cloudflare_health(provider: Callable) -> Callable:
    """Wrap a synchronous provider transparently without changing return/exceptions."""
    if getattr(provider, "_v62_health_wrapped", False):
        return provider

    @wraps(provider)
    def observed(model, messages, max_tokens):
        kind = _kind(model)
        started = time.perf_counter()
        try:
            result = provider(model, messages, max_tokens)
        except BaseException as exc:
            # Recording cannot prevent re-raising original provider exceptions.
            try:
                record_event(kind, "error", _category(exc),
                             int((time.perf_counter() - started) * 1000))
            except Exception:
                pass
            raise
        else:
            try:
                record_event(kind, "ok", duration_ms=int((time.perf_counter() - started) * 1000),
                             brief=kind == "generation" and isinstance(result, str)
                             and len(result.strip()) < 45)
            except Exception:
                pass
            return result

    observed._v62_health_wrapped = True
    return observed


def recent_snapshot(now: float | None = None) -> dict:
    """Rolling view of last 15 minutes / up to 300 completed Cloudflare calls."""
    current = time.monotonic() if now is None else float(now)
    with _LOCK:
        _purge(current)
        rows = tuple(_EVENTS)
    generation = [row for row in rows if row[1] == "generation"]
    moderation = [row for row in rows if row[1] == "safety"]
    errors = Counter(row[3] for row in rows if row[2] == "error")
    good = sum(row[2] == "ok" for row in generation)
    bad = len(generation) - good
    latencies = sorted(row[4] for row in generation if row[2] == "ok")
    p95 = latencies[max(0, (95 * len(latencies) + 99) // 100 - 1)] if latencies else None
    return {
        "window_minutes": 15,
        "max_samples": _MAX_EVENTS,
        "generation_ok": good,
        "generation_failed": bad,
        "safety_ok": sum(row[2] == "ok" for row in moderation),
        "safety_failed": sum(row[2] == "error" for row in moderation),
        "other_calls": len(rows) - len(generation) - len(moderation),
        "errors": dict(sorted(errors.items())),
        "brief_generation_answers": sum(row[5] and row[2] == "ok" for row in generation),
        "p95_generation_ms": p95,
        "sample_truncated": len(rows) == _MAX_EVENTS,
    }


def _status(s: dict, configured: bool) -> tuple[str, str]:
    """Conservative: observational status only, not an external availability probe."""
    if not configured:
        return "CONFIG MISSING", "Check CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN in Render."
    gen_total = s["generation_ok"] + s["generation_failed"]
    if not gen_total and not (s["safety_ok"] or s["safety_failed"]):
        return "NO RECENT CALLS", "Use /ai to test normally; this is not a live provider probe."
    if s["errors"].get("auth") or s["errors"].get("http_401") or s["errors"].get("http_403"):
        return "ACTION NEEDED", "Check Cloudflare credentials and permissions."
    if s["errors"].get("rate_limit") or s["errors"].get("http_429"):
        return "RATE LIMITED", "A 429 was observed; wait or inspect Cloudflare quotas."
    if s["safety_failed"]:
        return "SAFETY CHECK ERRORS", "Check Cloudflare moderation; no bypass/fallback enabled."
    if gen_total >= 5 and s["generation_failed"] / gen_total >= 0.4:
        return "ELEVATED FAILURES", "Inspect Render logs and Cloudflare connectivity."
    if gen_total and s["generation_failed"]:
        return "SOME FAILURES", "Review recent error categories below."
    if gen_total and s["generation_ok"]:
        return "RECENT CALLS OK", "Successful model calls observed; this does not certify answer accuracy."
    return "NO RECENT GENERATION", "Only safety calls were observed in this process."


def format_health_report() -> str:
    """For V6.0 admin allowlist ONLY; never attach as a public command."""
    snap = recent_snapshot()
    configured = bool(os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
                      and os.getenv("CLOUDFLARE_API_TOKEN", "").strip())
    status, guidance = _status(snap, configured)
    limit_raw = os.getenv("AI_DAILY_LIMIT", "8")
    try:
        daily = min(30, max(1, int(limit_raw)))
    except (ValueError, TypeError):
        daily = 8
    rows = [
        "🩺 Student Assistant — AI Reliability V6.2",
        f"Cloudflare (passive): {status}",
        f"Advice: {guidance}",
        "Window: last 15 minutes, current Render process only",
        f"Generation: {snap['generation_ok']} OK / {snap['generation_failed']} failed",
        f"Llama Guard safety: {snap['safety_ok']} OK / {snap['safety_failed']} failed",
        f"Generation p95 latency: {snap['p95_generation_ms']} ms" if snap['p95_generation_ms'] is not None
            else "Generation p95 latency: insufficient successful calls",
        f"Brief AI answers (<45 chars): {snap['brief_generation_answers']} (length only, not a quality score)",
        f"Bot daily limit: {daily} requests per student (configuration, not remaining provider quota)",
        "Provider remaining RPM/RPD/tokens: unknown (no billing/quota API queried)",
        "Gemini: developer-only; not used for student requests",
        "No automatic retries, provider fallback, or extra API calls.",
    ]
    if snap["errors"]:
        rows.append("Recent failure categories:")
        rows.extend(f"• {category}: {count}" for category, count in snap["errors"].items())
    if snap["sample_truncated"]:
        rows.append("Only the newest 300 calls are represented.")
    rows.append("Counters clear at restart; different Render workers have separate counters.")
    return "\n".join(rows)[:3700]


def main() -> int:
    print(format_health_report())
    print("Local report only; this CLI does not contact Cloudflare or Gemini.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
