# Gemini 3.1 Flash-Lite — separate restricted 18+ professional Telegram pilot

**Goal:** Keep the EXISTING public Student Assistant Bot and Cloudflare AI intact. Add a **separate restricted adult professional pilot** to the **same GitHub repository**, but as a **different Telegram bot and Render web service**. Nothing in this folder is registered with your public bot.

Google Gemini API Additional Terms (effective March 23, 2026) say you must be at least 18 and must not use the API in an app directed to or likely accessed by people under 18. They also describe Gemini API / AI Studio as for developer professional/business use, not consumer use. **This package is not suitable for broad public student access.** Confirm eligibility and applicable provider requirements independently before inviting anyone. An allowlist alone does **not** verify adulthood. No age-verification system is included.

Official: https://ai.google.dev/gemini-api/terms , https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite , https://ai.google.dev/gemini-api/docs/available-regions .

## 1. Contents

- `app.py`: independent Flask webhook receiver on `/telegram-gemini-webhook`, with Telegram secret header verification and health endpoint `/health`.
- `adult_pilot.py`: private-chat restriction, vetted user-ID allowlist, request quotas, multilingual modes and chat handlers.
- `gemini_ai_studio_v59.py`: the same tested Gemini 3.1 Flash-Lite REST client from V5.9 (stable `gemini-3.1-flash-lite`).
- `requirements.txt`, `.env.example`, `.gitignore`, three offline test files.

### Telegram commands

- `/myid` — show the numeric Telegram ID for manual operator approval (no Gemini request).
- `/start` and `/help` — explain the private professional pilot (only for enabled, allowlisted accounts).
- `/language tamil`, `/language sinhala`, `/language arabic`, `/language english`.
- `/mode ask`, `/mode explain`, `/mode maths`, `/mode quiz`, `/mode language`.
- `/ask Explain this work-related topic` — one question; plain text questions work too.
- `/quota` — local remaining requests, **not Google RPM/RPD**.

No Supabase tables or new APIs. No integration with the public bot's Notes, PDFs, flashcards or user databases. No conversation logs saved by this package; Google and Telegram process messages according to their terms.

## 2. Add the code to your existing GitHub project

From `C:\Users\Pros\Desktop\StudentAssistantBot`, **do not overwrite any existing files**.

1. Download `StudentAssistant_Gemini_Restricted_Adult_Professional_Pilot.zip`.
2. Extract the ZIP **directly into the existing `StudentAssistantBot` folder**. It creates a new folder named `adult_gemini_service`.
3. Confirm both files exist:
   - `adult_gemini_service\app.py`
   - `adult_gemini_service\gemini_ai_studio_v59.py`
4. VS Code PowerShell (at the `StudentAssistantBot` root):

```powershell
python -m unittest discover -s adult_gemini_service -p "test_*.py" -v
python -m py_compile adult_gemini_service\app.py adult_gemini_service\adult_pilot.py adult_gemini_service\gemini_ai_studio_v59.py

git add adult_gemini_service
git commit -m "Add separate restricted Gemini adult professional pilot"
git push origin main
```

The tests need no Gemini key, Telegram token or network connection.

**Do not copy** `app.py` over `main.py`. **Do not alter** the existing Render web service's token, webhook, AI routes or Root Directory.

## 3. Create a separate Telegram bot for the restricted pilot

