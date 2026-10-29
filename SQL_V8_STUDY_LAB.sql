-- V8 Study Lab: persistent group quiz battles. Apply manually in Supabase SQL Editor.
-- The bot uses an existing server-only service key, never an exposed browser key.
create table if not exists public.v8_quiz_battles (
  id uuid primary key,
  group_id bigint not null,
  created_by bigint not null,
  question text not null check (char_length(question) <= 260),
  options jsonb not null,
  correct text not null check (correct in ('A','B','C','D')),
  created_at timestamptz not null default now(),
  ends_at timestamptz not null,
  active boolean not null default true
);
create index if not exists v8_battle_lookup on public.v8_quiz_battles (group_id,created_at desc);
create table if not exists public.v8_quiz_answers (
  battle_id uuid not null references public.v8_quiz_battles(id) on delete cascade,
  user_id bigint not null,
  choice text not null check (choice in ('A','B','C','D')),
  correct boolean not null,
  created_at timestamptz not null default now(),
  primary key (battle_id,user_id)
);
create index if not exists v8_answer_battle on public.v8_quiz_answers(battle_id);
alter table public.v8_quiz_battles enable row level security;
alter table public.v8_quiz_answers enable row level security;
revoke all on public.v8_quiz_battles from anon,authenticated;
revoke all on public.v8_quiz_answers from anon,authenticated;
-- No anon/authenticated policies. Bot's secret service-role key stays server-side.
