import json
import time
import pandas as pd
import numpy as np
from src.ingestion.preprocess import process_pipeline
from collections import Counter

def run_real_ingestion(input_csv="data/raw/twcs.csv", output_json="data/processed/amazon_threads.json"):
    print(f"Loading raw data from {input_csv}...")
    start_time = time.time()
    df = pd.read_csv(input_csv, dtype={
        'tweet_id': str,
        'response_tweet_id': str,
        'in_response_to_tweet_id': str,
        'author_id': str
    })
    
    print("Running preprocessing pipeline (this may take a few minutes)...")
    conversations = process_pipeline(df, "AmazonHelp")
    
    print(f"Saving to {output_json}...")
    with open(output_json, 'w') as f:
        json.dump(conversations, f)
        
    print(f"Ingestion completed in {time.time() - start_time:.2f}s")
    
    unique_amazon_tweets = 0
    reconstructed_root_convos = len(conversations)
    branch_count = 0
    thread_lengths = []
    
    orphaned_threads = 0
    complete_threads = 0
    
    pii_replacements = 0
    
    inbound_lang_counts = Counter()
    outbound_lang_counts = Counter()
    
    total_branch_occurrences = 0
    
    for conv in conversations:
        if conv["is_orphaned_root"]:
            orphaned_threads += 1
        else:
            complete_threads += 1
            
        branches = conv["branches"]
        branch_count += len(branches)
        
        for branch in branches:
            thread_lengths.append(len(branch))
            total_branch_occurrences += len(branch)
            
        inbound_lang_counts[conv["inbound_language"]] += 1
        outbound_lang_counts[conv["outbound_language"]] += 1
        
        for tid, msg in conv["tweets"].items():
            if msg["author_id_hashed"] == "AmazonHelp":
                unique_amazon_tweets += 1
            
            # Count PII replacements
            import re
            pii_matches = len(re.findall(r'\[(?:PERSON|LOCATION|EMAIL_ADDRESS|PHONE_NUMBER|ORDER_ID|ACCOUNT_ID)_\d+\]', msg['text_clean']))
            pii_replacements += pii_matches

    avg_length = np.mean(thread_lengths) if thread_lengths else 0
    median_length = np.median(thread_lengths) if thread_lengths else 0
    max_length = np.max(thread_lengths) if thread_lengths else 0
    
    total_unique_tweets = sum(len(c["tweets"]) for c in conversations)
    
    report = {
        "Unique AmazonHelp tweets": unique_amazon_tweets,
        "Total unique physical tweets": total_unique_tweets,
        "Reconstructed root conversations": reconstructed_root_convos,
        "Branch count (total valid paths)": branch_count,
        "Complete vs Orphaned roots": f"{complete_threads} complete, {orphaned_threads} orphaned",
        "Average thread length": float(avg_length),
        "Median thread length": float(median_length),
        "Max thread length": int(max_length),
        "Unique vs repeated branch occurrences (tweets)": f"{total_unique_tweets} unique vs {total_branch_occurrences} total in branches",
        "PII replacements": pii_replacements,
        "Language Distribution (Inbound)": dict(inbound_lang_counts),
        "Language Distribution (Outbound)": dict(outbound_lang_counts)
    }
    
    print("\n=== INGESTION REPORT ===")
    print(json.dumps(report, indent=4))

if __name__ == "__main__":
    run_real_ingestion()