1. Telegram → [@BotFather](https://t.me/BotFather) → `/newbot`.
2. Create a distinct bot with adult-professional / developer-pilot name and description. Avoid advertising it to children or public school student groups.
3. Copy the new token **only into the separate Render service**. It is `ADULT_GEMINI_BOT_TOKEN`, **NOT** the public Student Assistant `BOT_TOKEN`.

Two bots require two tokens; reusing the existing bot token would override its webhook and interrupt the working student bot.

## 4. Create a second Render Web Service using the SAME repository

[Render Dashboard](https://dashboard.render.com/) → **New → Web Service** → select your existing **Student-Assistant-Telegram-Bot** GitHub repository.

- **Name:** `student-assistant-gemini-adult-pilot` (or any unique available name).
- **Branch:** `main`
- **Root Directory:** `adult_gemini_service` (**critical**; do not set this on the public bot).
- **Runtime:** Python
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app --workers 1 --threads 4 --bind 0.0.0.0:$PORT`

Render docs: https://render.com/docs/monorepo-support . You can connect multiple services to the same GitHub repo with different root directories.

### New service Environment variables

| Key | Value |
|---|---|
| `ADULT_GEMINI_BOT_TOKEN` | **New, different** bot token from @BotFather |
| `ADULT_GEMINI_WEBHOOK_SECRET` | Run the PowerShell command below to generate a secret |
| `ADULT_GEMINI_PUBLIC_URL` | Exact `https://....onrender.com` URL shown for the **new adult service**, with no final slash |
| `GEMINI_API_KEY` | Your Google AI Studio key (set **again in this separate service**; Render variables are not automatically shared) |
| `GEMINI_ENABLED` | **`false` initially** |
| `GEMINI_ADULT_USER_IDS` | **Empty initially** until operator approval |
| `GEMINI_DAILY_LIMIT` | `8` |
| `GEMINI_SHARED_DAILY_LIMIT` | `60` |
| `GEMINI_SHARED_MINUTE_LIMIT` | `5` |

To generate a Telegram webhook secret in local PowerShell (do not paste the result in chat or GitHub):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

The new service's URL might not be known before you create it. If the first deployment says `ADULT_GEMINI_PUBLIC_URL` is missing, copy the URL from the service page, add that environment variable, then redeploy **the new service**. This does not affect the old bot.

### Access activation

1. Keep `GEMINI_ENABLED=false` and the allowlist blank until you have established eligible **18+ professional/developer participants** through an appropriate verification process **outside the bot**. Never ask people to send IDs/passports into Telegram.
2. The new bot's `/myid` command shows each applicant's numeric ID without calling Gemini.
3. Once verification is complete, set `GEMINI_ADULT_USER_IDS=123456789,987654321` (replace example IDs with actually verified adult participant IDs).
4. Set `GEMINI_ENABLED=true` in the **separate** Render service, Save/Deploy. **Do not** change the public service's `AI_ENABLED`, `AI_ALLOW_PUBLIC`, `BOT_TOKEN`, etc.
5. In the **new bot** test `/start`, `/language tamil`, `/mode explain`, then `Explain machine learning for a software developer in Tamil`.
6. Verify an **unlisted Telegram account** and group messages cannot use Gemini.

If unsure whether your planned audience and service comply with Google terms, **keep `GEMINI_ENABLED=false`** and seek provider approval. Do not interpret a typed age confirmation or allowlist as definitive compliance.

## 5. Security and operation

- Separate bot token and webhook; verified Telegram secret header; private chats only; allowlist checked **before each request**; Gemini disabled by default.
- Request max 5,000 characters; responses split for Telegram size constraints.
- Pilot budgets: default 8 calls/account/day UTC, 60 shared calls/day and 5 shared calls/minute. All budgets are **in memory** (reset on service restart; multiple workers have separate counters); **not** the provider's billing/quotas. Keep a single Gunicorn worker. This is not production-ready accounting.
- Google API rate limits, billing and data usage still apply. Some free-tier prompts and outputs may be used by Google to improve products under its terms. Never paste confidential or private/student data.
- Failure responses are sanitized. No automated retries or Cloudflare fallback. Public Student Assistant users continue using Cloudflare AI as before.
- Render free web services can sleep and need warm-up after inactivity.

### Troubleshooting

- **Bot shows no reply:** new Render deployment must be `Live`, new service `ADULT_GEMINI_PUBLIC_URL` must be exact; check new service Logs for webhook errors. `/health` on the adult Render URL should return a small JSON object.
- **Access denied:** ensure eligibility was verified, the account ID was added to the new service's `GEMINI_ADULT_USER_IDS`, and `GEMINI_ENABLED=true`.
- **API 401/403:** Gemini key/region/account permissions; check only the new service environment.
- **API 404:** confirm `gemini-3.1-flash-lite` availability for your API key.
- **API 429:** project-wide Gemini quota or rate limit; quotas are separate from in-memory pilot limits.
- **Public bot stopped replying:** likely a token/webhook mix-up. Restore the public bot's own `BOT_TOKEN` and existing webhook. **Never reuse a Telegram token across these two Render services.**

## Offline verification

`python -m unittest discover -s adult_gemini_service -p "test_*.py" -v`

The tests check request encoding, sanitization, access controls, private-chat gating, quota limits, and absence of any imports from your existing student handlers. No real Telegram or Google network requests are made. **Live deployment has not been tested with your credentials.**
