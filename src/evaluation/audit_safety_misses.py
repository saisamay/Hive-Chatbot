import json
import re
from src.core.safety_detector import SafetyDetector

class AuditDetector(SafetyDetector):
    def evaluate_verbose(self, conversation):
        text = self._extract_text(conversation)
        
        for pattern in self.serious_patterns:
            if re.search(pattern, text):
                return "SAFETY_CONCERN", f"serious pattern match: {pattern}"
                
        for pattern in self.ambiguous_patterns:
            if re.search(pattern, text):
                return "UNKNOWN", f"ambiguous pattern match: {pattern}"
                
        return "SAFE", "no safety/ambiguous patterns matched"

def run_safety_audit():
    gold_set_path = "data/gold/gold_200.json"
    with open(gold_set_path, 'r', encoding='utf-8') as f:
        gold_cases = json.load(f)
        
    with open("data/processed/amazon_threads.json", 'r', encoding='utf-8') as f:
        threads_list = json.load(f)
        threads = {t['root_tweet_id']: t for t in threads_list}

    detector = AuditDetector()
    
    missed_ids = [
      "2555145",
      "650126",
      "2558502",
      "2706722",
      "979606",
      "115903",
      "2663076",
      "462479",
      "1135907",
      "802363",
      "612716",
      "1159300"
    ]
    
    for tid in missed_ids:
        thread = threads.get(tid)
        text = detector._extract_text(thread)
        gold_safety = "SAFETY_CONCERN"
        pred, reason = detector.evaluate_verbose(thread)
        print("========================================")
        print(f"root_tweet_id: {tid}")
        print(f"Text: {text}")
        print(f"Gold: {gold_safety}")
        print(f"Pred: {pred}")
        print(f"Reason: {reason}")
        print("========================================\n")

if __name__ == "__main__":
    run_safety_audit()
