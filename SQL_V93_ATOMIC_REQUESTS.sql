-- V9.3: optional database-atomic adult access request submission.
-- Run in Supabase SQL Editor after V9.1 and V9.2 migrations.
-- Re-entrant and non-destructive: leaves all existing approvals intact.
-- Only the trusted server-side Supabase service role can execute this RPC.

CREATE OR REPLACE FUNCTION public.v93_submit_adult_request(p_user_id BIGINT)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    current_status TEXT;
    last_change TIMESTAMPTZ;
    verified_status TEXT;
    expiry TIMESTAMPTZ;
BEGIN
    IF p_user_id IS NULL OR p_user_id <= 0 THEN
        RAISE EXCEPTION 'Invalid Telegram ID';
    END IF;

    -- Serialize simultaneous submissions from the same Telegram user.
    PERFORM pg_catalog.pg_advisory_xact_lock(p_user_id);

    SELECT status, valid_until INTO verified_status, expiry
      FROM public.study_verified_adults
     WHERE user_id = p_user_id;
    IF verified_status = 'verified' AND expiry > pg_catalog.now() THEN
        RETURN 'verified';
    END IF;

    SELECT status, updated_at INTO current_status, last_change
      FROM public.study_adult_access_requests
     WHERE user_id = p_user_id FOR UPDATE;
    IF FOUND THEN
        IF current_status = 'pending' THEN
            RETURN 'pending';
        END IF;
        IF last_change IS NULL OR
           last_change > pg_catalog.now() - INTERVAL '24 hours' THEN
            RETURN 'cooldown';
        END IF;
    END IF;

    INSERT INTO public.study_adult_access_requests (
        user_id, status, created_at, updated_at, reviewed_at, reviewed_by
    ) VALUES (p_user_id, 'pending', pg_catalog.now(), pg_catalog.now(), NULL, NULL)
    ON CONFLICT (user_id) DO UPDATE SET
        status = 'pending',
        created_at = EXCLUDED.created_at,
        updated_at = EXCLUDED.updated_at,
        reviewed_at = NULL,
        reviewed_by = NULL;
    RETURN 'created';
END;
$$;

REVOKE ALL ON FUNCTION public.v93_submit_adult_request(BIGINT)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.v93_submit_adult_request(BIGINT)
  TO service_role;
