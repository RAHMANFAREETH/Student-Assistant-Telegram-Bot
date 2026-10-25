-- Student Assistant Bot V7.2 — organization metadata only.
-- Run once in your EXISTING Supabase project SQL Editor.
-- Existing notes, flashcards, and bot settings are not changed.
-- Backend uses the configured Supabase secret/service-role key.
-- No direct anon/authenticated browser access is granted to this table.
CREATE TABLE IF NOT EXISTS public.ai_note_organizer_v72 (
    user_id BIGINT NOT NULL CHECK (user_id > 0),
    note_id BIGINT NOT NULL CHECK (note_id > 0),
    favorite BOOLEAN NOT NULL DEFAULT FALSE,
    subject TEXT NULL CHECK (subject IS NULL OR subject IN
        ('Science', 'Mathematics', 'Languages', 'History', 'Technology', 'General')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ai_note_organizer_v72_pk PRIMARY KEY (user_id, note_id)
);
CREATE INDEX IF NOT EXISTS ai_note_organizer_v72_user_favorites_idx
    ON public.ai_note_organizer_v72 (user_id, favorite, note_id DESC);
CREATE INDEX IF NOT EXISTS ai_note_organizer_v72_user_subject_idx
    ON public.ai_note_organizer_v72 (user_id, subject, note_id DESC);
ALTER TABLE public.ai_note_organizer_v72 ENABLE ROW LEVEL SECURITY;
-- No user-facing RLS policy. Server-only Supabase secret/service-role key is required.
REVOKE ALL ON public.ai_note_organizer_v72 FROM anon, authenticated;
