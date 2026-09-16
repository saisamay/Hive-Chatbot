import json
import os
from src.evaluation.harness import Evaluator
from src.evaluation.baselines import TrivialIntentBaseline

def main():
    print("Running baseline against 200 Golden Set...")
    evaluator = Evaluator("data/gold_set/labeled_gold_set.json")
    
    print("Loading full amazon threads...")
    with open("data/processed/amazon_threads.json", "r") as f:
        amazon_threads = json.load(f)
        amazon_thread_map = {t['root_tweet_id']: t for t in amazon_threads}
    
    baseline = TrivialIntentBaseline()
    preds = []
    
    missing_threads = 0
    for case in evaluator.gold_cases:
        root_id = case['root_tweet_id']
        thread_data = amazon_thread_map.get(root_id)
        
        if thread_data is None:
            missing_threads += 1
            # Mock empty
            thread_data = {"root_tweet_id": root_id, "tweets": {}}
            
        preds.append(baseline.predict(thread_data))
        
    print(f"Missing threads in corpus: {missing_threads}")
    
    results, _ = evaluator.evaluate(preds, run_name="step2_baseline")
    
    print("\n--- Baseline Intent Metrics ---")
    print(f"Accuracy: {results['intent']['accuracy']:.4f}")
    print(f"Macro F1: {results['intent']['macro_f1']:.4f}")
    print(f"Multi-Intent Accuracy: {results['intent']['multi_intent_accuracy']:.4f}")

if __name__ == "__main__":
    main()
