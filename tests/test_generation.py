import unittest
from unittest.mock import patch, MagicMock
from src.core.generation import Generator

class TestGeneration(unittest.TestCase):
    def setUp(self):
        # We patch the GenAI client to avoid needing a real API key in CI
        self.patcher = patch('src.core.generation.genai.Client')
        self.mock_client_class = self.patcher.start()
        
        self.mock_client = MagicMock()
        self.mock_client_class.return_value = self.mock_client
        
        self.generator = Generator(ai_disclosure_string="[AI TEST]")
        
    def tearDown(self):
        self.patcher.stop()
        
    def set_mock_llm_response(self, response_text):
        mock_response = MagicMock()
        mock_response.text = response_text
        self.mock_client.models.generate_content.return_value = mock_response

    def test_capability_available_but_not_executed(self):
        # Action is AVAILABLE, but not COMPLETED
        context = {
            "query_conversation": {"1": {"text_clean": "I want a refund", "inbound": True}},
            "predicted_intent": "Refund_Or_Return_Status",
            "capability_state": {
                "action_refund": {"status": "AVAILABLE", "execution_status": "NONE"}
            }
        }
        
        # Mock LLM obeying the prompt: discusses the refund, implies the action is possible, but does NOT claim execution
        self.set_mock_llm_response('{"generated_response": "I can issue a refund for you.", "claims_made": [], "actions_implied": ["action_refund"], "claimed_execution": false}')
        
        result = self.generator.generate_response(context)
        self.assertFalse(result["unsupported_claims_removed"])
        self.assertFalse(result.get("claimed_execution", False))
        self.assertIn("[AI TEST]", result["generated_response"])
        
    def test_capability_unavailable(self):
        # Action is UNAVAILABLE
        context = {
            "query_conversation": {"1": {"text_clean": "cancel my order", "inbound": True}},
            "predicted_intent": "Order_Cancellation",
            "capability_state": {
                "action_cancel_order": {"status": "UNAVAILABLE", "execution_status": "NONE"}
            }
        }
        
        # Mock LLM hallucinating that it can cancel the order
        self.set_mock_llm_response('{"generated_response": "I will cancel your order right away.", "claims_made": [], "actions_implied": ["action_cancel_order"], "claimed_execution": false}')
        
        result = self.generator.generate_response(context)
        
        # The deterministic validator must catch the unsupported claim and drop the response
        self.assertTrue(result["unsupported_claims_removed"])
        self.assertTrue(result["routed_to_deep_analysis"])

    def test_hallucination_prevention_on_unknown(self):
        # Action is UNKNOWN, but historical precedent says "refund issued"
        context = {
            "query_conversation": {"1": {"text_clean": "where is my refund?", "inbound": True}},
            "predicted_intent": "Refund_Or_Return_Status",
            "capability_state": {
                "action_refund": "UNKNOWN" 
            },
            "retrieved_precedents": [
                {
                    "precedent_intent": "Refund_Or_Return_Status",
                    "outcome_status": "RESOLVED",
                    "relevant_text": "I have issued your refund of $50. It will arrive in 3 days."
                }
            ]
        }
        
        # Mock LLM getting confused by the precedent and hallucinating a completed refund
        self.set_mock_llm_response('{"generated_response": "I have issued your refund of $50. It will arrive in 3 days.", "claims_made": ["Refund issued"], "actions_implied": ["action_refund"], "claimed_execution": true}')
        
        result = self.generator.generate_response(context)
        
        # The deterministic validator must flag this and block the response
        self.assertTrue(result["unsupported_claims_removed"])
        self.assertTrue(result["routed_to_deep_analysis"])
        self.assertIn("[AI TEST]", result["generated_response"])
        self.assertNotEqual(result["generated_response"].strip(), "I have issued your refund of $50. It will arrive in 3 days. [AI TEST]")

if __name__ == '__main__':
    unittest.main()
