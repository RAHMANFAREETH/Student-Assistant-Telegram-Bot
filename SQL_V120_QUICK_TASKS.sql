-- V12.0 development only: run in your existing Supabase SQL Editor AFTER local tests.
-- New table only. Does not modify the current assignments, exams or library.
-- Client does not connect to this table: Flask backend uses db.supabase service key.
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
REVOKE ALL ON TABLE public.v120_quick_tasks FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.v120_quick_tasks TO service_role;

-- Enforce 100 tasks per user at the database layer, including concurrent INSERTs.
-- Advisory lock serializes inserts for one user inside a transaction.
CREATE OR REPLACE FUNCTION public.v120_quick_tasks_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    PERFORM pg_catalog.pg_advisory_xact_lock(NEW.user_id);
    IF (SELECT count(*) FROM public.v120_quick_tasks WHERE user_id = NEW.user_id) >= 100 THEN
      RAISE EXCEPTION 'V12 task quota reached' USING ERRCODE = '23514';
    END IF;
  END IF;
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS v120_quick_tasks_guard_trigger ON public.v120_quick_tasks;
CREATE TRIGGER v120_quick_tasks_guard_trigger
BEFORE INSERT OR UPDATE ON public.v120_quick_tasks
FOR EACH ROW EXECUTE FUNCTION public.v120_quick_tasks_guard();
COMMIT;
