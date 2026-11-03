"""Fix old V7.13/V7.14 test assumptions for real Telegram keyboards.

Only patches two TEST_*.py files. Does not change production bot code.
Run: python FIX_V8_KEYBOARD_TESTS.py --check
     python FIX_V8_KEYBOARD_TESTS.py --apply
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime
from pathlib import Path
import sys

TARGETS = ("TEST_V7_13_IMAGE_FILTERS.py", "TEST_V7_14_AUTO_CROP.py")
OLD = 'rows = self.bot.sent[-1][2]["reply_markup"].rows'
NEW = (
    'markup = self.bot.sent[-1][2]["reply_markup"]',
    'rows = getattr(markup, "keyboard", getattr(markup, "rows", None))',
    'self.assertIsNotNone(rows, "Unsupported Telegram keyboard representation")',
)


def patch(data: bytes, filename: str) -> tuple[str, bytes]:
    text = data.decode("utf-8")
    if text.count(OLD) == 0 and NEW[1] in text:
        return "already fixed", data
    if text.count(OLD) != 1:
        raise ValueError(f"{filename}: expected one old keyboard assertion, found {text.count(OLD)}")
    newline = "\r\n" if "\r\n" in text else "\n"
    pos = text.index(OLD)
    line_start = text.rfind("\n", 0, pos) + 1
    indentation = text[line_start:pos]
    if indentation.strip():
        raise ValueError(f"{filename}: unexpected indentation before target")
    updated = text.replace(OLD, (newline + indentation).join(NEW), 1)
    ast.parse(updated, filename=filename)
    return "updated", updated.encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Preview compatibility only; no writes")
    group.add_argument("--apply", action="store_true", help="Apply test-only fix with backups")
    args = parser.parse_args()
    root = Path.cwd()
    pending = []
    try:
        for name in TARGETS:
            path = root / name
            original = path.read_bytes()
            status, replacement = patch(original, name)
            print(f"{name}: {status}")
            if status == "updated":
                pending.append((path, original, replacement))
    except (OSError, ValueError, SyntaxError, UnicodeError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        print("No files have been modified.", file=sys.stderr)
        return 1
    if args.check:
        print("CHECK OK. No files changed. Run --apply to fix only the test assertions.")
        return 0
    if not pending:
        print("Nothing to change: both tests are already compatible.")
        return 0
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    for path, original, replacement in pending:
        backup = path.with_name(path.name + f".pre_keyboard_fix_{stamp}.bak")
        backup.write_bytes(original)
        path.write_bytes(replacement)
        print(f"Patched {path.name}; backup: {backup.name}")
    print("APPLY OK. Production source and Render deployment were not changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
