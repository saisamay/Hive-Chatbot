import os
import pandas as pd
import json
from src.ingestion.preprocess import process_pipeline

def generate_synthetic_data(output_path: str):
    """Generates a synthetic Kaggle-like dataset for testing purposes."""
    data = [
        # Thread 1: Simple linear
        {"tweet_id": "1001", "author_id": "Cust123", "inbound": True, "created_at": "2026-09-01T10:00:00Z", "text": "Where is my package? Order # 111-9876543-1234567 @AmazonHelp", "in_response_to_tweet_id": None},
        {"tweet_id": "1002", "author_id": "AmazonHelp", "inbound": False, "created_at": "2026-09-01T10:05:00Z", "text": "Hi Jane, sorry to hear that. Could you DM us your tracking ID? ^John", "in_response_to_tweet_id": "1001"},
        
        # Thread 2: Branching thread
        {"tweet_id": "2001", "author_id": "Cust456", "inbound": True, "created_at": "2026-09-02T11:00:00Z", "text": "I got the wrong item delivered to my address in Seattle. It was supposed to be a laptop.", "in_response_to_tweet_id": None},
        {"tweet_id": "2002", "author_id": "AmazonHelp", "inbound": False, "created_at": "2026-09-02T11:02:00Z", "text": "Oh no! Let us check that. Can you provide the order ID?", "in_response_to_tweet_id": "2001"},
        
        # Branch 2A
        {"tweet_id": "2003", "author_id": "Cust456", "inbound": True, "created_at": "2026-09-02T11:05:00Z", "text": "Order ID is 999-1234567-9876543.", "in_response_to_tweet_id": "2002"},
        {"tweet_id": "2004", "author_id": "AmazonHelp", "inbound": False, "created_at": "2026-09-02T11:10:00Z", "text": "Thanks! We will send a replacement right away.", "in_response_to_tweet_id": "2003"},
        
        # Branch 2B
        {"tweet_id": "2005", "author_id": "Cust456", "inbound": True, "created_at": "2026-09-02T11:06:00Z", "text": "Wait, nevermind, my roommate ordered it.", "in_response_to_tweet_id": "2002"},
        {"tweet_id": "2006", "author_id": "AmazonHelp", "inbound": False, "created_at": "2026-09-02T11:12:00Z", "text": "Glad you figured it out! Have a great day.", "in_response_to_tweet_id": "2005"},
    ]
    df = pd.DataFrame(data)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Generated synthetic data at {output_path}")

def run_ingestion(input_csv: str, output_json: str):
    print(f"Loading raw data from {input_csv}...")
    df = pd.read_csv(input_csv, dtype={
        'tweet_id': str,
        'response_tweet_id': str,
        'in_response_to_tweet_id': str,
        'author_id': str
    })
    
    print("Running preprocessing pipeline...")
    processed_threads = process_pipeline(df)
    
    print(f"Saving processed threads to {output_json}...")
    with open(output_json, 'w') as f:
        json.dump(processed_threads, f, indent=2)
    print(f"Successfully processed {len(processed_threads)} threads.")

if __name__ == "__main__":
    RAW_DATA_PATH = "data/raw/synthetic_tweets.csv"
    PROCESSED_DATA_PATH = "data/processed/canonical_threads.json"
    
    if not os.path.exists(RAW_DATA_PATH):
        generate_synthetic_data(RAW_DATA_PATH)
        
    run_ingestion(RAW_DATA_PATH, PROCESSED_DATA_PATH)
