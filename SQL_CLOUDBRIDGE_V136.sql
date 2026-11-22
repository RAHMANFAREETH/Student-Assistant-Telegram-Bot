-- V13.6 incremental migration. Apply AFTER SQL_CLOUDBRIDGE_V134.sql.
-- Back up/review before running; preserve all V13.4 accounts and jobs.
alter table public.cloudbridge_jobs_v134
  add column if not exists total_bytes bigint check (total_bytes is null or total_bytes > 0),
  add column if not exists source_version text,
  add column if not exists upload_state_ciphertext text,
  add column if not exists result_file_id text,
  add column if not exists stage text,
  add column if not exists pause_requested boolean not null default false;

alter table public.cloudbridge_jobs_v134 drop constraint if exists cloudbridge_jobs_v134_status_check;
alter table public.cloudbridge_jobs_v134 add constraint cloudbridge_jobs_v134_status_check
  check (status in ('queued','running','paused','completed','failed','cancelled','needs_review'));

-- Persist and fence Google resumable sessions; only a job with an encrypted
-- upload session may be automatically reclaimed. Others stay for manual review.
-- Progress heartbeat refreshes claimed_at at every acknowledged 5-MiB chunk.
create or replace function public.cloudbridge_claim_job_v134(p_worker text)
returns setof public.cloudbridge_jobs_v134
language plpgsql security definer set search_path = '' as $$
begin
  return query
    with next_job as (
      select id from public.cloudbridge_jobs_v134
      where (
        (status = 'queued' and cancel_requested = false)
        or (status = 'running' and cancel_requested = false and pause_requested = false
            and (upload_state_ciphertext is not null or stage = 'preparing')
            and destination_provider = 'google'
            and claimed_at < now() - interval '15 minutes')
      ) and attempts < 3
      order by created_at, id
      for update skip locked limit 1
    )
    update public.cloudbridge_jobs_v134 j
      set status = 'running', claimed_at = now(), worker = left(p_worker, 80),
          attempts = j.attempts + 1
    from next_job
    where j.id = next_job.id
    returning j.*;
end $$;

revoke all on function public.cloudbridge_claim_job_v134(text) from public, anon, authenticated;
grant execute on function public.cloudbridge_claim_job_v134(text) to service_role;

-- Admin-only inspection: stale jobs without resumable session require review.
-- select id,stage,attempts,claimed_at from public.cloudbridge_jobs_v134
-- where status='running' and claimed_at < now()-interval '15 minutes';
