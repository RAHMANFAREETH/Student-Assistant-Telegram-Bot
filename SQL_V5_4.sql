-- Student Assistant Bot V5.4: independent per-student review schedules.
-- Run in Supabase SQL Editor. Does not change the original flashcards table.
create table if not exists public.flashcard_reviews (
    user_id bigint not null,
    flashcard_id text not null,
    repetitions integer not null default 0 check (repetitions >= 0),
    ease_factor numeric(4,2) not null default 2.50 check (ease_factor between 1.30 and 3.00),
    interval_days integer not null default 0 check (interval_days >= 0),
    due_at timestamptz not null default now(),
    last_reviewed_at timestamptz,
    last_rating text check (last_rating in ('again','hard','good','easy')),
    review_count integer not null default 0 check (review_count >= 0),
    primary key (user_id, flashcard_id)
);
create index if not exists flashcard_reviews_due_idx
    on public.flashcard_reviews (user_id, due_at);
-- Access to this table should remain server-side through the existing
-- SUPABASE_SECRET_KEY in db.py; never expose this key to Telegram clients.
alter table public.flashcard_reviews enable row level security;
revoke all on public.flashcard_reviews from anon, authenticated;
