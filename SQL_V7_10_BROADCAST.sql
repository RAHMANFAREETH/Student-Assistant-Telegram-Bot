-- V7.10: private bot announcements; apply using Supabase SQL editor.
-- Users must opt in. The bot already uses a server-side Supabase secret key.
-- This table contains Telegram numeric identifiers, not message content.
create table if not exists public.bot_broadcast_subscribers (
  user_id bigint primary key,
  chat_id bigint not null,
  subscribed boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint bot_broadcast_user_private_chat check (user_id > 0 and chat_id = user_id)
);

alter table public.bot_broadcast_subscribers enable row level security;
-- No anon/authenticated policies; only the existing server-side service-role key accesses it.
-- Do not expose SUPABASE_SECRET_KEY to client apps or commit it to Git.
create index if not exists bot_broadcast_subscribers_active_idx
  on public.bot_broadcast_subscribers (subscribed) where subscribed = true;
