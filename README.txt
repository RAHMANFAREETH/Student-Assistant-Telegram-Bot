V8.0 Combined Regression Test Fix 2 — keyboard button representation

Why: The earlier fix made tests accept both .keyboard and .rows. Your local Telegram keyboard currently supplies dicts for individual buttons, so the tests still fail on b.text. The new fix also supports dict-shaped buttons.

1. Extract this ZIP.
2. Copy FIX_V8_KEYBOARD_LABELS.py into StudentAssistantBot, next to TEST_V7_13_IMAGE_FILTERS.py and TEST_V7_14_AUTO_CROP.py.
3. Run:
   python FIX_V8_KEYBOARD_LABELS.py --check
   python FIX_V8_KEYBOARD_LABELS.py --apply
4. Re-run:
   python -m unittest TEST_V8_STUDY_LAB TEST_V7_17_ADVANCED_PDF TEST_V7_13_OFFICE_PDF TEST_V7_15_PHOTO_CROP TEST_V7_16_DOCUMENT_SCANNER TEST_V7_14_ENGINE_COMPAT TEST_V7_14_AUTO_CROP TEST_V7_13_IMAGE_FILTERS -q

Expected: 209 tests, OK (skipped=2), assuming no other differences.

Changes made: ONLY two TEST_*.py files; it creates backup files locally. No production Telegram menu, PDF engine, Render environment, or Supabase data is modified.

No push until full suite finishes OK. Avoid git add . to prevent committing backups or environment files.
