"""V6.1 Gemini diagnostics for the bot developer (not a Telegram feature).

Only the explicit CLI --live option sends one fixed, non-student prompt.
No Telegram handler, Flask route, startup hook or Cloudflare fallback is added.
The Google API key is read from Render's GEMINI_API_KEY variable, never printed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from gemini_ai_studio_v59 import API_URL, MODEL

_PROBE_TEXT = "In one short sentence, what is 2 plus 2?"
_TIMEOUT_SECONDS = 25
_MAX_RESPONSE_BYTES = 80_000


@dataclass(frozen=True)
class ProbeResult:
    status: str
    detail: str
    prompt_tokens: int | None = None
    response_tokens: int | None = None
    total_tokens: int | None = None


def config_status() -> dict[str, Any]:
    """Configuration metadata only, suitable for admin diagnostics."""
    return {
        "gemini_env": bool(os.environ.get("GEMINI_API_KEY", "").strip()),
        "model": MODEL,
        "telegram_routing": False,
        "api_connectivity": "not tested",  # never claim online simply from key presence
    }


def _quota_seconds(value: Any) -> int | None:
    """Parse numeric Retry-After seconds only. Ignore dates/arbitrary strings."""
    if isinstance(value, str) and value.strip().isascii() and value.strip().isdigit():
        n = int(value.strip())
        return n if 0 <= n <= 86_400 else None
    return None


def _non_negative_int(data: Any, field: str) -> int | None:
    value = data.get(field) if isinstance(data, dict) else None
    return value if type(value) is int and 0 <= value < 10**9 else None


def _status_error(code: int, retry_after: Any = None) -> ProbeResult:
    categories = {
        400: ("bad_request", "Google rejected the diagnostic request (HTTP 400)."),
        401: ("authentication", "Gemini API authentication failed (HTTP 401)."),
        403: ("permission", "Gemini API key or project permissions denied (HTTP 403)."),
        404: ("model_unavailable", "Gemini model unavailable for this key (HTTP 404)."),
        429: ("quota", "Gemini rate limit or quota reached (HTTP 429)."),
    }
    status, detail = categories.get(code, (
        "service_error" if code >= 500 else "http_error",
        f"Gemini service returned HTTP {code}.",
    ))
    # Retry-After is a hint for this one attempt, NOT a quota counter.
    delay = _quota_seconds(retry_after)
    if code == 429 and delay is not None:
        detail += f" Retry-After: {delay}s (server hint)."
    return ProbeResult(status, detail)


def _bounded_json(response: Any) -> Any:
    data = response.read(_MAX_RESPONSE_BYTES + 1)
    if len(data) > _MAX_RESPONSE_BYTES:
        raise ValueError("oversized response")
    return json.loads(data.decode("utf-8"))


def probe_once(api_key: str) -> ProbeResult:
    """Call Gemini exactly once with a fixed test question, not student content.

    No secrets, raw API errors, generated text, or request bodies are logged.
    The URL contains no API key. No retries, no quotas inferred from 1 call.
    """
    key = (api_key or "").strip()
    if not key or "\r" in key or "\n" in key:
        return ProbeResult("not_configured", "GEMINI_API_KEY is missing or invalid.")

    payload = {"contents": [{"role": "user", "parts": [{"text": _PROBE_TEXT}]}],
               "generationConfig": {"maxOutputTokens": 80, "temperature": 0}}
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key,
                 "User-Agent": "StudentAssistantBot-V6.1-Private-Render-Diagnostic"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            data = _bounded_json(resp)
    except urllib.error.HTTPError as error:
        headers = getattr(error, "headers", None)
        retry = headers.get("Retry-After") if headers is not None else None
        return _status_error(error.code, retry)
    except (urllib.error.URLError, TimeoutError, OSError):
        return ProbeResult("network", "Gemini connection failed or timed out from this environment.")
    except (ValueError, UnicodeError, TypeError, OverflowError):
        return ProbeResult("invalid_response", "Gemini response could not be decoded safely.")

    if not isinstance(data, dict):
        return ProbeResult("invalid_response", "Gemini response was not an object.")
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ProbeResult("no_answer", "Gemini returned no candidates (possibly filtered).")
    first = candidates[0] if isinstance(candidates[0], dict) else {}
    content = first.get("content") if isinstance(first.get("content"), dict) else {}
    parts = content.get("parts") if isinstance(content.get("parts"), list) else []
    has_text = any(isinstance(p, dict) and isinstance(p.get("text"), str)
                   and bool(p["text"].strip()) for p in parts)
    if not has_text:
        return ProbeResult("no_answer", "Gemini returned no text (possibly filtered).")

    usage = data.get("usageMetadata") if isinstance(data.get("usageMetadata"), dict) else {}
    return ProbeResult(
        "ok", "Gemini answered the fixed developer test request.",
        _non_negative_int(usage, "promptTokenCount"),
        _non_negative_int(usage, "candidatesTokenCount"),
        _non_negative_int(usage, "totalTokenCount"),
    )


def admin_line() -> str:
    """Rendered in private /aiops admin report. No network traffic."""
    state = "configured" if config_status()["gemini_env"] else "not configured"
    return f"Gemini API key on Render: {state}; connectivity: not tested by /aiops"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V6.1 private Render Gemini diagnostic; no Telegram traffic")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Inspect environment only (default, no network)")
    mode.add_argument("--live", action="store_true", help="Explicitly send one private sample request to Gemini")
    args = parser.parse_args(argv)
    status = config_status()
    print("V6.1 private Gemini Render diagnostic")
    print("Model:", status["model"])
    print("GEMINI_API_KEY:", "configured" if status["gemini_env"] else "missing")
    print("Telegram Gemini routing: disabled (Cloudflare remains public provider)")
    if not args.live:
        print("No API request sent; connectivity not verified.")
        return 0 if status["gemini_env"] else 2

    if not status["gemini_env"]:
        print("ERROR: GEMINI_API_KEY missing in this process; check Render Environment.")
        return 2
    result = probe_once(os.environ.get("GEMINI_API_KEY", ""))
    print("Live probe status:", result.status)
    print("Detail:", result.detail)
    if result.status == "ok":
        counts = (result.prompt_tokens, result.response_tokens, result.total_tokens)
        if any(v is not None for v in counts):
            print("This diagnostic call's token usage (prompt/output/total):",
                  "/".join(str(v) if v is not None else "n/a" for v in counts))
        print("This does not reveal remaining RPM/RPD quota or verify student access.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
