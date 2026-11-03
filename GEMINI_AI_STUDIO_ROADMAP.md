# Google AI Studio / Gemini — project continuity note

The user wants Gemini 3.1 Flash Lite alongside the existing Cloudflare AI. **Do not forget this goal.**

V5.8 adds study achievements only; it neither uses nor changes either AI provider.

The existing Student Assistant Bot serves a mixed-age audience, including possible O/L and A/L minors. Google Gemini API Terms restrict use in applications likely accessed by under-18 users. Adding Gemini to the public mixed-age bot without appropriate legal and access review is not part of V5.8. A clearly separated, compliant adult-only service may be considered in the future, with proper age controls and privacy protections. An allowlist of Telegram IDs alone does not verify adult age.

For the student-facing bot today, preserve the working Cloudflare AI integration while assessing the provider/model's suitability, student safety, costs and privacy. Don't upload Gemini API keys or Cloudflare tokens to GitHub.
