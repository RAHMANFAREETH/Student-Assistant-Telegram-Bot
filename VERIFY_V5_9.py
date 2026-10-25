"""Non-mutating V5.9 check. It never edits your Telegram bot code."""
from pathlib import Path
import sys


def main() -> int:
    root = Path.cwd()
    required = ("main.py", "navigation.py", "ai_study_assistant.py", "ui_v57.py", "achievements_v58.py", "gemini_ai_studio_v59.py", "GEMINI_V5_9_DEV_TEST.py")
    missing = [n for n in required if not (root / n).is_file()]
    if missing:
        print("Missing in current folder:", ", ".join(missing))
        print("Open your existing StudentAssistantBot project and copy the V5.9 files there.")
        return 1
    if not (root / "study_context_ai.py").is_file():
        print("WARNING: V5.6 study_context_ai.py is missing. Check your prior upgrades.")
    print("PASS — existing bot modules and V5.9 developer tester are present.")
    print("Nothing was installed into main.py, navigation.py, Render, or Telegram.")
    print("Next: python GEMINI_V5_9_DEV_TEST.py --dry-run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
