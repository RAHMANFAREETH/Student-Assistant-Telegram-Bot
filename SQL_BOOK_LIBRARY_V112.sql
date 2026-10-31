-- V11.2: additive, public-facing library enhancements. Back up Supabase first.
-- File bytes remain in the private Telegram channel. Always use service-role server-side.
BEGIN;

ALTER TABLE public.book_library_items
  ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'General',
  ADD COLUMN IF NOT EXISTS isbn TEXT,
  ADD COLUMN IF NOT EXISTS cover_file_id TEXT,
  ADD COLUMN IF NOT EXISTS download_count BIGINT NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS book_library_category_idx
  ON public.book_library_items (lower(category), added_at DESC) WHERE active;
CREATE INDEX IF NOT EXISTS book_library_language_idx
  ON public.book_library_items (lower(language), added_at DESC) WHERE active;
CREATE INDEX IF NOT EXISTS book_library_author_idx
  ON public.book_library_items (lower(author), added_at DESC) WHERE active;
CREATE INDEX IF NOT EXISTS book_library_isbn_idx
  ON public.book_library_items (isbn) WHERE active AND isbn IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.book_library_favorites (
  user_id BIGINT NOT NULL CHECK (user_id > 0),
  book_id UUID NOT NULL REFERENCES public.book_library_items(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, book_id)
);
CREATE INDEX IF NOT EXISTS book_library_favorites_recent_idx
  ON public.book_library_favorites (user_id, created_at DESC);
ALTER TABLE public.book_library_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.book_library_favorites ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.book_library_items FROM PUBLIC, anon, authenticated;
REVOKE ALL ON public.book_library_favorites FROM PUBLIC, anon, authenticated;

-- Literal substring match, not ILIKE-wildcard user input. 100-page cap in app;
-- limited size and offset also enforced server-side for defensive API use.
CREATE OR REPLACE FUNCTION public.book_library_v112_browse(
    p_query TEXT DEFAULT NULL,
    p_category TEXT DEFAULT NULL,
    p_author TEXT DEFAULT NULL,
    p_language TEXT DEFAULT NULL,
    p_isbn TEXT DEFAULT NULL,
    p_limit INT DEFAULT 6,
    p_offset INT DEFAULT 0
)
RETURNS SETOF public.book_library_items
LANGUAGE sql STABLE SECURITY INVOKER SET search_path = public
AS $$
  SELECT b.*
    FROM public.book_library_items AS b
   WHERE b.active = TRUE
     AND (p_query IS NULL OR (
           char_length(trim(p_query)) BETWEEN 2 AND 100 AND
           (position(lower(trim(p_query)) in lower(b.title)) > 0 OR
            position(lower(trim(p_query)) in lower(b.author)) > 0 OR
            position(lower(trim(p_query)) in lower(b.language)) > 0 OR
            position(lower(trim(p_query)) in lower(b.category)) > 0 OR
            position(lower(trim(p_query)) in lower(coalesce(b.isbn,''))) > 0)))
     AND (p_category IS NULL OR lower(b.category) = lower(p_category))
     AND (p_author IS NULL OR lower(b.author) = lower(p_author))
     AND (p_language IS NULL OR lower(b.language) = lower(p_language))
     AND (p_isbn IS NULL OR b.isbn = p_isbn)
   ORDER BY b.added_at DESC, b.id DESC
   LIMIT LEAST(GREATEST(coalesce(p_limit, 6), 1), 9)
  OFFSET LEAST(GREATEST(coalesce(p_offset, 0), 0), 800);
$$;

CREATE OR REPLACE FUNCTION public.book_library_v112_facets(p_kind TEXT)
RETURNS TABLE(value TEXT, book_count BIGINT)
LANGUAGE sql STABLE SECURITY INVOKER SET search_path = public
AS $$
  SELECT x.value, SUM(x.book_count)::BIGINT AS book_count
  FROM (
    SELECT b.category AS value, count(*)::BIGINT AS book_count
      FROM public.book_library_items b
     WHERE b.active AND p_kind = 'category' GROUP BY b.category
    UNION ALL
    SELECT b.author, count(*)::BIGINT
      FROM public.book_library_items b
     WHERE b.active AND p_kind = 'author' GROUP BY b.author
    UNION ALL
    SELECT b.language, count(*)::BIGINT
      FROM public.book_library_items b
     WHERE b.active AND p_kind = 'language' GROUP BY b.language
  ) x
  GROUP BY x.value ORDER BY book_count DESC, x.value ASC LIMIT 30;
$$;

CREATE OR REPLACE FUNCTION public.book_library_v112_record_delivery(p_book_id UUID)
RETURNS VOID LANGUAGE sql VOLATILE SECURITY INVOKER SET search_path = public
AS $$
  UPDATE public.book_library_items AS b
     SET download_count = b.download_count + 1
   WHERE b.id = p_book_id AND b.active = TRUE;
$$;

REVOKE ALL ON FUNCTION public.book_library_v112_browse(TEXT,TEXT,TEXT,TEXT,TEXT,INT,INT)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.book_library_v112_facets(TEXT)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.book_library_v112_record_delivery(UUID)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.book_library_v112_browse(TEXT,TEXT,TEXT,TEXT,TEXT,INT,INT) TO service_role;
GRANT EXECUTE ON FUNCTION public.book_library_v112_facets(TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.book_library_v112_record_delivery(UUID) TO service_role;
COMMIT;
