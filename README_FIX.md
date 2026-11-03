# V7.9 installer fix: preserve custom .gitignore

This fixes only the V7.9 dry-run error `Unexpected local edits in .gitignore`.
It never edits, replaces, merges, or deletes `.gitignore`.
All other seven project targets remain subject to the SAME exact old/new SHA-256 guard checks.
If another project file has local modifications, it will safely stop as before.

## Windows instructions
1. Back up or commit your current project. DO NOT delete or overwrite your custom .gitignore.
2. From this ZIP, copy `INSTALL_V7_9.py` into the existing `StudentAssistantBot` root, **replacing only the existing installer**, not any bot source file. Keep the original `V79_UPDATED` folder from the V7.9 patch.
3. Run `python INSTALL_V7_9.py --dry-run`. If anything unexpected is reported, STOP and share the full output; do not bypass its checks.
4. If dry-run is successful, run `python INSTALL_V7_9.py`, then `python -m unittest TEST_V7_9_AUDIT.py -v`.
5. Then run V7.10's dry-run and installer as previously described.

## IMPORTANT: .gitignore security review
Because your custom .gitignore is kept unchanged, confirm that it ignores `.env`, `.env.*` (with your `.env.example` exception if needed), `.venv/`, `*.db`, `*.zip`, `v79_backups/`, and `__pycache__/` before pushing. Add missing entries manually without deleting existing custom patterns.
Run in PowerShell: `git check-ignore .env` (should show `.env` if untracked and ignored) and `git ls-files .env` (should print nothing). Ignoring an already tracked secret does not untrack it.
Do not commit local secrets, .env or repository backup ZIPs.

## Rollback
The updated installer still supports `python INSTALL_V7_9.py --rollback` for its seven managed files. It does not touch .gitignore either way.
