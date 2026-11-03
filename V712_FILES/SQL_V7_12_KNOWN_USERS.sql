-- V7.12: Announcements for known existing bot users, without /subscribe.
-- Apply in the EXISTING Supabase SQL Editor after V7.10 broadcast SQL.
-- Stores numeric Telegram user/chat identifiers only; NEVER stores message content.
-- Explicit /unsubscribe choices remain in bot_broadcast_subscribers and are honored.
-- No existing study data is modified.

CREATE TABLE IF NOT EXISTS public.bot_known_users_v712 (
    user_id BIGINT PRIMARY KEY CHECK (user_id > 0),
    chat_id BIGINT NOT NULL CHECK (chat_id = user_id),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NULL,
    source TEXT NOT NULL DEFAULT 'private_chat'
        CHECK (source IN ('private_chat','historical_import'))
);

ALTER TABLE public.bot_known_users_v712 ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.bot_known_users_v712 FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE public.bot_known_users_v712 TO service_role;
-- Keep the existing preference table server-only as well.
GRANT SELECT, INSERT, UPDATE ON TABLE public.bot_broadcast_subscribers TO service_role;

-- Import numeric user IDs that were previously saved while using study features.
-- Missing/optional tables are safely skipped. Never changes or deletes their data.
-- Historical IDs may not have previously started a private Telegram chat; Telegram
-- will reject delivery to those users, and the bot will remember blocked targets.
DO $migration$
DECLARE
    src_table TEXT;
BEGIN
    FOREACH src_table IN ARRAY ARRAY[
        'ui_language_v57', 'notes', 'subjects', 'assignments',
        'study_materials', 'flashcards', 'ai_daily_quota',
        'study_sessions', 'quiz_attempts', 'voice_notes',
        'reminders', 'exams', 'translation_history',
        'study_preferences', 'timetable_entries',
        'ai_study_collections_v73', 'ai_note_organizer_v72',
        'bot_broadcast_subscribers'
    ]
    LOOP
        IF to_regclass('public.' || src_table) IS NOT NULL
           AND EXISTS (
             SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public'
               AND table_name = src_table
               AND column_name = 'user_id'
           ) THEN
            EXECUTE format(
                'INSERT INTO public.bot_known_users_v712'
                || '(user_id, chat_id, last_seen_at, source) '
                || 'SELECT DISTINCT user_id::BIGINT, user_id::BIGINT, NULL, '
                || '''historical_import'' '
                || 'FROM public.%I WHERE user_id IS NOT NULL AND user_id::BIGINT > 0 '
                || 'ON CONFLICT (user_id) DO NOTHING', src_table
            );
        END IF;
    END LOOP;
END;
$migration$;

-- Inspect counts, not personal IDs. Compare with the known size of your user group.
SELECT COUNT(*) AS known_user_ids FROM public.bot_known_users_v712;
