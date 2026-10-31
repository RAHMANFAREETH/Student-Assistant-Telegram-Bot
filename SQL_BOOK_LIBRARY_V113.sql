-- V11.3 Advanced Library — additive migration. BACK UP Supabase before running.
-- No content bytes or Telegram bot credentials are stored in these tables.
BEGIN;

ALTER TABLE public.book_library_items
 ADD COLUMN IF NOT EXISTS series_name TEXT,
 ADD COLUMN IF NOT EXISTS volume_number INT CHECK (volume_number BETWEEN 1 AND 500),
 ADD COLUMN IF NOT EXISTS edition TEXT,
 ADD COLUMN IF NOT EXISTS translator TEXT,
 ADD COLUMN IF NOT EXISTS publisher TEXT,
 ADD COLUMN IF NOT EXISTS published_year INT CHECK (published_year BETWEEN 1400 AND 2200),
 ADD COLUMN IF NOT EXISTS description TEXT,
 ADD COLUMN IF NOT EXISTS preview_text TEXT,
 ADD COLUMN IF NOT EXISTS cover_url TEXT,
 ADD COLUMN IF NOT EXISTS license_type TEXT,
 ADD COLUMN IF NOT EXISTS file_unique_id TEXT,
 ADD COLUMN IF NOT EXISTS sha256 TEXT;
CREATE INDEX IF NOT EXISTS book_library_series_idx ON public.book_library_items(lower(series_name),volume_number)
 WHERE active AND series_name IS NOT NULL;
CREATE INDEX IF NOT EXISTS book_library_file_uid_idx ON public.book_library_items(file_unique_id)
 WHERE active AND file_unique_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS book_library_hash_idx ON public.book_library_items(sha256)
 WHERE active AND sha256 IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.book_library_reading_progress(
 user_id BIGINT NOT NULL CHECK(user_id>0),
 book_id UUID NOT NULL REFERENCES public.book_library_items(id) ON DELETE CASCADE,
 status TEXT NOT NULL CHECK(status IN ('want','reading','completed')),
 percent INT NOT NULL DEFAULT 0 CHECK(percent BETWEEN 0 AND 100),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 PRIMARY KEY(user_id,book_id)
);
CREATE INDEX IF NOT EXISTS book_lib_progress_user_idx ON public.book_library_reading_progress(user_id,updated_at DESC);
CREATE OR REPLACE FUNCTION public.book_library_v113_progress_timestamp()
RETURNS trigger LANGUAGE plpgsql SET search_path=public AS $$ BEGIN NEW.updated_at=NOW(); RETURN NEW; END; $$;
DROP TRIGGER IF EXISTS book_lib_progress_stamp ON public.book_library_reading_progress;
CREATE TRIGGER book_lib_progress_stamp BEFORE UPDATE ON public.book_library_reading_progress
FOR EACH ROW EXECUTE FUNCTION public.book_library_v113_progress_timestamp();

CREATE TABLE IF NOT EXISTS public.book_library_reviews(
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id BIGINT NOT NULL CHECK(user_id>0),
 book_id UUID NOT NULL REFERENCES public.book_library_items(id) ON DELETE CASCADE,
 rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
 review_text TEXT NOT NULL CHECK(char_length(review_text) BETWEEN 2 AND 500),
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 UNIQUE(user_id,book_id)
);
CREATE INDEX IF NOT EXISTS book_lib_reviews_pending_idx ON public.book_library_reviews(created_at)
 WHERE status='pending';
CREATE INDEX IF NOT EXISTS book_lib_reviews_public_idx ON public.book_library_reviews(book_id,created_at DESC)
 WHERE status='approved';

CREATE TABLE IF NOT EXISTS public.book_library_challenges(
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id BIGINT NOT NULL CHECK(user_id>0),
 target_books INT NOT NULL CHECK(target_books BETWEEN 1 AND 100),
 days INT NOT NULL CHECK(days BETWEEN 1 AND 365),
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 ends_at TIMESTAMPTZ NOT NULL DEFAULT (NOW()+INTERVAL '30 days')
);
CREATE INDEX IF NOT EXISTS book_lib_challenge_user_idx ON public.book_library_challenges(user_id,created_at DESC);

