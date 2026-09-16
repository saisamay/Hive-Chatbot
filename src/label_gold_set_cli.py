import json
import os
import sys

TAXONOMY = {
    "1": "Delivery_Delayed",
    "2": "Package_Missing_Or_Stolen",
    "3": "Order_Cancellation",
    "4": "Refund_Or_Return_Status",
    "5": "Billing_Or_Prime_Charge",
    "6": "Account_Or_Verification",
    "7": "Account_Compromised",
    "8": "Item_Damaged_Or_Defective",
    "9": "Fraud_Or_Fake_Product",
    "10": "Digital_Content_Or_Streaming",
    "11": "Device_Technical_Issue",
    "12": "Promotions_Cashback_Or_Offers",
    "13": "Customer_Service_Or_Contact",
    "14": "UNKNOWN"
}

TRUST_TIERS = {"1": "AUTO_HANDLE", "2": "DEEP_ANALYSIS", "3": "HUMAN_ESCALATION"}
FRUSTRATION = {"1": "DECREASING", "2": "STABLE", "3": "INCREASING", "4": "UNKNOWN"}
SAFETY = {"1": "SAFE", "2": "SAFETY_CONCERN", "3": "UNKNOWN"}
CAPABILITY = {"1": "AVAILABLE", "2": "UNAVAILABLE", "3": "UNKNOWN"}
RESOLUTION = {"1": "RESOLVED", "2": "UNRESOLVED", "3": "UNKNOWN"}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_input(prompt, valid_choices=None, allow_empty=False):
    while True:
        val = input(prompt).strip()
        if not val and allow_empty:
            return val
        if valid_choices and val not in valid_choices:
            print(f"Invalid choice. Valid choices are: {', '.join(valid_choices)}")
            continue
        return val

def display_conversation(conv):
    print("="*80)
    print(f"Root Tweet ID: {conv['root_tweet_id']}")
    print("="*80)
    tweets = list(conv['tweets'].values())
    tweets.sort(key=lambda x: x['turn_index'])
    
    for t in tweets:
        sender = "CUSTOMER" if t['inbound'] else "AGENT"
        print(f"[{sender} - Turn {t['turn_index']}] {t['text_clean']}")
    print("="*80)

def main():
    unlabeled_path = "data/gold_set/unlabeled_sample.json"
    labeled_path = "data/gold_set/labeled_gold_set.json"
    
    if not os.path.exists(unlabeled_path):
        # Allow the script to function if there's no unlabeled data but labeled exists
        if os.path.exists(labeled_path):
            unlabeled = []
        else:
            print("Unlabeled sample not found. Run sample_gold_set.py first.")
            sys.exit(1)
    else:
        with open(unlabeled_path, 'r') as f:
            unlabeled = json.load(f)
        
    labeled_data = []
    labeled_ids = set()
    if os.path.exists(labeled_path):
        with open(labeled_path, 'r') as f:
            labeled_data = json.load(f)
            labeled_ids = {item["root_tweet_id"] for item in labeled_data}
            
    # Check if we have hit the target of 200 cases
    target = 200
    if len(labeled_data) >= target:
        print(f"{len(labeled_data)}/{target} completed \u2014 Golden Set complete.")
        return
            
    for i, conv in enumerate(unlabeled):
        root_id = conv["root_tweet_id"]
        if root_id in labeled_ids:
            continue
            
        clear_screen()
        print(f"Progress: {len(labeled_data)} / {target} completed.")
        display_conversation(conv)
        
        # A. Primary intent
        print("\nPrimary Intent Taxonomy:")
        for k, v in TAXONOMY.items():
            print(f"  {k}. {v}")
        p_intent_key = get_input("Select Primary Intent (1-11) or 'q' to quit: ", valid_choices=list(TAXONOMY.keys()) + ['q'])
        if p_intent_key == 'q':
            break
        p_intent = TAXONOMY[p_intent_key]
        
        # B. Multi-intent
        multi = get_input("Multi-intent? (y/n): ", valid_choices=['y', 'n'])
        add_intents = []
        if multi == 'y':
            while True:
                a_key = get_input("Add another intent (1-11) or empty to finish: ", valid_choices=list(TAXONOMY.keys()), allow_empty=True)
                if not a_key:
                    break
                add_intents.append(TAXONOMY[a_key])
                
        # C. Trust Tier
        print("\nTrust Tiers:")
        for k, v in TRUST_TIERS.items():
            print(f"  {k}. {v}")
        tt_key = get_input("Select Trust Tier (1-3): ", valid_choices=list(TRUST_TIERS.keys()))
        trust_tier = TRUST_TIERS[tt_key]
        
        # D. Frustration
        print("\nFrustration Trajectory:")
        for k, v in FRUSTRATION.items():
            print(f"  {k}. {v}")
        fr_key = get_input("Select Frustration (1-4): ", valid_choices=list(FRUSTRATION.keys()))
        frustration = FRUSTRATION[fr_key]
        
        # E. Safety
        print("\nSafety Ground Truth:")
        for k, v in SAFETY.items():
            print(f"  {k}. {v}")
        sf_key = get_input("Select Safety (1-3): ", valid_choices=list(SAFETY.keys()))
        safety = SAFETY[sf_key]
        
        # F. Capability
        print("\nCapability Availability:")
        for k, v in CAPABILITY.items():
            print(f"  {k}. {v}")
        cap_key = get_input("Select Capability (1-3): ", valid_choices=list(CAPABILITY.keys()))
        capability = CAPABILITY[cap_key]
        
        # G. Resolution
        print("\nResolution:")
        for k, v in RESOLUTION.items():
            print(f"  {k}. {v}")
        res_key = get_input("Select Resolution (1-3): ", valid_choices=list(RESOLUTION.keys()))
        resolution = RESOLUTION[res_key]
        
        # H. Facts
        facts = input("\nReference resolution / must-cover facts (1-2 sentences): ").strip()
        
        record = {
            "root_tweet_id": root_id,
            "primary_intent": p_intent,
            "secondary_intents": add_intents,
            "is_multi_intent": (multi == 'y'),
            "trust_tier": trust_tier,
            "frustration_trajectory": frustration,
            "safety": safety,
            "capability": capability,
            "resolution": resolution,
            "must_cover_facts": facts
        }
        
        labeled_data.append(record)
        labeled_ids.add(root_id)
        
        # Save progress
        with open(labeled_path, 'w') as f:
            json.dump(labeled_data, f, indent=2)
            
        if len(labeled_data) >= target:
            print(f"\n{len(labeled_data)}/{target} completed \u2014 Golden Set complete.")
            break
            
    if len(labeled_data) < target:
        print(f"\nLabeling session ended. {len(labeled_data)}/{target} completed.")

if __name__ == "__main__":
    main()
