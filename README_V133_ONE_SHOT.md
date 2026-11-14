# Student Assistant V13.3 — One coordinated legacy-conversion upgrade (validation branch)

**Scope and honesty:** This package gives your V13.2 Font & Writing Studio a new strict, reviewed-profile converter for legacy Tamil and Sinhala glyph encodings, plus a standalone offline DOCX font audit/Unicode-copy tool and a combined QA workflow. This is one installation; no intermediate V13.3 compatibility patches are needed for an unchanged V13.2 layout. It preserves the V13.2 FM Abhaya importer, Tamil Bamini/SunTommy, Arabic Windows-1256/ISO-8859-6, English Windows-1252/Mac Roman, existing PDF tools, security gates, 68 Mini App tools and 32 Arcade activities.

It **does not** invent Kalaham, Vanavil, Tharmini, FM Malithi, FM Derana or DL-family mappings. These font families are visible as *mapping required*, not as working one-click converters. A valid profile must include a source, rights statement, exact font family, glyph mappings and at least two independently established examples. The user-supplied `provenanceStatus=reviewed` field is a claim, not proof of mapping provenance: an administrator should audit its published source, samples and license before public use. Similar font names may have incompatible glyph encodings.

## One-time installation — Windows (your V13.2 validation branch)

1. Extract the ZIP *contents* next to `super_miniapp_v122_fonts.py` in `C:\Users\Pros\Desktop\StudentAssistantBot`, retaining `V133_PAYLOAD`.
2. `git switch v13-fonts-validation`
3. `python INSTALL_V133_ONESHOT.py --check` (continue only on CHECK OK)
4. `python INSTALL_V133_ONESHOT.py --apply` (backs up modified files, does not deploy or push)
5. Run the included single test orchestrator: `powershell -ExecutionPolicy Bypass -File .\RUN_V133_ALL_TESTS.ps1`, or run these individual commands:

```powershell
node --test TEST_V133_VERIFIED_PROFILES.mjs
python -X utf8 -m unittest TEST_V133_DOCX_AUDIT TEST_V133_ROUTE_INTEGRATION -q
node --test (Get-ChildItem -Filter 'TEST_*.mjs' -File | ForEach-Object FullName)
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

## Using the new tab

Open the existing authenticated Font & Writing Studio, select **🛡️ Reviewed profiles**, pick Tamil or Sinhala and the exact font, then import the reviewed JSON and paste legacy text. Nothing is uploaded: all conversions use browser JavaScript. For Arabic/English byte-accurate text conversions use the separate **Four-language legacy** tab.

The new verified-profile format is `student-legacy-profile-v1`:

```json
{
 "schema":"student-legacy-profile-v1",
 "language":"ta",
 "font":"Kalaham",
 "source":"https://example.invalid/documented-mapping",
 "license":"mapping's exact license",
 "provenanceStatus":"reviewed",
 "direction":"decode",
 "mappings":{"<a real original glyph sequence>":"<verified Unicode Tamil output>"},
 "preprocess":{},
 "samples":[{"legacy":"actual known source text","unicode":"actual verified expected text"},{"legacy":"second independently verified example","unicode":"expected text"}]
}
```

**The example above describes the schema only. It is NOT a Kalaham mapping, and must not be imported unchanged.** The importer rejects missing/mismatched vectors and unmapped text, and never substitutes Unicode characters silently. Reverse conversion is allowed only when explicitly supported, no pre-processing rules are needed, and the mapping has no collisions. Kalaham fonts and other commercial typefaces are **not included**.

## Independently verify a reviewed profile before public release

Prepare a **separate** JSON array of at least five `{"legacy":"...","unicode":"..."}` reference pairs manually checked in an authoritative source or real Word document. Then run:

```powershell
python VERIFY_LEGACY_PROFILE_V133.py "C:\path\reviewed-profile.json" "C:\path\independent-examples.json"
```

This reports all failures; it is not a substitute for inspection of full real assignments.

## Standalone DOCX font audit (safe by default)

To identify explicit legacy-font runs in Word document bodies and tables:

```powershell
python AUDIT_CONVERT_LEGACY_DOCX_V133.py "C:\path\assignment.docx" --audit-json "C:\path\font-audit.json"
```

To create a **separate** Unicode DOCX when you have an audited, exact-font profile:

```powershell
python AUDIT_CONVERT_LEGACY_DOCX_V133.py "C:\path\assignment.docx" --profile "C:\path\reviewed-profile.json" --output "C:\path\assignment-unicode.docx"
```

Caveats: This document converter requires python-docx; it handles *explicit run fonts in document body/table text* only. It refuses inherited font styles, adjacent same-font runs that might split a glyph, fields, drawings, unrecognized encodings, incomplete map coverage, and overwriting the original. It does not process headers/footers/text boxes, and it does not promise faithful page layout or convert Office files directly on Render. Review output in Word before exporting to PDF. No existing Telegram DOCX → PDF handler is changed.

## Cloud verification

This package includes `.github/workflows/v133-legacy-profiles-validation.yml` for the `v13-fonts-validation` branch. It runs browser converter tests using Node 22, offline DOCX tests inside your production Docker image (Python 3.12), and checks the Docker font families. This workflow does not access tokens, start the Telegram bot, deploy or merge `main`.

## Final status and incomplete source work

- Existing Unicode 80-font catalog: preserved. This is *font selection*, not proof each proprietary font is installed.
- Tamil: Bamini/SunTommy remain functioning. Kalaham, Vanavil, Tharmini, Senthamil, Amudham, TAB, TAM and TSCII need reviewed exact maps or a separately licensed proven converter. The Open-Tamil project documents mappings for Vanavil, TAB/TAM/TSCII, but mapping confidence and file-specific redistribution terms must be verified independently: https://github.com/Ezhil-Language-Foundation/open-tamil.
- Sinhala: existing Pandukabhaya FM Abhaya -> Unicode remains; FM Malithi and DL-family profiles need their source-specific mappings and real-document samples. Open-SL documents a DL Manel converter: https://github.com/Open-SL/sinhala-unicode-converter. No names are treated as proof that layouts are interchangeable.
- Arabic: older Windows-1256 / ISO-8859-6 byte encoding handling remains; Sakkal Majalla is a Unicode font needing suitable licensing, not a distinct character encoding.
- English: Windows-1252 / Macintosh Roman byte encoding remains; Times New Roman/Aptos/Arial similarly need no legacy encoding conversion.
- Production Render and Telegram are untouched. Do not deploy until full local, cloud and real legacy-document tests pass.

**Privacy:** No document content or profile mapping is uploaded by the browser. The DOCX helper runs locally. The GitHub workflow uses synthetic fixtures, not real student data.
