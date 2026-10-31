-- V11.7: additive, existing PDF books remain in book_library_items.
-- Execute in Supabase SQL Editor with an authorized administrator only.
-- Existing V11.1–V11.5 migrations are required first.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.library_media_v117 (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 title TEXT NOT NULL CHECK (char_length(title) BETWEEN 2 AND 180),
 author TEXT NOT NULL CHECK (char_length(author) BETWEEN 2 AND 120),
 language TEXT NOT NULL CHECK (char_length(language) BETWEEN 2 AND 70),
 category TEXT NOT NULL DEFAULT 'General' CHECK (char_length(category) BETWEEN 2 AND 70),
 media_kind TEXT NOT NULL CHECK (media_kind IN ('pdf','image','audio','video','zip','docx','pptx','epub','txt')),
 file_name TEXT NOT NULL,
 file_size BIGINT NOT NULL DEFAULT 0 CHECK (file_size >= 0),
 file_unique_id TEXT,
 sha256 TEXT,
 storage_channel_id BIGINT,
 storage_message_id BIGINT,
 review_channel_id BIGINT,
 review_message_id BIGINT,
 uploader_id BIGINT NOT NULL CHECK(uploader_id > 0),
 rights_statement TEXT NOT NULL CHECK (char_length(rights_statement) BETWEEN 2 AND 300),
 comment TEXT NOT NULL DEFAULT 'Admin upload',
 description TEXT DEFAULT '',
 aliases TEXT NOT NULL DEFAULT '',
 ocr_text TEXT NOT NULL DEFAULT '',
 preview_file_id TEXT,
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','processing','approved','rejected','hidden')),
 download_count BIGINT NOT NULL DEFAULT 0 CHECK(download_count>=0),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 approved_at TIMESTAMPTZ,
 CONSTRAINT valid_v117_storage CHECK (
   status <> 'approved' OR (storage_channel_id < 0 AND storage_message_id > 0))
);
CREATE INDEX IF NOT EXISTS library_media_v117_status_index ON public.library_media_v117(status,created_at DESC);
CREATE INDEX IF NOT EXISTS library_media_v117_filter_index ON public.library_media_v117(status,media_kind,language);
CREATE INDEX IF NOT EXISTS library_media_v117_uid_index ON public.library_media_v117(file_unique_id) WHERE status IN ('approved','pending','processing') AND file_unique_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS library_media_v117_hash_index ON public.library_media_v117(sha256) WHERE status IN ('approved','pending','processing') AND sha256 IS NOT NULL;
CREATE INDEX IF NOT EXISTS library_media_v117_uploader_index ON public.library_media_v117(uploader_id,created_at DESC);

