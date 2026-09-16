import re
from src.label_gold_set_cli import TAXONOMY

class TrivialIntentBaseline:
    """
    A trivial intent baseline that relies purely on basic keyword hits.
    If no keywords match, it predicts the majority class (Delivery_Delayed).
    """
    def __init__(self):
        self.majority_class = "Delivery_Delayed"
        self.rules = {
            "where": "Delivery_Delayed",
            "late": "Delivery_Delayed",
            "cancel": "Order_Cancellation",
            "refund": "Refund_Or_Return_Status",
            "return": "Refund_Or_Return_Status",
            "charge": "Billing_Or_Prime_Charge",
            "prime": "Billing_Or_Prime_Charge",
            "broken": "Item_Damaged_Or_Defective",
            "fake": "Fraud_Or_Fake_Product",
            "account": "Account_Or_Verification",
            "locked": "Account_Or_Verification",
            "hacked": "Account_Compromised",
            "video": "Digital_Content_Or_Streaming",
            "app": "Device_Technical_Issue",
            "promo": "Promotions_Cashback_Or_Offers",
        }

    def predict(self, conversation):
        """
        conversation: dict containing the conversation structure.
        """
        # Simple text concatenation of customer messages
        tweets = list(conversation['tweets'].values())
        customer_text = " ".join([t['text_clean'] for t in tweets if t['inbound']]).lower()
        
        predicted_intent = self.majority_class
        for kw, intent in self.rules.items():
            if kw in customer_text:
                predicted_intent = intent
                break
                
        return {
            "root_tweet_id": conversation["root_tweet_id"],
            "primary_intent": predicted_intent,
            "secondary_intents": [],
            "is_multi_intent": False,
            "trust_tier": "HUMAN_ESCALATION", # Default conservative
            "frustration_trajectory": "UNKNOWN",
            "safety": "SAFE",
            "capability": "UNKNOWN",
            "resolution": "UNRESOLVED"
        }

class StaticPolicyBaseline:
    """
    Simulates a traditional static decision tree / scripted bot.
    - Always predicts UNRESOLVED unless it hits a simple FAQ keyword.
    - Predicts HUMAN_ESCALATION on anger keywords or fallback.
    - Universally predicts SAFE (static bots can't detect complex safety issues).
    """
    def __init__(self):
        self.intent_baseline = TrivialIntentBaseline()
        
    def predict(self, conversation):
        tweets = list(conversation['tweets'].values())
        customer_text = " ".join([t['text_clean'] for t in tweets if t['inbound']]).lower()
        
        # Base intent prediction
        base_pred = self.intent_baseline.predict(conversation)
        
        # Static logic for Trust Tier
        anger_keywords = ["angry", "mad", "furious", "unacceptable", "wtf", "worst"]
        escalate_keywords = ["manager", "supervisor", "human", "call"]
        faq_keywords = ["how to cancel", "where is", "policy"]
        
        trust_tier = "HUMAN_ESCALATION" # Default fallback
        if any(kw in customer_text for kw in anger_keywords + escalate_keywords):
            trust_tier = "HUMAN_ESCALATION"
        elif any(kw in customer_text for kw in faq_keywords):
            trust_tier = "AUTO_HANDLE"
            
        # Static logic for Resolution
        resolution = "UNRESOLVED"
        if trust_tier == "AUTO_HANDLE":
            resolution = "RESOLVED" # Assumes FAQ handles it
            
        base_pred["trust_tier"] = trust_tier
        base_pred["safety"] = "SAFE"
        base_pred["resolution"] = resolution
        
        return base_pred
