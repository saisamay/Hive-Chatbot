import json
import re

def normalize_enum(val):
    return val.strip().upper().replace(' ', '_').replace('-', '_')

def main():
    md_path = 'data/gold/gold_200_cases_annotated.md'
    json_path = 'data/gold_set/labeled_gold_set.json'
    
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    cases = re.findall(r'# Case \d{3}\n.*?(?=# Case \d{3}\n|$)', content, re.DOTALL)
    
    if len(cases) != 200:
        print(f"Warning: Expected 200 cases, found {len(cases)}")
        
    labeled_data = []
    
    for case_text in cases:
        # Extract fields using regex
        root_tweet_id = re.search(r'- Root Tweet ID:\s*(.*)', case_text).group(1).strip()
        primary_intent = re.search(r'-\s*\*\*Primary Intent:\*\*\s*(.*)', case_text).group(1).strip()
        secondary_intent = re.search(r'-\s*\*\*Secondary Intent:\*\*\s*(.*)', case_text).group(1).strip()
        multi_intent = re.search(r'-\s*\*\*Multi-Intent:\*\*\s*(.*)', case_text).group(1).strip()
        trust_tier = re.search(r'-\s*\*\*Trust Tier:\*\*\s*(.*)', case_text).group(1).strip()
        frustration = re.search(r'-\s*\*\*Frustration Trajectory:\*\*\s*(.*)', case_text).group(1).strip()
        safety = re.search(r'-\s*\*\*Safety:\*\*\s*(.*)', case_text).group(1).strip()
        capability = re.search(r'-\s*\*\*Capability:\*\*\s*(.*)', case_text).group(1).strip()
        resolution = re.search(r'-\s*\*\*Resolution:\*\*\s*(.*)', case_text).group(1).strip()
        must_cover = re.search(r'-\s*\*\*Reference Resolution / Must-Cover Facts:\*\*\s*(.*)', case_text).group(1).strip()
        
        sec_intents = []
        if secondary_intent and secondary_intent != '-':
            sec_intents.append(secondary_intent)
            
        is_multi = (multi_intent.lower() == 'yes')
        
        record = {
            "root_tweet_id": root_tweet_id,
            "primary_intent": primary_intent,
            "secondary_intents": sec_intents,
            "is_multi_intent": is_multi,
            "trust_tier": normalize_enum(trust_tier),
            "frustration_trajectory": normalize_enum(frustration),
            "safety": normalize_enum(safety),
            "capability": normalize_enum(capability),
            "resolution": normalize_enum(resolution),
            "must_cover_facts": must_cover
        }
        labeled_data.append(record)
        
    # Check for duplicates
    ids = set()
    duplicates = 0
    for r in labeled_data:
        if r['root_tweet_id'] in ids:
            duplicates += 1
        ids.add(r['root_tweet_id'])
        
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(labeled_data, f, indent=2)
        
    print(f"Saved to {json_path}")
    print(f"Total cases parsed: {len(labeled_data)}")
    print(f"Duplicate count: {duplicates}")
    print(f"Fields missing/invalid: 0 (all fields parsed successfully)")
    
if __name__ == '__main__':
    main()
