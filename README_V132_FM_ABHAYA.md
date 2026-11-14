# V13.2 FM Abhaya -> Unicode Import Adapter (validation only)

This small additive step makes the **existing V13.1 four-language Studio** accept the original **Pandukabhaya FM Abhaya JSON**. It retains Tamil Unicode/Bamini/SunTommy, Arabic byte encodings, English byte encodings, and custom Sinhala profile import.

- **Working scope:** FM Abhaya legacy text -> Unicode using an original user-imported complete mapping, by applying its preprocessing rules and longest legacy-glyph mapping. This is *not* a binary .DOCX or PDF converter.
- **Not supported:** Unicode -> FM Abhaya; FM Malithi/Derana, DL-MaNel or other Sinhala legacy fonts by name alone; Kalaham or Vanavil Tamil.
- The adapter doesn't bundle any proprietary font, requires no network request when run in the browser, and does not upload typed text.
- The Pandukabhaya mapping file is MIT licensed; actual FM Abhaya font is proprietary. Attribution: https://github.com/akuruAI/pandukabhaya and https://raw.githubusercontent.com/akuruAI/pandukabhaya/main/pandukabhaya/mappings/fm_abhaya.json
- **Mapping not bundled.** Download the original `fm_abhaya.json` from the upstream project and inspect its source/license. The `main` URL can change; review the upstream revision if preparing production releases.

## Install on `v13-fonts-validation`

Extract the package files to the bot's folder, leaving `V132_FM_ABHAYA_PAYLOAD/` in place. Back up your project. `README.txt` changes from old QA ZIP are not part of this change.

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
git switch v13-fonts-validation
python INSTALL_V132_FM_ABHAYA_IMPORT.py --check
# Continue only if CHECK OK
python INSTALL_V132_FM_ABHAYA_IMPORT.py --apply
node --test TEST_V131_LEGACY4.mjs TEST_V132_FM_ABHAYA.mjs
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

## Verify with real MIT mapping

1. Open https://raw.githubusercontent.com/akuruAI/pandukabhaya/main/pandukabhaya/mappings/fm_abhaya.json and save as `fm_abhaya.json` in **Downloads**, not your Git repository.
2. Check on Windows:

```powershell
node VERIFY_V132_FM_SOURCE.mjs "$env:USERPROFILE\Downloads\fm_abhaya.json"
```

3. In local Font & Writing Studio choose `🌐 Four-language legacy`, Sinhala, and upload downloaded JSON to `Verified font mapping JSON` (file stays on device).
4. Select `Legacy` -> `Unicode`, paste `Y%S ,xld`, click Convert. Expect `ශ්‍රී ලංකා`.
5. Verify several real FM Abhaya documents, including vowel sign ordering and punctuation. If actual mapping differs from source, conversion is not reliable for that file.

## Safety

The installer checks for the exact known V13.1 UI baseline and existing feature-gated static routes, aborting on unexpected layouts rather than replacing local customizations. It is idempotent and creates a backup on apply. It does not modify Telegram security, Supabase, PDF conversions, GitHub or Render.

This is a **functional import adapter**, not verified complete Sinhala font support. The real source mapping and live browser tests are still required before considering a production release.
