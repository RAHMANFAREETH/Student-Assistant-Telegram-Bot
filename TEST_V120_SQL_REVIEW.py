"""Static guardrails, not a replacement for running the migration in Supabase."""
from pathlib import Path
import unittest

SQL = (Path(__file__).resolve().parent / 'SQL_V120_QUICK_TASKS_REVIEWED.sql').read_text(encoding='utf-8')

class SqlMigrationReview(unittest.TestCase):
    def test_only_new_task_table_mentioned_by_ddl(self):
        self.assertIn('CREATE TABLE IF NOT EXISTS public.v120_quick_tasks',SQL)
        for stmt in ('DROP TABLE', 'TRUNCATE', 'ALTER TABLE public.assignments',
                     'ALTER TABLE public.exams', 'ALTER TABLE public.book_'):
            self.assertNotIn(stmt,SQL)

    def test_row_level_security_and_client_revoke(self):
        self.assertIn('ENABLE ROW LEVEL SECURITY',SQL)
        self.assertIn('REVOKE ALL ON TABLE public.v120_quick_tasks FROM PUBLIC, anon, authenticated',SQL)
        self.assertIn('TO service_role',SQL)

    def test_guard_quota_and_transaction(self):
        self.assertIn('pg_advisory_xact_lock(NEW.user_id)',SQL)
        self.assertIn('>= 100',SQL)
        self.assertIn('BEGIN;',SQL)
        self.assertIn('COMMIT;',SQL)

    def test_trigger_exec_privilege_is_hardened(self):
        self.assertIn('REVOKE ALL ON FUNCTION public.v120_quick_tasks_guard() FROM PUBLIC, anon, authenticated',SQL)
        self.assertIn('GRANT EXECUTE ON FUNCTION public.v120_quick_tasks_guard() TO service_role',SQL)

if __name__=='__main__': unittest.main()
