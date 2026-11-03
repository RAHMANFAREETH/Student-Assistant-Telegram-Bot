STUDENT ASSISTANT BOT — STUDY MATERIALS UPLOAD FIX

Cause found in public GitHub main branch (2026-10-25):
translate.py registers a document handler without an active-translation-state filter.
Because Translation is registered before Study Materials in main.py, the
unrestricted handler swallows files even while Study Materials is waiting for one.

This fix makes the translation handler match only when actively translating a
document or OCR image. It preserves Translate, Study Materials, Cloudflare,
Gemini developer client, the Notes library and all databases.

Instructions:
1. Back up your current project, then copy FIX_DOCUMENT_ROUTING.py and
   TEST_DOCUMENT_ROUTING_FIX.py into the folder containing translate.py.
2. Run in VS Code PowerShell:
   python -m unittest TEST_DOCUMENT_ROUTING_FIX.py -v
   python FIX_DOCUMENT_ROUTING.py
   python -m py_compile translate.py study_materials.py main.py
3. Commit only the modified translate.py and optional fix tools:
   git add translate.py FIX_DOCUMENT_ROUTING.py TEST_DOCUMENT_ROUTING_FIX.py
   git commit -m "Fix document upload handler collision"
   git push origin main
4. After Render deployment is Live, choose Study Materials > Add Material >
   No Subject and upload a fresh TXT. It should immediately show "Reading study
   material..." and then "Study material saved!" or a specific error.

The installer makes a timestamped backup. If the file already has a different
custom document handler, it stops without changing the file. No SQL/API keys.
