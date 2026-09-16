import json
import re

transcript_path = "/home/samay/.gemini/antigravity/brain/c86733be-30fe-4d02-bf50-1ba50ccf8d9f/.system_generated/logs/transcript_full.jsonl"

with open(transcript_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        data = json.loads(line)
        if data.get('type') == 'USER_INPUT':
            content = data.get('content', '')
            print(f"Line {i}: length {len(content)}")
            if "Start of OCR" in content:
                print(f"Found 'Start of OCR' at line {i}")
                with open('data/gold/raw_user_input.txt', 'w', encoding='utf-8') as out:
                    out.write(content)
                print("Saved raw content to data/gold/raw_user_input.txt")
