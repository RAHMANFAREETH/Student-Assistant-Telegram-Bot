"""Guarded V12.0.2 worldwide clock + Telegram download integration.

Always --check first. No unrelated bot files or /library routes are modified.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, os, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / "V120_2_PAYLOAD"
BASELINE = {'super_miniapp_v120.js': 'f6295b97d79e35e55d1bce4e92a0051df0b1706e6f0ed0e2e011776e2a0cd795', 'super_miniapp_v120_tools.mjs': '08b24a0c5bc05712205250b7432b504cd5c480e378659823809fa1aa2c084e84', 'super_miniapp_v120_exports.py': None, 'TEST_SUPER_TOOLS_V120.mjs': '6394b79f809b3d471dd9593c04631f5aebc33c5956bcfe10f4b4ef8a86d9100b', 'TEST_SUPER_TOOLS_EXPANSION_V120.mjs': 'b0a91d6ee9faaa5aefa1d75c6b6beac15421f7557cdec021062c6a9bf3b147a4', 'TEST_SUPER_LOCALE_PLANNER_V120.mjs': '49d89743d8fd4c3ddad18bec5b952633ed5557de733944789ec10ab28088d473', 'TEST_V120_REBUILT_TOOLS.mjs': '2c5e00495eb0b5a4e29e3bdaf5a834fc15d84e6321c17ca8bf2da202de66f171', 'TEST_V120_2_EXPORT_WORLD.mjs': None, 'TEST_V120_2_EXPORT_CLOCK.py': None}

# V12.0.2 CSS: the original installer mistakenly required the older V12.0
# 50-tools CSS, but the V12.0 planner localization legitimately updated it.
# Append only new CSS rules to preserve planner/language layouts.
CSS_KNOWN_BASELINES = {
    "a40d9c8201a4e7c704babe7bbed6d230e6515223a2cdcef3870c9a919b67d4db",  # 50-tools baseline
    "89afcbf736371d7011a7073ba9398f79cc13d87255f31bfcca2a305f20eaf05e",  # planner/localization baseline
}
CSS_FILE = "super_miniapp_v120.css"
CSS_ADDITIONS = "V120_2_CSS_ADDITIONS.css"


def plan_css(root: Path):
    target = root / CSS_FILE
    fragment = PAYLOAD / CSS_ADDITIONS
    if (not target.is_file() or target.is_symlink() or
            not fragment.is_file() or fragment.is_symlink()):
        raise RuntimeError("Missing or unsafe CSS file/patch fragment")
    current = target.read_bytes()
    suffix = fragment.read_bytes()
    marker = b"/* V12.0.2 worldwide clocks & explicit save fallback */"
    if not suffix.startswith(marker) or suffix.count(marker) != 1:
        raise RuntimeError("Unexpected V12.0.2 CSS patch fragment")
    # Recognize an exact previous application to either approved base.
    # Do not silently accept an arbitrary stylesheet containing the marker.
    # This retains fail-closed semantics for user customizations.
    if digest(current) in CSS_KNOWN_BASELINES:
        return current.rstrip(b"\r\n") + b"\n\n" + suffix
    if marker in current:
        original = current.split(b"\n\n" + marker, 1)
        if (len(original) == 2 and any(digest(original[0] + tail) in CSS_KNOWN_BASELINES for tail in (b"", b"\n", b"\r\n"))
                and original[1] == suffix[len(marker):]):
            return None
    raise RuntimeError(
        "Local CSS does not match an approved V12.0 baseline: " + digest(current)[:16] +
        ". No files modified. Preserve your file and compare it before retrying."
    )


NEEDLE = '    if "v120_super_home" in app.view_functions:\n        return\n'
INSERT = (NEEDLE
          + '\n    # >>> V12.0.2 optional temporary exports >>>\n'
          + '    from super_miniapp_v120_exports import register_v120_exports\n'
          + '    register_v120_exports(app)\n'
          + '    # <<< V12.0.2 optional temporary exports <<<\n')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def plans(root: Path):
    actions = {}
    for name, old_hash in BASELINE.items():
        target = root/name
        source = PAYLOAD/name
        if not source.is_file() or source.is_symlink():
            raise RuntimeError("Missing or unsafe payload: " + name)
        if target.is_symlink() or target.is_dir():
            raise RuntimeError("Unsafe destination: " + name)
        new = source.read_bytes()
        existing = target.read_bytes() if target.exists() else None
        if existing == new:
            actions[name] = None
        elif old_hash is None:
            if existing is not None:
                raise RuntimeError("Unexpected existing file: " + name)
            actions[name] = new
        elif existing is None or digest(existing) != old_hash:
            raise RuntimeError("Local file differs from tested V12.0.1 baseline: " + name
                               + ". Preserve local changes and investigate; no files modified.")
        else:
            actions[name] = new

    actions[CSS_FILE] = plan_css(root)

    main = root / "super_miniapp_v120.py"
    if main.is_symlink() or not main.is_file():
        raise RuntimeError("Missing/unsafe super_miniapp_v120.py")
    raw = main.read_text(encoding="utf8")
    if NEEDLE not in raw or "def verify_super_session(" not in raw or "/app/api/tasks" not in raw:
        raise RuntimeError("Unknown V12.0 Mini App backend layout.")
    if "register_v120_exports(app)" in raw:
        actions["super_miniapp_v120.py"] = None
    else:
        if raw.count(NEEDLE)!=1:
            raise RuntimeError("Mini App registration hook not unique.")
        updated = raw.replace(NEEDLE, INSERT, 1)
        compile(updated, "super_miniapp_v120.py", "exec")
        actions["super_miniapp_v120.py"] = updated.encode("utf8")
    return actions


def main():
    args=argparse.ArgumentParser()
    mx=args.add_mutually_exclusive_group(required=True)
    mx.add_argument("--check",action="store_true")
    mx.add_argument("--apply",action="store_true")
    cfg=args.parse_args()
    changes=plans(ROOT)
    for fname,data in changes.items():
        print(("UNCHANGED " if data is None else ("ADD " if not (ROOT/fname).exists() else "UPDATE ")) + fname)
    if cfg.check:
        print("CHECK OK (no changes written)")
        return
    todo={k:v for k,v in changes.items() if v is not None}
    if not todo:
        print("NO CHANGES (already applied)")
        return
    backup=ROOT / ("V120_2_EXPORT_CLOCK_BACKUP_"+dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    backup.mkdir()
    for fname in todo:
        old=ROOT/fname
        if old.exists():shutil.copy2(old,backup/fname)
    for fname,contents in todo.items():
        out=ROOT/fname
        tmp=ROOT/(fname+".v1202tmp")
        if tmp.exists():raise RuntimeError("Unsafe leftover temp: "+str(tmp))
        try:
            with tmp.open("xb") as handle:handle.write(contents)
            os.replace(tmp,out)
        finally:
            if tmp.exists():tmp.unlink()
    print("APPLIED. Backup:",backup)
    print("Only named Super Mini App assets were changed. No Supabase migration.")
    print("Run Node, Python and full regression tests before any GitHub push/Render deploy.")


if __name__ == "__main__":
    try:main()
    except Exception as exc:
        print("ERROR:",exc,file=sys.stderr)
        sys.exit(2)
