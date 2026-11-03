# V12.0 Public Mini App Access + Menu Buttons — Development Fix

**Goal:** let everyone open and use the **50 browser-only utility tools** without manually verifying adult status. Preserve Telegram HMAC validation for **private** task/planner APIs, user-specific database isolation, existing Library routes, and other bot features.

## What this changes

- `/app` session endpoint can return `guest=true` when Telegram signed login is absent, expired or invalid **only when** `SUPER_MINIAPP_V120_PUBLIC_TOOLS=true`. It does not leak a user ID.
- Guest users can use the 50 locally computed tools. Guest quick tasks use `sessionStorage` (not shared cross-account storage), are **not backed up** and are lost after the browser session ends.
- An account with valid Telegram signed `initData` can use its own synced tasks/planner. When `SUPER_MINIAPP_V120_REQUIRE_ADULT=false`, V12 benign data features do not ask for an additional **manual adult verification** step. Signed Telegram identity is still **mandatory** for saved private data.
- Existing AI, V8/V9, Library, PDF, admin, and age restrictions in other features **are not changed**. If minors use the V12 utilities, do not expose age-restricted external AI to them. Follow applicable privacy and child-safety obligations.
- The prior **Access & Menu Repair** adds the V12 button to the Friendly Home Menu and main reply keyboard. The Telegram native Menu Button must be set separately in BotFather.

## Install in VS Code PowerShell

Extract all files from this ZIP into `C:\Users\Pros\Desktop\StudentAssistantBot`. There are no production-file replacements in the ZIP, only guarded installers, tests and this README.

**1. Configure existing Render release flags to `false` while preparing the fix:**

```
SUPER_MINIAPP_V120_ENABLED=false
SUPER_MINIAPP_V120_LAUNCH_ENABLED=false
```

**2. Apply menu repair first** (safe even if previously applied):

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 -m unittest TEST_V120_ACCESS_MENU_FIX -q
python INSTALL_V120_ACCESS_MENU_FIX.py --check
python INSTALL_V120_ACCESS_MENU_FIX.py --apply
```

**3. Apply the new public-mode fix**:

```powershell
python INSTALL_V120_PUBLIC_ACCESS.py --check
python INSTALL_V120_PUBLIC_ACCESS.py --apply
python -m py_compile navigation.py friendly_v119.py super_miniapp_v120.py super_miniapp_v120_launch.py
```

**4. Run regression tests before committing**:

```powershell
python -X utf8 -m unittest TEST_V120_ACCESS_MENU_FIX TEST_V120_PUBLIC_ACCESS TEST_V120_TELEGRAM_LAUNCH TEST_SUPER_MINIAPP_V120 TEST_SUPER_PLANNER_V120 TEST_SUPER_TASK_SYNC_V120 -q
node --test TEST_SUPER_TOOLS_V120.mjs TEST_SUPER_TOOLS_EXPANSION_V120.mjs TEST_SUPER_LOCALE_PLANNER_V120.mjs TEST_SUPER_TASK_SYNC_V120.mjs
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

The patch checks exact source anchors, refuses unexpected layouts, makes backups, and is idempotent. **Stop if any test fails.**

**5. Review and stage only these named files** after all tests pass:

```powershell
git status --short
git add -- navigation.py friendly_v119.py super_miniapp_v120.py super_miniapp_v120_launch.py super_miniapp_v120.js INSTALL_V120_ACCESS_MENU_FIX.py TEST_V120_ACCESS_MENU_FIX.py INSTALL_V120_PUBLIC_ACCESS.py TEST_V120_PUBLIC_ACCESS.py README_V120_PUBLIC_ACCESS.md
git diff --cached --check
git diff --cached --stat
git diff --cached -- navigation.py friendly_v119.py super_miniapp_v120.py super_miniapp_v120_launch.py super_miniapp_v120.js
```

If the diff contains only the intended changes and no secrets, then:

```powershell
git commit -m "Enable public V12 utilities with signed private data and menu buttons"
git push origin main
```

Confirm Render deployed the new commit. Then enable these variables in Render:

| Variable | Value |
|---|---|
| `SUPER_MINIAPP_V120_ENABLED` | `true` |
| `SUPER_MINIAPP_V120_LAUNCH_ENABLED` | `true` |
| `SUPER_MINIAPP_V120_LAUNCH_PUBLIC` | `true` |
| `SUPER_MINIAPP_V120_PUBLIC_URL` | `https://student-assistant-telegram-bot.onrender.com/app` |
| **NEW** `SUPER_MINIAPP_V120_PUBLIC_TOOLS` | `true` |
| **NEW** `SUPER_MINIAPP_V120_REQUIRE_ADULT` | `false` |
| `SUPER_MINIAPP_V120_PILOT_IDS` | Omit |

The two NEW flags are **required for the requested behavior**. Other existing environment settings stay as they are. If `SUPER_MINIAPP_V120_REQUIRE_ADULT` is missing, it defaults to `true` for safety.

**6. Telegram testing**:

- `/superapp` in the bot's private chat should open the 50-tool dashboard, even for a user with no manual age verification.
- The new **🎓 Super Mini App** Home Menu button should appear after the menu repair is deployed.
- Open `/app` in a regular browser: tools work in guest mode; saved account data is unavailable.
- From a Telegram signed Mini App session, task syncing uses only the verified Telegram user ID; on invalid signature it uses guest mode and cannot read any private tasks.
- Check that a second account cannot see the first account's saved tasks.
- **Telegram native Menu Button** near the message box: use @BotFather `/setmenubutton`, text `🎓 Super Mini App`, URL `https://student-assistant-telegram-bot.onrender.com/app`. This may replace your current native Library Menu Button, not your Library feature.

**Rollback:** set both `SUPER_MINIAPP_V120_ENABLED=false` and `SUPER_MINIAPP_V120_LAUNCH_ENABLED=false` in Render and deploy. Installer backups are retained locally.

## Testing status (standalone environment)

- Public-access Python focused tests: 11 passed.
- Existing JavaScript test files: 54 passed.
- Mobile browser smoke: guest opened all 50 cards, calculated fraction, created temporary task, no JavaScript exceptions.
- Windows full-regression and Telegram live deployment still **not verified** for this fix; run them on your project before announcing release.
