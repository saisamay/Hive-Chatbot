import json
import os
import collections
from src.evaluation.harness import Evaluator
from src.core.intent_classifier import IntentClassifier

def main():
    print("Loading Golden Set and threads...")
    evaluator = Evaluator("data/gold_set/labeled_gold_set.json")
    
    with open("data/processed/amazon_threads.json", "r") as f:
        threads = json.load(f)
    thread_map = {t['root_tweet_id']: t for t in threads}
    
    print("Loading trained classifier...")
    classifier = IntentClassifier()
    
    print("Running evaluation on 200 human-validated Golden Set...")
    preds = []
    missing = 0
    for case in evaluator.gold_cases:
        root_id = case['root_tweet_id']
        thread_data = thread_map.get(root_id)
        if not thread_data:
            missing += 1
            thread_data = {"root_tweet_id": root_id, "tweets": {}}
        preds.append(classifier.predict(thread_data))
        
    print(f"Missing threads in corpus: {missing}")
    results, per_case = evaluator.evaluate(preds, run_name="intent_classifier")
    
    print("\n" + "="*50)
    print("FINAL EVALUATION ON HUMAN-VALIDATED GOLDEN SET (N=200)")
    print("="*50)
    print(f"Accuracy: {results['intent']['accuracy']:.4f}")
    print(f"Macro F1: {results['intent']['macro_f1']:.4f}")
    print(f"Multi-Intent Accuracy: {results['intent']['multi_intent_accuracy']:.4f}")
    
    # Analyze UNKNOWN performance
    unknown_metrics = results['intent']['per_intent'].get("UNKNOWN", {"precision": 0, "recall": 0, "f1": 0})
    print(f"\nUNKNOWN Performance: P={unknown_metrics['precision']:.4f}, R={unknown_metrics['recall']:.4f}, F1={unknown_metrics['f1']:.4f}")
    
    print("\n--- Top Failure Modes (Confusions) ---")
    confusions = collections.Counter()
    for pc in per_case:
        gold = pc['gold_intent']
        pred = pc['predicted_intent']
        if gold != pred:
            confusions[(gold, pred)] += 1
            
    for (g, p), count in confusions.most_common(10):
        print(f"Gold: {g}  -->  Pred: {p} ({count} cases)")

if __name__ == "__main__":
    main()
