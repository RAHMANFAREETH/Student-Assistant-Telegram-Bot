-- Optional V5.7 language preference persistence; run in the existing Supabase SQL Editor.
-- This does not alter any existing notes, flashcards, students or AI quota tables.
create table if not exists public.ui_language_v57 (
  user_id bigint primary key,
  language text not null default 'en'
    check (language in ('en','ta','si','ar')),
  updated_at timestamptz not null default now()
);

alter table public.ui_language_v57 enable row level security;
revoke all on table public.ui_language_v57 from public, anon, authenticated;
grant select, insert, update, delete on table public.ui_language_v57 to service_role;
-- Access only from the trusted server-side Supabase client using service-role credentials.
-- Never expose service-role credentials in Telegram messages or client-side applications.
