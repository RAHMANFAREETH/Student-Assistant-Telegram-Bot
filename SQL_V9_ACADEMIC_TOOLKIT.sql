-- V9 Academic Toolkit: apply once to existing Supabase SQL Editor.
-- Bot only: server-side service-role credential. No browser-accessible rows.
create table if not exists public.v9_syllabus_topics (
 id uuid primary key, user_id bigint not null, title text not null check (char_length(title) between 3 and 120),
 completed boolean not null default false, created_at timestamptz not null default now());
create index if not exists v9_syllabus_owner on public.v9_syllabus_topics(user_id, created_at);

create table if not exists public.v9_mistakes (
 id uuid primary key, user_id bigint not null, topic text not null check (char_length(topic) <= 350),
 question text not null check (char_length(question) <= 350),
 answer text not null check (char_length(answer) <= 350),
 mastered boolean not null default false, created_at timestamptz not null default now());
create index if not exists v9_mistake_owner on public.v9_mistakes(user_id, created_at desc);

create table if not exists public.v9_focus_sessions (
 id uuid primary key, user_id bigint not null, starts_at timestamptz not null,
 ends_at timestamptz not null, minutes integer not null check(minutes between 5 and 90),
 completed boolean not null default false, created_at timestamptz not null default now());
create index if not exists v9_focus_owner on public.v9_focus_sessions(user_id, starts_at desc);

create table if not exists public.v9_study_rooms (
 id uuid primary key, creator_id bigint not null, title text not null check(char_length(title) between 4 and 70),
 join_code text not null unique check(char_length(join_code)=16), active boolean not null default true,
 created_at timestamptz not null default now());
create table if not exists public.v9_room_members (
 room_id uuid not null references public.v9_study_rooms(id) on delete cascade,
 user_id bigint not null, joined_at timestamptz not null default now(),
 primary key(room_id,user_id));
create index if not exists v9_room_member_owner on public.v9_room_members(user_id);
create table if not exists public.v9_room_notes (
 id uuid primary key, room_id uuid not null references public.v9_study_rooms(id) on delete cascade,
 user_id bigint not null, body text not null check(char_length(body) between 1 and 600),
 created_at timestamptz not null default now());
create index if not exists v9_notes_room on public.v9_room_notes(room_id,created_at desc);

alter table public.v9_syllabus_topics enable row level security;
alter table public.v9_mistakes enable row level security;
alter table public.v9_focus_sessions enable row level security;
alter table public.v9_study_rooms enable row level security;
alter table public.v9_room_members enable row level security;
alter table public.v9_room_notes enable row level security;
revoke all on public.v9_syllabus_topics from anon, authenticated;
revoke all on public.v9_mistakes from anon, authenticated;
revoke all on public.v9_focus_sessions from anon, authenticated;
revoke all on public.v9_study_rooms from anon, authenticated;
revoke all on public.v9_room_members from anon, authenticated;
revoke all on public.v9_room_notes from anon, authenticated;
-- Application must always scope reads and changes by Telegram user ID or verified room membership.
-- Review database role grants in Supabase after migration.
