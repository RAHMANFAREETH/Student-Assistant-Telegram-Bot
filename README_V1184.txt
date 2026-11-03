V11.8.4 SAFE REGRESSION DIAGNOSTIC (TEST ONLY)

This package contains RUN_REGRESSION_SAFE_V1184.py, a new independent runner.
It DOES NOT change main.py, tests, Supabase, Render, Telegram, or the current V11.8.3 installation.

Reason for this change:
- In Windows, pathlib glob('TEST_*.py') may also match lowercase test_*.py.
  The old runner accidentally ran a separate adult Gemini service test asserting
  main.py should not exist. The public StudentAssistantBot MUST retain main.py.
- Tests previously inherited the user's live environment flags. For instance,
  V93_REQUEST_RPC_ENABLED=true changes the V9.1 API flow and causes tests
  using fake old-style databases to fail. AZURE_TRANSLATOR_KEY similarly
  selects a different provider than the historical fallback tests expect.
- We do not yet have the individual Windows failure tracebacks for the other
  failed modules. This runner will make them easier to diagnose.

COPY RUN_REGRESSION_SAFE_V1184.py INTO THE PROJECT ROOT (same folder as main.py).

PowerShell:
  cd "C:\Users\Pros\Desktop\StudentAssistantBot"
  python -X utf8 RUN_REGRESSION_SAFE_V1184.py --affected-only
  python -X utf8 RUN_REGRESSION_SAFE_V1184.py

The first command runs the 10 previously failing uppercase modules; the second
runs ALL uppercase TEST_*.py modules. Both print a summary and save a complete
V1184_REGRESSION_REPORT_YYYYMMDD_HHMMSS.txt file in the project folder.
The process returns nonzero if any test fails, which is intentional.

Optional diagnostic to compare inherited application config:
  python -X utf8 RUN_REGRESSION_SAFE_V1184.py --affected-only --inherit-app-env

By default, only inherited application feature flags for BOOK_LIBRARY_,
LIBRARY_MEDIA_, LIBRARY_MANAGE_, LIBRARY_SEARCH_, V8_, V9_, V91_, V92_,
V93_, V10_, V101_, V11_, and AZURE_TRANSLATOR_KEY/REGION are suppressed
in CHILD TEST PROCESSES. All original variables remain intact in PowerShell.
Other credentials are not cleaned, so keep this test environment offline and
avoid testing with real production credentials when possible.

The tests may still fail on Windows Python 3.14. If so, upload the detailed
V1184 report (after checking it for secrets). Do not deploy yet. A clean unit
suite is a prerequisite for further integration verification, not proof of
real Telegram and Render readiness.
