"""V5.9: Developer-only Gemini AI Studio client.

This module deliberately does not register Telegram handlers or read Supabase.
Do not route messages from the existing mixed-age public bot through this client.
Google's Gemini API terms restrict API clients likely accessed by under-18 users.

Requires only Python's standard library. Do not print/commit API secrets.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

MODEL = "gemini-3.1-flash-lite"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
MAX_INPUT = 5000
MAX_OUTPUT = 7000
DEFAULT_TIMEOUT = 35

TASKS = {
    "ask": "Answer this study question accurately and clearly. If unsure, say so.",
    "explain": "Explain this topic to an adult university-level learner, with a short example.",
    "maths": "Help solve this maths problem with clear, verifiable steps; check the result.",
    "quiz": "Create 3 practice questions and a clearly marked answer key on the topic.",
    "language": "Explain this language-learning question, including an example when useful.",
}
LANGUAGES = {
    "english": "English",
    "tamil": "Tamil",
    "sinhala": "Sinhala",
    "arabic": "Arabic",
}


class GeminiClientError(RuntimeError):
    """Sanitized service error with no key or potentially private response body."""


def build_payload(question: str, task: str = "ask", language: str = "english") -> dict[str, Any]:
    if not isinstance(question, str):
        raise ValueError("Study question must be a string.")
    question = question.strip()
    if not question:
        raise ValueError("Enter a study question.")
    if len(question) > MAX_INPUT:
        raise ValueError(f"Question is too long (maximum {MAX_INPUT} characters).")
    if task not in TASKS:
        raise ValueError("Unknown task. Choose: " + ", ".join(TASKS))
    if language not in LANGUAGES:
        raise ValueError("Unknown language. Choose: " + ", ".join(LANGUAGES))
    system_text = (
        "You are an educational assistant for an adult developer's private API test. "
        "Respond in " + LANGUAGES[language] + ". "
        + TASKS[task]
        + " Do not invent references. Keep answers concise and accessible."
    )
    return {
        "systemInstruction": {"parts": [{"text": system_text}]},
        "contents": [{"role": "user", "parts": [{"text": question}]}],
        "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.4},
    }


def extract_text(payload: Any) -> str:
    """Use candidate text only; never reveal reasoning or raw errors."""
    if not isinstance(payload, dict):
        raise GeminiClientError("Gemini returned an unexpected response.")
    candidates = payload.get("candidates") or []
    if not isinstance(candidates, list) or not candidates:
        raise GeminiClientError("Gemini returned no answer. The request may have been filtered.")
    candidate = candidates[0] if isinstance(candidates[0], dict) else {}
    content = candidate.get("content") or {}
    parts = content.get("parts", []) if isinstance(content, dict) else []
    if not isinstance(parts, list):
        parts = []
    chunks = [p.get("text", "") for p in parts if isinstance(p, dict) and isinstance(p.get("text"), str)]
    answer = "\n".join(s.strip() for s in chunks if s.strip()).strip()
    if not answer:
        raise GeminiClientError("Gemini returned no text. Try another sample prompt.")
    return answer[:MAX_OUTPUT]


def read_api_key() -> str:
    """Return configured key without printing it; CLI can prompt when unset."""
    return (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()


class GeminiClient:
    def __init__(self, api_key: str, *, timeout: int = DEFAULT_TIMEOUT):
        self._api_key = (api_key or "").strip()
        if not self._api_key:
            raise ValueError("Gemini API key is missing.")
        if "\r" in self._api_key or "\n" in self._api_key:
            raise ValueError("API key contains invalid whitespace.")
        if not 1 <= timeout <= 120:
            raise ValueError("Timeout must be between 1 and 120 seconds.")
        self.timeout = timeout

    def generate(self, question: str, *, task: str = "ask", language: str = "english") -> str:
        payload = build_payload(question, task=task, language=language)
        request = urllib.request.Request(
            API_URL,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "x-goog-api-key": self._api_key,
                "User-Agent": "StudentAssistantBot-V5.9-Developer-Test",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(250_000)  # bounded response size
        except urllib.error.HTTPError as exc:
            code = exc.code
            if code in (401, 403):
                detail = "Authentication or API permissions failed. Check your AI Studio key and access."
            elif code == 404:
                detail = "Model not found or unavailable for this API key."
            elif code == 429:
                detail = "Rate limit or quota reached. Check AI Studio usage and try later."
            elif code == 400:
                detail = "Gemini rejected the request (HTTP 400). Check your model access."
            elif 500 <= code < 600:
                detail = "Google AI service is temporarily unavailable."
            else:
                detail = f"Gemini request failed (HTTP {code})."
            raise GeminiClientError(detail) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise GeminiClientError("Gemini connection failed or timed out. Check your connection.") from None
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise GeminiClientError("Gemini returned a response that could not be decoded.") from None
        return extract_text(decoded)
