-- Optional verified-adult access registry: no destructive operations.
-- This DOES NOT verify age; only a trusted verification provider or
-- properly authorized operator review may write records. Never store ID
-- documents, birthdates, or sensitive verification evidence in this table.
CREATE TABLE IF NOT EXISTS public.study_verified_adults (
    user_id BIGINT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'verified' CHECK (status IN ('verified','revoked')),
    verification_method TEXT NOT NULL CHECK (verification_method IN ('trusted_provider','manual_review')),
    verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ NOT NULL,
    CHECK (valid_until > verified_at)
);
CREATE INDEX IF NOT EXISTS study_verified_adults_valid_until_idx
ON public.study_verified_adults (valid_until);
ALTER TABLE public.study_verified_adults ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.study_verified_adults FROM anon, authenticated;
-- Do not create a public INSERT policy. Store and check the registry
-- only using authenticated server-side Supabase service-role access.
-- Example revocation (run only for an actual user's ID when requested):
-- UPDATE public.study_verified_adults SET status='revoked' WHERE user_id = 123;
