-- Student Assistant V13.4. Run once in Supabase SQL editor after backup/review.
-- Private server-owned tables; NO public/authenticated RLS access.
create table if not exists public.cloudbridge_accounts_v134 (
  user_id bigint not null check (user_id > 0),
  provider text not null check (provider in ('google','onedrive','dropbox')),
  tokens_ciphertext text not null check (length(tokens_ciphertext) between 30 and 16384),
  created_at timestamptz not null default now(),
  primary key (user_id, provider)
);
create table if not exists public.cloudbridge_oauth_states_v134 (
  state_hash text primary key check (length(state_hash) = 64),
  user_id bigint not null check (user_id > 0),
  provider text not null check (provider in ('google','onedrive','dropbox')),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default (now() + interval '10 minutes')
);
create index if not exists cloudbridge_oauth_expiry_v134 on public.cloudbridge_oauth_states_v134 (expires_at);
create table if not exists public.cloudbridge_jobs_v134 (
  id uuid primary key,
  user_id bigint not null check (user_id > 0),
  filename text not null check (length(filename) between 1 and 160),
  source_kind text not null check (source_kind in ('telegram', 'provider', 'url')),
  source_provider text check (source_provider is null or source_provider in ('google','onedrive','dropbox')),
  source_ref text not null check (length(source_ref) between 1 and 2048),
  destination_kind text not null check (destination_kind in ('telegram','provider')),
  destination_provider text check (destination_provider is null or destination_provider in ('google','onedrive','dropbox')),
  destination_path text,
  status text not null default 'queued' check (status in ('queued','running','completed','failed','cancelled','needs_review')),
  cancel_requested boolean not null default false,
  attempts int not null default 0 check (attempts between 0 and 3),
  bytes_done bigint not null default 0 check (bytes_done >= 0),
  worker text,
  error_code text,
  claimed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check ((source_kind = 'provider') = (source_provider is not null)),
  check ((destination_kind = 'provider') = (destination_provider is not null)),
  check ((destination_kind = 'provider') = (destination_path is not null))
);
create index if not exists cloudbridge_jobs_user_v134 on public.cloudbridge_jobs_v134 (user_id, created_at desc);
create index if not exists cloudbridge_jobs_queue_v134 on public.cloudbridge_jobs_v134 (created_at)
  where status = 'queued' and cancel_requested = false;

alter table public.cloudbridge_accounts_v134 enable row level security;
alter table public.cloudbridge_oauth_states_v134 enable row level security;
alter table public.cloudbridge_jobs_v134 enable row level security;
revoke all on public.cloudbridge_accounts_v134 from public, anon, authenticated;
revoke all on public.cloudbridge_oauth_states_v134 from public, anon, authenticated;
revoke all on public.cloudbridge_jobs_v134 from public, anon, authenticated;
grant all on public.cloudbridge_accounts_v134 to service_role;
grant all on public.cloudbridge_oauth_states_v134 to service_role;
grant all on public.cloudbridge_jobs_v134 to service_role;

create or replace function public.cloudbridge_guard_insert_v134()
returns trigger language plpgsql set search_path = '' as $$
begin
  if (select count(*) from public.cloudbridge_jobs_v134 where user_id = new.user_id) >= 100 then
    raise exception 'CloudBridge job history quota reached';
  end if;
  if (select count(*) from public.cloudbridge_jobs_v134
      where user_id = new.user_id and status in ('queued','running')) >= 5 then
    raise exception 'CloudBridge active transfer quota reached';
  end if;
  return new;
end $$;
drop trigger if exists cloudbridge_guard_insert_trigger_v134 on public.cloudbridge_jobs_v134;
create trigger cloudbridge_guard_insert_trigger_v134 before insert on public.cloudbridge_jobs_v134
  for each row execute function public.cloudbridge_guard_insert_v134();

create or replace function public.cloudbridge_stamp_v134()
returns trigger language plpgsql set search_path = '' as $$
begin
  new.updated_at = now();
  return new;
end $$;
drop trigger if exists cloudbridge_stamp_trigger_v134 on public.cloudbridge_jobs_v134;
create trigger cloudbridge_stamp_trigger_v134 before update on public.cloudbridge_jobs_v134
  for each row execute function public.cloudbridge_stamp_v134();

-- A callback can consume state exactly once, including under concurrency.
create or replace function public.cloudbridge_consume_oauth_v134(p_hash text)
returns table(user_id bigint, provider text)
language plpgsql security definer set search_path = '' as $$
begin
  return query
    delete from public.cloudbridge_oauth_states_v134 s
    where s.state_hash = p_hash and s.expires_at > now()
    returning s.user_id, s.provider;
end $$;

-- Atomic SKIP LOCKED claim: safe across Gunicorn worker processes.
-- Stale running jobs are intentionally NOT requeued: a remote file may
-- already exist, and auto-retry could duplicate it.
create or replace function public.cloudbridge_claim_job_v134(p_worker text)
returns setof public.cloudbridge_jobs_v134
language plpgsql security definer set search_path = '' as $$
begin
  return query
    with next_job as (
      select id from public.cloudbridge_jobs_v134
      where status = 'queued' and cancel_requested = false and attempts < 3
      order by created_at, id
      for update skip locked limit 1
    )
    update public.cloudbridge_jobs_v134 j
      set status='running', claimed_at=now(), worker=left(p_worker, 80), attempts=j.attempts+1
    from next_job
    where j.id=next_job.id
    returning j.*;
end $$;
revoke all on function public.cloudbridge_consume_oauth_v134(text) from public, anon, authenticated;
revoke all on function public.cloudbridge_claim_job_v134(text) from public, anon, authenticated;
grant execute on function public.cloudbridge_consume_oauth_v134(text) to service_role;
grant execute on function public.cloudbridge_claim_job_v134(text) to service_role;

-- Operational maintenance (run manually after checking destinations):
-- select id,user_id,filename,claimed_at from public.cloudbridge_jobs_v134
-- where status='running' and claimed_at < now()-interval '30 minutes';
-- Manually mark a stranded job 'needs_review' after inspection; NEVER
-- automatically reset running transfers to queued.
