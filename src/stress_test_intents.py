import json
import random

def run_stress_test():
    print("Loading data...")
    with open('data/processed/amazon_threads.json', 'r') as f:
        conversations = json.load(f)
        
    inbound_texts = []
    for conv in conversations:
        if conv.get("inbound_language") != "en":
            continue
        tweets = conv["tweets"]
        inbound_msgs = [m for m in tweets.values() if m["inbound"]]
        if not inbound_msgs:
            continue
        inbound_msgs.sort(key=lambda x: x["turn_index"])
        text = inbound_msgs[0]["text_clean"]
        if len(text.split()) > 3:
            inbound_texts.append(text.lower())
            
    print(f"Loaded {len(inbound_texts)} English inbound messages.")
    
    def search(keywords, anti_keywords=[], num_samples=5):
        matches = []
        for t in inbound_texts:
            if all(k in t for k in keywords) and not any(ak in t for ak in anti_keywords):
                matches.append(t)
        
        sample = random.sample(matches, min(num_samples, len(matches)))
        print(f"\n--- Search: {' AND '.join(keywords)} (Total matches: {len(matches)}) ---")
        for m in sample:
            print(f"- {m}")
            
    # Test Cancellation vs Refund
    search(["cancel", "refund"])
    search(["cancel"], anti_keywords=["refund"])
    search(["refund"], anti_keywords=["cancel"])
    
    # Test Account compromise vs Billing
    search(["hacked"])
    search(["charged", "prime"])
    search(["unauthorized", "charge"])
    
    # Test Damaged vs Missing/Empty package vs Fraud
    search(["damaged"])
    search(["empty", "box"])
    search(["stolen"])
    search(["fake"])
    
    # Test Digital service vs Device/App
    search(["prime video"])
    search(["app", "crash"])
    search(["echo", "connect"])
    
if __name__ == "__main__":
    run_stress_test()
