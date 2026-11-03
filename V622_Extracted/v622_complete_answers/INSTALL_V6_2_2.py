"""V6.2.2: improve Cloudflare answer completeness in the existing Student Assistant Bot.

Only changes two text passages inside ai_study_assistant.py. Never changes Gemini,
moderation, quota accounting, monitoring, routing, or Telegram handlers.
"""
from __future__ import annotations

import ast
from pathlib import Path
import shutil
import sys

NAME = 'ai_study_assistant.py'
OLD_LIMIT = 'MAX_OUTPUT_TOKENS = 650'
NEW_LIMIT = 'MAX_OUTPUT_TOKENS = 1800'
MARKER = '# V6.2.2: allow complete multilingual study explanations without extra requests'
OLD_PROMPT = '"Respond in the student\'s language (Tamil, Sinhala, English, or Arabic), unless they request another. "'
NEW_PROMPT = (OLD_PROMPT + '\n'
              '        "Write clear Telegram-friendly plain text without Markdown symbols such as ### or **. "\n'
              '        "For numbered examples, keep each example brief and finish every requested item. "')


def patch_ai(source: str) -> tuple[str, bool]:
    """Return modified source and whether it changed. Fail closed on unfamiliar sources."""
    ast.parse(source, filename=NAME)
    eol = '\r\n' if '\r\n' in source else '\n'
    if MARKER in source:
        if (source.count(MARKER) != 1 or source.count(NEW_LIMIT) != 1
                or NEW_PROMPT.replace('\n', eol) not in source):
            raise ValueError('Incomplete V6.2.2 patch detected; inspect manually')
        return source, False
    if source.count(OLD_LIMIT) != 1 or source.count(OLD_PROMPT) != 1:
        raise ValueError('Expected V6.2 Cloudflare settings not found; no changes made')
    if (source.count('def _provider_call(') != 1
            or '_provider_call = observe_cloudflare_health(_provider_call)' not in source
            or '_provider_call = wrap_cloudflare_provider(_provider_call)' not in source
            or 'GUARD_MODEL = ' not in source
            or 'def _check_safety(' not in source
            or 'split_telegram_text(answer, limit=3500)' not in source):
        raise ValueError('Expected V6.2 provider, moderation, and Telegram handlers not found')

    # Record migration immediately above the single limit declaration.
    updated = source.replace(OLD_LIMIT, MARKER + eol + NEW_LIMIT, 1)
    updated = updated.replace(OLD_PROMPT, NEW_PROMPT.replace('\n', eol), 1)
    ast.parse(updated, filename=NAME)
    return updated, True


def run(root: Path = Path('.')) -> bool:
    target = Path(root) / NAME
    if not target.is_file():
        raise ValueError('Missing ai_study_assistant.py')
    with target.open('r', encoding='utf-8', newline='') as stream:
        source = stream.read()
    updated, changed = patch_ai(source)
    if not changed:
        return False
    backup = target.with_name(NAME + '.before_v622.bak')
    if backup.exists():
        raise ValueError(f'Backup {backup.name} already exists: refusing overwrite')
    shutil.copy2(target, backup)
    try:
        with target.open('w', encoding='utf-8', newline='') as stream:
            stream.write(updated)
    except OSError:
        shutil.copy2(backup, target)
        raise
    return True


if __name__ == '__main__':
    try:
        changed = run()
    except (ValueError, OSError, SyntaxError, UnicodeError) as exc:
        print('V6.2.2 installation stopped safely:', exc)
        sys.exit(1)
    print('V6.2.2 installed; backup created.' if changed
          else 'V6.2.2 already installed; no files changed.')
