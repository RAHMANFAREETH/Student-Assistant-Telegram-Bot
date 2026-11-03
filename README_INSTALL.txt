STUDENT ASSISTANT BOT V5.5 — CLOUDFLARE REPLACEMENT FILES
==========================================================

This ZIP contains:
  ai_study_assistant.py    New Cloudflare AI handler (copy to your project)
  INSTALL_V5_5.py          RECOMMENDED safe patcher (copy to your project)
  SQL_V5_5_AI.sql          Supabase quota table + atomic function
  TEST_V5_5_AI.py         Offline tests
  main.py                  READY V5.5 from uploaded V5.4 snapshot (optional)
  navigation.py            READY V5.5 from uploaded V5.4 snapshot (optional)
  ENV_CLOUDFLARE_EXAMPLE.txt  Render settings reference ONLY

IMPORTANT: Your bot gained fixes after the V5.4 snapshot (Azure, AssemblyAI,
OCR and possibly blocked-user exception handling). Do NOT blindly replace your
current main.py or navigation.py with the snapshot versions: these files
may overwrite newer changes. Use INSTALL_V5_5.py against your CURRENT folder.
It only adds the required import, handler registration, and main-menu button.
It makes .before_v55.bak backups before touching either file.

INSTALLATION
1. Backup your CURRENT StudentAssistantBot folder before any edits.
2. Copy ONLY ai_study_assistant.py, INSTALL_V5_5.py, SQL_V5_5_AI.sql,
   TEST_V5_5_AI.py into your existing project folder.
3. Run SQL_V5_5_AI.sql in your existing Supabase SQL Editor if not done.
4. From VS Code PowerShell terminal in StudentAssistantBot, run:
     python INSTALL_V5_5.py
     python -m py_compile main.py navigation.py ai_study_assistant.py
     python -m unittest TEST_V5_5_AI.py -v
     git status --short
5. Confirm main.py includes the AI handler and navigation.py has the AI menu:
     Select-String -Path main.py -Pattern register_ai_study_assistant_handlers
     Select-String -Path navigation.py -Pattern 'Ask AI'
6. Add CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN in Render Environment.
   Set AI_ENABLED=true, AI_ALLOW_PUBLIC=false and AI_ALLOWED_USER_IDS to
   a verified adult tester ID for your initial test.
7. After reviewing Cloudflare/model terms, student age/privacy requirements,
   safety procedures and consent where applicable, the module supports public
   access by setting AI_ALLOW_PUBLIC=true. This is an operator decision; it is
   NOT a child-safety certification, and safety filters alone are insufficient.
8. Commit only reviewed source/test/SQL files (never .env or secrets):
     git add main.py navigation.py ai_study_assistant.py INSTALL_V5_5.py SQL_V5_5_AI.sql TEST_V5_5_AI.py
     git diff --cached --check
     git diff --cached --stat
     git commit -m "Add V5.5 Cloudflare AI Study Assistant"
     git push origin main
9. On Render (Live), test Telegram: /start -> 🤖 Ask AI -> 📖 Explain Topic
   Ask: "Explain photosynthesis in Tamil". Then test /aistats and /aiclear.
   Also verify Translation, OCR, Voice Notes and Flashcards still work.

NOTES
- This Cloudflare AI feature is NOT Gemini AI. Do not use Gemini as the
  provider for a public mixed-age Student Assistant bot.
- /ai works only in private Telegram chats, not groups.
- Daily per-user cap defaults to 8. Workers AI has an account-wide free quota.
- The offline tests simulate Cloudflare and Supabase; live API tests are required.
- Do not commit your .env, keys, backup files, or the untrusted older project ZIP.
