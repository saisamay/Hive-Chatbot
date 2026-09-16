import json
import os

from src.core.intent_classifier import IntentClassifier
from src.core.retrieval import RetrievalEngine
from src.core.generation import Generator
from src.core.trust_gate import TrustGate
from src.evaluation.harness import Evaluator
from unittest.mock import patch, MagicMock

def run_audit():
    gold_set_path = "data/gold/gold_200.json"
    with open(gold_set_path, 'r', encoding='utf-8') as f:
        gold_cases = json.load(f)
        
    with open("data/processed/amazon_threads.json", 'r', encoding='utf-8') as f:
        threads_list = json.load(f)
        threads = {t['root_tweet_id']: t for t in threads_list}

    classifier = IntentClassifier()
    trust_gate = TrustGate(confidence_threshold=0.6)
    
    # We just want to audit Trust Gate on these specific sets
    # We will run the pipeline quickly without retrieval/generation 
    # to isolate Trust Gate routing
    
    human_to_deep = []
    auto_to_human = []
    
    for case in gold_cases:
        case_id = case.get("root_tweet_id")
        query_conversation = threads.get(case_id)
        if not query_conversation:
            continue
            
        intent_res = classifier.predict(query_conversation)
        intent_pred = intent_res["primary_intent"]
        confidence = intent_res["confidence"]
        
        capability_state = {"mock": "UNKNOWN"} 
        
        # Hard Human rules triggers
        safety_signal = case.get("safety") == "SAFETY_CONCERN"
        frustration = case.get("frustration_trajectory", "STABLE")
        explicit_human = "human" in case.get("must_cover_facts", "").lower()
        
        tg_context = {
            "query_conversation": query_conversation,
            "predicted_intent": intent_pred,
            "intent_confidence": confidence,
            "retrieved_precedents": [],
            "capability_state": capability_state,
            "safety_legal_concern": safety_signal,
            "explicit_human_request": explicit_human,
            "frustration_trajectory": frustration
        }
        
        loop_state = {
            "deep_analysis_attempts": 0,
            "issue_persists": False,
            "repeated_complaints": 0
        }
        
        tg_decision = trust_gate.evaluate(tg_context, loop_state, None)
        predicted_tier = tg_decision["tier"]
        gold_tier = case.get("trust_tier")
        
        if gold_tier == "HUMAN_ESCALATION" and predicted_tier == "DEEP_ANALYSIS":
            human_to_deep.append({
                "id": case_id,
                "safety_signal": safety_signal,
                "explicit_human": explicit_human,
                "frustration": frustration,
                "reasons": tg_decision["reasons"],
                "gold_must_cover": case.get("must_cover_facts")
            })
            
        if gold_tier == "AUTO_HANDLE" and predicted_tier == "HUMAN_ESCALATION":
            auto_to_human.append({
                "id": case_id,
                "safety_signal": safety_signal,
                "explicit_human": explicit_human,
                "frustration": frustration,
                "reasons": tg_decision["reasons"],
                "gold_must_cover": case.get("must_cover_facts")
            })

    print(f"--- 82 Gold HUMAN -> Pred DEEP_ANALYSIS ---")
    print(f"Total found in audit: {len(human_to_deep)}")
    
    # Group by why it was human originally
    frustration_human = [c for c in human_to_deep if c['frustration'] in ('INCREASING', 'HIGH')]
    safety_human = [c for c in human_to_deep if c['safety_signal']]
    
    print(f"Cases with HIGH/INCREASING frustration: {len(frustration_human)}")
    print(f"Cases with explicit safety signal: {len(safety_human)}")
    
    print("\n--- 1 Gold AUTO -> Pred HUMAN ---")
    for c in auto_to_human:
        print(f"Case ID: {c['id']}")
        print(f"Safety Signal: {c['safety_signal']}, Explicit Human: {c['explicit_human']}")
        print(f"Predicted reasons: {c['reasons']}")
        print(f"Gold Cover: {c['gold_must_cover']}")

if __name__ == "__main__":
    run_audit()
