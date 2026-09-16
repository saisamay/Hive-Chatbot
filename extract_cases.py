import csv
import json
import re
import os
import random
from collections import defaultdict
from typing import List, Dict, Any

# Ensure output directory exists
os.makedirs('data/gold', exist_ok=True)

print("Loading CSV...")
df = []
tweet_dict = {}

amazon_help_tweet_ids = set()
amazon_help_tweets_count = 0

with open('data/raw/twcs.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # tweet_id,author_id,inbound,created_at,text,response_tweet_id,in_response_to_tweet_id
        tid = row['tweet_id']
        tweet_dict[tid] = row
        df.append(row)
        if row['author_id'] == 'AmazonHelp':
            amazon_help_tweets_count += 1
            amazon_help_tweet_ids.add(tid)

print(f"Total rows in twcs.csv: {len(df)}")
print(f"Total AmazonHelp-related rows: {amazon_help_tweets_count}")
print(f"Total unique AmazonHelp tweets: {len(amazon_help_tweet_ids)}")

print("Identifying conversations...")
def get_root(tweet_id):
    curr = tweet_id
    visited = set()
    while curr and curr in tweet_dict:
        if curr in visited:
            break
        visited.add(curr)
        parent = tweet_dict[curr]['in_response_to_tweet_id']
        if parent:
            curr = parent
        else:
            break
    return curr

# Find roots for all AmazonHelp tweets
amazon_roots = set()
for tid in amazon_help_tweet_ids:
    amazon_roots.add(get_root(tid))

print(f"Total candidate AmazonHelp root conversations: {len(amazon_roots)}")

print("Building child map...")
child_map = defaultdict(list)
for tid, t in tweet_dict.items():
    if t['in_response_to_tweet_id']:
        child_map[t['in_response_to_tweet_id']].append(tid)

print("Extracting conversations...")
def get_conversation_tree(root_id):
    tree = []
    queue = [root_id]
    visited = set()
    while queue:
        curr = queue.pop(0)
        if curr in visited:
            continue
        visited.add(curr)
        if curr in tweet_dict:
            tree.append(tweet_dict[curr])
            queue.extend(child_map.get(curr, []))
    return tree

# Extract all AmazonHelp conversations
conversations = {}
for root in amazon_roots:
    conv = get_conversation_tree(root)
    if len(conv) > 1:
        conv.sort(key=lambda x: int(x['tweet_id']))
        conversations[root] = conv

print(f"Total multi-tweet AmazonHelp conversations: {len(conversations)}")

cases = []
for root, conv in conversations.items():
    length = len(conv)
    has_branching = any(len(child_map.get(t['tweet_id'], [])) > 1 for t in conv)
    
    text_concat = " ".join([t['text'] for t in conv if t['author_id'] != 'AmazonHelp']).lower()
    frustration = bool(re.search(r'(wtf|fucking|shit|crap|hell|useless|terrible|worst|horrible|angry|cancel)', text_concat))
    repetition = len(conv) > 6
    
    if 'delivery' in text_concat or 'arrive' in text_concat or 'late' in text_concat or 'where is' in text_concat:
        topic = 'delivery'
    elif 'refund' in text_concat or 'charge' in text_concat or 'money' in text_concat:
        topic = 'billing/refund'
    elif 'account' in text_concat or 'login' in text_concat or 'password' in text_concat:
        topic = 'account'
    elif 'prime' in text_concat or 'video' in text_concat or 'music' in text_concat:
        topic = 'digital_services'
    else:
        topic = 'general'
        
    human_escalation = bool(re.search(r'(call me|supervisor|manager|human|real person|phone number)', text_concat))
    
    cases.append({
        'root_tweet_id': root,
        'length': length,
        'has_branching': has_branching,
        'topic': topic,
        'frustration': frustration,
        'human_escalation': human_escalation,
        'messages': conv
    })

buckets = defaultdict(list)
for c in cases:
    bucket_key = (c['topic'], 'long' if c['length'] > 4 else 'short', c['has_branching'], c['frustration'], c['human_escalation'])
    buckets[bucket_key].append(c)

print(f"Created {len(buckets)} diverse buckets.")

random.seed(42)
selected_cases = []
while len(selected_cases) < 200 and buckets:
    for key in list(buckets.keys()):
        if buckets[key]:
            selected_cases.append(buckets[key].pop(random.randint(0, len(buckets[key]) - 1)))
            if len(selected_cases) == 200:
                break
        else:
            del buckets[key]

if len(selected_cases) < 200:
    remaining = 200 - len(selected_cases)
    selected_roots = {c['root_tweet_id'] for c in selected_cases}
    unselected = [c for c in cases if c['root_tweet_id'] not in selected_roots]
    selected_cases.extend(random.sample(unselected, remaining))

print(f"Selected {len(selected_cases)} cases.")

def scrub_pii(text):
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '<EMAIL_1>', text)
    text = re.sub(r'\b(?:\+?1[-.●]?)?\(?([0-9]{3})\)?[-.●]?([0-9]{3})[-.●]?([0-9]{4})\b', '<PHONE_1>', text)
    text = re.sub(r'\b\d{3}-\d{7}-\d{7}\b', '<ORDER_ID_1>', text)
    text = re.sub(r'\b\d{16,17}\b', '<ORDER_ID_1>', text)
    text = re.sub(r'\b(TBA\d{12,15})\b', '<TRACKING_1>', text)
    text = re.sub(r'\b(1Z[A-Z0-9]{16})\b', '<TRACKING_1>', text)
    return text

