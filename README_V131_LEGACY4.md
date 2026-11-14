# Student Assistant V13.1 — Four-Language Legacy Conversion (additive prototype)

This package is an opt-in local-only **Font & Writing Studio panel**. It **does not** modify the current 80 font names, Tamil mappings, Telegram authentication, PDF rendering logic, database, or Render deployment.

## What works now

| Language | Format | Direction | Important limitation |
|---|---|---|---|
| Tamil | Unicode / Bamini / SunTommy | Existing bidirectional text mappings | Existing engine remains unchanged; does not add Kalaham/Vanavil |
| Arabic | UTF-8, Windows-1256, ISO-8859-6 | Both directions as **byte-accurate .txt** | They are old character sets, **not** Sakkal Majalla font transformations |
| English | UTF-8, Windows-1252, Macintosh Roman | Both directions as **byte-accurate .txt** | They are old character sets, **not** Times New Roman or Calibri |
| Sinhala | Unicode / a selected legacy Sinhala font map | Bidirectional *only when a sufficiently complete, reviewed mapping JSON is imported* | **No full FM Abhaya/DL mapping included**; incomplete mappings stop visibly; example is not production use |

**Do not claim fully implemented Sinhala legacy conversion based on this package alone.** A properly licensed, tested mapping is needed. Candidate open-source projects to evaluate include `sinhalanorm` (MIT; FM-Abhaya/Damindu decode), `Open-SL/sinhala-unicode-converter` (DL Manel/Kaputa/etc; verify redistribution terms), and `sinhala-font-bridge` (profile format and license notices). Sakkal Majalla, Noto and Iskoola Pota are Unicode fonts and do not need proprietary text encoding conversion. Some legacy fonts require separate mappings and are not aliases.

## Install on existing V13.0 bot

Unzip package contents in the existing project folder (next to `super_miniapp_v122_fonts.html`). It contains an `INSTALL_V131_LEGACY4.py` and `V131_LEGACY4_PAYLOAD/` folder. In PowerShell:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python INSTALL_V131_LEGACY4.py --check
# Read the file list; only continue on CHECK OK
python INSTALL_V131_LEGACY4.py --apply
node --test TEST_V131_LEGACY4.mjs
node --check super_miniapp_v122_fonts.js
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

No font files are shipped. All data conversion happens in the Mini App browser: no text is sent to server, stored, or logged. Only three GET-only static assets are served under existing `SUPER_FONT_STUDIO_V122_ENABLED` and `SUPER_MINIAPP_V120_ENABLED` flags. The existing `/app/api/session` gate remains.

## How to use

Open Font & Writing Studio, select `🌐 Four-language legacy`, then select language, source and target. Tamil works by pasting text. To decode an old Arabic/English `.txt` file, choose its original legacy encoding, select the original file and convert. To encode Unicode into an old byte format, paste text, select target, then Download encoded `.txt` (copy is intentionally disabled for raw bytes). For Sinhala select `Legacy` and load a *complete, verified JSON font mapping* corresponding to the original document; the supplied `sinhala_profile_example_v131.json` is **illustrative only** (maps `l` and `ld`) and will reject normal Sinhala documents.

## Safety and production readiness

- Text pasted as Latin gibberish does not identify a font; choose the source explicitly.
- Converting text to a different legacy encoding doesn't install any matching font.
- The UI uses a byte-accurate roundtrip when possible, blocks unmappable characters instead of replacing them, and limits file sizes.
- Do not deploy until browser QA, actual old-document fixtures, and Unicode rendering tests are completed. No historical test or production feature should be disabled to make it pass.
- This prototype does **not** provide complete four-language legacy conversion. It provides full native codepage support for selected Arabic/English encodings and safe Sinhala profile infrastructure.

See external source background: https://github.com/RavinduPabasara/sinhalanorm, https://github.com/Open-SL/sinhala-unicode-converter, and https://github.com/UDLHS/sinhala-font-bridge .
