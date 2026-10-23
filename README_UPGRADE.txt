TRANSLATOR V3 SETUP

1. Run supabase_translation_history.sql in Supabase SQL Editor.

2. Add to requirements.txt:
gTTS
python-docx
requests

3. Add OCR key:
OCR_SPACE_API_KEY=YOUR_REAL_KEY

Add the same key in Render > Environment.

4. Copy into project root:
translate.py
translation_history.py
translation_tts.py
translation_documents.py
translation_ocr.py

5. main.py does not need changing if it already contains:
register_translation_handlers(bot, show_main_menu)

6. Push:
git add .
git commit -m "Add Translator V3 features"
git push

Test:
- normal translation
- history
- Listen button
- TXT
- PDF
- DOCX
- OCR image
- scanned PDF
