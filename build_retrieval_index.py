import json
from src.core.retrieval import RetrievalEngine
from src.auto_label_gold_set import analyze_conversation

def determine_outcome(thread):
    tweets = list(thread['tweets'].values())
    tweets.sort(key=lambda x: x['turn_index'])
    
    # Simple heuristic for outcome status
    if not tweets:
        return "UNKNOWN"
        
    final_tweet = tweets[-1]
    final_text = final_tweet['text_clean'].lower()
    
    if final_tweet['inbound']:
        # Customer spoke last
        resolved_kws = ["thanks", "thank you", "great", "awesome", "fixed", "worked", "appreciate"]
        unresolved_kws = ["useless", "still not", "terrible", "worst", "didn't help", "frustrating", "no help"]
        
        if any(kw in final_text for kw in resolved_kws):
            return "RESOLVED"
        if any(kw in final_text for kw in unresolved_kws):
            return "UNRESOLVED"
            
    else:
        # Agent spoke last
        unresolved_kws = ["dm us", "send us a dm", "call us", "contact our team", "escalate"]
        if any(kw in final_text for kw in unresolved_kws):
            return "UNRESOLVED"
            
    return "UNKNOWN"

def determine_lifecycle(thread, outcome):
    tweets = list(thread['tweets'].values())
    tweets.sort(key=lambda x: x['turn_index'])
    if not tweets:
        return "UNKNOWN"
        
    # CLOSED requires evidence of closure
    if outcome == "RESOLVED":
        return "CLOSED"
        
    final_tweet = tweets[-1]
    if final_tweet['inbound']:
        return "ACTIVE" # Awaiting system response
    else:
        return "WAITING" # Awaiting customer response

def determine_lifecycle(thread, outcome):
    tweets = list(thread['tweets'].values())
    tweets.sort(key=lambda x: x['turn_index'])
    if not tweets:
        return "UNKNOWN"
        
    # CLOSED requires evidence of closure
    if outcome == "RESOLVED":
        return "CLOSED"
        
    final_tweet = tweets[-1]
    if final_tweet['inbound']:
        return "ACTIVE" # Awaiting system response
    else:
        return "WAITING" # Awaiting customer response

def main():
    print("Loading Gold Set for leakage prevention...")
    with open('data/gold/gold_200.json', 'r') as f:
        gold_ids = {c['root_tweet_id'] for c in json.load(f)}
        
    print("Loading full amazon threads...")
    with open('data/processed/amazon_threads.json', 'r') as f:
        threads = json.load(f)
        
    # Strictly isolate Gold Set
    corpus = [t for t in threads if t.get('inbound_language') == 'en' and t['root_tweet_id'] not in gold_ids]
    
    # For CPU efficiency and track constraints, let's limit the index size to a robust representative sample
    # Using 10,000 precedents is plenty for a high-quality MVP index and keeps embedding fast on CPU.
    corpus = corpus[:10000]
    
    print(f"Building retrieval index for {len(corpus)} historical precedents...")
    
    precedents = []
    for t in corpus:
        # Auto-label intent
        intent = analyze_conversation(t)['proposed_label']['primary_intent']
        outcome = determine_outcome(t)
        lifecycle = determine_lifecycle(t, outcome)
        
        # Combine text for embedding
        text = " ".join([tweet['text_clean'] for tweet in t['tweets'].values()]).lower()
        
        precedents.append({
            "root_tweet_id": t['root_tweet_id'],
            "intent": intent,
            "outcome_status": outcome,
            "lifecycle_status": lifecycle,
            "text": text
        })
        
    engine = RetrievalEngine()
    engine.build_index(precedents)
    print("Done.")

if __name__ == "__main__":
    main()
