import json
import collections
from src.auto_label_gold_set import analyze_conversation

def inspect_data():
    print("Loading labeled gold set...")
    with open('data/gold_set/labeled_gold_set.json', 'r') as f:
        gold_cases = json.load(f)
        gold_ids = {c['root_tweet_id'] for c in gold_cases}

    print("Loading processed threads...")
    with open('data/processed/amazon_threads.json', 'r') as f:
        threads = json.load(f)

    english_non_gold = [t for t in threads if t.get('inbound_language') == 'en' and t['root_tweet_id'] not in gold_ids]
    
    print(f"Total usable English training examples (non-gold): {len(english_non_gold)}")
    
    intent_counts = collections.Counter()
    unknown_reasons = collections.Counter()
    
    print("Auto-labeling training examples using heuristics to inspect distribution...")
    for t in english_non_gold:
        label = analyze_conversation(t)['proposed_label']
        primary = label['primary_intent']
        intent_counts[primary] += 1
        
    print("\n--- Intent Distribution ---")
    for intent, count in intent_counts.most_common():
        print(f"{intent}: {count} ({count/len(english_non_gold)*100:.2f}%)")
        
    print(f"\n--- UNKNOWN Distribution ---")
    unknown_count = intent_counts.get("UNKNOWN", 0)
    print(f"Total UNKNOWN: {unknown_count} ({unknown_count/len(english_non_gold)*100:.2f}%)")
    
    min_count = min(intent_counts.values()) if intent_counts else 0
    max_count = max(intent_counts.values()) if intent_counts else 0
    print(f"\n--- Class Imbalance ---")
    print(f"Ratio of Most Common to Least Common Intent: {max_count / min_count if min_count > 0 else 'N/A':.2f}x")
    
    print("\n--- Sufficiency Check ---")
    for intent, count in intent_counts.items():
        if count < 100:
            print(f"WARNING: {intent} has only {count} examples (less than 100).")
        else:
            print(f"OK: {intent} has {count} examples.")

if __name__ == "__main__":
    inspect_data()
