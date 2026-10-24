# Google AI Studio / Gemini 3.1 Flash Lite — retained project plan

**Not forgotten.** The user wants Gemini AI Studio considered alongside the working Cloudflare AI in the Student Assistant project.

## Current V5.7
- Public mixed-age Telegram Student Assistant: Cloudflare Workers AI + Llama Guard (existing V5.5–V5.6 implementation).
- Google AI Studio Gemini key: **not used by V5.7** and not needed in its Render environment.
- Azure Translator, AssemblyAI, PDF OCR, Flashcards, Supabase and all legacy modules remain unchanged.

## Why not enable Gemini in the current public bot?
Google Gemini API Additional Terms effective March 23, 2026 prohibit API clients directed toward or **likely to be accessed by people under 18**. The existing Student Assistant Bot also serves O/L/A/L students; its audience is not verified 18+ merely because most users are adults. Setting a Telegram allowlist or saying "18+" on a shared public bot does not itself resolve the restriction.

Source: https://ai.google.dev/gemini-api/terms

## Future compliant approach
- Only evaluate Gemini `gemini-3.1-flash-lite` for a **genuinely separate, adult-only deployment** after independent review of usage terms, access restrictions, geographic availability and user-data handling.
- Reuse educational prompt designs and code where appropriate, but use separate authentication/access controls and a separate service. Do not accidentally forward a public student's messages or private academic content to Gemini.
- Google AI Studio free-tier requests are quota limited, not unlimited. Never put `GEMINI_API_KEY` into published code or chats.

**No Gemini request handling or hidden routing was added to the public bot in V5.7.**
