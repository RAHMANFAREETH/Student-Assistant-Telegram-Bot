-- V11.9 Friendly Student Experience. Execute once in Supabase SQL editor.
-- Only your existing server-side service-role db client must query these tables.
-- No public anon/authenticated table privileges.

CREATE TABLE IF NOT EXISTS public.friendly_v119_users (
  user_id BIGINT PRIMARY KEY CHECK (user_id > 0),
  notify_new BOOLEAN NOT NULL DEFAULT FALSE,
  ref_code TEXT UNIQUE,
  referrer_id BIGINT,
  last_notified_key TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS friendly_v119_users_referrer_idx
  ON public.friendly_v119_users(referrer_id) WHERE referrer_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS friendly_v119_users_notify_idx
  ON public.friendly_v119_users(user_id) WHERE notify_new;

CREATE TABLE IF NOT EXISTS public.friendly_v119_saved (
  user_id BIGINT NOT NULL CHECK (user_id > 0),
  item_kind TEXT NOT NULL CHECK (item_kind IN ('m','b')),
  item_id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY(user_id,item_kind,item_id)
);
CREATE INDEX IF NOT EXISTS friendly_v119_saved_user_idx
  ON public.friendly_v119_saved(user_id,created_at DESC);

CREATE TABLE IF NOT EXISTS public.friendly_v119_events (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT NOT NULL CHECK (user_id > 0),
  action TEXT NOT NULL CHECK (length(action) BETWEEN 1 AND 40),
  item_kind TEXT CHECK (item_kind IN ('m','b')),
  item_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS friendly_v119_events_user_idx
  ON public.friendly_v119_events(user_id,created_at DESC);
CREATE INDEX IF NOT EXISTS friendly_v119_events_time_idx
  ON public.friendly_v119_events(created_at DESC);
-- Suggested maintenance: periodically DELETE old events older than 90 days.

CREATE TABLE IF NOT EXISTS public.friendly_v119_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id BIGINT NOT NULL CHECK (user_id > 0),
  item_kind TEXT NOT NULL CHECK (item_kind IN ('m','b')),
  item_id UUID NOT NULL,
  stars SMALLINT NOT NULL CHECK (stars BETWEEN 1 AND 5),
  review_text TEXT NOT NULL DEFAULT '' CHECK (char_length(review_text) <= 550),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id,item_kind,item_id)
);
CREATE INDEX IF NOT EXISTS friendly_v119_reviews_item_idx
  ON public.friendly_v119_reviews(item_kind,item_id,status);
CREATE INDEX IF NOT EXISTS friendly_v119_reviews_status_idx
  ON public.friendly_v119_reviews(status,created_at);

CREATE TABLE IF NOT EXISTS public.friendly_v119_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id BIGINT NOT NULL CHECK (user_id > 0),
  kind TEXT NOT NULL CHECK (kind IN ('suggestion','book_report')),
  message TEXT NOT NULL CHECK (length(message) BETWEEN 8 AND 650),
  item_kind TEXT CHECK (item_kind IN ('m','b')),
  item_id UUID,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','resolved')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS friendly_v119_feedback_status_idx
  ON public.friendly_v119_feedback(status,created_at);

ALTER TABLE public.friendly_v119_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.friendly_v119_saved ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.friendly_v119_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.friendly_v119_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.friendly_v119_feedback ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.friendly_v119_users,public.friendly_v119_saved,
  public.friendly_v119_events,public.friendly_v119_reviews,
  public.friendly_v119_feedback FROM anon,authenticated;
-- The existing Render service role bypasses RLS. Never expose its key.

-- Explicit privileges for your server-side Supabase service-role client.
GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE
  public.friendly_v119_users,public.friendly_v119_saved,
  public.friendly_v119_events,public.friendly_v119_reviews,
  public.friendly_v119_feedback TO service_role;
GRANT USAGE,SELECT ON SEQUENCE public.friendly_v119_events_id_seq TO service_role;