gold_200 = []
for i, c in enumerate(selected_cases):
    case_id = f"AMZ_{i+1:04d}"
    
    messages = []
    for m in c['messages']:
        scrubbed_text = scrub_pii(m['text'])
        scrubbed_text = re.sub(r'@(?!(?:AmazonHelp|amazon))\w+', '<USER_1>', scrubbed_text, flags=re.IGNORECASE)
        
        messages.append({
            'tweet_id': m['tweet_id'],
            'parent_tweet_id': m['in_response_to_tweet_id'],
            'created_at': m['created_at'],
            'author_id': m['author_id'] if m['author_id'] == 'AmazonHelp' else '<USER_1>',
            'inbound': str(m['inbound']).lower() == 'true',
            'text': scrubbed_text,
            'response_tweet_id': m['response_tweet_id']
        })
        
    gold_200.append({
        'case_id': case_id,
        'conversation_id': c['root_tweet_id'],
        'root_tweet_id': c['root_tweet_id'],
        'conversation_length': c['length'],
        'conversation_structure': 'branching' if c['has_branching'] else 'linear',
        'messages': messages
    })

with open('data/gold/gold_200.json', 'w') as f:
    json.dump(gold_200, f, indent=2)

with open('data/gold/gold_200.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    # Removing extra wrapper, flattening for the CSV as requested if needed, 
    # but the instructions said: "Each `messages` field should preserve the complete relevant conversation context" 
    # For CSV we can just have case_id and the tweet details
    writer.writerow(['case_id', 'conversation_id', 'tweet_id', 'parent_tweet_id', 'created_at', 'author_id', 'inbound', 'text'])
    for c in gold_200:
        for m in c['messages']:
            writer.writerow([
                c['case_id'], c['conversation_id'], m['tweet_id'], m['parent_tweet_id'],
                m['created_at'], m['author_id'], m['inbound'], m['text']
            ])

with open('data/gold/gold_200_annotation_template.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow([
        'case_id', 'intent', 'secondary_intent', 'multi_intent', 'trust_gate_tier',
        'safety_risk', 'capability_issue', 'must_cover_fact', 'human_escalation_required',
        'frustration_trajectory', 'one_line_reason', 'reference_resolution'
    ])
    for c in gold_200:
        writer.writerow([c['case_id']] + [''] * 11)

report = f"""# Gold Set Selection Report

## Dataset statistics
- Total TWCS rows: {len(df)}
- AmazonHelp rows: {amazon_help_tweets_count}
- Unique AmazonHelp tweets: {len(amazon_help_tweet_ids)}
- Candidate conversations: {len(amazon_roots)}
- Selected conversations = {len(selected_cases)}

## Distribution of selected 200

### Conversation Length
"""
length_counts = defaultdict(int)
for c in selected_cases:
    l = c['length']
    if l <= 2: bucket = 'short (<=2)'
    elif l <= 5: bucket = 'medium (3-5)'
    else: bucket = 'long (>=6)'
    length_counts[bucket] += 1
for k, v in length_counts.items():
    report += f"- {k}: {v}\n"

report += "\n### Structure\n"
structure_counts = defaultdict(int)
for c in selected_cases:
    structure_counts['branching' if c['has_branching'] else 'linear'] += 1
for k, v in structure_counts.items():
    report += f"- {k}: {v}\n"

report += "\n### Message Composition\n"
inbound_count = sum(sum(1 for m in c['messages'] if str(m['inbound']).lower() == 'true') for c in selected_cases)
outbound_count = sum(sum(1 for m in c['messages'] if str(m['inbound']).lower() == 'false') for c in selected_cases)
report += f"- Inbound messages: {inbound_count}\n"
report += f"- Outbound messages: {outbound_count}\n"

report += "\n### Topic Distribution (Approximated)\n"
topic_counts = defaultdict(int)
for c in selected_cases:
    topic_counts[c['topic']] += 1
for k, v in topic_counts.items():
    report += f"- {k}: {v}\n"

report += "\n### Indicators\n"
frustration_count = sum(1 for c in selected_cases if c['frustration'])
human_escalation_count = sum(1 for c in selected_cases if c['human_escalation'])
report += f"- Frustration indicators detected: {frustration_count}\n"
report += f"- Human escalation indicators detected: {human_escalation_count}\n"

with open('data/gold/gold_200_selection_report.md', 'w') as f:
    f.write(report)

print("Validation...")
print(f"- exactly 200 cases: {'PASS' if len(selected_cases) == 200 else 'FAIL'}")
print(f"- unique cases: {len(set(c['case_id'] for c in gold_200))}")
print(f"- unique root conversations: {len(set(c['conversation_id'] for c in gold_200))}")

print("Done.")
