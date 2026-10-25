"""V6.1 safely patches only the V6.0 admin report; preserves all bot handlers."""
from __future__ import annotations

import ast
from pathlib import Path
import shutil
import sys

OPS = "ai_ops_v60.py"
GEMINI = "gemini_ai_studio_v59.py"
NEW = "gemini_render_v61.py"
MARKER = "# V6.1 Gemini Render configuration-only status (no API call)"
ANCHOR = '        "Gemini Telegram routing: DISABLED (mixed-age bot)",'
INSERTION = (
    '        # V6.1 Gemini Render configuration-only status (no API call)\n'
    '        __import__("gemini_render_v61").admin_line(),'
)


def patch_ops(source: str) -> tuple[str, bool]:
    if MARKER in source:
        if source.count(MARKER) != 1 or source.count('"gemini_render_v61"') != 1:
            raise ValueError("V6.1 admin report has been partially modified; inspect manually")
        ast.parse(source, filename=OPS)
        return source, False
    if source.count(ANCHOR) != 1 or "def format_report()" not in source:
        raise ValueError("Compatible V6.0 admin report not found; no files changed")
    result = source.replace(ANCHOR, ANCHOR + "\n" + INSERTION.rstrip("\n"), 1)
    ast.parse(result, filename=OPS)
    return result, True


def _read(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return stream.read()


def _write(path: Path, body: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(body)


def run_install(root: Path = Path(".")) -> list[str]:
    root = Path(root)
    for name in (OPS, GEMINI, NEW):
        if not (root / name).is_file():
            raise ValueError(f"Missing {name}; copy all V6.1 files into your V6.0 project")
    source = _read(root / OPS)
    amended, changed = patch_ops(source)
    if not changed:
        return []
    backup = root / "ai_ops_v60.py.before_v61.bak"
    if backup.exists():
        raise ValueError("V6.1 backup already exists; refusing to overwrite")
    shutil.copy2(root / OPS, backup)
    try:
        _write(root / OPS, amended)
    except OSError:
        shutil.copy2(backup, root / OPS)
        raise
    return [OPS]


def main() -> int:
    try:
        updated = run_install(Path.cwd())
    except (ValueError, SyntaxError, OSError, UnicodeError) as err:
        print("V6.1 installer stopped safely:", err)
        return 1
    print("V6.1 installed: " + ", ".join(updated) if updated else "V6.1 already installed; no files changed.")
    print("Test: python -m unittest TEST_V6_1_GEMINI_RENDER.py -v")
    return 0


if __name__ == "__main__":
    sys.exit(main())
