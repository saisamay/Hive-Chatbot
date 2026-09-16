import json

def run_audit():
    with open('data/processed/amazon_threads.json', 'r') as f:
        threads = json.load(f)
        
    all_tweet_ids = []
    unique_tweet_ids = set()
    
    example_thread = None
    
    for t in threads:
        for msg in t:
            tid = msg['tweet_id']
            all_tweet_ids.append(tid)
            unique_tweet_ids.add(tid)
            
        # Find a good example thread (length >= 3, contains inbound and outbound)
        if example_thread is None and len(t) >= 3:
            has_inbound = any(m['inbound'] for m in t)
            has_outbound = any(not m['inbound'] for m in t)
            if has_inbound and has_outbound:
                example_thread = t
                
    total_msgs = len(all_tweet_ids)
    unique_msgs = len(unique_tweet_ids)
    duplicates = total_msgs - unique_msgs
    
    print(f"Total message occurrences across all branches: {total_msgs}")
    print(f"Unique physical tweets: {unique_msgs}")
    print(f"Duplicate tweet occurrences (due to branching): {duplicates}")
    print("\n--- Canonical JSON Schema Example ---")
    print(json.dumps(example_thread, indent=2))

if __name__ == '__main__':
    run_audit()
