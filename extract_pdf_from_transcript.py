import json
import re

transcript_path = "/home/samay/.gemini/antigravity/brain/c86733be-30fe-4d02-bf50-1ba50ccf8d9f/.system_generated/logs/transcript_full.jsonl"
output_path = "data/gold/gold_200_cases_annotated.md"

ocr_blocks = []

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        # We can just use raw regex on the JSON line
        # But JSON strings have escaped newlines
        matches = re.findall(r'==Start of OCR for page \d+==\\n(.*?)\\n==End of OCR for page \d+==', line)
        for match in matches:
            # Unescape
            unescaped = match.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\/', '/')
            ocr_blocks.append(unescaped)

if ocr_blocks:
    extracted_text = "\n".join(ocr_blocks)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(extracted_text)
    print(f"Successfully extracted {len(ocr_blocks)} OCR blocks, {len(extracted_text)} characters.")
else:
    print("Found 0 OCR blocks.")
