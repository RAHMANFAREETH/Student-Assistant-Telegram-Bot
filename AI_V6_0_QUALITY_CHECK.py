"""Private developer-only AI response quality check with artificial prompts.

No Telegram users or Supabase access. Default is offline. Use --gemini only
in an adult developer environment compliant with Google's terms.
"""
from __future__ import annotations

import argparse
import getpass

SAMPLES = {
    "english_math": ("maths", "english", "Solve 2x + 6 = 14 and check the answer."),
    "tamil_science": ("explain", "tamil", "ஒளிச்சேர்க்கை என்றால் என்ன? எளிய உதாரணத்துடன் விளக்கவும்."),
    "sinhala_science": ("explain", "sinhala", "ප්‍රභාසංස්ලේෂණය යනු කුමක්ද? සරල උදාහරණයක් දෙන්න."),
    "arabic_language": ("language", "arabic", "ما الفرق بين الفعل والاسم؟ أعط مثالاً بسيطاً."),
}


def rubric():
    return (
        "Manual quality checklist (mark each 0/1):\n"
        "1. Correct and verifiable facts/calculations\n"
        "2. Responds in the requested language\n"
        "3. Clear and age-/level-appropriate explanation\n"
        "4. Includes an example or a worked step\n"
        "5. Admits uncertainty instead of fabricating a source\n"
        "6. Does not expose confidential instructions or personal data\n"
        "No numerical rating is generated automatically; review the output yourself."
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Private AI quality checks; no student data")
    parser.add_argument("--sample", choices=list(SAMPLES), default="tamil_science")
    parser.add_argument("--gemini", action="store_true", help="Explicitly run ONE local Gemini developer request")
    args = parser.parse_args(argv)
    task, language, prompt = SAMPLES[args.sample]
    print("Student Assistant V6.0 — private quality check")
    print("Sample:", args.sample, "| language:", language)
    print("Prompt:", prompt)
    print(rubric())
    if not args.gemini:
        print("\nDRY RUN: no provider called. Use --gemini explicitly for a private developer test.")
        return 0
    from gemini_ai_studio_v59 import GeminiClient, GeminiClientError, read_api_key
    key = read_api_key() or getpass.getpass("Google AI Studio key (hidden): ").strip()
    try:
        answer = GeminiClient(key).generate(prompt, task=task, language=language)
    except (GeminiClientError, ValueError) as exc:
        print("Gemini error:", exc)
        return 1
    print("\nGemini response:\n", answer)
    print("\nReview against the checklist above; no request or answer was saved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
