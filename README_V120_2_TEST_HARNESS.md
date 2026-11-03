# V12.0.2 — Flask Test Harness Compatibility Repair

V12.0.2 adds 2 Flask endpoints for temporary image exports. The old test `FakeApp`
classes only implement `get`/`route`, while the new export module registers
its upload endpoint using `@app.post`. This can cause TEST_SUPER_MINIAPP_V120,
TEST_SUPER_PLANNER_V120, TEST_SUPER_TASK_SYNC_V120 and TEST_V120_PUBLIC_ACCESS
to fail during test setup. This patch adds `FakeApp.post()` to the two test
harnesses and checks the new 11-endpoint count, including BOTH export routes.

**Nothing in production code, authentication, RLS or the Library is changed.**
The patch refuses unexpected test layouts and backs up original test files.

Run in VS Code terminal from `C:\Users\Pros\Desktop\StudentAssistantBot`:

```powershell
python INSTALL_V120_2_TEST_HARNESS_FIX.py --check
python INSTALL_V120_2_TEST_HARNESS_FIX.py --apply
python -X utf8 -m unittest TEST_SUPER_MINIAPP_V120 TEST_SUPER_PLANNER_V120 TEST_SUPER_TASK_SYNC_V120 TEST_V120_PUBLIC_ACCESS TEST_V120_2_EXPORT_CLOCK -q
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

Do not commit or deploy until all tests pass. If anything still fails, run:

```powershell
python -X utf8 -m unittest TEST_SUPER_MINIAPP_V120 TEST_SUPER_PLANNER_V120 TEST_SUPER_TASK_SYNC_V120 TEST_V120_PUBLIC_ACCESS -v *> V120_2_FAILURE_DETAIL.txt
Get-Content .\V120_2_FAILURE_DETAIL.txt -Tail 90
```

Share only the failure tracebacks, after checking for secrets. No new Render
flags or Supabase migrations are needed for this test-only repair.
