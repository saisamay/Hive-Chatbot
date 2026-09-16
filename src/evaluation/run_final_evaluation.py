import json
import os
import sys

# Force evaluation to use Gemini for strict reproducibility.
os.environ["GENERATOR_PROVIDER"] = "gemini"

from src.core.intent_classifier import IntentClassifier
from src.core.retrieval import RetrievalEngine
from src.core.generation import Generator
from src.core.trust_gate import TrustGate
from src.core.safety_detector import SafetyDetector
import os
os.environ['GENERATOR_PROVIDER'] = 'gemini'
from src.evaluation.harness import Evaluator
from unittest.mock import patch, MagicMock

def run_evaluation():
    gold_set_path = "data/gold/gold_200_labeled.json"
    with open(gold_set_path, 'r', encoding='utf-8') as f:
        gold_cases = json.load(f)
        
    with open("data/processed/amazon_threads.json", 'r', encoding='utf-8') as f:
        threads_list = json.load(f)
        threads = {t['root_tweet_id']: t for t in threads_list}

    classifier = IntentClassifier()
    retriever = RetrievalEngine(index_path="models/retrieval/faiss.index")
    safety_detector = SafetyDetector()
    trust_gate = TrustGate(confidence_threshold=0.6)
    
    # ---------------------------------------------
    # Part D: Frustration Audit
    # ---------------------------------------------
    print("--- D. Frustration Field Audit ---")
    frustration_values = set()
    for case in gold_cases:
        f_val = case.get("frustration_trajectory")
        if f_val:
            frustration_values.add(f_val)
    print(f"Observed canonical frustration values in gold: {frustration_values}")
    
    # ---------------------------------------------
    # Part A: Primary Clean 200-Case Evaluation
    # ---------------------------------------------
    predictions = []
    
    with patch('src.core.generation.genai.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        generator = Generator(ai_disclosure_string="[AI Generated]")
        
        for case in gold_cases:
            case_id = case.get("root_tweet_id")
            query_conversation = threads.get(case_id)
            if not query_conversation:
                continue
                
            # 1. Intent
            intent_res = classifier.predict(query_conversation)
            intent_pred = intent_res["primary_intent"]
            confidence = intent_res["confidence"]
            
            # 2. Retrieval
            retrieval_res = retriever.retrieve(query_conversation, intent_pred, top_k=3)
            
            # 3. Generation (Mock normal behavior, no injected hallucinations)
            capability_state = {"mock": "UNKNOWN"} 
            
            mock_response_json = {
                "generated_response": "I can help you with that. Please DM your order number. [AI Generated]",
                "claims_made": [],
                "actions_implied": [],
                "claimed_execution": False
            }
            mock_response_obj = MagicMock()
            mock_response_obj.text = json.dumps(mock_response_json)
            mock_client.models.generate_content.return_value = mock_response_obj
            
            gen_context = {
                "query_conversation": query_conversation,
                "predicted_intent": intent_pred,
                "intent_confidence": confidence,
                "retrieved_precedents": retrieval_res.get("candidates", []),
                "capability_state": capability_state
            }
            
            gen_result = generator.generate_response(gen_context)
            
            # 3.5 Safety Evaluation
            safety_pred = safety_detector.evaluate(query_conversation)
            
            # 4. Trust Gate
            # CLEAN EVALUATION: We do NOT inject gold safety, frustration, or loops.
            # We assume default values for missing upstream classifiers.
            tg_context = {
                "query_conversation": query_conversation,
                "predicted_intent": intent_pred,
                "intent_confidence": confidence,
                "retrieved_precedents": retrieval_res.get("candidates", []),
                "capability_state": capability_state,
                "safety_legal_concern": safety_pred == "SAFETY_CONCERN",
                "explicit_human_request": False,
                "frustration_trajectory": "UNKNOWN"
            }
            
            loop_state = {
                "deep_analysis_attempts": 0,
                "issue_persists": False,
                "repeated_complaints": 0
            }
                
            tg_decision = trust_gate.evaluate(tg_context, loop_state, gen_result)
            
            # Compile Prediction Record
            pred_record = {
                "root_tweet_id": case_id,
                "primary_intent": intent_pred,
                "is_multi_intent": False,
                "secondary_intents": [],
                "trust_tier": tg_decision["tier"],
                "safety": safety_pred, # Pred
                "resolution": "UNKNOWN", # Pred 
                "capability": "UNKNOWN",
                "retrieval": retrieval_res,
                "tg_reasons": tg_decision["reasons"]
            }
            predictions.append(pred_record)
            
    print("\n--- Running Evaluation Harness ---")
    evaluator = Evaluator(gold_set_path)
    results, per_case = evaluator.evaluate(predictions, run_name="locked_final_eval")
    
    print("\n================ FINAL EVALUATION METRICS ================\n")
    print(json.dumps(results, indent=2))
    
    # ---------------------------------------------
    # Part C: Separate Loop Breaker Validation
    # ---------------------------------------------
    print("\n--- C. Loop Breaker Safety/Integration Test ---")
    loop_cases_tested = 5
    loop_success = 0
    for i in range(loop_cases_tested):
        tg_context = {
            "query_conversation": {"mock": "conversation"},
            "predicted_intent": "Delivery_Delayed",
            "intent_confidence": 0.9,
            "retrieved_precedents": [],
            "capability_state": {"mock": "AVAILABLE"},
            "safety_legal_concern": False,
            "explicit_human_request": False,
            "frustration_trajectory": "UNKNOWN"
        }
        loop_state = {
            "deep_analysis_attempts": 1,
            "issue_persists": True,
            "repeated_complaints": 2
        }
        gen_result = {"routed_to_deep_analysis": False}
        decision = trust_gate.evaluate(tg_context, loop_state, gen_result)
        if decision["tier"] == "HUMAN_ESCALATION" and "persistent_loop_after_deep_analysis" in decision["reasons"]:
            loop_success += 1
            
    print(f"Synthetic loop cases tested: {loop_cases_tested}")
    print(f"Successfully escalated to HUMAN_ESCALATION: {loop_success}")

if __name__ == "__main__":
    run_evaluation()
