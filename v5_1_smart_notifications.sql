-- =========================================================
-- STUDENT ASSISTANT BOT V5.1
-- Smart Notifications Center
-- Daily Brief + Weekly Review
-- =========================================================

create table if not exists public.notification_preferences (
    user_id bigint primary key,
    chat_id bigint not null,

    timezone text not null default 'Asia/Colombo',

    daily_brief_enabled boolean not null default true,
    daily_brief_hour integer not null default 7
        check (daily_brief_hour between 0 and 23),

    weekly_review_enabled boolean not null default true,
    weekly_review_dow integer not null default 0
        check (weekly_review_dow between 0 and 6),
    weekly_review_hour integer not null default 18
        check (weekly_review_hour between 0 and 23),

    last_daily_brief_date date,
    last_weekly_review_date date,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.notification_preferences
enable row level security;

grant select, insert, update, delete
on public.notification_preferences
to service_role;


-- =========================================================
-- TELEGRAM QUEUE HELPER
-- Safe to replace if an earlier version already created it.
-- =========================================================

create extension if not exists pg_net;

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
        raise exception
            'telegram_bot_token was not found in Supabase Vault';
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


-- =========================================================
-- SMART NOTIFICATION WORKER
-- Runs frequently; sends at most once per local date.
-- =========================================================

create or replace function public.send_smart_notifications()
returns void
language plpgsql
security definer
set search_path = public, extensions, vault
as $$
declare
    p record;

    local_now timestamp;
    local_date date;
    local_dow integer;

    day_start_utc timestamptz;
    next_day_start_utc timestamptz;
    week_ago_utc timestamptz;
    week_ahead_utc timestamptz;

    today_classes integer;
    due_today integer;
    overdue_assignments integer;
    exams_7d integer;
    active_goals integer;

    study_minutes_7d integer;
    completed_assignments_7d integer;
    quiz_average_7d numeric;

    daily_text text;
    weekly_text text;
begin

    for p in
        select *
        from public.notification_preferences
        order by user_id
    loop

        begin
            -- Validate timezone and derive local time.
            local_now := now() at time zone p.timezone;
        exception
            when others then
                -- Invalid timezone should not break the whole cron job.
                continue;
        end;

        local_date := local_now::date;
        local_dow := extract(dow from local_now)::integer;

        day_start_utc :=
            local_date::timestamp
            at time zone p.timezone;

        next_day_start_utc :=
            (local_date + 1)::timestamp
            at time zone p.timezone;

        week_ago_utc :=
            (local_now - interval '7 days')
            at time zone p.timezone;

        week_ahead_utc :=
            (local_now + interval '7 days')
            at time zone p.timezone;


        -- =================================================
        -- DAILY BRIEF
        -- =================================================

        if p.daily_brief_enabled
           and extract(hour from local_now)::integer
               = p.daily_brief_hour
           and p.last_daily_brief_date
               is distinct from local_date
        then

            select count(*)
            into today_classes
            from public.timetable_entries t
            where t.user_id = p.user_id
              and t.day_of_week
                  = extract(isodow from local_now)::integer - 1;


            select count(*)
            into due_today
            from public.assignments a
            where a.user_id = p.user_id
              and a.status = 'pending'
              and a.due_at >= day_start_utc
              and a.due_at < next_day_start_utc;


            select count(*)
            into overdue_assignments
            from public.assignments a
            where a.user_id = p.user_id
              and a.status = 'pending'
              and a.due_at < now();


            select count(*)
            into exams_7d
            from public.exams e
            where e.user_id = p.user_id
              and e.exam_at >= now()
              and e.exam_at <= week_ahead_utc;


            select count(*)
            into active_goals
            from public.study_goals g
            where g.user_id = p.user_id
              and g.status = 'pending';


            daily_text :=
                '☀️ Morning Study Brief'
                || E'\n\n📅 '
                || to_char(local_date, 'DD-MM-YYYY')
                || E'\n\n🗓 Classes today: '
                || coalesce(today_classes, 0)
                || E'\n📚 Assignments due today: '
                || coalesce(due_today, 0)
                || E'\n⚠️ Overdue assignments: '
                || coalesce(overdue_assignments, 0)
                || E'\n📝 Exams in next 7 days: '
                || coalesce(exams_7d, 0)
                || E'\n🎯 Active study goals: '
                || coalesce(active_goals, 0)
                || E'\n\nOpen ☀️ Today Hub for full details.';


            perform public.queue_telegram_message(
                p.chat_id,
                daily_text
            );


            update public.notification_preferences
            set
                last_daily_brief_date = local_date,
                updated_at = now()
            where user_id = p.user_id;

        end if;


        -- =================================================
        -- WEEKLY REVIEW
        -- =================================================

        if p.weekly_review_enabled
           and local_dow = p.weekly_review_dow
           and extract(hour from local_now)::integer
               = p.weekly_review_hour
           and p.last_weekly_review_date
               is distinct from local_date
        then

            select coalesce(
                sum(
                    coalesce(
                        s.actual_minutes,
                        s.planned_minutes,
                        0
                    )
                ),
                0
            )
            into study_minutes_7d
            from public.study_sessions s
            where s.user_id = p.user_id
              and s.status = 'completed'
              and s.started_at >= week_ago_utc;


            select count(*)
            into completed_assignments_7d
            from public.assignments a
            where a.user_id = p.user_id
              and a.status = 'completed'
              and a.completed_at is not null
              and a.completed_at >= week_ago_utc;


            select round(
                avg(q.score_percent)::numeric,
                1
            )
            into quiz_average_7d
            from public.quiz_attempts q
            where q.user_id = p.user_id
              and q.created_at >= week_ago_utc;


            select count(*)
            into overdue_assignments
            from public.assignments a
            where a.user_id = p.user_id
              and a.status = 'pending'
              and a.due_at < now();


            select count(*)
            into exams_7d
            from public.exams e
            where e.user_id = p.user_id
              and e.exam_at >= now()
              and e.exam_at <= week_ahead_utc;


            weekly_text :=
                '📅 Weekly Study Review'
                || E'\n\n⏱ Study time: '
                || coalesce(study_minutes_7d, 0)
                || ' minutes'
                || E'\n✅ Assignments completed: '
                || coalesce(completed_assignments_7d, 0)
                || E'\n❓ Quiz average: '
                || case
                    when quiz_average_7d is null
                    then 'No quiz data'
                    else quiz_average_7d::text || '%'
                   end
                || E'\n⚠️ Current overdue assignments: '
                || coalesce(overdue_assignments, 0)
                || E'\n📝 Exams in next 7 days: '
                || coalesce(exams_7d, 0)
                || E'\n\nOpen 🧠 Smart Insights for subject priorities.';


            perform public.queue_telegram_message(
                p.chat_id,
                weekly_text
            );


            update public.notification_preferences
            set
                last_weekly_review_date = local_date,
                updated_at = now()
            where user_id = p.user_id;

        end if;

    end loop;

end;
$$;


-- =========================================================
-- CRON
-- Every 15 minutes.
-- The worker checks each user's local timezone/hour.
-- =========================================================

create extension if not exists pg_cron;

select cron.unschedule(jobid)
from cron.job
where jobname = 'student-smart-notifications';

select cron.schedule(
    'student-smart-notifications',
    '*/15 * * * *',
    $$select public.send_smart_notifications();$$
);


-- =========================================================
-- VERIFY
-- =========================================================

-- select
--     jobid,
--     jobname,
--     schedule,
--     command,
--     active
-- from cron.job
-- where jobname = 'student-smart-notifications';
