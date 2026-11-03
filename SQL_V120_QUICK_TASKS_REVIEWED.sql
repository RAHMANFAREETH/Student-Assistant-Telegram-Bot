-- V12.0 new table only. Run in the existing Supabase SQL Editor before controlled pilot.
-- No existing Library, assignments, or exams schema is changed.
-- The application NEVER sends the Supabase service key to the browser.
BEGIN;
CREATE TABLE IF NOT EXISTS public.v120_quick_tasks (
    user_id bigint NOT NULL CHECK (user_id > 0),
    id uuid NOT NULL,
    title text NOT NULL CHECK (char_length(btrim(title)) BETWEEN 1 AND 160),
    done boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, id)
);
CREATE INDEX IF NOT EXISTS v120_quick_tasks_user_created_idx
    ON public.v120_quick_tasks (user_id, created_at, id);
ALTER TABLE public.v120_quick_tasks ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.v120_quick_tasks FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.v120_quick_tasks TO service_role;

-- Serialize concurrent inserts for each Telegram user so the quota cannot be raced.
CREATE OR REPLACE FUNCTION public.v120_quick_tasks_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    PERFORM pg_catalog.pg_advisory_xact_lock(NEW.user_id);
    IF (SELECT count(*) FROM public.v120_quick_tasks WHERE user_id = NEW.user_id) >= 100 THEN
      RAISE EXCEPTION 'V12 task quota reached' USING ERRCODE = '23514';
    END IF;
  END IF;
  NEW.updated_at := pg_catalog.now();
  RETURN NEW;
END;
$$;
-- Explicitly revoke default function EXECUTE grants from public API roles.
REVOKE ALL ON FUNCTION public.v120_quick_tasks_guard() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.v120_quick_tasks_guard() TO service_role;
DROP TRIGGER IF EXISTS v120_quick_tasks_guard_trigger ON public.v120_quick_tasks;
CREATE TRIGGER v120_quick_tasks_guard_trigger
BEFORE INSERT OR UPDATE ON public.v120_quick_tasks
FOR EACH ROW EXECUTE FUNCTION public.v120_quick_tasks_guard();
COMMIT;
