# Student Assistant Telegram Bot — V7.11 Text → PDF

## What is new?

Inside **🎙 Voice & PDF → 📄 PDF Tools**, there is a new **📝 Text → PDF** option.
Users can also type `/textpdf` in a **private chat** with the existing bot.

1. Tap 📝 Text → PDF (or send `/textpdf`).
2. Paste/type text in one or several Telegram messages (up to **20,000 characters / 30 messages**).
3. Tap **✅ Create Text PDF**.
4. Download the generated A4 PDF from Telegram. It has selectable/searchable text and automatic page breaks.

**🧹 Clear Text** resets the draft, **❌ Cancel** returns to PDF Tools, and **🏠 Main Menu** exits. The draft is only in the running bot process's memory; it is **not** saved to Supabase. Restarting Render loses unfinished drafts. PDFs are returned directly to the user's private chat.

## Requirements and languages

- Plain text (including line breaks), **English, Tamil, Sinhala and Arabic**.
- `fpdf2` and `uharfbuzz` are added to the existing `requirements.txt`. HarfBuzz is required for correct Tamil/Sinhala/Arabic ligatures and right-to-left layout.
- On the bot server, four **Noto Sans** Unicode font files are required. They are downloaded **at build time** by `INSTALL_TEXT_PDF_FONTS.py`, and intentionally **not included in this ZIP**. Some emojis may not display; this is a text document converter.
- No new bot, Render service, AI API, SQL, or secret environment variable is required.
- The existing Merge, Extract, Images to PDF, Rotate, and Protect handlers are not changed.

## 1. Install locally in VS Code (PowerShell)

1. Keep your current bot folder and make a Git commit/backup before upgrading.
2. Extract this ZIP. Copy **`INSTALL_V7_11.py`** and the whole **`V711_FILES`** folder into your current `StudentAssistantBot` folder (beside `main.py`).
3. From the root of that folder, run:

```powershell
python INSTALL_V7_11.py --dry-run
python INSTALL_V7_11.py
python -m pip install -r requirements.txt
python INSTALL_TEXT_PDF_FONTS.py
python -m unittest TEST_V7_11_TEXT_PDF.py -v
python -m py_compile main.py pdf_tools.py navigation.py text_pdf_v711.py
```

If the installer says **`pdf_tools.py differs from the reviewed V7.9 source`**, stop. Do **not** force-overwrite your code: it means we need to adapt the patch to your newer `pdf_tools.py`.

The font setup needs internet access during installation. `pdf_fonts/` is gitignored; it is an installation artifact, not source code.

## 2. Deploy to the SAME Render Web Service

In the existing Render service, update **Build Command** from:

```text
pip install -r requirements.txt
```

to:

```text
pip install -r requirements.txt && python INSTALL_TEXT_PDF_FONTS.py
```

**Keep the current Start Command unchanged**, e.g. `gunicorn main:app --bind 0.0.0.0:$PORT`.

You do **not** need new Environment Variables. The optional `TEXT_PDF_FONT_DIR` is only for custom font locations.

Once the local tests pass:

```powershell
git add pdf_tools.py navigation.py requirements.txt .gitignore text_pdf_v711.py INSTALL_TEXT_PDF_FONTS.py TEST_V7_11_TEXT_PDF.py INSTALL_V7_11.py
git commit -m "V7.11 add multilingual text-to-PDF tool"
git push origin main
```

Wait for Render to finish deploying. Check the Render build log for **`Unicode PDF fonts ready`**. Then test in Telegram (private chat):

`/start` → `🎙 Voice & PDF` → `📄 PDF Tools` → `📝 Text → PDF`, or send `/textpdf` directly. Try an English paragraph, then a separate Tamil, Sinhala, and Arabic sample and inspect their letter shaping in the resulting PDF.

## Safety, rollback, limits

- The installer works offline and **does not contact Render, Telegram, or Supabase**.
- It refuses to overwrite an unrecognized or locally edited `pdf_tools.py`.
- It creates `.v711_backup/` and may be reverted before later edits:

```powershell
python INSTALL_V7_11.py --rollback
```

- **20,000 characters** and **30 text messages** maximum per draft. Plain text only; files and images are not accepted in this mode.
- This is a **private-chat-only** tool because it holds an in-memory draft scoped to a chat ID.
- Users can send multiple messages but the bot process must stay running until they tap Create. The font files are local to Render and are installed on each build.
- The installer does not alter your `main.py`, database schema, AI provider settings, or any existing PDF operation.
- The PDF creator is not an AI-powered formatting service; it preserves plain text with basic headings, line breaks and paginated A4 layout.
- **Important:** Tests are offline. English searchable PDF output and 21 local tests were verified; multilingual *live Render* output still needs verification after installing HarfBuzz and Noto fonts.
