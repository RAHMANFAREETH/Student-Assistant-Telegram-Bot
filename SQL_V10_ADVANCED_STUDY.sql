-- V10 Learning Lab: review before running on your existing Supabase project.
-- No DROP/ALTER of V7/V8/V9 tables. Existing service-role credentials stay server-side.
create table if not exists public.v10_documents (
 id uuid primary key, user_id bigint not null,
 title text not null check(char_length(title) between 1 and 100),
 filename text not null check(char_length(filename) between 1 and 120),
 created_at timestamptz not null default now()
);
create index if not exists v10_documents_user on public.v10_documents(user_id,created_at desc);

create table if not exists public.v10_document_chunks (
 id uuid primary key,
 document_id uuid not null references public.v10_documents(id) on delete cascade,
 user_id bigint not null,
 page_number integer not null check(page_number between 1 and 1000),
 body text not null check(char_length(body) between 1 and 1350),
 created_at timestamptz not null default now()
);
create index if not exists v10_chunks_user on public.v10_document_chunks(user_id,document_id,page_number);

create table if not exists public.v10_card_schedule (
 user_id bigint not null,flashcard_id bigint not null,
 due_at timestamptz not null,
 interval_days integer not null check(interval_days between 1 and 180),
 repetitions integer not null default 0 check(repetitions>=0),
 last_rating text not null check(last_rating in ('again','hard','good','easy')),
 reviewed_at timestamptz not null default now(),
 primary key(user_id,flashcard_id)
);
create index if not exists v10_schedule_user_due on public.v10_card_schedule(user_id,due_at);

alter table public.v10_documents enable row level security;
alter table public.v10_document_chunks enable row level security;
alter table public.v10_card_schedule enable row level security;
revoke all on public.v10_documents from anon, authenticated;
revoke all on public.v10_document_chunks from anon, authenticated;
revoke all on public.v10_card_schedule from anon, authenticated;
-- Do not create permissive client policies: access only from bot server service-role key.
-- App-side queries always filter by Telegram user_id. Never expose service-role credentials.
-- Be aware: readable document excerpts are retained in Supabase until /v10delete.


-- V10 Gemini edition: separate, atomic per-user UTC-day quota.
-- Independent from all Cloudflare quotas and V8/V9 access tables.
create table if not exists public.v10_gemini_daily_quota (
    user_id bigint not null check (user_id > 0),
    quota_date date not null,
    request_count integer not null check (request_count between 0 and 10),
    primary key (user_id, quota_date)
);
alter table public.v10_gemini_daily_quota enable row level security;
revoke all on public.v10_gemini_daily_quota from anon, authenticated;

create or replace function public.v10_claim_gemini_quota(
    p_user_id bigint, p_daily_limit integer
) returns integer
language plpgsql
security definer
set search_path = public
as $$
declare v_used integer;
begin
    if p_user_id is null or p_user_id <= 0 or
       p_daily_limit is null or p_daily_limit not between 1 and 10 then
        raise exception 'Invalid V10 Gemini quota request';
    end if;
    insert into public.v10_gemini_daily_quota as q (user_id, quota_date, request_count)
        values (p_user_id, (now() at time zone 'UTC')::date, 1)
    on conflict (user_id, quota_date) do update
        set request_count = q.request_count + 1
        where q.request_count < p_daily_limit
    returning request_count into v_used;
    return coalesce(v_used, 0);
end;
$$;
revoke all on function public.v10_claim_gemini_quota(bigint, integer) from public, anon, authenticated;
grant execute on function public.v10_claim_gemini_quota(bigint, integer) to service_role;
-- Review grant and function ownership in your Supabase deployment before enabling.
