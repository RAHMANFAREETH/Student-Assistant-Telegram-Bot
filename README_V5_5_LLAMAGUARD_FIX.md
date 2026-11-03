# Student Assistant Telegram Bot V5.5 — Llama Guard Response HTTP 400 Fix

## Confirmed from Render logs

- `@cf/meta/llama-guard-3-8b` (student-input moderation) -> HTTP 200
- `@cf/qwen/qwen3-30b-a3b-fp8` (generate answer) -> HTTP 200
- `@cf/meta/llama-guard-3-8b` (answer moderation) -> HTTP 400

### Cause

`_check_safety(answer, response=True)` used to send an **assistant-only** message to Llama Guard 3. Cloudflare's model requires alternating `user` and `assistant` roles. An output moderation request must be given as two messages: `{role:"user",content:<the student's question>}` followed by `{role:"assistant",content:<the generated answer>}`.

Official Cloudflare changelog, 2025-03-17: https://developers.cloudflare.com/workers-ai/changelog/

### Fix

- Input moderation remains one `user` message.
- Output moderation now sends `[user original_question, assistant generated_answer]`.
- Safety moderation continues to fail closed if a model error occurs or the original question is unavailable. **Do not remove the safety checks.**
- No other Student Assistant modules were modified.

## Install (existing `C:\Users\Pros\Desktop\StudentAssistantBot`)

1. Back up the existing `ai_study_assistant.py`.
2. Copy the `ai_study_assistant.py` in this ZIP into your existing bot folder; replace only this file.
3. Optionally copy the four `TEST_V5_5_*.py` test files into the same folder. The additional test file is `TEST_V5_5_LLAMAGUARD_FIX.py`.
4. From VS Code PowerShell:

```powershell
python -m py_compile ai_study_assistant.py
python -m unittest TEST_V5_5_AI.py TEST_V5_5_DIAGNOSTICS.py TEST_V5_5_HTTP400.py TEST_V5_5_LLAMAGUARD_FIX.py -v
```

5. Review then deploy:

```powershell
git status
git diff -- ai_study_assistant.py
git add ai_study_assistant.py
git commit -m "Fix Cloudflare Llama Guard response format"
git push origin main
```

6. Confirm Render deployed the new commit. Test `/ai` > Ask Question > `Explain photosynthesis in Tamil`.

Expected Render model status sequence: `Llama Guard 200` -> `Qwen3 200` -> `Llama Guard 200`. A successful response is expected, but only a live run confirms it. If the final status remains 400, provide the `Cloudflare AI error codes:` log line as well.

No SQL change or new API keys are needed. Do not replace `.env`, `main.py`, `navigation.py`, `translate.py`, `translation_ocr.py`, or `speech_to_text.py`.

## Child safety and provider policies

The code's Llama Guard classifier is an imperfect safeguard and should not be considered a complete age-appropriate content policy. Review the provider/model terms, privacy, and child safety requirements before treating this as suitable for public/mixed-age student deployment.