CREATE TABLE IF NOT EXISTS public.book_library_collections(
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id BIGINT NOT NULL CHECK(user_id>0),
 name TEXT NOT NULL CHECK(char_length(name) BETWEEN 2 AND 80),
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 UNIQUE(id,user_id)
);
CREATE INDEX IF NOT EXISTS book_lib_collections_user_idx ON public.book_library_collections(user_id,created_at DESC);
CREATE TABLE IF NOT EXISTS public.book_library_collection_items(
 collection_id UUID NOT NULL REFERENCES public.book_library_collections(id) ON DELETE CASCADE,
 book_id UUID NOT NULL REFERENCES public.book_library_items(id) ON DELETE CASCADE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 PRIMARY KEY(collection_id,book_id)
);

CREATE TABLE IF NOT EXISTS public.book_library_subscriptions(
 user_id BIGINT NOT NULL CHECK(user_id>0),
 kind TEXT NOT NULL CHECK(kind IN ('category','author','challenge')),
 term TEXT NOT NULL CHECK(char_length(term) BETWEEN 2 AND 100),
 enabled BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 PRIMARY KEY(user_id,kind,term)
);
CREATE INDEX IF NOT EXISTS book_lib_subscriptions_match_idx ON public.book_library_subscriptions(kind,lower(term)) WHERE enabled;

