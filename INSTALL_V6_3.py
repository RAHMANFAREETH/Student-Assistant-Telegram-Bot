"""V6.3: student-initiated Cloudflare AI follow-up shortcuts.

Patches only the existing ai_study_assistant.py after V6.2.2.
No Telegram/Gemini routing changes, no new APIs, no SQL.
"""
from __future__ import annotations

import ast
from pathlib import Path
import shutil
import sys

TARGET = 'ai_study_assistant.py'
MARKER = '# V6.3: student-controlled AI follow-up shortcuts'

BUTTON_ANCHOR = 'BACK_BUTTON = "⬅️ AI Menu"'
BUTTON_PATCH = '''# V6.3: student-controlled AI follow-up shortcuts
CONTINUE_BUTTON = "➡️ Continue Answer"
SIMPLIFY_BUTTON = "🧩 Explain Simply"
EXAMPLES_BUTTON = "💡 More Examples"
V63_FOLLOW_UPS = {
    CONTINUE_BUTTON: (
        "Continue your previous answer immediately after its last part, without repeating it. "
        "First finish any incomplete sentence or numbered example, then finish the explanation. "
        "Use the same language and plain-text style. If the answer was already complete, "
        "say so briefly and give a one-sentence recap."
    ),
    SIMPLIFY_BUTTON: (
        "Explain the previous study topic again in much simpler terms for a beginner. "
        "Use short clear sentences, one everyday example, and a brief recap in the same language."
    ),
    EXAMPLES_BUTTON: (
        "Give three new, distinct, short examples of the topic we just discussed. "
        "Avoid repeating the prior examples. Explain each briefly in the same language."
    ),
}
'''
MARKUP_ANCHOR = '    markup.row(types.KeyboardButton(BACK_BUTTON), types.KeyboardButton(CLEAR_BUTTON))'
MARKUP_ADDITION = '''    markup.row(types.KeyboardButton(CONTINUE_BUTTON), types.KeyboardButton(SIMPLIFY_BUTTON))
    markup.add(types.KeyboardButton(EXAMPLES_BUTTON))'''

CHAT_ANCHOR = '''        if not text:
            return
        if len(text) > MAX_INPUT_CHARS:'''
CHAT_PATCH = '''        if not text:
            return
        # V6.3 quick actions are opt-in. The normal quota and safety path still runs.
        if text in V63_FOLLOW_UPS:
            history = session.get("history") or []
            if not history or history[-1].get("role") != "assistant":
                bot.send_message(message.chat.id,
                    "🤖 First ask a study question and get an answer, then use this shortcut.")
                return
            text = V63_FOLLOW_UPS[text]
        if len(text) > MAX_INPUT_CHARS:'''

MEMORY_ANCHOR = '            {"role": "assistant", "content": answer[:1800]},'
MEMORY_PATCH = '            {"role": "assistant", "content": answer[-1800:]},'


def patch_ai(source: str) -> tuple[str, bool]:
    """Fail closed on incompatible versions; retain original newline convention."""
    ast.parse(source, filename=TARGET)
    eol = '\r\n' if '\r\n' in source else '\n'
    if MARKER in source:
        checks = (
            source.count(MARKER) == 1,
            source.count('V63_FOLLOW_UPS = {') == 1,
            source.count('if text in V63_FOLLOW_UPS:') == 1,
            source.count('types.KeyboardButton(CONTINUE_BUTTON)') == 1,
            source.count(MEMORY_PATCH) == 1,
        )
        if not all(checks):
            raise ValueError('Partial V6.3 patch found; inspect file manually')
        return source, False

    checks = (
        '# V6.2.2: allow complete multilingual study explanations without extra requests' in source,
        'MAX_OUTPUT_TOKENS = 1800' in source,
        '_provider_call = observe_cloudflare_health(_provider_call)' in source,
        '_provider_call = wrap_cloudflare_provider(_provider_call)' in source,
        'GUARD_MODEL = ' in source,
        'def _check_safety(' in source,
        'def register_ai_study_assistant_handlers(' in source,
        'def _ai_chat_markup(' in source,
        'def _process_question(' in source,
        'split_telegram_text(answer, limit=3500)' in source,
    )
    if not all(checks):
        raise ValueError('Expected V6.2.2 Cloudflare AI code not found; no files changed')

    anchors = (BUTTON_ANCHOR, MARKUP_ANCHOR, CHAT_ANCHOR, MEMORY_ANCHOR)
    if any(source.count(a.replace('\n', eol)) != 1 for a in anchors):
        raise ValueError('Expected AI menu/handler layout not found; no files changed')

    changed = source.replace(BUTTON_ANCHOR,
        BUTTON_ANCHOR + eol + BUTTON_PATCH.replace('\n', eol).rstrip('\r\n'), 1)
    changed = changed.replace(MARKUP_ANCHOR,
        MARKUP_ANCHOR + eol + MARKUP_ADDITION.replace('\n', eol), 1)
    changed = changed.replace(CHAT_ANCHOR.replace('\n', eol),
        CHAT_PATCH.replace('\n', eol), 1)
    changed = changed.replace(MEMORY_ANCHOR, MEMORY_PATCH, 1)
    ast.parse(changed, filename=TARGET)
    return changed, True


def install(root: Path = Path('.')) -> bool:
    root = Path(root)
    target = root / TARGET
    if not target.is_file():
        raise ValueError(f'Missing {TARGET}; install into your existing bot project')
    with target.open('r', encoding='utf-8', newline='') as f:
        original = f.read()
    changed, needed = patch_ai(original)
    if not needed:
        return False
    backup = root / (TARGET + '.before_v63.bak')
    if backup.exists():
        raise ValueError(f'{backup.name} already exists; refusing overwrite')
    shutil.copy2(target, backup)
    try:
        with target.open('w', encoding='utf-8', newline='') as f:
            f.write(changed)
    except OSError:
        shutil.copy2(backup, target)
        raise
    return True


if __name__ == '__main__':
    try:
        done = install()
    except (ValueError, OSError, SyntaxError, UnicodeError) as error:
        print('V6.3 installation safely stopped:', error)
        sys.exit(1)
    print('V6.3 installed; backup created.' if done else 'V6.3 already installed; no changes made.')
