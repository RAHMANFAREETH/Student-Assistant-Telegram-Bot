# V12.0 Windows symlink test compatibility fix

The task sync installer **already applied** successfully, and JavaScript tests passed. The original `test_refuses_symlinks` tried to create a real symbolic link. Some Windows accounts cannot create symlinks without Developer Mode or elevation (WinError 1314).

This patch changes **only** `TEST_INSTALL_V120_TASK_SYNC.py`: it mocks `Path.is_symlink()` for the chosen test path and checks that the production installer still rejects symbolic-link destinations. No production code, bot handler, database, or feature flag is modified. Tests remain active (no skip).

## In VS Code (PowerShell)

1. Extract the ZIP into `C:\Users\Pros\Desktop\StudentAssistantBot`. Overwrite `TEST_INSTALL_V120_TASK_SYNC.py` only.
2. Run:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 -m unittest TEST_SUPER_MINIAPP_V120 TEST_SUPER_PLANNER_V120 TEST_SUPER_TASK_SYNC_V120 TEST_INSTALL_V120_TASK_SYNC -q
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

Expected: 40 Python tests pass; the existing HTML file-handle `ResourceWarning` may still appear and does not cause a test failure. Do not execute SQL or deploy the V12 development preview yet. Keep `SUPER_MINIAPP_V120_ENABLED=false`.
