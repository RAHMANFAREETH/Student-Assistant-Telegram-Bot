"""Student Assistant V6.0: private AI operations and safe, process-local metrics.

No secrets, user IDs, questions, generated answers, IP addresses, or student data
are collected. No Gemini calls and no routing of Telegram traffic to Gemini.
Metrics reset on each worker restart and are NOT a billing/quota source.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from functools import wraps
import importlib.util
import os
from threading import RLock
from time import monotonic, perf_counter

_STARTED_UTC = datetime.now(timezone.utc)
_STARTED_MONOTONIC = monotonic()
_LOCK = RLock()
_COUNTERS = Counter()
_ERROR_COUNTS = Counter()
_TOTAL_LATENCY_MS = Counter()
_SHORT_ANSWERS = 0


# Only selected code categories are recorded; exception text is discarded.
KNOWN_ERRORS = frozenset({
    "auth", "config", "rate_limit", "timeout", "network", "invalid_response",
    "empty_response", "safety_context_missing", "safety_unknown",
    "unavailable", "http_400", "http_401", "http_403", "http_404",
    "http_429", "http_500", "http_502", "http_503", "http_504",
})


def _yes(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"true", "yes", "1", "on"}


def admin_ids() -> frozenset[int]:
    """Separate admin allowlist; NEVER inherit AI_ALLOWED_USER_IDS."""
    raw = os.getenv("AI_OPS_ADMIN_IDS", "")
    return frozenset(int(part.strip()) for part in raw.split(",")
                     if part.strip().isascii() and part.strip().isdigit()
                     and int(part.strip()) > 0)


def classify_model(model: object) -> str:
    """Never retain arbitrary provider model names as metric keys."""
    value = str(model)
    if value == "@cf/meta/llama-guard-3-8b":
        return "safety"
    if value == "@cf/qwen/qwen3-30b-a3b-fp8":
        return "generation"
    return "other_cloudflare"


def record_cloudflare_result(kind: str, *, elapsed_ms: int,
                             error_code: str | None = None, answer_short: bool = False) -> None:
    """Aggregate only. No prompts, responses, identifiers, or exception bodies."""
    global _SHORT_ANSWERS
    if kind not in {"safety", "generation", "other_cloudflare"}:
        kind = "other_cloudflare"
    outcome = "failure" if error_code else "success"
    code = error_code if error_code in KNOWN_ERRORS else "other_error"
    with _LOCK:
        _COUNTERS[(kind, outcome)] += 1
        _TOTAL_LATENCY_MS[kind] += max(0, min(int(elapsed_ms), 300_000))
        if error_code:
            _ERROR_COUNTS[(kind, code)] += 1
        if kind == "generation" and not error_code and answer_short:
            _SHORT_ANSWERS += 1


def wrap_cloudflare_provider(provider):
    """Observe existing call without changing arguments, return values or exceptions."""
    if getattr(provider, "_v60_metrics_wrapped", False):
        return provider

    @wraps(provider)
    def observed(model, messages, max_tokens):
        kind = classify_model(model)
        started = perf_counter()
        try:
            response = provider(model, messages, max_tokens)
        except Exception as error:
            record_cloudflare_result(
                kind, elapsed_ms=int((perf_counter() - started) * 1000),
                error_code=getattr(error, "code", "other_error"),
            )
            raise
        else:
            record_cloudflare_result(
                kind, elapsed_ms=int((perf_counter() - started) * 1000),
                answer_short=(kind == "generation" and isinstance(response, str)
                              and 0 < len(response.strip()) < 45),
            )
            return response

    observed._v60_metrics_wrapped = True
    return observed


def metrics_snapshot() -> dict:
    """Immutable aggregate view: no user/message/secret fields."""
    with _LOCK:
        kinds = ("generation", "safety", "other_cloudflare")
        return {
            "started_utc": _STARTED_UTC.strftime("%Y-%m-%d %H:%M UTC"),
            "uptime_minutes": int((monotonic() - _STARTED_MONOTONIC) // 60),
            "providers": {
                name: {
                    "success": _COUNTERS[(name, "success")],
                    "failure": _COUNTERS[(name, "failure")],
                    "average_ms": (round(_TOTAL_LATENCY_MS[name] /
                                         max(1, _COUNTERS[(name, "success")] + _COUNTERS[(name, "failure")]))),
                } for name in kinds
            },
            "error_counts": {f"{kind}:{code}": count for (kind, code), count
                             in sorted(_ERROR_COUNTS.items())},
            "short_generation_answers": _SHORT_ANSWERS,
        }


def _recommendation(errors: dict) -> str:
    if any(key.endswith(":auth") or key.endswith(":http_401") or key.endswith(":http_403")
           for key in errors):
        return "Check Cloudflare API token permissions in Render (never share the token)."
    if any(key.endswith(":rate_limit") or key.endswith(":http_429") for key in errors):
        return "Check Workers AI rate limits/quota; do not auto-switch students to Gemini."
    if any(key.endswith(":timeout") or key.endswith(":network") for key in errors):
        return "Check provider connectivity and Render logs (without private messages)."
    if any(key.startswith("safety:") for key in errors):
        return "Review Cloudflare Llama Guard availability and moderation request formatting."
    return "No action indicated by these aggregate counters."


def format_report() -> str:
    s = metrics_snapshot()
    cloudflare_status = "configured" if (
        os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip() and
        os.getenv("CLOUDFLARE_API_TOKEN", "").strip()) else "missing configuration"
    enabled = "yes" if _yes("AI_ENABLED") else "no"
    public = "yes" if _yes("AI_ALLOW_PUBLIC") else "no"
    gemini_installed = importlib.util.find_spec("gemini_ai_studio_v59") is not None
    rows = [
        "🛠 Student Assistant — AI Operations V6.0",
        f"Cloudflare: {cloudflare_status}; AI enabled: {enabled}; public AI: {public}",
        "Gemini: developer-only client installed" if gemini_installed
            else "Gemini: developer-only client not found",
        "Gemini Telegram routing: DISABLED (mixed-age bot)",
        "",
        f"📊 This Render/Python process only — since {s['started_utc']}",
        f"Uptime: {s['uptime_minutes']} minutes",
    ]
    for name, info in s["providers"].items():
        rows.append(f"• {name}: {info['success']} OK / {info['failure']} failed; "
                    f"mean {info['average_ms']} ms")
    rows.append(f"• Brief generation answers (<45 chars): {s['short_generation_answers']}")
    if s["error_counts"]:
        rows.append("Error categories (no private data):")
        for code, count in sorted(s["error_counts"].items())[:12]:
            rows.append(f"• {code} × {count}")
        rows.append("Advice: " + _recommendation(s["error_counts"]))
    rows.extend([
        "", "Note: these count Cloudflare model calls, including safety checks, "
        "not unique questions, users, or billed tokens.",
        "Metrics reset on restart and differ across multiple workers.",
        "Student daily request count: /aistats (existing feature).",
    ])
    return "\n".join(rows)[:3800]


def register_ai_ops_v60_handlers(bot):
    """Install admin-only, private-chat command; no public menu button."""

    @bot.message_handler(commands=["aiops", "aiproviders"])
    def aiops_command(message):
        chat = getattr(message, "chat", None)
        sender = getattr(message, "from_user", None)
        if getattr(chat, "type", "") != "private":
            bot.send_message(chat.id, "🔒 AI diagnostics are available only in a private chat.")
            return
        if sender is None or int(getattr(sender, "id", 0)) not in admin_ids():
            bot.send_message(chat.id, "🔒 Admin diagnostics are not enabled for this account.")
            return
        bot.send_message(chat.id, format_report())

    return {"admin_command": aiops_command}
