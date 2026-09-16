import json
import random

TAXONOMY_14 = [
    "Delivery_Delayed", "Package_Missing_Or_Stolen", "Order_Cancellation",
    "Refund_Or_Return_Status", "Billing_Or_Subscription", "Account_Or_Verification",
    "Account_Compromised", "Item_Damaged_Or_Defective", "Fraud_Or_Fake_Product",
    "Digital_Content_Or_Streaming", "Software_App_Or_Device_Technical_Issue",
    "Promotions_Cashback_Or_Offers", "Customer_Service_Or_Contact", "UNKNOWN"
]

kw_map = {
    "Delivery_Delayed": ["late", "delayed", "not arrived", "still waiting", "guaranteed delivery", "where is", "delivery"],
    "Package_Missing_Or_Stolen": ["stolen", "missing", "not in mailbox", "empty box", "says delivered"],
    "Order_Cancellation": ["cancel", "cancelled", "canceling"],
    "Refund_Or_Return_Status": ["refund", "return", "money back", "returned"],
    "Billing_Or_Subscription": ["charged", "billing", "renewed", "prime charge", "subscription", "membership"],
    "Account_Or_Verification": ["verify", "verification", "locked", "on hold", "access"],
    "Account_Compromised": ["hacked", "stolen account", "changed my email", "unauthorized"],
    "Item_Damaged_Or_Defective": ["damaged", "broken", "defective", "smashed", "scratched", "ruined"],
    "Fraud_Or_Fake_Product": ["fake", "fraud", "counterfeit", "scam"],
    "Digital_Content_Or_Streaming": ["prime video", "streaming", "movie", "season", "episode", "music"],
    "Software_App_Or_Device_Technical_Issue": ["echo", "alexa", "kindle", "fire tv", "app crash", "wont connect", "not working", "setup"],
    "Promotions_Cashback_Or_Offers": ["cashback", "offer", "discount", "winner", "reward", "promo"],
    "Customer_Service_Or_Contact": ["call me", "contact me", "no reply", "speak to a human", "call back"]
}

def analyze_sample():
    with open("data/processed/amazon_threads.json", "r") as f:
        threads = json.load(f)
        
    # Get 100 random English threads
    english_threads = [t for t in threads if t.get("is_english", True)]
    random.seed(123)
    sample = random.sample(english_threads, 100)
    
    distribution = {k: 0 for k in TAXONOMY_14}
    ambiguities = []
    
    for t in sample:
        inbound = [m for m in t["tweets"].values() if m["inbound"]]
        inbound.sort(key=lambda x: x["turn_index"])
        text = " ".join([m["text_clean"].lower() for m in inbound])
        
        scores = {k: 0 for k in TAXONOMY_14 if k != "UNKNOWN"}
        for intent, kws in kw_map.items():
            for kw in kws:
                if kw in text:
                    scores[intent] += 1
                    
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        if sorted_scores[0][1] == 0:
            primary = "UNKNOWN"
            distribution["UNKNOWN"] += 1
        else:
            primary = sorted_scores[0][0]
            distribution[primary] += 1
            
            # Detect ambiguity
            if sorted_scores[1][1] > 0 and (sorted_scores[0][1] - sorted_scores[1][1]) <= 1:
                ambiguities.append({
                    "id": t["root_tweet_id"],
                    "text": text[:150] + "...",
                    "intents": f"{sorted_scores[0][0]} vs {sorted_scores[1][0]}"
                })

    print("--- 100 CASE DISTRIBUTION ---")
    for k, v in distribution.items():
        if v > 0:
             print(f"{k}: {v}")
             
    print(f"\n--- AMBIGUITIES FOUND: {len(ambiguities)} ---")
    for a in ambiguities[:5]:
        print(f"ID: {a['id']}")
        print(f"Conflict: {a['intents']}")
        print(f"Text: {a['text']}\n")

if __name__ == "__main__":
    analyze_sample()
