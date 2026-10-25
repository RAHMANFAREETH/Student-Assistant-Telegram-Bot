"""Safely install V6.2 into existing V6.1 Student Assistant Bot.

Patches only ai_study_assistant.py and ai_ops_v60.py. Uses UTF-8, backups,
AST syntax check and idempotent markers. Never modifies Telegram public routing.
"""
from __future__ import annotations

import ast
from pathlib import Path
import shutil
import sys

AI = "ai_study_assistant.py"
OPS = "ai_ops_v60.py"
MODULE = "ai_reliability_v62.py"
MAIN = "main.py"
V61 = "gemini_render_v61.py"

AI_ANCHOR = "_provider_call = wrap_cloudflare_provider(_provider_call)"
AI_MARKER = "# V6.2 passive Cloudflare health observation (never changes outputs)"
AI_PATCH = (
    "\n\n" + AI_MARKER + "\n"
    "from ai_reliability_v62 import observe_cloudflare_health\n"
    "_provider_call = observe_cloudflare_health(_provider_call)\n"
)
OPS_OLD_COMMANDS = '@bot.message_handler(commands=["aiops", "aiproviders"])'
OPS_NEW_COMMANDS = '@bot.message_handler(commands=["aiops", "aiproviders", "aihealth"])'
OPS_OLD_SEND = '        bot.send_message(chat.id, format_report())'
OPS_MARKER = '# V6.2 private admin health report (same authorization as /aiops)'
OPS_NEW_SEND = (
    '        ' + OPS_MARKER + '\n'
    '        command = ((getattr(message, "text", "") or "").split(maxsplit=1) or [""])[0].split("@", 1)[0]\n'
    '        if command == "/aihealth":\n'
    '            bot.send_message(chat.id, __import__("ai_reliability_v62").format_health_report())\n'
    '        else:\n'
    '            bot.send_message(chat.id, format_report())'
)


def patch_ai(source: str) -> tuple[str, bool]:
    if AI_MARKER in source:
        if source.count(AI_MARKER) != 1 or source.count("_provider_call = observe_cloudflare_health(_provider_call)") != 1:
            raise ValueError("Partial V6.2 Cloudflare health patch: inspect ai_study_assistant.py")
        ast.parse(source, filename=AI)
        return source, False
    if source.count(AI_ANCHOR) != 1 or "def register_ai_study_assistant_handlers" not in source:
        raise ValueError("Existing V6.0 Cloudflare monitoring not found; V6.2 not applied")
    modified = source.rstrip("\r\n") + AI_PATCH
    ast.parse(modified, filename=AI)
    return modified, True


def patch_ops(source: str) -> tuple[str, bool]:
    if OPS_MARKER in source:
        if source.count(OPS_MARKER) != 1 or source.count(OPS_NEW_COMMANDS) != 1 or source.count("format_health_report()") != 1:
            raise ValueError("Partial V6.2 admin-command patch: inspect ai_ops_v60.py")
        ast.parse(source, filename=OPS)
        return source, False
    if (source.count(OPS_OLD_COMMANDS) != 1 or source.count(OPS_OLD_SEND) != 1
            or '"gemini_render_v61"' not in source):
        raise ValueError("Compatible V6.1 admin diagnostics not found; V6.2 not applied")
    modified = source.replace(OPS_OLD_COMMANDS, OPS_NEW_COMMANDS, 1)
    modified = modified.replace(OPS_OLD_SEND, OPS_NEW_SEND, 1)
    ast.parse(modified, filename=OPS)
    return modified, True


def _read(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as f:
        return f.read()


def _write(path: Path, contents: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(contents)


def run_install(root: Path = Path('.')) -> list[str]:
    root = Path(root)
    for name in (MAIN, AI, OPS, MODULE, V61):
        if not (root / name).is_file():
            raise ValueError(f"Missing {name}; copy the V6.2 files into the existing V6.1 bot")
    patchers = {AI: patch_ai, OPS: patch_ops}
    originals, updates = {}, {}
    for name, patcher in patchers.items():
        original = _read(root / name)
        output, changed = patcher(original)
        originals[name] = original
        if changed:
            updates[name] = output
    if not updates:
        return []
    for name in updates:
        target = root / f"{name}.before_v62.bak"
        if target.exists():
            raise ValueError(f"Backup {target.name} already exists; refusing to overwrite")
    for name in updates:
        shutil.copy2(root / name, root / f"{name}.before_v62.bak")
    try:
        for name, output in updates.items():
            _write(root / name, output)
    except OSError:
        for name in updates:
            shutil.copy2(root / f"{name}.before_v62.bak", root / name)
        raise
    return sorted(updates)


def main() -> int:
    try:
        modified = run_install(Path.cwd())
    except (ValueError, OSError, SyntaxError, UnicodeError) as err:
        print("V6.2 installer stopped safely:", err)
        return 1
    print("V6.2 installed: " + ", ".join(modified) if modified else "V6.2 already installed; no files changed.")
    print("Test: python -m unittest TEST_V6_2_RELIABILITY.py -v")
    print("Admin private Telegram command after deployment: /aihealth")
    return 0


if __name__ == "__main__":
    sys.exit(main())
