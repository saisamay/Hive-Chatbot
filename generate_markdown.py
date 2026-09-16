import json
import os

with open('data/gold/gold_200.json', 'r') as f:
    cases = json.load(f)

markdown_output = []

for idx, case in enumerate(cases):
    case_num = idx + 1
    case_id = case.get('case_id', f"AMZ_{case_num:04d}")
    
    md = f"# Case {case_num:03d}\n\n"
    md += "## Conversation Metadata\n\n"
    md += f"- Case ID: {case_id}\n"
    md += f"- Root Tweet ID: {case['root_tweet_id']}\n"
    md += f"- Conversation ID: {case['conversation_id']}\n"
    md += f"- Conversation Length: {case['conversation_length']}\n"
    
    # Capitalize first letter of structure
    structure = str(case.get('conversation_structure', 'Linear')).capitalize()
    md += f"- Conversation Structure: {structure}\n\n"
    
    md += "## Conversation\n\n"
    
    turn_map = {}
    for i, msg in enumerate(case['messages']):
        turn_map[msg['tweet_id']] = i
        
        # Determine actor
        # If inbound == True, it's Customer. If inbound == False, it's Agent (AmazonHelp)
        is_inbound = msg.get('inbound', True)
        if type(is_inbound) == str:
            is_inbound = is_inbound.lower() == 'true'
            
        actor = "CUSTOMER" if is_inbound else "AGENT"
        
        # Check branching/reply
        parent_id = msg.get('parent_tweet_id')
        reply_str = ""
        if parent_id and parent_id in turn_map:
            parent_turn = turn_map[parent_id]
            # Only explicitly state if it's not a direct reply to the previous turn
            if parent_turn != i - 1:
                reply_str = f" | Reply to Turn {parent_turn}"
                
        md += f"**[{actor} - Turn {i}{reply_str}]**\n"
        md += f"{msg['text']}\n\n"
        
    md += """## Gold Set Annotation

- **Primary Intent:**
- **Secondary Intent:**
- **Multi-Intent:** Yes / No
- **Trust Gate Tier:** Auto-Handle / Deep Analysis / Human Escalation
- **Safety Risk:** Yes / No
- **Capability Issue:** Yes / No
- **Human Escalation Required:** Yes / No
- **Frustration Trajectory:** Decreasing / Stable / Increasing / Not Clear
- **Must-Cover Fact:**
- **Reference Resolution:**
- **One-Line Reason:**

## Annotation Notes

<optional notes>
"""
    
    markdown_output.append(md)

final_markdown = "\n".join(markdown_output)

output_path = 'data/gold/gold_200_cases.md'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(final_markdown)

print(f"Generated {len(cases)} cases in {output_path}")

# Validation checks
with open(output_path, 'r', encoding='utf-8') as f:
    content = f.read()

num_cases = content.count("# Case ")
has_annotations = content.count("## Gold Set Annotation")
has_primary_intent = content.count("- **Primary Intent:**")

print(f"Validation:")
print(f"- Found {num_cases} case headers")
print(f"- Found {has_annotations} annotation blocks")
print(f"- Found {has_primary_intent} Primary Intent fields")
