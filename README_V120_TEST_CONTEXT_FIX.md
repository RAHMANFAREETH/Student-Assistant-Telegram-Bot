# Student Assistant Bot — V12.0 preview test fix

The user's `python -X utf8 -m unittest TEST_SUPER_MINIAPP_V120 -q` originally failed 3/9 tests even though `INSTALL_SUPER_MINIAPP_V120.py --check` returned `CHECK OK`.

## Root causes
- The original test directly calls the new home view, which uses Flask `send_file` requiring an HTTP request context.
- The disabled-feature test expected `ValueError`, whereas Flask `abort(404)` raises `werkzeug.exceptions.NotFound`.
- The security-header test patched `flask.request.path` outside a request context (`flask.request` is a `LocalProxy`).

## What this fix changes
**Only** `TEST_SUPER_MINIAPP_V120.py` (plus this optional instruction file). The new test file mocks the boundary at `send_file` and `abort` in isolated unit tests, mocks the module's `request` proxy instead of dereferencing `flask.request`, adds a test guarding existing `/library` headers, and uses real Flask `test_client()` for actual 404, 200 and security-header assertions when Flask is installed.

**No production files changed** (`main.py`, `super_miniapp_v120.py`, existing Library code, environment flags, database).

## How to apply
1. Copy `TEST_SUPER_MINIAPP_V120.py` from this ZIP into your working `C:\Users\Pros\Desktop\StudentAssistantBot` folder. When Windows asks, choose **Replace** for that exact test file only.
2. Open VS Code Terminal and run:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 -m unittest TEST_SUPER_MINIAPP_V120 -q
python INSTALL_SUPER_MINIAPP_V120.py --check
```

3. Do not run `--apply` until the tests pass and the `--check` diff still adds only the V12 registration block. If so, cautiously run:

```powershell
python INSTALL_SUPER_MINIAPP_V120.py --apply
python -m py_compile main.py super_miniapp_v120.py
python -X utf8 -m unittest TEST_SUPER_MINIAPP_V120 -q
node --test TEST_SUPER_TOOLS_V120.mjs
```

The Node command is only available if Node.js is installed locally. Leave `SUPER_MINIAPP_V120_ENABLED=false`. Do not push to GitHub or deploy unfinished preview code just because these tests pass; test the entire bot first.

## Verification performed when packaging
- Standalone Python test suite: 12 tests, all passed, 2 skipped because Flask is not installed in the packaging environment. (On the Windows bot system Flask should exist, so 12 tests should execute.)
- Node JavaScript utility suite from unmodified V12 preview: 22 tests passed.
- No Render production testing is claimed.
