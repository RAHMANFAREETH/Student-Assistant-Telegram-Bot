"""Regression checks for Llama Guard's user/assistant alternation requirement.

Run: python -m unittest TEST_V5_5_AI.py TEST_V5_5_DIAGNOSTICS.py TEST_V5_5_HTTP400.py TEST_V5_5_LLAMAGUARD_FIX.py -v
"""
import unittest
from unittest.mock import patch
from TEST_V5_5_AI import ai, FakeBot, FakeMsg


class LlamaGuardInputOutputTests(unittest.TestCase):
    def setUp(self):
        ai._sessions.clear()
        ai._active_user_ids.clear()

    def test_student_question_has_user_role_only(self):
        with patch.object(ai, "_provider_call", return_value="safe") as call:
            self.assertTrue(ai._check_safety("What is biology?"))
        self.assertEqual(call.call_args.args[0], ai.GUARD_MODEL)
        self.assertEqual(call.call_args.args[1], [{"role": "user", "content": "What is biology?"}])

    def test_answer_check_alternates_user_then_assistant(self):
        with patch.object(ai, "_provider_call", return_value="safe") as call:
            self.assertTrue(ai._check_safety("Biology studies life.", response=True,
                                             original_question="What is biology?"))
        self.assertEqual(call.call_args.args[1], [
            {"role": "user", "content": "What is biology?"},
            {"role": "assistant", "content": "Biology studies life."},
        ])

    def test_empty_question_fails_closed(self):
        with patch.object(ai, "_provider_call") as call:
            with self.assertRaises(ai.AIUnavailable) as ctx:
                ai._check_safety("Hello", response=True)
        self.assertEqual(ctx.exception.code, "safety_context_missing")
        call.assert_not_called()

    def test_unsafe_generated_reply_still_blocked(self):
        with patch.object(ai, "_provider_call", return_value="unsafe\nS2") as call:
            self.assertFalse(ai._check_safety("Risky answer", response=True,
                                              original_question="A question"))
        self.assertEqual([m["role"] for m in call.call_args.args[1]], ["user", "assistant"])

    def test_unexpected_guard_result_fails_closed(self):
        with patch.object(ai, "_provider_call", return_value="uncertain"):
            with self.assertRaises(ai.AIUnavailable) as ctx:
                ai._check_safety("An answer", response=True, original_question="Question")
        self.assertEqual(ctx.exception.code, "safety_unknown")

    def test_process_question_sends_answer_after_both_safe_checks(self):
        # Runs full worker handler synchronously with mock Cloudflare + Supabase.
        bot = FakeBot()
        ai.register_ai_study_assistant_handlers(bot, lambda *args: None)
        ai._set_mode(111, "ask")
        session = ai._get_session(111)
        calls = []
        def provider(model, messages, max_tokens):
            calls.append((model, messages))
            return "safe" if model == ai.GUARD_MODEL else "Photosynthesis uses sunlight."
        with patch.object(ai, "claim_quota", return_value=1), patch.object(ai, "_provider_call", side_effect=provider):
            # _process_question is nested; run through registered handler with inline executor.
            with patch.object(ai._ai_executor, "submit", side_effect=lambda fn,*args: fn(*args)), \
                 patch.object(ai, "is_authorized", return_value=True):
                bot.call("ai_chat_message", FakeMsg("Explain photosynthesis"))
        self.assertEqual([m for m,_ in calls], [ai.GUARD_MODEL, ai.CF_MODEL, ai.GUARD_MODEL])
        self.assertEqual([t["role"] for t in calls[2][1]], ["user", "assistant"])
        self.assertEqual(calls[2][1][0]["content"], "Explain photosynthesis")
        self.assertEqual(calls[2][1][1]["content"], "Photosynthesis uses sunlight.")
        self.assertIn("Photosynthesis uses sunlight.", [m[1] for m in bot.messages])

if __name__ == "__main__": unittest.main()
