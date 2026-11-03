-- V9.1 — short-lived provider sessions. Does not modify existing user data.
-- The server grants access only after querying a real provider result.
CREATE TABLE IF NOT EXISTS public.study_age_sessions (
    user_id BIGINT PRIMARY KEY,
    session_id UUID NOT NULL UNIQUE,
    reference_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending'
      CHECK (status IN ('pending','complete','failed','expired')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    daily_count INTEGER NOT NULL DEFAULT 0 CHECK (daily_count BETWEEN 0 AND 3),
    count_date DATE NOT NULL DEFAULT CURRENT_DATE,
    CHECK (expires_at > created_at)
);
CREATE INDEX IF NOT EXISTS study_age_sessions_expires_idx
    ON public.study_age_sessions(expires_at);
ALTER TABLE public.study_age_sessions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.study_age_sessions FROM anon, authenticated;
-- Do not create public RLS policies. Access only through server service-role.
-- Existing public.study_verified_adults must already exist from SQL_V9_ADULT_ACCESS.sql.
