-- Run read-only after the migration. Expected: RLS=TRUE and no anon/authenticated grants.
SELECT c.relname, c.relrowsecurity AS rls_enabled,
       c.relforcerowsecurity AS rls_forced
FROM pg_catalog.pg_class AS c
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = 'v120_quick_tasks';

SELECT grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema='public' AND table_name='v120_quick_tasks'
ORDER BY grantee, privilege_type;

SELECT tgname, tgenabled FROM pg_catalog.pg_trigger
WHERE tgrelid = 'public.v120_quick_tasks'::regclass AND NOT tgisinternal;

SELECT has_function_privilege('anon','public.v120_quick_tasks_guard()','EXECUTE') AS anon_execute,
       has_function_privilege('authenticated','public.v120_quick_tasks_guard()','EXECUTE') AS authenticated_execute;
