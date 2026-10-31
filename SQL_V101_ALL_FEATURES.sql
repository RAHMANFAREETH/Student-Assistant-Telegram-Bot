-- V10.1 all 12 study enhancements: ADDITIVE and opt-in. Review and back up first.
-- Backend uses a SERVICE ROLE credential. Never expose it or grant anon writes.
-- Existing V7/V8/V9/V10 schemas and adult verification are untouched.
CREATE TABLE IF NOT EXISTS public.v101_chat_turns (
 id uuid PRIMARY KEY, user_id bigint NOT NULL CHECK (user_id>0),
 question text NOT NULL CHECK(char_length(question) BETWEEN 1 AND 350),
 answer text NOT NULL CHECK(char_length(answer) BETWEEN 1 AND 2500),
 created_at timestamptz NOT NULL DEFAULT now(),
 expires_at timestamptz NOT NULL DEFAULT (now() + interval '14 days')
);
CREATE INDEX IF NOT EXISTS v101_chat_user_recent ON public.v101_chat_turns(user_id,created_at DESC);

CREATE TABLE IF NOT EXISTS public.v101_plans (
 user_id bigint PRIMARY KEY CHECK(user_id>0),
 subject text NOT NULL CHECK(char_length(subject) BETWEEN 1 AND 180),
 days integer NOT NULL CHECK(days IN (7,14,30)),
 minutes_per_day integer NOT NULL CHECK(minutes_per_day BETWEEN 15 AND 240),
 plan jsonb NOT NULL CHECK(jsonb_typeof(plan)='array'),
 updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.v101_mock_mistakes (
 id uuid PRIMARY KEY, user_id bigint NOT NULL CHECK(user_id>0),
 question text NOT NULL, correct_answer text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS v101_mistakes_user_recent ON public.v101_mock_mistakes(user_id,created_at DESC);

CREATE TABLE IF NOT EXISTS public.v101_rooms (
 code text PRIMARY KEY CHECK(char_length(code) BETWEEN 12 AND 24),
 owner_user_id bigint NOT NULL CHECK(owner_user_id>0),
 goal text NOT NULL CHECK(char_length(goal) BETWEEN 3 AND 140),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS v101_room_owner ON public.v101_rooms(owner_user_id);

CREATE TABLE IF NOT EXISTS public.v101_room_members (
 user_id bigint PRIMARY KEY CHECK(user_id>0),
 room_code text NOT NULL REFERENCES public.v101_rooms(code) ON DELETE CASCADE,
 joined_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS v101_member_room ON public.v101_room_members(room_code);

CREATE TABLE IF NOT EXISTS public.v101_room_quizzes (
 id uuid PRIMARY KEY,
 room_code text NOT NULL REFERENCES public.v101_rooms(code) ON DELETE CASCADE,
 question text NOT NULL CHECK(char_length(question) BETWEEN 3 AND 320),
 answer text NOT NULL CHECK(char_length(answer) BETWEEN 1 AND 160),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS v101_room_quiz_recent ON public.v101_room_quizzes(room_code,created_at DESC);

CREATE TABLE IF NOT EXISTS public.v101_room_answers (
 quiz_id uuid NOT NULL REFERENCES public.v101_room_quizzes(id) ON DELETE CASCADE,
 user_id bigint NOT NULL CHECK(user_id>0),
 is_correct boolean NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(quiz_id,user_id)
);

DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['v101_chat_turns','v101_plans','v101_mock_mistakes',
                           'v101_rooms','v101_room_members','v101_room_quizzes','v101_room_answers']
 LOOP EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',t);
      EXECUTE format('REVOKE ALL ON TABLE public.%I FROM anon, authenticated',t);
 END LOOP;
END $$;

-- Explicit service-role table grants; never grant anon or authenticated.
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['v101_chat_turns','v101_plans','v101_mock_mistakes',
                           'v101_rooms','v101_room_members','v101_room_quizzes','v101_room_answers']
 LOOP EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.%I TO service_role',t);
 END LOOP;
END $$;

-- Atomic, bounded room join. Only callable by the authenticated bot backend service role.
CREATE OR REPLACE FUNCTION public.v101_join_study_room(p_user_id bigint,p_code text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=public
AS $$
DECLARE r record; n integer;
BEGIN
 IF p_user_id IS NULL OR p_user_id<=0 OR p_code IS NULL OR length(p_code)>24 THEN
  RAISE EXCEPTION 'Invalid study room request';
 END IF;
 SELECT code INTO r FROM public.v101_rooms AS rooms
  WHERE rooms.code=p_code FOR UPDATE;
 IF NOT FOUND THEN RETURN 'missing'; END IF;
 IF EXISTS(SELECT 1 FROM public.v101_room_members AS m WHERE m.user_id=p_user_id) THEN
   IF EXISTS(SELECT 1 FROM public.v101_room_members AS m WHERE m.user_id=p_user_id AND m.room_code=p_code)
   THEN RETURN 'already_member'; ELSE RETURN 'already_in_room'; END IF;
 END IF;
 SELECT count(*) INTO n FROM public.v101_room_members AS m WHERE m.room_code=p_code;
 IF n>=12 THEN RETURN 'full'; END IF;
 INSERT INTO public.v101_room_members(user_id,room_code) VALUES(p_user_id,p_code);
 RETURN 'joined';
END;
$$;
REVOKE ALL ON FUNCTION public.v101_join_study_room(bigint,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.v101_join_study_room(bigint,text) TO service_role;

-- No public read policies or client-side user_id trust. Verify RLS before enabling.
