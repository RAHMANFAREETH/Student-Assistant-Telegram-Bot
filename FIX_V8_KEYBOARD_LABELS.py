"""Test-only keyboard label compatibility fix, for V8 combined regression suite.

Works when reply_markup rows contain either dict buttons or button objects.
Does not edit production application code. Run with --check first, then --apply.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime
from pathlib import Path
import sys

TARGETS = ("TEST_V7_13_IMAGE_FILTERS.py", "TEST_V7_14_AUTO_CROP.py")
OLD = 'labels = [b.text for row in rows for b in row]'
NEW = 'labels = [b["text"] if isinstance(b, dict) else b.text for row in rows for b in row]'


def transform(path: Path) -> tuple[str, bytes, bytes]:
    source = path.read_bytes()
    text = source.decode("utf-8")
    if OLD not in text and NEW in text:
        return "already updated", source, source
    count = text.count(OLD)
    if count != 1:
        raise ValueError(f"{path.name}: expected one old assertion, found {count}. No changes made.")
    updated = text.replace(OLD, NEW, 1)
    ast.parse(updated, filename=path.name)
    return "needs patch", source, updated.encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--apply", action="store_true")
    options = parser.parse_args()
    pending = []
    try:
        for name in TARGETS:
            file = Path.cwd() / name
            status, old, new = transform(file)
            print(f"{name}: {status}")
            if old != new:
                pending.append((file, old, new))
    except (OSError, SyntaxError, ValueError, UnicodeError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 1
    if options.check:
        print("CHECK OK. No files changed.")
        return 0
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    for file, original, replacement in pending:
        backup = file.with_name(f"{file.name}.pre_labels_fix_{stamp}.bak")
        backup.write_bytes(original)
        file.write_bytes(replacement)
        print(f"Updated {file.name}; backup: {backup.name}")
    print("APPLY OK. Only the two test files were changed. Run the full test suite again.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
