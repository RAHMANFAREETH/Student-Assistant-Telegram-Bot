-- V5.5 private-tester AI. No question text is stored in this table.
-- Execute ONCE in Supabase SQL Editor (check migration before live deployment).
create table if not exists public.ai_daily_quota (
    user_id bigint not null,
    quota_date date not null default (now() at time zone 'utc')::date,
    request_count integer not null default 0 check (request_count >= 0),
    primary key (user_id, quota_date)
);

-- Privileged Supabase server client only; no direct client writes.
alter table public.ai_daily_quota enable row level security;
revoke all on public.ai_daily_quota from anon, authenticated, public;
grant select, insert, update on public.ai_daily_quota to service_role;

-- Atomic upsert. Maximum quota clamped on the server side.
create or replace function public.ai_claim_daily_quota(p_user_id bigint, p_daily_limit integer)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
    current_count integer;
    max_count integer := least(greatest(coalesce(p_daily_limit, 8), 1), 30);
begin
    if p_user_id is null or p_user_id <= 0 then
        raise exception 'Invalid user id';
    end if;
    insert into public.ai_daily_quota(user_id, quota_date, request_count)
    values (p_user_id, (now() at time zone 'utc')::date, 1)
    on conflict (user_id, quota_date)
        do update set request_count = public.ai_daily_quota.request_count + 1
        where public.ai_daily_quota.request_count < max_count
    returning request_count into current_count;
    return coalesce(current_count, 0);
end;
$$;
revoke all on function public.ai_claim_daily_quota(bigint, integer) from public, anon, authenticated;
grant execute on function public.ai_claim_daily_quota(bigint, integer) to service_role;

-- Optional admin maintenance every few months (does not run automatically):
-- delete from public.ai_daily_quota where quota_date < current_date - 60;
