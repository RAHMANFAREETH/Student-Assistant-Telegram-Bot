-- V11.1 Book Library. Run in the existing Supabase SQL Editor, after a backup.
-- Files stay in the private Telegram channel; only metadata/message references are stored here.
BEGIN;

CREATE TABLE IF NOT EXISTS public.book_library_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL CHECK (char_length(title) BETWEEN 2 AND 180),
    author TEXT NOT NULL CHECK (char_length(author) BETWEEN 2 AND 120),
    language TEXT NOT NULL CHECK (char_length(language) BETWEEN 2 AND 40),
    file_name TEXT NOT NULL DEFAULT '',
    file_size BIGINT NOT NULL DEFAULT 0 CHECK (file_size >= 0),
    channel_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL CHECK (message_id > 0),
    uploaded_by BIGINT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (channel_id, message_id)
);
CREATE INDEX IF NOT EXISTS book_library_items_recent_idx
    ON public.book_library_items (added_at DESC) WHERE active = TRUE;
ALTER TABLE public.book_library_items ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.book_library_items FROM PUBLIC, anon, authenticated;

-- SECURITY INVOKER: only the server-side Supabase service-role client should call it.
-- position() treats user input literally, including % and _ (no PostgREST filter injection).
CREATE OR REPLACE FUNCTION public.book_library_search(p_query TEXT, p_limit INTEGER DEFAULT 8)
RETURNS SETOF public.book_library_items
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = public
AS $$
    SELECT b.*
      FROM public.book_library_items AS b
     WHERE b.active = TRUE
       AND char_length(trim(coalesce(p_query, ''))) BETWEEN 2 AND 100
       AND (
           position(lower(trim(p_query)) in lower(b.title)) > 0 OR
           position(lower(trim(p_query)) in lower(b.author)) > 0 OR
           position(lower(trim(p_query)) in lower(b.language)) > 0
       )
     ORDER BY
       CASE WHEN lower(b.title) = lower(trim(p_query)) THEN 0
            WHEN left(lower(b.title), char_length(trim(p_query))) = lower(trim(p_query)) THEN 1
            ELSE 2 END,
       b.title, b.added_at DESC
     LIMIT LEAST(GREATEST(coalesce(p_limit, 8), 1), 10);
$$;
REVOKE ALL ON FUNCTION public.book_library_search(TEXT, INTEGER) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.book_library_search(TEXT, INTEGER) TO service_role;

COMMIT;
