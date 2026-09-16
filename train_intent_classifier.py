import json
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score
from src.auto_label_gold_set import analyze_conversation
from src.core.intent_classifier import IntentClassifier

def load_data():
    print("Loading gold set to exclude...")
    with open('data/gold_set/labeled_gold_set.json', 'r') as f:
        gold_ids = {c['root_tweet_id'] for c in json.load(f)}

    print("Loading amazon threads...")
    with open('data/processed/amazon_threads.json', 'r') as f:
        threads = json.load(f)

    # Filter strictly for English and non-gold to prevent leakage
    usable = [t for t in threads if t.get('inbound_language') == 'en' and t['root_tweet_id'] not in gold_ids]
    return usable

def generate_weak_labels(threads):
    print(f"Generating weak heuristic labels for {len(threads)} cases...")
    X, y = [], []
    for t in threads:
        # Extract text matching the classifier's feature extraction
        tweets = list(t['tweets'].values())
        text = " ".join([tweet['text_clean'] for tweet in tweets if tweet['inbound']]).lower()
        
        label = analyze_conversation(t)['proposed_label']['primary_intent']
        
        X.append(text)
        y.append(label)
    return X, y

def calibrate_threshold(pipeline, X_val, y_val):
    print("Calibrating UNKNOWN threshold on validation set...")
    probas = pipeline.predict_proba(X_val)
    classes = pipeline.classes_
    
    best_threshold = 0.0
    best_f1 = 0.0
    
    # Test thresholds from 0.1 to 0.9
    for threshold in np.arange(0.1, 0.9, 0.05):
        y_pred = []
        for p in probas:
            top_idx = np.argmax(p)
            if p[top_idx] < threshold:
                y_pred.append("UNKNOWN")
            else:
                y_pred.append(classes[top_idx])
                
        # Calculate macro F1
        f1 = f1_score(y_val, y_pred, average='macro', zero_division=0)
        
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
            
    print(f"Optimal threshold found: {best_threshold:.2f} (Macro F1: {best_f1:.4f})")
    return best_threshold, best_f1

def main():
    threads = load_data()
    X, y = generate_weak_labels(threads)
    
    # 80/20 Stratified Split
    print("Splitting data into 80/20 train/val...")
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print(f"Training on {len(X_train)} weakly-labeled examples...")
    pipeline = make_pipeline(
        TfidfVectorizer(max_features=10000, ngram_range=(1, 2)),
        LogisticRegression(max_iter=1000, class_weight='balanced')
    )
    
    pipeline.fit(X_train, y_train)
    
    threshold, val_f1 = calibrate_threshold(pipeline, X_val, y_val)
    
    print("Saving model...")
    classifier = IntentClassifier()
    classifier.save(pipeline, threshold)
    print("Model saved to models/intent_classifier.joblib")

if __name__ == "__main__":
    main()
