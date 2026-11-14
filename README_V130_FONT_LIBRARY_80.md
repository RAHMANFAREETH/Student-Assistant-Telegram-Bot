# Student Assistant V13.0 — 80 Unicode Font Choices + Legacy Guard + Telegram PDF Tools

This **add-on** extends the existing Student Assistant V13.0 Bot and Mini App. It is not a replacement bot. The ZIP contains the prior guarded four-language PDF Tools + Studio package and the new consolidated `INSTALL_V130_FONT_LIBRARY_80.py` installer. **Use ONLY that consolidated installer.**

## Verified scope

- **80 Unicode font-name choices** in the Studio: 18 Tamil, 26 English, 26 Arabic and 10 Sinhala, with search and academic/modern/decorative category filters. The full list is in `V130_FONT_LIBRARY_PAYLOAD/font_catalog_v130.json`.
- **25 separately labelled legacy font names** (15 Tamil, 10 Sinhala) in an information guide, not falsely offered as Unicode encoding conversion.
- Arabic's first academic choice is **Sakkal Majalla**; other essential options include Arabic Typesetting, Traditional Arabic, Amiri, Scheherazade New and Noto Naskh Arabic.
- Tamil options include Latha, Vijaya, Nirmala UI, Noto Tamil, Tiro Tamil, Catamaran and other Tamil Unicode families.
- Sinhala options include Iskoola Pota, Abhaya Libre, Noto Sinhala, Yaldevi, Gemunu Libre and other known families.
- English options include Times New Roman, Arial, Calibri, Aptos, Cambria, Georgia and others.
- Existing **Unicode ↔ Bamini ↔ SunTommy** conversion is retained as-is; unrelated unsupported legacy encodings are not guessed.
- Existing Telegram **PDF Tools → 🌍 Font & Writing Studio**, `/fontstudio` and `/fonts` launch routes are retained / installed if not already available.
- The converter continues to reject known *missing legacy Tamil/Sinhala fonts* before generating misleading PDFs; a new targeted exact-font preflight additionally detects missing **Sakkal Majalla, Arabic Typesetting, Traditional Arabic and Iskoola Pota** when explicitly used in active text/styles.
- The Studio previews text **locally on the device**. The preview does not install fonts or prove they exist in Render. A browser may substitute a font without warning from the OS.

### Critically important limitations

**The catalog lists font families; it does not bundle, install, license, or guarantee rendering of all 80 fonts.** Exact rendering requires the font installed on the relevant browser **and on the PDF conversion server**. Fonts included with Microsoft products generally cannot simply be copied to Render without an appropriate server/distribution license. No proprietary `.ttf`/`.otf` binaries are included. Never commit personal `.env`, keys or unlicensed font binaries.

The font preflight examines DOCX/PPTX direct run declarations and used Word styles. It cannot fully resolve **theme fonts**, all inherited slide layouts, or guarantee complex-script shaping and page layout. Review converted PDFs visually; for exact academic formatting, export directly from Word where the licensed font is present.

`OFFICE_EXACT_FONT_POLICY` options:

- `priority` (**default**): reject conversion if any of four high-impact Unicode families named above is explicitly requested but not installed/verified. The legacy-font guard runs separately regardless.
- `catalog`: additionally require **exact installation of all explicitly referenced fonts that appear in the 80-name catalog**. This is strict and may reject many ordinary documents on Render.
- `off`: disable **the new Unicode exact-font check only**. Legacy font checks remain active. This can permit silent Unicode font substitution; use only as an informed operational choice.

## Windows installation

1. Copy the ZIP contents **into** your existing `C:\Users\Pros\Desktop\StudentAssistantBot` project directory (same folder containing `main.py` and `Dockerfile`). Preserve `V130_*_PAYLOAD` directories. Do **not** replace your project with this ZIP.
2. In PowerShell:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python INSTALL_V130_FONT_LIBRARY_80.py --check
```

Only if it says `CHECK OK`:

```powershell
python INSTALL_V130_FONT_LIBRARY_80.py --apply
python -m py_compile office_to_pdf_v713.py office_legacy_fonts_v130.py office_font_catalog_v130.py pdf_fontstudio_v130.py
python -X utf8 -m unittest TEST_V130_FONT_LIBRARY TEST_V130_MULTIFONT TEST_V130_FOUR_LANGUAGES TEST_V130_PDF_FONT_STUDIO -q
node --test TEST_V130_FONT_LIBRARY.mjs TEST_V122_FONT_STUDIO.mjs
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

3. Check fonts on your Windows laptop (read-only):

```powershell
.\CHECK_WINDOWS_FONTS_V130.ps1
python office_font_catalog_v130.py --file "C:\path\to\your\document.docx"
```

4. The installer backs up modified files in `V130_80_FONT_BACKUP_<timestamp>` and refuses unfamiliar layouts/customized earlier files. **Never bypass `SAFE STOP` by blindly overwriting files.** To roll back, restore backed-up files and remove only newly-added add-on modules.

5. Only after all tests pass, manually review Git diffs (`git diff --check`, `git status --short`), stage **only intended source files**, rebuild the Docker image, and test from real Telegram Android. Do not run `git add .` in a project with old backups or secrets.

## Runtime verification

- Open PDF Tools → Font & Writing Studio; select Arabic and verify **Sakkal Majalla** is the first academic option. Its actual appearance depends on device installation.
- Switch to Tamil, English and Sinhala; check font search, category filter, Unicode text copy/download, and Arabic RTL text rendering.
- Check Tamil Bamini/SunTommy round-trip tests in the existing conversion tab.
- Convert known Unicode DOCX/PPTX documents. Compare page count, text shaping, headers, tables and spacing with their source documents.
- Test a document using Sakkal Majalla on Render: without a licensed server installation, the bot should issue a clear missing-font error, not claim it has faithfully rendered the document.
- Confirm Book Library, all PDF operations and private user-data access remain intact. Do not deploy until full regression passes.

## Local isolated testing completed

Using the uploaded V13.0 candidate source, the patch passed its initial compatibility check, installed successfully, and was idempotent on recheck. **51/51 focused Python tests** and **28/28 JavaScript tests** passed. A four-language DOCX was converted with locally available Noto fonts via LibreOffice; the output PDF's text was extracted and its rendered page inspected. **The full existing bot regression, Docker build and Telegram Android live tests have not yet been run against your Windows project or Render.**

## License/reference context

- Sakkal Majalla is a Microsoft-family font (`Majalla.ttf`/`Majallab.ttf`) and requires separate licensing consideration for server distribution: https://learn.microsoft.com/typography/font-list/sakkal-majalla
- Windows supplemental-font families: https://learn.microsoft.com/typography/fonts/windows_11_font_list
- Sinhala Unicode vs older encodings: https://icta.lk/icta-assets/uploads/2016/01/1090_Guide%20to%20creating%20Sinhala%20and%20Tamil%20Unicode%20fonts.pdf
- Font-specific licensing must be verified at each actual font source. A catalog label is not a license grant.
