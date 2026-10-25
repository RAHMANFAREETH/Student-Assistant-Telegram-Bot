"""V6.4: Student-initiated study shortcuts for the existing Cloudflare AI chat.

Patches only a known V6.3 ai_study_assistant.py layout. No Gemini
routing, provider, SQL, moderation, quota, or navigation changes.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
import shutil
import sys
import tempfile

TARGET = "ai_study_assistant.py"
MARKER = "# V6.4: turn the latest AI answer into study aids"

CONSTANT_ANCHOR = "V63_FOLLOW_UPS = {"
CONSTANTS = '''# V6.4: turn the latest AI answer into study aids
SUMMARY_BUTTON = "📝 Summarize Reply"
KEYPOINTS_BUTTON = "📌 Key Points"
PRACTICE_BUTTON = "🧠 Practice Quiz"
V64_STUDY_ACTIONS = {
    SUMMARY_BUTTON: (
        "Summarize only the most recent assistant answer excerpt available in our chat history "
        "in 4 or 5 short clear sentences. Use the same language as that answer, "
        "including Tamil, Sinhala, English, or Arabic. Do not invent any missing facts. "
        "If the excerpt is incomplete, briefly say the summary covers only the available excerpt. "
        "Finish with one takeaway sentence."
    ),
    KEYPOINTS_BUTTON: (
        "Extract up to five concise numbered key study points supported by the most recent "
        "assistant answer excerpt available in our chat history. Use the same language "
        "as the answer. Do not invent or add facts that the excerpt does not contain. "
        "If the excerpt is incomplete, say these are points from the available excerpt."
    ),
    PRACTICE_BUTTON: (
        "Create exactly three short multiple-choice practice questions based ONLY on the "
        "most recent assistant answer excerpt available in our chat history. "
        "For each question give four choices A, B, C, D. After all questions, "
        "provide an answer key with a one-sentence explanation for each answer. "
        "Match the answer's language. If the excerpt lacks enough factual detail, "
        "make fewer questions and say why rather than inventing answers."
    ),
}
'''

KEYBOARD_ANCHOR = '''    markup.add(types.KeyboardButton(EXAMPLES_BUTTON))
    markup.add(types.KeyboardButton("🏠 Main Menu"))'''
KEYBOARD_PATCH = '''    markup.add(types.KeyboardButton(EXAMPLES_BUTTON))
    markup.row(types.KeyboardButton(SUMMARY_BUTTON), types.KeyboardButton(KEYPOINTS_BUTTON))
    markup.add(types.KeyboardButton(PRACTICE_BUTTON))
    markup.add(types.KeyboardButton("🏠 Main Menu"))'''

HANDLER_ANCHOR = '''            text = V63_FOLLOW_UPS[text]
        if len(text) > MAX_INPUT_CHARS:'''
HANDLER_PATCH = '''            text = V63_FOLLOW_UPS[text]
        # V6.4 shortcuts require a previously completed answer in this student's session.
        if text in V64_STUDY_ACTIONS:
            history = session.get("history") or []
            if not history or history[-1].get("role") != "assistant":
                bot.send_message(message.chat.id,
                    "🤖 First ask a study question and get an answer, then use this study tool.")
                return
            text = V64_STUDY_ACTIONS[text]
        if len(text) > MAX_INPUT_CHARS:'''


def patch_ai(source: str) -> tuple[str, bool]:
    """Return patched code, whether changed. Refuse unfamiliar or partial versions."""
    ast.parse(source, filename=TARGET)
    eol = "\r\n" if "\r\n" in source else "\n"
    if MARKER in source:
        checks = (
            source.count(MARKER) == 1,
            source.count("V64_STUDY_ACTIONS = {") == 1,
            source.count("if text in V64_STUDY_ACTIONS:") == 1,
            source.count("types.KeyboardButton(SUMMARY_BUTTON)") == 1,
            source.count("types.KeyboardButton(KEYPOINTS_BUTTON)") == 1,
            source.count("types.KeyboardButton(PRACTICE_BUTTON)") == 1,
            source.count('text = V64_STUDY_ACTIONS[text]') == 1,
        )
        if not all(checks):
            raise ValueError("Incomplete V6.4 patch detected; no files changed")
        return source, False

    expected = (
        "# V6.3: student-controlled AI follow-up shortcuts",
        "# V6.2.2: allow complete multilingual study explanations without extra requests",
        "MAX_OUTPUT_TOKENS = 1800",
        '_provider_call = wrap_cloudflare_provider(_provider_call)',
        '_provider_call = observe_cloudflare_health(_provider_call)',
        'GUARD_MODEL = ',
        'def _check_safety(',
        'def _process_question(',
        'def register_ai_study_assistant_handlers(',
        'split_telegram_text(answer, limit=3500)',
        '"content": answer[-1800:]',
        'def claim_quota(',
        'if text in V63_FOLLOW_UPS:',
    )
    if any(fragment not in source for fragment in expected):
        raise ValueError("Expected V6.3 Cloudflare chat version not found; no files changed")

    anchors = (CONSTANT_ANCHOR, KEYBOARD_ANCHOR, HANDLER_ANCHOR)
    if any(source.count(a.replace("\n", eol)) != 1 for a in anchors):
        raise ValueError("Expected V6.3 buttons or handler differ; no files changed")

    updated = source.replace(CONSTANT_ANCHOR,
        CONSTANTS.replace("\n", eol) + CONSTANT_ANCHOR, 1)
    updated = updated.replace(KEYBOARD_ANCHOR.replace("\n", eol),
        KEYBOARD_PATCH.replace("\n", eol), 1)
    updated = updated.replace(HANDLER_ANCHOR.replace("\n", eol),
        HANDLER_PATCH.replace("\n", eol), 1)
    ast.parse(updated, filename=TARGET)
    return updated, True


def install(root: Path = Path(".")) -> bool:
    root = Path(root)
    target = root / TARGET
    if not target.is_file():
        raise ValueError(f"Missing {TARGET}; run this inside the existing StudentAssistantBot folder")
    with target.open("r", encoding="utf-8", newline="") as f:
        before = f.read()
    after, changed = patch_ai(before)
    if not changed:
        return False

    backup = root / (TARGET + ".before_v64.bak")
    if backup.exists():
        raise ValueError(f"{backup.name} already exists; refusing to overwrite backup")

    temp_path = None
    shutil.copy2(target, backup)
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="",
                                         dir=root, prefix=".v64_", suffix=".tmp",
                                         delete=False) as tmp:
            temp_path = Path(tmp.name)
            tmp.write(after)
        os.replace(temp_path, target)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        # Target is unchanged if os.replace did not succeed; backup always retained.
        raise
    return True


if __name__ == "__main__":
    try:
        changed = install()
    except (ValueError, OSError, SyntaxError, UnicodeError) as e:
        print("V6.4 safely stopped:", e)
        sys.exit(1)
    print("V6.4 installed; backup created." if changed
          else "V6.4 already installed; no files changed.")
