# Student Assistant — Gemini 3.1 Flash-Lite companion (restricted 18+ pilot)

## Why this is separate from your existing Telegram bot
Your working V5.5 public bot already uses Cloudflare AI. **Do not replace its `main.py`, its `ai_study_assistant.py`, or its Render Environment**. Google's Gemini API Additional Terms (effective March 23, 2026) prohibit using the API as part of an application directed to or likely accessed by people under 18. Your public Student Assistant Bot serves O/L and A/L students, so it is a mixed-age service. This ZIP is a **separate, limited-access bot for verified adult participants**, and must not be deployed on your existing public bot service. An allowlisted Telegram ID by itself is *not* proof of adult age; verify eligibility before granting access. Read the provider terms before going live.

Sources: https://ai.google.dev/gemini-api/terms , https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite , https://ai.google.dev/gemini-api/docs/rate-limits

## What's included
- `main.py`: an independent Telegram + Flask webhook bot.
- `gemini_engine.py`: Google Gemini 3.1 Flash-Lite REST integration with chat history, allowlist and pilot usage controls.
- `requirements.txt`, `.env.example`, `.gitignore`, `test_gemini_engine.py`.

Uses **no new Supabase tables** and does not modify the public StudentAssistantBot in any way. The free Google API can process personal data for product improvement. Do not submit private student notes, identities, passwords or confidential content.

## Setup
1. In Telegram BotFather, create a **new, separate bot** for the restricted adult group. Do not reuse your existing public bot's token or webhook.
2. Create a **new folder/repository** for this ZIP. Don't extract these files over the existing `StudentAssistantBot` folder.
3. Install Python dependencies in a virtualenv: `pip install -r requirements.txt`.
4. Run `python -m unittest -v test_gemini_engine.py` and `python -m py_compile main.py gemini_engine.py`.
5. Push this **separate** project to a **new private GitHub repository**. Confirm `.env` is never committed.
6. Create a **separate Render Web Service** connected to that repository, with Build: `pip install -r requirements.txt` and Start: `gunicorn main:app --workers 1 --threads 4 --bind 0.0.0.0:$PORT`.
7. Set these Render Environment variables:
   - `BOT_TOKEN`: new separate BotFather bot token.
   - `WEBHOOK_SECRET`: a randomly generated secret token, 16–256 characters, ASCII letters/numbers/underscore/hyphen only.
   - `GEMINI_API_KEY`: your private Google AI Studio key.
   - `GEMINI_ENABLED=false` **until** the deployment is restricted and participant age/eligibility review is complete.
   - `GEMINI_ADULT_USER_IDS`: comma-separated user IDs of **verified adult testers**. Public flag is deliberately not supported.
   - `GEMINI_DAILY_LIMIT=8`, `GEMINI_SHARED_DAILY_LIMIT=100`, `GEMINI_SHARED_MINUTE_LIMIT=8`.
8. Confirm the new Render service deploys and the new Telegram bot is responding. When suitable adult-only conditions are established, set `GEMINI_ENABLED=true` in this **separate** Render service.
9. Open the new bot: `/start`, ask `Explain photosynthesis in Tamil`, use `/quota`, then `/clear`. Test Sinhala, Arabic, maths, quizzes.

**Safety & operational limits**:
- No reliable age verification system is included. An account list is only an access control, not age verification.
- Usage limits and chat history are **in memory**; restart, scaling or multiple workers reset them. This is a small pilot, not a public quota solution. For production, use Supabase atomic quota tracking.
- AI API requests are sent to Google and may be used to improve services on the free tier.
- The model is not unlimited or guaranteed to be free indefinitely. Quotas are project-wide.
- To keep existing V5.5 stable, do not copy these files into the public bot project or push to its repo.
- This bot is intentionally distinct; it does not read notes or PDFs from your main student bot.
