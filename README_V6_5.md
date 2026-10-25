# Student Assistant Bot V6.5 — Save AI Study Material

**This package upgrades your existing V6.4 Student Assistant Telegram Bot.** It does not create a new bot, change webhook routes, change your Cloudflare provider, or activate Gemini for student messages.

## What changes

In the **private** `/ai` study conversation, two buttons appear after selecting a learning mode:

- **💾 Save AI Answer** — Save the last complete AI reply to your existing Supabase `notes` table, using a short title based on the study question.
- **🗂 Save AI Quiz** — Parse the last AI reply as 1–5 MCQs with exactly four A–D choices and a numbered answer key. Save each verified-format MCQ as one record in the existing `flashcards` table. Cards default to **No Subject**, as the existing flashcard workflow supports.

These actions **preview and require ✅ Confirm Save** or ❌ Cancel Save. Nothing is written during preview; a save does not call Cloudflare or consume additional AI quota. An AI call that generated the answer/quiz still consumes the existing daily quota. A duplicate save of the same answer is blocked within the current session.

### Study workflow

1. Start `/ai` in the private bot chat and select **💬 Ask Question** or **📝 Generate Quiz**.
2. Ask a study question or request 3 MCQs with `1. Question` and `A) ...` to `D) ...`, followed by an `Answer Key:` section containing `1. B`, `2. A`, etc.
3. Once a successful AI reply finishes, press **💾 Save AI Answer** or **🗂 Save AI Quiz**.
4. Review the preview, then **✅ Confirm Save**. Review the saved content via **📝 Notes → 📚 View Notes** or **🧠 Flashcards → 📚 My Flashcards**. You can re-study a saved note in your existing `/asknotes` workflow.

**Accuracy:** Answer-key parsing checks the *format*, not factual correctness. Verify AI answers before relying on them. If the quiz format is ambiguous, nothing is saved. Regenerate a well-structured quiz and retry.

**Privacy:** Only private Telegram chats can access the AI study session. Saving is scoped to the logged-in Telegram user ID. The AI reply is kept temporarily in the existing in-memory session before you explicitly choose to save. After confirmation, the selected material is stored in Supabase and persists like your existing Notes/Flashcards. The saved answer can contain information from your question, so do not save private personal information. Existing session expiration and reset behavior applies. This release limits saving to replies of 20,000 characters or fewer.

**Compatibility:** No new Supabase SQL, tables, API keys, or Render environment variables. Cloudflare, Llama Guard, Gemini developer tools, quota, AI operations, `/aihealth`, V6.3 follow-up buttons, and V6.4 study tools remain unchanged.

## Install on Windows / VS Code

1. Back up your existing `C:\Users\Pros\Desktop\StudentAssistantBot` directory, or at least `ai_study_assistant.py`. Do **not** upload or commit `.env`/API keys.
2. Extract the ZIP and copy **all five files at its root** directly into that existing bot directory:
   - `ai_save_v65.py`
   - `INSTALL_V6_5.py`
   - `TEST_V6_5_SAVE_STUDY.py`
   - `FIXTURE_V6_4_AI.txt` (offline test fixture only; NOT used by the live bot)
   - `README_V6_5.md`
3. In the VS Code PowerShell terminal, run:

```powershell
Test-Path .\INSTALL_V6_5.py
Test-Path .\ai_save_v65.py
Test-Path .\TEST_V6_5_SAVE_STUDY.py
Test-Path .\FIXTURE_V6_4_AI.txt
python -m unittest TEST_V6_5_SAVE_STUDY.py -v
python INSTALL_V6_5.py
python -m py_compile ai_study_assistant.py ai_save_v65.py
python -m unittest TEST_V6_5_SAVE_STUDY.py TEST_V6_4_STUDY_TOOLS.py -v
```

The four Test-Path checks should return `True`. The installer requires the expected V6.4 structure; it refuses to change unfamiliar code. It makes a backup named `ai_study_assistant.py.before_v65.bak` and is idempotent. The offline V6.5+V6.4 suites passed **42 tests** in the reconstructed project fixture. Your Windows installation and live Supabase connection still require verification.

If installed and your older test suites remain available, you can also run:

```powershell
python -m unittest TEST_V6_3_FOLLOW_UPS.py TEST_V6_2_RELIABILITY.py TEST_V6_1_GEMINI_RENDER.py TEST_V6_0_AI_OPS.py TEST_V5_9_GEMINI.py -v
```

After all available tests pass:

```powershell
git add ai_study_assistant.py ai_save_v65.py INSTALL_V6_5.py TEST_V6_5_SAVE_STUDY.py FIXTURE_V6_4_AI.txt README_V6_5.md
git commit -m "Add V6.5 confirmed AI notes and flashcard saving"
git push origin main
```

Make sure your Render deployment is **Live** and test using a *new AI reply generated after the deploy*, as old temporary sessions do not survive a restart.

## Limitations / errors

- A free-form quiz answer that does not contain clearly formatted numbered A–D questions **and** a numbered answer key cannot be saved as flashcards automatically. Use **💾 Save AI Answer** to keep the text as a note or regenerate the quiz in the requested format.
- The model may give the wrong correct option. You should verify the flashcards after saving.
- The user is asked to confirm every write; however, network timeouts are ambiguous. If the bot says it cannot verify a save, check your existing Notes/Flashcards before trying again to avoid duplicates.
- No subject assignment or flashcard editing is added here. Saved cards appear under **No Subject**.
- Only the most recent successful AI reply in the current live private chat session can be saved. Older replies and chat history are not persisted automatically.
- If a different live code version or manual modifications have changed V6.4 anchors, the installer intentionally refuses to apply the patch; keep your original files unchanged and review the mismatch.

## Roll back V6.5

If needed, restore the installer backup to recover V6.4 functionality without touching existing Supabase records:

```powershell
Copy-Item .\ai_study_assistant.py.before_v65.bak .\ai_study_assistant.py -Force
python -m py_compile ai_study_assistant.py
git add ai_study_assistant.py
git commit -m "Revert V6.5 AI save controls"
git push origin main
```

**Important:** Rollback does not delete notes/flashcards that were already saved. Existing Cloudflare and Gemini configurations remain unchanged.
