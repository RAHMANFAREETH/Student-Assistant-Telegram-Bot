-- V9.2 Smart Admin & expiry notifications. Supabase SQL Editor, after V9.1.
-- ADDITIVE migration: no existing tables, verification, or V8/V9 data changed.
-- Must be called only by existing trusted backend service_role credentials.

CREATE TABLE IF NOT EXISTS public.study_adult_expiry_notifications (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    milestone TEXT NOT NULL CHECK (milestone IN ('7d','1d','expired')),
    status TEXT NOT NULL DEFAULT 'leased' CHECK (status IN ('leased','sent')),
    claim_token UUID NOT NULL DEFAULT gen_random_uuid(),
    lease_until TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '15 minutes'),
    attempts INTEGER NOT NULL DEFAULT 1 CHECK (attempts BETWEEN 1 AND 10),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    UNIQUE(user_id,valid_until,milestone)
);
CREATE INDEX IF NOT EXISTS study_verified_adults_expiry_v92_idx
    ON public.study_verified_adults(status, valid_until);
CREATE INDEX IF NOT EXISTS study_adult_expiry_notifications_status_idx
    ON public.study_adult_expiry_notifications(status, lease_until);
ALTER TABLE public.study_adult_expiry_notifications ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.study_adult_expiry_notifications FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON public.study_adult_expiry_notifications TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.study_adult_expiry_notifications_id_seq TO service_role;

-- Server RPC leases up to 50 pending notifications. Only one milestone per
-- current approval is due at a time. Delivery is at-least-once (not exactly-once).
CREATE OR REPLACE FUNCTION public.v92_claim_expiry_notifications(p_limit INTEGER DEFAULT 20)
RETURNS TABLE(id BIGINT, user_id BIGINT, valid_until TIMESTAMPTZ, milestone TEXT, claim_token UUID)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
    IF p_limit IS NULL OR p_limit NOT BETWEEN 1 AND 50 THEN
        RAISE EXCEPTION 'Invalid notification batch size';
    END IF;

    RETURN QUERY
    WITH eligible AS (
        SELECT v.user_id, v.valid_until,
          CASE
            WHEN v.valid_until <= NOW() THEN 'expired'
            WHEN v.valid_until <= NOW() + INTERVAL '1 day' THEN '1d'
            ELSE '7d'
          END::TEXT AS milestone
        FROM public.study_verified_adults AS v
        WHERE v.status = 'verified'
          AND v.valid_until > NOW() - INTERVAL '30 days'
          AND v.valid_until <= NOW() + INTERVAL '7 days'
    ), due AS (
        SELECT e.user_id, e.valid_until, e.milestone
        FROM eligible AS e
        WHERE NOT EXISTS (
            SELECT 1 FROM public.study_adult_expiry_notifications AS n
            WHERE n.user_id = e.user_id
              AND n.valid_until = e.valid_until
              AND n.milestone = e.milestone
              AND (n.status = 'sent' OR n.lease_until > NOW() OR n.attempts >= 10)
        )
        ORDER BY e.valid_until ASC
        LIMIT p_limit
    ), upserted AS (
        INSERT INTO public.study_adult_expiry_notifications
            (user_id, valid_until, milestone, status, claim_token, lease_until, attempts)
        SELECT e.user_id, e.valid_until, e.milestone, 'leased', gen_random_uuid(),
               NOW() + INTERVAL '15 minutes', 1
        FROM due AS e
        ON CONFLICT (user_id, valid_until, milestone) DO UPDATE
          SET claim_token = gen_random_uuid(),
              lease_until = NOW() + INTERVAL '15 minutes',
              attempts = public.study_adult_expiry_notifications.attempts + 1
          WHERE public.study_adult_expiry_notifications.status = 'leased'
            AND public.study_adult_expiry_notifications.lease_until <= NOW()
            AND public.study_adult_expiry_notifications.attempts < 10
        RETURNING public.study_adult_expiry_notifications.id,
                  public.study_adult_expiry_notifications.user_id,
                  public.study_adult_expiry_notifications.valid_until,
                  public.study_adult_expiry_notifications.milestone,
                  public.study_adult_expiry_notifications.claim_token
    )
    SELECT u.id,u.user_id,u.valid_until,u.milestone,u.claim_token FROM upserted AS u;
END;
$$;

CREATE OR REPLACE FUNCTION public.v92_mark_expiry_notification_sent(
    p_event_id BIGINT, p_claim_token UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE n_count INTEGER;
BEGIN
    IF p_event_id IS NULL OR p_event_id <= 0 OR p_claim_token IS NULL THEN
        RETURN FALSE;
    END IF;
    UPDATE public.study_adult_expiry_notifications AS n
       SET status = 'sent', sent_at = NOW()
     WHERE n.id = p_event_id AND n.claim_token = p_claim_token
       AND n.status = 'leased';
    GET DIAGNOSTICS n_count = ROW_COUNT;
    RETURN n_count = 1;
END;
$$;

REVOKE ALL ON FUNCTION public.v92_claim_expiry_notifications(INTEGER) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.v92_mark_expiry_notification_sent(BIGINT,UUID) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.v92_claim_expiry_notifications(INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION public.v92_mark_expiry_notification_sent(BIGINT,UUID) TO service_role;
