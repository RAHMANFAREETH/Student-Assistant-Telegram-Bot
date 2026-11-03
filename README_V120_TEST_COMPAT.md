# V12.0.1 Regression Test Compatibility Fix

The 62-tool QA rebuild exposed two **outdated test assumptions**, confirmed by the Windows traceback:

- `TEST_SUPER_MINIAPP_V120`: it expected manual adult verification to be mandatory, even while `SUPER_MINIAPP_V120_REQUIRE_ADULT=false`. The repaired test explicitly verifies **both modes**: adult verification enforced when enabled, and omitted when disabled, **while rejecting invalid Telegram signatures in both modes**.
- `TEST_V7_9_AUDIT`: it expected exactly 11 original menu entries. The new 🎓 Super Mini App adds one optional entry. The repaired assertion verifies **11 legacy entries + 0 or 1 new entry**, prevents duplicate Mini App entries, and still checks Book Library presence.

No production files, Library code, bot code or environment variables are modified. **Only two test files are changed.**

In VS Code PowerShell after extracting this ZIP into the project root:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python INSTALL_V120_TEST_COMPAT_FIX.py --check
python INSTALL_V120_TEST_COMPAT_FIX.py --apply
python -X utf8 -m unittest TEST_SUPER_MINIAPP_V120 TEST_V7_9_AUDIT TEST_V120_PUBLIC_ACCESS TEST_V120_ACCESS_MENU_FIX -q
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
node --test TEST_SUPER_TOOLS_V120.mjs TEST_SUPER_TOOLS_EXPANSION_V120.mjs TEST_SUPER_LOCALE_PLANNER_V120.mjs TEST_SUPER_TASK_SYNC_V120.mjs TEST_V120_REBUILT_TOOLS.mjs
```

Proceed to a selective Git commit only after the complete regression is green. Never use `git add .` because there are many unrelated files and backup folders in the project.

The `ResourceWarning: unclosed file` seen in the older Flask test is a separate warning, not a reason to modify production code in this compatibility patch.
