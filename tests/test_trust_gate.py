import unittest
from src.core.trust_gate import TrustGate

class TestTrustGate(unittest.TestCase):
    def setUp(self):
        self.trust_gate = TrustGate(confidence_threshold=0.8)
        self.default_context = {
            "predicted_intent": "Refund_Or_Return_Status",
            "intent_confidence": 0.9,
            "capability_state": {"action_refund": {"status": "AVAILABLE"}},
            "query_conversation": {"1": {"text": "I need help"}},
            "frustration_trajectory": "STABLE"
        }
        self.default_loop_state = {
            "deep_analysis_attempts": 0,
            "issue_persists": False,
            "repeated_complaints": 0
        }

    def test_auto_handle_perfect_conditions(self):
        result = self.trust_gate.evaluate(self.default_context, self.default_loop_state)
        self.assertEqual(result["tier"], "AUTO_HANDLE")
        self.assertIn("high_confidence_safe_complete", result["reasons"])

    def test_human_request_override(self):
        ctx = self.default_context.copy()
        ctx["explicit_human_request"] = True
        result = self.trust_gate.evaluate(ctx, self.default_loop_state)
        self.assertEqual(result["tier"], "HUMAN_ESCALATION")
        self.assertIn("explicit_human_request", result["reasons"])
        self.assertIn("handoff_payload", result)

    def test_safety_legal_concern(self):
        ctx = self.default_context.copy()
        ctx["safety_legal_concern"] = True
        result = self.trust_gate.evaluate(ctx, self.default_loop_state)
        self.assertEqual(result["tier"], "HUMAN_ESCALATION")
        self.assertIn("safety_legal_concern", result["reasons"])

    def test_frustration_alone_is_not_safety(self):
        # Frustrated but no actual safety flag
        ctx = self.default_context.copy()
        ctx["frustration_trajectory"] = "INCREASING" # purely tracking frustration
        result = self.trust_gate.evaluate(ctx, self.default_loop_state)
        # Should remain Auto because high confidence and available capability, no safety flag
        self.assertEqual(result["tier"], "AUTO_HANDLE")

    def test_loop_breaker_triggers_human_after_deep_analysis(self):
        loop_state = {
            "deep_analysis_attempts": 1,
            "issue_persists": True,
            "repeated_complaints": 2
        }
        result = self.trust_gate.evaluate(self.default_context, loop_state)
        self.assertEqual(result["tier"], "HUMAN_ESCALATION")
        self.assertIn("persistent_loop_after_deep_analysis", result["reasons"])

    def test_unknown_intent_forces_deep_analysis(self):
        ctx = self.default_context.copy()
        ctx["predicted_intent"] = "UNKNOWN"
        result = self.trust_gate.evaluate(ctx, self.default_loop_state)
        self.assertEqual(result["tier"], "DEEP_ANALYSIS")
        self.assertIn("ambiguous_intent", result["reasons"])

    def test_low_confidence_forces_deep_analysis(self):
        ctx = self.default_context.copy()
        ctx["intent_confidence"] = 0.5
        result = self.trust_gate.evaluate(ctx, self.default_loop_state)
        self.assertEqual(result["tier"], "DEEP_ANALYSIS")
        self.assertIn("low_intent_confidence", result["reasons"])

    def test_unknown_capability_forces_deep_analysis(self):
        ctx = self.default_context.copy()
        ctx["capability_state"] = {"action_refund": "UNKNOWN"}
        result = self.trust_gate.evaluate(ctx, self.default_loop_state)
        self.assertEqual(result["tier"], "DEEP_ANALYSIS")
        self.assertIn("unknown_capability_action_refund", result["reasons"])

    def test_repeated_complaint_forces_deep_analysis_if_no_da_attempted(self):
        loop_state = {
            "deep_analysis_attempts": 0,
            "issue_persists": False,
            "repeated_complaints": 4
        }
        result = self.trust_gate.evaluate(self.default_context, loop_state)
        # Deep analysis has not been attempted, so it should try Deep Analysis first.
        self.assertEqual(result["tier"], "DEEP_ANALYSIS")
        self.assertIn("repeated_complaint_count_4", result["reasons"])

    def test_generation_hallucination_forces_deep_analysis(self):
        gen_result = {"routed_to_deep_analysis": True}
        result = self.trust_gate.evaluate(self.default_context, self.default_loop_state, gen_result)
        self.assertEqual(result["tier"], "DEEP_ANALYSIS")
        self.assertIn("unsupported_generation_claim", result["reasons"])

if __name__ == '__main__':
    unittest.main()
