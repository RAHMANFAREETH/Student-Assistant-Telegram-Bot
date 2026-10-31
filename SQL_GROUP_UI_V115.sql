-- V11.5 temporary group-menu deletion queue (additive migration).
-- Use the existing server-side Supabase service-role client. Never expose its key.
BEGIN;

CREATE TABLE IF NOT EXISTS public.bot_group_ephemeral_messages (
    chat_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    message_type TEXT NOT NULL DEFAULT 'menu'
      CHECK (message_type IN ('menu','book_links','redirect')),
    delete_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 10),
    lease_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(chat_id,message_id)
);
CREATE INDEX IF NOT EXISTS idx_v115_group_due
    ON public.bot_group_ephemeral_messages (delete_at)
    WHERE attempts < 3;
ALTER TABLE public.bot_group_ephemeral_messages ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.bot_group_ephemeral_messages FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.bot_group_ephemeral_messages TO service_role;

CREATE OR REPLACE FUNCTION public.v115_claim_due_group_messages(p_limit INTEGER DEFAULT 30)
RETURNS TABLE(out_chat_id BIGINT, out_message_id BIGINT)
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    WITH claimed AS (
        SELECT e.chat_id, e.message_id
        FROM public.bot_group_ephemeral_messages AS e
        WHERE e.delete_at <= now()
          AND e.attempts < 3
          AND (e.lease_until IS NULL OR e.lease_until <= now())
        ORDER BY e.delete_at, e.chat_id, e.message_id
        LIMIT LEAST(GREATEST(p_limit, 1), 60)
        FOR UPDATE SKIP LOCKED
    )
    UPDATE public.bot_group_ephemeral_messages AS e
    SET lease_until = now() + interval '90 seconds'
    FROM claimed AS c
    WHERE e.chat_id = c.chat_id AND e.message_id = c.message_id
    RETURNING e.chat_id, e.message_id;
END;
$$;

CREATE OR REPLACE FUNCTION public.v115_release_group_message(
    p_chat_id BIGINT, p_message_id BIGINT
) RETURNS VOID
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
    UPDATE public.bot_group_ephemeral_messages AS e
    SET attempts = LEAST(e.attempts + 1, 10),
        delete_at = now() + interval '2 minutes',
        lease_until = NULL
    WHERE e.chat_id = p_chat_id AND e.message_id = p_message_id;
END;
$$;

REVOKE ALL ON FUNCTION public.v115_claim_due_group_messages(INTEGER) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.v115_release_group_message(BIGINT, BIGINT) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.v115_claim_due_group_messages(INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION public.v115_release_group_message(BIGINT, BIGINT) TO service_role;

COMMIT;
