"""Install V6.0 admin diagnostics into the existing V5.9 bot.

Conservative, idempotent two-file patch with preflight, UTF-8-safe I/O,
non-overwriting backups and best-effort rollback on write errors.
"""
from __future__ import annotations

import ast
from pathlib import Path
import shutil
import sys

MAIN = "main.py"
AI = "ai_study_assistant.py"
OPS = "ai_ops_v60.py"
GEMINI = "gemini_ai_studio_v59.py"
MAIN_IMPORT = "from ai_ops_v60 import register_ai_ops_v60_handlers"
MAIN_REGISTRATION = "register_ai_ops_v60_handlers(bot)"
AI_MARKER = "# V6.0 aggregate Cloudflare monitoring (no prompt data)"
AI_SNIPPET = '''\n\n# V6.0 aggregate Cloudflare monitoring (no prompt data)
# This wraps existing calls without modifying provider requests or safety logic.
from ai_ops_v60 import wrap_cloudflare_provider
_provider_call = wrap_cloudflare_provider(_provider_call)
'''


def patch_main(source: str) -> tuple[str, bool]:
    has_import = MAIN_IMPORT in source
    has_reg = MAIN_REGISTRATION in source
    if has_import != has_reg:
        raise ValueError("Partial V6.0 main.py installation; inspect manually")
    if has_import:
        ast.parse(source, filename=MAIN)
        return source, False
    anchor_import = "from achievements_v58 import register_achievements_v58_handlers"
    anchor_reg = "register_achievements_v58_handlers(bot, show_main_menu)"
    if source.count(anchor_import) != 1 or source.count(anchor_reg) != 1:
        raise ValueError("Expected V5.8 main.py integration not found; no changes applied")
    if "register_ai_study_assistant_handlers(bot, show_main_menu)" not in source:
        raise ValueError("Cloudflare AI handler registration missing")
    source = source.replace(anchor_import, anchor_import + "\n" + MAIN_IMPORT, 1)
    source = source.replace(anchor_reg, anchor_reg + "\n" + MAIN_REGISTRATION, 1)
    if '"version": "5.8"' in source:
        source = source.replace('"version": "5.8"', '"version": "6.0"', 1)
    ast.parse(source, filename=MAIN)
    return source, True


def patch_ai(source: str) -> tuple[str, bool]:
    if AI_MARKER in source:
        if source.count(AI_MARKER) != 1 or "_provider_call = wrap_cloudflare_provider(_provider_call)" not in source:
            raise ValueError("Partial V6.0 AI instrumentation; inspect manually")
        ast.parse(source, filename=AI)
        return source, False
    tree = ast.parse(source, filename=AI)
    providers = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_provider_call"]
    handlers = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == "register_ai_study_assistant_handlers"]
    if len(providers) != 1 or len(handlers) != 1:
        raise ValueError("Expected V5.5 Cloudflare AI functions not found")
    if "GUARD_MODEL" not in source or "_check_safety" not in source:
        raise ValueError("Cloudflare safety checks not found; refusing patch")
    source = source.rstrip("\r\n") + AI_SNIPPET
    ast.parse(source, filename=AI)
    return source, True


def _read_exact_utf8(path: Path) -> str:
    # newline='' preserves CRLF in Windows files for minimal diffs.
    with path.open("r", encoding="utf-8", newline="") as stream:
        return stream.read()


def _write_exact_utf8(path: Path, value: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(value)


def run_install(root: Path = Path(".")) -> list[str]:
    root = Path(root)
    for filename in (MAIN, AI, OPS, GEMINI):
        if not (root / filename).is_file():
            raise ValueError(f"Missing {filename}; use the existing V5.9 project")
    patchers = {MAIN: patch_main, AI: patch_ai}
    originals: dict[str, str] = {}
    updates: dict[str, str] = {}
    for name, patch in patchers.items():
        old = _read_exact_utf8(root / name)
        updated, changed = patch(old)
        originals[name] = old
        if changed:
            updates[name] = updated
    if not updates:
        return []
    for name in updates:
        backup = root / (name + ".before_v60.bak")
        if backup.exists():
            raise ValueError(f"Backup already exists: {backup.name}; refusing to overwrite")
    for name in updates:
        shutil.copy2(root / name, root / (name + ".before_v60.bak"))
    try:
        for name, changed_content in updates.items():
            _write_exact_utf8(root / name, changed_content)
    except OSError:
        for name in updates:
            shutil.copy2(root / (name + ".before_v60.bak"), root / name)
        raise
    return sorted(updates)


def main():
    try:
        modified = run_install(Path.cwd())
    except (ValueError, OSError, SyntaxError, UnicodeError) as exc:
        print("V6.0 installation stopped safely:", exc)
        return 1
    if modified:
        print("V6.0 installed:", ", ".join(modified))
    else:
        print("V6.0 already installed; no files changed.")
    print("Set AI_OPS_ADMIN_IDS to your own Telegram numeric user ID in Render Environment.")
    print("Run: python -m unittest TEST_V6_0_AI_OPS.py -v")
    return 0


if __name__ == "__main__":
    sys.exit(main())
