-- V9.1 manual adult access workflow. Run once in Supabase SQL Editor.
-- Requires previously installed public.study_verified_adults table.
-- This migration does not modify or delete existing study data.

CREATE TABLE IF NOT EXISTS public.study_adult_access_requests (
    user_id BIGINT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending'
      CHECK (status IN ('pending', 'approved', 'rejected', 'revoked', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by BIGINT
);
CREATE INDEX IF NOT EXISTS study_adult_access_requests_status_idx
    ON public.study_adult_access_requests (status, created_at);

CREATE TABLE IF NOT EXISTS public.study_adult_access_audit (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL,
    admin_id BIGINT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('approved','rejected','revoked')),
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS study_adult_access_audit_user_idx
    ON public.study_adult_access_audit (user_id, created_at DESC);

ALTER TABLE public.study_adult_access_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.study_adult_access_audit ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.study_adult_access_requests FROM PUBLIC, anon, authenticated;
REVOKE ALL ON public.study_adult_access_audit FROM PUBLIC, anon, authenticated;
GRANT ALL ON public.study_adult_access_requests TO service_role;
GRANT ALL ON public.study_adult_access_audit TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.study_adult_access_audit_id_seq TO service_role;

-- These functions are atomic, so audit and eligibility cannot disagree due
-- to a partial write. Server-only RPC access: never call from Telegram clients.
CREATE OR REPLACE FUNCTION public.v91_review_adult_request(
    p_target_user_id BIGINT,
    p_admin_user_id BIGINT,
    p_action TEXT,
    p_valid_days INTEGER DEFAULT 180
)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE old_status TEXT;
DECLARE expiry TIMESTAMPTZ;
BEGIN
    IF p_target_user_id IS NULL OR p_target_user_id <= 0
       OR p_admin_user_id IS NULL OR p_admin_user_id <= 0
       OR p_target_user_id = p_admin_user_id THEN
        RAISE EXCEPTION 'Invalid IDs or self approval';
    END IF;
    IF p_action NOT IN ('approve', 'reject') OR p_action IS NULL THEN
        RAISE EXCEPTION 'Invalid review action';
    END IF;
    IF p_valid_days IS NULL OR p_valid_days NOT BETWEEN 1 AND 365 THEN
        RAISE EXCEPTION 'Invalid verification expiry';
    END IF;
    SELECT status INTO old_status
      FROM public.study_adult_access_requests
     WHERE user_id = p_target_user_id FOR UPDATE;
    IF old_status IS DISTINCT FROM 'pending' THEN
        RAISE EXCEPTION 'No pending access request';
    END IF;
    IF p_action = 'approve' THEN
        expiry := NOW() + make_interval(days => p_valid_days);
        INSERT INTO public.study_verified_adults
          (user_id,status,verification_method,verified_at,valid_until)
        VALUES (p_target_user_id,'verified','manual_review',NOW(),expiry)
        ON CONFLICT (user_id) DO UPDATE SET
          status='verified', verification_method='manual_review',
          verified_at=NOW(), valid_until=EXCLUDED.valid_until;
        UPDATE public.study_adult_access_requests
           SET status='approved',reviewed_at=NOW(),reviewed_by=p_admin_user_id,updated_at=NOW()
         WHERE user_id=p_target_user_id;
        INSERT INTO public.study_adult_access_audit(user_id,admin_id,action,valid_until)
        VALUES (p_target_user_id,p_admin_user_id,'approved',expiry);
        RETURN 'approved';
    END IF;
    UPDATE public.study_adult_access_requests
       SET status='rejected',reviewed_at=NOW(),reviewed_by=p_admin_user_id,updated_at=NOW()
     WHERE user_id=p_target_user_id;
    INSERT INTO public.study_adult_access_audit(user_id,admin_id,action)
    VALUES (p_target_user_id,p_admin_user_id,'rejected');
    RETURN 'rejected';
END;
$$;

CREATE OR REPLACE FUNCTION public.v91_revoke_adult_access(
    p_target_user_id BIGINT,
    p_admin_user_id BIGINT
)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
    IF p_target_user_id IS NULL OR p_target_user_id <= 0
       OR p_admin_user_id IS NULL OR p_admin_user_id <= 0 THEN
        RAISE EXCEPTION 'Invalid IDs';
    END IF;
    UPDATE public.study_verified_adults SET status='revoked'
     WHERE user_id=p_target_user_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User has no verified-adult record';
    END IF;
    UPDATE public.study_adult_access_requests
       SET status='revoked',reviewed_at=NOW(),reviewed_by=p_admin_user_id,updated_at=NOW()
     WHERE user_id=p_target_user_id;
    INSERT INTO public.study_adult_access_audit(user_id,admin_id,action)
    VALUES (p_target_user_id,p_admin_user_id,'revoked');
    RETURN 'revoked';
END;
$$;

REVOKE ALL ON FUNCTION public.v91_review_adult_request(BIGINT,BIGINT,TEXT,INTEGER)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.v91_revoke_adult_access(BIGINT,BIGINT)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.v91_review_adult_request(BIGINT,BIGINT,TEXT,INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION public.v91_revoke_adult_access(BIGINT,BIGINT) TO service_role;
