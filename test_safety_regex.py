import json
from src.core.safety_detector import SafetyDetector

detector = SafetyDetector()

gold_set_path = "data/gold/gold_200.json"
with open(gold_set_path, 'r', encoding='utf-8') as f:
    gold_cases = json.load(f)
    
with open("data/processed/amazon_threads.json", 'r', encoding='utf-8') as f:
    threads_list = json.load(f)
    threads = {t['root_tweet_id']: t for t in threads_list}

safety_cases = [c for c in gold_cases if c.get('safety') == 'SAFETY_CONCERN']
for case in safety_cases:
    tid = case['root_tweet_id']
    thread = threads.get(tid)
    text = detector._extract_text(thread)
    res = detector.evaluate(thread)
    print(f"ID: {tid} | Pred: {res} | Text: {text}")
