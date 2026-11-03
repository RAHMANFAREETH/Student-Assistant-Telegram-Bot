# Student Assistant Bot — V12.2 Font & Writing Studio add-on

**Status:** Development add-on for the V12.1 project provided on 2026-11-04. Not deployed. Existing 68 Mini App utilities, 32 Arcade activities, Book Library, bot handlers, Render worker, Supabase tables and user access controls remain unchanged.

## Four standalone tools

1. **Tamil legacy font converter**: Unicode ↔ Bamini ↔ SunTommy (includes cross-conversion), live text, copy, UTF-8 `.txt` download, swap, sample and input warnings. Actual fonts are not bundled; apply matching installed Bamini/SunTommy font in Word or DTP software.
2. **Tamil text cleaner**: NFC normalization, optional removal of zero-width marks, normalization of spaces, optional trim per line.
3. **Unicode inspector**: code-point report (first 70 visible), Tamil code-point count and warnings on invisible characters or unattached vowel signs.
4. **Tamil digits**: `0–9` ↔ `௦–௯` while preserving surrounding text.

All four run entirely in the browser. The page uses the existing `/app/api/session` endpoint for access verification, follows the master V12 feature flag, and uses self-hosted static assets. **No text, documents, passwords or photos are uploaded.** This release adds no external AI/API calls, paid dependencies, or SQL migration.

### Prerequisites

The uploaded project must already have the V12.1 Arcade integration in `super_miniapp_v120.py` and the script tag in `super_miniapp_v120.html`. Run Python, Node.js and the original regression runner in the same existing project directory. The add-on does not install Bamini, SunTommy or another font file.

## Windows PowerShell installation

Extract `V122_Font_Studio_Addon.zip` directly into `C:\Users\Pros\Desktop\StudentAssistantBot` with the folder `V122_FONT_STUDIO_PAYLOAD` intact. Then:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python INSTALL_V122_FONT_STUDIO.py --check
```

Review the diff. It must modify only `super_miniapp_v120.py` and `super_miniapp_v120.html`; new files are independent. Continue only when `CHECK OK` appears:

```powershell
python INSTALL_V122_FONT_STUDIO.py --apply
python -m py_compile super_miniapp_v120.py super_miniapp_v122_fonts.py
node --test TEST_V122_FONT_STUDIO.mjs TEST_V121_ARCADE.mjs
python -X utf8 -m unittest TEST_V122_FONT_STUDIO TEST_V121_ARCADE -q
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

Review test output; do not deploy if anything fails. Existing `.env`, Git and Render settings are not modified by the installer. Installer makes a `V122_FONT_STUDIO_BACKUP_*` folder when it patches the two existing files. A repeated `--apply` is idempotent and refuses to overwrite unexpected pre-existing files.

## Release and live checks

The new independent flag is **`SUPER_FONT_STUDIO_V122_ENABLED=true`** in Render after full testing. The existing `SUPER_MINIAPP_V120_ENABLED=true` must also remain enabled. Restart/redeploy the existing Render service after changing flags. When the new flag is off, Studio routes are not registered and the `/app` entry script fails quietly.

In the bot's Mini App, a new **Font & Writing Studio** shortcut will appear at the top of the tools area. Test Unicode `வணக்கம்` ↔ Bamini `tzf;fk;`, Unicode `தமிழ்` ↔ Bamini `jkpo;`, `சூ` → SunTommy `#`, a zero-width text cleanup, code-point inspection, and Tamil digits. Test in Telegram mobile, plus the existing Book Library, 68 tools, 32 Arcade activities and private task isolation.

### Conversion caveats

- Legacy Bamini/SunTommy font **encoding is not Unicode font styling**. Encoded output appears as Latin keys without the matching legacy font installed. Unicode-only fonts such as Latha and Noto Sans Tamil do not need character conversion.
- Legacy text and ordinary English share the same key positions. The converter cannot reliably identify mixed English words inside raw Bamini text. Convert known legacy regions only, and manually proofread the results.
- A few rare Tamil combinations, typographic variants, and ambiguous SunTommy glyphs may require manual correction. This tool does not claim universal support for TAB, TAM, TSCII, Kalaham, Anjal, proprietary fonts, `.docx` formatting changes, or PDFs. Those require separately verified mappings and file-handling logic.
- NFC and removing zero-width characters can alter deliberate formatting for some languages. Keep an original backup.

### Mapping provenance and attribution

The Bamini/SunTommy mapping tables were adapted into new JavaScript code from **Unicode to Non Unicode**, https://unicodetononunicode.com/data/tamil-mapping.json (CC BY 4.0, reviewed 2026-10-21). The source's provenance also credits the MIT-licensed `ag-sanjjeev/app-tamil-fonts-unicode-converter` and `Pakeetharan/unicode-bamini-converter`. We reorganized mapping facts into a reversible syllable parser, added special ரி/ரீ/ர் handling and Tamil word fixtures, and did not bundle source fonts. CC BY 4.0 license: https://creativecommons.org/licenses/by/4.0/.

## Source control

After local tests pass, stage **only** `super_miniapp_v120.py`, `super_miniapp_v120.html`, the `super_miniapp_v122_*` sources, `TEST_V122_FONT_STUDIO.*`, this README and (if needed for repeatable installation) `INSTALL_V122_FONT_STUDIO.py` plus its payload. Avoid `git add -A`, and never commit backup folders, credentials, `.env`, archive ZIPs or unrelated project changes.

## Rollback

Set `SUPER_FONT_STUDIO_V122_ENABLED=false` and redeploy/restart to disable the Studio without touching V12.1 or earlier tools. The two existing files may be restored from the exact timestamped V12.2 backup only if you are deliberately reverting the source integration.
