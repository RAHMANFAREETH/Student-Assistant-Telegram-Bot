"""Minimal V6.2.1 Qwen3 empty-response compatibility patch.

Only edits ai_study_assistant.py. Keeps V6.0/V6.2 observer hooks, student quotas,
Llama Guard and Gemini untouched. Creates non-overwriting UTF-8-safe backup.
"""
from __future__ import annotations
import ast
from pathlib import Path
import shutil
import sys

NAME = 'ai_study_assistant.py'
MARKER = '# V6.2.1 Qwen3 non-thinking request and safer blank-response fallback'
OLD_REQUEST = 'json={"messages": messages, "max_tokens": max_tokens},'
NEW_REQUEST = 'json=_v621_generation_payload(model, messages, max_tokens),'
OLD_FALLBACK = '            if output is None:\n                choices = result.get("choices") or []'
NEW_FALLBACK = '            if not isinstance(output, str) or not output.strip():\n                choices = result.get("choices") or []'
HELPER = '''\n\n''' + MARKER + '''
def _v621_generation_payload(model, messages, max_tokens):
    """Use Qwen3 non-thinking mode on generation calls only; no extra API calls.

    The /no_think text is a documented Qwen3 chat instruction. Llama Guard
    requests are passed unmodified. Caller-owned history is never mutated.
    """
    payload = {"messages": messages, "max_tokens": max_tokens}
    if model != CF_MODEL:
        return payload
    if not isinstance(messages, list) or not all(isinstance(msg, dict) for msg in messages):
        return payload
    copied = [dict(msg) for msg in messages]
    for msg in reversed(copied):
        if msg.get("role") == "user" and isinstance(msg.get("content"), str):
            msg["content"] += "\\n/no_think"
            payload["messages"] = copied
            break
    return payload
'''


def patch_ai(source: str) -> tuple[str, bool]:
    eol = "\r\n" if "\r\n" in source else "\n"
    if MARKER in source:
        if source.count(MARKER) != 1 or source.count(NEW_REQUEST) != 1 or NEW_FALLBACK.replace("\n", eol) not in source:
            raise ValueError('Partial V6.2.1 patch found; inspect manually')
        ast.parse(source, filename=NAME)
        return source, False
    old_fallback = OLD_FALLBACK.replace("\n", eol)
    new_fallback = NEW_FALLBACK.replace("\n", eol)
    if (source.count(OLD_REQUEST) != 1 or source.count(old_fallback) != 1
            or source.count('def _provider_call(') != 1
            or '_provider_call = observe_cloudflare_health(_provider_call)' not in source
            or '_provider_call = wrap_cloudflare_provider(_provider_call)' not in source
            or 'def _check_safety(' not in source):
        raise ValueError('This project does not match expected V6.2 AI source; nothing changed')
    # Insert helper ahead of provider, leaving the existing wrapper order intact.
    anchor = eol + 'def _provider_call('
    if source.count(anchor) != 1:
        raise ValueError('Cannot safely find _provider_call insertion point')
    result = source.replace(anchor, HELPER.replace("\n", eol) + anchor, 1)
    result = result.replace(OLD_REQUEST, NEW_REQUEST, 1)
    result = result.replace(old_fallback, new_fallback, 1)
    ast.parse(result, filename=NAME)
    return result, True


def run(root: Path = Path('.')) -> bool:
    root = Path(root)
    target = root / NAME
    if not target.exists():
        raise ValueError(f'Missing {NAME}')
    with target.open('r', encoding='utf-8', newline='') as f:
        source = f.read()
    changed, needed = patch_ai(source)
    if not needed:
        return False
    backup = root / (NAME + '.before_v621.bak')
    if backup.exists():
        raise ValueError('Backup already exists. Refusing overwrite.')
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
        installed = run()
    except (ValueError, OSError, SyntaxError, UnicodeError) as error:
        print('V6.2.1 installation stopped safely:', error)
        sys.exit(1)
    print('V6.2.1 patched ai_study_assistant.py; backup created.' if installed
          else 'V6.2.1 already installed; no files changed.')
