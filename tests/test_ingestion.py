import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.ingestion.preprocess import build_conversations, process_pipeline
from src.ingestion.pii_scrubber import PIIScrubber

def test_branching_reconstruction():
    mock_data = {
        'tweet_id': ['1', '2', '3', '4', '5'],
        'author_id': ['CustA', 'AmazonHelp', 'CustA', 'CustA', 'AmazonHelp'],
        'in_response_to_tweet_id': [None, '1', '2', '2', '3'],
        'text': ['I need help', 'How can we help?', 'Order 12345678', 'Actually nevermind', 'Thanks for the order ID'],
        'created_at': ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05']
    }
    df = pd.DataFrame(mock_data)
    
    conversations, _ = build_conversations(df, brand_handle='AmazonHelp')
    assert len(conversations) == 1, f"Expected 1 conversation, got {len(conversations)}"
    
    conv = conversations[0]
    assert len(conv['branches']) == 2
    
    paths = conv['branches']
    assert ['1', '2', '3', '5'] in paths
    assert ['1', '2', '4'] in paths
    
    # 2. Test: Same tweet in multiple branches without duplicate indexing
    # Tweet 1 and 2 are shared. The tweets_set should contain exactly 5 tweets
    assert len(conv['tweets_set']) == 5

@patch.object(PIIScrubber, 'scrub_text_deterministic', wraps=PIIScrubber().scrub_text_deterministic)
def test_pii_scrubbed_once_per_tweet(mock_scrub):
    # A single root with multiple branches
    mock_data = {
        'tweet_id': ['1', '2', '3', '4'],
        'author_id': ['CustA', 'AmazonHelp', 'CustA', 'CustA'],
        'in_response_to_tweet_id': [None, '1', '2', '2'],
        'text': ['My name is John', 'Hi John', 'I am still John', 'John again'],
        'created_at': ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04']
    }
    df = pd.DataFrame(mock_data)
    
    process_pipeline(df, brand_handle='AmazonHelp')
    
    # Although there are 2 branches, and tweet 1 and 2 appear in both branches,
    # the scrubber should be called exactly 4 times (once per unique physical tweet).
    assert mock_scrub.call_count == 4

def test_deterministic_pii_stable_across_conversation():
    # Verify that the same entity in different tweets of the same conversation gets the same placeholder
    mock_data = {
        'tweet_id': ['1', '2'],
        'author_id': ['CustA', 'AmazonHelp'],
        'in_response_to_tweet_id': [None, '1'],
        'text': ['Order ID 111-1234567-1234567 is late', 'We are looking into Order ID 111-1234567-1234567'],
        'created_at': ['2026-01-01', '2026-01-02']
    }
    df = pd.DataFrame(mock_data)
    
    conversations = process_pipeline(df, brand_handle='AmazonHelp')
    conv = conversations[0]
    
    text1 = conv['tweets']['1']['text_clean']
    text2 = conv['tweets']['2']['text_clean']
    
    assert "ORDER_ID_1" in text1
    assert "ORDER_ID_1" in text2
    assert "111-1234567-1234567" not in text1
    assert "111-1234567-1234567" not in text2

def test_schema_prevents_evaluation_leakage():
    # Prove that the output schema groups branches under a conversation root,
    # thereby forcing any train/eval split to keep branches together.
    mock_data = {
        'tweet_id': ['1', '2', '3'],
        'author_id': ['CustA', 'AmazonHelp', 'CustA'],
        'in_response_to_tweet_id': [None, '1', '2'],
        'text': ['Help', 'OK', 'Thanks'],
        'created_at': ['2026-01-01', '2026-01-02', '2026-01-03']
    }
    df = pd.DataFrame(mock_data)
    conversations = process_pipeline(df, brand_handle='AmazonHelp')
    
    assert isinstance(conversations, list)
    conv = conversations[0]
    
    assert "root_tweet_id" in conv
    assert "tweets" in conv
    assert "branches" in conv
    
    # Branches only hold references, not duplicate dictionaries
    assert isinstance(conv["branches"][0][0], str)
