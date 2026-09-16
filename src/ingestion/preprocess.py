import re
import pandas as pd
from typing import List, Dict, Any, Tuple
from src.ingestion.pii_scrubber import PIIScrubber
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

def clean_text(text: str) -> str:
    """
    Strip boilerplate @mentions, normalize whitespace.
    Do not lowercase or strip punctuation (needed for sentiment/tone).
    """
    if not isinstance(text, str):
        return ""
    # Remove all @mentions
    text = re.sub(r'@\w+', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_dm_handoff(text: str) -> bool:
    """Flag brand replies matching hand-off patterns."""
    text_lower = text.lower()
    patterns = ["dm us", "direct message", "send us a dm", "message us"]
    return any(p in text_lower for p in patterns)

def build_conversations(df: pd.DataFrame, brand_handle: str = "AmazonHelp") -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Reconstruct threads supporting branching into Conversation objects.
    """
    df['tweet_id'] = df['tweet_id'].astype(str).str.replace(r'\.0$', '', regex=True)
    # in_response_to_tweet_id could be NaN, fill with empty string or handle properly
    df['in_response_to_tweet_id'] = df['in_response_to_tweet_id'].fillna('').astype(str).str.replace(r'\.0$', '', regex=True)
    
    # Create lookup dictionaries for fast traversal
    tweets_by_id = df.set_index('tweet_id').to_dict(orient='index')
    
    # Map each tweet to its direct children
    children_map = {}
    for tweet_id, row in tweets_by_id.items():
        parent_id = row['in_response_to_tweet_id']
        if parent_id and parent_id != 'nan':
            if parent_id not in children_map:
                children_map[parent_id] = []
            children_map[parent_id].append(tweet_id)
            
    # Find root tweets
    roots = []
    for tweet_id, row in tweets_by_id.items():
        parent_id = row['in_response_to_tweet_id']
        is_orphaned = False
        
        if not parent_id or parent_id == 'nan':
            roots.append((tweet_id, False))
        elif parent_id not in tweets_by_id:
            roots.append((tweet_id, True))

    conversations = []

    def dfs(current_id: str, current_path: List[str], branches: List[List[str]], conv_tweets: set):
        conv_tweets.add(current_id)
        children = children_map.get(current_id, [])
        if not children:
            # Leaf node reached, save the path
            branches.append(list(current_path))
            return
        
        for child_id in children:
            current_path.append(child_id)
            dfs(child_id, current_path, branches, conv_tweets)
            current_path.pop()

    for root_id, is_orphaned in roots:
        branches = []
        conv_tweets_set = set()
        dfs(root_id, [root_id], branches, conv_tweets_set)
        
        # Now filter branches that actually contain the brand handle anywhere in the conversation
        has_brand = any(
            str(tweets_by_id[tid].get('author_id', '')).lower() == brand_handle.lower()
            for tid in conv_tweets_set
        )
        if has_brand:
            conversations.append({
                "root_tweet_id": root_id,
                "is_orphaned_root": is_orphaned,
                "tweets_set": conv_tweets_set,
                "branches": branches
            })

    return conversations, tweets_by_id

def detect_language_safe(text: str) -> str:
    try:
        if not text.strip():
            return "unknown"
        return detect(text)
    except LangDetectException:
        return "unknown"

def process_pipeline(df: pd.DataFrame, brand_handle: str = "AmazonHelp") -> List[Dict[str, Any]]:
    """
    End-to-end preprocessing pipeline for the raw dataset.
    Outputs Conversation objects ensuring exactly once PII scrubbing per tweet.
    """
    conversations, raw_tweets_by_id = build_conversations(df, brand_handle)
    scrubber = PIIScrubber()
    
    processed_conversations = []
    for conv in conversations:
        entity_map = {}
        entity_counters = {}
        
        processed_tweets = {}
        inbound_texts = []
        outbound_texts = []
        
        # Precompute depths
        depth_map = {conv['root_tweet_id']: 0}
        for branch in conv['branches']:
            for i, tid in enumerate(branch):
                depth_map[tid] = i
                
        for tid in conv['tweets_set']:
            raw_msg = raw_tweets_by_id[tid]
            is_brand = str(raw_msg.get('author_id', '')).lower() == brand_handle.lower()
            direction = "outbound" if is_brand else "inbound"
            
            raw_text = str(raw_msg.get('text', ''))
            cleaned_text = clean_text(raw_text)
            
            # Scrub exactly once per physical tweet per conversation
            scrubbed_text = scrubber.scrub_text_deterministic(cleaned_text, entity_map, entity_counters)
            hashed_author = scrubber.hash_customer_id(str(raw_msg.get('author_id', '')))
            
            dm_handoff = False
            if is_brand:
                dm_handoff = is_dm_handoff(scrubbed_text)
                
            processed_msg = {
                'tweet_id': tid,
                'author_id_hashed': hashed_author,
                'inbound': not is_brand,
                'direction': direction,
                'turn_index': depth_map[tid],
                'text_clean': scrubbed_text,
                'is_dm_handoff': dm_handoff,
                'created_at': raw_msg.get('created_at')
            }
            processed_tweets[tid] = processed_msg
            
            if not is_brand:
                inbound_texts.append(cleaned_text)
            else:
                outbound_texts.append(cleaned_text)
                
        inbound_lang = detect_language_safe(" ".join(inbound_texts)) if inbound_texts else "unknown"
        outbound_lang = detect_language_safe(" ".join(outbound_texts)) if outbound_texts else "unknown"
        
        processed_conversations.append({
            "root_tweet_id": conv["root_tweet_id"],
            "is_orphaned_root": conv["is_orphaned_root"],
            "tweets": processed_tweets,
            "branches": conv["branches"],
            "inbound_language": inbound_lang,
            "outbound_language": outbound_lang
        })
        
    return processed_conversations
