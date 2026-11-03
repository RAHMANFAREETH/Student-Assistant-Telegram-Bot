# V12.0 Telegram Access & Menu Repair (targeted, opt-in)

## Symptoms and diagnosis

- `/superapp` launches Telegram WebView but returns "Access unavailable". It is a rejected signed Telegram session (401), not a missing 50-tool feature. The patch adds safe, categorized logs **without weakening Telegram HMAC, verification, or the adult restriction**. The reason must be read in Render logs during a fresh live test.
- V12.0 introduced an explicit command only; no dedicated Home Menu button and no reply keyboard button were previously added.
- The Telegram native **Menu Button beside the chat composer** is configured separately through **@BotFather**. A menu button with the `/app` URL should provide Telegram signed data like an inline Web App button.

## Install

Extract **both** Python files into the existing `C:\Users\Pros\Desktop\StudentAssistantBot` folder. Ensure no active `/mediabulk` sessions before any Render restart.

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 -m unittest TEST_V120_ACCESS_MENU_FIX -q
python INSTALL_V120_ACCESS_MENU_FIX.py --check
python INSTALL_V120_ACCESS_MENU_FIX.py --apply
python -m py_compile navigation.py friendly_v119.py super_miniapp_v120.py super_miniapp_v120_launch.py
python -X utf8 -m unittest TEST_V120_ACCESS_MENU_FIX TEST_V120_TELEGRAM_LAUNCH TEST_SUPER_MINIAPP_V120 TEST_FRIENDLY_V119 -q
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

This installer changes only `navigation.py`, `friendly_v119.py`, `super_miniapp_v120_launch.py` and `super_miniapp_v120.py`. It backs them up, runs compilation **before writing**, refuses unknown layouts, and can be run again safely. It never modifies Supabase/Render or Telegram BotFather remotely.

## What is now in the UI

1. A dedicated **🎓 Super Mini App** Web App button in the V11.9 Friendly Home Menu, shown to eligible adults when both V12 flags and the URL are configured.
2. A dedicated **🎓 Super Mini App** text button in the bot's reply keyboard. Tapping sends the command through the normal `can_launch()` age gate and returns the signed **Open Student Assistant Super App** inline button. (Using a reply-keyboard `web_app` button directly is deliberately avoided; Telegram does not pass the same signed `initData` for that launch type.)
3. **Telegram native Menu Button**: open @BotFather → `/mybots` → choose Student Assistant Bot → Bot Settings → Menu Button, or `/setmenubutton` → choose your bot → text `🎓 Super Mini App` → URL `https://student-assistant-telegram-bot.onrender.com/app`. This is a BotFather configuration, not a code change.

## Diagnose "Access unavailable"

Once deployed, open `/superapp` in Telegram and use Render → Logs to search for:

`V12 login denied:`

Values include `expired_telegram_login`, `invalid_telegram_signature`, `missing_signed_user_or_timestamp`, `missing_telegram_initdata`, or `invalid_telegram_login`.

Do **not** paste the bot token, signed `tgWebAppData`, `initData`, Telegram login code, `.env`, or any query string containing sensitive data. Share only the reason code and/or ordinary HTTP status. If the reason is `invalid_telegram_signature`, inspect whether the registered `BOT_TOKEN` matches the bot that opened the Mini App; do not bypass verification. Some browser clients fail to provide signed data, in which case the correct action is to use an officially supported Telegram Mini App launch path.

## Commit only these reviewed files

```powershell
git add -- navigation.py friendly_v119.py super_miniapp_v120_launch.py super_miniapp_v120.py INSTALL_V120_ACCESS_MENU_FIX.py TEST_V120_ACCESS_MENU_FIX.py
git diff --cached --check
git diff --cached --stat
git diff --cached -- navigation.py friendly_v119.py super_miniapp_v120_launch.py super_miniapp_v120.py
git commit -m "Fix V12 Super Mini App navigation buttons and auth diagnostics"
git push origin main
```

Do not use `git add .`. Keep V12 public launch **off** until a valid adult account successfully opens `/app` and full tests pass. For emergency rollback, set `SUPER_MINIAPP_V120_ENABLED=false` and `SUPER_MINIAPP_V120_LAUNCH_ENABLED=false` and deploy. Other bot features are not impacted.
