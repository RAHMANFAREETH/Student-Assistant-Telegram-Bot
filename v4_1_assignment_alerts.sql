-- =========================================================
-- STUDENT ASSISTANT BOT V4.1
-- Assignment deadline alerts + dashboard support
-- =========================================================

-- 1) Add fields needed for Telegram deadline alerts.
alter table public.assignments
add column if not exists chat_id bigint;

alter table public.assignments
add column if not exists reminder_24h_sent boolean not null default false;

alter table public.assignments
add column if not exists reminder_3h_sent boolean not null default false;

alter table public.assignments
add column if not exists reminder_due_sent boolean not null default false;


create index if not exists assignments_alert_idx
on public.assignments (
    status,
    due_at,
    reminder_24h_sent,
    reminder_3h_sent,
    reminder_due_sent
);


-- 2) pg_net is used for Telegram HTTP requests.
create extension if not exists pg_net;


-- 3) Queue one Telegram message through pg_net.
create or replace function public.queue_telegram_message(
    p_chat_id bigint,
    p_text text
)
returns bigint
language plpgsql
security definer
set search_path = public, extensions, vault
as $$
declare
    token text;
    request_id bigint;
begin

    select decrypted_secret
    into token
    from vault.decrypted_secrets
    where name = 'telegram_bot_token'
    limit 1;

    if token is null or token = '' then
        raise exception 'telegram_bot_token was not found in Vault';
    end if;

    select net.http_post(
        url := 'https://api.telegram.org/bot'
               || token
               || '/sendMessage',

        headers := jsonb_build_object(
            'Content-Type',
            'application/json'
        ),

        body := jsonb_build_object(
            'chat_id',
            p_chat_id,
            'text',
            p_text
        ),

        timeout_milliseconds := 5000
    )
    into request_id;

    return request_id;
end;
$$;


-- 4) Send deadline alerts.
create or replace function public.send_assignment_deadline_alerts()
returns void
language plpgsql
security definer
set search_path = public, extensions, vault
as $$
declare
    r record;
    local_due text;
    subject_name text;
begin

    -- =====================================================
    -- WITHIN 24 HOURS
    -- =====================================================

    for r in
        select
            a.id,
            a.chat_id,
            a.title,
            a.due_at,
            a.subject_id
        from public.assignments a
        where a.status = 'pending'
          and a.chat_id is not null
          and a.reminder_24h_sent = false
          and a.due_at > now() + interval '3 hours'
          and a.due_at <= now() + interval '24 hours'
        order by a.due_at
        for update skip locked
    loop

        select s.name
        into subject_name
        from public.subjects s
        where s.id = r.subject_id
        limit 1;

        local_due := to_char(
            r.due_at at time zone 'Asia/Colombo',
            'DD-MM-YYYY HH12:MI AM'
        );

        perform public.queue_telegram_message(
            r.chat_id,
            '📅 Assignment Reminder'
            || E'\n\n⏳ Due within 24 hours'
            || E'\n📌 ' || r.title
            || case
                when subject_name is not null
                then E'\n📚 ' || subject_name
                else ''
               end
            || E'\n🕒 ' || local_due
            || E'\n\nPlan enough time to finish and submit it.'
        );

        update public.assignments
        set reminder_24h_sent = true
        where id = r.id;

    end loop;


    -- =====================================================
    -- WITHIN 3 HOURS
    -- =====================================================

    for r in
        select
            a.id,
            a.chat_id,
            a.title,
            a.due_at,
            a.subject_id
        from public.assignments a
        where a.status = 'pending'
          and a.chat_id is not null
          and a.reminder_3h_sent = false
          and a.due_at > now()
          and a.due_at <= now() + interval '3 hours'
        order by a.due_at
        for update skip locked
    loop

        select s.name
        into subject_name
        from public.subjects s
        where s.id = r.subject_id
        limit 1;

        local_due := to_char(
            r.due_at at time zone 'Asia/Colombo',
            'DD-MM-YYYY HH12:MI AM'
        );

        perform public.queue_telegram_message(
            r.chat_id,
            '🚨 Assignment Deadline Alert'
            || E'\n\n⏰ Less than 3 hours remaining'
            || E'\n📌 ' || r.title
            || case
                when subject_name is not null
                then E'\n📚 ' || subject_name
                else ''
               end
            || E'\n🕒 ' || local_due
            || E'\n\nFinish and submit it before the deadline.'
        );

        update public.assignments
        set
            reminder_24h_sent = true,
            reminder_3h_sent = true
        where id = r.id;

    end loop;


    -- =====================================================
    -- DEADLINE REACHED
    -- =====================================================

    for r in
        select
            a.id,
            a.chat_id,
            a.title,
            a.due_at,
            a.subject_id
        from public.assignments a
        where a.status = 'pending'
          and a.chat_id is not null
          and a.reminder_due_sent = false
          and a.due_at <= now()
        order by a.due_at
        for update skip locked
    loop

        select s.name
        into subject_name
        from public.subjects s
        where s.id = r.subject_id
        limit 1;

        local_due := to_char(
            r.due_at at time zone 'Asia/Colombo',
            'DD-MM-YYYY HH12:MI AM'
        );

        perform public.queue_telegram_message(
            r.chat_id,
            '⚠️ Assignment Deadline Reached'
            || E'\n\n📌 ' || r.title
            || case
                when subject_name is not null
                then E'\n📚 ' || subject_name
                else ''
               end
            || E'\n🕒 ' || local_due
            || E'\n\nIf you already submitted it, mark it completed in the bot.'
        );

        update public.assignments
        set
            reminder_24h_sent = true,
            reminder_3h_sent = true,
            reminder_due_sent = true
        where id = r.id;

    end loop;

end;
$$;


-- 5) Ensure Cron is available.
create extension if not exists pg_cron;


-- 6) Run assignment alert checks every 5 minutes.
select cron.schedule(
    'student-assignment-alerts',
    '*/5 * * * *',
    $$select public.send_assignment_deadline_alerts();$$
);


-- 7) Verify with:
-- select jobid, jobname, schedule, command, active
-- from cron.job
-- where jobname = 'student-assignment-alerts';
