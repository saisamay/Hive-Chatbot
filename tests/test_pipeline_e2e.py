import json
import os
import unittest
from unittest.mock import patch, MagicMock

from src.core.intent_classifier import IntentClassifier
from src.core.retrieval import RetrievalEngine
from src.core.generation import Generator
from src.core.trust_gate import TrustGate

class TestPipelineE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We need the 200 gold cases
        gold_set_path = "data/gold/gold_200.json"
        cls.gold_cases = []
        with open(gold_set_path, 'r', encoding='utf-8') as f:
            cls.gold_cases = json.load(f)
            
        cls.threads = {}
        with open("data/processed/amazon_threads.json", 'r', encoding='utf-8') as f:
            threads_list = json.load(f)
            cls.threads = {t['root_tweet_id']: t for t in threads_list}
            
        cls.classifier = IntentClassifier()
        # Model is already trained and loaded from models/intent_classifier.joblib
        
        # Initialize RetrievalEngine
        cls.retriever = RetrievalEngine(index_path="models/retrieval/faiss.index")
        
        # Initialize TrustGate
        cls.trust_gate = TrustGate(confidence_threshold=0.6) # using 0.6 as a reasonable threshold for MVP

    def setUp(self):
        # Mock Generator LLM so it can run 200 cases in CI without hitting API rate limits or needing keys
        self.patcher = patch('src.core.generation.genai.Client')
        self.mock_client_class = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_client_class.return_value = self.mock_client
        self.generator = Generator(ai_disclosure_string="[AI Generated]")

    def tearDown(self):
        self.patcher.stop()

    def set_mock_llm_response(self, intent, capability_state):
        mock_response = MagicMock()
        # Create a safe, default response that matches intent and doesn't hallucinate
        # If capability is UNKNOWN, we don't claim execution.
        mock_response.text = json.dumps({
            "generated_response": "I can help you with that. Could you please provide more information? [AI Generated]",
            "claims_made": [],
            "actions_implied": [],
            "claimed_execution": False
        })
        self.mock_client.models.generate_content.return_value = mock_response

    def test_end_to_end_pipeline(self):
        print(f"\n--- Starting E2E Integration Test on {len(self.gold_cases)} Gold Cases ---")
        
        pass_count = {
            "intent_stage": 0,
            "retrieval_stage": 0,
            "generation_stage": 0,
            "trust_gate_stage": 0,
            "e2e_completed": 0
        }
        
        failures = []
        
        for case in self.gold_cases:
            try:
                # 1. Thread Context
                case_id = case.get("root_tweet_id")
                query_conversation = self.threads.get(case_id)
                if not query_conversation:
                    raise ValueError(f"Thread {case_id} not found in canonical threads.")
                
                # 2. Intent Classification
                intent_res = self.classifier.predict(query_conversation)
                intent_pred = intent_res["primary_intent"]
                confidence = intent_res["confidence"]
                pass_count["intent_stage"] += 1
                
                # 3. Retrieval
                retrieval_res = self.retriever.retrieve(query_conversation, intent_pred, top_k=3)
                pass_count["retrieval_stage"] += 1
                
                # 4. Grounded Generation
                capability_state = {"mock_action": "UNKNOWN"} # Default track A state
                
                self.set_mock_llm_response(intent_pred, capability_state)
                
                gen_context = {
                    "query_conversation": query_conversation,
                    "predicted_intent": intent_pred,
                    "intent_confidence": confidence,
                    "retrieved_precedents": retrieval_res.get("candidates", []),
                    "capability_state": capability_state
                }
                
                gen_result = self.generator.generate_response(gen_context)
                
                # Verify AI disclosure
                self.assertIn("[AI Generated]", gen_result["generated_response"])
                
                pass_count["generation_stage"] += 1
                
                # 5. Trust Gate
                # Extract safety/frustration from gold case just to simulate upstream signals
                safety_signal = case.get("safety") == "SAFETY_CONCERN"
                frustration = case.get("frustration_trajectory", "STABLE")
                explicit_human = "human" in case.get("must_cover_facts", "").lower()
                
                tg_context = {
                    "query_conversation": query_conversation,
                    "predicted_intent": intent_pred,
                    "intent_confidence": confidence,
                    "retrieved_precedents": retrieval_res.get("candidates", []),
                    "capability_state": capability_state,
                    "safety_legal_concern": safety_signal,
                    "explicit_human_request": explicit_human,
                    "frustration_trajectory": frustration
                }
                
                # For this baseline test, we simulate no previous deep analysis loop
                loop_state = {
                    "deep_analysis_attempts": 0,
                    "issue_persists": False,
                    "repeated_complaints": 0
                }
                
                tg_decision = self.trust_gate.evaluate(tg_context, loop_state, gen_result)
                
                # Because capability is UNKNOWN, and it's 0 attempts, we expect DEEP_ANALYSIS 
                # UNLESS there's a hard safety rule or human request which forces HUMAN_ESCALATION.
                # It should NEVER be AUTO_HANDLE with UNKNOWN capability.
                
                self.assertNotEqual(tg_decision["tier"], "AUTO_HANDLE")
                
                pass_count["trust_gate_stage"] += 1
                pass_count["e2e_completed"] += 1
                
            except Exception as e:
                failures.append({
                    "case_id": case.get("root_tweet_id"),
                    "error": str(e)
                })

        print("\n--- Pipeline E2E Results ---")
        print(f"Total Cases: {len(self.gold_cases)}")
        print(f"Intent Stage Pass: {pass_count['intent_stage']}")
        print(f"Retrieval Stage Pass: {pass_count['retrieval_stage']}")
        print(f"Generation Stage Pass: {pass_count['generation_stage']}")
        print(f"Trust Gate Stage Pass: {pass_count['trust_gate_stage']}")
        print(f"E2E Completed Successfully: {pass_count['e2e_completed']}")
        
        if failures:
            print(f"\nFailures ({len(failures)}):")
            for f in failures[:5]: # print top 5
                print(f"Case ID {f['case_id']}: {f['error']}")
                
        # Assert completely executed E2E
        self.assertEqual(pass_count["e2e_completed"], len(self.gold_cases))

if __name__ == '__main__':
    unittest.main()
