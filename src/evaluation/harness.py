import json
import os
import datetime
from src.evaluation.metrics import (
    calculate_intent_metrics,
    calculate_trust_metrics,
    calculate_safety_metrics,
    calculate_resolution_metrics,
    calculate_capability_metrics
)

class Evaluator:
    def __init__(self, gold_set_path="data/gold/gold_200_labeled.json"):
        self.gold_set_path = gold_set_path
        with open(self.gold_set_path, 'r', encoding='utf-8') as f:
            self.gold_cases = json.load(f)
            
        # Map root_tweet_id to case for O(1) lookup
        self.gold_map = {case['root_tweet_id']: case for case in self.gold_cases}

    def evaluate(self, predictions, run_name="default_run"):
        """
        predictions: list of dicts. Must contain 'root_tweet_id' and predicted fields.
        """
        # Ensure we only evaluate against cases present in the gold set, in the same order
        ordered_gold = []
        ordered_preds = []
        
        pred_map = {p['root_tweet_id']: p for p in predictions}
        
        for g in self.gold_cases:
            if g['root_tweet_id'] in pred_map:
                ordered_gold.append(g)
                ordered_preds.append(pred_map[g['root_tweet_id']])
                
        if len(ordered_gold) != 200:
            print(f"Warning: Evaluating on {len(ordered_gold)} cases instead of 200.")
            
        results = {
            "metadata": {
                "run_name": run_name,
                "timestamp": datetime.datetime.now().isoformat(),
                "cases_evaluated": len(ordered_gold)
            },
            "intent": calculate_intent_metrics(ordered_gold, ordered_preds),
            "trust_gate": calculate_trust_metrics(ordered_gold, ordered_preds),
            "safety": calculate_safety_metrics(ordered_gold, ordered_preds),
            "resolution": calculate_resolution_metrics(ordered_gold, ordered_preds),
            "capability": calculate_capability_metrics(ordered_gold, ordered_preds)
        }
        
        per_case_results = self._generate_per_case_analysis(ordered_gold, ordered_preds)
        
        # Save output
        out_dir = f"data/evaluation_results/{run_name}"
        os.makedirs(out_dir, exist_ok=True)
        
        with open(os.path.join(out_dir, "aggregate_metrics.json"), 'w') as f:
            json.dump(results, f, indent=2)
            
        with open(os.path.join(out_dir, "per_case_analysis.json"), 'w') as f:
            json.dump(per_case_results, f, indent=2)
            
        return results, per_case_results

    def _generate_per_case_analysis(self, gold_cases, predictions):
        analysis = []
        for gold, pred in zip(gold_cases, predictions):
            
            # Simple mismatch flags
            intent_mismatch = gold.get('primary_intent') != pred.get('primary_intent')
            tier_mismatch = gold.get('trust_tier') != pred.get('trust_tier')
            safety_mismatch = gold.get('safety') != pred.get('safety')
            resolution_mismatch = gold.get('resolution') != pred.get('resolution')
            
            # Calculate a summary failure reason list
            failure_reasons = []
            if intent_mismatch:
                failure_reasons.append(f"Intent ({gold.get('primary_intent')} != {pred.get('primary_intent')})")
            if tier_mismatch:
                failure_reasons.append(f"Tier ({gold.get('trust_tier')} != {pred.get('trust_tier')})")
            if safety_mismatch:
                failure_reasons.append(f"Safety ({gold.get('safety')} != {pred.get('safety')})")
            if resolution_mismatch:
                failure_reasons.append(f"Resolution ({gold.get('resolution')} != {pred.get('resolution')})")
                
            record = {
                "root_tweet_id": gold['root_tweet_id'],
                "gold_intent": gold.get('primary_intent'),
                "predicted_intent": pred.get('primary_intent'),
                "gold_tier": gold.get('trust_tier'),
                "predicted_tier": pred.get('trust_tier'),
                "gold_safety": gold.get('safety'),
                "predicted_safety": pred.get('safety'),
                "gold_resolution": gold.get('resolution'),
                "predicted_resolution": pred.get('resolution'),
                "multi_intent_correct": gold.get('is_multi_intent') == pred.get('is_multi_intent'),
                "failure_reasons": failure_reasons,
                "cx_scores": pred.get('cx_scores', {}),
                "hallucination_check": pred.get('hallucination_check', {})
            }
            analysis.append(record)
            
        return analysis