CREATE TABLE IF NOT EXISTS public.library_media_v117_favorites (
 user_id BIGINT NOT NULL CHECK(user_id > 0),
 media_id UUID NOT NULL REFERENCES public.library_media_v117(id) ON DELETE CASCADE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(user_id,media_id)
);
CREATE TABLE IF NOT EXISTS public.library_media_v117_reading (
 user_id BIGINT NOT NULL CHECK(user_id > 0),
 media_id UUID NOT NULL REFERENCES public.library_media_v117(id) ON DELETE CASCADE,
 status TEXT NOT NULL CHECK(status IN ('want','reading','completed')),
 percent INT NOT NULL DEFAULT 0 CHECK(percent BETWEEN 0 AND 100),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(user_id,media_id)
);
CREATE TABLE IF NOT EXISTS public.library_media_v117_audit (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 admin_id BIGINT NOT NULL CHECK(admin_id > 0),
 action TEXT NOT NULL,
 media_id UUID,
 details TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.library_media_v117_downloads (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 media_id UUID NOT NULL REFERENCES public.library_media_v117(id) ON DELETE CASCADE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS library_media_v117_downloads_index ON public.library_media_v117_downloads(created_at DESC,media_id);

-- Parameterized search includes historical media beyond the 350 recent
-- candidates used for typo-tolerant fallback. It never returns pending files.
CREATE OR REPLACE FUNCTION public.library_v117_search_candidates(
 p_query TEXT,
 p_kind TEXT DEFAULT NULL,
 p_language TEXT DEFAULT NULL,
 p_author TEXT DEFAULT NULL,
 p_category TEXT DEFAULT NULL,
 p_min_bytes BIGINT DEFAULT 0,
 p_max_bytes BIGINT DEFAULT NULL,
 p_limit INT DEFAULT 250
) RETURNS SETOF public.library_media_v117
LANGUAGE sql STABLE SECURITY INVOKER SET search_path=public AS $$
 SELECT m.* FROM public.library_media_v117 AS m
 WHERE m.status='approved'
   AND length(trim(coalesce(p_query,''))) BETWEEN 2 AND 100
   AND (
     position(lower(p_query) in lower(m.title))>0 OR
     position(lower(p_query) in lower(m.author))>0 OR
     position(lower(p_query) in lower(m.aliases))>0 OR
     position(lower(p_query) in lower(m.ocr_text))>0 OR
     position(lower(p_query) in lower(m.category))>0 OR
     position(lower(p_query) in lower(coalesce(m.description,'')))>0
   )
   AND (p_kind IS NULL OR m.media_kind=p_kind)
   AND (p_language IS NULL OR lower(m.language) LIKE '%' || lower(p_language) || '%')
   AND (p_author IS NULL OR lower(m.author) LIKE '%' || lower(p_author) || '%')
   AND (p_category IS NULL OR lower(m.category) LIKE '%' || lower(p_category) || '%')
   AND m.file_size >= coalesce(p_min_bytes,0)
   AND (p_max_bytes IS NULL OR m.file_size <= p_max_bytes)
 ORDER BY m.approved_at DESC NULLS LAST
 LIMIT least(greatest(coalesce(p_limit,250),1),300);
$$;

-- Safe concurrent review: only one reviewer can claim a pending submission.
CREATE OR REPLACE FUNCTION public.library_v117_claim_media(p_id UUID)
RETURNS SETOF public.library_media_v117
LANGUAGE sql VOLATILE SECURITY INVOKER SET search_path=public AS $$
 UPDATE public.library_media_v117 AS m SET status='processing'
 WHERE m.id=p_id AND m.status='pending' RETURNING m.*;
$$;

CREATE OR REPLACE FUNCTION public.library_v117_record_delivery(p_id UUID)
RETURNS VOID LANGUAGE plpgsql SECURITY INVOKER SET search_path=public AS $$
BEGIN
 UPDATE public.library_media_v117 SET download_count=download_count+1
 WHERE id=p_id AND status='approved';
 IF FOUND THEN
   INSERT INTO public.library_media_v117_downloads(media_id) VALUES(p_id);
   -- Low-frequency cleanup avoids indefinite growth of anonymous event rows.
   IF random() < 0.02 THEN
      DELETE FROM public.library_media_v117_downloads
      WHERE created_at < now() - INTERVAL '90 days';
   END IF;
 END IF;
END;
$$;

-- Extend existing request statuses while preserving old values and handlers.
DO $$ DECLARE c RECORD;
BEGIN
 FOR c IN SELECT conname FROM pg_constraint
          WHERE conrelid='public.book_library_requests'::regclass AND contype='c'
          AND pg_get_constraintdef(oid) LIKE '%status%' LOOP
   EXECUTE format('ALTER TABLE public.book_library_requests DROP CONSTRAINT %I',c.conname);
 END LOOP;
END $$;
ALTER TABLE public.book_library_requests
 ADD CONSTRAINT book_library_requests_status_v117_check
 CHECK(status IN ('pending','fulfilled','found','uploaded','rejected'));

-- The same Supabase SERVICE ROLE used by existing bot bypasses RLS.
-- Do not expose these tables through anon/authenticated public clients.
ALTER TABLE public.library_media_v117 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.library_media_v117_favorites ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.library_media_v117_reading ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.library_media_v117_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.library_media_v117_downloads ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.library_media_v117,public.library_media_v117_favorites,
 public.library_media_v117_reading,public.library_media_v117_audit,
 public.library_media_v117_downloads FROM anon,authenticated;
REVOKE ALL ON FUNCTION public.library_v117_claim_media(UUID), public.library_v117_record_delivery(UUID),
 public.library_v117_search_candidates(TEXT,TEXT,TEXT,TEXT,TEXT,BIGINT,BIGINT,INT) FROM PUBLIC;

-- Explicitly preserve the private bot's service-role permissions.
GRANT ALL ON TABLE public.library_media_v117,public.library_media_v117_favorites,
 public.library_media_v117_reading,public.library_media_v117_audit,
 public.library_media_v117_downloads TO service_role;
GRANT USAGE,SELECT ON SEQUENCE public.library_media_v117_downloads_id_seq TO service_role;
GRANT EXECUTE ON FUNCTION public.library_v117_claim_media(UUID),public.library_v117_record_delivery(UUID),
 public.library_v117_search_candidates(TEXT,TEXT,TEXT,TEXT,TEXT,BIGINT,BIGINT,INT) TO service_role;