CREATE TABLE IF NOT EXISTS public.book_library_requests(
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id BIGINT NOT NULL CHECK(user_id>0),
 title TEXT NOT NULL CHECK(char_length(title) BETWEEN 2 AND 160),
 author TEXT,
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','fulfilled','rejected')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS book_lib_request_one_pending_title_idx
 ON public.book_library_requests(user_id,lower(title)) WHERE status='pending';
CREATE INDEX IF NOT EXISTS book_lib_requests_pending_idx ON public.book_library_requests(created_at) WHERE status='pending';
CREATE INDEX IF NOT EXISTS book_lib_requests_user_idx ON public.book_library_requests(user_id,status);

CREATE TABLE IF NOT EXISTS public.book_library_submissions(
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id BIGINT NOT NULL CHECK(user_id>0),
 title TEXT NOT NULL,
 author TEXT NOT NULL,
 language TEXT NOT NULL,
 rights_statement TEXT NOT NULL,
 review_channel_id BIGINT NOT NULL,
 review_message_id BIGINT NOT NULL,
 file_name TEXT NOT NULL,
 file_size BIGINT NOT NULL,
 file_unique_id TEXT,
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','processing','approved','rejected')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS book_lib_submissions_pending_idx ON public.book_library_submissions(created_at) WHERE status='pending';
CREATE INDEX IF NOT EXISTS book_lib_submissions_user_idx ON public.book_library_submissions(user_id,status);

CREATE TABLE IF NOT EXISTS public.book_library_reports(
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id BIGINT NOT NULL CHECK(user_id>0),
 book_id UUID NOT NULL REFERENCES public.book_library_items(id) ON DELETE CASCADE,
 kind TEXT NOT NULL CHECK(kind IN ('broken_file','metadata','inappropriate','copyright')),
 description TEXT,
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','resolved','dismissed')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS book_lib_report_one_pending_idx
 ON public.book_library_reports(user_id,book_id,kind) WHERE status='pending';
CREATE INDEX IF NOT EXISTS book_lib_reports_pending_idx ON public.book_library_reports(created_at) WHERE status='pending';

CREATE TABLE IF NOT EXISTS public.book_library_daily_stats(
 stat_day DATE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')::date,
 metric TEXT NOT NULL CHECK(metric IN ('deliveries','uploads','explicit_searches','not_found')),
 total BIGINT NOT NULL DEFAULT 0,
 PRIMARY KEY(stat_day,metric)
);
CREATE OR REPLACE FUNCTION public.book_library_v113_metric(p_metric TEXT)
RETURNS VOID LANGUAGE plpgsql SECURITY INVOKER SET search_path=public AS $$
BEGIN
 IF p_metric NOT IN ('deliveries','uploads','explicit_searches','not_found') THEN RETURN; END IF;
 INSERT INTO public.book_library_daily_stats AS stats(stat_day,metric,total)
 VALUES ((NOW() AT TIME ZONE 'UTC')::date,p_metric,1)
 ON CONFLICT(stat_day,metric) DO UPDATE SET total=stats.total+1;
END;
$$;

CREATE TABLE IF NOT EXISTS public.book_library_search_misses(
 query TEXT PRIMARY KEY CHECK(char_length(query) BETWEEN 2 AND 100),
 occurrences BIGINT NOT NULL DEFAULT 1,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE OR REPLACE FUNCTION public.book_library_v113_search_miss(p_query TEXT)
RETURNS VOID LANGUAGE plpgsql SECURITY INVOKER SET search_path=public AS $$
BEGIN
  IF length(trim(coalesce(p_query,''))) NOT BETWEEN 2 AND 100 THEN RETURN; END IF;
  INSERT INTO public.book_library_search_misses AS misses(query,occurrences)
  VALUES (lower(trim(p_query)),1)
  ON CONFLICT (query) DO UPDATE SET occurrences = misses.occurrences+1, updated_at=NOW();
END;
$$;

-- Atomic submission claim: two admin workers cannot approve the same upload simultaneously.
CREATE OR REPLACE FUNCTION public.book_library_v113_claim_submission(p_id UUID)
RETURNS SETOF public.book_library_submissions
LANGUAGE sql VOLATILE SECURITY INVOKER SET search_path=public AS $$
 UPDATE public.book_library_submissions AS s
 SET status='processing' WHERE s.id=p_id AND s.status='pending' RETURNING s.*;
$$;

-- Background notifier queue: enqueue once; workers claim with SKIP LOCKED.
CREATE TABLE IF NOT EXISTS public.book_library_notifications(
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id BIGINT NOT NULL CHECK(user_id>0),
 body TEXT NOT NULL CHECK(char_length(body) BETWEEN 2 AND 350),
 kind TEXT NOT NULL CHECK(kind IN ('new_book','challenge')),
 dedupe_key TEXT UNIQUE,
 due_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','claimed','sent','failed')),
 claimed_at TIMESTAMPTZ,
 sent_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS book_lib_notify_due_idx ON public.book_library_notifications(due_at)
 WHERE status='pending';
CREATE OR REPLACE FUNCTION public.book_library_v113_claim_notifications(p_limit INT DEFAULT 10)
RETURNS SETOF public.book_library_notifications
LANGUAGE sql VOLATILE SECURITY INVOKER SET search_path=public AS $$
 WITH claim AS (
   SELECT n.id FROM public.book_library_notifications AS n
   WHERE n.due_at<=NOW() AND (n.status='pending' OR
        (n.status='claimed' AND n.claimed_at<NOW()-INTERVAL '20 minutes'))
   ORDER BY n.due_at ASC LIMIT LEAST(GREATEST(p_limit,1),20)
   FOR UPDATE SKIP LOCKED
 )
 UPDATE public.book_library_notifications AS n
 SET status='claimed',claimed_at=NOW()
 FROM claim WHERE n.id=claim.id RETURNING n.*;
$$;

DO $$
DECLARE t TEXT;
BEGIN
 FOREACH t IN ARRAY ARRAY[
  'book_library_reading_progress','book_library_reviews','book_library_challenges',
  'book_library_collections','book_library_collection_items','book_library_subscriptions',
  'book_library_requests','book_library_submissions','book_library_reports',
  'book_library_search_misses','book_library_daily_stats','book_library_notifications']
 LOOP
   EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',t);
   EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated',t);
   EXECUTE format('GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE public.%I TO service_role',t);
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION public.book_library_v113_progress_timestamp() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.book_library_v113_metric(TEXT) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.book_library_v113_search_miss(TEXT) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.book_library_v113_claim_submission(UUID) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.book_library_v113_claim_notifications(INT) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.book_library_v113_progress_timestamp() TO service_role;
GRANT EXECUTE ON FUNCTION public.book_library_v113_metric(TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.book_library_v113_search_miss(TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.book_library_v113_claim_submission(UUID) TO service_role;
GRANT EXECUTE ON FUNCTION public.book_library_v113_claim_notifications(INT) TO service_role;
COMMIT;
