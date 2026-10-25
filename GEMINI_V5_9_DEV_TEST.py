"""Private, local Google AI Studio tester; NOT a Telegram bot feature.

Run: python GEMINI_V5_9_DEV_TEST.py --dry-run
     python GEMINI_V5_9_DEV_TEST.py --smoke
     python GEMINI_V5_9_DEV_TEST.py --task explain --language tamil
"""
from __future__ import annotations

import argparse
import getpass
import sys

from gemini_ai_studio_v59 import (
    API_URL,
    LANGUAGES,
    MODEL,
    TASKS,
    GeminiClient,
    GeminiClientError,
    build_payload,
    read_api_key,
)

SMOKE_QUESTION = "In one sentence, what is photosynthesis?"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Private Google AI Studio API test for adult developer; no Telegram handlers.")
    parser.add_argument("--dry-run", action="store_true", help="Validate local prompt formatting without network or credentials")
    parser.add_argument("--smoke", action="store_true", help="Send one harmless sample question to Gemini")
    parser.add_argument("--task", choices=list(TASKS), default="ask")
    parser.add_argument("--language", choices=list(LANGUAGES), default="english")
    args = parser.parse_args(argv)
    print("Student Assistant V5.9 — private Gemini developer tester")
    print("Model:", MODEL)
    print("Note: This does not connect Gemini to the public Telegram bot.")

    if args.dry_run:
        sample = build_payload(SMOKE_QUESTION, task=args.task, language=args.language)
        assert sample["contents"][0]["parts"][0]["text"] == SMOKE_QUESTION
        assert API_URL.startswith("https://generativelanguage.googleapis.com/")
        print("PASS — local payload and model URL validated; no API request sent.")
        return 0

    question = SMOKE_QUESTION if args.smoke else input("Your private test question (do not enter student data): ").strip()
    if not question:
        print("No question entered.")
        return 2
    key = read_api_key()
    if not key:
        try:
            key = getpass.getpass("Paste your Google AI Studio API key (hidden): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 2
    try:
        print("Sending one developer-only request...")
        response = GeminiClient(key).generate(question, task=args.task, language=args.language)
    except (ValueError, GeminiClientError) as exc:
        print("Error:", exc)
        return 1
    print("\nGemini response:\n" + response)
    print("\nSuccess — Google AI Studio API works from this computer. Public bot remains unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
